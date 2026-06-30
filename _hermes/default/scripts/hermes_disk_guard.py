#!/opt/homebrew/bin/python3
"""Monitor disk usage for Hermes backups and notify only on state changes.

Designed for cron. Checks the filesystem that contains the backup destination and
alerts when usage or free space crosses thresholds. Also estimates retained
backup footprint based on the configured backup retention count.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from hermes_state_backup import human_size, load_env_file, send_notification  # noqa: E402


def parse_args() -> argparse.Namespace:
    hermes_home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")).expanduser()
    default_dest = Path.home() / "Backups" / "hermes-state"
    parser = argparse.ArgumentParser(description="Check disk capacity for Hermes backup retention and notify on risk.")
    parser.add_argument("--hermes-home", default=str(hermes_home), help="Hermes home directory (default: %(default)s)")
    parser.add_argument("--backup-destination", default=str(default_dest), help="Backup destination to inspect")
    parser.add_argument("--keep", type=int, default=14, help="Expected retained backup count (default: %(default)s)")
    parser.add_argument("--warn-usage-pct", type=int, default=85, help="Warn when filesystem usage reaches this percent")
    parser.add_argument("--critical-usage-pct", type=int, default=92, help="Critical alert when filesystem usage reaches this percent")
    parser.add_argument("--min-free-gb", type=float, default=50.0, help="Warn when free space drops below this many GiB")
    parser.add_argument("--notify", choices=("auto", "discord", "telegram", "none"), default="auto")
    parser.add_argument(
        "--state-file",
        default=str(hermes_home / "state" / "disk_guard_state.json"),
        help="Where to persist last alert state so cron does not spam",
    )
    return parser.parse_args()


def load_state(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def list_backups(dest: Path) -> list[Path]:
    if not dest.exists():
        return []
    return sorted(dest.glob("hermes-state-*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True)


def assess(backup_dest: Path, keep: int, warn_pct: int, critical_pct: int, min_free_gb: float) -> dict:
    usage = shutil.disk_usage(backup_dest)
    used_pct = (usage.used / usage.total) * 100 if usage.total else 0.0
    free_gib = usage.free / (1024 ** 3)

    backups = list_backups(backup_dest)
    sizes = [p.stat().st_size for p in backups]
    current_backup_bytes = sum(sizes)
    latest_backup_bytes = sizes[0] if sizes else 0
    avg_backup_bytes = int(sum(sizes) / len(sizes)) if sizes else latest_backup_bytes
    projected_retained_bytes = avg_backup_bytes * max(keep, len(sizes) or 1)

    if used_pct >= critical_pct:
        level = "critical"
        reason = f"filesystem usage {used_pct:.1f}% >= {critical_pct}%"
    elif used_pct >= warn_pct:
        level = "warning"
        reason = f"filesystem usage {used_pct:.1f}% >= {warn_pct}%"
    elif free_gib < min_free_gb:
        level = "warning"
        reason = f"free space {free_gib:.1f} GiB < {min_free_gb:.1f} GiB"
    else:
        level = "ok"
        reason = "within thresholds"

    return {
        "level": level,
        "reason": reason,
        "used_pct": round(used_pct, 2),
        "free_gib": round(free_gib, 2),
        "disk_total_bytes": usage.total,
        "disk_used_bytes": usage.used,
        "disk_free_bytes": usage.free,
        "backup_count": len(backups),
        "current_backup_bytes": current_backup_bytes,
        "latest_backup_bytes": latest_backup_bytes,
        "avg_backup_bytes": avg_backup_bytes,
        "projected_retained_bytes": projected_retained_bytes,
        "backup_destination": str(backup_dest),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def build_message(status: dict, recovered: bool = False) -> str:
    if recovered:
        prefix = "✅ Hermes disk monitor recovered"
    elif status["level"] == "critical":
        prefix = "🚨 Hermes disk monitor critical"
    else:
        prefix = "⚠️ Hermes disk monitor warning"

    return (
        f"{prefix}\n"
        f"Reason: {status['reason']}\n"
        f"Disk used: {status['used_pct']:.1f}%\n"
        f"Free: {status['free_gib']:.1f} GiB\n"
        f"Backup dir: {status['backup_destination']}\n"
        f"Backups present: {status['backup_count']}\n"
        f"Current backup footprint: {human_size(status['current_backup_bytes'])}\n"
        f"Latest backup: {human_size(status['latest_backup_bytes'])}\n"
        f"Projected retained footprint: {human_size(status['projected_retained_bytes'])}"
    )


def main() -> int:
    args = parse_args()
    hermes_home = Path(args.hermes_home).expanduser().resolve()
    backup_dest = Path(args.backup_destination).expanduser().resolve()
    state_file = Path(args.state_file).expanduser().resolve()
    env = load_env_file(hermes_home / ".env")

    backup_dest.mkdir(parents=True, exist_ok=True)
    status = assess(
        backup_dest=backup_dest,
        keep=args.keep,
        warn_pct=args.warn_usage_pct,
        critical_pct=args.critical_usage_pct,
        min_free_gb=args.min_free_gb,
    )
    previous = load_state(state_file)
    previous_level = previous.get("level", "unknown")

    should_notify = False
    recovered = False
    if status["level"] in {"warning", "critical"} and status["level"] != previous_level:
        should_notify = True
    elif status["level"] == "ok" and previous_level in {"warning", "critical"}:
        should_notify = True
        recovered = True

    if should_notify and args.notify != "none":
        send_notification(env, args.notify, build_message(status, recovered=recovered))

    save_state(state_file, status)
    print(json.dumps(status, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
