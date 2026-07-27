#!/usr/bin/env bash
# Eval harness: prove git-with-index-lock fixes the VENT index.lock failure modes
# against a real worktree (default: current directory).
#
# Exit 0 only when all cases pass. Safe: never commits; cleans locks it creates.
set -u

ROOT="$(cd "${1:-.}" && pwd)"
cd "$ROOT"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WRAPPER="${GIT_WITH_INDEX_LOCK:-$SCRIPT_DIR/git-with-index-lock}"
if [[ ! -x "$WRAPPER" ]]; then
  chmod +x "$WRAPPER" 2>/dev/null || true
fi

LOCK="$(git rev-parse --path-format=absolute --git-path index.lock 2>/dev/null || true)"
if [[ -z "$LOCK" || "$LOCK" != /* ]]; then
  LOCK="$(cd "$(dirname "$(git rev-parse --git-path index.lock)")" && pwd)/$(basename "$(git rev-parse --git-path index.lock)")"
fi
MARKER="$ROOT/.git-index-lock-fix-eval-marker"
PASS=0
FAIL=0
HOLDER_PID=""

log() { printf '%s\n' "$*"; }
section() { printf '\n===== %s =====\n' "$*"; }
ok() { PASS=$((PASS + 1)); log "OK: $*"; }
bad() { FAIL=$((FAIL + 1)); log "FAIL: $*"; }

kill_holder() {
  local pid="${1:-}"
  [[ -n "$pid" ]] || return 0
  if kill -0 "$pid" 2>/dev/null; then
    pkill -P "$pid" 2>/dev/null || true
    kill "$pid" 2>/dev/null || true
    wait "$pid" 2>/dev/null || true
  fi
}

ensure_lock_clear() {
  local tries=0 p
  while [[ -e "$LOCK" && $tries -lt 30 ]]; do
    if command -v lsof >/dev/null 2>&1 && lsof -t "$LOCK" >/dev/null 2>&1; then
      for p in $(lsof -t "$LOCK" 2>/dev/null); do
        kill "$p" 2>/dev/null || true
      done
      sleep 0.05
    else
      rm -f "$LOCK"
    fi
    tries=$((tries + 1))
  done
  if [[ -e "$LOCK" ]] && ! lsof "$LOCK" >/dev/null 2>&1; then
    rm -f "$LOCK"
  fi
}

cleanup() {
  kill_holder "${HOLDER_PID:-}"
  HOLDER_PID=""
  ensure_lock_clear
  git restore --staged -- "$MARKER" 2>/dev/null || true
  rm -f "$MARKER"
}
trap cleanup EXIT

if [[ -e "$LOCK" ]]; then
  log "ERROR: pre-existing index.lock at $LOCK — refusing to run eval"
  exit 2
fi

date >"$MARKER"

section "ENV"
log "root=$ROOT"
log "wrapper=$WRAPPER"
log "lock=$LOCK"
log "branch=$(git rev-parse --abbrev-ref HEAD)"

section "CASE A — stale lock: wrapper recovers"
printf 'git-index-lock-fix-eval STALE\n' >"$LOCK"
set +e
OUT="$("$WRAPPER" add -- "$MARKER" 2>&1)"
RC=$?
set -e
log "rc=$RC out=$OUT"
if [[ $RC -eq 0 && ! -e "$LOCK" ]]; then
  ok "wrapper cleared stale lock and staged marker"
else
  bad "stale recovery failed rc=$RC lock=$([[ -e $LOCK ]] && echo yes || echo no)"
  ensure_lock_clear
fi
git restore --staged -- "$MARKER" 2>/dev/null || true

section "CASE B — short live holder: wrapper waits then succeeds"
(
  exec 9>"$LOCK"
  printf 'git-index-lock-fix-eval LIVE-SHORT pid=%s\n' "$$" >&9
  sleep 0.8
) &
HOLDER_PID=$!
sleep 0.1
set +e
OUT="$(GIT_INDEX_LOCK_MAX_WAIT_MS=5000 GIT_INDEX_LOCK_POLL_MS=50 \
  "$WRAPPER" add -- "$MARKER" 2>&1)"
RC=$?
set -e
wait "$HOLDER_PID" 2>/dev/null || true
kill_holder "$HOLDER_PID"
HOLDER_PID=""
ensure_lock_clear
log "rc=$RC out=$OUT"
if [[ $RC -eq 0 ]]; then
  ok "wrapper waited out short live holder"
else
  bad "short live holder recovery failed rc=$RC"
fi
git restore --staged -- "$MARKER" 2>/dev/null || true

section "CASE C — long live holder: wrapper fails without deleting held lock"
(
  exec 9>"$LOCK"
  printf 'git-index-lock-fix-eval LIVE-LONG pid=%s\n' "$$" >&9
  sleep 8
) &
HOLDER_PID=$!
sleep 0.1
set +e
OUT="$(GIT_INDEX_LOCK_MAX_WAIT_MS=500 GIT_INDEX_LOCK_POLL_MS=50 \
  "$WRAPPER" add -- "$MARKER" 2>&1)"
RC=$?
set -e
HELD=no
if lsof "$LOCK" >/dev/null 2>&1; then HELD=yes; fi
log "rc=$RC held=$HELD lock_exists=$([[ -e $LOCK ]] && echo yes || echo no)"
log "out=$OUT"
if [[ $RC -ne 0 && "$HELD" == "yes" ]]; then
  ok "wrapper timed out on live holder and left lock alone"
else
  bad "live-holder safety failed rc=$RC held=$HELD"
fi
kill_holder "$HOLDER_PID"
HOLDER_PID=""
ensure_lock_clear

section "CASE D — control: raw git still fails on stale lock"
ensure_lock_clear
printf 'git-index-lock-fix-eval RAW\n' >"$LOCK"
set +e
git add -- "$MARKER" >/tmp/git-index-lock-raw.out 2>&1
RC=$?
set -e
if [[ $RC -ne 0 ]] && grep -qi index.lock /tmp/git-index-lock-raw.out; then
  ok "control: raw git still blocked by stale lock"
else
  bad "control raw git rc=$RC $(cat /tmp/git-index-lock-raw.out)"
fi
set +e
OUT="$("$WRAPPER" add -- "$MARKER" 2>&1)"
RC=$?
set -e
if [[ $RC -eq 0 && ! -e "$LOCK" ]]; then
  ok "wrapper recovered the control stale lock"
else
  bad "wrapper failed control recovery rc=$RC lock=$([[ -e $LOCK ]] && echo yes || echo no) held=$(lsof "$LOCK" >/dev/null 2>&1 && echo yes || echo no) out=$OUT"
fi
git restore --staged -- "$MARKER" 2>/dev/null || true
rm -f "$MARKER"

section "SUMMARY"
log "pass=$PASS fail=$FAIL"
if [[ "$FAIL" -eq 0 && "$PASS" -ge 5 ]]; then
  log "FIX_EVAL_RESULT=PASS"
  exit 0
fi
log "FIX_EVAL_RESULT=FAIL"
exit 1
