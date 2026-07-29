#!/usr/bin/env python3
"""Disable pi-cursor-sdk's interactive question bridge by default."""

from __future__ import annotations

import os
import sys
from pathlib import Path

OLD = "return parseEnvBoolean(env[CURSOR_ASK_QUESTION_ENV], true);"
NEW = "return parseEnvBoolean(env[CURSOR_ASK_QUESTION_ENV], false);"


def package_path(agent_dir: Path) -> Path:
    return agent_dir / "npm" / "node_modules" / "pi-cursor-sdk" / "src" / "cursor-question-tool.ts"


def main(arguments: list[str]) -> int:
    if arguments not in ([], ["--check"]):
        print("usage: patch_pi_cursor_sdk.py [--check]", file=sys.stderr)
        return 2
    check_only = arguments == ["--check"]

    agent_dir = Path(os.environ.get("PI_CODING_AGENT_DIR", Path.home() / ".pi" / "agent")).expanduser()
    target = package_path(agent_dir)
    if not target.is_file():
        print(f"pi-cursor-sdk question-tool patch skipped: package not found at {target}")
        return 0

    source = target.read_text(encoding="utf-8")
    if NEW in source:
        print(f"pi-cursor-sdk interactive question bridge disabled by default: {target}")
        return 0
    if check_only:
        print(
            "pi-cursor-sdk verification failed: interactive question bridge is not disabled by default",
            file=sys.stderr,
        )
        return 1
    if OLD not in source:
        print(
            f"pi-cursor-sdk patch refused: expected upstream default not found in {target}",
            file=sys.stderr,
        )
        return 1

    target.write_text(source.replace(OLD, NEW, 1), encoding="utf-8")
    print(f"disabled pi-cursor-sdk interactive question bridge by default: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
