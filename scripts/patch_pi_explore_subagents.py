#!/usr/bin/env python3
"""Keep Pi explore-subagent RPC children from inheriting a Herdr pane identity."""

from __future__ import annotations

import os
import sys
from pathlib import Path

OLD = '''\tconst proc = spawn("pi", args, {
\t\tcwd,
\t\tshell: false,
\t\tdetached: process.platform !== "win32",
\t\tstdio: ["pipe", "pipe", "pipe"],
\t\tenv: { ...process.env, [CHILD_ENV]: "1" },
\t});'''
NEW = '''\t// RPC children are not terminal-pane owners. Do not let their lifecycle
\t// extensions report against the interactive parent pane they inherited.
\tconst childEnv = { ...process.env, [CHILD_ENV]: "1" };
\tfor (const key of [
\t\t"HERDR_ENV",
\t\t"HERDR_SOCKET_PATH",
\t\t"HERDR_WORKSPACE_ID",
\t\t"HERDR_TAB_ID",
\t\t"HERDR_PANE_ID",
\t]) {
\t\tdelete childEnv[key];
\t}

\tconst proc = spawn("pi", args, {
\t\tcwd,
\t\tshell: false,
\t\tdetached: process.platform !== "win32",
\t\tstdio: ["pipe", "pipe", "pipe"],
\t\tenv: childEnv,
\t});'''
def package_path(agent_dir: Path) -> Path:
    return agent_dir / "npm" / "node_modules" / "@howaboua" / "pi-explore-subagents" / "src" / "subagent.ts"


def main(arguments: list[str]) -> int:
    if arguments not in ([], ["--check"]):
        print("usage: patch_pi_explore_subagents.py [--check]", file=sys.stderr)
        return 2
    check_only = arguments == ["--check"]

    agent_dir = Path(
        os.environ.get("PI_CODING_AGENT_DIR", Path.home() / ".pi" / "agent")
    ).expanduser()
    target = package_path(agent_dir)
    if not target.is_file():
        print(f"pi-explore-subagents patch skipped: package not found at {target}")
        return 0

    source = target.read_text(encoding="utf-8")
    if NEW in source:
        print(f"pi-explore-subagents Herdr child-environment isolation verified: {target}")
        return 0
    if check_only:
        print(
            f"pi-explore-subagents verification failed: complete Herdr child-environment isolation is absent from {target}",
            file=sys.stderr,
        )
        return 1
    if OLD not in source:
        print(
            f"pi-explore-subagents patch refused: expected upstream spawn block not found in {target}",
            file=sys.stderr,
        )
        return 1

    target.write_text(source.replace(OLD, NEW, 1), encoding="utf-8")
    print(f"patched pi-explore-subagents to isolate Herdr identity: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
