#!/usr/bin/env python3
"""Quiet Doct plan comment dispatcher for Hermes Codex PR Watcher plan.

Cron/no_agent contract:
- print nothing when no pending comments/actions exist;
- when pending work exists, dispatch a Hermes one-shot worker that claims,
  applies, replies, acks, and resolves plan comments;
- keep a lock so one slow worker does not overlap with the next cron tick.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BASE_URL = "https://doct.nodaste.com"
WORKSPACE_ID = "6dbf05f0-fc4b-41f4-b927-5799ec7be0bb"
DOCUMENT_ID = "25cbf31c-6af9-4d5c-97a0-a155f8bba997"
PLAN_URL = "https://doct.nodaste.com/d/workspace_6dbf05f0-fc4b-41f4-b927-5799ec7be0bb/docs/25cbf31c-6af9-4d5c-97a0-a155f8bba997"
STATE_PATH = Path.home() / ".hermes" / "state" / "hermes-pr-codex-plan-comment-listener.json"
LOCK_PATH = Path.home() / ".hermes" / "state" / "hermes-pr-codex-plan-comment-listener.lock"
HERMES_PYTHON = Path.home() / ".hermes" / "hermes-agent" / "venv" / "bin" / "python"
LOCK_STALE_SECONDS = 30 * 60
WORKER_TIMEOUT_SECONDS = 20 * 60


def run_json(cmd: list[str], timeout: int = 45) -> dict:
    proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
    if proc.returncode != 0:
        print(
            "Doct plan comment listener error\n"
            f"Plan: {PLAN_URL}\n"
            f"Command failed: {' '.join(cmd[:4])} ...\n"
            f"stderr: {proc.stderr.strip()[:1200]}"
        )
        sys.exit(0)
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as exc:
        print(
            "Doct plan comment listener error\n"
            f"Plan: {PLAN_URL}\n"
            f"Could not parse JSON: {exc}\n"
            f"Output prefix: {(proc.stdout or '')[:1200]}"
        )
        sys.exit(0)


def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text())
        except Exception:
            return {}
    return {}


def save_state(**updates: object) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    state = load_state()
    state.update(
        {
            "last_checked_at": datetime.now(timezone.utc).isoformat(),
            "document_id": DOCUMENT_ID,
            "workspace_id": WORKSPACE_ID,
            "plan_url": PLAN_URL,
            **updates,
        }
    )
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def lock_is_active() -> bool:
    if not LOCK_PATH.exists():
        return False
    try:
        data = json.loads(LOCK_PATH.read_text())
        started = float(data.get("started_monotonic", 0))
    except Exception:
        started = 0
    age = time.monotonic() - started if started else LOCK_STALE_SECONDS + 1
    if age > LOCK_STALE_SECONDS:
        try:
            LOCK_PATH.unlink()
        except FileNotFoundError:
            pass
        return False
    save_state(lock_active=True, lock_age_seconds=round(age, 1))
    return True


def acquire_lock() -> bool:
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    if lock_is_active():
        return False
    payload = {
        "pid": os.getpid(),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "started_monotonic": time.monotonic(),
    }
    try:
        fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    with os.fdopen(fd, "w") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")
    return True


def release_lock() -> None:
    try:
        LOCK_PATH.unlink()
    except FileNotFoundError:
        pass


def pending_items() -> list[dict]:
    data = run_json(
        [
            "doct-agent",
            "plans",
            "queue",
            "list",
            "--base-url",
            BASE_URL,
            "--workspace-id",
            WORKSPACE_ID,
            "--document-id",
            DOCUMENT_ID,
            "--json",
        ]
    )
    items = data.get("items") or []
    actionable: list[dict] = []
    for item in items:
        queue_state = (item.get("queueState") or item.get("state") or "").lower()
        thread_state = (item.get("threadState") or "").lower()
        if queue_state in {"resolved", "closed", "done", "acknowledged"}:
            continue
        if thread_state in {"resolved", "closed"} or item.get("isResolved") is True:
            continue
        # Dispatch pending items. Already-claimed work is left alone until lease expiry/redelivery.
        if queue_state == "pending":
            actionable.append(item)
    return actionable


def build_worker_prompt(item_count: int) -> str:
    return f"""
You are a quiet Doct plan comment dispatcher running from a Hermes cron script. Do not create, update, remove, or schedule cron jobs. Do not ask the user for clarification; process the available Doct plan comments now.

Plan:
- Title: Hermes Codex PR Watcher Plan
- URL: {PLAN_URL}
- Base URL: {BASE_URL}
- Workspace ID: {WORKSPACE_ID}
- Document ID: {DOCUMENT_ID}
- Pending items seen by listener before dispatch: {item_count}

Required workflow:
1. Load/follow the html-plan-reviewer and doct-document-ops skills if available.
2. Use `doct-agent plans queue list --base-url {BASE_URL} --workspace-id {WORKSPACE_ID} --document-id {DOCUMENT_ID} --json` to inspect queue state.
3. While pending items exist for this exact document, claim one item with `doct-agent plans agent next --base-url {BASE_URL} --workspace-id {WORKSPACE_ID} --document-id {DOCUMENT_ID} --json`.
4. Read the claimed thread body, anchor, claim id, and current plan with `doct-agent plans show --base-url {BASE_URL} --id {DOCUMENT_ID} --json`.
5. Apply the smallest plan change that directly addresses the comment. If editing is needed, write the returned `sourceHtml` to a temp file, edit it, and update with `doct-agent plans update --base-url {BASE_URL} --id {DOCUMENT_ID} --workspace-id {WORKSPACE_ID} --file <tempfile> --source-format html --allow-untemplated --expected-version <document.version from the latest update/show when available> --json`. If the CLI response does not expose numeric version and you just read the latest source, use `--force` only for that intentional overwrite recovery and say so in the reply.
6. Add a visible reply, then ack and resolve the thread with the returned `threadId` and `claim.id`. If you cannot safely process a claim, release it with a clear reason instead of leaving it leased.
7. Finish with a concise summary: number processed, number released, and current pending queue count. Include blockers only if any remain.
""".strip()


def dispatch_worker(item_count: int) -> int:
    prompt = build_worker_prompt(item_count)
    cmd = [
        str(HERMES_PYTHON),
        "-m",
        "hermes_cli.main",
        "chat",
        "--quiet",
        "--toolsets",
        "terminal,file,skills",
        "--skills",
        "html-plan-reviewer,doct-document-ops",
        "--query",
        prompt,
    ]
    proc = subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        timeout=WORKER_TIMEOUT_SECONDS,
    )
    save_state(
        last_worker_exit_code=proc.returncode,
        last_worker_at=datetime.now(timezone.utc).isoformat(),
        last_worker_stdout_prefix=(proc.stdout or "")[:2000],
        last_worker_stderr_prefix=(proc.stderr or "")[:2000],
    )
    output = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    if proc.returncode != 0:
        print(
            "Doct plan comment dispatcher failed\n"
            f"Plan: {PLAN_URL}\n"
            f"Exit: {proc.returncode}\n"
            f"stderr: {err[:1200]}\n"
            f"stdout: {output[:1200]}"
        )
        return proc.returncode
    if output:
        print(output[-3500:])
    return 0


def main() -> None:
    items = pending_items()
    save_state(last_pending_count=len(items), lock_active=False)
    if not items:
        return
    if not acquire_lock():
        return
    try:
        dispatch_worker(len(items))
    finally:
        release_lock()


if __name__ == "__main__":
    main()
