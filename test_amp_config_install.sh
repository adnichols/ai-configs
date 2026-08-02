#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT

TARGET_ROOT="$TMP_ROOT/home/.config/amp"
mkdir -p "$TARGET_ROOT/plugins"

# Pre-existing local settings + an Orca plugin must survive install semantics.
printf '%s\n' '{"amp.remoteThreadCreation.enabled": false, "local.only": true}' > "$TARGET_ROOT/settings.json"
printf 'orca-owned\n' > "$TARGET_ROOT/plugins/orca-agent-status.ts"
printf 'old-modes\n' > "$TARGET_ROOT/plugins/subscription-models.ts"

AMP_CONFIG_TARGET="$TARGET_ROOT" bash "$REPO_ROOT/amp/install.sh" >/dev/null

cmp -s "$REPO_ROOT/amp/settings.json" "$TARGET_ROOT/settings.json"
cmp -s "$REPO_ROOT/amp/plugins/subscription-models.ts" "$TARGET_ROOT/plugins/subscription-models.ts"
grep -q 'orca-owned' "$TARGET_ROOT/plugins/orca-agent-status.ts"
grep -q 'old-modes' "$TARGET_ROOT/plugins/subscription-models.ts.before-ai-configs"
grep -q '"local.only": true' "$TARGET_ROOT/settings.json.before-ai-configs"

# Second install must not rewrite backups.
AMP_CONFIG_TARGET="$TARGET_ROOT" bash "$REPO_ROOT/amp/install.sh" >/dev/null
grep -q 'old-modes' "$TARGET_ROOT/plugins/subscription-models.ts.before-ai-configs"
grep -q '"local.only": true' "$TARGET_ROOT/settings.json.before-ai-configs"
grep -q 'orca-owned' "$TARGET_ROOT/plugins/orca-agent-status.ts"

printf 'Amp config installer tests passed.\n'
