#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TARGET_ROOT="${AMP_CONFIG_TARGET:-$HOME/.config/amp}"
TARGET_SETTINGS="$TARGET_ROOT/settings.json"
BACKUP_SETTINGS="${TARGET_SETTINGS}.before-ai-configs"
TARGET_PLUGINS="$TARGET_ROOT/plugins"
SOURCE_SETTINGS="$SOURCE_DIR/settings.json"
SOURCE_PLUGIN="$SOURCE_DIR/plugins/subscription-models.ts"
TARGET_PLUGIN="$TARGET_PLUGINS/subscription-models.ts"
BACKUP_PLUGIN="${TARGET_PLUGIN}.before-ai-configs"

# Orca owns this plugin on hosts where Orca is present. Never overwrite or remove it.
ORCA_PLUGIN_NAME="orca-agent-status.ts"

install_file() {
  local source="$1"
  local target="$2"
  local backup="$3"
  local mode="${4:-0644}"

  mkdir -p "$(dirname "$target")"
  if [[ -f "$target" ]] && ! cmp -s "$source" "$target" && [[ ! -e "$backup" ]]; then
    cp -p "$target" "$backup"
    echo "Preserved previous file at $backup"
  fi
  install -m "$mode" "$source" "$target"
}

if [[ ! -f "$SOURCE_SETTINGS" ]]; then
  echo "Missing managed Amp settings at $SOURCE_SETTINGS" >&2
  exit 1
fi
if [[ ! -f "$SOURCE_PLUGIN" ]]; then
  echo "Missing managed Amp plugin at $SOURCE_PLUGIN" >&2
  exit 1
fi

mkdir -p "$TARGET_ROOT" "$TARGET_PLUGINS"

install_file "$SOURCE_SETTINGS" "$TARGET_SETTINGS" "$BACKUP_SETTINGS" 0600
install_file "$SOURCE_PLUGIN" "$TARGET_PLUGIN" "$BACKUP_PLUGIN" 0644

if [[ -f "$TARGET_PLUGINS/$ORCA_PLUGIN_NAME" ]]; then
  echo "Left Orca-managed plugin in place: $TARGET_PLUGINS/$ORCA_PLUGIN_NAME"
fi

echo "Installed managed Amp config at $TARGET_ROOT"
echo "Managed surfaces:"
echo "  - settings.json (remote thread creation)"
echo "  - plugins/subscription-models.ts (ADN Low/Med/High/Ultra + Grok 4.5 modes)"
echo ""
echo "Note: Amp model-provider subscriptions (ChatGPT / SuperGrok) are host-local"
echo "credentials. On a new host, link them with:"
echo "  amp config model-providers add-chatgpt-subscription"
echo "  amp config model-providers list"
echo "  # then activate the desired ChatGPT + xAI subscriptions"
