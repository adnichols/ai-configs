#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT

TARGET="$TMP_ROOT/home/.config/herdr/config.toml"
FAKE_HERDR="$TMP_ROOT/herdr"
CALLS="$TMP_ROOT/calls"
mkdir -p "$(dirname "$TARGET")"
printf 'onboarding = true\n' > "$TARGET"

cat > "$FAKE_HERDR" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "$HERDR_TEST_CALLS"
case "$1 $2" in
  "config check")
    grep -q '^previous_tab = \["prefix+p", "alt+\["\]$' "$HERDR_CONFIG_PATH"
    ;;
  "server reload-config")
    ;;
  *)
    exit 2
    ;;
esac
SH
chmod +x "$FAKE_HERDR"

HERDR_BIN="$FAKE_HERDR" \
HERDR_TEST_CALLS="$CALLS" \
HERDR_CONFIG_TARGET="$TARGET" \
  bash "$REPO_ROOT/herdr/install.sh" >/dev/null

cmp -s "$REPO_ROOT/herdr/config.toml" "$TARGET"
grep -q '^onboarding = true$' "$TARGET.before-ai-configs"
[[ "$(grep -c '^config check$' "$CALLS")" -eq 2 ]]
[[ "$(grep -c '^server reload-config$' "$CALLS")" -eq 1 ]]

HERDR_BIN="$FAKE_HERDR" \
HERDR_TEST_CALLS="$CALLS" \
HERDR_CONFIG_TARGET="$TARGET" \
  bash "$REPO_ROOT/herdr/install.sh" >/dev/null

grep -q '^onboarding = true$' "$TARGET.before-ai-configs"
printf 'Herdr config installer tests passed.\n'
