#!/usr/bin/env bash
# Installs the tracked Devin CLI global guidance and custom subagent profiles.
set -euo pipefail

SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TARGET_ROOT="${DEVIN_CONFIG_TARGET:-$HOME/.config/devin}"
SOURCE_GUIDANCE="$SOURCE_DIR/AGENTS.md"
SOURCE_AGENTS=(
  "$SOURCE_DIR/agents/oracle.md"
  "$SOURCE_DIR/agents/planner.md"
  "$SOURCE_DIR/agents/reviewer.md"
  "$SOURCE_DIR/agents/completeness.md"
)

for source in "$SOURCE_GUIDANCE" "${SOURCE_AGENTS[@]}"; do
  if [[ ! -f "$source" ]]; then
    echo "Missing managed Devin file at $source" >&2
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

# Devin's CLI-owned files (config.json, cli/, sessions) are never managed here.
# The skills directory is user-extensible; only prune entries that can no
# longer resolve at all (dangling symlinks), preserving them under a timestamped
# backup root instead of deleting.
prune_dangling_skill_links() {
  local skills_dir="$TARGET_ROOT/skills"
  local entry
  local backup_root=""

  [[ -d "$skills_dir" ]] || return 0

  shopt -s nullglob dotglob
  for entry in "$skills_dir"/*; do
    [[ -L "$entry" ]] || continue
    [[ -e "$entry" ]] && continue

    if [[ -z "$backup_root" ]]; then
      backup_root="${TARGET_ROOT}.before-ai-configs/$(date -u +%Y%m%d-%H%M%S)-$$"
      mkdir -p "$backup_root/skills"
    fi
    mv -- "$entry" "$backup_root/skills/$(basename -- "$entry")"
    echo "Pruned dangling Devin skill link $(basename -- "$entry") (preserved at $backup_root/skills)"
  done
  shopt -u nullglob dotglob
}

prune_dangling_skill_links

install_managed_file "$SOURCE_GUIDANCE" "$TARGET_ROOT/AGENTS.md" 0644 "Devin guidance"
for source in "${SOURCE_AGENTS[@]}"; do
  install_managed_file "$source" "$TARGET_ROOT/agents/$(basename -- "$source")" 0644 "Devin agent"
done

echo "Devin CLI global configuration installed"
