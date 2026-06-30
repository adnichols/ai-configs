#!/usr/bin/env python3
"""Deprecated compatibility wrapper for the Heddle main release watcher.

The canonical watcher lives in the repository at:
  /Users/anichols/code/heddle-release/scripts/release/main-release-watch.py

Keep this profile-local path as a thin exec wrapper only so any stale cron prompt,
manually-entered command, or copied runbook cannot keep old release semantics.
The repo script releases the version already merged to main; it does not bump or
commit a new version on main.
"""
from __future__ import annotations

import os
import pathlib
import sys

CANONICAL_WATCHER = pathlib.Path(
    "/Users/anichols/code/heddle-release/scripts/release/main-release-watch.py"
)


def main() -> None:
    if not CANONICAL_WATCHER.exists():
        print(
            f"Canonical Heddle release watcher is missing: {CANONICAL_WATCHER}",
            file=sys.stderr,
        )
        raise SystemExit(2)

    env = os.environ.copy()
    env.setdefault("HOME", "/Users/anichols")
    env.setdefault("HEDDLE_RELEASE_AUTH_HOME", "/Users/anichols")
    os.execve(str(CANONICAL_WATCHER), [str(CANONICAL_WATCHER), *sys.argv[1:]], env)


if __name__ == "__main__":
    main()
