#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
agent_dir="${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}"
source_package="$repo_root/_pi/packages/pi-vcc"
stable_package="$agent_dir/local-packages/ai-configs/pi-vcc"
source_extension="$repo_root/_pi/extensions/percentage-compaction.ts"
live_extension="$agent_dir/extensions/percentage-compaction.ts"
settings="$agent_dir/settings.json"
source_only=0

usage() {
  echo "Usage: $0 [--source-only]"
  echo "  default: verify exact-one installed registration and source-identical mirrors"
  echo "  --source-only: verify source syntax and Bash 3.2 portability constraints"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --source-only) source_only=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

hash_path() {
  python3 - "$1" <<'PY'
import hashlib
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.exists():
    print("missing")
    raise SystemExit(0)
hash_value = hashlib.sha256()
if path.is_file():
    hash_value.update(path.read_bytes())
else:
    for child in sorted(item for item in path.rglob("*") if item.is_file()):
        relative = child.relative_to(path).as_posix().encode()
        hash_value.update(len(relative).to_bytes(8, "big"))
        hash_value.update(relative)
        content = child.read_bytes()
        hash_value.update(len(content).to_bytes(8, "big"))
        hash_value.update(content)
print(hash_value.hexdigest())
PY
}

source_hash="$(hash_path "$source_package")"
source_extension_hash="$(hash_path "$source_extension")"
[ "$source_hash" != "missing" ] || { echo "source package missing: $source_package" >&2; exit 1; }
[ "$source_extension_hash" != "missing" ] || { echo "source extension missing: $source_extension" >&2; exit 1; }
[ -f "$source_package/src/core/coordinator.ts" ] || { echo "source coordinator missing" >&2; exit 1; }
[ -f "$source_package/src/core/custom-message-classifier.ts" ] || { echo "source custom-message classifier missing" >&2; exit 1; }

if [ "$source_only" -eq 1 ]; then
  bash -n "$0"
  bun --check "$source_package/src/core/coordinator.ts" >/dev/null
  bun --check "$source_package/index.ts" >/dev/null
  bun --check "$source_extension" >/dev/null
  printf 'source package: %s %s\n' "$source_package" "$source_hash"
  printf 'source extension: %s %s\n' "$source_extension" "$source_extension_hash"
  echo "install state: source-only verification passed (Bash 3.2 portable; exact-one installed checks present)"
  exit 0
fi

command -v pi >/dev/null 2>&1 || { echo "Pi unavailable" >&2; exit 1; }
pi_version="$(pi --version 2>/dev/null)" || { echo "Pi unavailable" >&2; exit 1; }
stable_hash="$(hash_path "$stable_package")"
live_extension_hash="$(hash_path "$live_extension")"

counts="$(python3 - "$settings" "$stable_package" "$live_extension" <<'PY'
import json
import os
import sys
from pathlib import Path

settings = Path(sys.argv[1])
stable = os.path.realpath(os.path.expanduser(sys.argv[2]))
extension = os.path.realpath(os.path.expanduser(sys.argv[3]))
try:
    data = json.loads(settings.read_text())
except Exception:
    data = {}

def source(item):
    if isinstance(item, dict):
        return item.get("source")
    return item if isinstance(item, str) else None

packages = []
for item in data.get("packages", []):
    value = source(item)
    if isinstance(value, str) and not value.startswith(("npm:", "git:", "http:")):
        packages.append(os.path.realpath(os.path.expanduser(value)))
extensions = [
    os.path.realpath(os.path.expanduser(value))
    for value in data.get("extensions", [])
    if isinstance(value, str)
]
print(f"{packages.count(stable)} {extensions.count(extension)}")
PY
)"
set -- $counts
registration_count="${1:-0}"
extension_count="${2:-0}"

printf 'Pi version: %s\n' "$pi_version"
printf 'source package: %s %s\n' "$source_package" "$source_hash"
printf 'stable mirror: %s %s\n' "$stable_package" "$stable_hash"
printf 'source extension: %s %s\n' "$source_extension" "$source_extension_hash"
printf 'live extension: %s %s\n' "$live_extension" "$live_extension_hash"
printf 'stable package registrations: %s\n' "$registration_count"
printf 'enabled extension path registrations: %s\n' "$extension_count"

failures=0
[ "$stable_hash" != "missing" ] || { echo "FAIL: stable mirror missing" >&2; failures=1; }
[ "$live_extension_hash" != "missing" ] || { echo "FAIL: live extension missing" >&2; failures=1; }
[ "$source_hash" = "$stable_hash" ] || { echo "FAIL: stable mirror hash differs from source" >&2; failures=1; }
[ "$source_extension_hash" = "$live_extension_hash" ] || { echo "FAIL: live extension hash differs from source" >&2; failures=1; }
[ "$registration_count" = "1" ] || { echo "FAIL: expected exactly one stable package registration" >&2; failures=1; }
[ "$extension_count" = "1" ] || { echo "FAIL: expected exactly one enabled percentage-compaction extension path" >&2; failures=1; }

if [ "$failures" -ne 0 ]; then
  echo "install state: strict installed verification failed" >&2
  exit 1
fi

echo "install state: source and installed hashes match; exact-one registration verified"
