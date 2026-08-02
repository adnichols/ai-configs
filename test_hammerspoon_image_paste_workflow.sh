#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT

MAC_HOME="$TMP_ROOT/mac-home"
LEGACY_HOME="$TMP_ROOT/legacy-home"
LINUX_HOME="$TMP_ROOT/linux-home"
FAKE_BIN="$TMP_ROOT/bin"
mkdir -p "$MAC_HOME" "$LEGACY_HOME/.hammerspoon" "$LINUX_HOME" "$FAKE_BIN"
printf '#!/usr/bin/env bash\nexit 0\n' > "$FAKE_BIN/pngpaste"
chmod +x "$FAKE_BIN/pngpaste"

for run in 1 2; do
  HOME="$MAC_HOME" \
  PATH="$FAKE_BIN:/usr/bin:/bin" \
  HSP_WORKFLOW_OS=Darwin \
  HSP_WORKFLOW_SKIP_PACKAGES=1 \
    bash "$REPO_ROOT/hammerspoon/install.sh" >/dev/null
done

[[ -x "$MAC_HOME/.local/bin/remote-image-paste" ]]
[[ -f "$MAC_HOME/.hammerspoon/init.lua" ]]
[[ "$(grep -c '^-- BEGIN ai-configs remote image paste$' "$MAC_HOME/.hammerspoon/init.lua")" -eq 1 ]]
[[ "$(grep -c '^-- END ai-configs remote image paste$' "$MAC_HOME/.hammerspoon/init.lua")" -eq 1 ]]
grep -q 'com.mitchellh.ghostty' "$MAC_HOME/.hammerspoon/init.lua"
grep -q 'return false' "$MAC_HOME/.hammerspoon/init.lua"
bash -n "$MAC_HOME/.local/bin/remote-image-paste" "$REPO_ROOT/hammerspoon/install.sh"

if HOME="$TMP_ROOT/missing-pngpaste-home" \
  PATH="/usr/bin:/bin" \
  HSP_WORKFLOW_OS=Darwin \
  HSP_WORKFLOW_SKIP_PACKAGES=1 \
    bash "$REPO_ROOT/hammerspoon/install.sh" >/dev/null 2>&1; then
  echo "installer succeeded despite missing pngpaste" >&2
  exit 1
fi

cat > "$LEGACY_HOME/.hammerspoon/init.lua" <<'EOF'
-- Cmd+Shift+V uploads the current local clipboard image to both coding hosts
local remoteImagePaste = os.getenv("HOME") .. "/.local/bin/remote-image-paste"
remoteImagePasteTap:start()
EOF
HOME="$LEGACY_HOME" \
PATH="$FAKE_BIN:/usr/bin:/bin" \
HSP_WORKFLOW_OS=Darwin \
HSP_WORKFLOW_SKIP_PACKAGES=1 \
  bash "$REPO_ROOT/hammerspoon/install.sh" >/dev/null
[[ "$(grep -c '^-- BEGIN ai-configs remote image paste$' "$LEGACY_HOME/.hammerspoon/init.lua")" -eq 1 ]]
[[ "$(grep -c 'remoteImagePasteTap:start()' "$LEGACY_HOME/.hammerspoon/init.lua")" -eq 1 ]]

HOME="$LINUX_HOME" \
HSP_WORKFLOW_OS=Linux \
  bash "$REPO_ROOT/hammerspoon/install.sh" >/dev/null
[[ ! -e "$LINUX_HOME/.local/bin/remote-image-paste" ]]
[[ ! -e "$LINUX_HOME/.hammerspoon/init.lua" ]]

echo "Hammerspoon image-paste workflow tests passed."
