#!/usr/bin/env python3
"""Export/install managed Hermes configuration via ai-configs.

This script intentionally excludes secrets, auth state, session history, logs,
caches, SQLite state, checkpoints, and other runtime/generated data.

Default export destination:
  <repo>/_hermes/default

Usage:
  python scripts/hermes_config_sync.py export
  python scripts/hermes_config_sync.py refresh-manifest
  python scripts/hermes_config_sync.py verify
  python scripts/hermes_config_sync.py install --dry-run
  python scripts/hermes_config_sync.py install --apply
  python scripts/hermes_config_sync.py --component pi-analytics-collector install --dry-run
"""

from __future__ import annotations

import argparse
import fcntl
import fnmatch
import hashlib
import json
import os
import re
import shutil
import stat
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

CRON_RUNTIME_FIELDS = (
    "enabled", "state", "paused_at", "paused_reason", "next_run_at", "last_run_at",
    "last_status", "last_error", "last_delivery_error", "fire_claim", "run_claim",
)
COMPONENTS_DIR = "components"
COMPONENT_SCHEMA = "ai-configs.hermes-component.v1"
COMPONENT_CRON_RUNTIME_FIELDS = CRON_RUNTIME_FIELDS + (
    "created_at", "provider_snapshot", "model_snapshot",
)


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

        # Component manifests are repo-owned deployment metadata, not live Hermes
        # runtime files. Preserve them across authoritative live exports.
        copy_tree_filtered(bundle / COMPONENTS_DIR, stage / COMPONENTS_DIR)

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
        if p.is_file() and not should_exclude(p.relative_to(root)):
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


def backup_path(dst: Path, hermes_home: Path | None = None) -> Path:
    home = (hermes_home or DEFAULT_HERMES_HOME).expanduser().resolve()
    resolved_dst = dst.expanduser().resolve()
    stamp = os.environ.get("HERMES_AI_CONFIGS_INSTALL_STAMP") or now_stamp()
    try:
        rel = resolved_dst.relative_to(home)
    except ValueError:
        rel = Path(resolved_dst.name)
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


def load_cron_jobs(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to read cron jobs from {path}: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
        raise ValueError(f"Cron jobs file must contain a top-level jobs list: {path}")
    job_ids = set()
    for job in data["jobs"]:
        if not isinstance(job, dict) or not isinstance(job.get("id"), str) or not job["id"]:
            raise ValueError(f"Every cron job must be an object with a non-empty string id: {path}")
        if job["id"] in job_ids:
            raise ValueError(f"Cron job ids must be unique ({job['id']}): {path}")
        job_ids.add(job["id"])
    return data


def merge_cron_jobs(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    existing_by_id = {job["id"]: job for job in existing["jobs"]}
    merged = dict(incoming)
    merged_jobs = []

    for incoming_job in incoming["jobs"]:
        job = dict(incoming_job)
        existing_job = existing_by_id.get(job["id"])
        if existing_job is not None:
            for field in CRON_RUNTIME_FIELDS:
                if field in existing_job:
                    job[field] = existing_job[field]

            existing_repeat = existing_job.get("repeat")
            if isinstance(existing_repeat, dict) and "completed" in existing_repeat:
                incoming_repeat = job.get("repeat")
                repeat = dict(incoming_repeat) if isinstance(incoming_repeat, dict) else {}
                repeat["completed"] = existing_repeat["completed"]
                job["repeat"] = repeat
        merged_jobs.append(job)

    merged["jobs"] = merged_jobs
    if "updated_at" in existing:
        merged["updated_at"] = existing["updated_at"]
    return merged


def atomic_write_json(path: Path, data: dict[str, Any], mode: int) -> None:
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_path, mode)
        os.replace(temp_path, path)
        dir_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def install_cron_jobs(src: Path, dst: Path, dry_run: bool, backups: list[tuple[Path, Path]]) -> None:
    print(f"MERGE {src} -> {dst} (runtime state preserved)")
    if dry_run:
        return

    incoming = load_cron_jobs(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    lock_path = dst.parent / ".jobs.lock"
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        if dst.exists():
            existing = load_cron_jobs(dst)
            b = backup_path(dst)
            b.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dst, b)
            backups.append((dst, b))
            mode = stat.S_IMODE(dst.stat().st_mode)
            merged = merge_cron_jobs(existing, incoming)
        else:
            mode = stat.S_IMODE(src.stat().st_mode)
            merged = incoming
        atomic_write_json(dst, merged, mode)


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
        install_cron_jobs(cron_jobs, hermes_home / "cron" / "jobs.json", dry_run, backups)

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
                install_cron_jobs(cron_jobs, target / "cron" / "jobs.json", dry_run, backups)

    if backups and not dry_run:
        print("Backups written:")
        for _, b in backups:
            print(f"  {b}")


def refresh_manifest(bundle: Path) -> None:
    """Recompute the complete bundle manifest using only checked-in bundle source."""
    if not bundle.exists():
        raise SystemExit(f"Bundle not found: {bundle}")
    manifest = build_manifest(bundle, bundle)
    (bundle / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"REFRESHED MANIFEST: {manifest['file_count']} source files")


def manifest_failures(bundle: Path) -> tuple[dict[str, Any], list[str]]:
    manifest_path = bundle / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit("Missing manifest.json")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Unable to read manifest.json: {exc}") from exc
    failures: list[str] = []
    declared: dict[str, dict[str, Any]] = {}
    for item in manifest.get("files", []):
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            failures.append("invalid manifest file entry")
            continue
        declared[item["path"]] = item
        p = bundle / item["path"]
        if not p.exists():
            failures.append(f"missing {item['path']}")
            continue
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        if h != item.get("sha256"):
            failures.append(f"hash mismatch {item['path']}")
        if p.stat().st_size != item.get("bytes"):
            failures.append(f"size mismatch {item['path']}")
    actual = {
        p.relative_to(bundle).as_posix()
        for p in iter_files(bundle)
        if p.name != "manifest.json"
    }
    for path in sorted(actual - set(declared)):
        failures.append(f"unlisted source file {path}")
    for path in sorted(set(declared) - actual):
        if f"missing {path}" not in failures:
            failures.append(f"manifest lists absent source file {path}")
    if manifest.get("file_count") != len(declared):
        failures.append("manifest file_count does not match files")
    return manifest, failures


def verify(bundle: Path) -> None:
    if not bundle.exists():
        raise SystemExit(f"Bundle not found: {bundle}")
    manifest, failures = manifest_failures(bundle)
    findings = scan_secrets(bundle)
    if findings:
        failures.extend([f"secret-like token: {f}" for f in findings])
    if failures:
        print("VERIFY FAILED", file=sys.stderr)
        for f in failures[:100]:
            print(f"  {f}", file=sys.stderr)
        raise SystemExit(4)
    print(f"VERIFY OK: {manifest.get('file_count')} files, no obvious secret patterns")


def load_component(bundle: Path, name: str) -> dict[str, Any]:
    path = bundle / COMPONENTS_DIR / f"{name}.json"
    try:
        component = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Unable to read component manifest {path}: {exc}") from exc
    if not isinstance(component, dict) or component.get("schema") != COMPONENT_SCHEMA:
        raise SystemExit(f"Invalid component manifest schema: {path}")
    if component.get("name") != name:
        raise SystemExit(f"Component manifest name mismatch: {path}")
    files = component.get("files")
    job_ids = component.get("cron_job_ids")
    if not isinstance(files, list) or not files or not all(isinstance(p, str) and p for p in files):
        raise SystemExit(f"Component files must be a non-empty string list: {path}")
    if not isinstance(job_ids, list) or not job_ids or not all(isinstance(j, str) and j for j in job_ids):
        raise SystemExit(f"Component cron_job_ids must be a non-empty string list: {path}")
    if len(files) != len(set(files)) or len(job_ids) != len(set(job_ids)):
        raise SystemExit(f"Component manifest entries must be unique: {path}")
    if any(Path(p).is_absolute() or ".." in Path(p).parts for p in files):
        raise SystemExit(f"Component paths must remain within the bundle: {path}")
    return component


def validate_component_source(bundle: Path, component: dict[str, Any]) -> list[dict[str, Any]]:
    manifest, failures = manifest_failures(bundle)
    if failures:
        raise SystemExit("Stale full bundle manifest; run refresh-manifest before component operations")
    manifest_by_path = {item["path"]: item for item in manifest["files"]}
    for rel in component["files"]:
        item = manifest_by_path.get(rel)
        source = bundle / rel
        if item is None or not source.is_file():
            raise SystemExit(f"Component path is not validated by the full manifest: {rel}")
        if hashlib.sha256(source.read_bytes()).hexdigest() != item["sha256"]:
            raise SystemExit(f"Component path hash does not match the full manifest: {rel}")
    source_jobs = load_cron_jobs(bundle / "cron" / "jobs.json")["jobs"]
    by_id = {job["id"]: job for job in source_jobs}
    jobs = []
    for job_id in component["cron_job_ids"]:
        if job_id not in by_id:
            raise SystemExit(f"Component cron job is absent from source cron/jobs.json: {job_id}")
        jobs.append(by_id[job_id])
    return jobs


def merge_component_job(existing: dict[str, Any], incoming_job: dict[str, Any]) -> dict[str, Any]:
    """Add or update one job without changing unrelated jobs or top-level runtime data."""
    merged = dict(existing)
    jobs = list(existing["jobs"])
    replacement = dict(incoming_job)
    existing_index = next((i for i, job in enumerate(jobs) if job["id"] == incoming_job["id"]), None)
    if existing_index is not None:
        current = jobs[existing_index]
        # Source owns the full job definition; preserve only documented host
        # runtime fields so removed source fields converge on the next install.
        replacement = dict(incoming_job)
        for field in COMPONENT_CRON_RUNTIME_FIELDS:
            if field in current:
                replacement[field] = current[field]
        current_repeat = current.get("repeat")
        if isinstance(current_repeat, dict) and "completed" in current_repeat:
            incoming_repeat = replacement.get("repeat")
            repeat = dict(incoming_repeat) if isinstance(incoming_repeat, dict) else {}
            repeat["completed"] = current_repeat["completed"]
            replacement["repeat"] = repeat
        jobs[existing_index] = replacement
    else:
        jobs.append(replacement)
    merged["jobs"] = jobs
    return merged


def install_component_jobs(
    source_job: dict[str, Any], dst: Path, dry_run: bool, backups: list[tuple[Path, Path]],
    hermes_home: Path,
) -> None:
    print(f"JOB  {source_job['id']} -> {dst} (additive; unrelated jobs preserved)")
    if dry_run:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    lock_path = dst.parent / ".jobs.lock"
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        if dst.exists():
            existing = load_cron_jobs(dst)
            backup = backup_path(dst, hermes_home)
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dst, backup)
            backups.append((dst, backup))
            mode = stat.S_IMODE(dst.stat().st_mode)
        else:
            existing = {"jobs": []}
            mode = 0o600
        atomic_write_json(dst, merge_component_job(existing, source_job), mode)


def install_component(bundle: Path, hermes_home: Path, name: str, dry_run: bool) -> None:
    component = load_component(bundle, name)
    jobs = validate_component_source(bundle, component)
    backups: list[tuple[Path, Path]] = []
    for rel in component["files"]:
        source = bundle / rel
        destination = hermes_home / rel
        print(f"FILE {rel} -> {destination}")
        if not dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                backup = backup_path(destination, hermes_home)
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(destination, backup)
                backups.append((destination, backup))
            shutil.copy2(source, destination)
    for job in jobs:
        install_component_jobs(
            job, hermes_home / "cron" / "jobs.json", dry_run, backups, hermes_home
        )


def _job_source_fields(job: dict[str, Any]) -> dict[str, Any]:
    fields = {key: value for key, value in job.items() if key not in COMPONENT_CRON_RUNTIME_FIELDS}
    repeat = fields.get("repeat")
    if isinstance(repeat, dict):
        fields["repeat"] = {key: value for key, value in repeat.items() if key != "completed"}
    return fields


def verify_component(bundle: Path, hermes_home: Path, name: str) -> None:
    component = load_component(bundle, name)
    source_jobs = validate_component_source(bundle, component)
    failures = []
    for rel in component["files"]:
        source = bundle / rel
        destination = hermes_home / rel
        if not destination.is_file():
            failures.append(f"missing installed component file {rel}")
        elif source.read_bytes() != destination.read_bytes():
            failures.append(f"component file drift {rel}")
    try:
        destination_jobs = load_cron_jobs(hermes_home / "cron" / "jobs.json")["jobs"]
    except ValueError as exc:
        failures.append(str(exc))
        destination_jobs = []
    destination_by_id = {job["id"]: job for job in destination_jobs}
    for source_job in source_jobs:
        installed = destination_by_id.get(source_job["id"])
        if installed is None:
            failures.append(f"missing component cron job {source_job['id']}")
        elif _job_source_fields(installed) != _job_source_fields(source_job):
            failures.append(f"component cron job drift {source_job['id']}")
    if failures:
        print("COMPONENT VERIFY FAILED", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        raise SystemExit(4)
    print(
        f"COMPONENT VERIFY OK: {len(component['files'])} file(s), "
        f"{len(component['cron_job_ids'])} cron job(s)"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["export", "refresh-manifest", "verify", "install"])
    parser.add_argument("--hermes-home", default=str(DEFAULT_HERMES_HOME))
    parser.add_argument("--bundle", default=str(DEFAULT_BUNDLE))
    parser.add_argument("--component", help="Operate on one checked-in component manifest")
    parser.add_argument("--dry-run", action="store_true", help="Preview install actions")
    parser.add_argument("--apply", action="store_true", help="Actually install managed files")
    args = parser.parse_args()

    bundle = Path(args.bundle).expanduser().resolve()
    hermes_home = Path(args.hermes_home).expanduser().resolve()

    if args.command == "export":
        if args.component:
            raise SystemExit("Component mode does not support export")
        export_all(hermes_home, bundle)
        verify(bundle)
        print(f"Exported managed Hermes config to {bundle}")
    elif args.command == "refresh-manifest":
        if args.component:
            raise SystemExit("refresh-manifest always refreshes the full bundle")
        refresh_manifest(bundle)
    elif args.command == "verify":
        if args.component:
            verify_component(bundle, hermes_home, args.component)
        else:
            verify(bundle)
    elif args.command == "install":
        if args.apply == args.dry_run:
            raise SystemExit("For install, pass exactly one of --dry-run or --apply")
        if args.component:
            install_component(bundle, hermes_home, args.component, dry_run=args.dry_run)
        else:
            verify(bundle)
            install_all(bundle, hermes_home, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
