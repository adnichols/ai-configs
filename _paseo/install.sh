#!/usr/bin/env bash
# Installs the tracked Paseo daemon config and repo-managed Paseo skills.
#
# The daemon config is deep-merged into ~/.paseo/config.json so host-local
# keys survive; managed keys are authoritative. The bundled Paseo skills are
# deselected via agents.skills.selection (mode "custom", empty list) because
# the daemon rewrites managed skill files from its npm bundle at startup —
# repo-tuned copies under the same names would be reverted. This installer
# owns the paseo* skill directories in each runtime skills root instead.
set -euo pipefail

SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TARGET_ROOT="${PASEO_CONFIG_TARGET:-$HOME/.paseo}"
TARGET_CONFIG="$TARGET_ROOT/config.json"
SOURCE_CONFIG="$SOURCE_DIR/config.json"
SOURCE_SKILLS_DIR="$SOURCE_DIR/skills"
MERGE_CONFIG="$SOURCE_DIR/merge_config.py"

# Runtime skill roots the Paseo daemon normally fans its bundled skills out to.
# Overridable for tests: space-separated list of skills directories.
SKILL_TARGETS="${PASEO_SKILL_TARGETS:-$HOME/.agents/skills $HOME/.claude/skills $HOME/.codex/skills}"

for source in "$SOURCE_CONFIG" "$MERGE_CONFIG"; do
  if [[ ! -f "$source" ]]; then
    echo "Missing managed Paseo file at $source" >&2
    exit 1
  fi
done
if [[ ! -d "$SOURCE_SKILLS_DIR" ]]; then
  echo "Missing managed Paseo skills directory at $SOURCE_SKILLS_DIR" >&2
  exit 1
fi

install_skill_dir() {
  local source="$1"
  local target="$2"
  local name
  name="$(basename -- "$source")"
  local backup="${target}.before-ai-configs"

  mkdir -p "$(dirname -- "$target")"
  if [[ -d "$target" ]] && ! diff -r -q --exclude='.paseo-managed-files.json' "$source" "$target" >/dev/null 2>&1; then
    if [[ ! -e "$backup" ]]; then
      cp -a "$target" "$backup"
      echo "Preserved previous Paseo skill $name at $backup"
    fi
  fi
  rm -rf -- "$target"
  cp -a "$source" "$target"
  # The daemon's managed-files manifest is meaningless once the skill is
  # deselected; drop it so nothing mistakes this copy for daemon-managed.
  rm -f -- "$target/.paseo-managed-files.json"
  echo "Installed managed Paseo skill $name at $target"
}

python3 "$MERGE_CONFIG" "$SOURCE_CONFIG" "$TARGET_CONFIG"

shopt -s nullglob
for skill_source in "$SOURCE_SKILLS_DIR"/*/; do
  skill_name="$(basename -- "$skill_source")"
  for root in $SKILL_TARGETS; do
    install_skill_dir "$skill_source" "$root/$skill_name"
  done
done
shopt -u nullglob

# Apply the merged config to a running daemon without a restart. A restart
# also works; reload just avoids interrupting running agents.
if [[ "${PASEO_SKIP_RELOAD:-0}" != 1 ]] && command -v paseo >/dev/null 2>&1; then
  if paseo reload >/dev/null 2>&1; then
    echo "Reloaded Paseo daemon config"
  else
    echo "Paseo daemon not reloaded (not running or unreachable); config applies on next start"
  fi
fi

echo "Paseo configuration installed"
