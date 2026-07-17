#!/usr/bin/env python3
"""Quietly recover Herdr agents stopped by an unrecovered provider error.

The supervisor deliberately requires converging evidence across Herdr metadata,
the persisted agent transcript, process state, goal-plugin state, and repeated
observations.  It emits output only after an eligible one-shot intervention.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any


DEFAULT_STATE = Path.home() / ".local/state/herdr-session-supervisor/state.json"
DEFAULT_LOG = Path.home() / ".local/state/herdr-session-supervisor/monitor.log"
QUIET_PROCESSES = {"pi", "node", "exec_bridge", "claude", "codex", "opencode", "omp"}
PRIORITY_PATTERNS = (
    ("compaction", re.compile(r"compact|context (?:window|length|limit)|too many tokens", re.I)),
    (
        "provider",
        re.compile(
            r"provider|model|api error|rate.?limit|overloaded|service unavailable|"
            r"internal server error|connection (?:reset|closed)|timeout|authentication",
            re.I,
        ),
    ),
)


def run_json(argv: list[str], timeout: float = 12) -> dict[str, Any] | None:
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)
        if result.returncode != 0:
            return None
        value = json.loads(result.stdout)
        return value if isinstance(value, dict) else None
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None


def tail_jsonl(path: Path, limit_bytes: int = 4_000_000) -> list[dict[str, Any]]:
    try:
        with path.open("rb") as handle:
            size = handle.seek(0, os.SEEK_END)
            handle.seek(max(0, size - limit_bytes))
            data = handle.read().decode("utf-8", errors="replace")
        if size > limit_bytes:
            data = data.split("\n", 1)[-1]
        entries = []
        for line in data.splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                entries.append(item)
        return entries
    except OSError:
        return []


def text_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    return "\n".join(
        str(part.get("text", ""))
        for part in content
        if isinstance(part, dict) and part.get("type") in {"text", "output_text"}
    )


def transcript_evidence(path: Path) -> dict[str, Any]:
    entries = tail_jsonl(path)
    latest_goal: dict[str, Any] | None = None
    conversation: list[tuple[int, str, dict[str, Any]]] = []
    managed_processes: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(entries):
        if entry.get("type") == "custom" and entry.get("customType") in {
            "goal-state",
            "goals-state",
        }:
            data = entry.get("data")
            latest_goal = data if isinstance(data, dict) else None
        message = entry.get("message")
        if entry.get("type") == "message" and isinstance(message, dict):
            if message.get("role") == "toolResult" and message.get("toolName") == "process":
                details = message.get("details")
                if isinstance(details, dict):
                    process = details.get("process")
                    if isinstance(process, dict) and process.get("id"):
                        managed_processes[str(process["id"])] = process
                    processes = details.get("processes")
                    if isinstance(processes, list):
                        for process in processes:
                            if isinstance(process, dict) and process.get("id"):
                                managed_processes[str(process["id"])] = process
                    output = details.get("output")
                    message_text = str(details.get("message") or "")
                    match = re.search(r"\((proc_[^)]+)\) \[([^]]+)\]", message_text)
                    if isinstance(output, dict) and match:
                        previous = managed_processes.get(match.group(1), {})
                        managed_processes[match.group(1)] = {
                            **previous,
                            "id": match.group(1),
                            "status": output.get("status") or match.group(2),
                        }
            role = message.get("role")
            if role in {"user", "assistant"}:
                conversation.append((index, str(role), message))

    goal = latest_goal.get("goal") if latest_goal else None
    goal_status = goal.get("status") if isinstance(goal, dict) else None
    goal_controlled = bool(goal_status and goal_status != "complete")
    active_managed_processes = []
    for process in managed_processes.values():
        if process.get("status") != "running":
            continue
        pid = process.get("pid")
        try:
            if not isinstance(pid, int):
                continue
            os.kill(pid, 0)
        except (OSError, TypeError, ValueError):
            continue
        active_managed_processes.append(
            {"id": process.get("id"), "pid": pid, "name": process.get("name")}
        )
    if not conversation:
        return {
            "error": None,
            "goal_controlled": goal_controlled,
            "goal_status": goal_status,
            "active_managed_processes": active_managed_processes,
        }

    _, last_role, last_message = conversation[-1]
    error = None
    if last_role == "assistant" and last_message.get("stopReason") == "error":
        error_text = str(last_message.get("errorMessage") or text_content(last_message.get("content")))
        if error_text.strip():
            kind = "other"
            for candidate_kind, pattern in PRIORITY_PATTERNS:
                if pattern.search(error_text):
                    kind = candidate_kind
                    break
            fingerprint = hashlib.sha256(error_text.strip().encode()).hexdigest()[:20]
            error = {"text": error_text.strip(), "kind": kind, "fingerprint": fingerprint}
    return {
        "error": error,
        "goal_controlled": goal_controlled,
        "goal_status": goal_status,
        "last_role": last_role,
        "active_managed_processes": active_managed_processes,
    }


def process_evidence(session: str, pane_id: str) -> dict[str, Any]:
    payload = run_json(
        ["herdr", "--session", session, "pane", "process-info", "--pane", pane_id]
    )
    info = (((payload or {}).get("result") or {}).get("process_info") or {})
    processes = info.get("foreground_processes") or []
    meaningful = []
    agent_roots: set[int] = set()
    for process in processes:
        if not isinstance(process, dict):
            continue
        name = str(process.get("name") or process.get("argv0") or "")
        argv0 = Path(str(process.get("argv0") or name)).name
        if argv0 in {"pi", "claude", "codex", "opencode", "omp"} and isinstance(
            process.get("pid"), int
        ):
            agent_roots.add(process["pid"])
        if name in QUIET_PROCESSES or argv0 in QUIET_PROCESSES:
            continue
        meaningful.append({"pid": process.get("pid"), "name": name, "argv0": argv0})
    if agent_roots:
        try:
            result = subprocess.run(
                ["ps", "-axo", "pid=,ppid=,state=,comm="],
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
            rows: dict[int, tuple[int, str, str]] = {}
            for line in result.stdout.splitlines():
                fields = line.strip().split(None, 3)
                if len(fields) != 4:
                    continue
                try:
                    pid, ppid = int(fields[0]), int(fields[1])
                except ValueError:
                    continue
                rows[pid] = (ppid, fields[2], Path(fields[3]).name)
            descendants = set(agent_roots)
            changed = True
            while changed:
                changed = False
                for pid, (ppid, _state, _name) in rows.items():
                    if ppid in descendants and pid not in descendants:
                        descendants.add(pid)
                        changed = True
            for pid in sorted(descendants - agent_roots):
                ppid, state, name = rows[pid]
                if name in QUIET_PROCESSES or state.startswith("Z"):
                    continue
                meaningful.append({"pid": pid, "ppid": ppid, "name": name, "state": state})
        except (OSError, subprocess.TimeoutExpired):
            pass
    return {"background_active": bool(meaningful), "meaningful": meaningful, "raw": info}


def load_state(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def diagnostic(log_path: Path, message: str) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a") as handle:
        handle.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S%z')} {message}\n")


def collect_agents() -> list[tuple[str, dict[str, Any]]]:
    sessions_payload = run_json(["herdr", "session", "list", "--json"])
    sessions = (sessions_payload or {}).get("sessions") or []
    agents: list[tuple[str, dict[str, Any]]] = []
    for item in sessions:
        if not isinstance(item, dict) or not item.get("running") or not item.get("name"):
            continue
        session = str(item["name"])
        snapshot_payload = run_json(["herdr", "--session", session, "api", "snapshot"])
        snapshot = (((snapshot_payload or {}).get("result") or {}).get("snapshot") or {})
        for agent in snapshot.get("agents") or []:
            if isinstance(agent, dict):
                agents.append((session, agent))
    return agents


def infer_pi_transcript(cwd: str) -> Path | None:
    """Resolve Pi's cwd-bucket only when it has one unambiguous newest transcript."""
    if not cwd.startswith("/"):
        return None
    bucket_name = "--" + cwd.strip("/").replace("/", "-") + "--"
    bucket = Path.home() / ".pi/agent/sessions" / bucket_name
    try:
        candidates = sorted(bucket.glob("*.jsonl"), key=lambda path: path.stat().st_mtime, reverse=True)
    except OSError:
        return None
    return candidates[0] if candidates else None


def inspect_once(
    state: dict[str, Any],
    *,
    now: float,
    grace_seconds: int,
    required_observations: int,
    dry_run: bool,
    log_path: Path,
) -> list[dict[str, Any]]:
    records = state.setdefault("records", {})
    seen: set[str] = set()
    alerts: list[dict[str, Any]] = []
    live_agents = collect_agents()
    cwd_counts: dict[str, int] = {}
    for _session, agent in live_agents:
        cwd = str(agent.get("cwd") or "")
        cwd_counts[cwd] = cwd_counts.get(cwd, 0) + 1
    for session, agent in live_agents:
        pane_id = str(agent.get("pane_id") or "")
        status = str(agent.get("agent_status") or "unknown")
        agent_name = str(agent.get("agent") or "unknown")
        if not pane_id:
            continue
        key = f"{session}:{pane_id}"
        seen.add(key)
        record = records.setdefault(key, {})

        session_meta = agent.get("agent_session")
        transcript_path = None
        if isinstance(session_meta, dict) and session_meta.get("kind") == "path":
            transcript_path = Path(str(session_meta.get("value")))
        elif agent_name == "pi":
            cwd = str(agent.get("cwd") or "")
            if cwd_counts.get(cwd) == 1:
                transcript_path = infer_pi_transcript(cwd)
        evidence = transcript_evidence(transcript_path) if transcript_path else {
            "error": None,
            "goal_controlled": False,
            "goal_status": None,
            "active_managed_processes": [],
        }
        processes = process_evidence(session, pane_id)
        background_active = bool(
            processes["background_active"] or evidence.get("active_managed_processes")
        )
        error = evidence.get("error")

        eligible_surface = (
            status in {"idle", "done"}
            and error is not None
            and not evidence.get("goal_controlled")
            and not background_active
        )
        if not eligible_surface:
            record.update(
                {
                    "last_seen": now,
                    "status": status,
                    "reason": (
                        "goal-controlled" if evidence.get("goal_controlled") else
                        "background-active" if background_active else
                        "not-stopped-on-error"
                    ),
                    "candidate": None,
                }
            )
            continue

        fingerprint = f"{transcript_path}:{error['fingerprint']}"
        candidate = record.get("candidate")
        if not isinstance(candidate, dict) or candidate.get("fingerprint") != fingerprint:
            candidate = {
                "fingerprint": fingerprint,
                "first_seen": now,
                "observations": 1,
                "nudged": False,
                "kind": error["kind"],
            }
        else:
            candidate["observations"] = int(candidate.get("observations", 0)) + 1
        record.update({"last_seen": now, "status": status, "reason": "candidate", "candidate": candidate})

        matured = (
            now - float(candidate["first_seen"]) >= grace_seconds
            and int(candidate["observations"]) >= required_observations
        )
        if not matured or candidate.get("nudged"):
            continue

        sent = dry_run
        if not dry_run:
            result = subprocess.run(
                ["herdr", "--session", session, "pane", "run", pane_id, "continue"],
                capture_output=True,
                text=True,
                timeout=12,
                check=False,
            )
            sent = result.returncode == 0
            if not sent:
                diagnostic(log_path, f"send failed session={session} pane={pane_id}: {result.stderr.strip()}")
        if sent:
            candidate["nudged"] = True
            candidate["nudged_at"] = now
            alerts.append(
                {
                    "session": session,
                    "pane": pane_id,
                    "agent": agent_name,
                    "kind": error["kind"],
                    "error": error["text"][:300].replace("\n", " "),
                    "dry_run": dry_run,
                }
            )

    for key in list(records):
        if key not in seen and now - float(records[key].get("last_seen", 0)) > 86400:
            del records[key]
    state["last_scan"] = now
    return alerts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=60)
    parser.add_argument("--grace-seconds", type=int, default=120)
    parser.add_argument("--observations", type=int, default=3)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    state = load_state(args.state)
    while True:
        try:
            alerts = inspect_once(
                state,
                now=time.time(),
                grace_seconds=args.grace_seconds,
                required_observations=args.observations,
                dry_run=args.dry_run,
                log_path=args.log,
            )
            save_state(args.state, state)
            for alert in alerts:
                print("HERDR_SESSION_ATTENTION " + json.dumps(alert, sort_keys=True), flush=True)
        except Exception as error:  # keep the monitor alive; diagnostics do not wake Pi
            diagnostic(args.log, f"scan error: {type(error).__name__}: {error}")
        if args.once:
            return 0
        time.sleep(max(1, args.interval))


if __name__ == "__main__":
    sys.exit(main())
