#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_CONFIG="$SOURCE_DIR/config.toml"
TARGET_CONFIG="${HERDR_CONFIG_TARGET:-$HOME/.config/herdr/config.toml}"
BACKUP_CONFIG="${TARGET_CONFIG}.before-ai-configs"

find_herdr() {
  local candidate
  for candidate in "${HERDR_BIN:-}" "$HOME/.local/bin/herdr" /opt/homebrew/bin/herdr /usr/local/bin/herdr; do
    if [[ -n "$candidate" && -x "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  command -v herdr 2>/dev/null || return 1
}

validate_config() {
  local config="$1"
  local herdr_bin="${2:-}"

  if [[ -n "$herdr_bin" ]]; then
    HERDR_CONFIG_PATH="$config" "$herdr_bin" config check
  else
    echo "Herdr is not installed; deferring config validation until first launch."
  fi
}

herdr_bin="$(find_herdr || true)"
validate_config "$SOURCE_CONFIG" "$herdr_bin"

mkdir -p "$(dirname "$TARGET_CONFIG")"
if [[ -f "$TARGET_CONFIG" ]] && ! cmp -s "$SOURCE_CONFIG" "$TARGET_CONFIG" && [[ ! -e "$BACKUP_CONFIG" ]]; then
  cp -p "$TARGET_CONFIG" "$BACKUP_CONFIG"
  echo "Preserved previous Herdr config at $BACKUP_CONFIG"
fi

install -m 0644 "$SOURCE_CONFIG" "$TARGET_CONFIG"
validate_config "$TARGET_CONFIG" "$herdr_bin"
echo "Installed managed Herdr config at $TARGET_CONFIG"

if [[ -n "$herdr_bin" && "${HERDR_CONFIG_SKIP_RELOAD:-0}" != 1 ]]; then
  if "$herdr_bin" server reload-config >/dev/null 2>&1; then
    echo "Reloaded the running Herdr server configuration."
  else
    echo "No running Herdr server was reloaded; the config will apply on next launch."
  fi
fi
