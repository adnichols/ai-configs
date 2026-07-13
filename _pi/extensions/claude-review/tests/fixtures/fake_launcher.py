#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import signal
import sys
import time
from pathlib import Path


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--cwd", required=True)
    p.add_argument("--prompt-file")
    p.add_argument("--output", required=True)
    p.add_argument("--review-name", required=True)
    p.add_argument("--timeout-seconds", required=True)
    p.add_argument("--smoke", action="store_true")
    return p


def prompt_mode(path: str | None) -> tuple[str, float]:
    if not path:
        return os.environ.get("FAKE_CLAUDE_REVIEW_MODE", "success"), 0.0
    text = Path(path).read_text(encoding="utf-8")
    mode = "success"
    delay = 0.0
    for line in text.splitlines():
        if line.startswith("MODE="):
            mode = line.split("=", 1)[1].strip()
        elif line.startswith("DELAY="):
            delay = float(line.split("=", 1)[1].strip())
    return mode, delay


def main() -> int:
    args = parser().parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    mode, delay = prompt_mode(args.prompt_file)
    print(f"fake-launcher start mode={mode}", flush=True)
    if delay:
        time.sleep(delay)

    if mode == "hang":
        time.sleep(60)
        return 99
    if mode == "ignore-term":
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        time.sleep(60)
        return 98
    if mode == "classified-failure":
        output.write_text(
            "CLAUDE_AUTH_UNAVAILABLE_IN_TUI\n"
            "Claude TUI reported not logged in; run /login in Claude Code\n"
            "inspect=tmux -L fake attach -t review\n",
            encoding="utf-8",
        )
        return 21
    if mode == "no-artifact":
        return 0
    if mode == "malformed-success":
        output.write_text("VERDICT: CLEAN_FOR_PR\n", encoding="utf-8")
        return 0
    if mode == "nonzero-no-artifact":
        return 17

    if args.smoke:
        output.write_text(
            "CLAUDE_REVIEW_SMOKE_READY\n"
            "socket=fake-socket\n"
            "session=review\n",
            encoding="utf-8",
        )
    else:
        output.write_text(
            "VERDICT: CLEAN_FOR_PR\nNo issues found.\n\n"
            "---\nCLAUDE_REVIEW_LAUNCHER_METADATA\n"
            "socket=fake-socket\nsession=review\n",
            encoding="utf-8",
        )
    print("fake-launcher complete", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
