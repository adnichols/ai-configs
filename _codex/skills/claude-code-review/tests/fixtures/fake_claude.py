#!/usr/bin/env python3
"""Interactive fake Claude TUI for claude_interactive_review.py tests."""

from __future__ import annotations

import json
import os
import re
import select
import sys
import termios
import time
import tty
from pathlib import Path


def auth_status() -> int:
    logged_in = os.environ.get("FAKE_CLAUDE_AUTH", "1") != "0"
    print(json.dumps({"loggedIn": logged_in, "authMethod": "fake" if logged_in else "none"}))
    return 0 if logged_in else 1


def restore_tty(old_tty) -> None:
    if old_tty is not None:
        try:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old_tty)
        except Exception:
            pass


def persist_session_answer(session_id: str | None, answer: str) -> None:
    if not session_id:
        return
    project_key = re.sub(r"[^A-Za-z0-9_-]", "-", os.getcwd())
    record = Path.home() / ".claude" / "projects" / project_key / f"{session_id}.jsonl"
    record.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "type": "assistant",
        "sessionId": session_id,
        "message": {"role": "assistant", "content": [{"type": "text", "text": answer}]},
    }
    record.write_text(json.dumps(entry) + "\n", encoding="utf-8")


def interactive() -> int:
    old_tty = None
    try:
        old_tty = termios.tcgetattr(sys.stdin.fileno())
        tty.setcbreak(sys.stdin.fileno())
    except Exception:
        old_tty = None
    try:
        session_id = None
        if "--session-id" in sys.argv:
            index = sys.argv.index("--session-id")
            if index + 1 < len(sys.argv):
                session_id = sys.argv[index + 1]
        if os.environ.get("FAKE_CLAUDE_NO_READY") == "1":
            print("Claude Code fake loading", flush=True)
            time.sleep(300)
            return 0
        if os.environ.get("FAKE_CLAUDE_NOT_LOGGED_IN") == "1" or (
            os.environ.get("FAKE_CLAUDE_REJECT_CONFIG_DIR") == "1" and os.environ.get("CLAUDE_CONFIG_DIR")
        ):
            print("Not logged in · Please run /login", flush=True)
            time.sleep(300)
            return 0
        print("Claude Code fake\n❯ ", end="", flush=True)
        buf = ""
        echoed = os.environ.get("FAKE_CLAUDE_NO_ECHO") != "1"
        answered = False
        while True:
            ready, _, _ = select.select([sys.stdin], [], [], 300)
            if not ready:
                return 0
            ch = sys.stdin.read(1)
            if ch == "":
                return 0
            buf += ch
            if echoed:
                print(ch, end="", flush=True)
            if "/exit" in buf:
                return 0
            marker_match = re.search(r"CLAUDE_REVIEW_ANSWER_START_[0-9a-f]+", buf)
            sentinel_match = re.search(r"CLAUDE_REVIEW_FINAL_SENTINEL:([^\n\r]+)", buf)
            if marker_match and sentinel_match and ch in "\n\r" and not answered:
                answered = True
                marker = marker_match.group(0)
                sentinel = sentinel_match.group(1).strip()
                if os.environ.get("FAKE_CLAUDE_BOUNDARY_UNCERTAIN") == "1":
                    print(f"\n{marker}\nVERDICT: PASS_SCOPED\nBoundary-bad fake review\n{sentinel}\n❯ ", flush=True)
                    continue
                if os.environ.get("FAKE_CLAUDE_SESSION_LIMIT") == "1":
                    print("\n⎿  You've hit your session limit · resets 11:30am (America/Denver)\n❯ ", flush=True)
                    continue
                if os.environ.get("FAKE_CLAUDE_USAGE_BANNER") == "1":
                    print("\nYou've used 75% of your weekly limit · resets 3am (America/Denver)", flush=True)
                time.sleep(float(os.environ.get("FAKE_CLAUDE_ANSWER_DELAY", "1.5")))
                if os.environ.get("FAKE_CLAUDE_LONG_ALT_SCREEN") == "1":
                    body = "\n".join(f"Detailed review line {index:03d}" for index in range(1, 101))
                    answer = f"{marker}\nVERDICT: PLAN_NEEDS_REVISION\n{body}\n{sentinel}\nCLAUDE_REVIEW_FINAL_SENTINEL:{sentinel}"
                    persist_session_answer(session_id, answer)
                    print("\x1b[?1049h\x1b[2J\x1b[H", end="")
                    print(f"{answer}\n❯ ", flush=True)
                else:
                    review_body = "Fake Claude review body"
                    if os.environ.get("FAKE_CLAUDE_QUOTED_HARD_LIMITS") == "1":
                        review_body = (
                            "Fake Claude review body quoting provider examples:\n"
                            "- You've hit your session limit\n"
                            "- You've hit your weekly rate limit"
                        )
                    answer = f"{marker}\nVERDICT: PASS_SCOPED\n{review_body}\n{sentinel}\nCLAUDE_REVIEW_FINAL_SENTINEL:{sentinel}"
                    persist_session_answer(session_id, answer)
                    print(f"\n✻ Cooked for 0s\n{marker}\nVERDICT: PASS_SCOPED\n{review_body}\n{sentinel}\n❯ ", flush=True)
                buf = ""
    finally:
        restore_tty(old_tty)


def main() -> int:
    argv_file = os.environ.get("FAKE_CLAUDE_ARGV_FILE")
    if argv_file:
        with open(argv_file, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(sys.argv[1:]) + "\n")
    if len(sys.argv) >= 3 and sys.argv[1:] == ["auth", "status"]:
        return auth_status()
    return interactive()


if __name__ == "__main__":
    raise SystemExit(main())
