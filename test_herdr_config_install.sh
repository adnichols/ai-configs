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
    grep -q '^previous_tab = \["prefix+p", "ctrl+alt+\[", "alt+\["\]$' "$HERDR_CONFIG_PATH"
    grep -q '^next_tab = \["prefix+n", "ctrl+alt+]", "alt+]"\]$' "$HERDR_CONFIG_PATH"
    grep -q '^rename_tab = "prefix+<"$' "$HERDR_CONFIG_PATH"
    grep -q '^key = "prefix+shift+t"$' "$HERDR_CONFIG_PATH"
    grep -q '^command = "herdr-navigator.open"$' "$HERDR_CONFIG_PATH"
    ! grep -q '^key = "prefix+<"$' "$HERDR_CONFIG_PATH"
    ! grep -q '^command = "fullerzz.sesh.open-picker"$' "$HERDR_CONFIG_PATH"
    ;;
  "plugin list")
    case "$(cat "$HERDR_TEST_PLUGIN_STATE" 2>/dev/null || true)" in
      ready)
        printf '%s\n' '{"result":{"plugins":[{"plugin_id":"herdr-navigator","enabled":true,"actions":[{"id":"open"}],"source":{"kind":"github","owner":"thanhdat77","repo":"herdr-navigator","requested_ref":"v0.3.3"}}]}}'
        ;;
      wrong-source)
        printf '%s\n' '{"result":{"plugins":[{"plugin_id":"herdr-navigator","enabled":true,"actions":[{"id":"open"}],"source":{"kind":"github","owner":"other","repo":"navigator","requested_ref":"v9.9.9"}}]}}'
        ;;
      *)
        printf '%s\n' '{"result":{"plugins":[]}}'
        ;;
    esac
    ;;
  "plugin install")
    [[ "$3" == "thanhdat77/herdr-navigator" ]]
    [[ "$4" == "--ref" ]]
    [[ "$5" == "v0.3.3" ]]
    [[ "$6" == "--yes" ]]
    printf 'ready\n' > "$HERDR_TEST_PLUGIN_STATE"
    ;;
  "plugin enable")
    [[ "$3" == "herdr-navigator" ]]
    [[ -s "$HERDR_TEST_PLUGIN_STATE" ]]
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
HERDR_TEST_PLUGIN_STATE="$TMP_ROOT/navigator-installed" \
HERDR_CONFIG_TARGET="$TARGET" \
  bash "$REPO_ROOT/herdr/install.sh" >/dev/null

cmp -s "$REPO_ROOT/herdr/config.toml" "$TARGET"
grep -q '^onboarding = true$' "$TARGET.before-ai-configs"
[[ "$(grep -c '^config check$' "$CALLS")" -eq 2 ]]
[[ "$(grep -c '^plugin list --plugin herdr-navigator --json$' "$CALLS")" -eq 3 ]]
[[ "$(grep -c '^plugin install thanhdat77/herdr-navigator --ref v0.3.3 --yes$' "$CALLS")" -eq 1 ]]
[[ "$(grep -c '^plugin enable herdr-navigator$' "$CALLS")" -eq 1 ]]
[[ "$(grep -c '^server reload-config$' "$CALLS")" -eq 1 ]]

HERDR_BIN="$FAKE_HERDR" \
HERDR_TEST_CALLS="$CALLS" \
HERDR_TEST_PLUGIN_STATE="$TMP_ROOT/navigator-installed" \
HERDR_CONFIG_TARGET="$TARGET" \
  bash "$REPO_ROOT/herdr/install.sh" >/dev/null

grep -q '^onboarding = true$' "$TARGET.before-ai-configs"
[[ "$(grep -c '^plugin install thanhdat77/herdr-navigator --ref v0.3.3 --yes$' "$CALLS")" -eq 1 ]]
[[ "$(grep -c '^plugin enable herdr-navigator$' "$CALLS")" -eq 1 ]]

printf 'wrong-source\n' > "$TMP_ROOT/navigator-installed"
if HERDR_BIN="$FAKE_HERDR" \
  HERDR_TEST_CALLS="$CALLS" \
  HERDR_TEST_PLUGIN_STATE="$TMP_ROOT/navigator-installed" \
  HERDR_CONFIG_TARGET="$TARGET" \
    bash "$REPO_ROOT/herdr/install.sh" >"$TMP_ROOT/wrong-source.out" 2>"$TMP_ROOT/wrong-source.err"; then
  echo 'Expected mismatched Herdr Navigator source to fail safely.' >&2
  exit 1
fi
grep -q 'different source or requested ref' "$TMP_ROOT/wrong-source.err"
[[ "$(grep -c '^plugin install thanhdat77/herdr-navigator --ref v0.3.3 --yes$' "$CALLS")" -eq 1 ]]
[[ "$(grep -c '^plugin enable herdr-navigator$' "$CALLS")" -eq 1 ]]
printf 'Herdr config installer tests passed.\n'
