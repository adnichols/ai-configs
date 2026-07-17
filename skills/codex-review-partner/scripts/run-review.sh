#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  run-review.sh --mode <implementation-review|adversarial-implementation-review|plan-review|pair|smoke> [--verdict-profile <profile>] [--input <file>] [--cwd <dir>] [--output <file>] [--status-file <file>] [--process-identity-file <file> --job-nonce <nonce>] [--owner-pid <pid> --owner-start-identity <identity> --owner-boot-id <identity>] [--timeout-seconds <seconds>]

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
OWNER_PID="" OWNER_START_IDENTITY="" OWNER_BOOT_ID=""
while (($#)); do
  case "$1" in
    --mode) MODE="${2:-}"; shift 2 ;;
    --input) INPUT_PATH="${2:-}"; shift 2 ;;
    --cwd) TARGET_CWD="${2:-}"; shift 2 ;;
    --output) OUTPUT_PATH="${2:-}"; shift 2 ;;
    --status-file) STATUS_FILE="${2:-}"; shift 2 ;;
    --process-identity-file) PROCESS_IDENTITY_FILE="${2:-}"; shift 2 ;;
    --job-nonce) JOB_NONCE="${2:-}"; shift 2 ;;
    --owner-pid) OWNER_PID="${2:-}"; shift 2 ;;
    --owner-start-identity) OWNER_START_IDENTITY="${2:-}"; shift 2 ;;
    --owner-boot-id) OWNER_BOOT_ID="${2:-}"; shift 2 ;;
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
if [[ -n "$OWNER_PID" || -n "$OWNER_START_IDENTITY" || -n "$OWNER_BOOT_ID" ]]; then
  [[ "$OWNER_PID" =~ ^[1-9][0-9]*$ && -n "$OWNER_START_IDENTITY" && -n "$OWNER_BOOT_ID" ]] || { echo "--owner-pid, --owner-start-identity, and --owner-boot-id must be provided together" >&2; exit 2; }
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
EFFECTIVE_JOB_NONCE="${JOB_NONCE:-$(python3 -c 'import uuid; print(uuid.uuid4())')}"
cleanup() { rm -rf "$PRIVATE_DIR"; }
trap cleanup EXIT
if [[ "$MODE" == smoke ]]; then printf '%s' "$REVIEW_CONTRACT" >"$STDIN_FILE"; else printf '%s\n\n%s' "$REVIEW_CONTRACT" "$(<"$INPUT_PATH")" >"$STDIN_FILE"; fi

CLI_VERSION="unknown"
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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IDENTITY_HELPER="$SCRIPT_DIR/process_identity.py"
SUPERVISOR="$SCRIPT_DIR/review_supervisor.py"
SUPERVISOR_READY="$PRIVATE_DIR/supervisor-ready"
SUPERVISOR_FAILED="$PRIVATE_DIR/supervisor-failed"
SUPERVISOR_RESULT="$PRIVATE_DIR/supervisor-result.json"

[[ -r "$IDENTITY_HELPER" && -r "$SUPERVISOR" ]] || { echo "Codex review platform helpers are unavailable for $(uname -s): $IDENTITY_HELPER $SUPERVISOR" >&2; write_status failure CODEX_REVIEW_LAUNCH_FAILED exec 127 '' false not-checked || true; exit 127; }
if ! python3 "$IDENTITY_HELPER" preflight >"$PRIVATE_DIR/identity-preflight.json" 2>"$PRIVATE_DIR/identity-preflight.err"; then
  cat "$PRIVATE_DIR/identity-preflight.err" >&2
  write_status failure CODEX_REVIEW_LAUNCH_FAILED exec 127 '' false not-checked || true
  exit 127
fi
if ! python3 "$SUPERVISOR" --preflight >"$PRIVATE_DIR/supervisor-preflight.json" 2>"$PRIVATE_DIR/supervisor-preflight.err"; then
  cat "$PRIVATE_DIR/supervisor-preflight.err" >&2
  write_status failure CODEX_REVIEW_LAUNCH_FAILED exec 127 '' false not-checked || true
  exit 127
fi

snapshot_fields() {
  python3 - "$IDENTITY_HELPER" "$1" <<'PY'
import json,subprocess,sys
value=json.loads(subprocess.check_output([sys.executable,sys.argv[1],'snapshot','--pid',sys.argv[2]],text=True))
record=value.get('process')
if not isinstance(record,dict) or not record.get('alive'): raise SystemExit(1)
print(record['startIdentity'],value['bootId'],sep='\t')
PY
}
IFS=$'\t' read -r PARENT_START_IDENTITY PARENT_BOOT_ID < <(snapshot_fields "$$")
if [[ -z "$OWNER_PID" ]]; then
  OWNER_PID="$PPID"
  IFS=$'\t' read -r OWNER_START_IDENTITY OWNER_BOOT_ID < <(snapshot_fields "$OWNER_PID")
fi
CLI_VERSION="$(env CODEX_REVIEW_PARTNER_ACTIVE=1 "$LOGIN_SHELL" -l -c 'exec codex --version' 2>/dev/null || echo unknown)"

set +e
python3 "$SUPERVISOR" \
  --parent-pid "$$" --parent-start-identity "$PARENT_START_IDENTITY" --parent-boot-id "$PARENT_BOOT_ID" \
  --owner-pid "$OWNER_PID" --owner-start-identity "$OWNER_START_IDENTITY" --owner-boot-id "$OWNER_BOOT_ID" \
  --ready-file "$SUPERVISOR_READY" --failed-file "$SUPERVISOR_FAILED" --identity-file "$EFFECTIVE_PROCESS_IDENTITY_FILE" \
  --result-file "$SUPERVISOR_RESULT" --nonce "$EFFECTIVE_JOB_NONCE" --login-shell "$LOGIN_SHELL" --work-dir "$WORK_DIR" \
  --timeout-seconds "$TIMEOUT_SECONDS" -- exec --json -m gpt-5.6-sol -c 'model_reasoning_effort="high"' -s read-only -C "$WORK_DIR" -o "$FINAL_MESSAGE" - <"$STDIN_FILE" &
CODEX_PID=$!
for _ in $(seq 1 1000); do
  [[ -s "$SUPERVISOR_READY" || -s "$SUPERVISOR_FAILED" ]] && break
  sleep 0.01
done
if [[ ! -s "$SUPERVISOR_READY" ]]; then
  kill -TERM "$CODEX_PID" 2>/dev/null || true
  wait "$CODEX_PID" 2>/dev/null || true
  write_status failure CODEX_REVIEW_LAUNCH_FAILED exec 127 '' false not-checked || true
  if [[ -s "$SUPERVISOR_FAILED" ]]; then cat "$SUPERVISOR_FAILED" >&2; fi
  echo "Codex supervisor identity publication failed" >&2
  exit 127
fi
wait "$CODEX_PID"; CODEX_EXIT=$?
set -e

read -r RESULT_CODE RESULT_SIGNAL TIMED_OUT RESULT_CLEANUP < <(python3 - "$SUPERVISOR_RESULT" "$CODEX_EXIT" <<'PY'
import json,sys
try: value=json.load(open(sys.argv[1]))
except (OSError,json.JSONDecodeError): value={}
print(value.get('codexExitCode',sys.argv[2]),value.get('codexSignal',''),str(bool(value.get('timeout'))).lower(),str(bool(value.get('cleanupVerified'))).lower())
PY
)
if [[ "$TIMED_OUT" == true ]]; then
  write_status failure CODEX_REVIEW_INNER_TIMEOUT inner-timeout "$RESULT_CODE" "$RESULT_SIGNAL" true not-checked
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
