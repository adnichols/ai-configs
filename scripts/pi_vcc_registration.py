#!/usr/bin/env python3
"""Classify pi-vcc package registrations without substring matching."""

from __future__ import annotations

import json
import os
import re
import subprocess
from functools import lru_cache
from pathlib import Path

PACKAGE_NAMES = {"@adnichols/pi-vcc", "@sting8k/pi-vcc"}
OFFICIAL_REPO_PATHS = {"adnichols/pi-vcc", "sting8k/pi-vcc"}
NPM_NAME_PATTERN = re.compile(r"^(?:@adnichols/pi-vcc|@sting8k/pi-vcc)(?:@[^/]*)?$")
_PARSE_GIT_URL_JS = r"""
import { createRequire } from "module";
const require = createRequire(process.argv[1] + "/");
const { parseGitUrl } = require(process.argv[1] + "/dist/utils/git.js");
const source = process.argv[2] ?? "";
const parsed = parseGitUrl(source);
if (!parsed) {
  process.stdout.write("null");
} else {
  process.stdout.write(JSON.stringify({
    host: parsed.host || "",
    path: parsed.path || "",
  }));
}
"""


class PiGitUrlParserUnavailable(RuntimeError):
    """Raised when Pi's parseGitUrl cannot be loaded or executed."""


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


def _validated_package_root(root: Path) -> Path | None:
    manifest = root / "package.json"
    git_helper = root / "dist" / "utils" / "git.js"
    if not manifest.is_file() or not git_helper.is_file():
        return None
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if data.get("name") != "@earendil-works/pi-coding-agent":
        return None
    return root


def _package_root_from_path(path: Path) -> Path | None:
    try:
        real = path if path.is_absolute() else path.absolute()
        real = Path(os.path.realpath(real))
    except OSError:
        return None
    # Accept the package root itself, a nested path, or dist/cli.js.
    candidates = [real]
    if real.name == "cli.js" and real.parent.name == "dist":
        candidates.append(real.parent.parent)
    candidates.extend([real.parent, *real.parents])
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        validated = _validated_package_root(candidate)
        if validated is not None:
            return validated
    return None


@lru_cache(maxsize=1)
def _pi_package_root() -> Path | None:
    """Locate the installed @earendil-works/pi-coding-agent package root."""
    override = os.environ.get("PI_CODING_AGENT_PACKAGE_ROOT")
    if override:
        root = _package_root_from_path(Path(override).expanduser())
        if root is not None:
            return root
        # Explicit override that does not resolve is a hard failure later.
        return None

    # Walk every PATH entry. Test fixtures often inject a fake `pi` ahead of the
    # real binary, so skip non-Pi entries instead of trusting the first match.
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        if not directory:
            continue
        candidate = Path(directory) / "pi"
        if not candidate.exists() and not candidate.is_symlink():
            continue
        root = _package_root_from_path(candidate)
        if root is not None:
            return root

    # Fallback for hosts where `pi` is not on PATH but the package is global.
    try:
        completed = subprocess.run(
            ["npm", "root", "-g"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        completed = None
    if completed is not None and completed.returncode == 0:
        root = Path(completed.stdout.strip()) / "@earendil-works" / "pi-coding-agent"
        resolved = _validated_package_root(root)
        if resolved is not None:
            return resolved
    return None


def require_pi_package_root() -> Path:
    """Return the Pi package root or fail closed when it cannot be resolved."""
    if os.environ.get("PI_CODING_AGENT_PACKAGE_ROOT"):
        root = _pi_package_root()
        if root is None:
            raise PiGitUrlParserUnavailable(
                "PI_CODING_AGENT_PACKAGE_ROOT does not point at a valid "
                "@earendil-works/pi-coding-agent package"
            )
        return root
    root = _pi_package_root()
    if root is None:
        raise PiGitUrlParserUnavailable(
            "unable to locate @earendil-works/pi-coding-agent for parseGitUrl"
        )
    return root


@lru_cache(maxsize=512)
def _parse_git_url(source: str) -> dict | None:
    """Parse a source with Pi's parseGitUrl.

    Returns None only when Pi itself does not treat the source as a Git URL.
    Raises PiGitUrlParserUnavailable when the parser cannot be loaded or run.
    """
    root = require_pi_package_root()
    try:
        completed = subprocess.run(
            ["node", "--input-type=module", "-e", _PARSE_GIT_URL_JS, str(root), source],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise PiGitUrlParserUnavailable(
            f"failed to execute Pi parseGitUrl: {exc}"
        ) from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise PiGitUrlParserUnavailable(
            f"Pi parseGitUrl failed with exit {completed.returncode}: {detail}"
        )
    payload = completed.stdout.strip()
    if not payload or payload == "null":
        return None
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise PiGitUrlParserUnavailable(
            f"Pi parseGitUrl returned non-JSON output: {payload!r}"
        ) from exc
    if not isinstance(data, dict):
        raise PiGitUrlParserUnavailable(
            f"Pi parseGitUrl returned unexpected payload: {payload!r}"
        )
    return data


def is_official_npm_pi_vcc_source(value: str) -> bool:
    """Match Pi's npm: handling: requires a literal npm: prefix before any trim."""
    if not value.startswith("npm:"):
        return False
    # Pi does: source.slice("npm:".length).trim()
    spec = value[4:].strip()
    return bool(NPM_NAME_PATTERN.fullmatch(spec))


def is_official_pi_vcc_repo_source(value: str) -> bool:
    """Return True only for sources Pi itself parses as official GitHub pi-vcc.

    Path comparison is exact against Pi's returned path. No extra slash collapsing
    or `.git` stripping is applied on top of Pi's own normalization.
    """
    if not isinstance(value, str) or value == "":
        return False
    parsed = _parse_git_url(value)
    if not parsed:
        return False
    host = str(parsed.get("host") or "").lower()
    path = str(parsed.get("path") or "")
    # Host comparison is case-insensitive; path must match Pi's returned path exactly.
    return host == "github.com" and path in OFFICIAL_REPO_PATHS


def is_pi_vcc_source(value: object, stable_path: Path) -> bool:
    if not isinstance(value, str):
        return False
    # Pi checks npm: before any whitespace normalization. Do not strip first.
    if is_official_npm_pi_vcc_source(value):
        return True
    # Git classification uses Pi's parser on the raw source string.
    if is_official_pi_vcc_repo_source(value):
        return True
    # Remote-looking prefixes that failed Git classification are not local pi-vcc.
    if value.startswith(("npm:", "git:", "http:", "https:", "github:", "ssh:")):
        return False
    # Leading/trailing whitespace makes npm:/git: fall through as local in Pi; keep
    # local resolution on the raw string as well.
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
        if isinstance(value, str):
            candidate = value
            if not candidate.startswith(("npm:", "git:", "http:", "https:", "github:", "ssh:")):
                if _local_source_path(candidate, stable_path).resolve(strict=False) == stable:
                    stable_count += 1
    return stable_count, total_count
