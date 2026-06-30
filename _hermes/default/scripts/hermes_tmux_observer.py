#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path


def run(cmd: list[str], cwd: str | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, cwd=cwd, check=check)


def tmux_capture(worker: str, lines: int = 160) -> str:
    return run(["tmux", "capture-pane", "-p", "-t", worker, "-S", f"-{lines}"]).stdout


def recent_lines(text: str, n: int = 28) -> list[str]:
    return text.splitlines()[-n:]


def has_prompt(text: str) -> bool:
    return any(re.match(r"^\s*>\s*$", line) for line in recent_lines(text, 25))


def has_recent_progress(text: str) -> bool:
    markers = [
        "Working...",
        "Thinking...",
        "todo toggle",
        "✓ Todo",
        "Took ",
        "Passed:",
        "Verification",
        "What changed",
        "Root causes",
        "Current status",
        "read ",
        "write ",
        "edit ",
        "PM Review Complete",
        "Review Summary",
        "Integration Complete",
    ]
    recent = "\n".join(recent_lines(text, 20))
    return any(marker in recent for marker in markers)


def git_status(repo: str) -> str:
    return run(["git", "status", "--short", "--branch"], cwd=repo).stdout.strip()


def git_branch(repo: str) -> str:
    proc = run(["git", "branch", "--show-current"], cwd=repo)
    return proc.stdout.strip()


def classify(prompt: bool, progress: bool, clean: bool, mode: str) -> str:
    if progress:
        return "active"
    if prompt:
        return mode if clean else f"{mode}-dirty"
    return "waiting"


def main() -> int:
    parser = argparse.ArgumentParser(description="Hermes tmux observer")
    parser.add_argument("--name", required=True)
    parser.add_argument("--worker", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--mode", required=True)
    parser.add_argument("--pr-url", default="")
    parser.add_argument("--status-path", required=True)
    parser.add_argument("--poll", type=int, default=30)
    parser.add_argument("--heartbeat", type=int, default=300)
    args = parser.parse_args()

    status_path = Path(args.status_path).expanduser()
    status_path.parent.mkdir(parents=True, exist_ok=True)

    last_state = None
    last_heartbeat = 0.0

    while True:
        tail = tmux_capture(args.worker)
        prompt = has_prompt(tail)
        progress = has_recent_progress(tail)
        status = git_status(args.repo)
        clean = not any(
            line and not line.startswith("## ")
            for line in status.splitlines()
        )
        branch = git_branch(args.repo)
        state = classify(prompt, progress, clean, args.mode)
        excerpt = "\n".join(recent_lines(tail, 18))
        payload = {
            "ts": time.time(),
            "name": args.name,
            "worker": args.worker,
            "repo": args.repo,
            "branch": branch,
            "mode": args.mode,
            "state": state,
            "prompt": prompt,
            "progress": progress,
            "clean": clean,
            "pr_url": args.pr_url,
            "git_status": status,
            "tail_excerpt": excerpt,
        }
        status_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        now = time.time()
        if state != last_state:
            print(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] EVENT:PHASE_PROGRESS name={args.name} state={state} branch={branch}",
                flush=True,
            )
            if args.pr_url:
                print(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] EVENT:PR_STATUS name={args.name} pr={args.pr_url} clean={str(clean).lower()}",
                    flush=True,
                )
            last_state = state
            last_heartbeat = now
        elif now - last_heartbeat >= args.heartbeat:
            print(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] EVENT:OBSERVER_HEARTBEAT name={args.name} state={state} branch={branch} clean={str(clean).lower()}",
                flush=True,
            )
            last_heartbeat = now

        time.sleep(args.poll)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] EVENT:OBSERVER_STOPPED", flush=True)
        raise SystemExit(0)
