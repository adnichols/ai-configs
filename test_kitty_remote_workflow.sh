#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT

FAKE_BIN="$TMP_ROOT/bin"
MAC_HOME="$TMP_ROOT/mac-home"
LINUX_HOME="$TMP_ROOT/linux-home"
mkdir -p "$FAKE_BIN" "$MAC_HOME" "$LINUX_HOME/.config/herdr"
printf '#!/usr/bin/env bash\nexit 0\n' > "$FAKE_BIN/kitty"
printf '#!/usr/bin/env bash\nprintf image > "$1"\n' > "$FAKE_BIN/pngpaste"
chmod +x "$FAKE_BIN/kitty" "$FAKE_BIN/pngpaste"

for run in 1 2; do
  HOME="$MAC_HOME" \
  PATH="$FAKE_BIN:/usr/bin:/bin" \
  KITTY_WORKFLOW_OS=Darwin \
  KITTY_WORKFLOW_SKIP_PACKAGES=1 \
  KITTY_WORKFLOW_REFRESH_INTEGRATIONS=0 \
    bash "$REPO_ROOT/kitty/install.sh" >/dev/null
done

[[ -x "$MAC_HOME/.local/bin/clipssh" ]]
[[ -x "$MAC_HOME/.local/bin/kitty-paste-image-to-ssh" ]]
[[ -f "$MAC_HOME/.config/kitty/ai-configs-remote-workflow.conf" ]]
grep -q '^allow_remote_control yes$' "$MAC_HOME/.config/kitty/ai-configs-remote-workflow.conf"
grep -q 'kitty-paste-image-to-ssh' "$MAC_HOME/.config/kitty/ai-configs-remote-workflow.conf"
[[ -f "$MAC_HOME/.config/ai-configs/kitty-remote-workflow.zsh" ]]
[[ "$(grep -c '^# BEGIN ai-configs kitty remote workflow$' "$MAC_HOME/.zshrc")" -eq 1 ]]
[[ "$(grep -c '^# BEGIN ai-configs kitty remote workflow$' "$MAC_HOME/.config/kitty/kitty.conf")" -eq 1 ]]
[[ "$(grep -c '^# BEGIN ai-configs kitty remote workflow$' "$MAC_HOME/.config/kitty/ssh.conf")" -eq 1 ]]
grep -q '^mbp=anichols@mbp$' "$MAC_HOME/.clipssh/aliases"
grep -q '^dever=anichols@dever$' "$MAC_HOME/.clipssh/aliases"

cat > "$LINUX_HOME/.config/herdr/config.toml" <<'EOF'
  [ui.toast]
  delivery = "system"

[update]
channel = "preview"
EOF
HOME="$LINUX_HOME" \
PATH="/usr/bin:/bin" \
KITTY_WORKFLOW_OS=Linux \
KITTY_WORKFLOW_REFRESH_INTEGRATIONS=0 \
  bash "$REPO_ROOT/kitty/install.sh" >/dev/null

grep -q '^delivery = "terminal"$' "$LINUX_HOME/.config/herdr/config.toml"
[[ "$(grep -c 'delivery.*=' "$LINUX_HOME/.config/herdr/config.toml")" -eq 1 ]]
grep -q '^\[update\]$' "$LINUX_HOME/.config/herdr/config.toml"
[[ ! -e "$LINUX_HOME/.config/kitty/kitty.conf" ]]

# Exercise the real clipssh transfer path with fake clipboard and SSH tools.
CAPTURE_DIR="$TMP_ROOT/capture"
mkdir -p "$CAPTURE_DIR"
cat > "$FAKE_BIN/ssh" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$TEST_CAPTURE_DIR/ssh-commands"
cat >/dev/null
EOF
cat > "$FAKE_BIN/pbcopy" <<'EOF'
#!/usr/bin/env bash
cat > "$TEST_CAPTURE_DIR/clipboard"
EOF
chmod +x "$FAKE_BIN/ssh" "$FAKE_BIN/pbcopy"
first_path="$(HOME="$MAC_HOME" PATH="$FAKE_BIN:/usr/bin:/bin" OSTYPE=darwin TEST_CAPTURE_DIR="$CAPTURE_DIR" CLIPSSH_REMOTE_DIR='~/.cache/clipssh' "$REPO_ROOT/scripts/clipssh" mbp >/dev/null; cat "$CAPTURE_DIR/clipboard")"
second_path="$(HOME="$MAC_HOME" PATH="$FAKE_BIN:/usr/bin:/bin" OSTYPE=darwin TEST_CAPTURE_DIR="$CAPTURE_DIR" CLIPSSH_REMOTE_DIR='~/.cache/clipssh' "$REPO_ROOT/scripts/clipssh" mbp >/dev/null; cat "$CAPTURE_DIR/clipboard")"
[[ "$first_path" == '~/.cache/clipssh/clipboard-'*.png ]]
[[ "$second_path" == '~/.cache/clipssh/clipboard-'*.png ]]
[[ "$first_path" != "$second_path" ]]
grep -q 'mkdir -p' "$CAPTURE_DIR/ssh-commands"
grep -q 'chmod 700' "$CAPTURE_DIR/ssh-commands"

bash -n \
  "$REPO_ROOT/kitty/install.sh" \
  "$REPO_ROOT/scripts/clipssh" \
  "$REPO_ROOT/scripts/kitty-paste-image-to-ssh" \
  "$REPO_ROOT/scripts/install-kitty-remote-hosts.sh"

echo "Kitty remote workflow tests passed."
