#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
agent_dir="${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}"
source_package="$repo_root/_pi/packages/pi-vcc"
stable_package="$agent_dir/local-packages/ai-configs/pi-vcc"
source_extension="$repo_root/_pi/extensions/percentage-compaction.ts"
live_extension="$agent_dir/extensions/percentage-compaction.ts"
settings="$agent_dir/settings.json"

hash_tree() {
  local path="$1"
  if [[ ! -d "$path" ]]; then echo "missing"; return; fi
  (
    cd "$path"
    while IFS= read -r -d '' file; do
      printf '%s  %s\n' "$(sha256sum "$file" | awk '{print $1}')" "$file"
    done < <(find . -type f -print0 | sort -z)
  ) | sha256sum | awk '{print $1}'
}
hash_file() {
  local path="$1"
  [[ -f "$path" ]] && sha256sum "$path" | awk '{print $1}' || echo "missing"
}

source_hash="$(hash_tree "$source_package")"
stable_hash="$(hash_tree "$stable_package")"
source_extension_hash="$(hash_file "$source_extension")"
live_extension_hash="$(hash_file "$live_extension")"

registration="missing"
enabled_path="missing"
if [[ -f "$settings" ]]; then
  readarray -t values < <(python3 - "$settings" "$stable_package" "$live_extension" <<'PY'
import json, os, sys
from pathlib import Path
settings, stable, extension = Path(sys.argv[1]), os.path.realpath(os.path.expanduser(sys.argv[2])), os.path.realpath(os.path.expanduser(sys.argv[3]))
try: data = json.loads(settings.read_text())
except Exception: data = {}
def source(item):
    return item.get("source") if isinstance(item, dict) else item if isinstance(item, str) else None
packages = [os.path.realpath(os.path.expanduser(value)) for value in map(source, data.get("packages", [])) if isinstance(value, str) and not value.startswith(("npm:", "git:", "http:"))]
extensions = [os.path.realpath(os.path.expanduser(value)) for value in data.get("extensions", []) if isinstance(value, str)]
print("registered" if stable in packages else "missing")
print("enabled" if extension in extensions else "missing")
PY
  )
  registration="${values[0]:-missing}"
  enabled_path="${values[1]:-missing}"
fi

printf 'Pi version: %s\n' "$(pi --version 2>/dev/null || echo unavailable)"
printf 'source package: %s %s\n' "$source_package" "$source_hash"
printf 'stable mirror: %s %s\n' "$stable_package" "$stable_hash"
printf 'source extension: %s %s\n' "$source_extension" "$source_extension_hash"
printf 'live extension: %s %s\n' "$live_extension" "$live_extension_hash"
printf 'package registration: %s\n' "$registration"
printf 'enabled extension path: %s\n' "$enabled_path"

if [[ "$stable_hash" == "missing" || "$live_extension_hash" == "missing" ]]; then
  echo "install state: source valid; installed runtime incomplete (run ./install.sh --pi after checkpoint)"
elif [[ "$source_hash" != "$stable_hash" || "$source_extension_hash" != "$live_extension_hash" ]]; then
  echo "install state: installed drift from source (expected before parent installs reviewed checkpoint)"
else
  echo "install state: source and installed hashes match"
fi

[[ -f "$source_package/src/core/coordinator.ts" ]]
[[ -f "$source_extension" ]]
