#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT
FIXTURE_REPO="$TMP_ROOT/repo"
FAKE_BIN="$TMP_ROOT/bin"
KITTY_MARKER="$TMP_ROOT/kitty-ran"
mkdir -p "$FIXTURE_REPO/scripts" "$FIXTURE_REPO/herdr" "$FIXTURE_REPO/kitty" "$FAKE_BIN"

cp "$REPO_ROOT/scripts/install-kitty-remote-hosts.sh" "$FIXTURE_REPO/scripts/"
printf '#!/usr/bin/env bash\nexit 23\n' > "$FIXTURE_REPO/herdr/install.sh"
printf 'test-config = true\n' > "$FIXTURE_REPO/herdr/config.toml"
printf '#!/usr/bin/env bash\ntouch "$KITTY_TEST_MARKER"\n' > "$FIXTURE_REPO/kitty/install.sh"
printf '#!/usr/bin/env bash\nexit 0\n' > "$FIXTURE_REPO/scripts/clipssh"
printf '#!/usr/bin/env bash\nexit 0\n' > "$FIXTURE_REPO/scripts/kitty-paste-image-to-ssh"

cat > "$FAKE_BIN/ssh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
remote_command="${!#}"
bash -c "$remote_command"
SH
chmod +x "$FAKE_BIN/ssh"

if PATH="$FAKE_BIN:$PATH" \
  KITTY_TEST_MARKER="$KITTY_MARKER" \
  KITTY_REMOTE_HOSTS=test-host \
  KITTY_WORKFLOW_STRICT_REMOTE=1 \
    bash "$FIXTURE_REPO/scripts/install-kitty-remote-hosts.sh" >/dev/null 2>&1; then
  echo "Expected remote deployment to fail when the Herdr installer fails." >&2
  exit 1
fi

[[ ! -e "$KITTY_MARKER" ]]
printf 'Herdr remote deployment failure propagation test passed.\n'
