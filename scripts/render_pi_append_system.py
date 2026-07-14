#!/usr/bin/env python3
"""Render Pi's APPEND_SYSTEM.md with traceable ai-configs version metadata."""

from __future__ import annotations

import argparse
import datetime as dt
import subprocess
from pathlib import Path

TOKEN = "{{AI_CONFIGS_VERSION}}"


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=check,
        capture_output=True,
        text=True,
    )


def render(repo: Path, source: Path, target: Path, version_date: str) -> str:
    try:
        commit = git(repo, "rev-parse", "--short=8", "HEAD").stdout.strip()
    except subprocess.CalledProcessError as error:
        raise SystemExit("APPEND_SYSTEM.md installation requires an ai-configs Git checkout with a committed HEAD") from error

    try:
        relative_source = source.resolve().relative_to(repo.resolve())
    except ValueError as error:
        raise SystemExit(f"{source} must be inside the ai-configs repository") from error

    committed = subprocess.run(
        ["git", "-C", str(repo), "show", f"HEAD:{relative_source.as_posix()}"],
        check=False,
        capture_output=True,
    )
    if committed.returncode != 0:
        raise SystemExit(f"{relative_source} must be tracked by Git before installation")

    dirty = source.read_bytes() != committed.stdout
    version = f"{version_date}+{commit}{'-dirty' if dirty else ''}"

    text = source.read_text()
    if text.count(TOKEN) != 1:
        raise SystemExit(f"{source} must contain exactly one {TOKEN} token")

    target.write_text(text.replace(TOKEN, version))
    if TOKEN in target.read_text():
        raise SystemExit("unresolved APPEND_SYSTEM.md version token")
    return version


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--date", default=dt.date.today().isoformat())
    args = parser.parse_args()
    print(render(args.repo, args.source, args.target, args.date))


if __name__ == "__main__":
    main()
