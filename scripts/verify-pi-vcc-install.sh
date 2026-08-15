#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
agent_dir="${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}"
source_package="$repo_root/_pi/packages/pi-vcc"
stable_package="$agent_dir/local-packages/ai-configs/pi-vcc"
source_extension="$repo_root/_pi/extensions/percentage-compaction.ts"
live_extension="$agent_dir/extensions/percentage-compaction.ts"
settings="$agent_dir/settings.json"
identity_helper="$repo_root/scripts/pi-vcc-package-tree.py"
source_only=0
json_output=0

usage() {
  echo "Usage: $0 [--source-only] [--expected-package <path>] [--json]"
  echo "  default: verify exact-one installed registration and source-identical mirrors"
  echo "  --source-only: verify expected package syntax and tree identity"
  echo "  --expected-package: compare against this package instead of the repo package"
  echo "  --json: emit machine-readable package identity fields"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --source-only) source_only=1; shift ;;
    --expected-package)
      [ "$#" -ge 2 ] || { echo "--expected-package requires a path" >&2; exit 2; }
      source_package="$2"
      shift 2
      ;;
    --json) json_output=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

source_package="$(python3 - "$source_package" <<'PY'
import os, sys
print(os.path.abspath(os.path.expanduser(sys.argv[1])))
PY
)"

hash_file() {
  python3 - "$1" <<'PY'
import hashlib, sys
from pathlib import Path
path = Path(sys.argv[1])
if not path.is_file():
    print("missing")
else:
    print(hashlib.sha256(path.read_bytes()).hexdigest())
PY
}

package_identity() {
  python3 "$identity_helper" "$1"
}

[ -d "$source_package" ] || { echo "expected package missing: $source_package" >&2; exit 1; }
[ ! -L "$source_package" ] || { echo "expected package must not be a symlink: $source_package" >&2; exit 1; }
[ -f "$source_package/package.json" ] || { echo "expected package.json missing: $source_package/package.json" >&2; exit 1; }
[ -f "$source_package/src/hooks/before-compact.ts" ] || { echo "expected before-compact hook missing: $source_package/src/hooks/before-compact.ts" >&2; exit 1; }
[ -f "$source_package/src/core/custom-message-classifier.ts" ] || { echo "expected custom-message classifier missing: $source_package/src/core/custom-message-classifier.ts" >&2; exit 1; }
[ ! -e "$source_package/node_modules" ] && [ ! -L "$source_package/node_modules" ] || {
  echo "expected package node_modules must be absent: $source_package/node_modules" >&2
  exit 1
}
source_hash="$(package_identity "$source_package")"
source_extension_hash="$(hash_file "$source_extension")"
[ "$source_extension_hash" != "missing" ] || { echo "source extension missing: $source_extension" >&2; exit 1; }

if [ "$source_only" -eq 1 ]; then
  bash -n "$0"
  # The source package intentionally has peer dependencies that are supplied by
  # Pi at install/runtime. The standalone extension is syntax-checked here;
  # package registration, hook loading, and native-retention behavior are
  # exercised against the selected candidate by the real-host integration.
  bun --check "$source_extension" >/dev/null
  if [ "$json_output" -eq 1 ]; then
    python3 - "$source_package" "$source_hash" <<'PY'
import json, sys
print(json.dumps({"sourcePackageHash": sys.argv[2], "sourcePackagePath": sys.argv[1]}, sort_keys=True))
PY
  else
    printf 'source package: %s %s\n' "$source_package" "$source_hash"
    printf 'source extension: %s %s\n' "$source_extension" "$source_extension_hash"
    echo "install state: source-only verification passed (Bash 3.2 portable; exact-one installed checks present)"
  fi
  exit 0
fi

python3 - "$agent_dir" <<'PY'
import os, stat, sys
from pathlib import Path
agent = Path(os.path.abspath(os.path.expanduser(sys.argv[1])))
current = Path(agent.anchor)
targets = [current]
for part in agent.parts[1:]:
    current /= part
    targets.append(current)
targets.extend((agent / "local-packages", agent / "local-packages/ai-configs"))
for path in targets:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        continue
    if stat.S_ISLNK(mode):
        raise SystemExit(f"pi-vcc managed path must not contain a symlink ancestor: {path}")
PY
command -v pi >/dev/null 2>&1 || { echo "Pi unavailable" >&2; exit 1; }
pi_version="$(pi --version 2>/dev/null)" || { echo "Pi unavailable" >&2; exit 1; }
stable_hash="missing"
if [ -d "$stable_package" ] && [ ! -L "$stable_package" ]; then
  stable_hash="$(package_identity "$stable_package")"
elif [ -L "$stable_package" ]; then
  echo "FAIL: stable mirror must not be a symlink" >&2
fi
live_extension_hash="$(hash_file "$live_extension")"

counts="$(python3 - "$settings" "$stable_package" "$live_extension" "$repo_root/scripts" <<'PY'
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[4])
from pi_vcc_registration import (
    PiGitUrlParserUnavailable,
    package_source,
    registration_counts,
    require_pi_package_root,
)

settings = Path(sys.argv[1])
stable_path = Path(sys.argv[2])
extension = os.path.realpath(os.path.expanduser(sys.argv[3]))
try:
    data = json.loads(settings.read_text())
except Exception:
    data = {}

try:
    # Fail closed: exact-one verification cannot pass when the Pi parser is unavailable.
    require_pi_package_root()
    stable_count, pi_vcc_count = registration_counts(data.get("packages"), stable_path)
except PiGitUrlParserUnavailable as exc:
    raise SystemExit(f"FAIL: pi-vcc registration classification unavailable: {exc}") from exc
extension_name = os.path.basename(extension)
non_local_prefixes = ("npm:", "git:", "http:", "https:", "github:", "ssh:")

def extension_classification(item):
    value = package_source(item)
    if not isinstance(value, str) or value.startswith(non_local_prefixes):
        return "other"
    expanded = os.path.expanduser(value)
    if not os.path.isabs(expanded):
        normalized = os.path.normpath(expanded).replace(os.sep, "/")
        if normalized == f".pi/agent/extensions/{extension_name}":
            return "managed"
        return "ambiguous" if os.path.basename(normalized) == extension_name else "other"
    return "managed" if os.path.realpath(expanded) == extension else "other"

classifications = [extension_classification(item) for item in data.get("extensions", []) if isinstance(data.get("extensions"), list)]
print(stable_count, pi_vcc_count, classifications.count("managed"), classifications.count("ambiguous"))
PY
)"
set -- $counts
registration_count="${1:-0}"
pi_vcc_registration_count="${2:-0}"
explicit_extension_count="${3:-0}"
ambiguous_extension_count="${4:-0}"
autodiscovered_extension_count=0
[ "$live_extension_hash" != "missing" ] && autodiscovered_extension_count=1
enabled_extension_count=$((autodiscovered_extension_count + explicit_extension_count))

failures=0
[ "$stable_hash" != "missing" ] || { echo "FAIL: stable mirror missing" >&2; failures=1; }
[ "$live_extension_hash" != "missing" ] || { echo "FAIL: live extension missing" >&2; failures=1; }
[ "$source_hash" = "$stable_hash" ] || { echo "FAIL: stable mirror hash differs from expected package" >&2; failures=1; }
[ "$source_extension_hash" = "$live_extension_hash" ] || { echo "FAIL: live extension hash differs from source" >&2; failures=1; }
[ "$registration_count" = "1" ] || { echo "FAIL: expected exactly one stable package registration" >&2; failures=1; }
[ "$pi_vcc_registration_count" = "1" ] || { echo "FAIL: expected exactly one total pi-vcc package registration" >&2; failures=1; }
[ "$ambiguous_extension_count" = "0" ] || { echo "FAIL: ambiguous relative percentage-compaction registration; use the managed ~/.pi/agent/extensions path or remove the explicit entry" >&2; failures=1; }
[ "$enabled_extension_count" = "1" ] || { echo "FAIL: expected exactly one enabled percentage-compaction extension path (autodiscovered plus explicit)" >&2; failures=1; }
if [ "$failures" -ne 0 ]; then
  echo "install state: strict installed verification failed" >&2
  exit 1
fi

if [ "$json_output" -eq 1 ]; then
  python3 - "$source_package" "$source_hash" "$stable_package" "$stable_hash" <<'PY'
import json, sys
print(json.dumps({
    "sourcePackageHash": sys.argv[2],
    "sourcePackagePath": sys.argv[1],
    "stablePackageHash": sys.argv[4],
    "stablePackagePath": sys.argv[3],
}, sort_keys=True))
PY
else
  printf 'Pi version: %s\n' "$pi_version"
  printf 'source package: %s %s\n' "$source_package" "$source_hash"
  printf 'stable mirror: %s %s\n' "$stable_package" "$stable_hash"
  printf 'source extension: %s %s\n' "$source_extension" "$source_extension_hash"
  printf 'live extension: %s %s\n' "$live_extension" "$live_extension_hash"
  printf 'stable package registrations: %s\n' "$registration_count"
  printf 'total pi-vcc package registrations: %s\n' "$pi_vcc_registration_count"
  printf 'autodiscovered extension paths: %s\n' "$autodiscovered_extension_count"
  printf 'explicit extension path registrations: %s\n' "$explicit_extension_count"
  printf 'ambiguous relative extension registrations: %s\n' "$ambiguous_extension_count"
  printf 'enabled extension paths: %s\n' "$enabled_extension_count"
  echo "install state: expected and installed hashes match; exact-one registration verified"
fi
