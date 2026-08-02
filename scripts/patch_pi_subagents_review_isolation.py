#!/usr/bin/env python3
"""Make repo-owned review personas explicitly disable worktree isolation."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PACKAGE = Path("npm/node_modules/@tintinweb/pi-subagents")
REQUIRED_PRECEDENCE = {
    "src/invocation-config.ts": "isolation: agentConfig?.isolation ?? params.isolation,",
    "dist/invocation-config.js": "isolation: agentConfig?.isolation ?? params.isolation,",
}
REPLACEMENTS = {
    "src/types.ts": (
        'export type IsolationMode = "worktree";',
        'export type IsolationMode = "worktree" | "none";',
    ),
    "dist/types.d.ts": (
        'export type IsolationMode = "worktree";',
        'export type IsolationMode = "worktree" | "none";',
    ),
    "src/custom-agents.ts": (
        'isolation: fm.isolation === "worktree" ? "worktree" : undefined,',
        'isolation: fm.isolation === "worktree" || fm.isolation === "none" ? fm.isolation : undefined,',
    ),
    "dist/custom-agents.js": (
        'isolation: fm.isolation === "worktree" ? "worktree" : undefined,',
        'isolation: fm.isolation === "worktree" || fm.isolation === "none" ? fm.isolation : undefined,',
    ),
}


def main() -> int:
    agent_dir = Path(
        os.environ.get("PI_CODING_AGENT_DIR", Path.home() / ".pi" / "agent")
    ).expanduser()
    package = agent_dir / PACKAGE
    if not package.is_dir():
        print(
            f"pi-subagents patch refused: required package not found at {package}",
            file=sys.stderr,
        )
        return 1

    for relative, required in REQUIRED_PRECEDENCE.items():
        target = package / relative
        if not target.is_file() or required not in target.read_text(encoding="utf-8"):
            print(
                f"pi-subagents patch refused: agent-config isolation precedence missing in {target}",
                file=sys.stderr,
            )
            return 1

    updates = []
    for relative, (old, new) in REPLACEMENTS.items():
        target = package / relative
        if not target.is_file():
            print(f"pi-subagents patch refused: missing {target}", file=sys.stderr)
            return 1
        source = target.read_text(encoding="utf-8")
        if new in source:
            continue
        if old not in source:
            print(
                f"pi-subagents patch refused: expected upstream text not found in {target}",
                file=sys.stderr,
            )
            return 1
        updates.append((target, source.replace(old, new, 1)))

    for target, replacement in updates:
        target.write_text(replacement, encoding="utf-8")

    if updates:
        print("patched pi-subagents to support authoritative isolation: none")
    else:
        print("pi-subagents authoritative isolation: none already present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
