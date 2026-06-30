from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

_CTX = None
_PLUGIN_DIR = Path(__file__).parent
EVENT_PREFIX = "EVENT:"
SPINNER_TOKENS = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
ACTIVE_WORKING_MARKERS = [
    "Working...",
    "Thinking...",
]
ACTIVE_PROGRESS_MARKERS = [
    "todo ",
    "Tool result",
    " read ",
    " edit ",
    " write ",
]
REVIEW_SUMMARY_MARKERS = ["Review Summary", "Plan status:"]
REVIEW_RECOMMENDATION_MARKERS = ["Recommendation:", "Ready to execute", "Revision required before execution"]
INTEGRATE_COMPLETE_MARKERS = [
    "Integration Complete",
    "plan is now clean",
    "No [REVIEW:",
    "no [review:",
]
PM_REVIEW_COMPLETE_MARKERS = ["PM Review Complete"]
EXECUTION_BLOCKED_MARKERS = ["execution blocked", " real blocker", " blocked"]


def _get_hermes_home() -> Path:
    try:
        from hermes_constants import get_hermes_home

        return get_hermes_home()
    except Exception:
        env_home = os.environ.get("HERMES_HOME")
        if env_home:
            return Path(env_home).expanduser()
        return Path.home() / ".hermes"


DEFAULT_TMP_DIR = _get_hermes_home() / "tmp"

PHASE_TO_EVENT = {
    "planning": "plan_ready",
    "review": "review_complete",
    "integrate": "integrate_complete",
    "pm_review_plan": "pm_review_complete",
    "pm_review_implementation": "pm_review_complete",
}

PHASE_ENUM = [
    "planning",
    "review",
    "integrate",
    "commit_reviewed_plan",
    "pm_review_plan",
    "execute",
    "validate",
    "pm_review_implementation",
]

PI_TMUX_WATCH_CONTROL_SCHEMA = {
    "name": "pi_tmux_watch_control",
    "description": (
        "Manage an event-driven watcher for a pi tmux target. Resolves the actual pi worker pane, "
        "tracks watcher state, writes status/log files, detects phase progress, and can auto-inject the "
        "next message in Hermes CLI mode."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["arm", "status", "stop", "list", "observe"],
                "description": "What to do: arm a watcher, inspect one watcher, stop one watcher, list all watchers, or observe once.",
            },
            "target": {
                "type": "string",
                "description": "tmux target. Prefer a pane id like '%73', but a window target is accepted and will be resolved to the pi worker pane.",
            },
            "watcher_id": {
                "type": "string",
                "description": "Existing watcher id for status or stop.",
            },
            "plan_file": {
                "type": "string",
                "description": "Optional plan file path used for plan-ready inference and reporting.",
            },
            "next_message": {
                "type": "string",
                "description": "Optional user message to inject when the watcher fires. Works only in Hermes CLI mode.",
            },
            "poll_seconds": {
                "type": "number",
                "description": "Polling interval in seconds for armed watchers. Default 5.",
            },
            "idle_streak": {
                "type": "integer",
                "description": "How many consecutive idle polls are required before idle_prompt can fire. Default 2.",
            },
            "timeout_seconds": {
                "type": "integer",
                "description": "Max seconds to wait before the watcher times out. Default 1800.",
            },
            "role": {
                "type": "string",
                "description": "Role for injected message, usually 'user'. Default user.",
            },
            "event": {
                "type": "string",
                "enum": ["idle_prompt", "review_complete", "pm_review_complete", "integrate_complete", "execution_blocked", "plan_ready"],
                "description": "Which event should trigger the watcher. Default idle_prompt.",
            },
            "phase": {
                "type": "string",
                "enum": PHASE_ENUM,
                "description": "Optional workflow phase label used for phase-progress reporting.",
            },
            "status_path": {
                "type": "string",
                "description": "Optional explicit JSON status path under ~/.hermes/tmp/.",
            },
            "log_path": {
                "type": "string",
                "description": "Optional explicit log path under ~/.hermes/tmp/.",
            },
            "require_pi": {
                "type": "boolean",
                "description": "Require the resolved target to look like an actual pi worker pane. Default true.",
            },
            "report_phase_progress": {
                "type": "boolean",
                "description": "Emit EVENT:PHASE_PROGRESS lines when phase state changes. Default true.",
            },
        },
        "required": ["action"],
    },
}


def _install_skill() -> None:
    try:
        from hermes_constants import get_hermes_home

        dest = get_hermes_home() / "skills" / "productivity" / "pi-tmux-event-bridge" / "SKILL.md"
    except Exception:
        dest = Path.home() / ".hermes" / "skills" / "productivity" / "pi-tmux-event-bridge" / "SKILL.md"
    src = _PLUGIN_DIR / "skill.md"
    if src.exists() and not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


def _emit(event: str, payload: Optional[dict] = None, *, as_json: bool = False) -> None:
    if as_json:
        out = {"event": event}
        if payload:
            out.update(payload)
        print(json.dumps(out, ensure_ascii=False), flush=True)
        return
    if payload:
        print(f"{EVENT_PREFIX}{event} {json.dumps(payload, ensure_ascii=False, sort_keys=True)}", flush=True)
    else:
        print(f"{EVENT_PREFIX}{event}", flush=True)


def _run_tmux(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["tmux", *args], capture_output=True, text=True)


def _pane_format_fields() -> str:
    return "\t".join(
        [
            "#{pane_id}",
            "#{pane_index}",
            "#{pane_active}",
            "#{pane_current_command}",
            "#{pane_title}",
            "#{pane_current_path}",
            "#{session_name}",
            "#{window_index}",
            "#{window_name}",
        ]
    )


def _parse_pane_line(line: str) -> dict:
    parts = line.split("\t")
    while len(parts) < 9:
        parts.append("")
    pane_id, pane_index, pane_active, current_command, title, current_path, session_name, window_index, window_name = parts[:9]
    return {
        "pane_id": pane_id,
        "pane_index": pane_index,
        "pane_active": pane_active == "1",
        "pane_current_command": current_command,
        "pane_title": title,
        "pane_current_path": current_path,
        "session_name": session_name,
        "window_index": window_index,
        "window_name": window_name,
    }


def _list_panes(target: str) -> list[dict]:
    cp = _run_tmux("list-panes", "-t", target, "-F", _pane_format_fields())
    if cp.returncode != 0:
        raise RuntimeError(cp.stderr.strip() or f"tmux list-panes failed for {target}")
    panes = []
    for line in cp.stdout.splitlines():
        line = line.strip()
        if line:
            panes.append(_parse_pane_line(line))
    return panes


def _pane_info(target: str) -> dict:
    cp = _run_tmux("display-message", "-p", "-t", target, _pane_format_fields())
    if cp.returncode != 0:
        raise RuntimeError(cp.stderr.strip() or f"tmux display-message failed for {target}")
    return _parse_pane_line(cp.stdout.strip())


def _capture_tail(target: str, lines: int = 160) -> str:
    cp = _run_tmux("capture-pane", "-t", target, "-p")
    if cp.returncode != 0:
        raise RuntimeError(cp.stderr.strip() or f"tmux capture-pane failed for {target}")
    parts = cp.stdout.splitlines()
    return "\n".join(parts[-lines:])


def _recent_nonempty_lines(tail: str, limit: int = 20) -> list[str]:
    return [line.rstrip() for line in tail.splitlines() if line.strip()][-limit:]


def _recent_text(tail: str, limit: int = 20) -> str:
    return "\n".join(_recent_nonempty_lines(tail, limit=limit))


def _prompt_visible(tail: str) -> bool:
    lines = _recent_nonempty_lines(tail, limit=8)
    return any(line.strip() == ">" for line in lines[-4:])


def _working_recent(tail: str) -> bool:
    recent = _recent_text(tail, limit=10)
    return any(tok in recent for tok in SPINNER_TOKENS) or any(marker in recent for marker in ACTIVE_WORKING_MARKERS)


def _has_progress_recent(tail: str) -> bool:
    recent = _recent_text(tail, limit=12)
    lower_recent = recent.lower()
    return any(marker.lower() in lower_recent for marker in ACTIVE_PROGRESS_MARKERS)


def _looks_like_pi_worker(pane: dict, tail: str) -> bool:
    command = (pane.get("pane_current_command") or "").strip().lower()
    title = (pane.get("pane_title") or "").strip().lower()
    if command == "pi":
        return True
    if "π" in (pane.get("pane_title") or ""):
        return True
    if "π  |" in tail:
        return True
    if " think:" in tail and "📁 " in tail:
        return True
    if title.startswith("pi") or "doct-" in title:
        return True
    return False


def _score_worker_pane(pane: dict) -> int:
    score = 0
    command = (pane.get("pane_current_command") or "").strip().lower()
    title = (pane.get("pane_title") or "")
    if command == "pi":
        score += 100
    if "π" in title:
        score += 30
    if title.lower().startswith("pi"):
        score += 20
    if pane.get("pane_active"):
        score += 5
    try:
        score -= int(pane.get("pane_index") or "0")
    except Exception:
        pass
    return score


def _resolve_targets(target: str, require_pi: bool = True) -> dict:
    target = (target or "").strip()
    if not target:
        raise RuntimeError("target is required")
    if target.startswith("%"):
        worker = _pane_info(target)
        panes = [worker]
    else:
        panes = _list_panes(target)
        if not panes:
            raise RuntimeError(f"No tmux panes found for target {target}")
        worker = sorted(panes, key=_score_worker_pane, reverse=True)[0]
    worker_tail = _capture_tail(worker["pane_id"])
    looks_like_worker = _looks_like_pi_worker(worker, worker_tail)
    if require_pi and not looks_like_worker:
        raise RuntimeError(
            f"Resolved pane {worker['pane_id']} does not look like a pi worker pane "
            f"(command={worker.get('pane_current_command')!r}, title={worker.get('pane_title')!r})"
        )
    controller = None
    other_panes = [pane for pane in panes if pane.get("pane_id") != worker.get("pane_id")]
    if other_panes:
        controller = sorted(
            other_panes,
            key=lambda pane: (
                1 if (pane.get("pane_current_command") or "").strip().lower() in {"python", "python3"} else 0,
                1 if "dever" in (pane.get("pane_title") or "").lower() else 0,
                1 if pane.get("pane_active") else 0,
            ),
            reverse=True,
        )[0]
    return {
        "input_target": target,
        "worker": worker,
        "worker_tail": worker_tail,
        "controller": controller,
        "looks_like_worker": looks_like_worker,
        "panes": panes,
    }


def _idle_prompt(tail: str, *, same_count: int, working: bool, has_progress: bool) -> bool:
    if not _prompt_visible(tail) or working:
        return False
    if same_count >= 2:
        return True
    return not has_progress


def _tail_hash(tail: str) -> str:
    return hashlib.sha256(tail.encode("utf-8", errors="replace")).hexdigest()[:16]


def _marker_present(tail: str, markers: list[str], *, recent_limit: int = 50) -> bool:
    recent = _recent_text(tail, limit=recent_limit)
    lower_recent = recent.lower()
    for marker in markers:
        if marker.lower() in lower_recent:
            return True
    return False


def _detect_events(
    tail: str,
    *,
    plan_file: str | None,
    idle_streak: int,
    idle_streak_required: int,
    same_count: int,
) -> tuple[list[str], dict]:
    working = _working_recent(tail)
    has_progress = _has_progress_recent(tail)
    prompt_visible = _prompt_visible(tail)
    idle = _idle_prompt(tail, same_count=same_count, working=working, has_progress=has_progress)
    review_summary = _marker_present(tail, REVIEW_SUMMARY_MARKERS)
    review_recommendation = _marker_present(tail, REVIEW_RECOMMENDATION_MARKERS)
    integrate_complete = _marker_present(tail, INTEGRATE_COMPLETE_MARKERS)
    pm_review_complete = _marker_present(tail, PM_REVIEW_COMPLETE_MARKERS)
    blocked = _marker_present(tail, EXECUTION_BLOCKED_MARKERS)
    plan_ready = bool(plan_file and Path(plan_file).expanduser().exists())

    events: list[str] = []
    if idle and idle_streak >= idle_streak_required:
        events.append("idle_prompt")
    if plan_ready and idle and idle_streak >= idle_streak_required:
        events.append("plan_ready")
    if review_summary and review_recommendation and not working:
        events.append("review_complete")
    if pm_review_complete and not working:
        events.append("pm_review_complete")
    if integrate_complete and not working:
        events.append("integrate_complete")
    if blocked and (idle or idle_streak >= 1 or not working):
        events.append("execution_blocked")

    markers = {
        "prompt_visible": prompt_visible,
        "idle_prompt": idle,
        "working": working,
        "has_progress": has_progress,
        "review_summary": review_summary,
        "review_recommendation": review_recommendation,
        "integrate_complete": integrate_complete,
        "pm_review_complete": pm_review_complete,
        "execution_blocked": blocked,
        "plan_file_exists": plan_ready,
    }
    return list(dict.fromkeys(events)), markers


def _classify_state(*, trusted: bool, events: list[str], idle_prompt: bool, working: bool, has_progress: bool, same_count: int) -> str:
    if not trusted:
        return "untrusted_target"
    if any(event in events for event in ("review_complete", "integrate_complete", "pm_review_complete")):
        return "phase_complete"
    if idle_prompt and same_count >= 1:
        return "idle"
    if working:
        return "active"
    if has_progress and same_count == 0:
        return "active"
    if same_count >= 2:
        return "stale"
    return "ambiguous"


def _default_paths(watcher_id: str) -> tuple[Path, Path]:
    DEFAULT_TMP_DIR.mkdir(parents=True, exist_ok=True)
    return (
        DEFAULT_TMP_DIR / f"{watcher_id}-status.json",
        DEFAULT_TMP_DIR / f"{watcher_id}.log",
    )


def _inject_message(message: str, role: str = "user") -> bool:
    global _CTX
    if _CTX is None:
        return False
    try:
        return bool(_CTX.inject_message(message, role=role))
    except Exception:
        return False


@dataclass
class WatcherState:
    watcher_id: str
    target_input: str
    event: str
    phase: str | None
    plan_file: str | None
    next_message: str | None
    role: str
    poll_seconds: float
    idle_streak_required: int
    timeout_seconds: int
    require_pi: bool
    report_phase_progress: bool
    status_path: str
    log_path: str
    running: bool = True
    fired: bool = False
    fired_event: str | None = None
    injected: bool = False
    last_error: str | None = None
    last_tail_excerpt: str | None = None
    last_change_at: float | None = None
    started_at: float | None = None
    stopped_at: float | None = None
    resolved_target: str | None = None
    resolved_worker: dict | None = None
    controller_target: str | None = None
    controller_pane: dict | None = None
    same_count: int = 0
    idle_prompt: bool = False
    working: bool = False
    has_progress: bool = False
    trusted_target: bool = False
    state_classification: str | None = None
    last_events: list[str] | None = None
    last_markers: dict | None = None
    phase_status: str | None = None


_WATCHERS: dict[str, WatcherState] = {}
_WATCHER_THREADS: dict[str, threading.Thread] = {}
_WATCHER_LOCK = threading.Lock()


def _write_status(state: WatcherState) -> None:
    path = Path(state.status_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(state)
    if payload.get("last_tail_excerpt") and len(payload["last_tail_excerpt"]) > 4000:
        payload["last_tail_excerpt"] = payload["last_tail_excerpt"][-4000:]
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))


def _log(state: WatcherState, event: str, **payload) -> None:
    path = Path(state.log_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "watcher_id": state.watcher_id,
        "event": event,
        **payload,
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def _phase_progress_payload(state: WatcherState, *, status: str, phase_event: str | None = None) -> dict:
    return {
        "watcher_id": state.watcher_id,
        "phase": state.phase,
        "status": status,
        "phase_event": phase_event,
        "target_input": state.target_input,
        "resolved_target": state.resolved_target,
        "status_path": state.status_path,
        "log_path": state.log_path,
    }


def _watcher_loop(state: WatcherState) -> None:
    last_tail_hash = None
    idle_streak = 0
    last_state_classification = None
    last_phase_status = None
    start = time.time()
    state.started_at = start
    try:
        if state.resolved_target and state.resolved_worker:
            resolved = {
                "worker": state.resolved_worker,
                "controller": state.controller_pane,
                "looks_like_worker": state.trusted_target,
            }
        else:
            resolved = _resolve_targets(state.target_input, require_pi=state.require_pi)
            state.resolved_target = resolved["worker"]["pane_id"]
            state.resolved_worker = resolved["worker"]
            state.controller_pane = resolved.get("controller")
            state.controller_target = resolved.get("controller", {}).get("pane_id") if resolved.get("controller") else None
            state.trusted_target = bool(resolved.get("looks_like_worker"))
        _log(
            state,
            "PREFLIGHT_OK",
            target_input=state.target_input,
            resolved_target=state.resolved_target,
            controller_target=state.controller_target,
            worker_command=state.resolved_worker.get("pane_current_command") if state.resolved_worker else None,
            worker_title=state.resolved_worker.get("pane_title") if state.resolved_worker else None,
        )
        _emit(
            "PREFLIGHT_OK",
            {
                "watcher_id": state.watcher_id,
                "target_input": state.target_input,
                "resolved_target": state.resolved_target,
                "controller_target": state.controller_target,
                "status_path": state.status_path,
                "log_path": state.log_path,
            },
        )
        if state.phase and state.report_phase_progress:
            state.phase_status = "watching"
            payload = _phase_progress_payload(state, status="watching")
            _log(state, "PHASE_PROGRESS", **payload)
            _emit("PHASE_PROGRESS", payload)
            last_phase_status = "watching"

        while state.running:
            tail = _capture_tail(state.resolved_target)
            tail_hash = _tail_hash(tail)
            if tail_hash == last_tail_hash:
                state.same_count += 1
            else:
                state.same_count = 0
                state.last_change_at = time.time()
                last_tail_hash = tail_hash

            pane = _pane_info(state.resolved_target)
            trusted = _looks_like_pi_worker(pane, tail)
            events, markers = _detect_events(
                tail,
                plan_file=state.plan_file,
                idle_streak=idle_streak,
                idle_streak_required=state.idle_streak_required,
                same_count=state.same_count,
            )
            state.resolved_worker = pane
            state.trusted_target = trusted
            state.idle_prompt = bool(markers["idle_prompt"])
            state.working = bool(markers["working"])
            state.has_progress = bool(markers["has_progress"])
            state.last_events = events
            state.last_markers = markers
            state.last_tail_excerpt = "\n".join(tail.splitlines()[-60:])
            state.state_classification = _classify_state(
                trusted=trusted,
                events=events,
                idle_prompt=state.idle_prompt,
                working=state.working,
                has_progress=state.has_progress,
                same_count=state.same_count,
            )

            idle_streak = idle_streak + 1 if state.idle_prompt else 0

            if state.state_classification != last_state_classification:
                _log(state, "STATE_CHANGED", classification=state.state_classification, events=events, markers=markers)
                _emit(
                    "STATE_CHANGED",
                    {
                        "watcher_id": state.watcher_id,
                        "state": state.state_classification,
                        "resolved_target": state.resolved_target,
                        "events": events,
                    },
                )
                last_state_classification = state.state_classification

            if not trusted:
                state.last_error = "Resolved target no longer looks like the pi worker pane."
                _log(state, "TARGET_UNTRUSTED", resolved_target=state.resolved_target)
                _emit(
                    "TARGET_UNTRUSTED",
                    {
                        "watcher_id": state.watcher_id,
                        "resolved_target": state.resolved_target,
                        "status_path": state.status_path,
                        "log_path": state.log_path,
                    },
                )
                state.running = False
                _write_status(state)
                break

            if state.phase and state.report_phase_progress:
                phase_done_event = PHASE_TO_EVENT.get(state.phase)
                current_phase_status = "watching"
                if phase_done_event and phase_done_event in events:
                    current_phase_status = "complete"
                elif state.state_classification == "untrusted_target":
                    current_phase_status = "untrusted"
                elif state.state_classification == "stale":
                    current_phase_status = "stalled"
                if current_phase_status != last_phase_status:
                    state.phase_status = current_phase_status
                    payload = _phase_progress_payload(state, status=current_phase_status, phase_event=phase_done_event if current_phase_status == "complete" else None)
                    _log(state, "PHASE_PROGRESS", **payload)
                    _emit("PHASE_PROGRESS", payload)
                    last_phase_status = current_phase_status

            _write_status(state)

            if state.event == "idle_prompt":
                eligible_events = list(events)
            else:
                eligible_events = [event for event in events if event != "idle_prompt"]

            if state.event in eligible_events:
                state.fired = True
                state.fired_event = state.event
                _log(state, "WATCHER_FIRED", fired_event=state.event, phase=state.phase)
                _emit(
                    state.event.upper(),
                    {
                        "watcher_id": state.watcher_id,
                        "phase": state.phase,
                        "resolved_target": state.resolved_target,
                        "status_path": state.status_path,
                        "log_path": state.log_path,
                    },
                )
                if state.next_message:
                    state.injected = _inject_message(state.next_message, role=state.role)
                    if state.injected:
                        _log(state, "MESSAGE_INJECTED", role=state.role, message=state.next_message)
                        _emit(
                            "MESSAGE_INJECTED",
                            {
                                "watcher_id": state.watcher_id,
                                "phase": state.phase,
                                "message": state.next_message,
                            },
                        )
                    else:
                        state.last_error = "Injection unavailable (likely gateway mode or no active CLI reference)."
                        _log(state, "INJECT_UNAVAILABLE", message=state.next_message)
                        _emit(
                            "INJECT_UNAVAILABLE",
                            {
                                "watcher_id": state.watcher_id,
                                "phase": state.phase,
                                "message": state.next_message,
                            },
                        )
                state.running = False
                _write_status(state)
                break

            if state.timeout_seconds and (time.time() - start) > state.timeout_seconds:
                state.last_error = f"Timed out after {state.timeout_seconds}s"
                _log(state, "TIMEOUT", timeout_seconds=state.timeout_seconds)
                _emit(
                    "TIMEOUT",
                    {
                        "watcher_id": state.watcher_id,
                        "phase": state.phase,
                        "resolved_target": state.resolved_target,
                        "status_path": state.status_path,
                        "log_path": state.log_path,
                    },
                )
                state.running = False
                _write_status(state)
                break

            time.sleep(state.poll_seconds)
    except Exception as exc:
        state.last_error = str(exc)
        _log(state, "WATCHER_ERROR", error=str(exc))
        _emit(
            "WATCHER_ERROR",
            {
                "watcher_id": state.watcher_id,
                "phase": state.phase,
                "error": str(exc),
                "status_path": state.status_path,
                "log_path": state.log_path,
            },
        )
    finally:
        state.stopped_at = time.time()
        _write_status(state)


def _watcher_payload(state: WatcherState) -> dict:
    payload = asdict(state)
    if payload.get("last_tail_excerpt") and len(payload["last_tail_excerpt"]) > 2000:
        payload["last_tail_excerpt"] = payload["last_tail_excerpt"][-2000:]
    return payload


def _arm_watcher(args: dict) -> dict:
    target = (args.get("target") or "").strip()
    if not target:
        return {"error": "target is required for action=arm"}
    watcher_id = f"watch_{uuid.uuid4().hex[:10]}"
    default_status, default_log = _default_paths(watcher_id)
    status_path = str(Path(args.get("status_path") or default_status).expanduser())
    log_path = str(Path(args.get("log_path") or default_log).expanduser())
    require_pi = bool(True if args.get("require_pi") is None else args.get("require_pi"))
    try:
        resolved = _resolve_targets(target, require_pi=require_pi)
    except Exception as exc:
        return {"error": str(exc)}
    state = WatcherState(
        watcher_id=watcher_id,
        target_input=target,
        event=args.get("event") or "idle_prompt",
        phase=(args.get("phase") or "").strip() or None,
        plan_file=args.get("plan_file"),
        next_message=args.get("next_message"),
        role=args.get("role") or "user",
        poll_seconds=float(args.get("poll_seconds") or 5.0),
        idle_streak_required=int(args.get("idle_streak") or 2),
        timeout_seconds=int(args.get("timeout_seconds") or 1800),
        require_pi=require_pi,
        report_phase_progress=bool(True if args.get("report_phase_progress") is None else args.get("report_phase_progress")),
        status_path=status_path,
        log_path=log_path,
        resolved_target=resolved["worker"]["pane_id"],
        resolved_worker=resolved["worker"],
        controller_target=resolved.get("controller", {}).get("pane_id") if resolved.get("controller") else None,
        controller_pane=resolved.get("controller"),
        trusted_target=bool(resolved.get("looks_like_worker")),
    )
    thread = threading.Thread(target=_watcher_loop, args=(state,), daemon=True, name=f"pi-tmux-{watcher_id}")
    replaced_watchers: list[str] = []
    with _WATCHER_LOCK:
        for existing in _WATCHERS.values():
            if not existing.running:
                continue
            if existing.target_input == target or (
                existing.resolved_target and existing.resolved_target == state.resolved_target
            ):
                existing.running = False
                replaced_watchers.append(existing.watcher_id)
                _log(existing, "REPLACED", replaced_by=watcher_id)
        _WATCHERS[watcher_id] = state
        _WATCHER_THREADS[watcher_id] = thread
    thread.start()
    return {
        "success": True,
        "watcher": _watcher_payload(state),
        "replaced_watchers": replaced_watchers,
        "note": (
            "Watcher armed. Prefer a CLI controller for autonomous next-step injection. "
            "Use terminal watch_patterns on EVENT:PHASE_PROGRESS, EVENT:TARGET_UNTRUSTED, EVENT:WATCHER_ERROR, "
            "and EVENT:TIMEOUT for Discord-visible progress notifications."
        ),
    }


def _status_watcher(args: dict) -> dict:
    watcher_id = (args.get("watcher_id") or "").strip()
    if not watcher_id:
        return {"error": "watcher_id is required for action=status"}
    with _WATCHER_LOCK:
        state = _WATCHERS.get(watcher_id)
    if not state:
        return {"error": f"Watcher not found: {watcher_id}"}
    return {"success": True, "watcher": _watcher_payload(state)}


def _stop_watcher(args: dict) -> dict:
    watcher_id = (args.get("watcher_id") or "").strip()
    if not watcher_id:
        return {"error": "watcher_id is required for action=stop"}
    with _WATCHER_LOCK:
        state = _WATCHERS.get(watcher_id)
    if not state:
        return {"error": f"Watcher not found: {watcher_id}"}
    state.running = False
    _log(state, "STOP_REQUESTED")
    return {"success": True, "watcher": _watcher_payload(state)}


def _list_watchers() -> dict:
    with _WATCHER_LOCK:
        watchers = [_watcher_payload(state) for state in _WATCHERS.values()]
    return {"success": True, "watchers": watchers}


def _observe_once(args: dict) -> dict:
    target = (args.get("target") or "").strip()
    if not target:
        return {"error": "target is required for action=observe"}
    require_pi = bool(True if args.get("require_pi") is None else args.get("require_pi"))
    resolved = _resolve_targets(target, require_pi=require_pi)
    tail = resolved["worker_tail"]
    events, markers = _detect_events(
        tail,
        plan_file=args.get("plan_file"),
        idle_streak=int(args.get("idle_streak") or 2),
        idle_streak_required=int(args.get("idle_streak") or 2),
        same_count=0,
    )
    return {
        "success": True,
        "target_input": target,
        "resolved_target": resolved["worker"]["pane_id"],
        "worker": resolved["worker"],
        "controller": resolved.get("controller"),
        "trusted_target": bool(resolved.get("looks_like_worker")),
        "idle_prompt": bool(markers["idle_prompt"]),
        "working": bool(markers["working"]),
        "has_progress": bool(markers["has_progress"]),
        "events": events,
        "markers": markers,
        "tail_excerpt": "\n".join(tail.splitlines()[-60:]),
        "inject_available": bool(_CTX is not None and getattr(getattr(_CTX, "_manager", None), "_cli_ref", None) is not None),
    }


def pi_tmux_watch_control(args: dict, **kwargs) -> str:
    action = (args.get("action") or "").strip()
    if action == "arm":
        return json.dumps(_arm_watcher(args), ensure_ascii=False)
    if action == "status":
        return json.dumps(_status_watcher(args), ensure_ascii=False)
    if action == "stop":
        return json.dumps(_stop_watcher(args), ensure_ascii=False)
    if action == "list":
        return json.dumps(_list_watchers(), ensure_ascii=False)
    if action == "observe":
        try:
            return json.dumps(_observe_once(args), ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"error": str(exc)}, ensure_ascii=False)
    return json.dumps({"error": "Invalid action. Use arm, status, stop, list, or observe."}, ensure_ascii=False)


def _build_parser(subparser: argparse.ArgumentParser) -> None:
    subs = subparser.add_subparsers(dest="pi_tmux_command")

    watch = subs.add_parser("watch", help="Watch a tmux target and emit grounded workflow events")
    watch.add_argument("--target", required=True)
    watch.add_argument("--plan-file")
    watch.add_argument("--phase", choices=PHASE_ENUM)
    watch.add_argument("--poll-seconds", type=float, default=5.0)
    watch.add_argument("--idle-streak", type=int, default=2)
    watch.add_argument("--timeout", type=float, default=1800)
    watch.add_argument("--once", action="store_true")
    watch.add_argument("--json", action="store_true")
    watch.add_argument("--status-file")
    watch.add_argument("--log-file")
    watch.add_argument("--no-require-pi", action="store_true")
    watch.add_argument("--no-phase-progress", action="store_true")
    watch.set_defaults(func=_cmd_watch)

    inject = subs.add_parser("inject", help="Inject a message into an active Hermes CLI session")
    inject.add_argument("--message", required=True)
    inject.add_argument("--role", default="user")
    inject.add_argument("--json", action="store_true")
    inject.set_defaults(func=_cmd_inject)

    auto = subs.add_parser("auto-next", help="Wait for the phase/event, then inject the next workflow message into Hermes CLI")
    auto.add_argument("--target", required=True)
    auto.add_argument("--plan-file")
    auto.add_argument("--message")
    auto.add_argument("--stage", choices=["planning", "review", "integrate", "pm-plan", "validate"])
    auto.add_argument("--phase", choices=PHASE_ENUM)
    auto.add_argument("--role", default="user")
    auto.add_argument("--poll-seconds", type=float, default=5.0)
    auto.add_argument("--idle-streak", type=int, default=2)
    auto.add_argument("--timeout", type=float, default=1800)
    auto.add_argument("--json", action="store_true")
    auto.add_argument("--status-file")
    auto.add_argument("--log-file")
    auto.add_argument("--no-require-pi", action="store_true")
    auto.add_argument("--no-phase-progress", action="store_true")
    auto.set_defaults(func=_cmd_auto_next)

    status = subs.add_parser("status", help="Show plugin status and whether CLI injection is available")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=_cmd_status)


def _stage_message(stage: str, plan_file: str | None) -> str:
    if stage == "planning":
        if not plan_file:
            raise ValueError("--plan-file is required for stage=planning")
        return f"/review:change {plan_file}"
    if stage == "review":
        if not plan_file:
            raise ValueError("--plan-file is required for stage=review")
        return f"/review:change-integrate {plan_file}"
    if stage == "integrate":
        return "/dev:pm-review stage=plan"
    if stage == "pm-plan":
        return "/dev:run"
    if stage == "validate":
        return "/dev:pm-review stage=implementation"
    raise ValueError(f"Unsupported stage: {stage}")


def _blocking_watch(
    *,
    target: str,
    plan_file: str | None,
    phase: str | None,
    poll_seconds: float,
    idle_streak_required: int,
    timeout_seconds: float,
    as_json: bool,
    once: bool,
    require_pi: bool,
    report_phase_progress: bool,
    status_path: str | None,
    log_path: str | None,
    next_message: str | None = None,
    role: str = "user",
) -> int:
    watcher_id = f"cliwatch_{uuid.uuid4().hex[:10]}"
    default_status, default_log = _default_paths(watcher_id)
    state = WatcherState(
        watcher_id=watcher_id,
        target_input=target,
        event=PHASE_TO_EVENT.get(phase or "", "idle_prompt") if phase else "idle_prompt",
        phase=phase,
        plan_file=plan_file,
        next_message=next_message,
        role=role,
        poll_seconds=poll_seconds,
        idle_streak_required=idle_streak_required,
        timeout_seconds=int(timeout_seconds),
        require_pi=require_pi,
        report_phase_progress=report_phase_progress,
        status_path=str(Path(status_path or default_status).expanduser()),
        log_path=str(Path(log_path or default_log).expanduser()),
    )
    _watcher_loop(state)
    payload = _watcher_payload(state)
    if as_json:
        print(json.dumps(payload, ensure_ascii=False), flush=True)
    else:
        print(json.dumps(payload, indent=2, ensure_ascii=False), flush=True)
    if state.last_error:
        return 1
    if state.fired or once:
        return 0
    return 0


def _cmd_watch(args: argparse.Namespace) -> int:
    return _blocking_watch(
        target=args.target,
        plan_file=args.plan_file,
        phase=args.phase,
        poll_seconds=args.poll_seconds,
        idle_streak_required=args.idle_streak,
        timeout_seconds=args.timeout,
        as_json=args.json,
        once=args.once,
        require_pi=not args.no_require_pi,
        report_phase_progress=not args.no_phase_progress,
        status_path=args.status_file,
        log_path=args.log_file,
    )


def _cmd_inject(args: argparse.Namespace) -> int:
    ok = _inject_message(args.message, role=args.role)
    if ok:
        _emit("MESSAGE_INJECTED", {"role": args.role}, as_json=args.json)
        return 0
    _emit("INJECT_UNAVAILABLE", {"reason": "No active Hermes CLI session (gateway mode or no CLI ref)."}, as_json=args.json)
    return 1


def _cmd_auto_next(args: argparse.Namespace) -> int:
    message = args.message or _stage_message(args.stage, args.plan_file)
    phase = args.phase or {
        "planning": "planning",
        "review": "review",
        "integrate": "integrate",
        "pm-plan": "pm_review_plan",
        "validate": "validate",
    }.get(args.stage or "")
    return _blocking_watch(
        target=args.target,
        plan_file=args.plan_file,
        phase=phase,
        poll_seconds=args.poll_seconds,
        idle_streak_required=args.idle_streak,
        timeout_seconds=args.timeout,
        as_json=args.json,
        once=True,
        require_pi=not args.no_require_pi,
        report_phase_progress=not args.no_phase_progress,
        status_path=args.status_file,
        log_path=args.log_file,
        next_message=message,
        role=args.role,
    )


def _cmd_status(args: argparse.Namespace) -> int:
    available = bool(_CTX is not None and getattr(getattr(_CTX, "_manager", None), "_cli_ref", None) is not None)
    payload = {
        "inject_available": available,
        "mode": "cli" if available else "gateway_or_no_cli",
        "plugin_dir": str(_PLUGIN_DIR),
        "tmp_dir": str(DEFAULT_TMP_DIR),
    }
    print(json.dumps(payload, ensure_ascii=False) if args.json else "\n".join(f"{k}: {v}" for k, v in payload.items()), flush=True)
    return 0


def _dispatch(args: argparse.Namespace) -> int:
    func = getattr(args, "func", None)
    if func is None:
        print("Usage: hermes pi-tmux <watch|inject|auto-next|status>")
        return 1
    return int(func(args) or 0)


def register(ctx):
    global _CTX
    _CTX = ctx
    _install_skill()
    ctx.register_tool(
        name="pi_tmux_watch_control",
        toolset="pi_tmux",
        schema=PI_TMUX_WATCH_CONTROL_SCHEMA,
        handler=pi_tmux_watch_control,
        check_fn=lambda: shutil.which("tmux") is not None,
        description="Manage a grounded in-process event-driven tmux watcher for pi workflows.",
        emoji="📺",
    )
    ctx.register_cli_command(
        name="pi-tmux",
        help="Watch pi tmux sessions, emit phase progress events, and optionally auto-inject next workflow steps",
        description="Grounded tmux watcher for pi workflows with pane resolution, phase progress events, status/log files, and optional Hermes CLI message injection.",
        setup_fn=_build_parser,
        handler_fn=_dispatch,
    )
