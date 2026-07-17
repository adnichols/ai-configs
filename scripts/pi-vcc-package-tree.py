#!/usr/bin/env python3
"""Compute the canonical identity of an admissible pi-vcc package tree."""

from __future__ import annotations

import argparse
import hashlib
import os
import stat
import sys
from pathlib import Path


class TreeIdentityError(ValueError):
    """The package tree contains an unsupported or unreadable entry."""


def _field(digest: "hashlib._Hash", value: bytes) -> None:
    digest.update(len(value).to_bytes(8, "big"))
    digest.update(value)


def package_tree_identity(root: Path) -> str:
    digest = hashlib.sha256()

    def visit(path: Path, relative: bytes) -> None:
        try:
            metadata = path.lstat()
        except OSError as exc:
            raise TreeIdentityError(f"cannot inspect {path}: {exc}") from exc
        if stat.S_ISLNK(metadata.st_mode):
            raise TreeIdentityError(f"symlinks are not allowed in package trees: {path}")
        if stat.S_ISDIR(metadata.st_mode):
            entry_type = b"directory"
            canonical_mode = b"040000"
        elif stat.S_ISREG(metadata.st_mode):
            entry_type = b"file"
            canonical_mode = b"100755" if stat.S_IMODE(metadata.st_mode) & 0o111 else b"100644"
        else:
            raise TreeIdentityError(f"special entries are not allowed in package trees: {path}")
        _field(digest, entry_type)
        _field(digest, relative)
        # Git preserves the executable class, but checkout umasks can add group
        # write bits (for example 0644 on macOS versus 0664 on Linux). Hash the
        # portable repository mode so one commit has one cross-host identity.
        _field(digest, canonical_mode)
        if entry_type == b"file":
            _field(digest, metadata.st_size.to_bytes(8, "big"))
            try:
                with path.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(chunk)
            except OSError as exc:
                raise TreeIdentityError(f"cannot read {path}: {exc}") from exc
            return
        try:
            with os.scandir(path) as entries:
                children = sorted(entries, key=lambda item: os.fsencode(item.name))
        except OSError as exc:
            raise TreeIdentityError(f"cannot list {path}: {exc}") from exc
        for child in children:
            name = os.fsencode(child.name)
            visit(Path(child.path), name if relative == b"." else relative + b"/" + name)

    visit(root, b".")
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    try:
        print(package_tree_identity(args.path))
    except TreeIdentityError as exc:
        print(f"package tree identity error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
