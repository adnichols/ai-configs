#!/usr/bin/env python3
import argparse
import json
import os
import signal
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path


def emit(payload, exit_code=0):
    print(json.dumps(payload, indent=2, sort_keys=True))
    raise SystemExit(exit_code)


def tmux_display(target, fmt):
    proc = subprocess.run(
        ["tmux", "display-message", "-p", "-t", target, fmt],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        emit(
            {
                "ok": False,
                "error": "tmux_lookup_failed",
                "target": target,
                "stderr": proc.stderr.strip(),
            },
            1,
        )
    return proc.stdout.rstrip("\n")


def read_proc_maps():
    parents = defaultdict(list)
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        try:
            stat = (entry / "stat").read_text()
            after = stat.rsplit(")", 1)[1].strip().split()
            ppid = int(after[1])
            parents[ppid].append(pid)
        except Exception:
            continue
    return parents


def descendants(root_pid, parents):
    seen = set()
    queue = [root_pid]
    while queue:
        current = queue.pop(0)
        for child in parents.get(current, []):
            if child not in seen:
                seen.add(child)
                queue.append(child)
    return seen


def cmdline_for(pid):
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
        if raw:
            parts = [p.decode(errors="replace") for p in raw.split(b"\0") if p]
            if parts:
                return parts
    except Exception:
        pass
    try:
        return [Path(f"/proc/{pid}/comm").read_text().strip()]
    except Exception:
        return []


def is_pi_process(pid):
    parts = cmdline_for(pid)
    if not parts:
        return False
    exe = os.path.basename(parts[0])
    return exe == "pi"


def process_exists(pid):
    return Path(f"/proc/{pid}").exists()


def resolve_signal(name):
    normalized = name.upper()
    if normalized.startswith("SIG"):
        normalized = normalized[3:]
    try:
        return getattr(signal, f"SIG{normalized}")
    except AttributeError:
        emit({"ok": False, "error": "invalid_signal", "signal": name}, 1)


def main():
    parser = argparse.ArgumentParser(
        description="Kill exactly one pi process tied to one tmux pane after exact scope checks. Defaults to dry-run."
    )
    parser.add_argument("--pane", required=True, help="tmux pane id, e.g. %%1")
    parser.add_argument("--expected-session", required=True)
    parser.add_argument("--expected-window", required=True)
    parser.add_argument("--expected-cwd", required=True)
    parser.add_argument("--signal", default="TERM")
    parser.add_argument("--wait-seconds", type=float, default=5.0)
    parser.add_argument("--execute", action="store_true", help="Actually send the signal. Without this flag the script is dry-run only.")
    args = parser.parse_args()

    fmt = "#{pane_id}\t#{session_name}\t#{window_name}\t#{pane_pid}\t#{pane_current_command}\t#{pane_current_path}"
    pane_id, session_name, window_name, pane_pid, pane_command, pane_cwd = tmux_display(args.pane, fmt).split("\t")

    mismatches = {}
    if session_name != args.expected_session:
        mismatches["session"] = {"expected": args.expected_session, "actual": session_name}
    if window_name != args.expected_window:
        mismatches["window"] = {"expected": args.expected_window, "actual": window_name}
    if os.path.realpath(pane_cwd) != os.path.realpath(args.expected_cwd):
        mismatches["cwd"] = {"expected": os.path.realpath(args.expected_cwd), "actual": os.path.realpath(pane_cwd)}
    if mismatches:
        emit(
            {
                "ok": False,
                "error": "scope_mismatch",
                "pane": {
                    "pane_id": pane_id,
                    "session_name": session_name,
                    "window_name": window_name,
                    "pane_pid": int(pane_pid),
                    "pane_current_command": pane_command,
                    "pane_cwd": pane_cwd,
                },
                "mismatches": mismatches,
            },
            1,
        )

    parents = read_proc_maps()
    root_pid = int(pane_pid)
    candidates = sorted(pid for pid in ({root_pid} | descendants(root_pid, parents)) if is_pi_process(pid))
    if not candidates:
        emit(
            {
                "ok": False,
                "error": "no_pi_process_in_target_pane",
                "pane": {
                    "pane_id": pane_id,
                    "session_name": session_name,
                    "window_name": window_name,
                    "pane_pid": root_pid,
                    "pane_current_command": pane_command,
                    "pane_cwd": pane_cwd,
                },
            },
            1,
        )
    if len(candidates) != 1:
        emit(
            {
                "ok": False,
                "error": "ambiguous_pi_processes_in_target_pane",
                "pane": {
                    "pane_id": pane_id,
                    "session_name": session_name,
                    "window_name": window_name,
                    "pane_pid": root_pid,
                    "pane_current_command": pane_command,
                    "pane_cwd": pane_cwd,
                },
                "pi_candidates": [
                    {"pid": pid, "cmdline": cmdline_for(pid)} for pid in candidates
                ],
            },
            1,
        )

    target_pid = candidates[0]
    payload = {
        "ok": True,
        "mode": "execute" if args.execute else "dry_run",
        "pane": {
            "pane_id": pane_id,
            "session_name": session_name,
            "window_name": window_name,
            "pane_pid": root_pid,
            "pane_current_command": pane_command,
            "pane_cwd": pane_cwd,
        },
        "target": {
            "pid": target_pid,
            "cmdline": cmdline_for(target_pid),
            "signal": args.signal.upper(),
        },
    }

    if not args.execute:
        emit(payload, 0)

    sig = resolve_signal(args.signal)
    try:
        os.kill(target_pid, sig)
    except ProcessLookupError:
        payload["target"]["already_exited"] = True
        emit(payload, 0)

    deadline = time.time() + max(args.wait_seconds, 0)
    while time.time() < deadline:
        if not process_exists(target_pid):
            payload["target"]["exited"] = True
            emit(payload, 0)
        time.sleep(0.1)

    payload["target"]["exited"] = not process_exists(target_pid)
    payload["target"]["still_running_after_wait"] = process_exists(target_pid)
    emit(payload, 0 if not payload["target"]["still_running_after_wait"] else 1)


if __name__ == "__main__":
    main()
