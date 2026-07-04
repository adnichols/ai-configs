#!/usr/bin/env python3
"""Durable listener/dispatcher for one owned Good Morning Doct plan document.

Loops until the document is archived/removed from the GM ownership registry. Claims
one routed Doct plan work item at a time via `doct-agent plans agent next --wait`,
then dispatches a detached Hermes CLI worker to process/reply/ack/resolve the exact
claim. Ordinary conversation comments are intentionally not routed work.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import signal
import subprocess
import sys
import time
from typing import Any

BASE_URL = "https://doct.nodaste.com"
STATE_DIR = pathlib.Path.home() / ".hermes" / "state" / "gm-plan-maintainer"
REGISTRY = STATE_DIR / "active-plans.json"
RUN_DIR = STATE_DIR / "runs"
LOG_DIR = STATE_DIR / "logs"
PID_DIR = STATE_DIR / "pids"
WORKER_DIR = STATE_DIR / "workers"
OBSIDIAN = pathlib.Path.home() / "Obsidian"

MAX_WORKERS = int(os.environ.get("GM_PLAN_COMMENT_MAX_WORKERS", "3"))
WORKER_TIMEOUT_SECONDS = int(os.environ.get("GM_PLAN_COMMENT_WORKER_TIMEOUT_SECONDS", "2700"))


def now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def log(document_id: str, msg: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with (LOG_DIR / f"{document_id}.log").open("a", encoding="utf-8") as f:
        f.write(f"{now()} {msg}\n")


def run(cmd: list[str], *, cwd: pathlib.Path = OBSIDIAN, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, timeout=timeout)


def load_registry() -> dict[str, Any]:
    if not REGISTRY.exists():
        return {"active_plans": []}
    try:
        return json.loads(REGISTRY.read_text(encoding="utf-8"))
    except Exception:
        return {"active_plans": []}


def entry_document_id(item: dict[str, Any]) -> str:
    return str(item.get("document_id") or item.get("plan_id") or "")


def registry_entry(document_id: str) -> dict[str, Any] | None:
    reg = load_registry()
    for item in reg.get("active_plans", []):
        if entry_document_id(item) == document_id and item.get("status", "active") == "active":
            return item
    return None


def mark_archived(document_id: str) -> None:
    reg = load_registry()
    changed = False
    for item in reg.get("active_plans", []):
        if entry_document_id(item) == document_id and item.get("status") != "archived":
            item["status"] = "archived"
            item["archived_at"] = now()
            changed = True
    if changed:
        tmp = REGISTRY.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(reg, indent=2) + "\n", encoding="utf-8")
        tmp.replace(REGISTRY)


def document_lifecycle(document_id: str) -> str:
    cp = run([
        "doct-agent", "plans", "show",
        "--base-url", BASE_URL,
        "--id", document_id,
        "--json",
    ], timeout=30)
    if cp.returncode != 0:
        log(document_id, f"show failed rc={cp.returncode}: {cp.stderr.strip() or cp.stdout.strip()}")
        return "unknown"
    try:
        data = json.loads(cp.stdout)
        plan = data.get("plan") if isinstance(data.get("plan"), dict) else {}
        doc = data.get("document") if isinstance(data.get("document"), dict) else {}
        return str(plan.get("lifecycleState") or doc.get("status") or data.get("lifecycleState") or "active")
    except Exception as exc:
        log(document_id, f"show json parse failed: {exc}")
        return "active"


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except Exception:
        return False


def worker_record_path(document_id: str, thread_id: str) -> pathlib.Path:
    safe_thread = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in thread_id)
    return WORKER_DIR / f"{document_id}_{safe_thread}.json"


def load_worker_records(document_id: str) -> list[dict[str, Any]]:
    WORKER_DIR.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for path in WORKER_DIR.glob(f"{document_id}_*.json"):
        try:
            rec = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        rec["record_path"] = str(path)
        records.append(rec)
    return records


def cleanup_dead_worker_records(document_id: str) -> None:
    for rec in load_worker_records(document_id):
        pid = int(rec.get("pid") or 0)
        if not pid or not pid_alive(pid):
            path = pathlib.Path(str(rec.get("record_path")))
            try:
                path.unlink()
            except Exception:
                pass


def active_external_workers(document_id: str) -> list[dict[str, Any]]:
    cleanup_dead_worker_records(document_id)
    active = []
    for rec in load_worker_records(document_id):
        pid = int(rec.get("pid") or 0)
        if pid and pid_alive(pid):
            active.append(rec)
    return active


def claim_parts(claim: dict[str, Any]) -> tuple[str, str]:
    thread = claim.get("thread") if isinstance(claim.get("thread"), dict) else {}
    item = claim.get("item") if isinstance(claim.get("item"), dict) else {}
    nested_claim = claim.get("claim") if isinstance(claim.get("claim"), dict) else {}
    thread_id = str(claim.get("threadId") or claim.get("thread_id") or thread.get("id") or item.get("threadId") or item.get("id") or "unknown-thread")
    claim_id = str(claim.get("claimId") or claim.get("claim_id") or nested_claim.get("id") or item.get("claimId") or "")
    return thread_id, claim_id


def active_worker_for_thread(document_id: str, thread_id: str) -> dict[str, Any] | None:
    for rec in active_external_workers(document_id):
        if rec.get("thread_id") == thread_id:
            return rec
    return None


def release_claim(document_id: str, workspace_id: str, thread_id: str, claim_id: str, reason: str) -> None:
    if not claim_id or not thread_id:
        return
    cp = run([
        "doct-agent", "plans", "release",
        "--base-url", BASE_URL,
        "--workspace-id", workspace_id,
        "--thread-id", thread_id,
        "--claim-id", claim_id,
        "--reason", reason,
        "--json",
    ], timeout=30)
    if cp.returncode == 0:
        log(document_id, f"released duplicate claim thread={thread_id} claim={claim_id} reason={reason}")
    else:
        log(document_id, f"release failed thread={thread_id} claim={claim_id} rc={cp.returncode}: {(cp.stderr or cp.stdout).strip()[:500]}")


def start_worker(document_id: str, workspace_id: str, claim: dict[str, Any]) -> subprocess.Popen[Any] | None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    WORKER_DIR.mkdir(parents=True, exist_ok=True)
    thread_id, claim_id = claim_parts(claim)

    existing = active_worker_for_thread(document_id, thread_id)
    if existing:
        release_claim(document_id, workspace_id, thread_id, claim_id, f"worker already active pid={existing.get('pid')}")
        return None

    run_id = f"{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}_{thread_id}"
    claim_path = RUN_DIR / f"{document_id}_{run_id}.json"
    claim_path.write_text(json.dumps(claim, indent=2) + "\n", encoding="utf-8")
    entry = registry_entry(document_id) or {}
    source_path = entry.get("source_path") or ""
    review_url = entry.get("review_url") or f"{BASE_URL}/docs/{document_id}"

    prompt = f"""
Process one claimed Doct plan comment/action for Aaron's Good Morning briefing.

Load/follow skills: doct-document-ops and aaron-good-morning. Work from /Users/anichols/Obsidian.

Doct plan:
- base_url: {BASE_URL}
- document_id: {document_id}
- workspace_id: {workspace_id}
- review_url: {review_url}
- source_path: {source_path}
- claim_json: {claim_path}
- thread_id: {thread_id}
- claim_id: {claim_id}

Required workflow:
1. Read the claim JSON and the full HTML source file.
2. Use the annotation context and reviewer note to make the smallest correct update to the Good Morning HTML artifact. If the comment asks for future formatting behavior, update both today's HTML as applicable and the durable `aaron-good-morning` skill if needed so future GM runs follow it.
3. If the comment requests investigation (for example coding-session detail), use grounded local evidence: files, session_search, git logs/status, or delegated subagents if appropriate. Do not guess.
4. Save changed files.
5. Push any changed HTML back to Doct with `doct-agent plans update --base-url {BASE_URL} --id {document_id} --workspace-id {workspace_id} --file <source_path> --source-format html --expected-version <latest version when available> --json`.
6. Reply when useful, then ack and resolve the exact Doct thread using the provided claim id:
   doct-agent plans reply --base-url {BASE_URL} --document-id {document_id} --workspace-id {workspace_id} --thread-id {thread_id} --body "Updated the report." --json
   doct-agent plans ack --base-url {BASE_URL} --workspace-id {workspace_id} --thread-id {thread_id} --claim-id {claim_id} --summary "..." --json
   doct-agent plans resolve --base-url {BASE_URL} --workspace-id {workspace_id} --thread-id {thread_id} --claim-id {claim_id} --summary "..." --json
7. If you cannot safely complete it, release the claim with `doct-agent plans release ... --reason "..." --json` and leave a concise local final response explaining the blocker. Do not message Aaron directly; this listener is local/durable.
""".strip()

    out_path = RUN_DIR / f"{document_id}_{run_id}.hermes.log"
    out = out_path.open("ab", buffering=0)
    out.write((
        f"# START {now()} document={document_id} thread={thread_id} claim={claim_id}\n"
        f"# claim_json={claim_path}\n"
        "# STDOUT/STDERR\n"
    ).encode("utf-8"))

    proc = subprocess.Popen(
        [
            "hermes", "chat", "-Q",
            "--toolsets", "terminal,file,skills,delegation,session_search",
            "--skills", "doct-document-ops,aaron-good-morning",
            "-q", prompt,
        ],
        cwd=str(OBSIDIAN),
        stdout=out,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        close_fds=True,
    )
    rec = {
        "pid": proc.pid,
        "document_id": document_id,
        "workspace_id": workspace_id,
        "thread_id": thread_id,
        "claim_id": claim_id,
        "run_id": run_id,
        "claim_path": str(claim_path),
        "log_path": str(out_path),
        "started_at": now(),
        "started_monotonic": time.monotonic(),
    }
    worker_record_path(document_id, thread_id).write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    log(document_id, f"dispatched worker pid={proc.pid} thread={thread_id} claim={claim_id} claim_path={claim_path} log={out_path}")
    out.close()
    return proc


def reap_local_workers(document_id: str, workers: dict[int, dict[str, Any]]) -> None:
    for pid, rec in list(workers.items()):
        proc: subprocess.Popen[Any] = rec["proc"]
        rc = proc.poll()
        age = time.monotonic() - float(rec.get("started_monotonic", time.monotonic()))
        if rc is None and age > WORKER_TIMEOUT_SECONDS:
            log(document_id, f"worker timeout; terminating pid={pid} thread={rec.get('thread_id')} age={int(age)}s")
            try:
                os.killpg(pid, signal.SIGTERM)
            except Exception:
                try:
                    proc.terminate()
                except Exception:
                    pass
            rec["started_monotonic"] = time.monotonic() - WORKER_TIMEOUT_SECONDS + 60
            continue
        if rc is not None:
            log(document_id, f"worker finished pid={pid} thread={rec.get('thread_id')} rc={rc} log={rec.get('log_path')}")
            path = worker_record_path(document_id, str(rec.get("thread_id") or ""))
            try:
                path.unlink()
            except Exception:
                pass
            workers.pop(pid, None)


def main() -> int:
    if len(sys.argv) not in {2, 3}:
        print("usage: gm_plan_comment_listener.py <document_id> [workspace_id]", file=sys.stderr)
        return 2
    document_id = sys.argv[1]
    entry = registry_entry(document_id) or {}
    workspace_id = sys.argv[2] if len(sys.argv) == 3 else str(entry.get("workspace_id") or "")
    if not workspace_id:
        print(f"missing workspace_id for document {document_id}", file=sys.stderr)
        return 2
    PID_DIR.mkdir(parents=True, exist_ok=True)
    pid_file = PID_DIR / f"{document_id}.pid"
    pid_file.write_text(str(os.getpid()), encoding="utf-8")
    workers: dict[int, dict[str, Any]] = {}

    def _term(_signum, _frame):
        log(document_id, "received termination signal; exiting dispatcher only, detached workers continue")
        try:
            pid_file.unlink(missing_ok=True)
        finally:
            raise SystemExit(0)

    signal.signal(signal.SIGTERM, _term)
    signal.signal(signal.SIGINT, _term)

    cleanup_dead_worker_records(document_id)
    log(document_id, f"Doct listener dispatcher started workspace={workspace_id} max_workers={MAX_WORKERS} worker_timeout={WORKER_TIMEOUT_SECONDS}s")
    try:
        while True:
            reap_local_workers(document_id, workers)
            cleanup_dead_worker_records(document_id)
            external_active = active_external_workers(document_id)
            active_count = len(workers) + len([r for r in external_active if int(r.get("pid") or 0) not in workers])

            if not registry_entry(document_id):
                log(document_id, "registry no longer owns active document; exiting")
                return 0
            lifecycle = document_lifecycle(document_id).lower()
            if lifecycle == "archived":
                mark_archived(document_id)
                log(document_id, "document archived; exiting")
                return 0

            if active_count >= MAX_WORKERS:
                log(document_id, f"worker limit reached active={active_count} max={MAX_WORKERS}; waiting before next claim")
                time.sleep(10)
                continue

            cp = run([
                "doct-agent", "plans", "agent", "next",
                "--base-url", BASE_URL,
                "--workspace-id", workspace_id,
                "--document-id", document_id,
                "--wait",
                "--timeout", "60",
                "--json",
            ], timeout=90)
            text = (cp.stdout or "").strip()
            if cp.returncode != 0:
                err = (cp.stderr or cp.stdout or "").strip()
                if "timed out waiting for a plan comment claim" in err.lower() or "timeout" in err.lower():
                    continue
                log(document_id, f"agent next failed rc={cp.returncode}: {err[:1000]}")
                time.sleep(10)
                continue
            if not text:
                continue
            try:
                data = json.loads(text)
            except Exception as exc:
                log(document_id, f"agent next json parse failed: {exc}; text={text[:1000]}")
                time.sleep(5)
                continue
            if data.get("status") in {"empty", "timeout"}:
                continue
            thread_id, claim_id = claim_parts(data)
            if thread_id != "unknown-thread" or claim_id:
                proc = start_worker(document_id, workspace_id, data)
                if proc is not None:
                    rec_path = worker_record_path(document_id, thread_id)
                    try:
                        rec = json.loads(rec_path.read_text(encoding="utf-8"))
                    except Exception:
                        rec = {"thread_id": thread_id, "pid": proc.pid, "started_monotonic": time.monotonic()}
                    rec["proc"] = proc
                    workers[proc.pid] = rec
            else:
                log(document_id, f"agent next returned unrecognized payload: {text[:1000]}")
    finally:
        try:
            if pid_file.exists() and pid_file.read_text(encoding="utf-8").strip() == str(os.getpid()):
                pid_file.unlink()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
