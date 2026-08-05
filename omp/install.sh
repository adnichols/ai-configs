#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TARGET_ROOT="${OMP_CONFIG_TARGET:-$HOME/.omp/agent}"
TARGET_CONFIG="$TARGET_ROOT/config.yml"
BACKUP_CONFIG="${TARGET_CONFIG}.before-ai-configs"
SOURCE_CONFIG="$SOURCE_DIR/config.yml"

if [[ ! -f "$SOURCE_CONFIG" ]]; then
  echo "Missing managed OMP config at $SOURCE_CONFIG" >&2
  exit 1
fi

mkdir -p "$TARGET_ROOT"

if [[ -f "$TARGET_CONFIG" ]] && ! cmp -s "$SOURCE_CONFIG" "$TARGET_CONFIG" && [[ ! -e "$BACKUP_CONFIG" ]]; then
  cp -p "$TARGET_CONFIG" "$BACKUP_CONFIG"
  chmod 0600 "$BACKUP_CONFIG"
  echo "Preserved previous OMP config at $BACKUP_CONFIG"
fi

install -m 0600 "$SOURCE_CONFIG" "$TARGET_CONFIG"
echo "Installed managed OMP config at $TARGET_CONFIG"
