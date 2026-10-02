#!/usr/bin/env python3
"""Copy images the operator pasted into this conversation into a bugbash evidence directory.

Pasted screenshots live only inside the driving session's transcript. Worker agents in
other worktrees cannot see them, so the bugbash driver exports them to files and passes
absolute paths in each handoff.

Supports OMP sessions (~/.omp/agent/sessions, images stored as blob:sha256 refs in
~/.omp/agent/blobs) and Codex rollouts (~/.codex/sessions, images inlined as data URLs).
Without --session, the newest top-level session whose recorded cwd equals --cwd is used.

Idempotent: images already listed in <out>/manifest.jsonl are skipped. Each newly
exported image is printed as one JSON line so the driver can attach it to an issue.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
import time
from pathlib import Path

HOME = Path.home()
OMP_SESSIONS = HOME / ".omp/agent/sessions"
OMP_BLOBS = HOME / ".omp/agent/blobs"
CODEX_SESSIONS = HOME / ".codex/sessions"
CODEX_LOOKBACK_SECONDS = 14 * 24 * 3600
EXT = {"image/png": "png", "image/jpeg": "jpg", "image/jpg": "jpg", "image/webp": "webp", "image/gif": "gif"}


def session_cwd(path: Path) -> str | None:
    """Return the cwd recorded in the first few lines of an OMP or Codex session file."""
    try:
        with path.open() as handle:
            for _ in range(4):
                line = handle.readline()
                if not line:
                    break
                record = json.loads(line)
                if record.get("type") == "session":
                    return record.get("cwd")
                if record.get("type") == "session_meta":
                    return record.get("payload", {}).get("cwd")
    except (OSError, json.JSONDecodeError):
        return None
    return None


def find_session(cwd: str) -> Path:
    target = os.path.realpath(cwd)
    candidates: list[Path] = []
    if OMP_SESSIONS.is_dir():
        candidates += OMP_SESSIONS.glob("*/*.jsonl")
    if CODEX_SESSIONS.is_dir():
        cutoff = time.time() - CODEX_LOOKBACK_SECONDS
        candidates += (p for p in CODEX_SESSIONS.rglob("rollout-*.jsonl") if p.stat().st_mtime >= cutoff)
    matches = [p for p in candidates if (c := session_cwd(p)) and os.path.realpath(c) == target]
    if not matches:
        sys.exit(f"no OMP or Codex session found for cwd {target}; pass --session")
    return max(matches, key=lambda p: p.stat().st_mtime)


def user_images(path: Path):
    """Yield (message_id, timestamp, text, mime, bytes_or_blob_path) for user-pasted images."""
    with path.open() as handle:
        for line in handle:
            if '"image' not in line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("type") == "message":  # OMP
                message = record.get("message", {})
                if message.get("role") != "user":
                    continue
                parts = message.get("content")
                if not isinstance(parts, list):
                    continue
                text = " ".join(p.get("text", "") for p in parts if p.get("type") == "text")
                for part in parts:
                    data = part.get("data", "")
                    if part.get("type") == "image" and data.startswith("blob:sha256:"):
                        sha = data.removeprefix("blob:sha256:")
                        yield record.get("id"), record.get("timestamp"), text, part.get("mimeType"), ("blob", sha)
            elif record.get("type") == "response_item":  # Codex
                payload = record.get("payload", {})
                if payload.get("type") != "message" or payload.get("role") != "user":
                    continue
                parts = payload.get("content")
                if not isinstance(parts, list):
                    continue
                text = " ".join(p.get("text", "") for p in parts if p.get("type") == "input_text")
                for part in parts:
                    url = part.get("image_url", "")
                    if part.get("type") == "input_image" and url.startswith("data:"):
                        header, _, encoded = url.partition(",")
                        mime = header.removeprefix("data:").split(";")[0]
                        yield None, record.get("timestamp"), text, mime, ("bytes", base64.b64decode(encoded))


def read_blob(sha: str) -> bytes | None:
    for candidate in [OMP_BLOBS / sha, *OMP_BLOBS.glob(f"{sha}.*")]:
        if candidate.is_file():
            return candidate.read_bytes()
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", required=True, type=Path, help="bugbash images directory")
    parser.add_argument("--session", type=Path, help="session file; default: newest session for --cwd")
    parser.add_argument("--cwd", default=os.getcwd(), help="driving session cwd (default: current directory)")
    parser.add_argument("--since", help="only export images from messages at or after this ISO timestamp")
    args = parser.parse_args()

    session = args.session or find_session(args.cwd)
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = args.out / "manifest.jsonl"
    known = set()
    if manifest.exists():
        known = {json.loads(line)["sha256"] for line in manifest.read_text().splitlines() if line.strip()}

    exported = 0
    with manifest.open("a") as out:
        for message_id, timestamp, text, mime, source in user_images(session):
            if args.since and timestamp and timestamp < args.since:
                continue
            kind, value = source
            data = read_blob(value) if kind == "blob" else value
            if data is None:
                print(json.dumps({"error": "blob missing", "blob": value, "timestamp": timestamp}), file=sys.stderr)
                continue
            sha = hashlib.sha256(data).hexdigest()
            if sha in known:
                continue
            dest = args.out / f"{sha[:12]}.{EXT.get(mime or '', 'bin')}"
            dest.write_bytes(data)
            entry = {
                "sha256": sha,
                "file": str(dest.resolve()),
                "mime": mime,
                "timestamp": timestamp,
                "message_id": message_id,
                "text": text.strip()[:400],
                "session": str(session),
            }
            out.write(json.dumps(entry) + "\n")
            print(json.dumps(entry))
            known.add(sha)
            exported += 1
    print(f"exported {exported} new image(s) from {session}", file=sys.stderr)


if __name__ == "__main__":
    main()
