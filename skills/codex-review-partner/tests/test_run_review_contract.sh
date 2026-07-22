#!/usr/bin/env bash
set -euo pipefail

ROOT="$(mktemp -d)"
trap 'rm -rf "$ROOT"' EXIT
LAUNCHER="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/run-review.sh"
mkdir -p "$ROOT/bin" "$ROOT/work tree"
export HOME="$ROOT"
printf 'export PATH=%q\n' "$ROOT/bin:/usr/bin:/bin" >"$ROOT/.bash_profile"

cat >"$ROOT/bin/codex" <<'EOF'
#!/usr/bin/env python3
import json, os, pathlib, signal, subprocess, sys, time
args=sys.argv[1:]
if args == ['--version']:
    print('codex-cli 0.144.4'); sys.exit(0)
prompt=sys.stdin.read()
if os.environ.get('FAKE_PROMPT_CAPTURE'):
    pathlib.Path(os.environ['FAKE_PROMPT_CAPTURE']).write_text(prompt)
path=pathlib.Path(args[args.index('-o')+1])
mode=os.environ.get('FAKE_CODEX_MODE','success')
print(json.dumps({'type':'thread.started','thread_id':'fake'}), flush=True)
if mode == 'silence': time.sleep(.25)
if mode == 'identity-pause': time.sleep(.5)
if mode == 'timeout':
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    child=subprocess.Popen([sys.executable,'-c','import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(30)'])
    pathlib.Path(os.environ['FAKE_CHILD_PID']).write_text(str(child.pid))
    time.sleep(30)
if mode == 'nonzero':
    print(json.dumps({'type':'error','message':'unknown provider shape'}), flush=True); sys.exit(9)
if mode == 'exit137': sys.exit(137)
if mode == 'signal': os.kill(os.getpid(), signal.SIGTERM)
text=os.environ.get('FAKE_FINAL','Review complete.\nVERDICT: CLEAN_FOR_PR\n')
if mode != 'missing': path.write_text(text)
print(json.dumps({'type':'turn.completed','usage':{'input_tokens':1}}), flush=True)
EOF
chmod +x "$ROOT/bin/codex"
printf 'Review this bounded packet.\n' >"$ROOT/input.md"

run() {
  PATH="$ROOT/bin:/usr/bin:/bin" SHELL=/bin/bash "$LAUNCHER" "$@"
}

portable_stat() {
  python3 - "$1" <<'PY'
import json,os,stat,sys
value=os.stat(sys.argv[1])
print(json.dumps({'inode':value.st_ino,'mode':stat.S_IMODE(value.st_mode),'mtime_ns':value.st_mtime_ns},sort_keys=True))
PY
}

assert_fails() {
  local needle="$1"; shift
  if "$@" >"$ROOT/fail.out" 2>"$ROOT/fail.err"; then
    echo "expected failure: $*" >&2; exit 1
  fi
  grep -F "$needle" "$ROOT/fail.err" >/dev/null
}

# Review modes require an explicit compatible profile before Codex launch.
assert_fails 'requires --verdict-profile' run --mode implementation-review --input "$ROOT/input.md"
assert_fails 'incompatible' run --mode plan-review --verdict-profile pre-pr-implementation --input "$ROOT/input.md"
assert_fails 'accepts no --verdict-profile' run --mode pair --verdict-profile generic-plan --input "$ROOT/input.md"

# The actual model prompt explicitly suppresses nested review launches for every non-smoke consumer.
for mode_profile in \
  'implementation-review generic-implementation' \
  'adversarial-implementation-review generic-implementation' \
  'plan-review generic-plan' \
  'pair '; do
  read -r mode profile <<<"$mode_profile"
  args=(--mode "$mode" --input "$ROOT/input.md" --output "$ROOT/prompt-output" --timeout-seconds 3)
  if [[ -n "${profile:-}" ]]; then args+=(--verdict-profile "$profile"); fi
  final='Review complete.'
  case "$profile" in
    generic-implementation) final+=$'\nVERDICT: CLEAN_FOR_PR' ;;
    generic-plan) final+=$'\nVERDICT: PLAN_EXECUTION_READY' ;;
  esac
  FAKE_FINAL="$final" FAKE_PROMPT_CAPTURE="$ROOT/prompt-capture" run "${args[@]}" >/dev/null
  grep -F 'workflow is already active for this request' "$ROOT/prompt-capture" >/dev/null
  grep -F 'do not invoke codex-review-partner, run-review.sh, codex_review, or launch any nested Codex review' "$ROOT/prompt-capture" >/dev/null
  if [[ "$mode" != pair ]]; then
    grep -F 'Do not run or invoke tests, test suites, builds, linters, typechecks, benchmarks, verification scripts, validation commands' "$ROOT/prompt-capture" >/dev/null
    grep -F 'the calling/coordinating agent exclusively owns test and verification execution' "$ROOT/prompt-capture" >/dev/null
    grep -F 'Read-only inspection commands such as git diff, rg, and file reads are allowed' "$ROOT/prompt-capture" >/dev/null
  fi
done

# Final-message capture is separate from JSONL progress, with strict grammar.
status="$ROOT/status.json"; output="$ROOT/out file.md"
FAKE_FINAL=$'Body\r\nVERDICT: CLEAN_FOR_PR   \r\n' run --mode implementation-review --verdict-profile generic-implementation --input "$ROOT/input.md" --cwd "$ROOT/work tree" --output "$output" --status-file "$status" --timeout-seconds 3 >"$ROOT/events.jsonl"
tr -d '\r' <"$output" | grep -Fx 'VERDICT: CLEAN_FOR_PR   ' >/dev/null
grep -F 'thread.started' "$ROOT/events.jsonl" >/dev/null
python3 - "$status" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); assert d['protocolVersion']==1 and d['outcome']=='success' and d['classification']=='CODEX_REVIEW_SUCCEEDED'
assert d['cliVersion']
PY

# The extension-owned sidecar is atomic, nonce-bound, and records durable adapter identity.
identity="$ROOT/process-identity.json"
FAKE_CODEX_MODE=identity-pause FAKE_FINAL=$'Body\nVERDICT: CLEAN_FOR_PR\n' run --mode implementation-review --verdict-profile generic-implementation --input "$ROOT/input.md" --output "$ROOT/identity-output" --status-file "$ROOT/identity-status" --process-identity-file "$identity" --job-nonce nonce-123 --timeout-seconds 3 >"$ROOT/identity-events" &
identity_launcher=$!
for _ in $(seq 1 100); do [[ -s "$identity" ]] && break; sleep .01; done
python3 - "$identity" "$LAUNCHER" <<'PY'
import json,pathlib,subprocess,sys
d=json.load(open(sys.argv[1]));assert d['protocolVersion']==2 and d['nonce']=='nonce-123'
helper=pathlib.Path(sys.argv[2]).with_name('process_identity.py')
snapshot=json.loads(subprocess.check_output([sys.executable,str(helper),'snapshot','--pid',str(d['leaderPid'])],text=True))
record=snapshot['process'];assert snapshot['bootId']==d['bootId']
assert record['pgid']==d['leaderPgid'] and record['sid']==d['leaderSid'] and record['startIdentity']==d['leaderStartIdentity']
PY
wait "$identity_launcher"

# A final valid-status publication failure leaves every caller-owned inode detail untouched.
printf '\x00caller-owned\xffbytes\n' >"$output"
chmod 640 "$output"
touch -t 202001020304.05 "$output"
cp "$output" "$ROOT/output-before"
before_stat="$(portable_stat "$output")"
assert_fails 'final status publication failed' env CODEX_REVIEW_TEST_FAIL_FINAL_STATUS_WRITE=1 FAKE_FINAL=$'Body\nVERDICT: CLEAN_FOR_PR\n' PATH="$ROOT/bin:/usr/bin:/bin" SHELL=/bin/bash "$LAUNCHER" --mode implementation-review --verdict-profile generic-implementation --input "$ROOT/input.md" --output "$output" --status-file "$status" --timeout-seconds 3
cmp "$ROOT/output-before" "$output"
[[ "$(portable_stat "$output")" == "$before_stat" ]]

# TERM before the protected final rename leaves the original wholly untouched.
marker="$ROOT/before-commit"; allow="$ROOT/allow-commit"
env CODEX_REVIEW_TEST_BEFORE_OUTPUT_COMMIT_MARKER="$marker" CODEX_REVIEW_TEST_ALLOW_OUTPUT_COMMIT="$allow" FAKE_FINAL=$'Body\nVERDICT: CLEAN_FOR_PR\n' PATH="$ROOT/bin:/usr/bin:/bin" SHELL=/bin/bash "$LAUNCHER" --mode implementation-review --verdict-profile generic-implementation --input "$ROOT/input.md" --output "$output" --status-file "$status" --timeout-seconds 3 >"$ROOT/interrupted.out" 2>"$ROOT/interrupted.err" &
interrupted_pid=$!
for _ in $(seq 1 100); do [[ -e "$marker" ]] && break; sleep .02; done
kill -TERM "$interrupted_pid"
set +e; wait "$interrupted_pid"; interrupted_code=$?; set -e
[[ "$interrupted_code" == 143 ]]
cmp "$ROOT/output-before" "$output"
[[ "$(portable_stat "$output")" == "$before_stat" ]]
assert_fails 'terminated by signal' env FAKE_CODEX_MODE=signal PATH="$ROOT/bin:/usr/bin:/bin" SHELL=/bin/bash "$LAUNCHER" --mode smoke --input "$ROOT/input.md" --status-file "$status" --timeout-seconds 3
python3 - "$status" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); assert d['classification']=='CODEX_REVIEW_CODEX_SIGNAL' and d['matchedSource']=='signal'
PY

for bad in \
  'VERDICT: PASS_SCOPED' \
  'VERDICT: CLEAN_FOR_PR|after' \
  'VERDICT: CLEAN_FOR_PR|VERDICT: FINDINGS_TO_RESOLVE' \
  '> VERDICT: CLEAN_FOR_PR' \
  '```|VERDICT: CLEAN_FOR_PR|```'; do
  old='caller-owned'; printf %s "$old" >"$output"
  final="${bad//|/$'\n'}"
  assert_fails 'final message is invalid' env FAKE_FINAL="$final" PATH="$ROOT/bin:/usr/bin:/bin" SHELL=/bin/bash "$LAUNCHER" --mode implementation-review --verdict-profile generic-implementation --input "$ROOT/input.md" --output "$output" --status-file "$status" --timeout-seconds 3
  [[ "$(cat "$output")" == "$old" ]]
done

# Every locked compatible pair accepts its profile vocabulary.
declare -a pairs=(
  'implementation-review pre-pr-implementation CLEAN_FOR_PR'
  'implementation-review run-plan-pm PASS_SCOPED'
  'implementation-review generic-implementation FINDINGS_TO_RESOLVE'
  'adversarial-implementation-review pre-pr-implementation BLOCKED_BY_QUESTION'
  'adversarial-implementation-review generic-implementation REVIEW_INCOMPLETE_RERUN_NEEDED'
  'plan-review reviewed-html-plan PLAN_EXECUTION_READY'
  'plan-review generic-plan PLAN_NEEDS_REVISION'
)
for row in "${pairs[@]}"; do
  read -r mode profile token <<<"$row"
  FAKE_FINAL="Body
VERDICT: $token" run --mode "$mode" --verdict-profile "$profile" --input "$ROOT/input.md" --output "$output" --status-file "$status" --timeout-seconds 3 >/dev/null
done

# Smoke uses the real route and exact sentinel; missing/progress-only/nonzero fail truthfully.
FAKE_FINAL=CODEX_REVIEW_SMOKE_READY run --mode smoke --input "$ROOT/input.md" --output "$output" --status-file "$status" --timeout-seconds 3 >/dev/null
assert_fails 'final message is missing' env FAKE_CODEX_MODE=missing PATH="$ROOT/bin:/usr/bin:/bin" SHELL=/bin/bash "$LAUNCHER" --mode smoke --input "$ROOT/input.md" --status-file "$status" --timeout-seconds 3
assert_fails 'Codex exited nonzero' env FAKE_CODEX_MODE=nonzero PATH="$ROOT/bin:/usr/bin:/bin" SHELL=/bin/bash "$LAUNCHER" --mode smoke --input "$ROOT/input.md" --status-file "$status" --timeout-seconds 3
python3 - "$status" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); assert d['classification']=='CODEX_REVIEW_CODEX_EXIT_NONZERO' and d['matchedSource']=='generic'
PY
assert_fails 'Codex exited nonzero (137)' env FAKE_CODEX_MODE=exit137 PATH="$ROOT/bin:/usr/bin:/bin" SHELL=/bin/bash "$LAUNCHER" --mode smoke --input "$ROOT/input.md" --status-file "$status" --timeout-seconds 3
python3 - "$status" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); assert d['classification']=='CODEX_REVIEW_CODEX_EXIT_NONZERO' and d['codexExitCode']==137 and d['codexSignal'] is None
PY

# Missing or malformed cleanup evidence is never accepted as a normal outcome.
for result_mode in missing malformed cleanup-false inconsistent missing-signal invalid-signal-reason; do
  rm -f "$status.supervisor-result.json" "$status.supervisor-failed.txt"
  assert_fails 'cleanup could not be verified' env CODEX_REVIEW_TEST_SUPERVISOR_RESULT="$result_mode" FAKE_FINAL=CODEX_REVIEW_SMOKE_READY PATH="$ROOT/bin:/usr/bin:/bin" SHELL=/bin/bash "$LAUNCHER" --mode smoke --input "$ROOT/input.md" --status-file "$status" --timeout-seconds 3
  python3 - "$status" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); assert d['classification']=='CODEX_REVIEW_CLEANUP_FAILED' and d['matchedSource']=='cleanup'
PY
  if [[ "$result_mode" == missing ]]; then [[ -s "$status.supervisor-failed.txt" ]]; else [[ -s "$status.supervisor-result.json" ]]; fi
done
mkdir -p "$ROOT/evidence-tmp"
assert_fails 'retained supervisor evidence' env TMPDIR="$ROOT/evidence-tmp" CODEX_REVIEW_TEST_SUPERVISOR_RESULT=missing FAKE_FINAL=CODEX_REVIEW_SMOKE_READY PATH="$ROOT/bin:/usr/bin:/bin" SHELL=/bin/bash "$LAUNCHER" --mode smoke --input "$ROOT/input.md" --timeout-seconds 3
find "$ROOT/evidence-tmp/codex-review-evidence" -name '*.supervisor-failed.txt' -type f | grep . >/dev/null

# Inner timeout kills the full process group and records timeout precedence.
assert_fails 'timed out' env FAKE_CODEX_MODE=timeout FAKE_CHILD_PID="$ROOT/child.pid" PATH="$ROOT/bin:/usr/bin:/bin" SHELL=/bin/bash "$LAUNCHER" --mode smoke --input "$ROOT/input.md" --status-file "$status" --timeout-seconds 1
python3 - "$status" "$ROOT/child.pid" "$LAUNCHER" <<'PY'
import json,pathlib,subprocess,sys,time
d=json.load(open(sys.argv[1])); assert d['classification']=='CODEX_REVIEW_INNER_TIMEOUT' and d['timeout'] is True
assert d['codexExitCode']==137 and d['codexSignal'] in (9,'9')
pid=int(open(sys.argv[2]).read())
helper=pathlib.Path(sys.argv[3]).with_name('process_identity.py')
for _ in range(40):
    value=json.loads(subprocess.check_output([sys.executable,str(helper),'snapshot','--pid',str(pid)],text=True))
    if not value['process'] or not value['process']['alive']: break
    time.sleep(.05)
else: raise AssertionError('descendant survived timeout')
PY

echo 'PASS: Codex launcher final-message, profile, status, timeout, and no-clobber contracts'
