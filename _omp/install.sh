#!/usr/bin/env bash
# Installs the tracked OMP config, guidance, and custom agents.
set -euo pipefail

SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TARGET_ROOT="${OMP_CONFIG_TARGET:-$HOME/.omp/agent}"
TARGET_CONFIG="$TARGET_ROOT/config.yml"
SOURCE_CONFIG="$SOURCE_DIR/config.yml"
SOURCE_GUIDANCE="$SOURCE_DIR/AGENTS.md"
SOURCE_AGENTS=(
  "$SOURCE_DIR/agents/oracle.md"
  "$SOURCE_DIR/agents/reviewer.md"
)

for source in "$SOURCE_CONFIG" "$SOURCE_GUIDANCE" "${SOURCE_AGENTS[@]}"; do
  if [[ ! -f "$source" ]]; then
    echo "Missing managed OMP file at $source" >&2
    exit 1
  fi
done

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

install_managed_file "$SOURCE_CONFIG" "$TARGET_CONFIG" 0600 "OMP config"
install_managed_file "$SOURCE_GUIDANCE" "$TARGET_ROOT/AGENTS.md" 0644 "OMP guidance"
for source in "${SOURCE_AGENTS[@]}"; do
  install_managed_file "$source" "$TARGET_ROOT/agents/$(basename -- "$source")" 0644 "OMP agent"
done
