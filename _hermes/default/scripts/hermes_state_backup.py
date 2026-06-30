#!/usr/bin/env python3
"""Lean Hermes home backup for config + memory preservation.

Backs up only the parts of HERMES_HOME that are painful to recreate after a
fresh install, excluding the local repo checkout, virtualenv, caches, logs,
and other reproducible artifacts.

Designed to be cron-safe:
- non-interactive
- writes a timestamped tar.gz archive atomically
- prunes old backups optionally
- exits nonzero on failure
- can notify a Discord or Telegram home channel on failure using tokens already
  stored in the backed-up .env file
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import sys
import tarfile
import tempfile
import textwrap
import traceback
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

DEFAULT_INCLUDE_FILES = [
    ".env",
    "config.yaml",
    "auth.json",
    "SOUL.md",
    "channel_directory.json",
    "discord_threads.json",
    "gateway_state.json",
    "processes.json",
]

DEFAULT_INCLUDE_GLOBS = [
    "state.db",
    "state.db-wal",
]

DEFAULT_INCLUDE_DIRS = [
    "cron",
    "hooks",
    "memories",
    "pairing",
    "profiles",
    "scripts",
    "sessions",
    "skills",
    "state",
    "watchers",
]

# Files/dirs intentionally excluded because they are reproducible, bulky, or cache-like.
EXCLUDED_NOTES = {
    "hermes-agent": "local repo checkout; reinstall/re-clone instead",
    "bin": "generated helper binaries; reinstall instead",
    "cache": "cache",
    "sandboxes": "ephemeral execution environments",
    "audio_cache": "derived audio outputs",
    "image_cache": "derived image outputs",
    "logs": "rebuildable logs",
    ".hermes_history": "shell/chat history, not required for config+memory restore",
    ".update_check": "ephemeral metadata",
    ".skills_prompt_snapshot.json": "rebuildable cache",
    "state.db-shm": "sqlite shared-memory file; transient when DB is closed",
    "whatsapp": "platform-specific working state; excluded from lean backup by default",
    "cron/output": "cron delivery logs; useful for audit but not required for config+memory restore",
}


@dataclass
class BackupResult:
    archive_path: Path
    bytes_written: int
    included_entries: list[str]
    pruned_archives: list[Path]


def parse_args() -> argparse.Namespace:
    home_default = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")).expanduser()
    parser = argparse.ArgumentParser(
        description="Create a lean Hermes home backup with optional failure notifications.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """
            Examples:
              hermes_state_backup.py
              hermes_state_backup.py --destination ~/Backups/hermes-state --keep 14
              hermes_state_backup.py --notify auto
            """
        ),
    )
    parser.add_argument("--hermes-home", default=str(home_default), help="Hermes home directory (default: %(default)s)")
    parser.add_argument(
        "--destination",
        default=str(Path.home() / "Backups" / "hermes-state"),
        help="Directory where backup archives are written (default: %(default)s)",
    )
    parser.add_argument("--prefix", default="hermes-state", help="Archive filename prefix (default: %(default)s)")
    parser.add_argument("--keep", type=int, default=14, help="How many archives to retain in destination (default: %(default)s)")
    parser.add_argument(
        "--notify",
        choices=("auto", "discord", "telegram", "none"),
        default="auto",
        help="Notify on failure using platform credentials from .env (default: %(default)s)",
    )
    parser.add_argument(
        "--notify-success",
        action="store_true",
        help="Also send a success notification (off by default; useful while validating cron wiring)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be backed up without writing an archive",
    )
    return parser.parse_args()


def load_env_file(env_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not env_path.exists():
        return values
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if value and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key] = value
    return values


def expand_include_entries(hermes_home: Path) -> list[Path]:
    entries: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path) -> None:
        resolved = path
        if resolved.exists() and resolved not in seen:
            seen.add(resolved)
            entries.append(resolved)

    for rel in DEFAULT_INCLUDE_FILES:
        add(hermes_home / rel)
    for rel in DEFAULT_INCLUDE_DIRS:
        add(hermes_home / rel)
    for pattern in DEFAULT_INCLUDE_GLOBS:
        for match in sorted(hermes_home.glob(pattern)):
            add(match)

    return sorted(entries, key=lambda p: p.relative_to(hermes_home).as_posix())


def build_manifest(hermes_home: Path, destination: Path, entries: Iterable[Path], archive_name: str) -> dict:
    rel_entries = [p.relative_to(hermes_home).as_posix() for p in entries]
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "hermes_home": str(hermes_home),
        "destination": str(destination),
        "archive_name": archive_name,
        "include_files": DEFAULT_INCLUDE_FILES,
        "include_globs": DEFAULT_INCLUDE_GLOBS,
        "include_dirs": DEFAULT_INCLUDE_DIRS,
        "excluded_notes": EXCLUDED_NOTES,
        "included_entries": rel_entries,
        "script": "hermes_state_backup.py",
        "version": 1,
    }


def make_tar_filter() -> Callable[[tarfile.TarInfo], tarfile.TarInfo | None]:
    """Exclude bulky/rebuildable state at any depth in the archive.

    Top-level include entries can contain nested Hermes profiles. Applying the
    lean exclusions only at the active profile root lets nested profile cache,
    logs, and cron output dominate the backup, so match path components rather
    than only archive-root prefixes.
    """
    excluded_dir_names = {
        "hermes-agent",
        "bin",
        "cache",
        "sandboxes",
        "audio_cache",
        "image_cache",
        "logs",
        "__pycache__",
        "home",
        "Library",
        "node_modules",
        ".git",
        ".npm",
        ".cargo",
        ".codex",
    }
    excluded_file_names = {
        ".hermes_history",
        ".update_check",
        ".skills_prompt_snapshot.json",
        "state.db-shm",
    }

    def _filter(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo | None:
        name = tarinfo.name.rstrip("/")
        parts = [part for part in name.split("/") if part]
        if not parts:
            return tarinfo
        if parts[-1] in excluded_file_names:
            return None
        if any(part in excluded_dir_names for part in parts):
            return None
        for idx, part in enumerate(parts[:-1]):
            if part == "cron" and parts[idx + 1] == "output":
                return None
        return tarinfo

    return _filter


def create_archive(hermes_home: Path, destination: Path, prefix: str, entries: list[Path], dry_run: bool) -> BackupResult:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive_name = f"{prefix}-{timestamp}.tar.gz"
    archive_path = destination / archive_name

    if dry_run:
        return BackupResult(archive_path=archive_path, bytes_written=0, included_entries=[p.relative_to(hermes_home).as_posix() for p in entries], pruned_archives=[])

    destination.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{prefix}-", suffix=".tar.gz", dir=str(destination))
    os.close(fd)
    tmp_path = Path(tmp_name)

    try:
        with tarfile.open(tmp_path, mode="w:gz", format=tarfile.PAX_FORMAT) as tf:
            tar_filter = make_tar_filter()
            for path in entries:
                arcname = path.relative_to(hermes_home).as_posix()
                tf.add(path, arcname=arcname, recursive=True, filter=tar_filter)

            manifest = build_manifest(hermes_home, destination, entries, archive_name)
            payload = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
            info = tarfile.TarInfo(name="backup-manifest.json")
            info.size = len(payload)
            info.mtime = int(datetime.now().timestamp())
            tf.addfile(info, io.BytesIO(payload))

        tmp_path.replace(archive_path)
        size = archive_path.stat().st_size
        return BackupResult(
            archive_path=archive_path,
            bytes_written=size,
            included_entries=[p.relative_to(hermes_home).as_posix() for p in entries],
            pruned_archives=[],
        )
    except Exception:
        with contextlib.suppress(FileNotFoundError):
            tmp_path.unlink()
        raise


def prune_old_archives(destination: Path, prefix: str, keep: int) -> list[Path]:
    if keep < 1 or not destination.exists():
        return []
    archives = sorted(destination.glob(f"{prefix}-*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
    doomed = archives[keep:]
    pruned: list[Path] = []
    for path in doomed:
        path.unlink()
        pruned.append(path)
    return pruned


def human_size(num_bytes: int) -> str:
    value = float(num_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024.0 or unit == "TB":
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{num_bytes} B"


def send_notification(env: dict[str, str], mode: str, message: str) -> str:
    if mode == "none":
        return "notifications disabled"
    if mode in ("auto", "discord"):
        sent = send_discord(env, message)
        if sent:
            return sent
        if mode == "discord":
            raise RuntimeError("Discord notification requested but DISCORD_BOT_TOKEN or DISCORD_HOME_CHANNEL is not configured")
    if mode in ("auto", "telegram"):
        sent = send_telegram(env, message)
        if sent:
            return sent
        if mode == "telegram":
            raise RuntimeError("Telegram notification requested but TELEGRAM_BOT_TOKEN or TELEGRAM_HOME_CHANNEL is not configured")
    if mode == "auto":
        raise RuntimeError("No usable notification target found in .env (checked Discord and Telegram home channels)")
    raise RuntimeError(f"Unsupported notify mode: {mode}")


def send_discord(env: dict[str, str], message: str) -> str | None:
    token = env.get("DISCORD_BOT_TOKEN") or os.environ.get("DISCORD_BOT_TOKEN")
    channel_id = env.get("DISCORD_HOME_CHANNEL") or os.environ.get("DISCORD_HOME_CHANNEL")
    if not token or not channel_id:
        return None
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    data = json.dumps({"content": message[:1900]}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "hermes-home-backup/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        if resp.status // 100 != 2:
            raise RuntimeError(f"Discord notification failed with HTTP {resp.status}")
    return "discord"


def send_telegram(env: dict[str, str], message: str) -> str | None:
    token = env.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = env.get("TELEGRAM_HOME_CHANNEL") or os.environ.get("TELEGRAM_HOME_CHANNEL")
    if not token or not chat_id:
        return None
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = urllib.parse.urlencode({"chat_id": chat_id, "text": message[:4000]}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    with urllib.request.urlopen(req, timeout=20) as resp:
        if resp.status // 100 != 2:
            raise RuntimeError(f"Telegram notification failed with HTTP {resp.status}")
    return "telegram"


def main() -> int:
    args = parse_args()
    hermes_home = Path(args.hermes_home).expanduser().resolve()
    destination = Path(args.destination).expanduser().resolve()
    env = load_env_file(hermes_home / ".env")

    if not hermes_home.exists():
        print(f"ERROR: Hermes home does not exist: {hermes_home}", file=sys.stderr)
        return 2
    if destination == hermes_home or destination in [hermes_home / rel for rel in ["scripts", "sessions", "skills", "profiles", "cron"]]:
        print("ERROR: destination must be outside the live Hermes home/state directories", file=sys.stderr)
        return 2
    try:
        destination.relative_to(hermes_home)
        print("ERROR: destination must not live inside Hermes home", file=sys.stderr)
        return 2
    except ValueError:
        pass

    entries = expand_include_entries(hermes_home)
    if not entries:
        print("ERROR: nothing matched the lean backup include list", file=sys.stderr)
        return 2

    try:
        result = create_archive(hermes_home, destination, args.prefix, entries, args.dry_run)
        pruned = [] if args.dry_run else prune_old_archives(destination, args.prefix, args.keep)
        result.pruned_archives = pruned

        summary = {
            "archive": str(result.archive_path),
            "bytes_written": result.bytes_written,
            "human_size": human_size(result.bytes_written),
            "included_entries": result.included_entries,
            "pruned_archives": [str(p) for p in pruned],
            "dry_run": args.dry_run,
        }
        print(json.dumps(summary, indent=2))

        if args.notify_success and not args.dry_run:
            msg = (
                f"✅ Hermes lean backup succeeded\n"
                f"Archive: {result.archive_path.name}\n"
                f"Size: {human_size(result.bytes_written)}\n"
                f"Saved in: {destination}"
            )
            try:
                sent_via = send_notification(env, args.notify, msg)
                print(f"Success notification sent via {sent_via}", file=sys.stderr)
            except Exception as notify_exc:
                print(f"WARNING: backup succeeded but success notification failed: {notify_exc}", file=sys.stderr)
        return 0
    except Exception as exc:
        error_text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        print(error_text, file=sys.stderr)
        msg = (
            f"❌ Hermes lean backup FAILED\n"
            f"Home: {hermes_home}\n"
            f"Destination: {destination}\n"
            f"Error: {exc}"
        )
        try:
            sent_via = send_notification(env, args.notify, msg)
            print(f"Failure notification sent via {sent_via}", file=sys.stderr)
        except Exception as notify_exc:
            print(f"WARNING: failure notification could not be delivered: {notify_exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
