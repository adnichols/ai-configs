#!/usr/bin/env python3
"""Durable listener/dispatcher for one owned Good Morning plan-review plan.

Loops until the plan is archived/removed from the GM ownership registry. Claims one
comment at a time via `plan-review agent next --wait`, then dispatches a detached
Hermes CLI worker to process/ack/resolve that exact claim. The dispatcher does
not wait for workers before claiming the next comment; this prevents one slow
comment from blocking the whole review queue.
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

BASE_URL = "http://mbp.braid-python.ts.net:4317"
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


def log(plan_id: str, msg: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with (LOG_DIR / f"{plan_id}.log").open("a", encoding="utf-8") as f:
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


def registry_entry(plan_id: str) -> dict[str, Any] | None:
    reg = load_registry()
    for item in reg.get("active_plans", []):
        if item.get("plan_id") == plan_id and item.get("status", "active") == "active":
            return item
    return None


def mark_archived(plan_id: str) -> None:
    reg = load_registry()
    changed = False
    for item in reg.get("active_plans", []):
        if item.get("plan_id") == plan_id and item.get("status") != "archived":
            item["status"] = "archived"
            item["archived_at"] = now()
            changed = True
    if changed:
        tmp = REGISTRY.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(reg, indent=2) + "\n", encoding="utf-8")
        tmp.replace(REGISTRY)


def plan_lifecycle(plan_id: str) -> str:
    cp = run(["plan-review", "show", plan_id, "--url", BASE_URL, "--json"], timeout=30)
    if cp.returncode != 0:
        log(plan_id, f"show failed rc={cp.returncode}: {cp.stderr.strip() or cp.stdout.strip()}")
        return "unknown"
    try:
        data = json.loads(cp.stdout)
        return str(data.get("plan", {}).get("lifecycleState") or "unknown")
    except Exception as exc:
        log(plan_id, f"show json parse failed: {exc}")
        return "unknown"


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


def worker_record_path(plan_id: str, comment_id: str) -> pathlib.Path:
    safe_comment = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in comment_id)
    return WORKER_DIR / f"{plan_id}_{safe_comment}.json"


def load_worker_records(plan_id: str) -> list[dict[str, Any]]:
    WORKER_DIR.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for path in WORKER_DIR.glob(f"{plan_id}_*.json"):
        try:
            rec = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        rec["record_path"] = str(path)
        records.append(rec)
    return records


def cleanup_dead_worker_records(plan_id: str) -> None:
    for rec in load_worker_records(plan_id):
        pid = int(rec.get("pid") or 0)
        if not pid or not pid_alive(pid):
            path = pathlib.Path(str(rec.get("record_path")))
            try:
                path.unlink()
            except Exception:
                pass


def active_external_workers(plan_id: str) -> list[dict[str, Any]]:
    cleanup_dead_worker_records(plan_id)
    active = []
    for rec in load_worker_records(plan_id):
        pid = int(rec.get("pid") or 0)
        if pid and pid_alive(pid):
            active.append(rec)
    return active


def active_worker_for_comment(plan_id: str, comment_id: str) -> dict[str, Any] | None:
    for rec in active_external_workers(plan_id):
        if rec.get("comment_id") == comment_id:
            return rec
    return None


def release_claim(plan_id: str, comment_id: str, claim_id: str, reason: str) -> None:
    if not claim_id:
        return
    cp = run([
        "plan-review", "release", comment_id,
        "--claim", claim_id,
        "--url", BASE_URL,
        "--json",
    ], timeout=30)
    if cp.returncode == 0:
        log(plan_id, f"released duplicate claim comment={comment_id} claim={claim_id} reason={reason}")
    else:
        log(plan_id, f"release failed comment={comment_id} claim={claim_id} rc={cp.returncode}: {(cp.stderr or cp.stdout).strip()[:500]}")


def start_worker(plan_id: str, claim: dict[str, Any]) -> subprocess.Popen[Any] | None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    WORKER_DIR.mkdir(parents=True, exist_ok=True)
    comment = claim.get("comment") or claim.get("item") or {}
    comment_id = claim.get("commentId") or comment.get("id") or "unknown-comment"
    claim_id = claim.get("claimId") or claim.get("claim", {}).get("id") or ""

    existing = active_worker_for_comment(plan_id, comment_id)
    if existing:
        release_claim(plan_id, comment_id, claim_id, f"worker already active pid={existing.get('pid')}")
        return None

    run_id = f"{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}_{comment_id}"
    claim_path = RUN_DIR / f"{plan_id}_{run_id}.json"
    claim_path.write_text(json.dumps(claim, indent=2) + "\n", encoding="utf-8")
    entry = registry_entry(plan_id) or {}
    source_path = entry.get("source_path") or ""
    review_url = entry.get("review_url") or f"{BASE_URL}/p/{plan_id}"

    prompt = f"""
Process one claimed plan-review comment for Aaron's Good Morning briefing.

Load/follow skills: doct-document-ops and aaron-good-morning. Work from /Users/anichols/Obsidian.

Plan:
- plan_id: {plan_id}
- review_url: {review_url}
- source_path: {source_path}
- claim_json: {claim_path}
- comment_id: {comment_id}
- claim_id: {claim_id}

Required workflow:
1. Read the claim JSON and the full HTML source file.
2. Use the annotation context and reviewer note to make the smallest correct update to the Good Morning HTML artifact. If the comment asks for future formatting behavior, update both today's HTML as applicable and the durable `aaron-good-morning` skill if needed so future GM runs follow it.
3. If the comment requests investigation (for example coding-session detail), use grounded local evidence: files, session_search, git logs/status, or delegated subagents if appropriate. Do not guess.
4. Save changed files.
5. Acknowledge and resolve the exact comment using plan-review with the provided claim id:
   plan-review ack {comment_id} --claim {claim_id} --summary "..." --changed-files <paths> --json --url {BASE_URL}
   plan-review resolve {comment_id} --note "Done" --summary "..." --changed-files <paths> --json --url {BASE_URL}
6. If you cannot safely complete it, release the claim if appropriate and leave a concise local final response explaining the blocker. Do not message Aaron directly; this listener is local/durable.
""".strip()

    out_path = RUN_DIR / f"{plan_id}_{run_id}.hermes.log"
    out = out_path.open("ab", buffering=0)
    out.write((
        f"# START {now()} plan={plan_id} comment={comment_id} claim={claim_id}\n"
        f"# claim_json={claim_path}\n"
        "# STDOUT/STDERR\n"
    ).encode("utf-8"))

    proc = subprocess.Popen(
        [
            "hermes", "chat", "-Q",
            "--toolsets", "terminal,file,skills,delegation,session_search",
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
        "plan_id": plan_id,
        "comment_id": comment_id,
        "claim_id": claim_id,
        "run_id": run_id,
        "claim_path": str(claim_path),
        "log_path": str(out_path),
        "started_at": now(),
        "started_monotonic": time.monotonic(),
    }
    worker_record_path(plan_id, comment_id).write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    log(plan_id, f"dispatched worker pid={proc.pid} comment={comment_id} claim={claim_id} claim_path={claim_path} log={out_path}")
    # Parent can close its copy; child keeps its FD.
    out.close()
    return proc


def reap_local_workers(plan_id: str, workers: dict[int, dict[str, Any]]) -> None:
    for pid, rec in list(workers.items()):
        proc: subprocess.Popen[Any] = rec["proc"]
        rc = proc.poll()
        age = time.monotonic() - float(rec.get("started_monotonic", time.monotonic()))
        if rc is None and age > WORKER_TIMEOUT_SECONDS:
            log(plan_id, f"worker timeout; terminating pid={pid} comment={rec.get('comment_id')} age={int(age)}s")
            try:
                os.killpg(pid, signal.SIGTERM)
            except Exception:
                try:
                    proc.terminate()
                except Exception:
                    pass
            # Keep tracking; next reap will observe exit.
            rec["started_monotonic"] = time.monotonic() - WORKER_TIMEOUT_SECONDS + 60
            continue
        if rc is not None:
            log(plan_id, f"worker finished pid={pid} comment={rec.get('comment_id')} rc={rc} log={rec.get('log_path')}")
            path = worker_record_path(plan_id, str(rec.get("comment_id") or ""))
            try:
                path.unlink()
            except Exception:
                pass
            workers.pop(pid, None)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: gm_plan_comment_listener.py <plan_id>", file=sys.stderr)
        return 2
    plan_id = sys.argv[1]
    PID_DIR.mkdir(parents=True, exist_ok=True)
    pid_file = PID_DIR / f"{plan_id}.pid"
    pid_file.write_text(str(os.getpid()), encoding="utf-8")
    workers: dict[int, dict[str, Any]] = {}

    def _term(_signum, _frame):
        log(plan_id, "received termination signal; exiting dispatcher only, detached workers continue")
        try:
            pid_file.unlink(missing_ok=True)
        finally:
            raise SystemExit(0)

    signal.signal(signal.SIGTERM, _term)
    signal.signal(signal.SIGINT, _term)

    cleanup_dead_worker_records(plan_id)
    log(plan_id, f"listener dispatcher started max_workers={MAX_WORKERS} worker_timeout={WORKER_TIMEOUT_SECONDS}s")
    try:
        while True:
            reap_local_workers(plan_id, workers)
            cleanup_dead_worker_records(plan_id)
            external_active = active_external_workers(plan_id)
            active_count = len(workers) + len([r for r in external_active if int(r.get("pid") or 0) not in workers])

            if not registry_entry(plan_id):
                log(plan_id, "registry no longer owns active plan; exiting")
                return 0
            lifecycle = plan_lifecycle(plan_id)
            if lifecycle == "archived":
                mark_archived(plan_id)
                log(plan_id, "plan archived; exiting")
                return 0

            if active_count >= MAX_WORKERS:
                log(plan_id, f"worker limit reached active={active_count} max={MAX_WORKERS}; waiting before next claim")
                time.sleep(10)
                continue

            cp = run([
                "plan-review", "agent", "next", plan_id,
                "--url", BASE_URL,
                "--wait", "--timeout", "60000", "--json",
            ], timeout=90)
            text = (cp.stdout or "").strip()
            if cp.returncode != 0:
                err = (cp.stderr or cp.stdout or "").strip()
                if "Archived plans cannot claim comments" in err:
                    mark_archived(plan_id)
                    log(plan_id, "plan archived according to agent next; exiting")
                    return 0
                log(plan_id, f"agent next failed rc={cp.returncode}: {err[:1000]}")
                time.sleep(10)
                continue
            if not text:
                continue
            try:
                data = json.loads(text)
            except Exception as exc:
                log(plan_id, f"agent next json parse failed: {exc}; text={text[:1000]}")
                time.sleep(5)
                continue
            if data.get("status") in {"empty", "timeout"}:
                continue
            if data.get("commentId") or data.get("comment") or data.get("item"):
                proc = start_worker(plan_id, data)
                if proc is not None:
                    comment = data.get("comment") or data.get("item") or {}
                    comment_id = data.get("commentId") or comment.get("id") or "unknown-comment"
                    run_id = f"{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}_{comment_id}"
                    rec_path = worker_record_path(plan_id, comment_id)
                    try:
                        rec = json.loads(rec_path.read_text(encoding="utf-8"))
                    except Exception:
                        rec = {"comment_id": comment_id, "pid": proc.pid, "started_monotonic": time.monotonic()}
                    rec["proc"] = proc
                    workers[proc.pid] = rec
            else:
                log(plan_id, f"agent next returned unrecognized payload: {text[:1000]}")
    finally:
        try:
            if pid_file.exists() and pid_file.read_text(encoding="utf-8").strip() == str(os.getpid()):
                pid_file.unlink()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
