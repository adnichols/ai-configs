#!/usr/bin/env bash
# Unit/integration tests for scripts/git-with-index-lock
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
WRAPPER="$REPO_ROOT/scripts/git-with-index-lock"
PASS=0
FAIL=0

log() { printf '%s\n' "$*"; }
ok() { PASS=$((PASS + 1)); log "OK: $*"; }
bad() { FAIL=$((FAIL + 1)); log "FAIL: $*"; }

if [[ ! -x "$WRAPPER" ]]; then
  chmod +x "$WRAPPER"
fi

WORKDIR="$(mktemp -d -t git-with-index-lock-test.XXXXXX)"
cleanup() {
  rm -rf "$WORKDIR"
}
trap cleanup EXIT

git -C "$WORKDIR" init -q
git -C "$WORKDIR" config user.email "test@example.com"
git -C "$WORKDIR" config user.name "Test"
echo base >"$WORKDIR/file.txt"
git -C "$WORKDIR" add file.txt
git -C "$WORKDIR" commit -q -m "init"

LOCK="$(git -C "$WORKDIR" rev-parse --path-format=absolute --git-path index.lock 2>/dev/null || true)"
if [[ -z "$LOCK" || "$LOCK" != /* ]]; then
  LOCK="$WORKDIR/$(git -C "$WORKDIR" rev-parse --git-path index.lock)"
fi
MARKER="$WORKDIR/marker.txt"

# --- stale lock cleared and command succeeds ---
printf 'stale-test\n' >"$LOCK"
echo one >"$MARKER"
set +e
OUT="$("$WRAPPER" -C "$WORKDIR" add -- marker.txt 2>&1)"
RC=$?
set -e
if [[ $RC -eq 0 && ! -e "$LOCK" ]]; then
  ok "stale lock cleared and add succeeded"
else
  bad "stale lock case rc=$RC lock_exists=$([[ -e $LOCK ]] && echo yes || echo no) out=$OUT"
  rm -f "$LOCK"
fi
git -C "$WORKDIR" restore --staged -- marker.txt 2>/dev/null || true

# --- live holder: wrapper waits, does not clear, then succeeds after release ---
echo two >"$MARKER"
(
  exec 9>"$LOCK"
  printf 'live-holder\n' >&9
  sleep 1
) &
HOLDER=$!
sleep 0.15
set +e
OUT="$("$WRAPPER" -C "$WORKDIR" add -- marker.txt 2>&1)"
RC=$?
set -e
wait "$HOLDER" 2>/dev/null || true
if [[ $RC -eq 0 ]]; then
  ok "live short holder: wrapper waited and succeeded"
else
  bad "live short holder failed rc=$RC out=$OUT"
fi
rm -f "$LOCK"
git -C "$WORKDIR" restore --staged -- marker.txt 2>/dev/null || true

# --- live holder beyond budget: fail without deleting held lock ---
echo three >"$MARKER"
(
  exec 9>"$LOCK"
  printf 'long-holder\n' >&9
  sleep 5
) &
HOLDER=$!
sleep 0.15
set +e
OUT="$(GIT_INDEX_LOCK_MAX_WAIT_MS=400 GIT_INDEX_LOCK_POLL_MS=50 \
  "$WRAPPER" -C "$WORKDIR" add -- marker.txt 2>&1)"
RC=$?
set -e
if [[ $RC -ne 0 && -e "$LOCK" ]] && lsof "$LOCK" >/dev/null 2>&1; then
  ok "long live holder: failed without clearing held lock"
else
  bad "long live holder case rc=$RC lock=$([[ -e $LOCK ]] && echo yes || echo no) out=$OUT"
fi
kill "$HOLDER" 2>/dev/null || true
wait "$HOLDER" 2>/dev/null || true
rm -f "$LOCK"

# --- no lsof: fail closed rather than unlink an unverifiable lock ---
printf 'unknown-holder\n' >"$LOCK"
echo no-lsof >"$MARKER"
set +e
OUT="$(PATH=/usr/bin:/bin GIT_INDEX_LOCK_MAX_WAIT_MS=200 GIT_INDEX_LOCK_POLL_MS=50 \
  "$WRAPPER" -C "$WORKDIR" add -- marker.txt 2>&1)"
RC=$?
set -e
if [[ $RC -ne 0 && -e "$LOCK" ]] && printf '%s' "$OUT" | grep -qi 'lsof unavailable'; then
  ok "without lsof, wrapper fails closed and preserves lock"
else
  bad "no-lsof safety rc=$RC lock=$([[ -e $LOCK ]] && echo yes || echo no) out=$OUT"
fi
rm -f "$LOCK"

# --- non-lock git errors pass through without inventing success ---
set +e
OUT="$("$WRAPPER" -C "$WORKDIR" add -- does-not-exist-xyz.txt 2>&1)"
RC=$?
set -e
if [[ $RC -ne 0 ]] && printf '%s' "$OUT" | grep -qi 'did not match\|pathspec\|fatal'; then
  ok "non-lock errors pass through"
else
  bad "non-lock error handling rc=$RC out=$OUT"
fi

# --- control: raw git still fails on stale lock ---
printf 'raw-stale\n' >"$LOCK"
echo four >"$MARKER"
set +e
git -C "$WORKDIR" add -- marker.txt >/dev/null 2>&1
RC=$?
set -e
if [[ $RC -ne 0 && -e "$LOCK" ]]; then
  ok "control: raw git still fails on stale lock"
else
  bad "control raw git unexpectedly rc=$RC"
fi
rm -f "$LOCK"

log "pass=$PASS fail=$FAIL"
if [[ "$FAIL" -eq 0 && "$PASS" -ge 5 ]]; then
  log "TEST_RESULT=PASS"
  exit 0
fi
log "TEST_RESULT=FAIL"
exit 1
