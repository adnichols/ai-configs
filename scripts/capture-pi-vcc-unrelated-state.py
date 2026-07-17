#!/usr/bin/env python3
"""Capture deterministic hashes for Pi agent state unrelated to pi-vcc."""

import argparse
import hashlib
import json
import os
import stat
from pathlib import Path

from pi_vcc_registration import is_pi_vcc_source, package_source


# These surfaces are runtime activity, not installer-managed configuration.
# Excluding them keeps the manifest attributable to --pi-vcc even while other
# Pi sessions, review subprocesses, and status extensions are active.
VOLATILE_TOP_LEVEL = {
    ".update-check",
    "cache",
    "messenger",
    "pi-vcc.log.jsonl",
    "powerline-footer",
    "sessions",
}


def normalized_settings(path, stable):
    data = json.loads(path.read_text()) if path.exists() else {}
    if not isinstance(data, dict):
        raise ValueError("settings.json must contain a JSON object")
    packages = data.get("packages")
    if isinstance(packages, list):
        packages = [
            item for item in packages
            if not is_pi_vcc_source(package_source(item), stable)
        ]
        # Canonicalize managed-only installs: missing packages and empty filtered
        # packages must hash identically so adding only pi-vcc is not "unrelated".
        if packages:
            data["packages"] = packages
        else:
            data.pop("packages", None)
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode()


def capture(agent_dir):
    stable = agent_dir / "local-packages" / "ai-configs" / "pi-vcc"
    settings = agent_dir / "settings.json"
    files = {}
    if agent_dir.exists():
        for root, directories, names in os.walk(agent_dir, followlinks=False):
            current = Path(root)
            real_directories = []
            for name in sorted(directories):
                path = current / name
                if current == agent_dir and name in VOLATILE_TOP_LEVEL:
                    continue
                if path == stable:
                    continue
                if path.is_symlink():
                    relative = path.relative_to(agent_dir).as_posix()
                    files[relative] = hashlib.sha256(os.readlink(path).encode()).hexdigest()
                else:
                    real_directories.append(name)
            directories[:] = real_directories
            for name in sorted(names):
                path = current / name
                if current == agent_dir and name in VOLATILE_TOP_LEVEL:
                    continue
                if path == settings:
                    continue
                relative = path.relative_to(agent_dir).as_posix()
                mode = path.lstat().st_mode
                if stat.S_ISLNK(mode):
                    payload = os.readlink(path).encode()
                elif stat.S_ISREG(mode):
                    payload = path.read_bytes()
                else:
                    raise ValueError(f"unsupported special entry: {path}")
                files[relative] = hashlib.sha256(payload).hexdigest()
    normalized = normalized_settings(settings, stable)
    return {
        "files": files,
        "normalizedSettingsHash": hashlib.sha256(normalized).hexdigest(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    agent_dir = Path(os.environ.get("PI_CODING_AGENT_DIR", Path.home() / ".pi" / "agent")).expanduser().absolute()
    result = json.dumps(capture(agent_dir), indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(result)


if __name__ == "__main__":
    main()
