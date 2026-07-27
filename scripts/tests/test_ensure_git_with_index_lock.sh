#!/usr/bin/env bash
# Tests for scripts/ensure-git-with-index-lock bootstrap behavior.
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENSURE="$REPO_ROOT/scripts/ensure-git-with-index-lock"
PASS=0
FAIL=0

ok() { PASS=$((PASS + 1)); printf 'OK: %s\n' "$*"; }
bad() { FAIL=$((FAIL + 1)); printf 'FAIL: %s\n' "$*"; }

chmod +x "$ENSURE" "$REPO_ROOT/scripts/git-with-index-lock"

TMP_HOME="$(mktemp -d -t ensure-git-wl-home.XXXXXX)"
cleanup() { rm -rf "$TMP_HOME"; }
trap cleanup EXIT

export HOME="$TMP_HOME"
export PATH="/usr/bin:/bin:/usr/sbin:/sbin"
unset AI_CONFIGS_ROOT

# From repo scripts path with empty home: should install into fake HOME and print link/dest.
set +e
OUT="$(ENSURE_GIT_WL_QUIET=1 "$ENSURE" 2>/tmp/ensure-git-wl.err)"
RC=$?
set -e
if [[ $RC -eq 0 && -x "$OUT" && "$OUT" == *git-with-index-lock ]]; then
  ok "bootstraps into empty HOME from script location ($OUT)"
else
  bad "bootstrap empty HOME rc=$RC out=$OUT err=$(cat /tmp/ensure-git-wl.err)"
fi

if [[ -x "$HOME/.agents/scripts/git-with-index-lock" && -L "$HOME/.local/bin/git-with-index-lock" ]]; then
  ok "installs agents/scripts copy and local/bin symlink"
else
  bad "missing install artifacts under $HOME"
fi

# Second call should hit PATH/install short-circuit.
export PATH="$HOME/.local/bin:$PATH"
set +e
OUT2="$(ENSURE_GIT_WL_QUIET=1 "$ENSURE" 2>/dev/null)"
RC2=$?
set -e
if [[ $RC2 -eq 0 && -x "$OUT2" ]]; then
  ok "second resolve uses installed binary"
else
  bad "second resolve rc=$RC2 out=$OUT2"
fi

# Locate-only mode with AI_CONFIGS_ROOT and wiped install dirs.
rm -rf "$HOME/.agents" "$HOME/.local"
export PATH="/usr/bin:/bin"
export AI_CONFIGS_ROOT="$REPO_ROOT"
set +e
OUT3="$(ENSURE_GIT_WL_INSTALL=0 ENSURE_GIT_WL_QUIET=1 "$ENSURE" 2>/dev/null)"
RC3=$?
set -e
if [[ $RC3 -eq 0 && "$OUT3" == "$REPO_ROOT/scripts/git-with-index-lock" ]]; then
  ok "AI_CONFIGS_ROOT locate-only returns repo script"
else
  bad "locate-only rc=$RC3 out=$OUT3"
fi

printf 'pass=%s fail=%s\n' "$PASS" "$FAIL"
if [[ "$FAIL" -eq 0 && "$PASS" -ge 3 ]]; then
  printf 'TEST_RESULT=PASS\n'
  exit 0
fi
printf 'TEST_RESULT=FAIL\n'
exit 1
