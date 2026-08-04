#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
DELIVERY="$ROOT/skills/delivery-run/scripts/delivery"
chmod +x "$DELIVERY"

TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT

pass() {
  printf 'PASS %s\n' "$1"
  TESTS_PASSED=$((TESTS_PASSED + 1))
}

fail() {
  printf 'FAIL %s\n' "$1" >&2
  TESTS_FAILED=$((TESTS_FAILED + 1))
}

run_test() {
  local name="$1"
  TESTS_RUN=$((TESTS_RUN + 1))
  if "$name"; then
    pass "$name"
  else
    fail "$name"
  fi
}

make_repo() {
  local dir="$1"
  mkdir -p "$dir"
  git -C "$dir" init -q
  git -C "$dir" config user.email "test@example.com"
  git -C "$dir" config user.name "Test"
  echo "x" >"$dir/README.md"
  git -C "$dir" add README.md
  git -C "$dir" commit -q -m "init"
  git -C "$dir" branch -M main
  git -C "$dir" checkout -q -b feature/nod-1-test
}

test_init_creates_ledger() {
  local repo="$TMP_ROOT/init-repo"
  make_repo "$repo"
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" init --issue NOD-1 --plan thoughts/plans/x.html >/dev/null
  [[ -f "$repo/.delivery/ledger.json" ]] || return 1
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
assert d["schemaVersion"]==1
assert d["receipts"]==[]
assert d["issue"]=="NOD-1"
assert d["stage"]=="INTAKE"
assert d["doctrine"]=="guidance-not-gates"
assert "planPm" in d["evidence"]
assert "planTech" in d["evidence"]
assert d["evidence"]["planTech"]["status"] == "pending"
assert "completenessReview" in d["evidence"]
assert d["plan"]=="thoughts/plans/x.html"
PY
}

test_record_receipts_coexist_and_validate() {
  local repo="$TMP_ROOT/receipt-repo"
  make_repo "$repo"
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" init --issue NOD-RECEIPT >/dev/null
  python3 - "$repo" <<'PY'
import json,sys
from pathlib import Path
root=Path(sys.argv[1])
base={"schemaVersion":1,"mode":"pi-review-stack","status":"success","startedAt":"2026-01-01T00:00:00Z","finishedAt":"2026-01-01T00:00:01Z","cwd":str(root),"repoRoot":str(root),"managedSurfaceManifest":{"path":"manifest.json","sha256":"0"*64,"surfaceCount":1},"transportProbe":{"status":"pass","reason":None},"hosts":[],"warnings":[],"rollback":{"attempted":False,"status":"not_needed","snapshotPath":None}}
for name,command in (("transaction.json","transaction"),("remote.json","remote-hosts")):
 d=dict(base);d["command"]=command
 (root/name).write_text(json.dumps(d)+"\n")
(root/"invalid.json").write_text('{"schemaVersion":1}\n')
PY
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" record-receipt transaction.json --command transaction >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" record-receipt remote.json --command remote-hosts >/dev/null
  if DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" record-receipt invalid.json >/dev/null 2>&1; then return 1; fi
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
value=json.load(open(sys.argv[1]))
assert value["schemaVersion"]==1
assert [item["command"] for item in value["receipts"]]==["transaction","remote-hosts"]
assert all(len(item["sha256"])==64 for item in value["receipts"])
assert value["ledgerRevision"] >= 3
PY
}

test_unprotected_stage_moves_without_gates() {
  local repo="$TMP_ROOT/stage-repo"
  make_repo "$repo"
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" init --issue NOD-2 >/dev/null
  # Jump ahead with no evidence recorded — must succeed.
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" stage PR_OPEN --note "soft jump" >/dev/null
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
assert d["stage"]=="PR_OPEN"
assert any(h.get("type")=="stage" for h in d["history"])
assert any("soft jump" in (n.get("text") or "") for n in d["notes"])
PY
}

test_check_exit_zero_with_gaps() {
  local repo="$TMP_ROOT/check-repo"
  make_repo "$repo"
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" init --issue NOD-3 >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" stage AUTOREVIEW >/dev/null
  set +e
  out="$(DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" check -v 2>&1)"
  code=$?
  set -e
  [[ "$code" -eq 0 ]] || return 1
  printf '%s' "$out" | rg -q "never hard-block|exit: 0|guidance only" || return 1
  printf '%s' "$out" | rg -q "MISSING_|advisories" || return 1
  # JSON mode also exit 0 with hardBlock false
  json="$(DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" check --json)"
  python3 -c 'import json,sys; d=json.loads(sys.argv[1]); assert d["hardBlock"] is False; assert d["advisories"]' "$json"
}

test_record_and_show() {
  local repo="$TMP_ROOT/record-repo"
  make_repo "$repo"
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" init --issue NOD-4 >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" record autoreview --status pass \
    --artifact thoughts/validation/x.md --summary "clean" >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" record completionEval --status gap \
    --gap "BDD missing" --summary "thin" >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" record completenessReview --status pass \
    --artifact thoughts/validation/x-completeness.md --summary "visible reviewer agrees AC1-AC4 are complete" >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" record customerImpact --status pass \
    --summary "operators unblocked" --promised "honest status" --observed "status axes" >/dev/null
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
assert d["evidence"]["autoreview"]["status"]=="pass"
assert d["completionEval"]["status"]=="gap"
assert "BDD missing" in d["completionEval"]["gaps"]
assert d["evidence"]["completenessReview"]["status"]=="pass"
assert d["customerImpact"]["summary"]=="operators unblocked"
assert "honest status" in d["customerImpact"]["promised"]
PY
  out="$(DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" show)"
  printf '%s' "$out" | rg -q "NOD-4" || return 1
  printf '%s' "$out" | rg -q "autoreview: pass" || return 1
}

test_completion_review_dry_run_uses_tab_create() {
  local repo="$TMP_ROOT/completion-review-repo"
  make_repo "$repo"
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" init --issue NOD-5 --plan thoughts/plans/x.html >/dev/null
  json="$(HERDR_WORKSPACE_ID=w1 DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" completion-review --dry-run --pane w1:p1)"
  python3 -c 'import json,sys
from pathlib import Path
p=json.loads(sys.argv[1])
assert p["model"]=="xai/grok-4.5:high", p
assert p["sourcePane"]=="w1:p1", p
assert p["reviewerName"].startswith("completeness-"), p
assert p["startCommand"][-2:]==["--model", "xai/grok-4.5:high"], p
cmd=p["tabCreateCommand"]
assert cmd[:7]==["herdr", "tab", "create", "--workspace", "w1", "--cwd", str(Path(sys.argv[2]).resolve())], p
assert cmd[7]=="--label" and cmd[8].startswith("complete · ") and cmd[9]=="--no-focus", p
assert ("split" + "Command") not in p, p
assert "VERDICT: COMPLETE" in p["prompt"], p
assert "acceptance criterion" in p["prompt"].lower(), p
' "$json" "$repo"
}

prepare_completion_review_repo() {
  local repo="$1"
  make_repo "$repo"
  mkdir -p "$repo/thoughts/plans"
  printf '<article data-plan>completion tabs</article>\n' >"$repo/thoughts/plans/x.html"
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" init --issue NOD-5 --plan thoughts/plans/x.html >/dev/null
}

test_completion_review_launch_creates_labeled_tab() {
  local repo="$TMP_ROOT/completion-tab-launch-repo"
  local fake_bin="$TMP_ROOT/fake-herdr-completion-tab"
  local herdr_log="$TMP_ROOT/fake-herdr-completion-tab.log"
  prepare_completion_review_repo "$repo"
  mkdir -p "$fake_bin"
  cat >"$fake_bin/herdr" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"$FAKE_HERDR_LOG"
if [[ "$1" == "tab" && "$2" == "create" ]]; then
  printf '{"result":{"tab":{"tab_id":"w1:t9"},"root_pane":{"pane_id":"w1:p9"}}}\n'
fi
exit 0
SH
  chmod +x "$fake_bin/herdr"
  PATH="$fake_bin:$PATH" FAKE_HERDR_LOG="$herdr_log" HERDR_WORKSPACE_ID=w1 HERDR_PANE_ID=w1:p1 \
    "$DELIVERY" --cwd "$repo" completion-review >/dev/null
  rg -q "tab create --workspace w1 --cwd .*completion-tab-launch-repo --label complete · .* --no-focus" "$herdr_log" || return 1
  rg -q "agent start completeness-.* --kind pi --pane w1:p9" "$herdr_log" || return 1
  rg -q "agent prompt completeness-" "$herdr_log" || return 1
  ! rg -q "pane[[:space:]]+split" "$herdr_log" || return 1
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); review=d["completenessReview"]
assert review["agentName"].startswith("completeness-")
assert review["paneId"] == "w1:p9"
assert review["tabId"] == "w1:t9"
assert review["tabLabel"].startswith("complete · ")
PY
}

test_completion_review_rerun_reuses_tab() {
  local repo="$TMP_ROOT/completion-tab-rerun-repo"
  local fake_bin="$TMP_ROOT/fake-herdr-completion-rerun"
  local herdr_log="$TMP_ROOT/fake-herdr-completion-rerun.log"
  prepare_completion_review_repo "$repo"
  mkdir -p "$fake_bin"
  cat >"$fake_bin/herdr" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"$FAKE_HERDR_LOG"
if [[ "$1" == "tab" && "$2" == "create" ]]; then
  printf '{"result":{"tab":{"tab_id":"w1:t9"},"root_pane":{"pane_id":"w1:p9"}}}\n'
fi
exit 0
SH
  chmod +x "$fake_bin/herdr"
  PATH="$fake_bin:$PATH" FAKE_HERDR_LOG="$herdr_log" HERDR_WORKSPACE_ID=w1 HERDR_PANE_ID=w1:p1 \
    "$DELIVERY" --cwd "$repo" completion-review >/dev/null
  : >"$herdr_log"
  PATH="$fake_bin:$PATH" FAKE_HERDR_LOG="$herdr_log" HERDR_WORKSPACE_ID=w1 HERDR_PANE_ID=w1:p1 \
    "$DELIVERY" --cwd "$repo" completion-review --rerun >/dev/null
  ! rg -q "tab create|agent start" "$herdr_log" || return 1
  rg -q "agent prompt completeness-" "$herdr_log" || return 1
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))["completenessReview"]
assert r["round"] == 2
assert r["paneId"] == "w1:p9"
assert r["tabId"] == "w1:t9"
PY
}

test_completion_review_rerun_rejects_legacy_record_without_tab() {
  local repo="$TMP_ROOT/completion-tab-legacy-rerun-repo"
  local fake_bin="$TMP_ROOT/fake-herdr-completion-legacy-rerun"
  local herdr_log="$TMP_ROOT/fake-herdr-completion-legacy-rerun.log"
  local out code
  prepare_completion_review_repo "$repo"
  mkdir -p "$fake_bin"
  cat >"$fake_bin/herdr" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"$FAKE_HERDR_LOG"
exit 0
SH
  chmod +x "$fake_bin/herdr"
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
path=sys.argv[1]
d=json.load(open(path))
d["completenessReview"]={
    "status":"pending",
    "agentName":"completeness-legacy",
    "paneId":"w1:p9",
    "requestId":"legacy-request",
    "round":1,
}
json.dump(d,open(path,"w"),indent=2)
PY
  set +e
  out="$(PATH="$fake_bin:$PATH" FAKE_HERDR_LOG="$herdr_log" HERDR_WORKSPACE_ID=w1 HERDR_PANE_ID=w1:p1 \
    "$DELIVERY" --cwd "$repo" completion-review --rerun 2>&1)"
  code=$?
  set -e
  [[ "$code" -ne 0 ]] || return 1
  printf '%s' "$out" | rg -q "no tab metadata.*without --rerun.*fresh labeled tab" || return 1
  [[ ! -s "$herdr_log" ]] || return 1
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))["completenessReview"]
assert r["requestId"] == "legacy-request"
assert r["round"] == 1
assert "tabId" not in r
PY
}

 test_agent_tab_create_failure_paths() {
  local repo="$TMP_ROOT/agent-tab-failure-repo"
  local fake_bin="$TMP_ROOT/fake-herdr-agent-tab-failure"
  local mode_file="$TMP_ROOT/fake-herdr-agent-tab-mode"
  local herdr_log="$TMP_ROOT/fake-herdr-agent-tab-failure.log"
  prepare_completion_review_repo "$repo"
  mkdir -p "$fake_bin"
  cat >"$fake_bin/herdr" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"$FAKE_HERDR_LOG"
mode="$(cat "$FAKE_HERDR_MODE")"
if [[ "$1" == "pane" && "$2" == "get" ]]; then
  case "$mode" in
    missing-workspace) printf '{"result":{"pane":{"pane_id":"w1:p1"}}}\n' ;;
    pane-non-json) printf 'not-json\n' ;;
    pane-non-object) printf '[]\n' ;;
    *) printf '{"result":{"pane":{"workspace_id":"w1"}}}\n' ;;
  esac
elif [[ "$1" == "tab" && "$2" == "create" ]]; then
  case "$mode" in
    tab-non-json) printf 'not-json\n' ;;
    tab-non-object) printf '[]\n' ;;
    missing-root-pane) printf '{"result":{"tab":{"tab_id":"w1:t9"},"root_pane":{}}}\n' ;;
    missing-tab-id) printf '{"result":{"tab":{},"root_pane":{"pane_id":"w1:p9"}}}\n' ;;
    *) printf '{"result":{"tab":{"tab_id":"w1:t9"},"root_pane":{"pane_id":"w1:p9"}}}\n' ;;
  esac
fi
exit 0
SH
  chmod +x "$fake_bin/herdr"
  local mode out code
  for mode in missing-workspace pane-non-json pane-non-object tab-non-json tab-non-object missing-root-pane missing-tab-id; do
    printf '%s\n' "$mode" >"$mode_file"
    : >"$herdr_log"
    set +e
    out="$(env -u HERDR_WORKSPACE_ID PATH="$fake_bin:$PATH" FAKE_HERDR_MODE="$mode_file" \
      FAKE_HERDR_LOG="$herdr_log" HERDR_PANE_ID=w1:p1 \
      "$DELIVERY" --cwd "$repo" completion-review 2>&1)"
    code=$?
    set -e
    [[ "$code" -ne 0 ]] || return 1
    printf '%s' "$out" | rg -qi "workspace discovery|tab creation" || return 1
    printf '%s' "$out" | rg -qi "tried|attempted" || return 1
    printf '%s' "$out" | rg -qi "next action" || return 1
    ! rg -q "pane[[:space:]]+split|agent start" "$herdr_log" || return 1
  done
}

test_merge_ready_requires_validated_completeness_review() {
  local repo="$TMP_ROOT/completeness-gate-repo"
  make_repo "$repo"
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" init --issue NOD-6 --plan thoughts/plans/x.html >/dev/null
  set +e
  out="$(DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" stage MERGE_READY 2>&1)"
  code=$?
  set -e
  [[ "$code" -ne 0 ]] || return 1
  printf '%s' "$out" | rg -q "visible completeness review has not been accepted" || return 1
  # A generic evidence record cannot forge the validated visible verdict.
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" record completenessReview --status pass --summary "forged" >/dev/null
  set +e
  out="$(DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" stage MERGE_READY 2>&1)"
  code=$?
  set -e
  [[ "$code" -ne 0 ]] || return 1
  printf '%s' "$out" | rg -q "visible completeness review has not been accepted" || return 1
}

test_accepted_completeness_review_allows_merge_ready_only_while_fresh() {
  local repo="$TMP_ROOT/completeness-accept-repo"
  local fake_bin="$TMP_ROOT/fake-herdr"
  make_repo "$repo"
  mkdir -p "$repo/thoughts/plans" "$fake_bin"
  printf '<html>plan</html>\n' >"$repo/thoughts/plans/x.html"
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" init --issue NOD-7 --plan thoughts/plans/x.html >/dev/null
  python3 - "$repo/.delivery/ledger.json" "$DELIVERY" "$repo" <<'PY'
import json,runpy,sys
path,delivery,root=sys.argv[1:];m=runpy.run_path(delivery);d=json.load(open(path));request="1"*32
d["completenessReview"]={"status":"pending","agentName":"completeness-nod-7","paneId":"w1:p2","requestId":request,"requestLedgerRevision":d["ledgerRevision"],"planSha256":m["plan_sha256"](d,m["Path"](root)),"worktreeFingerprint":m["working_tree_fingerprint"](m["Path"](root)),"round":1}
json.dump(d,open(path,"w"),indent=2)
PY
  cat >"$fake_bin/herdr" <<'SH'
#!/usr/bin/env bash
if [[ "$1" == "agent" && "$2" == "read" ]]; then
  printf 'COMPLETENESS_REVIEW_RESPONSE_ID: 11111111111111111111111111111111\nVERDICT: COMPLETE\nAll criteria are evidenced.\n'
  exit 0
fi
exit 64
SH
  chmod +x "$fake_bin/herdr"
  PATH="$fake_bin:$PATH" DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" completion-review --accept >/dev/null
  # The content fingerprint survives a commit of the exact reviewed files.
  git -C "$repo" add -A
  git -C "$repo" commit -qm "reviewed implementation"
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" stage MERGE_READY >/dev/null
  [[ -f "$repo/thoughts/validation/delivery-completeness.md" ]] || return 1
  printf '\nchanged after review\n' >>"$repo/thoughts/plans/x.html"
  set +e
  out="$(DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" stage MERGE_READY 2>&1)"
  code=$?
  set -e
  [[ "$code" -ne 0 ]] || return 1
  printf '%s' "$out" | rg -q "stale for the current plan" || return 1
}

test_completion_review_rejects_prior_round_verdict() {
  local repo="$TMP_ROOT/completeness-old-verdict-repo"
  local fake_bin="$TMP_ROOT/fake-herdr-old-verdict"
  make_repo "$repo"
  mkdir -p "$repo/thoughts/plans" "$fake_bin"
  printf '<html>plan</html>\n' >"$repo/thoughts/plans/x.html"
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" init --issue NOD-8 --plan thoughts/plans/x.html >/dev/null
  python3 - "$repo/.delivery/ledger.json" "$DELIVERY" "$repo" <<'PY'
import json,runpy,sys
path,delivery,root=sys.argv[1:];m=runpy.run_path(delivery);d=json.load(open(path));request="2"*32
d["completenessReview"]={"status":"pending","agentName":"completeness-nod-8","paneId":"w1:p2","requestId":request,"requestLedgerRevision":d["ledgerRevision"],"planSha256":m["plan_sha256"](d,m["Path"](root)),"worktreeFingerprint":m["working_tree_fingerprint"](m["Path"](root)),"round":2}
json.dump(d,open(path,"w"),indent=2)
PY
  cat >"$fake_bin/herdr" <<'SH'
#!/usr/bin/env bash
if [[ "$1" == "agent" && "$2" == "read" ]]; then
  printf 'COMPLETENESS_REVIEW_RESPONSE_ID: 33333333333333333333333333333333\nVERDICT: COMPLETE\nAn older response.\n'
  exit 0
fi
exit 64
SH
  chmod +x "$fake_bin/herdr"
  set +e
  out="$(PATH="$fake_bin:$PATH" DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" completion-review --accept 2>&1)"
  code=$?
  set -e
  [[ "$code" -ne 0 ]] || return 1
  printf '%s' "$out" | rg -q "current response ID.*missing.*visible IDs" || return 1
}

test_completeness_parser_reports_wrapped_duplicate_malformed_and_truncated() {
  python3 - "$DELIVERY" <<'PY'
import json,runpy,sys,tempfile
from pathlib import Path
module=runpy.run_path(sys.argv[1]);parse=module["parse_completeness_transcript"];rid="a"*32;old="b"*32
assert len(module["completeness_reviewer_name"]({"id":"delivery/"+"very-long-identity-"*5})) <= 32
exact=parse(f"COMPLETENESS_REVIEW_RESPONSE_ID: {rid}\nVERDICT: COMPLETE\n",rid);assert exact["accepted"]
wrapped=parse(f"COMPLETENESS_REVIEW_RESPONSE_ID:\n\n{rid}\nnotes\nVERDICT:\nCOMPLETE\n",rid);assert wrapped["accepted"]
duplicate=parse(f"COMPLETENESS_REVIEW_RESPONSE_ID: {rid}\nVERDICT: COMPLETE\nCOMPLETENESS_REVIEW_RESPONSE_ID: {rid}\nVERDICT: FINDINGS_TO_RESOLVE\n",rid);assert not duplicate["accepted"] and duplicate["verdict"]=="FINDINGS_TO_RESOLVE" and duplicate["duplicateCount"]==2
malformed=parse(f"COMPLETENESS_REVIEW_RESPONSE_ID: {rid}\nVERDICT: COMPLETE\nVERDICT: COMPLETE\n",rid);assert not malformed["accepted"] and "2 parsed verdicts" in malformed["diagnostic"]
missing=parse(f"VERDICT: COMPLETE\nCOMPLETENESS_REVIEW_RESPONSE_ID: {old}\nVERDICT: COMPLETE\n",rid);assert not missing["accepted"] and missing["likelyTruncated"] and old in missing["visibleIds"]
with tempfile.TemporaryDirectory() as temp:
    session=Path(temp)/"session.jsonl"
    event={"type":"message","message":{"role":"assistant","content":[{"type":"text","text":f"COMPLETENESS_REVIEW_RESPONSE_ID: {rid}\nVERDICT: COMPLETE\n"}]}}
    session.write_text(json.dumps(event)+"\n")
    extracted=module["pi_session_transcript"](session);assert parse(extracted,rid)["accepted"]
PY
}

test_ledger_lock_serializes_and_rejects_stale_writer() {
  local repo="$TMP_ROOT/ledger-lock-repo"
  make_repo "$repo"
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" init --issue NOD-LOCK >/dev/null
  python3 - "$DELIVERY" "$repo" <<'PY'
import json,os,subprocess,sys
from pathlib import Path
delivery,root=sys.argv[1],Path(sys.argv[2]);ledger=root/'.delivery/ledger.json'
code='''import json,runpy,sys,time\nm=runpy.run_path(sys.argv[1]);p=m["Path"](sys.argv[2]);d=json.loads(p.read_text());d.setdefault("notes",[]).append({"at":m["utc_now"](),"text":sys.argv[3]});time.sleep(.25);m["write_json"](p,d)'''
ps=[subprocess.Popen([sys.executable,'-c',code,delivery,str(ledger),label],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for label in ('alpha','beta')]
results=[p.communicate()+(p.returncode,) for p in ps];codes=sorted(item[2] for item in results);assert codes[0]==0 and codes[1]!=0,results
failed='alpha' if 'alpha' not in [n['text'] for n in json.loads(ledger.read_text())['notes']] else 'beta'
retry=subprocess.run([delivery,'--cwd',str(root),'note',failed],env={**os.environ,'DELIVERY_SKIP_HERDR':'1'},capture_output=True,text=True);assert retry.returncode==0,retry.stderr
value=json.loads(ledger.read_text());assert {n['text'] for n in value['notes']} >= {'alpha','beta'};assert value['ledgerRevision']>=3
PY
}

test_ledger_lock_timeout_reports_holder_metadata() {
  local repo="$TMP_ROOT/ledger-timeout-repo"
  make_repo "$repo"
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" init --issue NOD-TIMEOUT >/dev/null
  python3 - "$DELIVERY" "$repo" <<'PY'
import fcntl,json,os,subprocess,sys,time
from pathlib import Path
delivery,root=sys.argv[1],Path(sys.argv[2]);lock=root/'.delivery/ledger.lock';fd=os.open(lock,os.O_CREAT|os.O_RDWR,0o600);fcntl.flock(fd,fcntl.LOCK_EX);os.ftruncate(fd,0);os.write(fd,b'{"pid":4242,"command":"holder-test","expectedRevision":1}\n');os.fsync(fd)
result=subprocess.run([delivery,'--cwd',str(root),'note','blocked'],env={**os.environ,'DELIVERY_SKIP_HERDR':'1','DELIVERY_LEDGER_LOCK_TIMEOUT_SECONDS':'0.1'},capture_output=True,text=True)
fcntl.flock(fd,fcntl.LOCK_UN);os.close(fd);assert result.returncode!=0;assert 'holder-test' in result.stderr and 'expectedRevision' in result.stderr,result.stderr
PY
}

test_force_reinitialization_uses_locked_replace_semantics() {
  local repo="$TMP_ROOT/force-replace-repo"
  make_repo "$repo"
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" init --issue NOD-OLD >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" note "advance revision" >/dev/null
  before="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["ledgerRevision"])' "$repo/.delivery/ledger.json")"
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" init --force --issue NOD-NEW >/dev/null
  python3 - "$repo/.delivery/ledger.json" "$before" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]));assert d["issue"]=="NOD-NEW";assert d["ledgerRevision"]>int(sys.argv[2])
PY
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" bootstrap --force --issue NOD-BOOT >/dev/null
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]));assert d["issue"]=="NOD-BOOT";assert d["ledgerRevision"]>0
PY
}

test_unrelated_writer_proceeds_during_implementation_launch_lease() {
  local repo="$TMP_ROOT/launch-lease-note-repo"
  make_repo "$repo"
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" init --issue NOD-LEASE >/dev/null
  python3 - "$DELIVERY" "$repo" <<'PY'
import fcntl,os,subprocess,sys
from pathlib import Path
delivery,root=sys.argv[1],Path(sys.argv[2]);lock=root/'.delivery/implementation-launch.lock';fd=os.open(lock,os.O_CREAT|os.O_RDWR,0o600);fcntl.flock(fd,fcntl.LOCK_EX)
result=subprocess.run([delivery,'--cwd',str(root),'note','independent evidence'],env={**os.environ,'DELIVERY_SKIP_HERDR':'1'},capture_output=True,text=True)
fcntl.flock(fd,fcntl.LOCK_UN);os.close(fd);assert result.returncode==0,result.stderr
PY
}

test_board_lists_multiple() {
  local a="$TMP_ROOT/board-a" b="$TMP_ROOT/board-b"
  make_repo "$a"
  make_repo "$b"
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$a" init --issue NOD-A --id demo/a >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$b" init --issue NOD-B --id demo/b >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$b" stage PR_OPEN >/dev/null
  json="$(DELIVERY_SKIP_HERDR=1 "$DELIVERY" board --json --root "$a" --root "$b")"
  python3 -c 'import json,sys
d=json.loads(sys.argv[1])
ids={r["id"] for r in d["runs"]}
assert "demo/a" in ids and "demo/b" in ids
assert d["count"]>=2
' "$json"
}

test_stages_lists_guidance() {
  out="$("$DELIVERY" stages)"
  printf '%s' "$out" | rg -q "EXECUTION_READY" || return 1
  printf '%s' "$out" | rg -q "Automatically authorize.*launch the dedicated" || return 1
  printf '%s' "$out" | rg -q "PR creation without another operator approval pause" || return 1
}

test_set_issue_after_start() {
  local repo="$TMP_ROOT/set-issue-repo"
  make_repo "$repo"
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" init --slug widget-polish >/dev/null
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
assert d.get("issue") in (None, "")
assert d.get("slug")=="widget-polish"
PY
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" set --issue NOD-999 --retarget-id >/dev/null
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
assert d["issue"]=="NOD-999"
assert d["id"].endswith("NOD-999") or "NOD-999" in d["id"]
assert any(h.get("type")=="set" for h in d["history"])
PY
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" set --clear-issue >/dev/null
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
assert d.get("issue") is None
PY
}

test_phase_herdr_label_format() {
  python3 - "$DELIVERY" <<'PY'
import importlib.util, sys
from importlib.machinery import SourceFileLoader
from pathlib import Path
path = Path(sys.argv[1]).resolve()
loader = SourceFileLoader("delivery_cli", str(path))
spec = importlib.util.spec_from_loader(loader.name, loader)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
loader.exec_module(mod)
assert mod.phase_code("PLAN_DRAFT") == "PL"
assert mod.phase_code("IMPLEMENTING") == "I"
assert mod.phase_code("AUTOREVIEW") == "R"
assert mod.phase_code("PR_OPEN") == "PR"
assert mod.phase_code("DONE") == "D"
assert mod.phase_code("BLOCKED") == "B"
ledger = {
    "stage": "IMPLEMENTING",
    "issue": "NOD-99",
    "slug": "one-login-path",
    "labels": {"baseTitle": "NOD-99 one login path"},
}
label = mod.herdr_display_label(ledger)
assert label.startswith("I: "), label
assert "NOD-99" in label and "login" in label.lower(), label
assert "IMPLEMENTING" not in label, label
ledger["stage"] = "DONE"
assert mod.herdr_display_label(ledger).startswith("D: ")
assert mod.strip_phase_prefix("PL: nod-1 hello") == "nod-1 hello"
assert mod.strip_stage_suffix("NOD-1475 · IMPLEMENTING") == "NOD-1475"
assert mod.sanitize_base_title("R: NOD-1475 · IMPLEMENTING") == "NOD-1475"
# Legacy contaminated herdr label must rebuild from slug, not keep STAGE.
legacy = {
    "stage": "SCOPED_REVIEW",
    "issue": "NOD-1475",
    "slug": "session-snapshot-stream",
    "goal": "NOD-1475 session snapshot stream",
    "labels": {
        "baseTitle": "NOD-1475 · IMPLEMENTING",
        "herdr": "I: NOD-1475 · IMPLEMENTING",
    },
}
fixed = mod.herdr_display_label(legacy)
assert fixed.startswith("R: "), fixed
assert "NOD-1475" in fixed, fixed
assert "snapshot" in fixed.lower() or "session" in fixed.lower(), fixed
assert "IMPLEMENTING" not in fixed, fixed
assert "SCOPED_REVIEW" not in fixed, fixed
# Stage moves only change the code prefix; base title stays the work name.
legacy["stage"] = "IMPLEMENTING"
moved = mod.herdr_display_label(legacy)
assert moved.startswith("I: "), moved
assert "IMPLEMENTING" not in moved, moved
assert "snapshot" in moved.lower() or "session" in moved.lower(), moved
PY
}

test_spawn_dry_run_names_from_goal() {
  local repo="$TMP_ROOT/spawn-repo"
  make_repo "$repo"
  # fake origin/main so base check can pass without network
  git -C "$repo" branch -M main
  git -C "$repo" branch origin/main main 2>/dev/null || true
  # create a lightweight ref that rev-parse can see as origin/main via explicit base main
  json="$(DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" spawn --dry-run --base main -- \
    "Please help me make auto-sync status honest")"
  python3 -c 'import json,sys
d=json.loads(sys.argv[1])
assert d["dryRun"] is True
assert d["slug"]=="make-auto-sync-status-honest" or "auto-sync" in d["slug"]
assert d["branch"].startswith("delivery/")
assert d["label"].startswith("PL: "), d
assert "auto-sync" in d["label"].lower() or "honest" in d["label"].lower()
assert d.get("phaseCode")=="PL"
assert d["agent"]=="pi"
' "$json"
  json2="$(DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" spawn --dry-run --base main --issue NOD-99 -- \
    "one login path")"
  python3 -c 'import json,sys
d=json.loads(sys.argv[1])
assert d["issue"]=="NOD-99"
assert d["branch"] in ("nod-99", "NOD-99") or "nod-99" in d["branch"].lower()
assert d["label"].startswith("PL: "), d
assert "NOD-99" in d["label"]
' "$json2"
  # Freeform: issue embedded in the request, no --issue flag
  json3="$(DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" spawn --dry-run --base main -- \
    "NOD-1457 one login path please")"
  python3 -c 'import json,sys
d=json.loads(sys.argv[1])
assert d["issue"]=="NOD-1457", d
assert d.get("issueInferred") is True, d
assert "login" in d["slug"], d
assert "nod-1457" not in d["slug"], d
assert d["branch"].lower()=="nod-1457" or d["branch"].lower().startswith("nod-1457-"), d
assert d["label"].startswith("PL: "), d
assert "NOD-1457" in d["label"], d
assert "login" in d["label"].lower(), d
' "$json3"
  set +e
  out="$(DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" spawn --dry-run --stage EXECUTION_READY \
    --base main -- "invalid direct execution-ready spawn" 2>&1)"
  code=$?
  set -e
  [[ "$code" -ne 0 ]] || return 1
  printf '%s' "$out" | rg -q "no explicit execution-ready review request" || return 1
}

test_spawn_uses_workspace_scoped_default_agent_name() {
  local repo="$TMP_ROOT/spawn-agent-repo"
  local worktree="$TMP_ROOT/spawn-agent-worktree"
  local fake_bin="$TMP_ROOT/fake-herdr-spawn-agent"
  local log="$TMP_ROOT/fake-herdr-spawn-agent.log"
  make_repo "$repo"
  make_repo "$worktree"
  mkdir -p "$fake_bin"
  cat >"$fake_bin/herdr" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"$FAKE_HERDR_LOG"
if [[ "$1" == "worktree" && "$2" == "create" ]]; then
  python3 - "$FAKE_HERDR_WORKTREE" <<'PY'
import json,sys
worktree=sys.argv[1]
print(json.dumps({"result": {
  "root_pane": {"pane_id": "wTest42:p1", "cwd": worktree, "workspace_id": "wTest42", "tab_id": "wTest42:t1"},
  "workspace": {"workspace_id": "wTest42", "worktree": {"checkout_path": worktree}},
  "worktree": {"path": worktree, "open_workspace_id": "wTest42"},
  "tab": {"tab_id": "wTest42:t1"},
}}))
PY
fi
SH
  chmod +x "$fake_bin/herdr"
  local json
  json="$(PATH="$fake_bin:$PATH" FAKE_HERDR_LOG="$log" FAKE_HERDR_WORKTREE="$worktree" \
    HERDR_WORKSPACE_ID=wCaller HERDR_TAB_ID=wCaller:t9 HERDR_PANE_ID=wCaller:p9 \
    "$DELIVERY" --cwd "$repo" spawn --base main --quiet --json -- "agent collision regression")"
  python3 -c 'import json,re,sys
p=json.loads(sys.argv[1])
assert p["agent"]["name"] == "delivery-77546573743432", p
assert re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", p["agent"]["name"]), p
assert p["agent"]["prompted"] is True, p
' "$json"
  rg -Fxq "agent start delivery-77546573743432 --kind pi --pane wTest42:p1 --timeout 60000" "$log" || return 1
  rg -q "^agent prompt delivery-77546573743432 " "$log" || return 1
  rg -Fq 'Read `.delivery/AGENT_BRIEF.md` when present. If it is absent, continue from `delivery show`, the ledger, and the plan' "$log" || return 1
  rg -Fxq "workspace rename wTest42 PL: agent collision regression" "$log" || return 1
  rg -Fxq "tab rename wTest42:t1 PL: agent collision regression" "$log" || return 1
  ! rg -q "^(workspace|tab) rename wCaller" "$log" || return 1
}

test_reflect_logs_outside_worktree() {
  local repo="$TMP_ROOT/reflect-repo"
  local pi_home="$TMP_ROOT/pi-home"
  make_repo "$repo"
  mkdir -p "$pi_home"
  DELIVERY_SKIP_HERDR=1 HOME="$pi_home" "$DELIVERY" --cwd "$repo" bootstrap --slug reflect-demo >/dev/null
  DELIVERY_SKIP_HERDR=1 HOME="$pi_home" "$DELIVERY" --cwd "$repo" reflect \
    --trigger end-of-run --outcome done \
    --friction "manual stage updates forgotten twice" \
    --rework "had to redo plan after missing customer impact" \
    --improvement "bootstrap should print reflect reminder earlier" \
    --mark-done >/dev/null
  [[ -f "$pi_home/.pi/DELIVERY_REFLECTIONS.md" ]] || return 1
  [[ -f "$pi_home/.pi/delivery-reflections.jsonl" ]] || return 1
  rg -q "manual stage updates forgotten twice" "$pi_home/.pi/DELIVERY_REFLECTIONS.md" || return 1
  rg -q "Friction|Rework challenges|Improvement opportunities" "$pi_home/.pi/DELIVERY_REFLECTIONS.md" || return 1
  python3 - "$pi_home/.pi/delivery-reflections.jsonl" "$repo/.delivery/ledger.json" <<'PY'
import json,sys
line=open(sys.argv[1]).read().strip().splitlines()[-1]
rec=json.loads(line)
assert "manual stage updates" in rec["friction"][0]
assert rec["outcome"]=="done"
assert rec["delivery"]["slug"]=="reflect-demo"
led=json.load(open(sys.argv[2]))
assert led["stage"]=="DONE"
assert led.get("lastReflectionAt")
PY
  out="$(DELIVERY_SKIP_HERDR=1 HOME="$pi_home" "$DELIVERY" --cwd "$repo" reflect --list 3)"
  printf '%s' "$out" | rg -q "reflect-demo|end-of-run|DELIVERY_REFLECTIONS" || return 1
}

test_bootstrap_writes_agent_brief() {
  local repo="$TMP_ROOT/bootstrap-repo"
  make_repo "$repo"
  out="$(DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" bootstrap \
    --slug cold-start --goal "ship delivery navigator for new agents" 2>&1)"
  [[ -f "$repo/.delivery/ledger.json" ]] || return 1
  [[ -f "$repo/.delivery/AGENT_BRIEF.md" ]] || return 1
  printf '%s' "$out" | rg -q "Recommended next step|guidance, not gates|Cold start|delivery show" || {
    # brief is printed to stdout; accept either printed brief or file contents
    rg -q "Recommended next step" "$repo/.delivery/AGENT_BRIEF.md" || return 1
    rg -q "guidance, not gates" "$repo/.delivery/AGENT_BRIEF.md" || return 1
    rg -q "Linear optional|attach later|set --issue" "$repo/.delivery/AGENT_BRIEF.md" || return 1
  }
  rg -q "Recommended next step" "$repo/.delivery/AGENT_BRIEF.md" || return 1
  rg -q "run-plan|reviewed-html-plan|autoreview" "$repo/.delivery/AGENT_BRIEF.md" || return 1
  # refresh keeps ledger and rewrites brief
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" stage PLAN_DRAFT >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" bootstrap --refresh >/dev/null
  rg -q "PLAN_DRAFT" "$repo/.delivery/AGENT_BRIEF.md" || return 1
  # attach issue after bootstrap
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" set --issue NOD-42 --retarget-id >/dev/null
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
assert d["issue"]=="NOD-42"
assert d.get("goal")
assert d.get("agentBrief")
PY
}

test_browser_review_waits_for_explicit_readiness_request() {
  local repo="$TMP_ROOT/readiness-request-repo"
  make_repo "$repo"
  mkdir -p "$repo/thoughts/plans"
  printf '<article data-plan>browser-review</article>\n' >"$repo/thoughts/plans/x.html"
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" bootstrap --slug readiness-demo --plan thoughts/plans/x.html >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" stage PLAN_BROWSER_REVIEW >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" bootstrap --refresh >/dev/null
  local brief="$repo/.delivery/AGENT_BRIEF.md"
  rg -q "Request execution-ready review" "$brief" || return 1
  rg -q "plan-reviewer-execution-ready" "$brief" || return 1
  rg -q "planReadinessRequest" "$brief" || return 1
  local out
  out="$(DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" check -v)"
  printf '%s' "$out" | rg -q "MISSING_planReadinessRequest" || return 1
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" record planReadinessRequest --status pass \
    --summary "Doct execution-ready review request" >/dev/null
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
assert d["evidence"]["planReadinessRequest"]["status"] == "pass"
assert d["evidence"]["planReadinessRequest"]["planSha256"]
PY
}

test_readiness_review_requires_explicit_request() {
  local repo="$TMP_ROOT/readiness-authorization-repo"
  make_repo "$repo"
  mkdir -p "$repo/thoughts/validation"
  printf '# Sol plan review\n\nVERDICT: PLAN_EXECUTION_READY\n' >"$repo/thoughts/validation/plan-review.md"
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" init --issue NOD-READINESS --plan README.md >/dev/null
  set +e
  out="$(DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" stage PLAN_PM_REVIEW 2>&1)"
  code=$?
  set -e
  [[ "$code" -ne 0 ]] || return 1
  printf '%s' "$out" | rg -q "no explicit execution-ready review request" || return 1
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" record planReadinessRequest --status pass \
    --summary "Doct execution-ready review request" >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" stage PLAN_PM_REVIEW >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" stage PLAN_TECH_REVIEW >/dev/null
  set +e
  out="$(DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" stage EXECUTION_READY 2>&1)"
  code=$?
  set -e
  [[ "$code" -ne 0 ]] || return 1
  printf '%s' "$out" | rg -q "Sol medium planner review" || return 1

  set +e
  out="$(DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" record planTech --status pass \
    --artifact thoughts/validation/plan-review.md --summary "independent plan review" \
    --reviewer planner --model openai-codex/gpt-5.6-terra --reasoning-level medium \
    --verdict PLAN_EXECUTION_READY 2>&1)"
  code=$?
  set -e
  [[ "$code" -ne 0 ]] || return 1
  printf '%s' "$out" | rg -q "requires model openai-codex/gpt-5.6-sol" || return 1

  set +e
  out="$(DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" record planTech --status pass \
    --artifact thoughts/validation/plan-review.md --summary "missing profile decision" \
    --reviewer planner --model openai-codex/gpt-5.6-sol --reasoning-level medium \
    --verdict PLAN_EXECUTION_READY 2>&1)"
  code=$?
  set -e
  [[ "$code" -ne 0 ]] || return 1
  printf '%s' "$out" | rg -q "requires --implementation-profile" || return 1

  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" record planTech --status pass \
    --artifact thoughts/validation/plan-review.md --summary "independent Sol medium plan review" \
    --reviewer planner --model openai-codex/gpt-5.6-sol --reasoning-level medium \
    --verdict PLAN_EXECUTION_READY --implementation-profile terra-high \
    --implementation-rationale "deterministic tests strongly validate this plan" >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" stage EXECUTION_READY >/dev/null
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
review=json.load(open(sys.argv[1]))["evidence"]["planTech"]
assert review["status"] == "pass"
assert review["reviewer"] == "planner"
assert review["model"] == "openai-codex/gpt-5.6-sol"
assert review["reasoningLevel"] == "medium"
assert review["verdict"] == "PLAN_EXECUTION_READY"
assert review["implementationProfile"] == "terra-high"
assert "deterministic tests" in review["implementationRationale"]
assert review["planSha256"]
PY

  printf '\nmaterial plan change\n' >>"$repo/README.md"
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" record planReadinessRequest --status pass \
    --summary "fresh execution-ready request" >/dev/null
  set +e
  out="$(DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" stage EXECUTION_READY 2>&1)"
  code=$?
  set -e
  [[ "$code" -ne 0 ]] || return 1
  printf '%s' "$out" | rg -q "Sol medium planner review" || return 1
}

test_init_cannot_bypass_authorization_stages() {
  local repo="$TMP_ROOT/init-authorization-repo"
  make_repo "$repo"
  mkdir -p "$repo/thoughts/plans"
  printf '<article data-plan>init-bypass</article>\n' >"$repo/thoughts/plans/x.html"
  set +e
  out="$(DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" init --stage EXECUTION_READY \
    --plan thoughts/plans/x.html 2>&1)"
  code=$?
  set -e
  [[ "$code" -ne 0 ]] || return 1
  printf '%s' "$out" | rg -q "no explicit execution-ready review request" || return 1
  [[ ! -f "$repo/.delivery/ledger.json" ]] || return 1

  set +e
  out="$(DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" init --stage IMPLEMENTING \
    --plan thoughts/plans/x.html 2>&1)"
  code=$?
  set -e
  [[ "$code" -ne 0 ]] || return 1
  printf '%s' "$out" | rg -q "no explicit execution-ready review request" || return 1
}

test_bootstrap_cannot_bypass_authorization_stages() {
  local repo="$TMP_ROOT/bootstrap-authorization-repo"
  make_repo "$repo"
  mkdir -p "$repo/thoughts/plans"
  printf '<article data-plan>bootstrap-bypass</article>\n' >"$repo/thoughts/plans/x.html"
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" bootstrap --plan thoughts/plans/x.html >/dev/null

  set +e
  out="$(DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" bootstrap --force \
    --stage EXECUTION_READY --plan thoughts/plans/x.html 2>&1)"
  code=$?
  set -e
  [[ "$code" -ne 0 ]] || return 1
  printf '%s' "$out" | rg -q "no explicit execution-ready review request" || return 1

  set +e
  out="$(DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" bootstrap \
    --stage EXECUTION_READY 2>&1)"
  code=$?
  set -e
  [[ "$code" -ne 0 ]] || return 1
  printf '%s' "$out" | rg -q "no explicit execution-ready review request" || return 1
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
assert json.load(open(sys.argv[1]))["stage"] == "INTAKE"
PY
}

test_approval_cannot_bypass_readiness_request() {
  local repo="$TMP_ROOT/approval-authorization-repo"
  make_repo "$repo"
  mkdir -p "$repo/thoughts/plans"
  printf '<article data-plan>approval-bypass</article>\n' >"$repo/thoughts/plans/x.html"
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" init --plan thoughts/plans/x.html >/dev/null
  # Simulate a legacy/child-ledger path that wrote EXECUTION_READY directly.
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
path=sys.argv[1]
d=json.load(open(path))
d["stage"]="EXECUTION_READY"
json.dump(d,open(path,"w"),indent=2)
PY
  set +e
  out="$(PI_MODEL=test-model PI_REASONING_LEVEL=high DELIVERY_SKIP_HERDR=1 \
    "$DELIVERY" --cwd "$repo" approve-implementation --source chat \
    --summary "Operator received status, changes, model, and steps" 2>&1)"
  code=$?
  set -e
  [[ "$code" -ne 0 ]] || return 1
  printf '%s' "$out" | rg -q "no explicit execution-ready review request" || return 1
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
assert json.load(open(sys.argv[1]))["implementationApproval"]["status"] == "pending"
PY
  # Even a forged current approval cannot enter IMPLEMENTING without readiness.
  python3 - "$repo/.delivery/ledger.json" "$repo/thoughts/plans/x.html" <<'PY'
import hashlib,json,sys
ledger_path,plan_path=sys.argv[1:]
d=json.load(open(ledger_path))
d["implementationApproval"].update({
    "status":"approved",
    "planSha256":hashlib.sha256(open(plan_path,"rb").read()).hexdigest(),
})
json.dump(d,open(ledger_path,"w"),indent=2)
PY
  set +e
  out="$(DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" stage IMPLEMENTING 2>&1)"
  code=$?
  set -e
  [[ "$code" -ne 0 ]] || return 1
  printf '%s' "$out" | rg -q "no current execution-ready review request" || return 1
}

test_held_execution_ready_requires_manual_authorization() {
  local repo="$TMP_ROOT/implementation-approval-repo"
  local fake_bin="$TMP_ROOT/fake-herdr-implementation"
  local herdr_log="$TMP_ROOT/fake-herdr-implementation.log"
  make_repo "$repo"
  mkdir -p "$repo/thoughts/plans" "$repo/thoughts/validation" "$fake_bin"
  printf '<article data-plan>revision-one</article>\n' >"$repo/thoughts/plans/x.html"
  printf '# Plan review\n\nVERDICT: PLAN_EXECUTION_READY\n' >"$repo/thoughts/validation/x-plan-review.md"
  cat >"$fake_bin/herdr" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"$FAKE_HERDR_LOG"
if [[ "$1" == "tab" && "$2" == "create" ]]; then
  printf '{"result":{"tab":{"tab_id":"w1:t9"},"root_pane":{"pane_id":"w1:p2"}}}\n'
fi
exit 0
SH
  chmod +x "$fake_bin/herdr"

  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" init --plan thoughts/plans/x.html >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" record planReadinessRequest --status pass \
    --summary "Doct execution-ready review request" >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" record planTech --status pass \
    --artifact thoughts/validation/x-plan-review.md --summary "independent Sol medium plan review" \
    --reviewer planner --model openai-codex/gpt-5.6-sol --reasoning-level medium \
    --verdict PLAN_EXECUTION_READY --implementation-profile sol-medium \
    --implementation-rationale "critical correctness is difficult to validate fully before merge" >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" stage EXECUTION_READY >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" bootstrap --refresh >/dev/null
  rg -q "Automatic execution-ready handoff" "$repo/.delivery/AGENT_BRIEF.md" || return 1
  rg -q 'continue through PR creation' "$repo/.delivery/AGENT_BRIEF.md" || return 1
  set +e
  out="$(DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" stage IMPLEMENTING 2>&1)"
  code=$?
  set -e
  [[ "$code" -ne 0 ]] || return 1
  printf '%s' "$out" | rg -q "current implementation authorization" || return 1

  set +e
  out="$(PATH="$fake_bin:$PATH" FAKE_HERDR_LOG="$herdr_log" HERDR_WORKSPACE_ID=w1 HERDR_PANE_ID=w1:p1 \
    "$DELIVERY" --cwd "$repo" approve-implementation --source chat \
    --summary "Operator deliberately selected Terra high" \
    --model openai-codex/gpt-5.6-terra --reasoning-level high 2>&1)"
  code=$?
  set -e
  [[ "$code" -ne 0 ]] || return 1
  printf '%s' "$out" | rg -q "manual implementation model selection requires --override-reason" || return 1
  [[ ! -s "$herdr_log" ]] || return 1

  PATH="$fake_bin:$PATH" FAKE_HERDR_LOG="$herdr_log" HERDR_WORKSPACE_ID=w1 HERDR_TAB_ID=w1:t1 HERDR_PANE_ID=w1:p1 \
    PI_PROVIDER=openai-codex PI_MODEL=gpt-5.6-terra PI_REASONING_LEVEL=high \
    "$DELIVERY" --cwd "$repo" approve-implementation --source chat \
    --summary "Operator deliberately selected Terra high" \
    --model openai-codex/gpt-5.6-terra --reasoning-level high \
    --override-reason "manual operator choice for this implementation" >/dev/null
  rg -q "tab create" "$herdr_log" || return 1
  rg -q "tab focus w1:t9" "$herdr_log" || return 1
  rg -q -- "--workspace w1" "$herdr_log" || return 1
  rg -q -- "--label impl ·" "$herdr_log" || return 1
  rg -q -- "--no-focus" "$herdr_log" || return 1
  rg -q "agent start implementation-.* --kind pi --pane w1:p2 --timeout 60000 -- --provider openai-codex --model gpt-5.6-terra --thinking high" "$herdr_log" || return 1
  rg -q "agent prompt implementation-" "$herdr_log" || return 1
  ! rg -q "pane[[:space:]]+split" "$herdr_log" || return 1

  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
review=d["evidence"]["planTech"]
approval=d["implementationApproval"]
profile=d["implementationProfile"]
assert review["implementationProfile"] == "sol-medium"
assert "difficult to validate" in review["implementationRationale"]
assert approval["status"] == "approved"
assert approval["source"] == "chat"
assert approval["profile"] == "manual"
assert approval["model"] == "openai-codex/gpt-5.6-terra"
assert approval["reasoningLevel"] == "high"
assert approval["selectionSource"] == "manual-approval"
assert approval["overrideReason"] == "manual operator choice for this implementation"
assert approval["planSha256"]
assert profile["status"] == "ready"
assert profile["profile"] == "manual"
assert profile["provider"] == "openai-codex"
assert profile["model"] == "gpt-5.6-terra"
assert profile["reasoningLevel"] == "high"
assert profile["agentName"].startswith("implementation-")
assert profile["paneId"] == "w1:p2"
assert profile["tabId"] == "w1:t9"
assert profile["tabLabel"].startswith("impl · "), profile
assert profile["sourcePaneId"] == "w1:p1"
assert profile["planSha256"] == approval["planSha256"]
owner=d.get("workspaceOwner") or {}
assert owner.get("role") == "implementation"
assert owner.get("tabId") == "w1:t9"
assert owner.get("paneId") == "w1:p2"
assert any((t or {}).get("tabId") == "w1:t1" for t in (d.get("tabsToRetire") or [])), d.get("tabsToRetire")
PY

  local launch_log_lines
  launch_log_lines="$(wc -l <"$herdr_log")"
  set +e
  out="$(PATH="$fake_bin:$PATH" FAKE_HERDR_LOG="$herdr_log" HERDR_WORKSPACE_ID=w1 HERDR_PANE_ID=w1:p1 \
    "$DELIVERY" --cwd "$repo" approve-implementation --source chat --summary again 2>&1)"
  code=$?
  set -e
  [[ "$code" -ne 0 ]] || return 1
  printf '%s' "$out" | rg -q "already approved" || return 1
  [[ "$(wc -l <"$herdr_log")" -eq "$launch_log_lines" ]] || return 1

  set +e
  out="$(PATH="$fake_bin:$PATH" FAKE_HERDR_LOG="$herdr_log" HERDR_WORKSPACE_ID=w1 HERDR_PANE_ID=w1:p1 \
    "$DELIVERY" --cwd "$repo" start-implementation 2>&1)"
  code=$?
  set -e
  [[ "$code" -ne 0 ]] || return 1
  printf '%s' "$out" | rg -q "already ready" || return 1
  [[ "$(wc -l <"$herdr_log")" -eq "$launch_log_lines" ]] || return 1

  set +e
  out="$(PI_PROVIDER=openai-codex PI_MODEL=gpt-5.6-terra PI_REASONING_LEVEL=high HERDR_PANE_ID=w1:p1 \
    DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" verify-implementation-profile 2>&1)"
  code=$?
  set -e
  [[ "$code" -ne 0 ]] || return 1
  printf '%s' "$out" | rg -q "current Herdr pane does not match" || return 1

  set +e
  out="$(PI_PROVIDER=openai-codex PI_MODEL=gpt-5.6-sol PI_REASONING_LEVEL=medium HERDR_PANE_ID=w1:p2 \
    DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" stage IMPLEMENTING 2>&1)"
  code=$?
  set -e
  [[ "$code" -ne 0 ]] || return 1
  printf '%s' "$out" | rg -q "current Pi runtime is not the selected implementation model" || return 1

  : >"$herdr_log"
  PATH="$fake_bin:$PATH" FAKE_HERDR_LOG="$herdr_log" \
    PI_PROVIDER=openai-codex PI_MODEL=gpt-5.6-terra PI_REASONING_LEVEL=high \
    HERDR_WORKSPACE_ID=w1 HERDR_TAB_ID=w1:t9 HERDR_PANE_ID=w1:p2 \
    "$DELIVERY" --cwd "$repo" verify-implementation-profile >/dev/null
  rg -q "tab close w1:t1" "$herdr_log" || return 1
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
assert d.get("tabsToRetire") in (None, [])
assert d["workspaceOwner"]["role"] == "implementation"
PY
  PI_PROVIDER=openai-codex PI_MODEL=gpt-5.6-terra PI_REASONING_LEVEL=high HERDR_PANE_ID=w1:p2 \
    DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" stage IMPLEMENTING >/dev/null

  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
path=sys.argv[1]; d=json.load(open(path)); d.setdefault("labels", {}).update({"herdrWorkspaceId":"w1","herdrTabId":"w1:t1"}); json.dump(d,open(path,"w"),indent=2)
PY
  : >"$herdr_log"
  # Ambient HERDR_TAB_ID still points at retired planning tab; chrome follows workspaceOwner.
  PATH="$fake_bin:$PATH" FAKE_HERDR_LOG="$herdr_log" HERDR_WORKSPACE_ID=w1 HERDR_TAB_ID=w1:t1 HERDR_PANE_ID=w1:p2 \
    "$DELIVERY" --cwd "$repo" stage SCOPED_REVIEW >/dev/null
  rg -q "tab rename w1:t9" "$herdr_log" || return 1
  ! rg -q "tab rename w1:t1" "$herdr_log" || return 1
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
assert d["workspaceOwner"]["tabId"] == "w1:t9"
assert d["labels"]["herdrTabId"] == "w1:t9"
assert d["implementationProfile"]["tabId"] == "w1:t9"
PY

  printf '<article data-plan>revision-two</article>\n' >"$repo/thoughts/plans/x.html"
  set +e
  out="$(DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" stage EXECUTION_READY 2>&1)"
  code=$?
  set -e
  [[ "$code" -ne 0 ]] || return 1
  printf '%s' "$out" | rg -q "plan changed after the recorded execution-ready review request" || return 1
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" record planReadinessRequest --status pass \
    --summary "Fresh Doct execution-ready review request" >/dev/null
  set +e
  out="$(DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" stage EXECUTION_READY 2>&1)"
  code=$?
  set -e
  [[ "$code" -ne 0 ]] || return 1
  printf '%s' "$out" | rg -q "Sol medium planner review" || return 1
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" \
    revoke-implementation-approval --reason "material plan feedback" >/dev/null
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
assert d["implementationApproval"]["status"] == "pending"
assert d["implementationApproval"]["reason"] == "material plan feedback"
assert d["implementationProfile"]["status"] == "pending"
PY
}

test_normal_work_routes_to_terra_high() {
  local repo="$TMP_ROOT/terra-implementation-repo"
  local fake_bin="$TMP_ROOT/fake-herdr-terra"
  local herdr_log="$TMP_ROOT/fake-herdr-terra.log"
  make_repo "$repo"
  mkdir -p "$repo/thoughts/plans" "$repo/thoughts/validation" "$fake_bin"
  printf '<article data-plan>testable implementation</article>\n' >"$repo/thoughts/plans/x.html"
  printf '# Plan review\n\nVERDICT: PLAN_EXECUTION_READY\n' >"$repo/thoughts/validation/x-plan-review.md"
  cat >"$fake_bin/herdr" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"$FAKE_HERDR_LOG"
if [[ "$1" == "tab" && "$2" == "create" ]]; then
  printf '{"result":{"tab":{"tab_id":"w-deep:t2"},"root_pane":{"pane_id":"w-deep:p2"}}}\n'
fi
exit 0
SH
  chmod +x "$fake_bin/herdr"

  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" init --plan thoughts/plans/x.html >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" record planReadinessRequest --status pass --summary ready >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" record planTech --status pass \
    --artifact thoughts/validation/x-plan-review.md --summary "testable work" --reviewer planner \
    --model openai-codex/gpt-5.6-sol --reasoning-level medium --verdict PLAN_EXECUTION_READY \
    --implementation-profile terra-high \
    --implementation-rationale "deterministic unit and integration tests exercise the changed behavior" >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" stage EXECUTION_READY >/dev/null

  PATH="$fake_bin:$PATH" FAKE_HERDR_LOG="$herdr_log" HERDR_WORKSPACE_ID=w-deep HERDR_PANE_ID=w-deep:p1 \
    "$DELIVERY" --cwd "$repo" approve-implementation --source chat \
    --summary "Operator approved the planner-selected Terra implementation profile" >/dev/null
  rg -q "agent start implementation-.* --kind pi --pane w-deep:p2 --timeout 60000 -- --provider openai-codex --model gpt-5.6-terra --thinking high" "$herdr_log" || return 1

  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
review=d["evidence"]["planTech"]
approval=d["implementationApproval"]
profile=d["implementationProfile"]
assert review["implementationProfile"] == "terra-high"
assert "deterministic" in review["implementationRationale"]
assert approval["profile"] == "terra-high"
assert approval["model"] == "openai-codex/gpt-5.6-terra"
assert approval["reasoningLevel"] == "high"
assert profile["profile"] == "terra-high"
assert profile["provider"] == "openai-codex"
assert profile["model"] == "gpt-5.6-terra"
assert profile["reasoningLevel"] == "high"
PY

  set +e
  out="$(PI_PROVIDER=openai-codex PI_MODEL=gpt-5.6-sol PI_REASONING_LEVEL=medium HERDR_PANE_ID=w-deep:p2 \
    DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" verify-implementation-profile 2>&1)"
  code=$?
  set -e
  [[ "$code" -ne 0 ]] || return 1
  printf '%s' "$out" | rg -q "current Pi runtime is not the selected implementation model" || return 1

  # Simulate a launch recorded by the older fixed-profile ledger schema.
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
path=sys.argv[1]
d=json.load(open(path))
for key in ("profile", "selectionSource", "overrideReason"):
    d["implementationApproval"].pop(key, None)
    d["implementationProfile"].pop(key, None)
json.dump(d,open(path,"w"),indent=2)
PY

  PI_PROVIDER=openai-codex PI_MODEL=gpt-5.6-terra PI_REASONING_LEVEL=high HERDR_PANE_ID=w-deep:p2 \
    DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" verify-implementation-profile \
    --adopt-current-runtime --reason "manual operator model choice for this implementation" >/dev/null
  PI_PROVIDER=openai-codex PI_MODEL=gpt-5.6-terra PI_REASONING_LEVEL=high HERDR_PANE_ID=w-deep:p2 \
    DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" stage IMPLEMENTING >/dev/null
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
assert d["implementationApproval"]["selectionSource"] == "manual-runtime"
assert d["implementationApproval"]["model"] == "openai-codex/gpt-5.6-terra"
assert d["implementationApproval"]["reasoningLevel"] == "high"
assert d["implementationProfile"]["profile"] == "manual"
assert d["implementationProfile"]["modelRef"] == "openai-codex/gpt-5.6-terra"
assert d["implementationProfile"]["reasoningLevel"] == "high"
assert "manual operator" in d["implementationProfile"]["overrideReason"]
PY
}

test_execution_ready_auto_starts_without_operator_approval() {
  local repo="$TMP_ROOT/auto-execution-repo"
  local fake_bin="$TMP_ROOT/fake-herdr-auto-execution"
  local herdr_log="$TMP_ROOT/fake-herdr-auto-execution.log"
  make_repo "$repo"
  mkdir -p "$repo/thoughts/plans" "$repo/thoughts/validation" "$fake_bin"
  printf '<article data-plan>automatic execution</article>\n' >"$repo/thoughts/plans/x.html"
  printf 'VERDICT: PLAN_EXECUTION_READY\n' >"$repo/thoughts/validation/x-plan-review.md"
  cat >"$fake_bin/herdr" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"$FAKE_HERDR_LOG"
if [[ "$1" == "tab" && "$2" == "create" ]]; then
  printf '{"result":{"tab":{"tab_id":"w-auto:t2"},"root_pane":{"pane_id":"w-auto:p2"}}}\n'
fi
exit 0
SH
  chmod +x "$fake_bin/herdr"
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" init --plan thoughts/plans/x.html >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" record planReadinessRequest --status pass --summary ready >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" record planTech --status pass \
    --artifact thoughts/validation/x-plan-review.md --summary ready --reviewer planner \
    --model openai-codex/gpt-5.6-sol --reasoning-level medium --verdict PLAN_EXECUTION_READY \
    --implementation-profile terra-high --implementation-rationale "tests strongly validate the change" >/dev/null

  PATH="$fake_bin:$PATH" FAKE_HERDR_LOG="$herdr_log" HERDR_WORKSPACE_ID=w-auto HERDR_PANE_ID=w-auto:p1 \
    "$DELIVERY" --cwd "$repo" stage EXECUTION_READY >/dev/null
  rg -q "agent start implementation-.* --kind pi --pane w-auto:p2.*--model gpt-5.6-terra --thinking high" "$herdr_log" || return 1
  rg -q "agent prompt implementation-" "$herdr_log" || return 1
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
assert d["stage"] == "EXECUTION_READY"
assert d["implementationApproval"]["status"] == "approved"
assert d["implementationApproval"]["source"] == "workflow"
assert d["implementationProfile"]["status"] == "ready"
PY
}

test_implementation_agent_launch_race_reconciles_live_agent() {
  local repo="$TMP_ROOT/implementation-launch-reconcile-repo"
  local fake_bin="$TMP_ROOT/fake-herdr-implementation-reconcile"
  local herdr_log="$TMP_ROOT/fake-herdr-implementation-reconcile.log"
  make_repo "$repo"
  mkdir -p "$repo/thoughts/plans" "$repo/thoughts/validation" "$fake_bin"
  printf '<article data-plan>ready</article>\n' >"$repo/thoughts/plans/x.html"
  printf 'VERDICT: PLAN_EXECUTION_READY\n' >"$repo/thoughts/validation/x-plan-review.md"
  cat >"$fake_bin/herdr" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"$FAKE_HERDR_LOG"
if [[ "$1" == "tab" && "$2" == "create" ]]; then
  printf '{"result":{"tab":{"tab_id":"w-race:t2"},"root_pane":{"pane_id":"w-race:p2"}}}\n'
elif [[ "$1" == "agent" && "$2" == "start" ]]; then
  echo 'synthetic shell-readiness race' >&2
  exit 9
elif [[ "$1" == "agent" && "$2" == "get" ]]; then
  printf '{"result":{"agent":{"agent":"pi","agent_status":"idle","name":"implementation-race","pane_id":"w-race:p2"}}}\n'
fi
exit 0
SH
  chmod +x "$fake_bin/herdr"
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" init --plan thoughts/plans/x.html >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" record planReadinessRequest --status pass --summary ready >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" record planTech --status pass \
    --artifact thoughts/validation/x-plan-review.md --summary ready --reviewer planner \
    --model openai-codex/gpt-5.6-sol --reasoning-level medium --verdict PLAN_EXECUTION_READY \
    --implementation-profile terra-high --implementation-rationale "tests strongly validate the change" >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" stage EXECUTION_READY >/dev/null
  PATH="$fake_bin:$PATH" FAKE_HERDR_LOG="$herdr_log" HERDR_WORKSPACE_ID=w-race HERDR_PANE_ID=w-race:p1 \
    "$DELIVERY" --cwd "$repo" approve-implementation --source chat --summary approved \
    --agent-name implementation-race >/dev/null
  rg -q "agent get implementation-race" "$herdr_log" || return 1
  rg -q "agent prompt implementation-race" "$herdr_log" || return 1
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
assert d["implementationProfile"]["status"] == "ready"
assert any(h.get("type") == "implementation_agent_reconciled" for h in d["history"])
PY
}

test_done_rejects_incomplete_implementation_run() {
  local repo="$TMP_ROOT/done-integrity-repo"
  local pi_home="$TMP_ROOT/done-integrity-home"
  make_repo "$repo"
  mkdir -p "$pi_home"
  DELIVERY_SKIP_HERDR=1 HOME="$pi_home" "$DELIVERY" --cwd "$repo" init --plan README.md >/dev/null
  DELIVERY_SKIP_HERDR=1 HOME="$pi_home" "$DELIVERY" --cwd "$repo" stage IMPLEMENTING >/dev/null 2>&1 || true
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
path=sys.argv[1];d=json.load(open(path));d["history"].append({"at":"2026-01-01T00:00:00Z","type":"stage","detail":"EXECUTION_READY -> IMPLEMENTING"});d["stage"]="IMPLEMENTING";json.dump(d,open(path,"w"),indent=2)
PY
  set +e
  out="$(DELIVERY_SKIP_HERDR=1 HOME="$pi_home" "$DELIVERY" --cwd "$repo" reflect \
    --trigger end-of-run --outcome done --mark-done 2>&1)"
  code=$?
  set -e
  [[ "$code" -ne 0 ]] || return 1
  printf '%s' "$out" | rg -q "cannot enter DONE.*missing required delivery evidence" || return 1
  DELIVERY_SKIP_HERDR=1 HOME="$pi_home" "$DELIVERY" --cwd "$repo" blocker \
    'pause before completion' --mark-blocked >/dev/null
  set +e
  out="$(DELIVERY_SKIP_HERDR=1 HOME="$pi_home" "$DELIVERY" --cwd "$repo" blocker \
    --clear --stage DONE 2>&1)"
  code=$?
  set -e
  [[ "$code" -ne 0 ]] || return 1
  printf '%s' "$out" | rg -q "cannot restore DONE.*missing required delivery evidence" || return 1
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
path=sys.argv[1];d=json.load(open(path));assert d["stage"] == "BLOCKED";d["blockers"]=[];d["stage"]="IMPLEMENTING"
for key in ("implementation","scopedReview","implPm","completionEval","customerImpact","autoreview","verify","pr"):
    d["evidence"][key]["status"]="pass"
d["evidence"]["adversarialQa"]["status"]="na"
d["prUrl"]="https://example.test/pull/1"
d["completenessReview"]={"status":"waived","summary":"explicit test waiver"}
json.dump(d,open(path,"w"),indent=2)
PY
  DELIVERY_SKIP_HERDR=1 HOME="$pi_home" "$DELIVERY" --cwd "$repo" reflect \
    --trigger end-of-run --outcome done --mark-done >/dev/null
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
assert json.load(open(sys.argv[1]))["stage"] == "DONE"
PY
}

test_plan_review_cycle_limit_stops_fourth_gap() {
  local repo="$TMP_ROOT/plan-review-budget-repo"
  make_repo "$repo"
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" init --plan README.md >/dev/null
  for cycle in 1 2 3; do
    DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" record planTech --status gap \
      --summary "cycle $cycle blocker set" >/dev/null
  done
  set +e
  out="$(DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" record planTech --status gap \
    --summary "cycle 4 blocker" 2>&1)"
  code=$?
  set -e
  [[ "$code" -ne 0 ]] || return 1
  printf '%s' "$out" | rg -q "planning review convergence budget exhausted" || return 1
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]));assert d["planReviewCycleCount"] == 3
PY
}

test_implementation_agent_launch_failures_are_not_ready() {
  local repo="$TMP_ROOT/implementation-launch-failure-repo"
  local fake_bin="$TMP_ROOT/fake-herdr-implementation-failure"
  local mode_file="$TMP_ROOT/fake-herdr-implementation-mode"
  make_repo "$repo"
  mkdir -p "$repo/thoughts/plans" "$repo/thoughts/validation" "$fake_bin"
  printf '<article data-plan>ready</article>\n' >"$repo/thoughts/plans/x.html"
  printf 'VERDICT: PLAN_EXECUTION_READY\n' >"$repo/thoughts/validation/x-plan-review.md"
  printf 'start-fail\n' >"$mode_file"
  cat >"$fake_bin/herdr" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
if [[ -n "${FAKE_HERDR_LOG:-}" ]]; then
  printf '%s\n' "$*" >>"$FAKE_HERDR_LOG"
fi
mode="$(cat "$FAKE_HERDR_MODE")"
if [[ "$1" == "tab" && "$2" == "create" ]]; then
  printf '{"result":{"tab":{"tab_id":"w2:t2"},"root_pane":{"pane_id":"w2:p2"}}}\n'
elif [[ "$1" == "tab" && "$2" == "close" ]]; then
  exit 0
elif [[ "$1" == "agent" && "$2" == "start" && "$mode" == "start-fail" ]]; then
  echo "synthetic start failure" >&2
  exit 9
elif [[ "$1" == "agent" && "$2" == "start" && "$mode" == "hold" ]]; then
  : >"$FAKE_HERDR_HOLD_READY"
  while [[ ! -e "$FAKE_HERDR_HOLD_RELEASE" ]]; do sleep 0.02; done
elif [[ "$1" == "agent" && "$2" == "prompt" && "$mode" == "prompt-fail" ]]; then
  echo "synthetic prompt failure" >&2
  exit 8
fi
exit 0
SH
  chmod +x "$fake_bin/herdr"
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" init --plan thoughts/plans/x.html >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" record planReadinessRequest --status pass --summary ready >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" record planTech --status pass \
    --artifact thoughts/validation/x-plan-review.md --summary ready --reviewer planner \
    --model openai-codex/gpt-5.6-sol --reasoning-level medium --verdict PLAN_EXECUTION_READY \
    --implementation-profile terra-high --implementation-rationale "tests strongly validate the change" >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" stage EXECUTION_READY >/dev/null

  local fail_log="$TMP_ROOT/fake-herdr-implementation-failure.log"
  : >"$fail_log"
  set +e
  PATH="$fake_bin:$PATH" FAKE_HERDR_MODE="$mode_file" FAKE_HERDR_LOG="$fail_log" HERDR_WORKSPACE_ID=w2 HERDR_TAB_ID=w2:t1 HERDR_PANE_ID=w2:p1 \
    "$DELIVERY" --cwd "$repo" approve-implementation --source chat --summary approved >/dev/null 2>&1
  code=$?
  set -e
  [[ "$code" -ne 0 ]] || return 1
  rg -q "tab close w2:t2" "$fail_log" || return 1
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
assert d["stage"] == "EXECUTION_READY"
assert d["implementationApproval"]["status"] == "approved"
assert d["implementationProfile"]["status"] == "start-failed"
assert d["implementationProfile"].get("tabId") in (None, "")
assert d["implementationProfile"].get("paneId") in (None, "")
PY

  printf 'prompt-fail\n' >"$mode_file"
  set +e
  PATH="$fake_bin:$PATH" FAKE_HERDR_MODE="$mode_file" HERDR_WORKSPACE_ID=w2 HERDR_PANE_ID=w2:p1 \
    "$DELIVERY" --cwd "$repo" start-implementation >/dev/null 2>&1
  code=$?
  set -e
  [[ "$code" -ne 0 ]] || return 1
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
assert d["stage"] == "EXECUTION_READY"
assert d["implementationProfile"]["status"] == "prompt-failed"
PY

  local hold_ready="$TMP_ROOT/fake-herdr-hold-ready"
  local hold_release="$TMP_ROOT/fake-herdr-hold-release"
  local first_output="$TMP_ROOT/fake-herdr-first-launch.out"
  printf 'hold\n' >"$mode_file"
  rm -f "$hold_ready" "$hold_release"
  PATH="$fake_bin:$PATH" FAKE_HERDR_MODE="$mode_file" FAKE_HERDR_HOLD_READY="$hold_ready" \
    FAKE_HERDR_HOLD_RELEASE="$hold_release" HERDR_WORKSPACE_ID=w2 HERDR_PANE_ID=w2:p1 \
    "$DELIVERY" --cwd "$repo" start-implementation >"$first_output" 2>&1 &
  local first_pid=$!
  local ready_seen=0
  for _ in $(seq 1 100); do
    if [[ -e "$hold_ready" ]]; then ready_seen=1; break; fi
    sleep 0.02
  done
  if [[ "$ready_seen" -ne 1 ]]; then
    touch "$hold_release"
    wait "$first_pid" || true
    return 1
  fi
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" note "concurrent independent evidence" >/dev/null
  set +e
  out="$(PATH="$fake_bin:$PATH" FAKE_HERDR_MODE="$mode_file" HERDR_WORKSPACE_ID=w2 HERDR_PANE_ID=w2:p1 \
    "$DELIVERY" --cwd "$repo" start-implementation 2>&1)"
  code=$?
  set -e
  touch "$hold_release"
  wait "$first_pid" || return 1
  [[ "$code" -ne 0 ]] || return 1
  printf '%s' "$out" | rg -q "launch is already in progress" || return 1
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
assert d["stage"] == "EXECUTION_READY"
assert d["implementationApproval"]["status"] == "approved"
assert d["implementationProfile"]["status"] == "ready"
assert any(n.get("text")=="concurrent independent evidence" for n in d["notes"])
assert d["ledgerRevision"] > 0
PY
}

test_docs_use_labeled_tabs_not_pane_splits() {
  local corpus=(
    "$ROOT/skills/delivery-run/SKILL.md"
    "$ROOT/skills/run-plan/SKILL.md"
    "$ROOT/skills/supervise/SKILL.md"
    "$ROOT/skills/supervise/supervisor-prompt.md"
    "$ROOT/_pi/prompts/delivery:run.md"
    "$ROOT/_pi/prompts/delivery:bootstrap.md"
    "$ROOT/AGENTS.md"
  )
  local file
  for file in "${corpus[@]}"; do
    [[ -f "$file" ]] || return 1
  done
  ! rg -n "visible adjacent|adjacent visible|splits an adjacent|[Ss]plits the driving pane|adjacent Herdr pane|adjacent pane|pane[[:space:]]+split" "${corpus[@]}" || return 1
  rg -q "labeled.*tab|tab create" "$ROOT/skills/delivery-run/SKILL.md" || return 1
  rg -q "labeled.*tab|tab create" "$ROOT/skills/supervise/SKILL.md" || return 1
  help="$($DELIVERY completion-review --help)"
  printf '%s' "$help" | rg -q "tab-create/start/prompt" || return 1
  ! printf '%s' "$help" | rg -q "split[/]start[/]prompt" || return 1
}

test_operator_attention_reconciles_delivery_state() {
  local repo="$TMP_ROOT/operator-attention-repo"
  local fake_bin="$TMP_ROOT/operator-attention-bin"
  local attention_log="$TMP_ROOT/operator-attention.log"
  make_repo "$repo"
  mkdir -p "$repo/thoughts/plans" "$repo/thoughts/validation" "$fake_bin"
  printf '<!doctype html><html><head><title>Plan X</title></head><body><h1>Plan X</h1></body></html>\n' >"$repo/thoughts/plans/x.html"
  printf '<!doctype html><html><head><title>Plan Y</title></head><body><h1>Plan Y</h1></body></html>\n' >"$repo/thoughts/plans/y.html"
  printf 'VERDICT: PLAN_EXECUTION_READY\n' >"$repo/thoughts/validation/plan-review.md"
  cat >"$fake_bin/herdr-operator-attention" <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"$ATTENTION_LOG"
exit "${ATTENTION_EXIT:-0}"
SH
  cat >"$fake_bin/herdr" <<'SH'
#!/usr/bin/env bash
if [[ "$1" == "pane" && "$2" == "split" ]]; then
  printf '{"result":{"pane":{"pane_id":"w-attn:p2"}}}\n'
  exit 0
fi
if [[ "$1" == "agent" && "$2" == "start" ]]; then
  echo 'synthetic launch failure' >&2
  exit 9
fi
exit 0
SH
  chmod +x "$fake_bin/herdr-operator-attention" "$fake_bin/herdr"
  local env_path="$fake_bin:$PATH"

  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" init --plan thoughts/plans/x.html >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" record planReadinessRequest --status pass --summary ready >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" record planTech --status pass \
    --artifact thoughts/validation/plan-review.md --summary ready --reviewer planner \
    --model openai-codex/gpt-5.6-sol --reasoning-level medium --verdict PLAN_EXECUTION_READY \
    --implementation-profile terra-high --implementation-rationale "tests strongly validate the change" >/dev/null

  PATH="$env_path" ATTENTION_LOG="$attention_log" HERDR_PANE_ID=w-attn:p1 \
    "$DELIVERY" --cwd "$repo" stage EXECUTION_READY --hold >/dev/null
  tail -1 "$attention_log" | rg -Fxq 'clear --pane w-attn:p1' || return 1

  set +e
  PATH="$env_path" ATTENTION_LOG="$attention_log" HERDR_PANE_ID=w-attn:p1 \
    "$DELIVERY" --cwd "$repo" approve-implementation --source chat --summary approved >/dev/null 2>&1
  local approve_code=$?
  set -e
  [[ "$approve_code" -ne 0 ]] || return 1
  tail -1 "$attention_log" | rg -Fxq 'clear --pane w-attn:p1' || return 1

  PATH="$env_path" ATTENTION_LOG="$attention_log" HERDR_PANE_ID=w-attn:p1 \
    "$DELIVERY" --cwd "$repo" revoke-implementation-approval --reason feedback >/dev/null
  tail -1 "$attention_log" | rg -Fxq 'clear --pane w-attn:p1' || return 1

  PATH="$env_path" ATTENTION_LOG="$attention_log" HERDR_PANE_ID=w-attn:p1 \
    "$DELIVERY" --cwd "$repo" blocker 'need auth decision' --mark-blocked >/dev/null
  tail -1 "$attention_log" | rg -Fxq 'set --pane w-attn:p1 --kind blocker --message need auth decision' || return 1
  PATH="$env_path" ATTENTION_LOG="$attention_log" HERDR_PANE_ID=w-attn:p1 \
    "$DELIVERY" --cwd "$repo" blocker --clear >/dev/null
  PATH="$env_path" ATTENTION_LOG="$attention_log" HERDR_PANE_ID=w-attn:p1 \
    "$DELIVERY" --cwd "$repo" stage EXECUTION_READY --hold >/dev/null
  tail -1 "$attention_log" | rg -Fxq 'clear --pane w-attn:p1' || return 1

  # A current approved state clears, then changing the plan path invalidates it and restores approval wait.
  python3 - "$repo/.delivery/ledger.json" "$repo/thoughts/plans/x.html" <<'PY'
import hashlib,json,sys
path,plan=sys.argv[1:];d=json.load(open(path));d['implementationApproval'].update({'status':'approved','planSha256':hashlib.sha256(open(plan,'rb').read()).hexdigest()});json.dump(d,open(path,'w'),indent=2)
PY
  PATH="$env_path" ATTENTION_LOG="$attention_log" HERDR_PANE_ID=w-attn:p1 \
    "$DELIVERY" --cwd "$repo" set --plan thoughts/plans/y.html >/dev/null
  tail -1 "$attention_log" | rg -Fxq 'clear --pane w-attn:p1' || return 1

  # Fresh readiness records also revoke an otherwise current approval and reconcile immediately.
  python3 - "$repo/.delivery/ledger.json" "$repo/thoughts/plans/y.html" <<'PY'
import hashlib,json,sys
path,plan=sys.argv[1:];d=json.load(open(path));d['implementationApproval'].update({'status':'approved','planSha256':hashlib.sha256(open(plan,'rb').read()).hexdigest()});json.dump(d,open(path,'w'),indent=2)
PY
  PATH="$env_path" ATTENTION_LOG="$attention_log" HERDR_PANE_ID=w-attn:p1 \
    "$DELIVERY" --cwd "$repo" record planReadinessRequest --status pass --summary refreshed >/dev/null
  tail -1 "$attention_log" | rg -Fxq 'clear --pane w-attn:p1' || return 1

  PATH="$env_path" ATTENTION_LOG="$attention_log" HERDR_PANE_ID=w-attn:p1 \
    "$DELIVERY" --cwd "$repo" stage PLAN_BROWSER_REVIEW >/dev/null
  tail -1 "$attention_log" | rg -Fxq 'clear --pane w-attn:p1' || return 1

  local before_skip
  before_skip="$(wc -l <"$attention_log")"
  PATH="$env_path" ATTENTION_LOG="$attention_log" HERDR_PANE_ID=w-attn:p1 DELIVERY_SKIP_HERDR=1 \
    "$DELIVERY" --cwd "$repo" stage PR_OPEN >/dev/null
  [[ "$(wc -l <"$attention_log")" -eq "$before_skip" ]] || return 1
}

test_skill_doctrine_wording() {
  rg -q "guidance, not gates|Guidance, not gates|never hard-block|always exits 0" \
    "$ROOT/skills/delivery-run/SKILL.md" || return 1
  rg -q "plan-reviewer-execution-ready" "$ROOT/skills/delivery-run/SKILL.md" || return 1
  rg -q "approve-implementation" "$ROOT/skills/delivery-run/SKILL.md" || return 1
  rg -q "planReadinessRequest|plan-reviewer-execution-ready" \
    "$ROOT/skills/delivery-run/scripts/delivery" || return 1
  rg -q "approve-implementation" "$ROOT/skills/delivery-run/scripts/delivery" || return 1
  rg -q "plan-reviewer-execution-ready" "$ROOT/skills/reviewed-html-plan/SKILL.md" || return 1
  rg -q "openai-codex/gpt-5.6-sol" "$ROOT/skills/reviewed-html-plan/SKILL.md" || return 1
  rg -q 'subagent_type.*planner|`planner` subagent' "$ROOT/skills/reviewed-html-plan/SKILL.md" || return 1
  rg -q "reasoning-level medium --verdict PLAN_EXECUTION_READY" "$ROOT/skills/reviewed-html-plan/SKILL.md" || return 1
  rg -q "Automatic execution-ready handoff" "$ROOT/skills/reviewed-html-plan/SKILL.md" || return 1
  rg -q "verify-implementation-profile" "$ROOT/skills/run-plan/SKILL.md" || return 1
  rg -q "start-implementation" "$ROOT/skills/delivery-run/SKILL.md" || return 1
  rg -q '"terra-high"' "$ROOT/skills/delivery-run/scripts/delivery" || return 1
  rg -q '"provider": "openai-codex"' "$ROOT/skills/delivery-run/scripts/delivery" || return 1
  rg -q '"model": "gpt-5.6-terra"' "$ROOT/skills/delivery-run/scripts/delivery" || return 1
  ! rg -q 'deepseek-v4-flash' "$ROOT/skills/delivery-run/scripts/delivery" || return 1
  rg -q '"sol-medium"' "$ROOT/skills/delivery-run/scripts/delivery" || return 1
  rg -q 'DEFAULT_IMPLEMENTATION_PROFILE = "terra-high"' "$ROOT/skills/delivery-run/scripts/delivery" || return 1
  rg -q "COMPLETENESS_REVIEW" "$ROOT/skills/delivery-run/SKILL.md" || return 1
  rg -q "xai/grok-4.5:high" "$ROOT/skills/run-plan/SKILL.md" || return 1
  rg -q "completion-review" "$ROOT/_pi/prompts/delivery:run.md" || return 1
  rg -q "automatically authorizes the exact reviewed plan" "$ROOT/_pi/prompts/dev:reviewed-html-plan.md" || return 1
  rg -q 'delivery stage EXECUTION_READY' "$ROOT/_pi/prompts/delivery:run.md" || return 1
  rg -q 'continues through PR creation' "$ROOT/_pi/prompts/delivery:bootstrap.md" || return 1
  rg -q "PLAN_TITLE" "$ROOT/skills/delivery-run/scripts/delivery" || return 1
  rg -q "Untitled Plan" "$ROOT/skills/doct-document-ops/SKILL.md" || return 1
  rg -q -- "--title" "$ROOT/skills/doct-document-ops/SKILL.md" || return 1
  rg -q "YAML frontmatter" "$ROOT/skills/doct-document-ops/SKILL.md" || return 1
  rg -q "Doct document / tree title" "$ROOT/skills/doct-document-ops/SKILL.md" || return 1
  rg -qi "in-content plan title" "$ROOT/skills/doct-document-ops/SKILL.md" || return 1
}

test_plan_title_extraction_and_advisory() {
  python3 - "$DELIVERY" <<'PY'
import importlib.util, sys, tempfile
from importlib.machinery import SourceFileLoader
from pathlib import Path
path = Path(sys.argv[1]).resolve()
loader = SourceFileLoader("delivery_cli", str(path))
spec = importlib.util.spec_from_loader(loader.name, loader)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
loader.exec_module(mod)
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    good = root / "good.markdoc"
    good.write_text("---\ntitle: Real Plan Title\nstatus: browser-review-draft\n---\n\n# Real Plan Title\n\n{% section id=\"goal\" title=\"Goal\" %}\nok\n{% /section %}\n", encoding="utf-8")
    bad = root / "bad.markdoc"
    bad.write_text("# Heading only is not enough\n\n## Goal\nDo stuff.\n", encoding="utf-8")
    mismatch_md = root / "mismatch.markdoc"
    mismatch_md.write_text("---\ntitle: Frontmatter Title\n---\n\n# Different Heading\n", encoding="utf-8")
    html = root / "good.html"
    html.write_text("<!doctype html><html><head><title>HTML Plan Title</title></head><body><h1>HTML Plan Title</h1></body></html>", encoding="utf-8")
    mismatch_html = root / "mismatch.html"
    mismatch_html.write_text("<!doctype html><html><head><title>Doc Title</title></head><body><h1>Body Title</h1></body></html>", encoding="utf-8")
    assert mod.extract_plan_title(good) == "Real Plan Title"
    h2_only = root / "h2-only.markdoc"
    h2_only.write_text("---\ntitle: Correct title\n---\n\n## Goal\nBody.\n", encoding="utf-8")
    assert mod.extract_plan_title(h2_only) == "Correct title"
    assert mod.plan_title_problem({"plan": "h2-only.markdoc", "stage": "PLAN_BROWSER_REVIEW", "worktree": str(root)}, root) is None
    assert mod.extract_plan_title(bad) is None
    assert mod.extract_plan_title(html) == "HTML Plan Title"
    assert mod.extract_plan_title(mismatch_html) is None
    case_html = root / "case.html"
    case_html.write_text("<!doctype html><html><head><title>Canonical Title</title></head><body><h1>canonical title</h1></body></html>", encoding="utf-8")
    assert mod.extract_plan_title(case_html) is None
    assert not mod.titles_match("Canonical Title", "canonical title")
    assert mod.titles_match("Canonical  Title", "Canonical Title")
    assert mod.extract_plan_title(mismatch_md) is None
    assert mod.is_untitled_plan_title("Untitled Plan")
    assert not mod.is_untitled_plan_title("Real Plan Title")
    ledger_bad = {"plan": "bad.markdoc", "stage": "PLAN_BROWSER_REVIEW", "worktree": str(root)}
    problem = mod.plan_title_problem(ledger_bad, root)
    assert problem and "frontmatter" in problem.lower(), problem
    ledger_mismatch = {"plan": "mismatch.html", "stage": "PLAN_BROWSER_REVIEW", "worktree": str(root)}
    mprob = mod.plan_title_problem(ledger_mismatch, root)
    assert mprob and "mismatched" in mprob.lower(), mprob
    ledger_recorded = {
        "plan": "good.html",
        "stage": "PLAN_BROWSER_REVIEW",
        "worktree": str(root),
        "doctTitle": "Stale Doct Title",
        "doctTitleSource": "doct",
    }
    rprob = mod.plan_title_problem(ledger_recorded, root)
    assert rprob and "does not match" in rprob.lower(), rprob
    # Content-derived planContentTitle alone must not invent Doct drift.
    ledger_content_only = {
        "plan": "good.html",
        "stage": "PLAN_BROWSER_REVIEW",
        "worktree": str(root),
        "planContentTitle": "HTML Plan Title",
    }
    assert mod.plan_title_problem(ledger_content_only, root) is None
    advisories = mod.build_advisories(ledger_bad, root)
    codes = {a["code"] for a in advisories}
    assert "PLAN_TITLE" in codes, advisories
    ledger_good = {"plan": "good.markdoc", "stage": "PLAN_BROWSER_REVIEW", "worktree": str(root)}
    assert mod.plan_title_problem(ledger_good, root) is None
    codes_good = {a["code"] for a in mod.build_advisories(ledger_good, root)}
    assert "PLAN_TITLE" not in codes_good, codes_good
PY

  local repo="$TMP_ROOT/plan-title-repo"
  make_repo "$repo"
  mkdir -p "$repo/thoughts/plans"
  cat >"$repo/thoughts/plans/untitled.markdoc" <<'EOF'
# Only a heading

## Goal
Missing frontmatter title.
EOF
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" init --slug title-check --plan thoughts/plans/untitled.markdoc >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" stage PLAN_BROWSER_REVIEW >/dev/null
  local out
  out="$(DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" check --json)"
  python3 -c 'import json,sys; d=json.loads(sys.argv[1]); codes={a["code"] for a in d.get("advisories") or []}; assert "PLAN_TITLE" in codes, d' "$out"
}


test_workspace_owner_handoff_and_witness_close() {
  local repo="$TMP_ROOT/owner-handoff-repo"
  local fake_bin="$TMP_ROOT/fake-herdr-owner-handoff"
  local herdr_log="$TMP_ROOT/fake-herdr-owner-handoff.log"
  make_repo "$repo"
  mkdir -p "$repo/thoughts/plans" "$repo/thoughts/validation" "$fake_bin"
  printf '<article data-plan>owner-handoff</article>\n' >"$repo/thoughts/plans/x.html"
  printf 'VERDICT: PLAN_EXECUTION_READY\n' >"$repo/thoughts/validation/x-plan-review.md"
  cat >"$fake_bin/herdr" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"$FAKE_HERDR_LOG"
if [[ "$1" == "tab" && "$2" == "create" ]]; then
  if rg -q "complete ·" <<<"$*"; then
    printf '{"result":{"tab":{"tab_id":"w-own:t-complete"},"root_pane":{"pane_id":"w-own:p-complete"}}}\n'
  else
    printf '{"result":{"tab":{"tab_id":"w-own:t-impl"},"root_pane":{"pane_id":"w-own:p-impl"}}}\n'
  fi
fi
exit 0
SH
  chmod +x "$fake_bin/herdr"
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" init --plan thoughts/plans/x.html >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" record planReadinessRequest --status pass --summary ready >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" record planTech --status pass \
    --artifact thoughts/validation/x-plan-review.md --summary ready --reviewer planner \
    --model openai-codex/gpt-5.6-sol --reasoning-level medium --verdict PLAN_EXECUTION_READY \
    --implementation-profile terra-high --implementation-rationale "tests strongly validate the change" >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" stage EXECUTION_READY >/dev/null

  PATH="$fake_bin:$PATH" FAKE_HERDR_LOG="$herdr_log" HERDR_WORKSPACE_ID=w-own HERDR_TAB_ID=w-own:t-plan HERDR_PANE_ID=w-own:p-plan \
    "$DELIVERY" --cwd "$repo" approve-implementation --source chat --summary go >/dev/null
  rg -q "tab focus w-own:t-impl" "$herdr_log" || return 1
  ! rg -q "tab close w-own:t-plan" "$herdr_log" || return 1
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
assert d["workspaceOwner"]["role"]=="implementation"
assert d["workspaceOwner"]["tabId"]=="w-own:t-impl"
assert any(t.get("tabId")=="w-own:t-plan" and t.get("reason")=="planning-handoff-complete" for t in d.get("tabsToRetire") or [])
PY

  : >"$herdr_log"
  PATH="$fake_bin:$PATH" FAKE_HERDR_LOG="$herdr_log" \
    PI_PROVIDER=openai-codex PI_MODEL=gpt-5.6-terra PI_REASONING_LEVEL=high \
    HERDR_WORKSPACE_ID=w-own HERDR_TAB_ID=w-own:t-impl HERDR_PANE_ID=w-own:p-impl \
    "$DELIVERY" --cwd "$repo" verify-implementation-profile >/dev/null
  rg -q "tab close w-own:t-plan" "$herdr_log" || return 1
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); assert d.get("tabsToRetire") in (None, [])
PY

  PATH="$fake_bin:$PATH" FAKE_HERDR_LOG="$herdr_log" HERDR_WORKSPACE_ID=w-own HERDR_PANE_ID=w-own:p-impl \
    "$DELIVERY" --cwd "$repo" completion-review >/dev/null
  : >"$herdr_log"
  PATH="$fake_bin:$PATH" FAKE_HERDR_LOG="$herdr_log" HERDR_WORKSPACE_ID=w-own HERDR_TAB_ID=w-own:t-impl HERDR_PANE_ID=w-own:p-impl \
    "$DELIVERY" --cwd "$repo" completion-review --waive --summary "test waiver closes witness" >/dev/null
  rg -q "tab close w-own:t-complete" "$herdr_log" || return 1
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
assert d["completenessReview"]["status"]=="waived"
assert d["workspaceOwner"]["tabId"]=="w-own:t-impl"
PY
}

run_test test_workspace_owner_handoff_and_witness_close
run_test test_plan_title_extraction_and_advisory
run_test test_init_creates_ledger
run_test test_record_receipts_coexist_and_validate
run_test test_unprotected_stage_moves_without_gates
run_test test_check_exit_zero_with_gaps
run_test test_record_and_show
run_test test_completion_review_dry_run_uses_tab_create
run_test test_completion_review_launch_creates_labeled_tab
run_test test_completion_review_rerun_reuses_tab
run_test test_completion_review_rerun_rejects_legacy_record_without_tab
run_test test_agent_tab_create_failure_paths
run_test test_merge_ready_requires_validated_completeness_review
run_test test_accepted_completeness_review_allows_merge_ready_only_while_fresh
run_test test_completion_review_rejects_prior_round_verdict
run_test test_completeness_parser_reports_wrapped_duplicate_malformed_and_truncated
run_test test_ledger_lock_serializes_and_rejects_stale_writer
run_test test_ledger_lock_timeout_reports_holder_metadata
run_test test_force_reinitialization_uses_locked_replace_semantics
run_test test_unrelated_writer_proceeds_during_implementation_launch_lease
run_test test_board_lists_multiple
run_test test_stages_lists_guidance
run_test test_set_issue_after_start
run_test test_bootstrap_writes_agent_brief
run_test test_reflect_logs_outside_worktree
run_test test_phase_herdr_label_format
run_test test_spawn_dry_run_names_from_goal
run_test test_spawn_uses_workspace_scoped_default_agent_name
run_test test_browser_review_waits_for_explicit_readiness_request
run_test test_readiness_review_requires_explicit_request
run_test test_init_cannot_bypass_authorization_stages
run_test test_bootstrap_cannot_bypass_authorization_stages
run_test test_approval_cannot_bypass_readiness_request
run_test test_held_execution_ready_requires_manual_authorization
run_test test_normal_work_routes_to_terra_high
run_test test_execution_ready_auto_starts_without_operator_approval
run_test test_implementation_agent_launch_race_reconciles_live_agent
run_test test_done_rejects_incomplete_implementation_run
run_test test_plan_review_cycle_limit_stops_fourth_gap
run_test test_implementation_agent_launch_failures_are_not_ready
run_test test_docs_use_labeled_tabs_not_pane_splits
run_test test_operator_attention_reconciles_delivery_state
run_test test_skill_doctrine_wording

printf '\n%d/%d passed\n' "$TESTS_PASSED" "$TESTS_RUN"
if [[ "$TESTS_FAILED" -ne 0 ]]; then
  exit 1
fi
