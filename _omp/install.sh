#!/usr/bin/env bash
# Installs the tracked OMP config, guidance, custom agents, extensions, plugins, and ADN.
set -euo pipefail

SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TARGET_ROOT="${OMP_CONFIG_TARGET:-$HOME/.omp/agent}"
TARGET_CONFIG="$TARGET_ROOT/config.yml"
SOURCE_CONFIG="$SOURCE_DIR/config.yml"
SOURCE_MODELS="$SOURCE_DIR/models.yml"
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
  "$SOURCE_DIR/extensions/herdr-omp-agent-state.ts"
  "$SOURCE_DIR/extensions/orca-agent-status.ts"
  "$SOURCE_DIR/extensions/orca-prefill.ts"
  "$SOURCE_DIR/extensions/orca-titlebar-spinner.ts"
  "$SOURCE_DIR/extensions/thinking-shortcuts.ts"
)
SOURCE_ADN="$REPO_ROOT/_adn"
SOURCE_ADN_MANIFEST="$SOURCE_ADN/manifest.json"
SOURCE_ADN_SETUP="$SOURCE_ADN/scripts/setup-adn.ts"
OMP_CONFIG_PRUNE="${OMP_CONFIG_PRUNE:-0}"

for source in "$SOURCE_CONFIG" "$SOURCE_MODELS" "$SOURCE_GUIDANCE" "$SOURCE_DELIVERY_SKILL" "$SOURCE_DELIVERY_CLI" "$SOURCE_ADN_MANIFEST" "$SOURCE_ADN_SETUP" "${SOURCE_AGENTS[@]}" "${SOURCE_EXTENSIONS[@]}"; do
  if [[ ! -f "$source" ]]; then
    echo "Missing managed OMP file at $source" >&2
    exit 1
  fi
done
if [[ ! -d "$SOURCE_ADN" ]]; then
  echo "Missing captured ADN source at $SOURCE_ADN" >&2
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

install_omp_plugins() {
  echo "No managed OMP plugins"
}

install_adn() {
  local dest="$SHARED_TARGET/adn"
  if ! command -v rsync >/dev/null 2>&1; then
    echo "rsync is required to install ADN" >&2
    exit 1
  fi
  mkdir -p "$dest"
  rsync -a --delete --exclude locks --exclude '.DS_Store' --exclude '*.log' "$SOURCE_ADN/" "$dest/"
  echo "Installed managed ADN source at $dest"
  if [[ "${ADN_SKIP_APPLY:-0}" == "1" ]]; then
    echo "Skipped ADN apply (ADN_SKIP_APPLY=1)"
    return
  fi
  if ! command -v bun >/dev/null 2>&1; then
    echo "bun is required to apply ADN into the OMP agent profile" >&2
    exit 1
  fi
  if [[ -n "${OMP_CONFIG_TARGET:-}" ]]; then
    ADN_ROOT="$dest" bun "$dest/scripts/setup-adn.ts" apply --agent-root "$TARGET_ROOT"
  else
    ADN_ROOT="$dest" bun "$dest/scripts/setup-adn.ts" apply
  fi
}

preserve_unmanaged_tree_entries() {
  local target_dir="$1"
  local source_dir="$2"
  local backup_root=""
  local entry
  local basename

  [[ "$OMP_CONFIG_PRUNE" == "1" ]] || return 0
  [[ -d "$target_dir" ]] || return 0

  shopt -s nullglob dotglob
  for entry in "$target_dir"/*; do
    basename="$(basename -- "$entry")"
    [[ "$basename" == *.before-ai-configs ]] && continue
    [[ -e "$source_dir/$basename" || -L "$source_dir/$basename" ]] && continue

    if [[ -z "$backup_root" ]]; then
      backup_root="${TARGET_ROOT}.before-ai-configs/$(date -u +%Y%m%d-%H%M%S)-$$"
      mkdir -p "$backup_root/$(basename -- "$target_dir")"
    fi
    mv -- "$entry" "$backup_root/$(basename -- "$target_dir")/$basename"
    echo "Preserved unmanaged OMP entry at $backup_root/$(basename -- "$target_dir")/$basename"
  done
  shopt -u nullglob dotglob
}

preserve_unmanaged_path() {
  local target="$1"
  local backup_root

  [[ "$OMP_CONFIG_PRUNE" == "1" ]] || return 0
  [[ -e "$target" || -L "$target" ]] || return 0

  backup_root="${TARGET_ROOT}.before-ai-configs/$(date -u +%Y%m%d-%H%M%S)-$$"
  mkdir -p "$backup_root"
  mv -- "$target" "$backup_root/$(basename -- "$target")"
  echo "Preserved unmanaged OMP path at $backup_root/$(basename -- "$target")"
}

preserve_unmanaged_tree_entries "$TARGET_ROOT/agents" "$SOURCE_DIR/agents"
preserve_unmanaged_tree_entries "$TARGET_ROOT/extensions" "$SOURCE_DIR/extensions"
preserve_unmanaged_path "$TARGET_ROOT/commands"
preserve_unmanaged_path "$TARGET_ROOT/skills"
preserve_unmanaged_path "$TARGET_ROOT/SYSTEM.md"

install_managed_file "$SOURCE_CONFIG" "$TARGET_CONFIG" 0600 "OMP config"
if [[ -e "$TARGET_ROOT/models.yml" || -L "$TARGET_ROOT/models.yml" ]]; then
  echo "Preserved existing OMP models config at $TARGET_ROOT/models.yml"
else
  install_managed_file "$SOURCE_MODELS" "$TARGET_ROOT/models.yml" 0600 "OMP model overrides"
fi
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
install_omp_plugins
install_adn
