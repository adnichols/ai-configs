#!/usr/bin/env python3
"""Export/install managed Hermes configuration via ai-configs.

This script intentionally excludes secrets, auth state, session history, logs,
caches, SQLite state, checkpoints, and other runtime/generated data.

Default export destination:
  <repo>/_hermes/default

Usage:
  python scripts/hermes_config_sync.py export
  python scripts/hermes_config_sync.py verify
  python scripts/hermes_config_sync.py install --dry-run
  python scripts/hermes_config_sync.py install --apply
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception as exc:  # pragma: no cover - script bootstrap guard
    print(f"PyYAML is required to run this script: {exc}", file=sys.stderr)
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE = REPO_ROOT / "_hermes" / "default"
DEFAULT_HERMES_HOME = Path(os.environ.get("HERMES_HOME", "~/.hermes")).expanduser()
REDACTED = "[REDACTED: managed outside ai-configs]"

SECRET_KEY_RE = re.compile(
    r"(api[_-]?key|token|secret|password|credential|credentials|client[_-]?secret|"
    r"private[_-]?key|access[_-]?key|refresh[_-]?token|pat|bearer)",
    re.IGNORECASE,
)
SECRET_VALUE_RES = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}"),
    re.compile(r"doct_pat_v1_[A-Za-z0-9_-]+"),
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}"),
    # Discord bot tokens commonly have three dot-separated base64-ish segments.
    re.compile(r"[MN][A-Za-z\d_-]{23,}\.[A-Za-z\d_-]{6,}\.[A-Za-z\d_-]{20,}"),
]

# Directories/files that are source-like and safe to manage from ai-configs.
TOP_LEVEL_DIRS = ["skills", "hooks", "plugins", "scripts", "platforms"]
TOP_LEVEL_FILES = ["SOUL.md", "shell-hooks-allowlist.json", "honcho.dever.json"]
MEMORY_FILES = ["MEMORY.md", "USER.md"]
PROFILE_DIRS = ["skills", "hooks", "plugins", "scripts", "platforms"]
PROFILE_FILES = ["SOUL.md", "shell-hooks-allowlist.json"]

EXCLUDE_NAMES = {
    ".git",
    ".DS_Store",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
    "venv",
    ".venv",
    "env",
    "dist",
    "build",
    "cache",
    "logs",
    "tmp",
    "output",
    "audio_cache",
    "image_cache",
    "sandboxes",
    "sandbox",
    "checkpoints",
    "state-snapshots",
    "state",
    "index-cache",
    ".curator_backups",
    ".curator_state",
    ".hub",
    ".usage.json",
}
EXCLUDE_SUFFIXES = (".pyc", ".pyo", ".lock", ".pid", ".log")
EXCLUDE_GLOBS = [
    "*.db",
    "*.db-*",
    "*.sqlite",
    "*.sqlite-*",
    "*.tar.gz",
    "*.zip",
    "scan_*.json",
    "state.json",
]
NEVER_EXPORT = {
    ".env",
    "auth.json",
    "auth.lock",
    "state.db",
    "state.db-wal",
    "state.db-shm",
    "processes.json",
    "gateway.pid",
    "gateway.lock",
}

MANAGED_TOP_LEVEL_TARGETS = [
    "config/config.yaml",
    "cron/jobs.json",
    "memories/MEMORY.md",
    "memories/USER.md",
    *TOP_LEVEL_FILES,
    *TOP_LEVEL_DIRS,
]


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def should_exclude(path: Path) -> bool:
    parts = set(path.parts)
    if parts & EXCLUDE_NAMES:
        return True
    if path.name in NEVER_EXPORT:
        return True
    if path.suffix in EXCLUDE_SUFFIXES:
        return True
    return any(fnmatch.fnmatch(path.name, pat) for pat in EXCLUDE_GLOBS)


def copy_tree_filtered(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    for item in src.rglob("*"):
        rel = item.relative_to(src)
        if should_exclude(rel):
            continue
        out = dst / rel
        if item.is_dir():
            out.mkdir(parents=True, exist_ok=True)
        elif item.is_file():
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, out)


def sanitize(obj: Any, key_path: tuple[str, ...] = ()) -> Any:
    current_key = key_path[-1] if key_path else ""
    if isinstance(obj, dict):
        return {k: sanitize(v, key_path + (str(k),)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize(v, key_path + (str(i),)) for i, v in enumerate(obj)]
    if SECRET_KEY_RE.search(current_key):
        if obj in (None, "", [], {}):
            return obj
        return REDACTED
    if isinstance(obj, str):
        redacted = obj
        for rx in SECRET_VALUE_RES:
            redacted = rx.sub(REDACTED, redacted)
        return redacted
    return obj


def write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def export_config(src_home: Path, dst_root: Path) -> None:
    cfg = src_home / "config.yaml"
    if cfg.exists():
        data = yaml.safe_load(cfg.read_text(encoding="utf-8"))
        write_yaml(dst_root / "config" / "config.yaml", sanitize(data))


def export_profile(profile_home: Path, out: Path) -> None:
    if (profile_home / "config.yaml").exists():
        data = yaml.safe_load((profile_home / "config.yaml").read_text(encoding="utf-8"))
        write_yaml(out / "config" / "config.yaml", sanitize(data))
    for name in PROFILE_FILES:
        src = profile_home / name
        if src.exists() and src.is_file() and not should_exclude(Path(name)):
            (out / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, out / name)
    for name in PROFILE_DIRS:
        copy_tree_filtered(profile_home / name, out / name)
    for mem in MEMORY_FILES:
        src = profile_home / "memories" / mem
        if src.exists():
            (out / "memories").mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, out / "memories" / mem)
    cron_jobs = profile_home / "cron" / "jobs.json"
    if cron_jobs.exists():
        (out / "cron").mkdir(parents=True, exist_ok=True)
        shutil.copy2(cron_jobs, out / "cron" / "jobs.json")


def export_all(src_home: Path, bundle: Path) -> None:
    src_home = src_home.expanduser().resolve()
    if not src_home.exists():
        raise SystemExit(f"Hermes home not found: {src_home}")

    with tempfile.TemporaryDirectory(prefix="hermes-export-") as tmp:
        stage = Path(tmp) / "default"
        stage.mkdir(parents=True)
        export_config(src_home, stage)

        for name in TOP_LEVEL_FILES:
            src = src_home / name
            if src.exists() and src.is_file() and not should_exclude(Path(name)):
                shutil.copy2(src, stage / name)
        for name in TOP_LEVEL_DIRS:
            copy_tree_filtered(src_home / name, stage / name)
        for mem in MEMORY_FILES:
            src = src_home / "memories" / mem
            if src.exists():
                (stage / "memories").mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, stage / "memories" / mem)
        cron_jobs = src_home / "cron" / "jobs.json"
        if cron_jobs.exists():
            (stage / "cron").mkdir(parents=True, exist_ok=True)
            shutil.copy2(cron_jobs, stage / "cron" / "jobs.json")

        profiles_root = src_home / "profiles"
        if profiles_root.exists():
            for profile_dir in sorted(profiles_root.iterdir(), key=lambda p: p.name):
                if not profile_dir.is_dir():
                    continue
                export_profile(profile_dir, stage / "profiles" / profile_dir.name)

        write_static_docs(stage)
        sanitize_exported_text_files(stage)
        manifest = build_manifest(stage, src_home)
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        findings = scan_secrets(stage)
        if findings:
            print("Potential secret findings; refusing to export:", file=sys.stderr)
            for f in findings[:50]:
                print(f"  {f}", file=sys.stderr)
            raise SystemExit(3)

        backup_existing(bundle)
        if bundle.exists():
            shutil.rmtree(bundle)
        bundle.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(stage, bundle)


def backup_existing(path: Path) -> None:
    if not path.exists():
        return
    backup_root = path.parent / ".backups"
    backup_root.mkdir(parents=True, exist_ok=True)
    dest = backup_root / f"{path.name}-{now_stamp()}"
    shutil.copytree(path, dest)


def write_static_docs(root: Path) -> None:
    (root / "README.md").write_text(
        "# Hermes managed config export\n\n"
        "This directory is the ai-configs source copy of managed Hermes configuration.\n\n"
        "## Workflow\n\n"
        "- Export current local Hermes config: `python scripts/hermes_config_sync.py export`\n"
        "- Verify the repo copy: `python scripts/hermes_config_sync.py verify`\n"
        "- Preview install back into Hermes: `python scripts/hermes_config_sync.py install --dry-run`\n"
        "- Install managed files into Hermes: `python scripts/hermes_config_sync.py install --apply`\n\n"
        "For future changes, prefer editing this repo copy first, then run the install command.\n"
        "After any Hermes configuration change, run export + verify, then commit and push ai-configs before considering the work complete.\n\n"
        "## Exclusions\n\n"
        "Secrets and runtime state are intentionally not stored here: `.env`, `auth.json`, "
        "OAuth tokens, sessions, logs, caches, SQLite state, checkpoints, process state, and generated output.\n"
        "Secret-like config leaves are written as `[REDACTED: managed outside ai-configs]`; "
        "the installer skips those leaves so local secrets remain in `~/.hermes`.\n",
        encoding="utf-8",
    )
    (root / "EXCLUSIONS.md").write_text(
        "# Exclusions and localization contract\n\n"
        "This export captures source-like Hermes configuration: config conventions, skills, hooks, "
        "plugins, scripts, memories, cron job definitions, and profile-local equivalents.\n\n"
        "Excluded by design:\n\n"
        "- `.env`, `auth.json`, OAuth/PAT/API tokens, credential pools, and private keys\n"
        "- `sessions/`, `state.db*`, `kanban.db*`, checkpoints, state snapshots, process state\n"
        "- logs, caches, audio/image artifacts, paste dumps, cron output, temp directories\n"
        "- Hermes source checkout / venv / node_modules under `~/.hermes/hermes-agent`\n"
        "- host locks and pid files\n\n"
        "Install preserves machine-local secrets by recursively merging config and skipping any "
        "redacted leaves. If a future change needs to remove a config key, do that explicitly in Hermes "
        "or extend the installer with a deletion manifest.\n",
        encoding="utf-8",
    )


def iter_files(root: Path):
    for p in sorted(root.rglob("*")):
        if p.is_file():
            yield p


def build_manifest(root: Path, src_home: Path) -> dict[str, Any]:
    files = []
    for p in iter_files(root):
        if p.name == "manifest.json":
            continue
        rel = p.relative_to(root).as_posix()
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        files.append({"path": rel, "bytes": p.stat().st_size, "sha256": h})
    return {
        "schema": "ai-configs.hermes-managed-export.v1",
        "generated_at": now_stamp(),
        "source_home": str(src_home),
        "redaction_marker": REDACTED,
        "file_count": len(files),
        "files": files,
    }


def sanitize_exported_text_files(root: Path) -> None:
    """Redact token-looking values in copied text files before writing the manifest."""
    for p in iter_files(root):
        if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp3", ".wav", ".pdf"}:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        redacted = text
        for rx in SECRET_VALUE_RES:
            redacted = rx.sub(REDACTED, redacted)
        if redacted != text:
            p.write_text(redacted, encoding="utf-8")


def scan_secrets(root: Path) -> list[str]:
    findings: list[str] = []
    for p in iter_files(root):
        if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp3", ".wav", ".pdf"}:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        text_for_scan = text.replace(REDACTED, "")
        for rx in SECRET_VALUE_RES:
            if rx.search(text_for_scan):
                findings.append(f"{p.relative_to(root)} matches {rx.pattern}")
                break
    return findings


def merge_skip_redacted(existing: Any, incoming: Any) -> Any:
    if incoming == REDACTED:
        return existing
    if isinstance(existing, dict) and isinstance(incoming, dict):
        merged = dict(existing)
        for key, val in incoming.items():
            merged[key] = merge_skip_redacted(existing.get(key), val)
        return merged
    if isinstance(incoming, list):
        return [merge_skip_redacted(None, v) for v in incoming]
    return incoming


def install_file(src: Path, dst: Path, dry_run: bool, backups: list[tuple[Path, Path]]) -> None:
    print(f"FILE {src.relative_to(DEFAULT_BUNDLE.parent.parent)} -> {dst}")
    if dry_run:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        b = backup_path(dst)
        b.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dst, b)
        backups.append((dst, b))
    shutil.copy2(src, dst)


def install_dir(src: Path, dst: Path, dry_run: bool, backups: list[tuple[Path, Path]]) -> None:
    print(f"DIR  {src.relative_to(DEFAULT_BUNDLE.parent.parent)} -> {dst}")
    if dry_run:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        b = backup_path(dst)
        b.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(dst, b)
        backups.append((dst, b))
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def backup_path(dst: Path) -> Path:
    home = DEFAULT_HERMES_HOME.expanduser()
    stamp = os.environ.get("HERMES_AI_CONFIGS_INSTALL_STAMP") or now_stamp()
    rel = dst.relative_to(home) if str(dst).startswith(str(home)) else Path(dst.name)
    return home / "backups" / f"ai-configs-install-{stamp}" / rel


def install_config(bundle: Path, hermes_home: Path, dry_run: bool, backups: list[tuple[Path, Path]]) -> None:
    src = bundle / "config" / "config.yaml"
    if not src.exists():
        return
    dst = hermes_home / "config.yaml"
    print(f"MERGE {src.relative_to(REPO_ROOT)} -> {dst} (redacted leaves skipped)")
    if dry_run:
        return
    incoming = yaml.safe_load(src.read_text(encoding="utf-8"))
    existing = yaml.safe_load(dst.read_text(encoding="utf-8")) if dst.exists() else {}
    merged = merge_skip_redacted(existing, incoming)
    if dst.exists():
        b = backup_path(dst)
        b.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dst, b)
        backups.append((dst, b))
    write_yaml(dst, merged)


def install_all(bundle: Path, hermes_home: Path, dry_run: bool) -> None:
    if not bundle.exists():
        raise SystemExit(f"Bundle not found: {bundle}. Run export first.")
    backups: list[tuple[Path, Path]] = []
    hermes_home = hermes_home.expanduser()
    install_config(bundle, hermes_home, dry_run, backups)

    for name in TOP_LEVEL_FILES:
        src = bundle / name
        if src.exists():
            install_file(src, hermes_home / name, dry_run, backups)
    for name in TOP_LEVEL_DIRS:
        src = bundle / name
        if src.exists():
            install_dir(src, hermes_home / name, dry_run, backups)
    for mem in MEMORY_FILES:
        src = bundle / "memories" / mem
        if src.exists():
            install_file(src, hermes_home / "memories" / mem, dry_run, backups)
    cron_jobs = bundle / "cron" / "jobs.json"
    if cron_jobs.exists():
        install_file(cron_jobs, hermes_home / "cron" / "jobs.json", dry_run, backups)

    profiles = bundle / "profiles"
    if profiles.exists():
        for profile in sorted([p for p in profiles.iterdir() if p.is_dir()]):
            target = hermes_home / "profiles" / profile.name
            install_config(profile, target, dry_run, backups)
            for name in PROFILE_FILES:
                src = profile / name
                if src.exists():
                    install_file(src, target / name, dry_run, backups)
            for name in PROFILE_DIRS:
                src = profile / name
                if src.exists():
                    install_dir(src, target / name, dry_run, backups)
            for mem in MEMORY_FILES:
                src = profile / "memories" / mem
                if src.exists():
                    install_file(src, target / "memories" / mem, dry_run, backups)
            cron_jobs = profile / "cron" / "jobs.json"
            if cron_jobs.exists():
                install_file(cron_jobs, target / "cron" / "jobs.json", dry_run, backups)

    if backups and not dry_run:
        print("Backups written:")
        for _, b in backups:
            print(f"  {b}")


def verify(bundle: Path) -> None:
    if not bundle.exists():
        raise SystemExit(f"Bundle not found: {bundle}")
    manifest_path = bundle / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit("Missing manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures = []
    for item in manifest.get("files", []):
        p = bundle / item["path"]
        if not p.exists():
            failures.append(f"missing {item['path']}")
            continue
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        if h != item["sha256"]:
            failures.append(f"hash mismatch {item['path']}")
    findings = scan_secrets(bundle)
    if findings:
        failures.extend([f"secret-like token: {f}" for f in findings])
    if failures:
        print("VERIFY FAILED", file=sys.stderr)
        for f in failures[:100]:
            print(f"  {f}", file=sys.stderr)
        raise SystemExit(4)
    print(f"VERIFY OK: {manifest.get('file_count')} files, no obvious secret patterns")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["export", "verify", "install"])
    parser.add_argument("--hermes-home", default=str(DEFAULT_HERMES_HOME))
    parser.add_argument("--bundle", default=str(DEFAULT_BUNDLE))
    parser.add_argument("--dry-run", action="store_true", help="Preview install actions")
    parser.add_argument("--apply", action="store_true", help="Actually install managed files")
    args = parser.parse_args()

    bundle = Path(args.bundle).expanduser().resolve()
    hermes_home = Path(args.hermes_home).expanduser().resolve()

    if args.command == "export":
        export_all(hermes_home, bundle)
        verify(bundle)
        print(f"Exported managed Hermes config to {bundle}")
    elif args.command == "verify":
        verify(bundle)
    elif args.command == "install":
        if args.apply == args.dry_run:
            raise SystemExit("For install, pass exactly one of --dry-run or --apply")
        verify(bundle)
        install_all(bundle, hermes_home, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
