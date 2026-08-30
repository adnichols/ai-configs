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
    grep -q '^previous_tab = \["prefix+p", "alt+\[", "ctrl+alt+\["\]$' "$HERDR_CONFIG_PATH"
    grep -q '^next_tab = \["prefix+n", "alt+]", "ctrl+alt+]"\]$' "$HERDR_CONFIG_PATH"
    grep -q '^rename_tab = \["prefix+comma", "prefix+<"\]$' "$HERDR_CONFIG_PATH"
    grep -q '^key = "prefix+t"$' "$HERDR_CONFIG_PATH"
    grep -q '^command = "herdr-navigator.open"$' "$HERDR_CONFIG_PATH"
    grep -q '^last_pane = "prefix+;"$' "$HERDR_CONFIG_PATH"
    ! grep -q '^command = "herdr-navigator.jump-back"$' "$HERDR_CONFIG_PATH"
    ! grep -q '^key = "prefix+<"$' "$HERDR_CONFIG_PATH"
    ! grep -q 'fullerzz.sesh' "$HERDR_CONFIG_PATH"
    grep -q '^command = "persiyanov.reviewr.toggle"$' "$HERDR_CONFIG_PATH"
    ;;
  "plugin list")
    case "$4" in
      "herdr-navigator")
        case "$(cat "$HERDR_TEST_PLUGIN_STATE" 2>/dev/null || true)" in
          ready)
            printf '%s\n' '{"result":{"plugins":[{"plugin_id":"herdr-navigator","enabled":true,"actions":[{"id":"open"}],"source":{"kind":"github","owner":"thanhdat77","repo":"herdr-navigator","requested_ref":"v0.3.6"}}]}}'
            ;;
          wrong-source)
            printf '%s\n' '{"result":{"plugins":[{"plugin_id":"herdr-navigator","enabled":true,"actions":[{"id":"open"}],"source":{"kind":"github","owner":"other","repo":"navigator","requested_ref":"v9.9.9"}}]}}'
            ;;
          *)
            printf '%s\n' '{"result":{"plugins":[]}}'
            ;;
        esac
        ;;
      "cobanov.herdr-ntfysh")
        case "$(cat "$HERDR_TEST_NTFY_STATE" 2>/dev/null || true)" in
          ready)
            printf '%s\n' "{\"result\":{\"plugins\":[{\"plugin_id\":\"cobanov.herdr-ntfysh\",\"enabled\":true,\"plugin_root\":\"$HERDR_TEST_NTFY_PLUGIN_PATH\",\"source\":{\"kind\":\"local\"}}]}}"
            ;;
          github)
            printf '%s\n' '{"result":{"plugins":[{"plugin_id":"cobanov.herdr-ntfysh","enabled":true,"source":{"kind":"github","owner":"cobanov","repo":"herdr-ntfysh"}}]}}'
            ;;
          *)
            printf '%s\n' '{"result":{"plugins":[]}}'
            ;;
        esac
        ;;
      *)
        exit 2
        ;;
    esac
    ;;
  "plugin install")
    [[ "$3" == "thanhdat77/herdr-navigator" ]]
    [[ "$4" == "--ref" ]]
    [[ "$5" == "v0.3.6" ]]
    [[ "$6" == "--yes" ]]
    printf 'ready\n' > "$HERDR_TEST_PLUGIN_STATE"
    ;;
  "plugin link")
    [[ "$3" == "$HERDR_TEST_NTFY_PLUGIN_PATH" ]]
    printf 'ready\n' > "$HERDR_TEST_NTFY_STATE"
    ;;
  "plugin uninstall")
    [[ "$3" == "cobanov.herdr-ntfysh" ]]
    rm -f "$HERDR_TEST_NTFY_STATE"
    ;;
  "plugin enable")
    case "$3" in
      "herdr-navigator")
        [[ -s "$HERDR_TEST_PLUGIN_STATE" ]]
        ;;
      "cobanov.herdr-ntfysh")
        [[ -s "$HERDR_TEST_NTFY_STATE" ]]
        ;;
      *)
        exit 2
        ;;
    esac
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
HERDR_TEST_NTFY_STATE="$TMP_ROOT/ntfy-installed" \
HERDR_TEST_NTFY_PLUGIN_PATH="$REPO_ROOT/tools/herdr-ntfysh" \
HERDR_NTFY_SKIP_BUILD=1 \
HERDR_CONFIG_TARGET="$TARGET" \
  bash "$REPO_ROOT/herdr/install.sh" >/dev/null

cmp -s "$REPO_ROOT/herdr/config.toml" "$TARGET"
grep -q '^onboarding = true$' "$TARGET.before-ai-configs"
[[ "$(grep -c '^config check$' "$CALLS")" -eq 2 ]]
[[ "$(grep -c '^plugin list --plugin herdr-navigator --json$' "$CALLS")" -eq 3 ]]
[[ "$(grep -c '^plugin install thanhdat77/herdr-navigator --ref v0.3.6 --yes$' "$CALLS")" -eq 1 ]]
[[ "$(grep -c '^plugin enable herdr-navigator$' "$CALLS")" -eq 1 ]]
[[ "$(grep -c '^server reload-config$' "$CALLS")" -eq 1 ]]
# First run installs the vendored ntfysh: one link, one enable, one state query + one verify query.
[[ "$(grep -c '^plugin link ' "$CALLS")" -eq 1 ]]
[[ "$(grep -c '^plugin enable cobanov.herdr-ntfysh$' "$CALLS")" -eq 1 ]]
[[ "$(grep -c '^plugin list --plugin cobanov.herdr-ntfysh --json$' "$CALLS")" -eq 2 ]]

HERDR_BIN="$FAKE_HERDR" \
HERDR_TEST_CALLS="$CALLS" \
HERDR_TEST_PLUGIN_STATE="$TMP_ROOT/navigator-installed" \
HERDR_TEST_NTFY_STATE="$TMP_ROOT/ntfy-installed" \
HERDR_TEST_NTFY_PLUGIN_PATH="$REPO_ROOT/tools/herdr-ntfysh" \
HERDR_NTFY_SKIP_BUILD=1 \
HERDR_CONFIG_TARGET="$TARGET" \
  bash "$REPO_ROOT/herdr/install.sh" >/dev/null

grep -q '^onboarding = true$' "$TARGET.before-ai-configs"
[[ "$(grep -c '^plugin install thanhdat77/herdr-navigator --ref v0.3.6 --yes$' "$CALLS")" -eq 1 ]]
[[ "$(grep -c '^plugin enable herdr-navigator$' "$CALLS")" -eq 1 ]]
# Second run is a no-op for ntfysh (already linked and enabled).
[[ "$(grep -c '^plugin link ' "$CALLS")" -eq 1 ]]
[[ "$(grep -c '^plugin enable cobanov.herdr-ntfysh$' "$CALLS")" -eq 1 ]]
[[ "$(grep -c '^plugin list --plugin cobanov.herdr-ntfysh --json$' "$CALLS")" -eq 3 ]]

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
[[ "$(grep -c '^plugin install thanhdat77/herdr-navigator --ref v0.3.6 --yes$' "$CALLS")" -eq 1 ]]
[[ "$(grep -c '^plugin enable herdr-navigator$' "$CALLS")" -eq 1 ]]



# Replace an upstream GitHub-managed ntfysh (matching the machine's current
# state) with the vendored copy: uninstall, build (skipped here), link, enable.
printf 'ready\n' > "$TMP_ROOT/navigator-installed"
printf 'github\n' > "$TMP_ROOT/ntfy-installed"
HERDR_BIN="$FAKE_HERDR" \
HERDR_TEST_CALLS="$CALLS" \
HERDR_TEST_PLUGIN_STATE="$TMP_ROOT/navigator-installed" \
HERDR_TEST_NTFY_STATE="$TMP_ROOT/ntfy-installed" \
HERDR_TEST_NTFY_PLUGIN_PATH="$REPO_ROOT/tools/herdr-ntfysh" \
HERDR_NTFY_SKIP_BUILD=1 \
HERDR_CONFIG_TARGET="$TARGET" \
  bash "$REPO_ROOT/herdr/install.sh" >/dev/null
[[ "$(grep -c '^plugin uninstall cobanov.herdr-ntfysh$' "$CALLS")" -eq 1 ]]
[[ "$(grep -c '^plugin link ' "$CALLS")" -eq 2 ]]
[[ "$(grep -c '^plugin enable cobanov.herdr-ntfysh$' "$CALLS")" -eq 2 ]]
[[ "$(grep -c '^plugin list --plugin cobanov.herdr-ntfysh --json$' "$CALLS")" -eq 5 ]]
printf 'Herdr config installer tests passed.\n'
