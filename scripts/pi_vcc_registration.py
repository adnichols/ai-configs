#!/usr/bin/env python3
"""Classify pi-vcc package registrations without substring matching."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

PACKAGE_NAMES = {"@adnichols/pi-vcc", "@sting8k/pi-vcc"}
NPM_PATTERN = re.compile(r"^npm:(?:@adnichols/pi-vcc|@sting8k/pi-vcc)(?:@[^/]*)?$")
REPO_PATTERN = re.compile(
    r"^(?:git:|github:|https?://|ssh://|git@)?(?:github\.com[:/])?(?:adnichols|sting8k)/pi-vcc(?:\.git)?(?:#.*)?$",
    re.IGNORECASE,
)


def package_source(item):
    if isinstance(item, dict):
        return item.get("source")
    return item if isinstance(item, str) else None


def _local_source_path(value: str, stable_path: Path) -> Path:
    expanded = Path(os.path.expanduser(value))
    try:
        agent_dir = stable_path.absolute().parents[2]
    except IndexError:
        agent_dir = stable_path.absolute().parent
    return expanded.absolute() if expanded.is_absolute() else (agent_dir / expanded).absolute()


def is_pi_vcc_source(value: object, stable_path: Path) -> bool:
    if not isinstance(value, str):
        return False
    if NPM_PATTERN.fullmatch(value) or REPO_PATTERN.fullmatch(value):
        return True
    if value.startswith(("npm:", "git:", "http:", "https:", "github:", "ssh:")):
        return False
    candidate = _local_source_path(value, stable_path)
    try:
        if candidate.resolve(strict=False) == stable_path.resolve(strict=False):
            return True
        manifest = candidate / "package.json"
        if manifest.is_file():
            data = json.loads(manifest.read_text(encoding="utf-8"))
            return data.get("name") in PACKAGE_NAMES
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    return False


def registration_counts(packages: object, stable_path: Path) -> tuple[int, int]:
    values = packages if isinstance(packages, list) else []
    stable = stable_path.resolve(strict=False)
    stable_count = 0
    total_count = 0
    for item in values:
        value = package_source(item)
        if is_pi_vcc_source(value, stable_path):
            total_count += 1
        if isinstance(value, str) and not value.startswith(("npm:", "git:", "http:", "https:", "github:", "ssh:")):
            if _local_source_path(value, stable_path).resolve(strict=False) == stable:
                stable_count += 1
    return stable_count, total_count
