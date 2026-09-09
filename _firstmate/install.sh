#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TARGET_ROOT="${FIRSTMATE_HOME:-${FM_HOME:-$HOME/code/firstmate}}"

if [[ ! -d "$TARGET_ROOT" ]] || [[ ! -f "$TARGET_ROOT/bin/fm-spawn.sh" ]]; then
  echo "Error: $TARGET_ROOT is not a Firstmate home (missing directory or bin/fm-spawn.sh)" >&2
  exit 1
fi

install_managed_file() {
  local source="$1"
  local target="$2"
  local mode="$3"
  local label="$4"
  local backup="${target}.before-ai-configs"

  mkdir -p "$(dirname -- "$target")"
  if [[ -f "$target" ]] && ! cmp -s "$source" "$target" && [[ ! -e "$backup" ]]; then
    cp -p "$target" "$backup"
    chmod "$mode" "$backup"
    echo "Preserved previous $label at $backup"
  fi
  install -m "$mode" "$source" "$target"
  echo "Installed managed $label at $target"
}

while IFS=$'\t' read -r source_rel dest_rel mode; do
  [[ -n "$source_rel" ]] || continue
  source="$SOURCE_DIR/$source_rel"
  if [[ ! -f "$source" ]]; then
    echo "Error: missing managed source $source" >&2
    exit 1
  fi
  install_managed_file "$source" "$TARGET_ROOT/$dest_rel" "$mode" "$dest_rel"
done <<'EOF'
config/crew-dispatch.json	config/crew-dispatch.json	0644
config/crew-harness	config/crew-harness	0644
data/captain.md	data/captain.md	0644
data/captain-shared.md	data/captain-shared.md	0644
EOF
