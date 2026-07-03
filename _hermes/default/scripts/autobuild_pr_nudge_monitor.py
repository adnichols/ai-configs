#!/usr/bin/env python3
"""Reusable PR nudge monitor for autobuild Linear issues.

Quiet-by-default cron script. Configure monitors in:
  ~/.hermes/pr-nudge-monitors.json

The script only acts on PRs linked to Linear issues that have the configured
required label (default: autobuild). Non-autobuild PRs are ignored.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HOME = Path.home()
HERMES_HOME = Path(os.environ.get("HERMES_HOME", HOME / ".hermes"))
ROOT_CONFIG_PATH = HERMES_HOME / "pr-nudge-monitors.json"
BUNDLED_CONFIG_PATH = HERMES_HOME / "scripts" / "autobuild_pr_nudge_monitor.config.json"
CONFIG_PATH = Path(os.environ["PR_NUDGE_CONFIG"]) if os.environ.get("PR_NUDGE_CONFIG") else (ROOT_CONFIG_PATH if ROOT_CONFIG_PATH.exists() else BUNDLED_CONFIG_PATH)
STATE_PATH = Path(os.environ.get("PR_NUDGE_STATE", HERMES_HOME / "state" / "autobuild_pr_nudge_monitor.json"))
LOG_PATH = Path(os.environ.get("PR_NUDGE_LOG", HERMES_HOME / "logs" / "autobuild_pr_nudge_monitor.log"))
DRY_RUN = os.environ.get("DRY_RUN", "").lower() in {"1", "true", "yes"}
MERGE_READY_LABEL = os.environ.get("PR_NUDGE_MERGE_READY_LABEL", "merge-ready")
MERGE_READY_LABEL_COLOR = os.environ.get("PR_NUDGE_MERGE_READY_LABEL_COLOR", "0E8A16")
MERGE_READY_LABEL_DESCRIPTION = os.environ.get(
    "PR_NUDGE_MERGE_READY_LABEL_DESCRIPTION",
    "Autobuild monitor: current head is clean and Codex-ready",
)
CODEX_LOGIN_RE = re.compile(r"codex|chatgpt", re.I)
BOILERPLATE_THUMBS_RE = re.compile(r"otherwise it will react with 👍|Useful\? React with 👍 / 👎", re.I)
RATE_LIMIT_RE = re.compile(r"rate_limited|Ratelimited|requestsRemaining=0", re.I)
REVIEWED_COMMIT_RE = re.compile(r"Reviewed commit:\*\*\s*`?([0-9a-f]{7,40})`?", re.I)


@dataclass(frozen=True)
class Monitor:
    name: str
    repo: str
    repo_dir: Path | None
    linear_team: str
    linear_project: str | None
    issue_key_prefix: str
    required_label: str
    rework_state: str
    merge_on_codex_ready: bool
    enabled: bool = True

    @property
    def issue_re(self) -> re.Pattern[str]:
        return re.compile(rf"\b{re.escape(self.issue_key_prefix)}-\d+\b", re.I)

    @property
    def state_key(self) -> str:
        return re.sub(r"[^A-Za-z0-9_.-]+", "_", self.name or self.repo)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(msg: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(f"{utc_now()} {msg}\n")


def run(cmd: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    log("$ " + " ".join(shlex.quote(c) for c in cmd))
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check)


def json_cmd(cmd: list[str], *, cwd: Path | None = None) -> Any:
    cp = run(cmd, cwd=cwd)
    text = cp.stdout.strip()
    return json.loads(text) if text else None


def gh_api(repo: str, endpoint: str, *, cwd: Path | None = None, paginate: bool = True) -> Any:
    cmd = ["gh", "api", endpoint]
    if paginate:
        cmd.append("--paginate")
    return json_cmd(cmd, cwd=cwd)


def load_config(path: Path = CONFIG_PATH) -> list[Monitor]:
    if not path.exists():
        raise SystemExit(f"Missing config: {path}. Create it with a monitors[] list.")
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    monitors_raw = raw.get("monitors") if isinstance(raw, dict) else raw
    if not isinstance(monitors_raw, list):
        raise SystemExit(f"Invalid config: {path}; expected monitors list")
    monitors: list[Monitor] = []
    for item in monitors_raw:
        if not item.get("enabled", True):
            continue
        repo = item["repo"]
        repo_dir = Path(item["repo_dir"]).expanduser() if item.get("repo_dir") else None
        linear_team = item.get("linear_team") or item.get("team")
        if not linear_team:
            raise SystemExit(f"Monitor {item.get('name') or repo} missing linear_team")
        prefix = item.get("issue_key_prefix") or linear_team
        monitors.append(
            Monitor(
                name=item.get("name") or repo,
                repo=repo,
                repo_dir=repo_dir,
                linear_team=linear_team,
                linear_project=item.get("linear_project") or item.get("project"),
                issue_key_prefix=prefix.upper(),
                required_label=item.get("required_label", "autobuild"),
                rework_state=item.get("rework_state", "Rework"),
                merge_on_codex_ready=bool(item.get("merge_on_codex_ready", True)),
            )
        )
    return monitors


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"monitors": {}}
    try:
        with STATE_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("monitors", {})
        return data
    except Exception as exc:
        log(f"state load failed: {exc}")
        return {"monitors": {}}


def save_state(state: dict[str, Any]) -> None:
    if DRY_RUN:
        return
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)
    tmp.replace(STATE_PATH)


def monitor_state(state: dict[str, Any], monitor: Monitor) -> dict[str, Any]:
    monitors = state.setdefault("monitors", {})
    data = monitors.setdefault(monitor.state_key, {"events": {}, "completed_notified": False})
    data.setdefault("events", {})
    data.setdefault("completed_notified", False)
    return data


def rate_limited(text: str) -> bool:
    return bool(RATE_LIMIT_RE.search(text or ""))


def ltui_json(cmd: list[str], *, cwd: Path | None = None) -> tuple[bool, Any, str]:
    cp = run(cmd, cwd=cwd, check=False)
    combined = (cp.stdout + cp.stderr).strip()
    if cp.returncode != 0:
        return False, None, combined
    try:
        return True, json.loads(cp.stdout), combined
    except Exception as exc:
        return False, None, f"JSON parse failed: {exc}; output={combined[:1000]}"


def list_required_label_issues(monitor: Monitor) -> tuple[dict[str, dict[str, Any]] | None, str]:
    cmd = ["ltui", "--format", "json", "--limit", "250", "issues", "list", "--team", monitor.linear_team, "--label", monitor.required_label]
    if monitor.linear_project:
        cmd.extend(["--project", monitor.linear_project])
    ok, data, msg = ltui_json(cmd, cwd=monitor.repo_dir)
    if not ok:
        return None, msg
    rows = data.get("rows") if isinstance(data, dict) else data
    issues: dict[str, dict[str, Any]] = {}
    for row in rows or []:
        ident = row.get("identifier") or row.get("id") or row.get("key")
        if isinstance(ident, str) and monitor.issue_re.fullmatch(ident):
            issues[ident.upper()] = row
    return issues, ""


def ltui_update_rework(monitor: Monitor, issue: str) -> tuple[bool, str]:
    if DRY_RUN:
        return True, "dry-run"
    cmd = ["ltui", "issues", "update", issue, "--team", monitor.linear_team, "--state", monitor.rework_state]
    if monitor.linear_project:
        cmd.extend(["--project", monitor.linear_project])
    cp = run(cmd, cwd=monitor.repo_dir, check=False)
    return cp.returncode == 0, (cp.stdout + cp.stderr).strip()


def ltui_comment(monitor: Monitor, issue: str, body: str) -> tuple[bool, str]:
    if DRY_RUN:
        return True, "dry-run"
    comment_file = Path("/tmp") / f"pr-nudge-{monitor.state_key}-{issue}-{os.getpid()}.md"
    comment_file.write_text(body, encoding="utf-8")
    try:
        cp = run(["ltui", "issues", "comment", issue, "--body", f"@{comment_file}"], cwd=monitor.repo_dir, check=False)
        return cp.returncode == 0, (cp.stdout + cp.stderr).strip()
    finally:
        try:
            comment_file.unlink()
        except FileNotFoundError:
            pass


def codex_user(item: dict[str, Any]) -> bool:
    user = item.get("user") or item.get("author") or {}
    login = user.get("login") or user.get("name") or ""
    return bool(CODEX_LOGIN_RE.search(login))


def extract_linear_ids(monitor: Monitor, pr: dict[str, Any], issue_comments: list[dict[str, Any]]) -> list[str]:
    ids: list[str] = []

    def add(found: str) -> None:
        found = found.upper()
        if found not in ids:
            ids.append(found)

    for text in [pr.get("title") or "", pr.get("headRefName") or ""]:
        for found in monitor.issue_re.findall(text):
            add(found)

    body = pr.get("body") or ""
    closing_re = re.compile(rf"(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s*:?#?\s*({re.escape(monitor.issue_key_prefix)}-\d+)", re.I)
    for found in closing_re.findall(body):
        add(found)

    link_re = re.compile(rf"linear\.app/[^/]+/issue/({re.escape(monitor.issue_key_prefix)}-\d+)", re.I)
    for c in issue_comments:
        cbody = c.get("body") or ""
        if "linear.app" not in cbody:
            continue
        matches = link_re.findall(cbody)
        if matches:
            # First Linear linkback URL is the attached issue. Later URLs may be related issue refs.
            add(matches[0])
    return ids


def body_has_ready_signal(body: str) -> bool:
    normalized = (body or "").strip().lower()
    if not normalized:
        return False
    compact = re.sub(r"\s+", " ", normalized)
    explicit_ready_phrases = [
        "didn't find any major issues",
        "did not find any major issues",
        "no issues found",
        "no changes requested",
        "looks good to me",
        "ready to merge",
        "nothing to flag",
    ]
    if any(p in compact for p in explicit_ready_phrases):
        return True
    if BOILERPLATE_THUMBS_RE.search(body or ""):
        return False
    if compact in {"👍", ":+1:", "+1", "lgtm", "looks good", "ship it", "approved"}:
        return True
    return any(p in compact for p in ["lgtm", "approved"])


def reviewed_commit_matches_head(body: str, head: str) -> bool:
    match = REVIEWED_COMMIT_RE.search(body or "")
    if not match:
        return True
    reviewed = match.group(1).lower()
    head = (head or "").lower()
    return bool(head) and (head.startswith(reviewed) or reviewed.startswith(head))


def pr_label_names(pr: dict[str, Any]) -> set[str]:
    return {str(label.get("name") or label).casefold() for label in pr.get("labels") or []}


def ensure_merge_ready_label(monitor: Monitor) -> None:
    if DRY_RUN:
        return
    run(
        [
            "gh",
            "label",
            "create",
            MERGE_READY_LABEL,
            "--repo",
            monitor.repo,
            "--color",
            MERGE_READY_LABEL_COLOR,
            "--description",
            MERGE_READY_LABEL_DESCRIPTION,
            "--force",
        ],
        cwd=monitor.repo_dir,
        check=False,
    )


def set_merge_ready_label(monitor: Monitor, pr: dict[str, Any], ready: bool, outputs: list[str], reason: str) -> None:
    has_label = MERGE_READY_LABEL.casefold() in pr_label_names(pr)
    if ready == has_label:
        return
    pr_number = pr["number"]
    action = "add" if ready else "remove"
    if DRY_RUN:
        outputs.append(f"[dry-run] {monitor.name}: would {action} `{MERGE_READY_LABEL}` on PR #{pr_number} ({reason}). {pr.get('url')}")
        return
    if ready:
        ensure_merge_ready_label(monitor)
        cp = run(["gh", "pr", "edit", str(pr_number), "--repo", monitor.repo, "--add-label", MERGE_READY_LABEL], cwd=monitor.repo_dir, check=False)
    else:
        cp = run(["gh", "pr", "edit", str(pr_number), "--repo", monitor.repo, "--remove-label", MERGE_READY_LABEL], cwd=monitor.repo_dir, check=False)
    combined = (cp.stdout + cp.stderr).strip()
    if cp.returncode == 0:
        verb = "added to" if ready else "removed from"
        outputs.append(f"🏷️ {monitor.name}: `{MERGE_READY_LABEL}` {verb} PR #{pr_number} ({reason}). {pr.get('url')}")
        labels = pr.setdefault("labels", [])
        if ready:
            labels.append({"name": MERGE_READY_LABEL})
        else:
            pr["labels"] = [label for label in labels if str(label.get("name") or label).casefold() != MERGE_READY_LABEL.casefold()]
    else:
        outputs.append(f"⚠️ {monitor.name}: failed to {action} `{MERGE_READY_LABEL}` on PR #{pr_number}: {combined[:500]} {pr.get('url')}")


def body_is_feedback(body: str) -> bool:
    if not body or body_has_ready_signal(body):
        return False
    lowered = body.lower()
    return any(m in lowered for m in ["codex review", "automated review suggestions", "p0 badge", "p1 badge", "p2 badge", "p3 badge", "request changes", "suggestion", "bug", "issue"])


def reaction_ready(monitor: Monitor, endpoint: str) -> bool:
    try:
        reactions = gh_api(monitor.repo, endpoint, cwd=monitor.repo_dir, paginate=True) or []
    except Exception as exc:
        log(f"{monitor.name}: reaction fetch failed {endpoint}: {exc}")
        return False
    return any(r.get("content") == "+1" and codex_user(r) for r in reactions)


def analyze_codex(monitor: Monitor, pr: dict[str, Any], reviews: list[dict[str, Any]], review_comments: list[dict[str, Any]], issue_comments: list[dict[str, Any]]) -> dict[str, Any]:
    head = pr.get("headRefOid") or ""
    head_short10 = head[:10]
    feedback: list[dict[str, Any]] = []
    ready: list[dict[str, Any]] = []

    for c in review_comments:
        if not codex_user(c):
            continue
        if (c.get("commit_id") or "") != head:
            continue
        body = c.get("body") or ""
        if body_is_feedback(body):
            feedback.append({"kind": "review_comment", "id": c.get("id"), "url": c.get("html_url"), "body": body[:500]})
        if body_has_ready_signal(body):
            ready.append({"kind": "review_comment", "id": c.get("id"), "url": c.get("html_url")})
        if c.get("id") and reaction_ready(monitor, f"repos/{monitor.repo}/pulls/comments/{c['id']}/reactions"):
            ready.append({"kind": "review_comment_reaction", "id": c.get("id"), "url": c.get("html_url")})

    for r in reviews:
        if not codex_user(r):
            continue
        commit_id = r.get("commit_id") or ""
        if commit_id and commit_id != head:
            continue
        body = r.get("body") or ""
        state = (r.get("state") or "").upper()
        if state == "APPROVED":
            ready.append({"kind": "review_approved", "id": r.get("id"), "url": r.get("html_url")})
        elif body_has_ready_signal(body) and (head in body or head_short10 in body or not commit_id):
            ready.append({"kind": "review_ready_text", "id": r.get("id"), "url": r.get("html_url")})
        if body_is_feedback(body) and not any(f["kind"] == "review_comment" for f in feedback):
            feedback.append({"kind": "review_body", "id": r.get("id"), "url": r.get("html_url"), "body": body[:500]})

    for c in issue_comments:
        if not codex_user(c):
            continue
        body = c.get("body") or ""
        if body_has_ready_signal(body) and reviewed_commit_matches_head(body, head):
            ready.append({"kind": "issue_comment_ready", "id": c.get("id"), "url": c.get("html_url")})
        if c.get("id") and (head in body or head_short10 in body) and reaction_ready(monitor, f"repos/{monitor.repo}/issues/comments/{c['id']}/reactions"):
            ready.append({"kind": "issue_comment_reaction", "id": c.get("id"), "url": c.get("html_url")})

    return {"feedback": feedback, "ready": ready}


def conflict_state(monitor: Monitor, pr_number: int, list_state: str) -> tuple[bool, str]:
    pull = gh_api(monitor.repo, f"repos/{monitor.repo}/pulls/{pr_number}", cwd=monitor.repo_dir, paginate=False)
    mergeable = pull.get("mergeable")
    mergeable_state = pull.get("mergeable_state") or ""
    if mergeable is None or mergeable_state == "unknown":
        time.sleep(2)
        pull = gh_api(monitor.repo, f"repos/{monitor.repo}/pulls/{pr_number}", cwd=monitor.repo_dir, paginate=False)
        mergeable = pull.get("mergeable")
        mergeable_state = pull.get("mergeable_state") or ""
    dirty = list_state == "DIRTY" or mergeable is False or mergeable_state in {"dirty", "blocked"}
    return dirty, f"mergeStateStatus={list_state or 'unknown'}, mergeable={mergeable}, mergeable_state={mergeable_state or 'unknown'}"


def mark_rework(monitor: Monitor, issue: str, issue_meta: dict[str, Any], pr: dict[str, Any], reason: str, detail_url: str, detail_text: str, mstate: dict[str, Any], outputs: list[str]) -> None:
    head = pr.get("headRefOid") or ""
    pr_number = pr["number"]
    key = f"rework:{reason}:{issue}:pr{pr_number}:{head}:{detail_url or detail_text[:80]}"
    issue_state = str((issue_meta or {}).get("state") or "")
    issue_already_in_rework = issue_state.casefold() == monitor.rework_state.casefold()
    if key in mstate["events"] and issue_already_in_rework:
        return
    body = (
        f"Automated autobuild PR monitor moved this back to **{monitor.rework_state}**.\n\n"
        f"PR #{pr_number} has {reason}: {pr.get('url')}\n"
        f"{detail_text}\n\n"
        "Agent: respond to the Codex feedback / resolve the merge conflict, push the fix, and get a fresh Codex 👍 before returning this to review."
    )
    ok_update, update_out = ltui_update_rework(monitor, issue)
    if not ok_update:
        if rate_limited(update_out):
            log(f"{monitor.name}: ltui rate limited updating {issue}: {update_out}")
            return
        outputs.append(f"⚠️ {monitor.name}: failed to move {issue} to {monitor.rework_state} for PR #{pr_number}: {update_out[:500]}")
        return
    ok_comment, comment_out = ltui_comment(monitor, issue, body)
    if not ok_comment:
        if rate_limited(comment_out):
            log(f"{monitor.name}: ltui rate limited commenting {issue}: {comment_out}")
            return
        outputs.append(f"⚠️ {monitor.name}: moved {issue} to {monitor.rework_state} for PR #{pr_number}, but failed to add comment: {comment_out[:500]}")
        return
    mstate["events"][key] = utc_now()
    outputs.append(f"↩️ {monitor.name}: {issue} → {monitor.rework_state}; PR #{pr_number} {reason}. {detail_url or pr.get('url')}")


def merge_pr(monitor: Monitor, pr: dict[str, Any], ready_sources: list[dict[str, Any]], mstate: dict[str, Any], outputs: list[str]) -> None:
    if not monitor.merge_on_codex_ready:
        return
    head = pr.get("headRefOid") or ""
    pr_number = pr["number"]
    key = f"merge:pr{pr_number}:{head}:{','.join(str(s.get('id')) for s in ready_sources)}"
    if key in mstate["events"]:
        return
    if DRY_RUN:
        outputs.append(f"[dry-run] {monitor.name}: would merge PR #{pr_number}: {pr.get('url')}")
        return
    cp = run(["gh", "pr", "merge", str(pr_number), "--repo", monitor.repo, "--squash", "--delete-branch", "--auto"], cwd=monitor.repo_dir, check=False)
    combined = (cp.stdout + cp.stderr).strip()
    if cp.returncode != 0 and ("not supported" in combined.lower() or "GraphQL" in combined or "Pull request is in clean status" in combined):
        cp = run(["gh", "pr", "merge", str(pr_number), "--repo", monitor.repo, "--squash", "--delete-branch"], cwd=monitor.repo_dir, check=False)
        combined = (cp.stdout + cp.stderr).strip()
    if cp.returncode == 0:
        mstate["events"][key] = utc_now()
        outputs.append(f"✅ {monitor.name}: merge/auto-merge set for PR #{pr_number} after Codex 👍: {pr.get('url')}")
    else:
        outputs.append(f"⚠️ {monitor.name}: PR #{pr_number} has Codex 👍 but merge failed: {combined[:700]} {pr.get('url')}")


def process_monitor(monitor: Monitor, state: dict[str, Any], outputs: list[str]) -> None:
    mstate = monitor_state(state, monitor)
    label_issues, label_msg = list_required_label_issues(monitor)
    if label_issues is None:
        if rate_limited(label_msg):
            log(f"{monitor.name}: Linear rate-limited while listing {monitor.required_label} issues; skipping quietly")
            return
        outputs.append(f"⚠️ {monitor.name}: could not list Linear issues with label {monitor.required_label}: {label_msg[:700]}")
        return

    prs = json_cmd([
        "gh", "pr", "list", "--repo", monitor.repo, "--state", "open", "--json",
        "number,title,url,headRefName,body,headRefOid,mergeStateStatus,reviewDecision,labels", "--limit", "100",
    ], cwd=monitor.repo_dir)

    if not prs:
        if not mstate.get("completed_notified"):
            outputs.append(f"✅ {monitor.name}: no open PRs in {monitor.repo}.")
            mstate["completed_notified"] = True
        return
    mstate["completed_notified"] = False

    for pr in prs:
        n = pr["number"]
        try:
            issue_comments = gh_api(monitor.repo, f"repos/{monitor.repo}/issues/{n}/comments", cwd=monitor.repo_dir, paginate=True) or []
            linked = extract_linear_ids(monitor, pr, issue_comments)
            autobuild_linked = [issue for issue in linked if issue in label_issues]

            reviews = gh_api(monitor.repo, f"repos/{monitor.repo}/pulls/{n}/reviews", cwd=monitor.repo_dir, paginate=True) or []
            review_comments = gh_api(monitor.repo, f"repos/{monitor.repo}/pulls/{n}/comments", cwd=monitor.repo_dir, paginate=True) or []
            dirty, dirty_detail = conflict_state(monitor, n, pr.get("mergeStateStatus") or "")
            codex = analyze_codex(monitor, pr, reviews, review_comments, issue_comments)

            if dirty:
                set_merge_ready_label(monitor, pr, False, outputs, "merge conflict/dirty state")
                for issue in autobuild_linked:
                    mark_rework(monitor, issue, label_issues.get(issue, {}), pr, "a merge conflict", pr.get("url") or "", dirty_detail, mstate, outputs)
                continue

            if codex["feedback"]:
                set_merge_ready_label(monitor, pr, False, outputs, "current-head Codex feedback")
                first = codex["feedback"][0]
                detail_url = first.get("url") or pr.get("url") or ""
                for issue in autobuild_linked:
                    mark_rework(monitor, issue, label_issues.get(issue, {}), pr, "current-head Codex feedback", detail_url, f"Current-head Codex feedback: {detail_url}", mstate, outputs)
                continue

            if codex["ready"]:
                set_merge_ready_label(monitor, pr, True, outputs, "clean with current-head Codex ready signal")
                if autobuild_linked:
                    merge_pr(monitor, pr, codex["ready"], mstate, outputs)
            else:
                set_merge_ready_label(monitor, pr, False, outputs, "waiting for current-head Codex ready signal")
        except Exception as exc:
            outputs.append(f"⚠️ {monitor.name}: monitor error on PR #{n}: {exc}")
            log(f"{monitor.name}: error on PR #{n}: {exc}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Monitor GitHub PRs linked to autobuild Linear issues and nudge on Codex feedback/conflicts.")
    parser.add_argument("--config", default=str(CONFIG_PATH), help="Path to JSON config (default: ~/.hermes/pr-nudge-monitors.json)")
    parser.add_argument("--list-config", action="store_true", help="Print configured monitor names/repos and exit")
    args = parser.parse_args(argv)

    monitors = load_config(Path(args.config).expanduser())
    if args.list_config:
        print(json.dumps([m.__dict__ | {"repo_dir": str(m.repo_dir) if m.repo_dir else None} for m in monitors], indent=2, default=str))
        return 0

    state = load_state()
    outputs: list[str] = []
    for monitor in monitors:
        try:
            process_monitor(monitor, state, outputs)
        except Exception as exc:
            outputs.append(f"⚠️ {monitor.name}: monitor failed: {exc}")
            log(f"{monitor.name}: monitor failed: {exc}")
    save_state(state)
    if outputs:
        print("\n".join(outputs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
