#!/usr/bin/env python3
"""Quiet watchdog for OpenCode Linear build NOD-533.

Prints only when the run reaches a terminal/blocking state or appears stalled.
State is kept locally so repeated cron ticks stay quiet after reporting.
"""
from __future__ import annotations

import glob
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = os.environ.get("OPENCODE_URL", "http://127.0.0.1:63333")
REPO = os.environ.get("OPENCODE_DIRECTORY", "/Users/anichols/code/heddle")
ISSUE = "NOD-533"
WORKSPACE_ID = "wrk_nod_533"
SESSION_ID = "ses_1f82a5e48fferVb5vsGQKjIwcL"
SUBSESSION_ID = "ses_1f82a1690ffe3qYyrLUaisy3bp"
STATE_PATH = Path("/Users/anichols/.hermes/profiles/nerd/cron/state/nod_533_monitor.json")
ORCH = "/Users/anichols/.config/opencode/scripts/linear_build_orchestrator.py"

BLOCKING_VERDICTS = {
    "VALIDATION_FAILED",
    "PM_NOT_ACCEPTABLE",
    "CODE_REVIEW_BLOCKED",
}
TERMINAL_STAGES = {"PR_CREATED", "COMPLETE"}


def load_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text())
    except Exception:
        return {}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True))


def get_json(path: str):
    with urllib.request.urlopen(BASE + path, timeout=15) as r:
        return json.load(r)


def find_workspace() -> dict | None:
    q = urllib.parse.quote(REPO, safe="")
    try:
        rows = get_json(f"/experimental/workspace?directory={q}")
    except Exception:
        return None
    for row in rows:
        if row.get("id") == WORKSPACE_ID:
            return row
    return None


def session_status() -> dict:
    q = urllib.parse.quote(REPO, safe="")
    try:
        return get_json(f"/session/status?directory={q}")
    except Exception as e:
        return {"error": str(e)}


def latest_ledger(workspace_dir: str) -> str | None:
    paths = glob.glob(str(Path(workspace_dir) / "thoughts" / "runs" / "nod-533*.md"))
    if not paths:
        paths = glob.glob(str(Path(workspace_dir) / "thoughts" / "runs" / "*.md"))
    if not paths:
        return None
    return max(paths, key=lambda p: os.path.getmtime(p))


def ledger_status(path: str) -> dict | None:
    env = dict(os.environ)
    env["HOME"] = "/Users/anichols"
    proc = subprocess.run(
        ["python3", ORCH, "status", "--ledger", path],
        text=True,
        capture_output=True,
        timeout=30,
        env=env,
    )
    if proc.returncode != 0:
        return {"error": (proc.stderr or proc.stdout).strip()}
    return json.loads(proc.stdout)


def latest_stage_update(state: dict) -> str | None:
    updates = []
    for stage, info in state.get("stages", {}).items():
        if info.get("updatedAt"):
            updates.append(info["updatedAt"])
    return max(updates) if updates else None


def summarize(state: dict, ledger: str, workspace: dict, status: dict, reason: str) -> str:
    stage = state.get("currentStage")
    stages = state.get("stages", {})
    verdict = stages.get(stage, {}).get("verdict") if stage else None
    blockers = state.get("blockers") or []
    pr_url = None
    for key in ("prUrl", "pullRequestUrl", "url"):
        if state.get(key):
            pr_url = state[key]
            break
    lines = [
        f"Linear build {ISSUE}: {reason}",
        f"Workspace: {workspace.get('id')} ({workspace.get('directory')})",
        f"Session: {SESSION_ID}; worker: {SUBSESSION_ID}",
        f"Current stage: {stage}",
        f"Verdict: {verdict}",
        f"Ledger: {ledger}",
    ]
    if pr_url:
        lines.append(f"PR: {pr_url}")
    if blockers:
        lines.append("Blockers: " + json.dumps(blockers, ensure_ascii=False)[:1500])
    lines.append("OpenCode session status: " + json.dumps(status, sort_keys=True)[:1000])
    return "\n".join(lines)


def main() -> int:
    old = load_state()
    now = int(time.time())
    workspace = find_workspace()
    status = session_status()
    if not workspace:
        if now - old.get("created", now) > 1800 and old.get("reported") != "no_workspace":
            old.update({"created": old.get("created", now), "reported": "no_workspace"})
            save_state(old)
            print(f"Linear build {ISSUE}: HERMES_WATCHDOG_STALLED — workspace {WORKSPACE_ID} not found. Session status: {json.dumps(status)}")
        else:
            old.setdefault("created", now)
            save_state(old)
        return 0

    ledger = latest_ledger(workspace["directory"])
    if not ledger:
        old.setdefault("created", now)
        save_state(old)
        return 0

    state = ledger_status(ledger)
    if not state or state.get("error"):
        return 0

    stage = state.get("currentStage")
    stages = state.get("stages", {})
    verdict = stages.get(stage, {}).get("verdict") if stage else None
    blockers = state.get("blockers") or []
    latest = latest_stage_update(state)
    sig = {"stage": stage, "verdict": verdict, "blockers": blockers, "ledger": ledger, "latest": latest}
    old["last_seen"] = now
    old["last_sig"] = sig

    reason = None
    if stage in TERMINAL_STAGES and verdict in {"PASS", "PR_CREATED", "COMPLETE"}:
        reason = "terminal success"
    elif isinstance(verdict, str) and (verdict.startswith("BLOCKED_") or verdict in BLOCKING_VERDICTS):
        reason = "blocked"
    elif blockers:
        reason = "blocked"
    else:
        # Stalled: both tracked sessions idle and no stage update for >45m.
        active = status.get(SESSION_ID, {}).get("type") == "busy" or status.get(SUBSESSION_ID, {}).get("type") == "busy"
        last_change = old.get("last_change_ts", now)
        if old.get("last_stage") != stage or old.get("last_verdict") != verdict or old.get("last_latest") != latest:
            last_change = now
        old.update({"last_change_ts": last_change, "last_stage": stage, "last_verdict": verdict, "last_latest": latest})
        if not active and now - last_change > 2700:
            reason = "HERMES_WATCHDOG_STALLED"

    report_key = json.dumps({"reason": reason, "sig": sig}, sort_keys=True)
    if reason and old.get("reported_key") != report_key:
        old["reported_key"] = report_key
        save_state(old)
        print(summarize(state, ledger, workspace, status, reason))
        return 0

    save_state(old)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
