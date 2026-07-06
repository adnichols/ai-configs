#!/usr/bin/env python3
"""GitHub-backed PR agent lease/claim helper.

Purpose: prevent two Hermes/Pi agents on different hosts from remediating the same
GitHub PR at the same time. The lease is stored as hidden HTML-comment metadata
on the PR issue thread, so hosts only need shared GitHub access.

It also has a best-effort active-session scanner for pi/herdr/tmux so a supervisor
can notice non-Hermes-managed agents already working on the same PR.

Typical use from a supervisor before launching/nudging a coding agent:
  github_pr_agent_claim.py acquire --repo Nodaste-Lab/heddle --pr 365 --ttl-minutes 90
  github_pr_agent_claim.py scan    --repo Nodaste-Lab/heddle --pr 365 --hosts local,dever
  github_pr_agent_claim.py status  --repo Nodaste-Lab/heddle --pr 365
  github_pr_agent_claim.py release --repo Nodaste-Lab/heddle --pr 365

Exit codes:
  0: acquired/owned/released/status ok; scan found no in-flight conflict
  2: blocked by another active owner or active session conflict
  3: GitHub/tooling error
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import secrets
import shlex
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

MARKER = "hermes-pr-agent-lease:v1"
DEFAULT_TTL_MINUTES = 90
DEFAULT_SETTLE_SECONDS = 3.0
DEFAULT_SCAN_HOSTS = os.environ.get("PR_AGENT_SCAN_HOSTS", "local,dever")
BUSY_STATUSES = {"working", "blocked"}
MAYBE_BUSY_STATUSES = {"unknown"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def default_owner() -> str:
    host = socket.gethostname().split(".")[0] or "unknown-host"
    profile = os.environ.get("HERMES_PROFILE") or "default"
    user = os.environ.get("USER") or os.environ.get("USERNAME") or "unknown-user"
    return f"{host}:{profile}:{user}"


def run_command(args: list[str], *, input_text: str | None = None, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def run_shell(command: str, *, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        shell=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def run_gh(args: list[str], *, input_text: str | None = None) -> Any:
    cp = run_command(["gh", *args], input_text=input_text, timeout=60)
    if cp.returncode != 0:
        raise RuntimeError((cp.stderr or cp.stdout or "gh command failed").strip())
    out = cp.stdout.strip()
    if not out:
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return out


@dataclass(frozen=True)
class Lease:
    comment_id: int
    comment_created_at: datetime | None
    comment_updated_at: datetime | None
    data: dict[str, Any]

    @property
    def sort_time(self) -> datetime:
        return self.comment_updated_at or self.comment_created_at or datetime.min.replace(tzinfo=timezone.utc)

    @property
    def owner(self) -> str:
        return str(self.data.get("owner") or "")

    @property
    def nonce(self) -> str:
        return str(self.data.get("nonce") or "")

    @property
    def action(self) -> str:
        return str(self.data.get("action") or "acquire")

    @property
    def expires_at(self) -> datetime | None:
        return parse_time(str(self.data.get("expires_at") or ""))

    @property
    def expired(self) -> bool:
        exp = self.expires_at
        return bool(exp and exp <= utc_now())

    @property
    def released(self) -> bool:
        return self.action == "release"


@dataclass(frozen=True)
class PRInfo:
    repo: str
    pr: int
    repo_name: str
    head_ref: str
    head_oid: str
    title: str


def encode_payload(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_payload(token: str) -> dict[str, Any] | None:
    try:
        padded = token + "=" * (-len(token) % 4)
        return json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
    except Exception:
        return None


def extract_payloads(body: str) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    needle = f"<!-- {MARKER} "
    pos = 0
    while True:
        start = body.find(needle, pos)
        if start < 0:
            return payloads
        start += len(needle)
        end = body.find(" -->", start)
        if end < 0:
            return payloads
        token = body[start:end].strip()
        data = decode_payload(token)
        if isinstance(data, dict):
            payloads.append(data)
        pos = end + 4


def list_leases(repo: str, pr: int) -> list[Lease]:
    comments = run_gh(["api", f"repos/{repo}/issues/{pr}/comments", "--paginate"]) or []
    leases: list[Lease] = []
    for c in comments:
        body = c.get("body") or ""
        for data in extract_payloads(body):
            if data.get("repo") != repo or int(data.get("pr") or 0) != pr:
                continue
            leases.append(
                Lease(
                    comment_id=int(c.get("id") or 0),
                    comment_created_at=parse_time(c.get("created_at")),
                    comment_updated_at=parse_time(c.get("updated_at")),
                    data=data,
                )
            )
    leases.sort(key=lambda l: (l.sort_time, l.comment_id))
    return leases


def active_lease(repo: str, pr: int) -> Lease | None:
    latest_by_owner: dict[str, Lease] = {}
    for lease in list_leases(repo, pr):
        latest_by_owner[lease.owner] = lease
    active = [l for l in latest_by_owner.values() if not l.expired and not l.released]
    if not active:
        return None
    active.sort(key=lambda l: (l.sort_time, l.comment_id))
    return active[-1]


def render_lease_body(payload: dict[str, Any], note: str = "") -> str:
    token = encode_payload(payload)
    rendered_note = f"\n{note.strip()}\n" if note.strip() else "\n"
    return f"<!-- {MARKER} {token} -->{rendered_note}"


def write_lease(repo: str, pr: int, payload: dict[str, Any], note: str = "", comment_id: int | None = None) -> int:
    body = render_lease_body(payload, note)
    if comment_id:
        result = run_gh(["api", "--method", "PATCH", f"repos/{repo}/issues/comments/{comment_id}", "-f", f"body={body}"])
        if isinstance(result, dict) and result.get("id"):
            return int(result["id"])
        return comment_id
    # `gh pr comment` has no stable JSON output, so use the Issues comments API.
    result = run_gh(["api", f"repos/{repo}/issues/{pr}/comments", "-f", f"body={body}"])
    if isinstance(result, dict) and result.get("id"):
        return int(result["id"])
    leases = list_leases(repo, pr)
    return leases[-1].comment_id if leases else 0


def get_pr_info(repo: str, pr: int) -> PRInfo:
    data = run_gh(["pr", "view", str(pr), "--repo", repo, "--json", "headRefName,headRefOid,title"])
    repo_name = repo.split("/", 1)[-1]
    return PRInfo(
        repo=repo,
        pr=pr,
        repo_name=repo_name,
        head_ref=str(data.get("headRefName") or ""),
        head_oid=str(data.get("headRefOid") or ""),
        title=str(data.get("title") or ""),
    )


def pr_tokens(info: PRInfo) -> list[str]:
    # Use exact PR/branch/head markers only. Do not match the bare number (`365`) or
    # split branch words (`test`), because those produce noisy false positives in
    # terminal scrollback, process IDs, and unrelated test output.
    tokens = [
        info.repo_name,
        f"pr-{info.pr}",
        f"pr/{info.pr}",
        f"pr_{info.pr}",
        f"pr{info.pr}",
        f"#{info.pr}",
    ]
    if info.head_ref:
        tokens.append(info.head_ref)
    if info.head_oid:
        tokens.append(info.head_oid[:12])
    return list(dict.fromkeys(t.lower() for t in tokens if t))


def summarize_match(text: str, info: PRInfo) -> tuple[bool, list[str]]:
    hay = text.lower()
    tokens = pr_tokens(info)
    specific_hits = [t for t in tokens if t != info.repo_name.lower() and t in hay]
    # A specific PR/branch/head match is enough. Repo-only matches are context, not proof.
    return bool(specific_hits), specific_hits[:12]


def classify_finding(source: str, status: str, text: str, info: PRInfo) -> tuple[str, bool, list[str]]:
    matched, evidence = summarize_match(text, info)
    status_l = (status or "unknown").lower()
    if status_l in BUSY_STATUSES and matched:
        return "in_flight", True, evidence
    if status_l in MAYBE_BUSY_STATUSES and matched:
        return "possible_in_flight", True, evidence
    if matched:
        return "matched_idle_or_unknown", False, evidence
    return "candidate_repo_context", False, evidence


def read_herdr_pane(pane_id: str) -> str:
    cp = run_command(["herdr", "pane", "read", pane_id, "--source", "recent-unwrapped", "--lines", "120"], timeout=10)
    return cp.stdout if cp.returncode == 0 else ""


def scan_herdr(info: PRInfo, include_idle: bool = False) -> list[dict[str, Any]]:
    if run_shell("command -v herdr >/dev/null 2>&1", timeout=5).returncode != 0:
        return []
    cp = run_command(["herdr", "pane", "list"], timeout=15)
    if cp.returncode != 0 or not cp.stdout.strip():
        return []
    try:
        data = json.loads(cp.stdout)
        panes = data.get("result", {}).get("panes", [])
    except Exception:
        return []
    findings: list[dict[str, Any]] = []
    repo_l = info.repo_name.lower()
    for pane in panes:
        pane_id = str(pane.get("pane_id") or "")
        fields = " ".join(str(pane.get(k) or "") for k in ["cwd", "foreground_cwd", "pane_id", "tab_id", "workspace_id", "agent", "agent_status"])
        agent_session = pane.get("agent_session") or {}
        fields = f"{fields} {agent_session.get('value', '')}"
        # Avoid reading every pane; read repo-ish or status-busy panes first.
        should_read = repo_l in fields.lower() or (pane.get("agent_status") in BUSY_STATUSES)
        tail = read_herdr_pane(pane_id) if pane_id and should_read else ""
        full_text = f"{fields}\n{tail}"
        classification, in_flight, evidence = classify_finding("herdr", str(pane.get("agent_status") or "unknown"), full_text, info)
        if in_flight or (include_idle and evidence):
            findings.append({
                "source": "herdr",
                "pane_id": pane_id,
                "agent": pane.get("agent"),
                "agent_status": pane.get("agent_status"),
                "cwd": pane.get("cwd"),
                "foreground_cwd": pane.get("foreground_cwd"),
                "workspace_id": pane.get("workspace_id"),
                "tab_id": pane.get("tab_id"),
                "session": agent_session,
                "classification": classification,
                "in_flight": in_flight,
                "evidence": evidence,
                "tail_excerpt": tail[-800:] if tail else "",
            })
    return findings


def tmux_capture(pane_id: str) -> str:
    cp = run_command(["tmux", "capture-pane", "-p", "-t", pane_id, "-S", "-120"], timeout=10)
    return cp.stdout if cp.returncode == 0 else ""


def scan_tmux(info: PRInfo, include_idle: bool = False) -> list[dict[str, Any]]:
    if run_shell("command -v tmux >/dev/null 2>&1", timeout=5).returncode != 0:
        return []
    fmt = "#{session_name}\t#{window_name}\t#{pane_id}\t#{pane_current_path}\t#{pane_current_command}\t#{pane_active}"
    cp = run_command(["tmux", "list-panes", "-a", "-F", fmt], timeout=10)
    if cp.returncode != 0 or not cp.stdout.strip():
        return []
    findings: list[dict[str, Any]] = []
    repo_l = info.repo_name.lower()
    for line in cp.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 6:
            continue
        session, window, pane_id, cwd, command, active = parts[:6]
        fields = " ".join([session, window, pane_id, cwd, command, active])
        should_capture = repo_l in fields.lower() or command.lower() in {"pi", "claude", "codex", "opencode", "bash", "zsh"}
        tail = tmux_capture(pane_id) if should_capture else ""
        full_text = f"{fields}\n{tail}"
        matched, evidence = summarize_match(full_text, info)
        looks_agent = any(x in (command + " " + tail).lower() for x in ["pi", "claude", "codex", "opencode", "agent"])
        in_flight = bool(matched and looks_agent)
        classification = "possible_in_flight" if in_flight else "matched_idle_or_unknown"
        if in_flight or (include_idle and evidence):
            findings.append({
                "source": "tmux",
                "session_name": session,
                "window_name": window,
                "pane_id": pane_id,
                "cwd": cwd,
                "current_command": command,
                "pane_active": active,
                "classification": classification,
                "in_flight": in_flight,
                "evidence": evidence,
                "tail_excerpt": tail[-800:] if tail else "",
            })
    return findings


def scan_ps(info: PRInfo, include_idle: bool = False) -> list[dict[str, Any]]:
    cp = run_command(["ps", "-axo", "pid=,ppid=,stat=,command="], timeout=10)
    if cp.returncode != 0:
        return []
    findings: list[dict[str, Any]] = []
    for line in cp.stdout.splitlines():
        lower = line.lower()
        if "github_pr_agent_claim.py" in lower:
            continue
        if not any(agent in lower for agent in [" pi", "/pi", "claude", "codex", "opencode", "herdr"]):
            continue
        matched, evidence = summarize_match(line, info)
        if matched or (include_idle and info.repo_name.lower() in lower):
            fields = line.split(None, 3)
            findings.append({
                "source": "process",
                "pid": fields[0] if len(fields) > 0 else "",
                "ppid": fields[1] if len(fields) > 1 else "",
                "stat": fields[2] if len(fields) > 2 else "",
                "command": fields[3] if len(fields) > 3 else line,
                "classification": "possible_in_flight" if matched else "candidate_repo_context",
                "in_flight": bool(matched),
                "evidence": evidence,
            })
    return findings


def scan_local_for_pr(repo: str, pr: int, include_idle: bool = False) -> dict[str, Any]:
    info = get_pr_info(repo, pr)
    findings: list[dict[str, Any]] = []
    findings.extend(scan_herdr(info, include_idle=include_idle))
    findings.extend(scan_tmux(info, include_idle=include_idle))
    findings.extend(scan_ps(info, include_idle=include_idle))
    # De-dupe obvious herdr/tmux overlaps by pane_id/source while preserving separate sources.
    return {
        "host": socket.gethostname().split(".")[0],
        "repo": repo,
        "pr": pr,
        "head_ref": info.head_ref,
        "head_oid": info.head_oid,
        "findings": findings,
        "in_flight_count": sum(1 for f in findings if f.get("in_flight")),
    }


def is_local_host(host: str) -> bool:
    host_l = host.lower()
    local_names = {"local", "localhost", socket.gethostname().lower(), socket.gethostname().split(".")[0].lower()}
    return host_l in local_names


def remote_scan(host: str, repo: str, pr: int, include_idle: bool = False) -> dict[str, Any]:
    if is_local_host(host):
        result = scan_local_for_pr(repo, pr, include_idle=include_idle)
        result["requested_host"] = host
        return result
    remote_cmd = " ".join([
        "$HOME/.hermes/scripts/github_pr_agent_claim.py",
        "scan-local",
        "--repo", shlex.quote(repo),
        "--pr", str(pr),
        "--json",
        "--include-idle" if include_idle else "",
    ]).strip()
    cp = run_command(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", host, remote_cmd], timeout=45)
    # scan-local returns 2 when it found an in-flight session; that is a valid
    # scan result, not an SSH/tooling failure.
    if cp.returncode not in (0, 2):
        return {"requested_host": host, "host": host, "error": (cp.stderr or cp.stdout).strip(), "findings": [], "in_flight_count": 0}
    try:
        out = cp.stdout.strip()
        if not out.startswith("{"):
            out = out[out.find("{"):]
        data = json.loads(out)
        data["requested_host"] = host
        if cp.stderr.strip():
            data["stderr"] = cp.stderr.strip()[-500:]
        return data
    except Exception:
        return {"requested_host": host, "host": host, "error": "remote scan returned non-JSON", "raw": cp.stdout[-1000:], "findings": [], "in_flight_count": 0}


def scan_hosts(repo: str, pr: int, hosts: str, include_idle: bool = False) -> dict[str, Any]:
    host_list = [h.strip() for h in hosts.split(",") if h.strip()]
    results = [remote_scan(host, repo, pr, include_idle=include_idle) for host in host_list]
    return {
        "status": "scan_complete",
        "repo": repo,
        "pr": pr,
        "hosts": results,
        "in_flight_count": sum(int(r.get("in_flight_count") or 0) for r in results),
    }


def active_session_conflicts(scan: dict[str, Any]) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    for host in scan.get("hosts", []):
        for finding in host.get("findings", []):
            if finding.get("in_flight"):
                conflicts.append({"host": host.get("host") or host.get("requested_host"), **finding})
    return conflicts


def acquire(args: argparse.Namespace) -> int:
    owner = args.owner or default_owner()
    current = active_lease(args.repo, args.pr)
    if current and current.owner != owner and not args.force:
        print(json.dumps({
            "status": "blocked",
            "repo": args.repo,
            "pr": args.pr,
            "owner": owner,
            "active_owner": current.owner,
            "active_expires_at": current.data.get("expires_at"),
            "active_comment_id": current.comment_id,
            "active_purpose": current.data.get("purpose"),
        }, indent=2, sort_keys=True))
        return 2

    if args.check_active_sessions and not args.allow_active_sessions:
        scan = scan_hosts(args.repo, args.pr, args.scan_hosts, include_idle=args.include_idle_sessions)
        conflicts = active_session_conflicts(scan)
        # If this same owner is renewing an existing lease, allow the already-owned run to continue;
        # otherwise pre-existing active sessions mean a non-lease actor may be working.
        if conflicts and not (current and current.owner == owner):
            print(json.dumps({
                "status": "blocked_active_session",
                "repo": args.repo,
                "pr": args.pr,
                "owner": owner,
                "conflicts": conflicts,
                "scan": scan,
            }, indent=2, sort_keys=True))
            return 2

    nonce = args.nonce or secrets.token_urlsafe(12)
    now = utc_now()
    payload = {
        "marker": MARKER,
        "action": "acquire",
        "repo": args.repo,
        "pr": args.pr,
        "head": args.head or "",
        "owner": owner,
        "host": socket.gethostname(),
        "purpose": args.purpose,
        "nonce": nonce,
        "claimed_at": iso(now),
        "expires_at": iso(now + timedelta(minutes=args.ttl_minutes)),
        "pid": os.getpid(),
    }
    if args.dry_run:
        print(json.dumps({"status": "would_acquire", "lease": payload, "previous_active_owner": current.owner if current else None}, indent=2, sort_keys=True))
        return 0

    renew_comment_id = current.comment_id if current and current.owner == owner and not args.force else None
    comment_id = write_lease(args.repo, args.pr, payload, note=args.visible_note, comment_id=renew_comment_id)
    if args.settle_seconds > 0:
        time.sleep(args.settle_seconds)
    winner = active_lease(args.repo, args.pr)
    if winner and winner.owner == owner and winner.nonce == nonce:
        print(json.dumps({
            "status": "acquired",
            "repo": args.repo,
            "pr": args.pr,
            "owner": owner,
            "expires_at": payload["expires_at"],
            "comment_id": comment_id,
            "nonce": nonce,
        }, indent=2, sort_keys=True))
        return 0

    print(json.dumps({
        "status": "lost_race",
        "repo": args.repo,
        "pr": args.pr,
        "owner": owner,
        "posted_comment_id": comment_id,
        "active_owner": winner.owner if winner else None,
        "active_expires_at": winner.data.get("expires_at") if winner else None,
        "active_comment_id": winner.comment_id if winner else None,
    }, indent=2, sort_keys=True))
    return 2


def status(args: argparse.Namespace) -> int:
    lease = active_lease(args.repo, args.pr)
    if not lease:
        print(json.dumps({"status": "unclaimed", "repo": args.repo, "pr": args.pr}, indent=2, sort_keys=True))
        return 0
    print(json.dumps({
        "status": "claimed",
        "repo": args.repo,
        "pr": args.pr,
        "active_owner": lease.owner,
        "active_expires_at": lease.data.get("expires_at"),
        "active_comment_id": lease.comment_id,
        "active_head": lease.data.get("head"),
        "active_purpose": lease.data.get("purpose"),
    }, indent=2, sort_keys=True))
    return 0


def release(args: argparse.Namespace) -> int:
    owner = args.owner or default_owner()
    current = active_lease(args.repo, args.pr)
    if current and current.owner != owner and not args.force:
        print(json.dumps({
            "status": "blocked",
            "repo": args.repo,
            "pr": args.pr,
            "owner": owner,
            "active_owner": current.owner,
            "active_expires_at": current.data.get("expires_at"),
            "active_comment_id": current.comment_id,
        }, indent=2, sort_keys=True))
        return 2
    now = utc_now()
    payload = {
        "marker": MARKER,
        "action": "release",
        "repo": args.repo,
        "pr": args.pr,
        "owner": owner,
        "host": socket.gethostname(),
        "purpose": args.purpose,
        "nonce": args.nonce or secrets.token_urlsafe(12),
        "claimed_at": iso(now),
        "expires_at": iso(now),
        "pid": os.getpid(),
    }
    if args.dry_run:
        print(json.dumps({"status": "would_release", "lease": payload}, indent=2, sort_keys=True))
        return 0
    release_comment_id = current.comment_id if current and current.owner == owner else None
    comment_id = write_lease(args.repo, args.pr, payload, note=args.visible_note, comment_id=release_comment_id)
    print(json.dumps({"status": "released", "repo": args.repo, "pr": args.pr, "owner": owner, "comment_id": comment_id}, indent=2, sort_keys=True))
    return 0


def scan_cmd(args: argparse.Namespace) -> int:
    result = scan_hosts(args.repo, args.pr, args.hosts, include_idle=args.include_idle)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 2 if result["in_flight_count"] else 0


def scan_local_cmd(args: argparse.Namespace) -> int:
    result = scan_local_for_pr(args.repo, args.pr, include_idle=args.include_idle)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 2 if result["in_flight_count"] else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Acquire/release a GitHub-backed PR agent lease and scan active PR sessions.")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--repo", required=True, help="GitHub repo, e.g. Nodaste-Lab/heddle")
        p.add_argument("--pr", type=int, required=True, help="Pull request number")
        p.add_argument("--owner", default=os.environ.get("PR_AGENT_CLAIM_OWNER"), help="Stable owner id; defaults to host:profile:user")
        p.add_argument("--purpose", default="pr-codex-feedback", help="Why this lease exists")

    p_acq = sub.add_parser("acquire", help="Acquire or renew the lease")
    add_common(p_acq)
    p_acq.add_argument("--head", default="", help="Current PR head sha for observability")
    p_acq.add_argument("--ttl-minutes", type=int, default=DEFAULT_TTL_MINUTES)
    p_acq.add_argument("--settle-seconds", type=float, default=DEFAULT_SETTLE_SECONDS)
    p_acq.add_argument("--nonce", default="")
    p_acq.add_argument("--visible-note", default="", help="Optional visible text after the hidden marker; default stays invisible")
    p_acq.add_argument("--force", action="store_true", help="Override an active lease from another owner")
    p_acq.add_argument("--dry-run", action="store_true")
    p_acq.add_argument("--check-active-sessions", action="store_true", help="Scan pi/herdr/tmux before acquiring if no same-owner lease exists")
    p_acq.add_argument("--allow-active-sessions", action="store_true", help="Do not block acquire on scan findings")
    p_acq.add_argument("--scan-hosts", default=DEFAULT_SCAN_HOSTS, help="Comma-separated host list for --check-active-sessions; use local for this host")
    p_acq.add_argument("--include-idle-sessions", action="store_true", help="Include idle matched sessions in scan output")
    p_acq.set_defaults(func=acquire)

    p_status = sub.add_parser("status", help="Show active lease status")
    add_common(p_status)
    p_status.set_defaults(func=status)

    p_rel = sub.add_parser("release", help="Release the lease")
    add_common(p_rel)
    p_rel.add_argument("--nonce", default="")
    p_rel.add_argument("--visible-note", default="")
    p_rel.add_argument("--force", action="store_true")
    p_rel.add_argument("--dry-run", action="store_true")
    p_rel.set_defaults(func=release)

    p_scan = sub.add_parser("scan", help="Scan local/remote hosts for active pi/herdr/tmux sessions matching the PR")
    p_scan.add_argument("--repo", required=True)
    p_scan.add_argument("--pr", type=int, required=True)
    p_scan.add_argument("--hosts", default=DEFAULT_SCAN_HOSTS, help="Comma-separated hosts; local means this host")
    p_scan.add_argument("--include-idle", action="store_true")
    p_scan.set_defaults(func=scan_cmd)

    p_scan_local = sub.add_parser("scan-local", help="Scan only this host; used by remote scan")
    p_scan_local.add_argument("--repo", required=True)
    p_scan_local.add_argument("--pr", type=int, required=True)
    p_scan_local.add_argument("--include-idle", action="store_true")
    p_scan_local.add_argument("--json", action="store_true", help="Accepted for remote callers; output is always JSON")
    p_scan_local.set_defaults(func=scan_local_cmd)

    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except subprocess.TimeoutExpired as exc:
        print(json.dumps({"status": "error", "error": f"timeout: {exc}"}, indent=2, sort_keys=True), file=sys.stderr)
        return 3
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, indent=2, sort_keys=True), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
