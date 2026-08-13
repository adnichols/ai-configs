#!/usr/bin/env bash
# Installs the tracked OMP config, guidance, custom agents, and extensions.
set -euo pipefail

SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TARGET_ROOT="${OMP_CONFIG_TARGET:-$HOME/.omp/agent}"
TARGET_CONFIG="$TARGET_ROOT/config.yml"
SOURCE_CONFIG="$SOURCE_DIR/config.yml"
SOURCE_GUIDANCE="$SOURCE_DIR/AGENTS.md"
REPO_ROOT="$(cd -- "$SOURCE_DIR/.." && pwd)"
SOURCE_DELIVERY_SKILL="$REPO_ROOT/skills/delivery-run/SKILL.md"
SOURCE_DELIVERY_CLI="$REPO_ROOT/skills/delivery-run/scripts/delivery"
SHARED_TARGET="${OMP_SHARED_TARGET:-$HOME/.agents}"
BIN_TARGET="${OMP_BIN_TARGET:-$HOME/.local/bin}"
SOURCE_AGENTS=(
  "$SOURCE_DIR/agents/oracle.md"
  "$SOURCE_DIR/agents/planner.md"
  "$SOURCE_DIR/agents/reviewer.md"
  "$SOURCE_DIR/agents/completeness.md"
)
SOURCE_EXTENSIONS=(
  "$SOURCE_DIR/extensions/deepinfra.ts"
)

for source in "$SOURCE_CONFIG" "$SOURCE_GUIDANCE" "$SOURCE_DELIVERY_SKILL" "$SOURCE_DELIVERY_CLI" "${SOURCE_AGENTS[@]}" "${SOURCE_EXTENSIONS[@]}"; do
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
for source in "${SOURCE_EXTENSIONS[@]}"; do
  install_managed_file "$source" "$TARGET_ROOT/extensions/$(basename -- "$source")" 0644 "OMP extension"
done

install_managed_file "$SOURCE_DELIVERY_SKILL" "$SHARED_TARGET/skills/delivery-run/SKILL.md" 0644 "OMP delivery skill"
install_managed_file "$SOURCE_DELIVERY_CLI" "$SHARED_TARGET/scripts/delivery" 0755 "delivery CLI"
mkdir -p "$BIN_TARGET"
ln -sfn "$SHARED_TARGET/scripts/delivery" "$BIN_TARGET/delivery"
echo "Installed delivery command at $BIN_TARGET/delivery"
