#!/usr/bin/env python3
"""Point the pi-prewalk default execution target at DeepInfra DeepSeek Flash.

pi-prewalk is a one-way plan -> execute switch: a strong model commits to a
plan and seeds the todo list, then the session hands mechanical implementation
off to a fast/cheap model at the first edit/write. The upstream npm package
defaults that execution target to `opencode/glm-5.2`. ai-configs sets the
managed execution default to `deepinfra/deepseek-ai/DeepSeek-V4-Flash-0731`, so
this patch rewrites the package default so an unqualified `pi --prewalk` /
`/prewalk` executes on DeepSeek Flash instead of GLM-5.2.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

OLD = '''/**
 * Default target model when none is given (upstream's `@smol` role has no
 * analogue here). GLM-5.2 on opencode — a fast/cheap implementation model.
 * Falls back to the cheapest available model if this one has no configured key.
 */
const DEFAULT_PREWALK_TARGET = { provider: "opencode", id: "glm-5.2" };'''

NEW = '''/**
 * Default target model when none is given (upstream's `@smol` role has no
 * analogue here). DeepSeek V4 Flash on deepinfra — the ai-configs execution
 * default. Falls back to the cheapest available model if this one has no
 * configured key.
 */
const DEFAULT_PREWALK_TARGET = { provider: "deepinfra", id: "deepseek-ai/DeepSeek-V4-Flash-0731" };'''


def package_path(agent_dir: Path) -> Path:
    return agent_dir / "npm" / "node_modules" / "pi-prewalk" / "extensions" / "prewalk.ts"


def main(arguments: list[str]) -> int:
    if arguments not in ([], ["--check"]):
        print("usage: patch_pi_prewalk_execution_target.py [--check]", file=sys.stderr)
        return 2
    check_only = arguments == ["--check"]

    agent_dir = Path(
        os.environ.get("PI_CODING_AGENT_DIR", os.environ.get("PI_AGENT_DIR", Path.home() / ".pi" / "agent"))
    ).expanduser()
    target = package_path(agent_dir)
    if not target.is_file():
        print(f"pi-prewalk execution-target patch skipped: package not found at {target}")
        return 0

    source = target.read_text(encoding="utf-8")
    if NEW in source:
        print(f"pi-prewalk DeepSeek Flash execution default verified: {target}")
        return 0
    if check_only:
        print(
            f"pi-prewalk verification failed: DeepSeek Flash execution default is absent from {target}",
            file=sys.stderr,
        )
        return 1
    if OLD not in source:
        print(
            f"pi-prewalk patch refused: expected upstream DEFAULT_PREWALK_TARGET block not found in {target}",
            file=sys.stderr,
        )
        return 1

    target.write_text(source.replace(OLD, NEW, 1), encoding="utf-8")
    print(f"patched pi-prewalk to execute on DeepSeek Flash by default: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
