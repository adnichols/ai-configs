#!/usr/bin/env python3
"""GitHub-backed PR agent lease/claim helper.

Purpose: prevent two Hermes/Pi agents on different hosts from remediating the same
GitHub PR at the same time. The lease is stored as hidden HTML-comment metadata
on the PR issue thread, so hosts only need shared GitHub access.

Typical use from a supervisor before launching/nudging a coding agent:
  github_pr_agent_claim.py acquire --repo Nodaste-Lab/heddle --pr 365 --ttl-minutes 90
  github_pr_agent_claim.py status  --repo Nodaste-Lab/heddle --pr 365
  github_pr_agent_claim.py release --repo Nodaste-Lab/heddle --pr 365

Exit codes:
  0: acquired/owned/released/status ok
  2: blocked by another active owner
  3: GitHub/tooling error
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import secrets
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


def run_gh(args: list[str], *, input_text: str | None = None) -> Any:
    cp = subprocess.run(
        ["gh", *args],
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Acquire/release a GitHub-backed PR agent lease.")
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

    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, indent=2, sort_keys=True), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
