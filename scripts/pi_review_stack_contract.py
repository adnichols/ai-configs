#!/usr/bin/env python3
"""Validate/expand Pi review-stack surfaces and write install-summary-v1 receipts."""

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1
SUMMARY_SCHEMA_VERSION = 1
VARIABLES = ("PI_AGENT_DIR", "SHARED_SKILLS_DIR", "AGENT_SCRIPTS_DIR", "LOCAL_BIN_DIR")
KINDS = {"exact-directory", "overlay-children", "file", "json-merge", "symlink", "remove-set"}
BASE_FIELDS = {"id", "kind", "source", "destination", "scopes", "mode", "preserveUnlisted", "rollbackBoundary"}
SUMMARY_STATUSES = {"success", "failed", "partial", "rolled_back", "rollback_failed"}
SUMMARY_MODES = {"pi-review-stack", "all", "pi", "tools", "skills", "remote-kitty"}
TRANSPORT_STATUSES = {"pass", "fail", "not_run"}
ROLLBACK_STATUSES = {"not_needed", "succeeded", "failed"}


def fail(message):
    raise ValueError(message)


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_manifest_path():
    return Path(__file__).with_name("pi-review-stack-managed-surfaces.json")


def load_manifest(path, repo_root=None):
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail("invalid managed-surface manifest: %s" % exc)
    if not isinstance(data, dict) or set(data) != {"schemaVersion", "surfaces"}:
        fail("manifest must contain exactly schemaVersion and surfaces")
    if data["schemaVersion"] != SCHEMA_VERSION or not isinstance(data["surfaces"], list):
        fail("manifest requires schemaVersion 1 and surfaces array")
    ids = set()
    destinations = set()
    by_id = {}
    for index, surface in enumerate(data["surfaces"]):
        if not isinstance(surface, dict):
            fail("surface %d must be an object" % index)
        kind = surface.get("kind")
        allowed = set(BASE_FIELDS)
        if kind == "symlink":
            allowed.add("targetSurfaceId")
        if kind == "remove-set":
            allowed.add("entries")
        unknown = set(surface) - allowed
        missing = BASE_FIELDS - set(surface)
        if unknown:
            fail("surface %d unknown field(s): %s" % (index, ", ".join(sorted(unknown))))
        if missing:
            fail("surface %d missing field(s): %s" % (index, ", ".join(sorted(missing))))
        sid = surface["id"]
        if not isinstance(sid, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", sid) or sid in ids:
            fail("surface %d has invalid or duplicate id" % index)
        ids.add(sid)
        if kind not in KINDS:
            fail("surface %s has unsupported kind" % sid)
        source = surface["source"]
        if source is None:
            if kind not in {"symlink", "remove-set"}:
                fail("surface %s source may be null only for removals/links" % sid)
        elif not isinstance(source, str) or not safe_relative(source):
            fail("surface %s has unsafe source path" % sid)
        elif repo_root is not None and not (Path(repo_root) / source).exists():
            fail("surface %s source does not exist: %s" % (sid, source))
        for field in ("destination", "rollbackBoundary"):
            value = surface[field]
            validate_template(value, "%s %s" % (sid, field))
        if surface["destination"] in destinations:
            fail("duplicate destination: %s" % surface["destination"])
        destinations.add(surface["destination"])
        scopes = surface["scopes"]
        if not isinstance(scopes, list) or not scopes or "pi-review-stack" not in scopes or any(x not in {"pi-review-stack", "full"} for x in scopes):
            fail("surface %s has invalid scopes" % sid)
        mode = surface["mode"]
        if mode != "preserve" and not (isinstance(mode, str) and re.fullmatch(r"0[0-7]{3}", mode)):
            fail("surface %s has invalid mode" % sid)
        if not isinstance(surface["preserveUnlisted"], bool):
            fail("surface %s preserveUnlisted must be boolean" % sid)
        if kind == "symlink" and not isinstance(surface.get("targetSurfaceId"), str):
            fail("surface %s symlink requires targetSurfaceId" % sid)
        if kind == "remove-set":
            entries = surface.get("entries")
            if not isinstance(entries, list) or entries != sorted(entries) or len(entries) != len(set(entries)) or any(not isinstance(x, str) or not safe_relative(x) for x in entries):
                fail("surface %s remove-set entries must be unique sorted safe paths" % sid)
        by_id[sid] = surface
    roots = default_roots()
    for sid, surface in by_id.items():
        destination = expand_template(surface["destination"], roots)
        boundary = expand_template(surface["rollbackBoundary"], roots)
        if not contained(destination, boundary):
            fail("surface %s rollback boundary does not contain destination" % sid)
        if surface["kind"] == "symlink" and surface["targetSurfaceId"] not in by_id:
            fail("surface %s targetSurfaceId is unknown" % sid)
    return data


def safe_relative(value):
    if not value or value.startswith("/") or "\\" in value:
        return False
    return ".." not in Path(value).parts


def validate_template(value, label):
    if not isinstance(value, str) or value.startswith("/") or "\\" in value or ".." in Path(value).parts:
        fail("%s has parent traversal or absolute path" % label)
    variables = re.findall(r"\$\{([^}]+)\}", value)
    if not variables or any(item not in VARIABLES for item in variables):
        fail("%s uses unsupported or missing variable" % label)
    residue = re.sub(r"\$\{[^}]+\}", "ROOT", value)
    if "$" in residue:
        fail("%s uses unsupported variable syntax" % label)


def default_roots():
    return {
        "PI_AGENT_DIR": os.environ.get("PI_AGENT_DIR", os.environ.get("PI_CODING_AGENT_DIR", ".pi/agent")),
        "SHARED_SKILLS_DIR": os.environ.get("SHARED_SKILLS_DIR", ".agents/skills"),
        "AGENT_SCRIPTS_DIR": os.environ.get("AGENT_SCRIPTS_DIR", ".agents/scripts"),
        "LOCAL_BIN_DIR": os.environ.get("LOCAL_BIN_DIR", ".local/bin"),
    }


def expand_template(value, roots=None):
    roots = roots or default_roots()
    result = value
    for name, replacement in roots.items():
        result = result.replace("${%s}" % name, replacement.strip("/"))
    if "${" in result or not safe_relative(result):
        fail("expanded path is unsafe: %s" % result)
    return Path(result).as_posix()


def contained(destination, boundary):
    destination = Path("/") / destination
    boundary = Path("/") / boundary
    try:
        destination.relative_to(boundary)
        return True
    except ValueError:
        return False


def expanded_surfaces(data, scope):
    roots = default_roots()
    by_id = {item["id"]: item for item in data["surfaces"]}
    result = []
    for surface in data["surfaces"]:
        if scope not in surface["scopes"]:
            continue
        item = dict(surface)
        item["destination"] = expand_template(item["destination"], roots)
        item["rollbackBoundary"] = expand_template(item["rollbackBoundary"], roots)
        if item["kind"] == "symlink":
            item["target"] = expand_template(by_id[item["targetSurfaceId"]]["destination"], roots)
        result.append(item)
    return result


def manifest_info(path, data, repo_root=None):
    manifest_path = Path(path).resolve()
    raw = manifest_path.read_bytes()
    if repo_root is not None:
        try:
            display_path = manifest_path.relative_to(Path(repo_root).resolve()).as_posix()
        except ValueError:
            display_path = str(manifest_path)
    else:
        display_path = str(path)
    return {
        "path": display_path,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "surfaceCount": len(data["surfaces"]),
    }


def parse_json_arg(raw, expected, label):
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        fail("invalid %s JSON: %s" % (label, exc))
    if not isinstance(value, expected):
        fail("%s must be JSON %s" % (label, expected.__name__))
    return value


def write_atomic_private(path, payload):
    path = Path(path).expanduser()
    if os.path.lexists(str(path)):
        mode = os.lstat(str(path)).st_mode
        if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
            fail("summary destination must be a regular file or absent: %s" % path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_tmp = tempfile.mkstemp(prefix=".%s.tmp." % path.name, dir=str(path.parent))
    tmp = Path(raw_tmp)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(tmp), str(path))
        directory_fd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except BaseException:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass
        raise


def command_validate(args):
    data = load_manifest(args.manifest, args.repo_root)
    info = manifest_info(args.manifest, data, args.repo_root)
    print(json.dumps({"schemaVersion": data["schemaVersion"], "surfaceCount": info["surfaceCount"], "sha256": info["sha256"], "ids": [x["id"] for x in data["surfaces"]]}, sort_keys=True))


def command_list(args):
    data = load_manifest(args.manifest, args.repo_root)
    for item in expanded_surfaces(data, args.scope):
        if args.format == "json":
            print(json.dumps(item, sort_keys=True))
        else:
            entries = json.dumps(item.get("entries", []), separators=(",", ":"))
            print("\t".join([item["id"], item["kind"], item.get("source") or "-", item["destination"], item["mode"], str(item["preserveUnlisted"]).lower(), item["rollbackBoundary"], item.get("target", "-"), entries]))


def command_verify(args):
    repo_root = Path(args.repo_root).resolve()
    home = Path(args.home).expanduser().resolve()
    data = load_manifest(args.manifest, repo_root)
    failures = []
    by_id = {item["id"]: item for item in expanded_surfaces(data, args.scope)}
    for item in by_id.values():
        destination = home / item["destination"]
        source = repo_root / item["source"] if item.get("source") else None
        kind = item["kind"]
        if kind == "overlay-children":
            if not destination.is_dir():
                failures.append("missing directory %s" % destination)
                continue
            for child in source.iterdir():
                if not same_tree(child, destination / child.name):
                    failures.append("installed parity %s" % (destination / child.name))
        elif kind == "exact-directory":
            if not same_tree(source, destination, ignore=(".ai-configs-managed.json",)):
                failures.append("installed exact-directory parity %s" % destination)
        elif kind == "file":
            if item["id"] in {"helper-process-identity", "helper-review-supervisor"} and (not destination.is_file() or stat.S_IMODE(os.lstat(str(destination)).st_mode) & 0o500 != 0o500):
                failures.append("installed review helper must be owner-readable and executable: %s" % destination)
                continue
            if item["id"] == "pi-append-system":
                if not valid_append_system(repo_root, source, destination):
                    failures.append("installed rendered APPEND_SYSTEM.md")
            elif not destination.is_file() or source.read_bytes() != destination.read_bytes():
                if item["id"] == "script-review-orchestration":
                    failures.append("installed review runtime parity %s" % destination)
                else:
                    failures.append("installed file parity %s" % destination)
        elif kind == "json-merge":
            if item["id"] == "pi-models" and not valid_model_merge(source, destination, home / by_id["pi-settings"]["destination"]):
                failures.append("installed merged model contract %s" % destination)
            if item["id"] == "pi-settings" and not valid_settings(destination, home / by_id["pi-extensions"]["destination"]):
                failures.append("disabled Pi extension remains explicitly registered in settings.json")
        elif kind == "remove-set":
            boundary = home / item["rollbackBoundary"]
            for entry in item["entries"]:
                if os.path.lexists(str(boundary / entry)):
                    failures.append("removed surface remains %s" % (boundary / entry))
        elif kind == "symlink":
            expected = str(home / item["target"])
            if not destination.is_symlink() or not os.path.isabs(os.readlink(str(destination))) or os.path.realpath(str(destination)) != os.path.realpath(expected):
                failures.append("installed symlink parity %s" % destination)
        if item["mode"] != "preserve" and os.path.lexists(str(destination)):
            actual = stat.S_IMODE(os.lstat(str(destination)).st_mode)
            if item["id"] in {"helper-process-identity", "helper-review-supervisor"}:
                if actual & 0o500 != 0o500:
                    failures.append("installed review helper must be owner-readable and executable: %s" % destination)
            elif actual != int(item["mode"], 8):
                if item["id"] == "script-review-orchestration":
                    failures.append("installed review runtime must have exact mode 0755: %s" % destination)
                else:
                    failures.append("mode %s expected %s got %04o" % (destination, item["mode"], actual))
    if failures:
        for failure in failures:
            print("FAIL: %s" % failure, file=sys.stderr)
        raise ValueError("verification failed with %d issue(s)" % len(failures))
    print("Pi review-stack manifest verification passed (%d surfaces)." % len(by_id))


def same_tree(left, right, ignore=()):
    if not os.path.lexists(str(right)):
        return False
    args = ["diff", "-qr"]
    for name in ignore:
        args.append("-x")
        args.append(name)
    args.extend([str(left), str(right)])
    result = subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return result.returncode == 0


def valid_append_system(repo_root, source, destination):
    if not destination.is_file():
        return False
    source_text = source.read_text(encoding="utf-8")
    installed = destination.read_text(encoding="utf-8")
    token = "{{AI_CONFIGS_VERSION}}"
    if source_text.count(token) != 1 or token in installed:
        return False
    prefix, suffix = source_text.split(token)
    if not installed.startswith(prefix) or not installed.endswith(suffix):
        return False
    version = installed[len(prefix):len(installed) - len(suffix) if suffix else None]
    commit = subprocess.run(["git", "-C", str(repo_root), "rev-parse", "--short=8", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    relative = source.resolve().relative_to(repo_root).as_posix()
    committed = subprocess.run(["git", "-C", str(repo_root), "show", "HEAD:" + relative], check=True, capture_output=True).stdout
    dirty = source.read_bytes() != committed
    return re.fullmatch(r"\d{4}-\d{2}-\d{2}\+%s%s" % (re.escape(commit), "-dirty" if dirty else ""), version) is not None


def valid_model_merge(source, destination, settings_path):
    try:
        wanted = json.loads(source.read_text(encoding="utf-8"))
        actual = json.loads(destination.read_text(encoding="utf-8"))
        settings = json.loads(settings_path.read_text(encoding="utf-8")) if settings_path.exists() else {}
    except (OSError, json.JSONDecodeError):
        return False
    wanted_providers = wanted.get("providers", {})
    actual_providers = actual.get("providers", {})
    for provider_id, provider in wanted_providers.items():
        target = actual_providers.get(provider_id)
        if not isinstance(target, dict):
            return False
        targets = {item.get("id"): item for item in target.get("models", []) if isinstance(item, dict)}
        for model in provider.get("models", []):
            if model.get("id") not in targets or not nested_contains(targets[model["id"]], model):
                return False
    retired = {"gpt-5.4", "gpt-5.4-mini"}
    managed = actual_providers.get("openai-codex", {})
    if any(isinstance(item, dict) and item.get("id") in retired for item in managed.get("models", [])):
        return False
    for provider_id in ("opencode", "opencode-go", "opencode-zen"):
        provider = actual_providers.get(provider_id, {})
        if isinstance(provider, dict) and "glm-5.2" in provider.get("modelOverrides", {}):
            return False
    enabled = settings.get("enabledModels", []) if isinstance(settings, dict) else []
    for value in enabled if isinstance(enabled, list) else []:
        if isinstance(value, str) and (value in retired or re.fullmatch(r"openai-codex(?:-[^/]*)?/gpt-5\.4(?:-mini)?", value)):
            return False
    return True


def nested_contains(actual, expected):
    if not isinstance(actual, dict):
        return False
    return all(key in actual and (nested_contains(actual[key], value) if isinstance(value, dict) else actual[key] == value) for key, value in expected.items())


def valid_settings(path, extensions_dir):
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except json.JSONDecodeError:
        return False
    if not isinstance(data, dict):
        return False
    disabled = {"claude-review", "codex-review"}
    live = os.path.realpath(str(extensions_dir))
    for item in data.get("extensions", []):
        source = item if isinstance(item, str) else item.get("source") if isinstance(item, dict) else None
        if not isinstance(source, str):
            continue
        expanded = os.path.expanduser(source)
        normalized = os.path.normpath(expanded).replace(os.sep, "/")
        if os.path.basename(normalized) in disabled and (normalized == ".pi/agent/extensions/" + os.path.basename(normalized) or (os.path.isabs(expanded) and os.path.dirname(os.path.realpath(expanded)) == live)):
            return False
    return True


def command_write_summary(args):
    if args.mode not in SUMMARY_MODES:
        fail("invalid summary mode enum")
    if args.status not in SUMMARY_STATUSES or args.transport_status not in TRANSPORT_STATUSES or args.rollback_status not in ROLLBACK_STATUSES:
        fail("invalid summary status enum")
    data = load_manifest(args.manifest, args.repo_root)
    hosts = parse_json_arg(args.hosts_json, list, "hosts")
    warnings = parse_json_arg(args.warnings_json, list, "warnings")
    if any(not isinstance(x, str) for x in warnings):
        fail("warnings must contain strings")
    for host in hosts:
        if not isinstance(host, dict) or set(host) != {"host", "status", "cwd", "exitCode", "warning"}:
            fail("host summary record has wrong fields")
        if host["status"] not in {"success", "failed", "skipped"}:
            fail("host summary record has invalid status")
        if host["exitCode"] is not None and not isinstance(host["exitCode"], int):
            fail("host summary exitCode must be integer or null")
    payload = {
        "schemaVersion": SUMMARY_SCHEMA_VERSION,
        "command": args.command,
        "mode": args.mode,
        "status": args.status,
        "startedAt": args.started_at or utc_now(),
        "finishedAt": utc_now(),
        "cwd": str(Path(args.cwd or os.getcwd()).resolve()),
        "repoRoot": str(Path(args.repo_root).resolve()),
        "managedSurfaceManifest": manifest_info(args.manifest, data, args.repo_root),
        "transportProbe": {"status": args.transport_status, "reason": args.transport_reason},
        "hosts": hosts,
        "warnings": warnings,
        "rollback": {"attempted": args.rollback_attempted, "status": args.rollback_status, "snapshotPath": args.snapshot_path},
    }
    write_atomic_private(args.output, payload)


def build_parser():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--manifest", default=str(default_manifest_path()))
    common.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    validate = sub.add_parser("validate", parents=[common])
    validate.set_defaults(func=command_validate)
    listing = sub.add_parser("list", parents=[common])
    listing.add_argument("--scope", default="pi-review-stack", choices=("pi-review-stack", "full"))
    listing.add_argument("--format", default="tsv", choices=("tsv", "json"))
    listing.set_defaults(func=command_list)
    verify = sub.add_parser("verify", parents=[common])
    verify.add_argument("--scope", default="pi-review-stack", choices=("pi-review-stack", "full"))
    verify.add_argument("--home", default=str(Path.home()))
    verify.set_defaults(func=command_verify)
    summary = sub.add_parser("write-summary", parents=[common])
    summary.add_argument("--output", required=True)
    summary.add_argument("--command", required=True, choices=("install", "transaction", "remote-hosts"))
    summary.add_argument("--mode", required=True)
    summary.add_argument("--status", required=True)
    summary.add_argument("--started-at")
    summary.add_argument("--cwd")
    summary.add_argument("--transport-status", default="not_run")
    summary.add_argument("--transport-reason")
    summary.add_argument("--hosts-json", default="[]")
    summary.add_argument("--warnings-json", default="[]")
    summary.add_argument("--rollback-attempted", action="store_true")
    summary.add_argument("--rollback-status", default="not_needed")
    summary.add_argument("--snapshot-path")
    summary.set_defaults(func=command_write_summary)
    return parser


def main():
    args = build_parser().parse_args()
    try:
        args.func(args)
        return 0
    except (OSError, ValueError) as exc:
        print("pi-review-stack contract: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
