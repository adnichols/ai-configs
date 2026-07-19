#!/usr/bin/env python3
"""Durable Doct plan-comment listener for one document.

Waits for routed plan-review comments, dispatches a Hermes worker for each claim,
and exits successfully when the Doct document is archived. Intended for launchd
with KeepAlive.SuccessfulExit=false so crashes restart but archival stops it.
"""
from __future__ import annotations

import json
import os
import pathlib
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any

BASE_URL = "https://doct.nodaste.com"
DOCT_AGENT = "/opt/homebrew/bin/doct-agent"
HERMES = str(pathlib.Path.home() / ".local" / "bin" / "hermes")
STATE_ROOT = pathlib.Path.home() / ".hermes" / "state" / "doct-document-listeners"
WORKER_TIMEOUT_SECONDS = 45 * 60


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(cmd: list[str], timeout: int = 90) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)


def load_json_output(cp: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    if cp.returncode != 0:
        raise RuntimeError((cp.stderr or cp.stdout or "command failed").strip())
    return json.loads(cp.stdout or "{}")


def document_state(document_id: str) -> tuple[str, dict[str, Any]]:
    data = load_json_output(run([
        DOCT_AGENT, "documents", "get", "--base-url", BASE_URL,
        "--id", document_id, "--json",
    ], timeout=45))
    status = str(data.get("status") or "").lower()
    if data.get("archivedAt") or status == "archived":
        return "archived", data
    return "active", data


def claim_parts(claim: dict[str, Any]) -> tuple[str, str]:
    thread = claim.get("thread") if isinstance(claim.get("thread"), dict) else {}
    item = claim.get("item") if isinstance(claim.get("item"), dict) else {}
    nested = claim.get("claim") if isinstance(claim.get("claim"), dict) else {}
    thread_id = str(claim.get("threadId") or claim.get("thread_id") or thread.get("id") or item.get("threadId") or item.get("id") or "")
    claim_id = str(claim.get("claimId") or claim.get("claim_id") or nested.get("id") or item.get("claimId") or "")
    return thread_id, claim_id


def release(workspace_id: str, thread_id: str, claim_id: str, reason: str) -> None:
    if not thread_id or not claim_id:
        return
    run([
        DOCT_AGENT, "plans", "release", "--base-url", BASE_URL,
        "--workspace-id", workspace_id, "--thread-id", thread_id,
        "--claim-id", claim_id, "--reason", reason, "--json",
    ], timeout=45)


def process_claim(
    document_id: str,
    workspace_id: str,
    document_url: str,
    source_path: str,
    claim: dict[str, Any],
    run_dir: pathlib.Path,
) -> int:
    thread_id, claim_id = claim_parts(claim)
    if not thread_id or not claim_id:
        return 2
    claim_path = run_dir / f"claim-{int(time.time())}-{thread_id}.json"
    claim_path.write_text(json.dumps(claim, indent=2) + "\n", encoding="utf-8")
    log_path = run_dir / f"worker-{int(time.time())}-{thread_id}.log"
    prompt = f"""Process exactly one claimed Doct plan-review comment/action.

Load and follow the doct-document-ops skill. Do not create or manage cron jobs. Do not ask the user for clarification.

Document:
- URL: {document_url}
- Base URL: {BASE_URL}
- Workspace ID: {workspace_id}
- Document ID: {document_id}
- Canonical source path: {source_path or "not declared"}
- Claim JSON: {claim_path}
- Thread ID: {thread_id}
- Claim ID: {claim_id}

Required workflow:
1. Read the claim JSON and current plan using `doct-agent plans show --base-url {BASE_URL} --id {document_id} --json`.
2. Use the reviewer body and anchor context. Make the smallest correct change that addresses the comment. If the canonical source path above is declared, read and update that file first. Otherwise, if the claim or plan identifies a local source path, update that source first. Only fall back to temporary HTML when no canonical source can be identified. Do not invent repository facts.
3. Push changed HTML with `doct-agent plans update --base-url {BASE_URL} --id {document_id} --workspace-id {workspace_id} --file <file> --source-format html --allow-untemplated --expected-version <latest document.version> --json`. Re-read on version conflict and reconcile; use `--force` only when intentionally overwriting the just-read current source.
4. Add a visible reply, then ack and resolve this exact thread/claim. If it cannot be handled safely, release the claim with a concise reason.
5. Final output must be concise plain text; do not include raw HTML, CSS, diffs, or command transcripts.
"""
    cmd = [
        HERMES, "chat", "-Q", "--toolsets", "terminal,file,skills,session_search",
        "--skills", "doct-document-ops", "-q", prompt,
    ]
    with log_path.open("ab", buffering=0) as out:
        out.write(f"# {stamp()} thread={thread_id} claim={claim_id}\n".encode())
        try:
            cp = subprocess.run(cmd, stdout=out, stderr=subprocess.STDOUT, timeout=WORKER_TIMEOUT_SECONDS)
            return cp.returncode
        except subprocess.TimeoutExpired:
            release(workspace_id, thread_id, claim_id, "Hermes worker timed out before safe completion")
            return 124


def main() -> int:
    if len(sys.argv) not in {4, 5}:
        print("usage: doct_document_comment_listener.py <document_id> <workspace_id> <document_url> [source_path]", file=sys.stderr)
        return 2
    document_id, workspace_id, document_url = sys.argv[1:4]
    source_path = sys.argv[4] if len(sys.argv) == 5 else ""
    state_dir = STATE_ROOT / document_id
    run_dir = state_dir / "runs"
    state_dir.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(parents=True, exist_ok=True)
    state_path = state_dir / "state.json"
    stop = False

    def handle_stop(_signum, _frame):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGTERM, handle_stop)
    signal.signal(signal.SIGINT, handle_stop)

    while not stop:
        try:
            lifecycle, metadata = document_state(document_id)
            state_path.write_text(json.dumps({
                "document_id": document_id,
                "workspace_id": workspace_id,
                "document_url": document_url,
                "lifecycle": lifecycle,
                "document_status": metadata.get("status"),
                "archived_at": metadata.get("archivedAt"),
                "last_checked_at": stamp(),
                "pid": os.getpid(),
            }, indent=2) + "\n", encoding="utf-8")
            if lifecycle == "archived":
                return 0
        except Exception as exc:
            state_path.write_text(json.dumps({
                "document_id": document_id, "workspace_id": workspace_id,
                "document_url": document_url, "lifecycle": "unknown",
                "last_error": str(exc), "last_checked_at": stamp(), "pid": os.getpid(),
            }, indent=2) + "\n", encoding="utf-8")
            time.sleep(15)
            continue

        cp = run([
            DOCT_AGENT, "plans", "agent", "next", "--base-url", BASE_URL,
            "--workspace-id", workspace_id, "--document-id", document_id,
            "--wait", "--timeout", "60", "--json",
        ], timeout=90)
        if cp.returncode != 0:
            text = (cp.stderr or cp.stdout or "").lower()
            if "timeout" not in text and "timed out" not in text:
                time.sleep(10)
            continue
        try:
            claim = json.loads(cp.stdout or "{}")
        except json.JSONDecodeError:
            time.sleep(5)
            continue
        if claim.get("status") in {"empty", "timeout"}:
            continue
        thread_id, claim_id = claim_parts(claim)
        if not thread_id or not claim_id:
            continue
        rc = process_claim(document_id, workspace_id, document_url, source_path, claim, run_dir)
        with (state_dir / "worker-history.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps({"at": stamp(), "thread_id": thread_id, "claim_id": claim_id, "exit_code": rc}) + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
