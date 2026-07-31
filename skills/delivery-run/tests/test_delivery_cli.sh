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
assert d["issue"]=="NOD-1"
assert d["stage"]=="INTAKE"
assert d["doctrine"]=="guidance-not-gates"
assert "planPm" in d["evidence"]
assert d["plan"]=="thoughts/plans/x.html"
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
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" record customerImpact --status pass \
    --summary "operators unblocked" --promised "honest status" --observed "status axes" >/dev/null
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
assert d["evidence"]["autoreview"]["status"]=="pass"
assert d["completionEval"]["status"]=="gap"
assert "BDD missing" in d["completionEval"]["gaps"]
assert d["customerImpact"]["summary"]=="operators unblocked"
assert "honest status" in d["customerImpact"]["promised"]
PY
  out="$(DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" show)"
  printf '%s' "$out" | rg -q "NOD-4" || return 1
  printf '%s' "$out" | rg -q "autoreview: pass" || return 1
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
  printf '%s' "$out" | rg -q "Pause: present the operator approval summary" || return 1
  ! printf '%s' "$out" | rg -q "EXECUTION_READY.*Use /skill:run-plan" || return 1
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
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" stage EXECUTION_READY >/dev/null
}

test_execution_ready_requires_current_operator_approval() {
  local repo="$TMP_ROOT/implementation-approval-repo"
  make_repo "$repo"
  mkdir -p "$repo/thoughts/plans"
  printf '<article data-plan>revision-one</article>\n' >"$repo/thoughts/plans/x.html"
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" init --plan thoughts/plans/x.html >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" record planReadinessRequest --status pass \
    --summary "Doct execution-ready review request" >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" stage EXECUTION_READY >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" bootstrap --refresh >/dev/null
  rg -q "Execution-ready approval pause" "$repo/.delivery/AGENT_BRIEF.md" || return 1
  rg -qi 'do \*\*not\*\* invoke `run-plan`' "$repo/.delivery/AGENT_BRIEF.md" || return 1
  set +e
  out="$(DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" stage IMPLEMENTING 2>&1)"
  code=$?
  set -e
  [[ "$code" -ne 0 ]] || return 1
  printf '%s' "$out" | rg -q "explicit operator implementation approval" || return 1
  PI_MODEL=test-model PI_REASONING_LEVEL=high DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" \
    approve-implementation --source chat --summary "Operator received status, changes, model, and steps" >/dev/null
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" stage IMPLEMENTING >/dev/null
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
approval=json.load(open(sys.argv[1]))["implementationApproval"]
assert approval["status"] == "approved"
assert approval["source"] == "chat"
assert approval["model"] == "test-model"
assert approval["reasoningLevel"] == "high"
assert approval["planSha256"]
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
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" stage EXECUTION_READY >/dev/null
  set +e
  out="$(DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" stage IMPLEMENTING 2>&1)"
  code=$?
  set -e
  [[ "$code" -ne 0 ]] || return 1
  printf '%s' "$out" | rg -q "plan changed after" || return 1
  DELIVERY_SKIP_HERDR=1 "$DELIVERY" --cwd "$repo" \
    revoke-implementation-approval --reason "material plan feedback" >/dev/null
  python3 - "$repo/.delivery/ledger.json" <<'PY'
import json,sys
approval=json.load(open(sys.argv[1]))["implementationApproval"]
assert approval["status"] == "pending"
assert approval["reason"] == "material plan feedback"
PY
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
  rg -q "Execution-ready operator approval pause" "$ROOT/skills/reviewed-html-plan/SKILL.md" || return 1
  rg -q "implementation approval" "$ROOT/skills/run-plan/SKILL.md" || return 1
  rg -q "operator-approval summary" "$ROOT/_pi/prompts/dev:reviewed-html-plan.md" || return 1
  rg -q 'in `EXECUTION_READY`, pause before product-code work' "$ROOT/_pi/prompts/delivery:run.md" || return 1
  rg -q 'except at `EXECUTION_READY`' "$ROOT/_pi/prompts/delivery:bootstrap.md" || return 1
}

run_test test_init_creates_ledger
run_test test_unprotected_stage_moves_without_gates
run_test test_check_exit_zero_with_gaps
run_test test_record_and_show
run_test test_board_lists_multiple
run_test test_stages_lists_guidance
run_test test_set_issue_after_start
run_test test_bootstrap_writes_agent_brief
run_test test_reflect_logs_outside_worktree
run_test test_phase_herdr_label_format
run_test test_spawn_dry_run_names_from_goal
run_test test_browser_review_waits_for_explicit_readiness_request
run_test test_readiness_review_requires_explicit_request
run_test test_execution_ready_requires_current_operator_approval
run_test test_skill_doctrine_wording

printf '\n%d/%d passed\n' "$TESTS_PASSED" "$TESTS_RUN"
if [[ "$TESTS_FAILED" -ne 0 ]]; then
  exit 1
fi
