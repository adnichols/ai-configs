#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_CONFIG="$SOURCE_DIR/config.toml"
TARGET_CONFIG="${HERDR_CONFIG_TARGET:-$HOME/.config/herdr/config.toml}"
BACKUP_CONFIG="${TARGET_CONFIG}.before-ai-configs"
NAVIGATOR_PLUGIN_ID="herdr-navigator"
NAVIGATOR_PLUGIN_OWNER="thanhdat77"
NAVIGATOR_PLUGIN_REPO="herdr-navigator"
NAVIGATOR_PLUGIN_SOURCE="$NAVIGATOR_PLUGIN_OWNER/$NAVIGATOR_PLUGIN_REPO"
NAVIGATOR_PLUGIN_REF="v0.3.3"

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

navigator_plugin_state() {
  local herdr_bin="$1"

  "$herdr_bin" plugin list --plugin "$NAVIGATOR_PLUGIN_ID" --json | python3 -c '
import json
import sys

plugin_id, owner, repo, requested_ref = sys.argv[1:]
try:
    payload = json.load(sys.stdin)
except (json.JSONDecodeError, OSError):
    raise SystemExit(1)

plugins = payload.get("result", {}).get("plugins", [])
plugin = next((item for item in plugins if item.get("plugin_id") == plugin_id), None)
if plugin is None:
    print("missing")
    raise SystemExit(0)

source = plugin.get("source") or {}
if (
    source.get("kind") != "github"
    or source.get("owner") != owner
    or source.get("repo") != repo
    or source.get("requested_ref") != requested_ref
):
    print("wrong-source")
elif not any(action.get("id") == "open" for action in plugin.get("actions", [])):
    print("missing-open-action")
elif plugin.get("enabled") is True:
    print("ready")
else:
    print("disabled")
' "$NAVIGATOR_PLUGIN_ID" "$NAVIGATOR_PLUGIN_OWNER" "$NAVIGATOR_PLUGIN_REPO" "$NAVIGATOR_PLUGIN_REF"
}

ensure_navigator_plugin() {
  local herdr_bin="$1"
  local state

  if ! state="$(navigator_plugin_state "$herdr_bin")"; then
    echo "Unable to inspect the installed Herdr Navigator plugin." >&2
    return 1
  fi

  case "$state" in
    ready)
      return 0
      ;;
    missing)
      "$herdr_bin" plugin install "$NAVIGATOR_PLUGIN_SOURCE" --ref "$NAVIGATOR_PLUGIN_REF" --yes
      ;;
    disabled)
      ;;
    wrong-source)
      echo "Refusing to replace $NAVIGATOR_PLUGIN_ID: the installed plugin has a different source or requested ref." >&2
      return 1
      ;;
    missing-open-action)
      echo "Herdr Navigator is missing its required open action; reinstall the managed $NAVIGATOR_PLUGIN_SOURCE plugin." >&2
      return 1
      ;;
    *)
      echo "Unexpected Herdr Navigator plugin state: $state" >&2
      return 1
      ;;
  esac

  "$herdr_bin" plugin enable "$NAVIGATOR_PLUGIN_ID"

  state="$(navigator_plugin_state "$herdr_bin")" || {
    echo "Unable to verify the installed Herdr Navigator plugin." >&2
    return 1
  }
  if [[ "$state" != "ready" ]]; then
    echo "Herdr Navigator is not enabled with its managed open action after installation (state: $state)." >&2
    return 1
  fi
}

herdr_bin="$(find_herdr || true)"
validate_config "$SOURCE_CONFIG" "$herdr_bin"

if [[ -n "$herdr_bin" ]]; then
  ensure_navigator_plugin "$herdr_bin"
else
  echo "Herdr is not installed; deferring Herdr Navigator installation until first config install."
fi

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
