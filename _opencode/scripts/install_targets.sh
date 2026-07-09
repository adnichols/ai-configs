#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_TARGET="${OPENCODE_RUNTIME_TARGET:-$HOME/.config/opencode}"
OBSIDIAN_TARGET="${OPENCODE_OBSIDIAN_TARGET:-$HOME/Documents/Obsidian/adn_vault/_opencode-dev}"

INSTALL_RUNTIME=1
INSTALL_OBSIDIAN=1
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage: ./scripts/install_targets.sh [options]

Install the managed OpenCode configuration from this repository into one or both targets.

Options:
  --runtime-only            Install only to ~/.config/opencode
  --obsidian-only           Install only to adn_vault/_opencode-dev
  --runtime-target PATH     Override the runtime target path
  --obsidian-target PATH    Override the Obsidian target path
  --dry-run                 Print actions without modifying files
  --help                    Show this help text
EOF
}

log() {
  printf '%s\n' "$*"
}

run_cmd() {
  if (( DRY_RUN )); then
    printf '+ '
    printf '%q ' "$@"
    printf '\n'
    return 0
  fi

  "$@"
}

ensure_dir() {
  run_cmd mkdir -p "$1"
}

copy_dir() {
  local rel="$1"
  local target_root="$2"
  local source_path="$ROOT/$rel"
  local target_path="$target_root/$rel"

  [[ -d "$source_path" ]] || return 0

  ensure_dir "$target_path"

  if (( DRY_RUN )); then
    log "+ rsync -a '$source_path/' '$target_path/'"
    return 0
  fi

  rsync -a "$source_path/" "$target_path/"
}

copy_file() {
  local rel="$1"
  local target_root="$2"
  local source_path="$ROOT/$rel"
  local target_path="$target_root/$rel"

  [[ -f "$source_path" ]] || return 0

  ensure_dir "$(dirname "$target_path")"

  if (( DRY_RUN )); then
    log "+ rsync -a '$source_path' '$target_path'"
    return 0
  fi

  rsync -a "$source_path" "$target_path"
}

copy_template_as_config() {
  local target_root="$1"
  local source_path="$ROOT/config-template.json"
  local target_path="$target_root/opencode.json"

  ensure_dir "$target_root"

  if [[ -f "$target_path" ]]; then
    log "Keeping existing config: $target_path"
    return 0
  fi

  if (( DRY_RUN )); then
    log "+ rsync -a '$source_path' '$target_path'"
    return 0
  fi

  rsync -a "$source_path" "$target_path"
}

remove_path() {
  local target_root="$1"
  local rel="$2"
  local target_path="$target_root/$rel"

  if [[ ! -e "$target_path" && ! -L "$target_path" ]]; then
    return 0
  fi

  run_cmd rm -rf "$target_path"
}

install_runtime() {
  local target_root="$1"

  log "Installing runtime profile to $target_root"

  local dirs=(agents commands prompts skills scripts)
  local files=(
    .gitignore
    AGENTS.md
    OPENCODE_ONBOARDING.md
    QUICKSTART.md
    config-template.json
    dcp.jsonc
    read-truncation-warning-plugin.js
    simple-plugin-test.js
    smart-title.jsonc
  )

  for dir in "${dirs[@]}"; do
    copy_dir "$dir" "$target_root"
  done

  for file in "${files[@]}"; do
    copy_file "$file" "$target_root"
  done

  copy_template_as_config "$target_root"
}

install_obsidian() {
  local target_root="$1"

  log "Installing Obsidian profile to $target_root"

  local dirs=(agents commands prompts skills scripts)
  local files=(
    .gitignore
    AGENTS.md
    QUICKSTART.md
    config-template.json
    dcp.jsonc
    read-truncation-warning-plugin.js
    simple-plugin-test.js
    smart-title.jsonc
  )
  local excluded_paths=(
    OPENCODE_ONBOARDING.md
    scripts/sync_to_repo.sh
    commands/cmd:wrap-gpt.md
    commands/cmd:wrap-k2.5.md
    commands/cmd:wrap-opus.md
  )

  for dir in "${dirs[@]}"; do
    copy_dir "$dir" "$target_root"
  done

  for file in "${files[@]}"; do
    copy_file "$file" "$target_root"
  done

  copy_template_as_config "$target_root"

  for rel in "${excluded_paths[@]}"; do
    remove_path "$target_root" "$rel"
  done
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --runtime-only)
      INSTALL_RUNTIME=1
      INSTALL_OBSIDIAN=0
      ;;
    --obsidian-only)
      INSTALL_RUNTIME=0
      INSTALL_OBSIDIAN=1
      ;;
    --runtime-target)
      shift
      RUNTIME_TARGET="$1"
      ;;
    --obsidian-target)
      shift
      OBSIDIAN_TARGET="$1"
      ;;
    --dry-run)
      DRY_RUN=1
      ;;
    --help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown option: %s\n\n' "$1" >&2
      usage >&2
      exit 1
      ;;
  esac
  shift
done

if (( INSTALL_RUNTIME )); then
  install_runtime "$RUNTIME_TARGET"
fi

if (( INSTALL_OBSIDIAN )); then
  install_obsidian "$OBSIDIAN_TARGET"
fi

log "Install complete."
