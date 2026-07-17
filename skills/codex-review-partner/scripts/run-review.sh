#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  run-review.sh --mode <implementation-review|adversarial-implementation-review|plan-review|pair|smoke> [--verdict-profile <profile>] [--input <file>] [--cwd <dir>] [--output <file>] [--status-file <file>] [--process-identity-file <file> --job-nonce <nonce>] [--timeout-seconds <seconds>]

Review modes require --verdict-profile. Compatible pairs:
  implementation-review: pre-pr-implementation, run-plan-pm, generic-implementation
  adversarial-implementation-review: pre-pr-implementation, generic-implementation
  plan-review: reviewed-html-plan, generic-plan
Pair and smoke accept no verdict profile. Smoke needs no input file.

Migration example:
  run-review.sh --mode implementation-review --verdict-profile generic-implementation --input /tmp/review.md --output /tmp/review-output.md
EOF
}

MODE="" INPUT_PATH="" TARGET_CWD="" OUTPUT_PATH="" STATUS_FILE="" PROCESS_IDENTITY_FILE="" JOB_NONCE="" VERDICT_PROFILE="" TIMEOUT_SECONDS=3600
while (($#)); do
  case "$1" in
    --mode) MODE="${2:-}"; shift 2 ;;
    --input) INPUT_PATH="${2:-}"; shift 2 ;;
    --cwd) TARGET_CWD="${2:-}"; shift 2 ;;
    --output) OUTPUT_PATH="${2:-}"; shift 2 ;;
    --status-file) STATUS_FILE="${2:-}"; shift 2 ;;
    --process-identity-file) PROCESS_IDENTITY_FILE="${2:-}"; shift 2 ;;
    --job-nonce) JOB_NONCE="${2:-}"; shift 2 ;;
    --verdict-profile) VERDICT_PROFILE="${2:-}"; shift 2 ;;
    --timeout-seconds) TIMEOUT_SECONDS="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ "$TIMEOUT_SECONDS" =~ ^[1-9][0-9]*$ ]] || { echo "--timeout-seconds must be a positive integer" >&2; exit 2; }
[[ -n "$MODE" ]] || { usage >&2; exit 2; }
if [[ -n "$PROCESS_IDENTITY_FILE" || -n "$JOB_NONCE" ]]; then
  [[ -n "$PROCESS_IDENTITY_FILE" && -n "$JOB_NONCE" ]] || { echo "--process-identity-file and --job-nonce must be provided together" >&2; exit 2; }
fi

case "$MODE" in
  implementation-review)
    REVIEW_CONTRACT='You are performing an implementation review. The Codex review-partner workflow is already active for this request: do not invoke codex-review-partner, run-review.sh, codex_review, or launch any nested Codex review. Stay read-only. Focus on correctness, edge cases, missed callsites, test gaps, and maintainability.'
    COMPATIBLE='pre-pr-implementation run-plan-pm generic-implementation' ;;
  adversarial-implementation-review)
    REVIEW_CONTRACT='You are performing an adversarial implementation review. The Codex review-partner workflow is already active for this request: do not invoke codex-review-partner, run-review.sh, codex_review, or launch any nested Codex review. Stay read-only. Inspect sibling failures, partial fixes, repeated assumptions, missed callsites, missing tests, and nearby plan-bound edge cases.'
    COMPATIBLE='pre-pr-implementation generic-implementation' ;;
  plan-review)
    REVIEW_CONTRACT='You are performing a plan review. The Codex review-partner workflow is already active for this request: do not invoke codex-review-partner, run-review.sh, codex_review, or launch any nested Codex review. Stay read-only. Focus on missing steps, unsafe assumptions, sequencing risks, verification gaps, migration hazards, and rollback concerns.'
    COMPATIBLE='reviewed-html-plan generic-plan' ;;
  pair)
    REVIEW_CONTRACT='You are acting as a pairing partner. The Codex review-partner workflow is already active for this request: do not invoke codex-review-partner, run-review.sh, codex_review, or launch any nested Codex review. Stay read-only unless explicitly asked for edits. Focus on tradeoffs, debugging next steps, likely failure modes, and simplifications.'
    COMPATIBLE='' ;;
  smoke)
    REVIEW_CONTRACT='Reply with exactly CODEX_REVIEW_SMOKE_READY and nothing else.'
    COMPATIBLE='' ;;
  *) echo "Unsupported mode: $MODE" >&2; usage >&2; exit 2 ;;
esac

if [[ "$MODE" == pair || "$MODE" == smoke ]]; then
  [[ -z "$VERDICT_PROFILE" ]] || { echo "$MODE accepts no --verdict-profile" >&2; exit 2; }
else
  [[ -n "$VERDICT_PROFILE" ]] || { echo "$MODE requires --verdict-profile; migration: add --verdict-profile generic-$([[ $MODE == plan-review ]] && echo plan || echo implementation)" >&2; exit 2; }
  [[ " $COMPATIBLE " == *" $VERDICT_PROFILE "* ]] || { echo "review mode/profile pair is incompatible; valid pairs: $MODE: ${COMPATIBLE// /, }" >&2; exit 2; }
fi

if [[ "$MODE" != smoke ]]; then
  [[ -n "$INPUT_PATH" && -f "$INPUT_PATH" ]] || { echo "Input file not found: $INPUT_PATH" >&2; exit 2; }
  [[ -s "$INPUT_PATH" ]] || { echo "Input file is empty: $INPUT_PATH" >&2; exit 2; }
fi
[[ -z "$TARGET_CWD" || -d "$TARGET_CWD" ]] || { echo "Working directory not found: $TARGET_CWD" >&2; exit 2; }
WORK_DIR="${TARGET_CWD:-$PWD}"

LOGIN_SHELL="${SHELL:-/bin/zsh}"
[[ -x "$LOGIN_SHELL" ]] || { echo "Configured login shell is unavailable: $LOGIN_SHELL" >&2; exit 2; }
case "${LOGIN_SHELL##*/}" in sh|bash|zsh|ksh|dash) ;; *) echo "Configured login shell is unsupported for review automation: $LOGIN_SHELL; use sh, bash, zsh, ksh, or dash" >&2; exit 2;; esac

PRIVATE_DIR="$(mktemp -d)"; chmod 700 "$PRIVATE_DIR"
FINAL_MESSAGE="$PRIVATE_DIR/final-message"; STDIN_FILE="$PRIVATE_DIR/prompt"
EFFECTIVE_PROCESS_IDENTITY_FILE="${PROCESS_IDENTITY_FILE:-$PRIVATE_DIR/process-identity.json}"
cleanup() { rm -rf "$PRIVATE_DIR"; }
trap cleanup EXIT
if [[ "$MODE" == smoke ]]; then printf '%s' "$REVIEW_CONTRACT" >"$STDIN_FILE"; else printf '%s\n\n%s' "$REVIEW_CONTRACT" "$(<"$INPUT_PATH")" >"$STDIN_FILE"; fi

CLI_VERSION="$(env CODEX_REVIEW_PARTNER_ACTIVE=1 "$LOGIN_SHELL" -l -c 'exec codex --version' 2>/dev/null || echo unknown)"
write_status() {
  local outcome="$1" classification="$2" matched="$3" exit_code="$4" signal_name="$5" timed_out="$6" validation="$7"
  [[ -n "$STATUS_FILE" ]] || return 0
  mkdir -p "$(dirname "$STATUS_FILE")"
  python3 - "$STATUS_FILE" "$CLI_VERSION" "$outcome" "$classification" "$matched" "$exit_code" "$signal_name" "$timed_out" "$validation" <<'PY'
import json,os,sys,tempfile
p,version,outcome,classification,matched,code,signal,timed,validation=sys.argv[1:]
d={'protocolVersion':1,'cliVersion':version.strip(),'outcome':outcome,'classification':classification,'matchedSource':matched or None,'codexExitCode':None if code=='' else int(code),'codexSignal':signal or None,'timeout':timed=='true','finalMessageValidation':validation}
fd,tmp=tempfile.mkstemp(prefix='.codex-status-',dir=os.path.dirname(os.path.abspath(p))); os.fchmod(fd,0o600)
with os.fdopen(fd,'w') as f: json.dump(d,f,sort_keys=True); f.write('\n')
os.replace(tmp,p); os.chmod(p,0o600)
PY
}

export CODEX_REVIEW_TIMEOUT_MARKER="$PRIVATE_DIR/timed-out"
SUPERVISOR="$PRIVATE_DIR/supervisor.py"
SUPERVISOR_READY="$PRIVATE_DIR/supervisor-ready"
SUPERVISOR_FAILED="$PRIVATE_DIR/supervisor-failed"
cat >"$SUPERVISOR" <<'PY'
#!/usr/bin/env python3
import ctypes
import json
import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import time


def atomic_text(path, text, mode=0o600):
    target = os.path.abspath(path)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f'.{os.path.basename(target)}.', dir=os.path.dirname(target))
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, 'w') as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        os.chmod(target, mode)
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


expected_parent = int(sys.argv[1])
ready_path, failed_path, identity_path, nonce, login_shell, work_dir = sys.argv[2:8]
command = sys.argv[8:]
try:
    def kill_private_group(_signum, _frame):
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        os.killpg(os.getpgrp(), signal.SIGKILL)

    signal.signal(signal.SIGTERM, kill_private_group)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(1, signal.SIGTERM, 0, 0, 0) != 0:  # PR_SET_PDEATHSIG
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))
    if os.getppid() != expected_parent:
        raise RuntimeError('review launcher parent exited before supervisor initialization')

    hook = os.environ.get('CODEX_REVIEW_TEST_BEFORE_IDENTITY_MARKER')
    if hook:
        atomic_text(hook, f'{os.getpid()}\n')
        allow = os.environ.get('CODEX_REVIEW_TEST_ALLOW_IDENTITY_PUBLICATION', f'{hook}.allow')
        while not os.path.exists(allow):
            time.sleep(0.01)

    if os.getppid() != expected_parent:
        raise RuntimeError('review launcher parent exited before identity publication')
    pid = os.getpid()
    pgid = os.getpgid(0)
    raw = pathlib.Path(f'/proc/{pid}/stat').read_text()
    tail = raw[raw.rfind(')') + 2:].split()
    if int(tail[2]) != pgid or pid != pgid:
        raise RuntimeError(f'private supervisor identity mismatch: pid={pid} pgid={pgid} procPgid={tail[2]}')
    if identity_path:
        identity = {
            'protocolVersion': 1,
            'nonce': nonce,
            'codexPid': pid,
            'codexPgid': pgid,
            'processStartIdentity': tail[19],
            'bootId': pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        }
        atomic_text(identity_path, json.dumps(identity, sort_keys=True) + '\n')
    atomic_text(ready_path, 'ready\n')
    if os.getppid() != expected_parent:
        raise RuntimeError('review launcher parent exited before Codex exec')
    environment = os.environ.copy()
    environment['CODEX_REVIEW_PARTNER_ACTIVE'] = '1'
    os.chdir(work_dir)
    child = subprocess.Popen([login_shell, '-l', '-c', 'exec codex "$@"', 'codex', *command], env=environment)
    result = child.wait()
    raise SystemExit(128 + (-result) if result < 0 else result)
except SystemExit:
    raise
except BaseException as error:
    try:
        atomic_text(failed_path, f'{type(error).__name__}: {error}\n')
    except BaseException:
        pass
    print(f'Codex supervisor launch failed: {error}', file=sys.stderr, flush=True)
    raise SystemExit(127)
PY
chmod 700 "$SUPERVISOR"
set +e
# The private supervisor remains the process-group leader, publishes its stable
# identity, and waits for Codex in the same group. Its parent-death handler
# kills the complete private group, including descendants, before reparenting
# can leave an unbounded reviewer process behind.
setsid python3 "$SUPERVISOR" "$$" "$SUPERVISOR_READY" "$SUPERVISOR_FAILED" "$EFFECTIVE_PROCESS_IDENTITY_FILE" "$JOB_NONCE" "$LOGIN_SHELL" "$WORK_DIR" exec --json -m gpt-5.6-sol -c 'model_reasoning_effort="high"' -s read-only -C "$WORK_DIR" -o "$FINAL_MESSAGE" - <"$STDIN_FILE" &
CODEX_GROUP=$!
CODEX_PID=$!
for _ in $(seq 1 1000); do
  [[ -s "$SUPERVISOR_READY" || -s "$SUPERVISOR_FAILED" ]] && break
  sleep 0.01
done
if [[ ! -s "$SUPERVISOR_READY" ]]; then
  kill -KILL -- "-$CODEX_GROUP" 2>/dev/null || true
  wait "$CODEX_PID" 2>/dev/null || true
  write_status failure CODEX_REVIEW_LAUNCH_FAILED exec 127 '' false not-checked || true
  if [[ -s "$SUPERVISOR_FAILED" ]]; then cat "$SUPERVISOR_FAILED" >&2; fi
  echo "Codex supervisor identity publication failed" >&2
  exit 127
fi
python3 - "$$" "$EFFECTIVE_PROCESS_IDENTITY_FILE" "$JOB_NONCE" "$TIMEOUT_SECONDS" <<'PY' &
import ctypes,json,os,pathlib,signal,sys,time
expected_parent=int(sys.argv[1]); identity_path=sys.argv[2]; nonce=sys.argv[3]
libc=ctypes.CDLL(None,use_errno=True)
if libc.prctl(1,signal.SIGKILL,0,0,0) != 0: raise SystemExit(1)  # PR_SET_PDEATHSIG
if os.getppid() != expected_parent: raise SystemExit
time.sleep(int(sys.argv[4]))
if os.getppid() != expected_parent: raise SystemExit
def validated_identity():
    try: evidence=json.loads(pathlib.Path(identity_path).read_text())
    except (OSError,json.JSONDecodeError): raise SystemExit
    if evidence.get('protocolVersion') != 1 or evidence.get('nonce') != nonce: raise SystemExit
    if evidence.get('bootId') != pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(): raise SystemExit
    pid=int(evidence['codexPid']); pgid=int(evidence['codexPgid'])
    try:
        raw=pathlib.Path(f'/proc/{pid}/stat').read_text(); tail=raw[raw.rfind(')')+2:].split()
    except OSError: raise SystemExit
    if tail[0] == 'Z' or int(tail[2]) != pgid or tail[19] != evidence.get('processStartIdentity'): raise SystemExit
    return pid,pgid
pid,pgid=validated_identity()
open(os.environ['CODEX_REVIEW_TIMEOUT_MARKER'],'w').close()
try: os.killpg(pgid,signal.SIGTERM)
except ProcessLookupError: raise SystemExit
time.sleep(2)
verified_pid,verified_pgid=validated_identity()
if (verified_pid,verified_pgid) != (pid,pgid): raise SystemExit
try: os.killpg(pgid,signal.SIGKILL)
except ProcessLookupError: pass
PY
WATCHDOG_PID=$!
wait "$CODEX_PID"; CODEX_EXIT=$?
kill "$WATCHDOG_PID" 2>/dev/null; wait "$WATCHDOG_PID" 2>/dev/null
set -e

TIMED_OUT=false
if [[ -f "$PRIVATE_DIR/timed-out" ]]; then TIMED_OUT=true; fi
if [[ "$TIMED_OUT" == true ]]; then
  SIGNAL_NUMBER=''
  if (( CODEX_EXIT > 128 )); then SIGNAL_NUMBER=$((CODEX_EXIT - 128)); fi
  write_status failure CODEX_REVIEW_INNER_TIMEOUT inner-timeout "$CODEX_EXIT" "$SIGNAL_NUMBER" true not-checked
  echo "Codex review timed out after ${TIMEOUT_SECONDS}s" >&2; exit 124
fi
if (( CODEX_EXIT != 0 )); then
  if (( CODEX_EXIT == 126 || CODEX_EXIT == 127 )); then
    write_status failure CODEX_REVIEW_LAUNCH_FAILED exec "$CODEX_EXIT" '' false not-checked
    echo "Codex launch failed ($CODEX_EXIT)" >&2; exit "$CODEX_EXIT"
  fi
  if (( CODEX_EXIT > 128 )); then
    SIGNAL_NUMBER=$((CODEX_EXIT - 128))
    write_status failure CODEX_REVIEW_CODEX_SIGNAL signal "$CODEX_EXIT" "$SIGNAL_NUMBER" false not-checked
    echo "Codex terminated by signal $SIGNAL_NUMBER" >&2; exit "$CODEX_EXIT"
  fi
  write_status failure CODEX_REVIEW_CODEX_EXIT_NONZERO generic "$CODEX_EXIT" '' false not-checked
  echo "Codex exited nonzero ($CODEX_EXIT); inspect JSONL/stderr evidence" >&2; exit "$CODEX_EXIT"
fi
if [[ ! -s "$FINAL_MESSAGE" ]]; then
  write_status failure CODEX_REVIEW_ARTIFACT_MISSING final-message 0 '' false missing
  echo "Codex final message is missing" >&2; exit 20
fi

set +e
python3 - "$MODE" "$VERDICT_PROFILE" "$FINAL_MESSAGE" <<'PY'
import re,sys
mode,profile,p=sys.argv[1:]
text=open(p,encoding='utf-8').read().replace('\r\n','\n').replace('\r','\n')
if mode=='smoke': raise SystemExit(0 if text.strip()=='CODEX_REVIEW_SMOKE_READY' else 1)
if mode=='pair': raise SystemExit(0)
tokens={
'pre-pr-implementation':{'FINDINGS_TO_RESOLVE','CLEAN_FOR_PR','BLOCKED_BY_QUESTION','REVIEW_INCOMPLETE_RERUN_NEEDED'},
'generic-implementation':{'FINDINGS_TO_RESOLVE','CLEAN_FOR_PR','BLOCKED_BY_QUESTION','REVIEW_INCOMPLETE_RERUN_NEEDED'},
'run-plan-pm':{'PASS_SCOPED','PASS_WITH_DOCUMENTED_OUT_OF_SCOPE_FOLLOW_UPS','FIX_IN_SCOPE_FINDINGS','BLOCKED_BY_SCOPE_QUESTION','REVIEW_INCOMPLETE_RERUN_NEEDED'},
'reviewed-html-plan':{'PLAN_EXECUTION_READY','PLAN_NEEDS_REVISION','BLOCKED_BY_PRODUCT_QUESTION','REVIEW_INCOMPLETE_RERUN_NEEDED'},
'generic-plan':{'PLAN_EXECUTION_READY','PLAN_NEEDS_REVISION','BLOCKED_BY_QUESTION','REVIEW_INCOMPLETE_RERUN_NEEDED'}}[profile]
lines=text.split('\n'); fenced=False; candidates=[]
for i,line in enumerate(lines):
    logical=line.rstrip(' \t')
    if re.match(r'^\s*```',logical): fenced=not fenced; continue
    if not fenced and re.match(r'^VERDICT: [A-Z0-9_]+$',logical): candidates.append((i,logical[9:]))
nonempty=[i for i,l in enumerate(lines) if l.rstrip(' \t')]
ok=len(candidates)==1 and candidates[0][0]==nonempty[-1] and candidates[0][1] in tokens
raise SystemExit(0 if ok else 1)
PY
VALID=$?
set -e
if (( VALID != 0 )); then
  write_status failure CODEX_REVIEW_ARTIFACT_INVALID final-message 0 '' false invalid
  echo "Codex final message is invalid for mode/profile" >&2; exit 21
fi

PUBLISH_TMP=""
abort_publication() {
  local status="$1"
  [[ -z "$PUBLISH_TMP" ]] || rm -f "$PUBLISH_TMP"
  write_status failure CODEX_REVIEW_OUTPUT_COMMIT_FAILED output-commit 0 '' false valid || true
  exit "$status"
}
if [[ -n "$OUTPUT_PATH" ]]; then
  mkdir -p "$(dirname "$OUTPUT_PATH")"
  PUBLISH_TMP="$(mktemp "$(dirname "$OUTPUT_PATH")/.codex-review.XXXXXX")"
  chmod 600 "$PUBLISH_TMP"; cp "$FINAL_MESSAGE" "$PUBLISH_TMP"
fi
if [[ "${CODEX_REVIEW_TEST_FAIL_FINAL_STATUS_WRITE:-}" == 1 ]] || ! write_status success CODEX_REVIEW_SUCCEEDED final-message 0 '' false valid; then
  [[ -z "$PUBLISH_TMP" ]] || rm -f "$PUBLISH_TMP"
  echo "Codex final status publication failed; caller output restored" >&2
  exit 22
fi
if [[ -n "$PUBLISH_TMP" ]]; then
  trap 'abort_publication 130' INT
  trap 'abort_publication 143' TERM
  trap 'abort_publication 129' HUP
  if [[ -n "${CODEX_REVIEW_TEST_BEFORE_OUTPUT_COMMIT_MARKER:-}" ]]; then
    : >"$CODEX_REVIEW_TEST_BEFORE_OUTPUT_COMMIT_MARKER"
    while [[ ! -e "${CODEX_REVIEW_TEST_ALLOW_OUTPUT_COMMIT:-$PRIVATE_DIR/allow-output-commit}" ]]; do sleep 0.02; done
  fi
  trap '' INT TERM HUP
  if ! mv -f "$PUBLISH_TMP" "$OUTPUT_PATH"; then
    trap - INT TERM HUP
    write_status failure CODEX_REVIEW_OUTPUT_COMMIT_FAILED output-commit 0 '' false valid || true
    echo "Codex output commit failed; caller output unchanged" >&2
    exit 23
  fi
fi
