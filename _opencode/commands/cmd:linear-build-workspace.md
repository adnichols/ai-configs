---
description: Run a deterministic Linear issue build in an OpenCode workspace
argument-hint: "ISSUE_KEY [BASE_REF]"
model: openai/gpt-5.6-sol
reasoningEffort: medium
subtask: false
---

# Linear Issue Build Workspace Runner

Build one Linear issue through an OpenCode-registered workspace, not a naked git worktree. The OpenCode workspace is the unit of orchestration so the build appears in the OpenCode workspace picker and has a durable run ledger enforced by `linear_build_orchestrator.py`.

**Arguments**: `$ARGUMENTS`

## Parse Arguments

- `ISSUE_KEY` is required, e.g. `NOD-123`.
- `BASE_REF` is optional and defaults to `origin/develop`.

If `ISSUE_KEY` is missing, stop with:

```text
Usage: /cmd:linear-build-workspace ISSUE_KEY [BASE_REF]
Example: /cmd:linear-build-workspace NOD-662 origin/develop
```

## Non-Negotiable Rules

- OpenCode is the orchestrator. Do not delegate orchestration to Hermes.
- This slash-command is an autonomous build authorization. Within the issue scope and guarded ledger workflow, the operator has already authorized planning research, implementation, commits, pushes, PR creation, Linear linking/state updates, and bounded remediation. Do not ask for additional permission to commit, push, create a PR, or continue to the next guarded stage.
- User feedback is not a normal control surface for this workflow. Resolve uncertainty by inspecting the issue, plan, codebase, docs, tests, prior decisions, and review artifacts; delegate research if useful. Ask the operator only for a true blocking product/security decision that cannot be resolved from available evidence and would materially change intended behavior.
- Create or reuse an OpenCode workspace before planning or implementation.
- The OpenCode session must be created with the target `workspaceID` and with the session HTTP `directory` set to the workspace directory. Changing `cwd` after the session starts does not move the session into the workspace list.
- If this command was launched from a root-repo session before the workspace existed, do not stop for manual handoff. Launch a replacement workspace-owned session with `launch_linear_build_workspace.py`, report the new session/workspace, and stop only this misplaced root session.
- Never run broad environment dumps such as `printenv`, `env`, or `set` to prove session ownership. If a narrow environment value is needed, read only the named variable. Secret exposure is a blocker.
- Do not create a standalone git worktree outside OpenCode workspace registration.
- Keep one durable run ledger at `thoughts/runs/<issue-slug>.md` inside the workspace.
- Use `linear_build_orchestrator.py` to initialize the ledger, guard stage transitions, record artifact verdicts, and record blockers.
- Every stage must write an exact verdict through the helper before the next stage starts.
- Do not treat timeouts, native evidence gaps, or synthetic browser events as acceptable validation.
- Do not push or open a PR until validation, code review, and PM review are complete; once those gates pass, push and open the PR without asking for extra approval.
- After the PR exists, monitor GitHub feedback and keep addressing all remaining P1/P2 feedback until the mechanical PR feedback artifact reports `PR_FEEDBACK_CLEAR`. Do not stop after the first remediation pass while P1/P2 items remain.

## Stage 0: Preconditions and Issue Capture

Run:

```bash
ltui auth test
gh auth status
git status --porcelain=v1
git fetch --prune --tags
```

If the current repo is dirty, continue only if the dirty files are unrelated to the workspace setup. Do not modify or revert unrelated files.

Fetch issue metadata:

```bash
RUN_TMP="${TMPDIR:-/tmp}/opencode-linear-build/${ISSUE_KEY}"
mkdir -p "${RUN_TMP}"
ltui --format json --fields identifier,title,url,state,project \
  issues view "${ISSUE_KEY}" --no-attachment-probe > "${RUN_TMP}/${ISSUE_KEY}.json"
```

Capture:

- `ISSUE_TITLE`
- `ISSUE_URL`
- `ISSUE_STATE`
- `ISSUE_PROJECT`
- `BASE_REF` defaulting to `origin/develop`

## Stage 1: Create or Reuse OpenCode Workspace

Use the helper script so OpenCode workspace registration is the source of truth:

```bash
python3 "$HOME/.config/opencode/scripts/create_linear_workspace.py" \
  "${ISSUE_KEY}" \
  --base-ref "${BASE_REF}" \
  --title "${ISSUE_TITLE}" \
  --repo "$(git rev-parse --show-toplevel)" \
  > "${RUN_TMP}/${ISSUE_KEY}-workspace.json"
```

The helper must report a `workspaceID` like `wrk_nod_123` and a workspace directory under OpenCode's workspace storage. Verify it is in the OpenCode workspace list:

```bash
opencode debug scrap
WORKSPACE_ID="$(python3 -c 'import re,sys; print("wrk_" + re.sub(r"[^a-z0-9]+", "_", sys.argv[1].lower()).strip("_"))' "${ISSUE_KEY}")"
opencode db "select id,type,branch,directory from workspace where id = '${WORKSPACE_ID}'" --format json
```

If the workspace is not listed, stop with `BLOCKED_WORKSPACE_NOT_REGISTERED`. Do not fall back to a plain git worktree.

All remaining work must run from a session that is workspace-owned by the helper's `workspaceID`, not merely from an agent process whose `cwd` was changed to the workspace directory. In practice, the command can safely continue only when its current directory is exactly the helper-reported workspace directory and the OpenCode workspace row matches the same `workspaceID` and directory. Do not inspect the full process environment to decide this.

Run this mechanical directory check after workspace verification:

```bash
WORKSPACE_DIR="$(python3 -c 'import json,sys; data=json.load(open(sys.argv[1])); print(data.get("directory") or data.get("workspace", {}).get("directory", ""))' "${RUN_TMP}/${ISSUE_KEY}-workspace.json")"
CURRENT_SESSION_DIRECTORY_MATCH="$(python3 -c 'import os,sys; expected=os.path.realpath(sys.argv[1]); actual=os.path.realpath(os.getcwd()); print("yes" if actual == expected else "no")' "${WORKSPACE_DIR}")"
```

If `CURRENT_SESSION_DIRECTORY_MATCH` is `no`, the current session is not already associated with the target workspace. Automatically launch the workspace-owned continuation instead of asking the operator to do it:

```bash
python3 "$HOME/.config/opencode/scripts/launch_linear_build_workspace.py" \
  "${ISSUE_KEY}" \
  --base-ref "${BASE_REF}" \
  --repo "$(git rev-parse --show-toplevel)"
```

Then stop this misplaced root-repo session and report:

```text
HANDOFF_TO_WORKSPACE_SESSION
Workspace: <workspaceID>
Directory: <workspace directory>
Session: <new workspace-owned session id>
Next: monitor the workspace-owned session and ledger; do not continue the build in this root-repo session.
```

This stop is required because OpenCode session/workspace ownership is fixed when the session is created.

## Stage 2: Initialize Enforced Run Ledger

In the workspace directory, initialize the ledger with the orchestration helper. Do not hand-write the initial ledger.

```bash
RUN_TMP="${RUN_TMP:-${TMPDIR:-/tmp}/opencode-linear-build/${ISSUE_KEY}}"
ISSUE_JSON_PATH="${RUN_TMP}/${ISSUE_KEY}.json"
WORKSPACE_JSON_PATH="${RUN_TMP}/${ISSUE_KEY}-workspace.json"
WORKSPACE_DIR="$(python3 -c 'import json,sys; data=json.load(open(sys.argv[1])); print(data.get("directory") or data.get("workspace", {}).get("directory", ""))' "${WORKSPACE_JSON_PATH}")"
ISSUE_TITLE="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("title", ""))' "${ISSUE_JSON_PATH}")"
ISSUE_URL="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("url", ""))' "${ISSUE_JSON_PATH}")"
ISSUE_STATE="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("state", ""))' "${ISSUE_JSON_PATH}")"
ISSUE_PROJECT="$(python3 -c 'import json,sys; value=json.load(open(sys.argv[1])).get("project", ""); print(value.get("name", "") if isinstance(value, dict) else value)' "${ISSUE_JSON_PATH}")"

cd "${WORKSPACE_DIR}"
LEDGER_PATH="$(python3 "$HOME/.config/opencode/scripts/linear_build_orchestrator.py" init \
  --issue-key "${ISSUE_KEY}" \
  --title "${ISSUE_TITLE}" \
  --url "${ISSUE_URL}" \
  --state "${ISSUE_STATE}" \
  --project "${ISSUE_PROJECT}" \
  --base-ref "${BASE_REF}" \
  --workspace-json "${WORKSPACE_JSON_PATH}")"
```

The run ledger must include:

- issue key, title, URL, state, project
- workspace id, workspace directory, branch, base ref
- current stage
- stage verdict table
- artifact paths
- command log
- blocker log
- review/remediation loop count
- manual/native evidence status
- PR URL once created
- exact resume instructions

First ledger verdicts are created by the helper:

```text
STAGE: ISSUE_CAPTURE
VERDICT: PASS
STAGE: WORKSPACE_READY
VERDICT: PASS
STAGE: LEDGER_READY
VERDICT: PASS
```

## Stage 3: Plan

Create one canonical plan in the workspace:

```text
thoughts/plans/<issue-slug>.md
```

Planning requirements:

- include `OPENCODE_PLAN_READY` only if truly execution-ready
- include product-intent alignment
- include observable acceptance criteria
- include BDD scenarios
- include a test coverage matrix
- include repo-specific verification commands
- include manual native/WKWebView evidence if the issue touches native or HUD surfaces
- include `## Progress` and resume instructions

If the plan is not ready, do additional focused research in this session until it is ready. Only write `STAGE: PLAN`, `VERDICT: BLOCKED_RESEARCH_OR_DECISION` and stop when the missing decision is genuinely unresolvable from Linear, repo evidence, docs, tests, product intent, prior plans, or bounded subagent research.

Before starting planning, run:

```bash
python3 "$HOME/.config/opencode/scripts/linear_build_orchestrator.py" guard \
  --ledger "${LEDGER_PATH}" \
  --next-stage PLAN
```

After the plan is ready, record it mechanically:

```bash
python3 "$HOME/.config/opencode/scripts/linear_build_orchestrator.py" stage \
  --ledger "${LEDGER_PATH}" \
  --stage PLAN \
  --verdict OPENCODE_PLAN_READY \
  --artifact "thoughts/plans/<issue-slug>.md" \
  --note "Canonical execution-ready plan created."
```

If planning remains blocked after focused research, record and stop:

```bash
python3 "$HOME/.config/opencode/scripts/linear_build_orchestrator.py" block \
  --ledger "${LEDGER_PATH}" \
  --stage PLAN \
  --code BLOCKED_RESEARCH_OR_DECISION \
  --note "<specific missing evidence or decision>" \
  --evidence "<research artifact path proving the issue cannot be answered from Linear, repo docs, specs, tests, code, or bounded subagent research>"
```

## Stage 4: Plan Gates

Run bounded Codex and Claude Code review gates through the required review runner. Do not substitute OpenCode `research`, `quality-reviewer`, `reviewer-*`, or generic subagents for these two required reviews. The Claude reviewer path delegates transport to the canonical private-tmux interactive launcher; do not invoke Claude Code directly from this command.

```bash
REVIEW_RUN_ID="${ISSUE_KEY}-$(date -u +%Y%m%dT%H%M%SZ)"

python3 "$HOME/.config/opencode/scripts/linear_build_review.py" \
  --kind plan \
  --reviewer codex \
  --issue-key "${ISSUE_KEY}" \
  --plan "thoughts/plans/<issue-slug>.md" \
  --base-ref "${BASE_REF}" \
  --output "thoughts/reviews/codex-plan-review-${REVIEW_RUN_ID}.md"

python3 "$HOME/.config/opencode/scripts/linear_build_review.py" \
  --kind plan \
  --reviewer claude \
  --issue-key "${ISSUE_KEY}" \
  --plan "thoughts/plans/<issue-slug>.md" \
  --base-ref "${BASE_REF}" \
  --output "thoughts/reviews/claude-plan-review-${REVIEW_RUN_ID}.md"
```

Proceed only when the run ledger records:

```text
STAGE: PLAN_GATES
VERDICT: PASS
```

Use the helper to enforce this transition and verify exact artifact first lines:

```bash
python3 "$HOME/.config/opencode/scripts/linear_build_orchestrator.py" guard --ledger "${LEDGER_PATH}" --next-stage PLAN_GATES
python3 "$HOME/.config/opencode/scripts/linear_build_orchestrator.py" artifact-verdict --ledger "${LEDGER_PATH}" --stage PLAN_GATES --artifact thoughts/reviews/codex-plan-review-${REVIEW_RUN_ID}.md --expect EXECUTION_READY --expect PASS_NO_ISSUES --expect BLOCKED_BY_SCOPE_QUESTION --expect BLOCKED_RESEARCH_OR_DECISION
python3 "$HOME/.config/opencode/scripts/linear_build_orchestrator.py" artifact-verdict --ledger "${LEDGER_PATH}" --stage PLAN_GATES --artifact thoughts/reviews/claude-plan-review-${REVIEW_RUN_ID}.md --expect EXECUTION_READY --expect PASS_NO_ISSUES --expect BLOCKED_BY_SCOPE_QUESTION --expect BLOCKED_RESEARCH_OR_DECISION
python3 "$HOME/.config/opencode/scripts/linear_build_orchestrator.py" stage --ledger "${LEDGER_PATH}" --stage PLAN_GATES --verdict PASS --note "Plan review gates passed."
```

If either artifact records a blocked verdict, the helper updates the ledger and exits non-zero. Treat the review as work to integrate, not as a request for operator feedback: inspect the finding, update the plan, rerun the bounded review gate, and continue once the artifacts pass. Stop only when the blocked verdict depends on a true unresolvable product/security decision.

## Stage 5: Implementation

Implement phase-by-phase from the plan.

Before editing product code:

```bash
python3 "$HOME/.config/opencode/scripts/linear_build_orchestrator.py" guard --ledger "${LEDGER_PATH}" --next-stage IMPLEMENTATION
```

Rules:

- update plan progress immediately after each completed phase
- run each phase's targeted verification
- run one scoped `quality-reviewer` pass after each substantial phase
- log any deviation in both the plan and run ledger
- resolve behavior-changing implementation decisions from the plan, Linear issue, product intent, existing repo patterns, and tests before asking the operator; stop only if the decision remains unresolvable and materially changes intended behavior

When implementation is complete:

```bash
python3 "$HOME/.config/opencode/scripts/linear_build_orchestrator.py" stage \
  --ledger "${LEDGER_PATH}" \
  --stage IMPLEMENTATION \
  --verdict PASS \
  --note "Implementation complete against the approved plan."
```

## Stage 6: Validation

Run the plan's full validation bar and the repo-appropriate gates.

Before validation:

```bash
python3 "$HOME/.config/opencode/scripts/linear_build_orchestrator.py" guard --ledger "${LEDGER_PATH}" --next-stage VALIDATION
```

For Heddle-like macOS/HUD work, prefer:

```bash
npm test
npm run design-system:verify
npm run security:check
SPRITE_HUD_ALLOW_TEST_CLERK_KEY=1 npm run build
SPRITE_HUD_ALLOW_TEST_CLERK_KEY=1 npm run mac:build
```

Validation adversity rules:

- Plain `npm test` timeouts are failures until reproduced, fixed, or proven with focused evidence.
- Environment-gated `npm run build` must be recorded honestly; use the documented local override only when the repo allows it.
- Synthetic JS/DOM events cannot satisfy native installed-app evidence requirements.
- If validation cannot be completed, write `VERDICT: BLOCKED_VALIDATION` and stop.

Log commands as they run:

```bash
python3 "$HOME/.config/opencode/scripts/linear_build_orchestrator.py" log-command \
  --ledger "${LEDGER_PATH}" \
  --stage VALIDATION \
  --command "npm test" \
  --result "PASS: <counts>"
```

Record validation result through the helper. Prefer reading the artifact's exact first line so failures are recorded before stopping:

```bash
python3 "$HOME/.config/opencode/scripts/linear_build_orchestrator.py" artifact-verdict \
  --ledger "${LEDGER_PATH}" \
  --stage VALIDATION \
  --artifact /tmp/opencode-validation-${ISSUE_KEY}.md \
  --expect VALIDATION_PASSED \
  --expect VALIDATION_FAILED \
  --expect BLOCKED_VALIDATION
```

## Stage 7: Evidence

If native, HUD, WKWebView, installed app, or browser UX behavior is in scope, collect typed evidence:

- automated unit/build evidence
- browser or web smoke evidence
- installed-app pointer/coordinate path when required
- installed-app Accessibility/AX path when required
- screenshot/log paths
- explicit caveats for anything not captured

Write `VERDICT: PASS` only when evidence matches the plan's acceptance criteria.

Record manual/native evidence status explicitly:

```bash
python3 "$HOME/.config/opencode/scripts/linear_build_orchestrator.py" evidence \
  --ledger "${LEDGER_PATH}" \
  --required \
  --status passed \
  --path /tmp/<evidence-file-or-screenshot>

python3 "$HOME/.config/opencode/scripts/linear_build_orchestrator.py" stage \
  --ledger "${LEDGER_PATH}" \
  --stage EVIDENCE \
  --verdict PASS \
  --note "Manual/native evidence satisfies the plan."
```

If manual evidence is not required, record `--status not_required` and stage `EVIDENCE` as `PASS`. If evidence is pending or blocked, do not advance to review.

## Stage 8: Code Review and PM Review

Run scoped implementation review against the plan. Findings must be classified as:

- `IN_PLAN`
- `PLAN_PREREQUISITE`
- `REGRESSION_FROM_THIS_DIFF`
- `OUT_OF_SCOPE_FOLLOW_UP`
- `QUESTION`

Fix in-plan, prerequisite, regression, BDD-gap, verification-gap, implicit-only-coverage, and misleading-evidence findings before advancing. Use `OUT_OF_SCOPE_FOLLOW_UP` only for real issues that are outside the plan, not required for truthful verification, and not introduced by this workspace; record each with evidence and a tracking destination.

Required code review invocations:

```bash
REVIEW_RUN_ID="${ISSUE_KEY}-$(date -u +%Y%m%dT%H%M%SZ)"

python3 "$HOME/.config/opencode/scripts/linear_build_review.py" \
  --kind code \
  --reviewer codex \
  --issue-key "${ISSUE_KEY}" \
  --plan "thoughts/plans/<issue-slug>.md" \
  --base-ref "${BASE_REF}" \
  --output "thoughts/reviews/codex-code-review-${REVIEW_RUN_ID}.md"

python3 "$HOME/.config/opencode/scripts/linear_build_review.py" \
  --kind code \
  --reviewer claude \
  --issue-key "${ISSUE_KEY}" \
  --plan "thoughts/plans/<issue-slug>.md" \
  --base-ref "${BASE_REF}" \
  --output "thoughts/reviews/claude-code-review-${REVIEW_RUN_ID}.md"
```

Then run post-implementation PM/product review. If PM returns not acceptable, enter a bounded remediation loop and update the run ledger.

Stop after three non-converging review/remediation cycles with `VERDICT: BLOCKED_REVIEW_CONVERGENCE`.

Use exact artifact gates:

```bash
python3 "$HOME/.config/opencode/scripts/linear_build_orchestrator.py" guard --ledger "${LEDGER_PATH}" --next-stage CODE_REVIEW
python3 "$HOME/.config/opencode/scripts/linear_build_orchestrator.py" artifact-verdict --ledger "${LEDGER_PATH}" --stage CODE_REVIEW --artifact thoughts/reviews/codex-code-review-${REVIEW_RUN_ID}.md --expect CODE_REVIEW_ACCEPTABLE --expect PASS_SCOPED --expect PASS_NO_ISSUES --expect CODE_REVIEW_BLOCKED --expect FIX_IN_SCOPE_FINDINGS --expect BLOCKED_BY_SCOPE_QUESTION
python3 "$HOME/.config/opencode/scripts/linear_build_orchestrator.py" artifact-verdict --ledger "${LEDGER_PATH}" --stage CODE_REVIEW --artifact thoughts/reviews/claude-code-review-${REVIEW_RUN_ID}.md --expect CODE_REVIEW_ACCEPTABLE --expect PASS_SCOPED --expect PASS_NO_ISSUES --expect CODE_REVIEW_BLOCKED --expect FIX_IN_SCOPE_FINDINGS --expect BLOCKED_BY_SCOPE_QUESTION

python3 "$HOME/.config/opencode/scripts/linear_build_review.py" \
  --kind pm \
  --reviewer codex \
  --issue-key "${ISSUE_KEY}" \
  --plan "thoughts/plans/<issue-slug>.md" \
  --base-ref "${BASE_REF}" \
  --output "thoughts/reviews/pm-post-implementation-review-${REVIEW_RUN_ID}.md"

python3 "$HOME/.config/opencode/scripts/linear_build_orchestrator.py" guard --ledger "${LEDGER_PATH}" --next-stage PM_REVIEW
python3 "$HOME/.config/opencode/scripts/linear_build_orchestrator.py" artifact-verdict --ledger "${LEDGER_PATH}" --stage PM_REVIEW --artifact thoughts/reviews/pm-post-implementation-review-${REVIEW_RUN_ID}.md --expect PM_ACCEPTABLE_FOR_CODE_REVIEW --expect PM_NOT_ACCEPTABLE
```

Blocked review verdicts are intentionally included in `--expect` so they are persisted in the ledger before the helper exits non-zero.

Do not manually mark `CODE_REVIEW` or `PM_REVIEW` with `stage` unless the corresponding review artifacts above already exist and pass `artifact-verdict`. `PASS_WITH_CAVEAT` is not an acceptable review-gate verdict; caveats must be fixed when they are in scope, required for verification, or introduced by this diff. Only true out-of-scope caveats may be logged under an accepted verdict, and they must include evidence plus a tracking destination.

## Stage 9: Commit, Push, PR

Only after all prior stages pass:

```bash
python3 "$HOME/.config/opencode/scripts/linear_build_orchestrator.py" guard --ledger "${LEDGER_PATH}" --next-stage PR_READY
python3 "$HOME/.config/opencode/scripts/linear_build_orchestrator.py" stage --ledger "${LEDGER_PATH}" --stage PR_READY --verdict PR_READY --note "All pre-PR gates passed."
```

1. Inspect `git status --short`, `git diff --stat`, and `git diff --name-only`.
2. Commit only scoped changes.
3. Push the workspace branch.
4. Create a PR to `BASE_REF`'s target branch.
5. Link the PR to Linear with `ltui issues link` and move the issue to the appropriate review state.

Record PR creation mechanically:

```bash
python3 "$HOME/.config/opencode/scripts/linear_build_orchestrator.py" stage \
  --ledger "${LEDGER_PATH}" \
  --stage PR_CREATED \
  --verdict PR_CREATED \
  --artifact "${PR_URL}" \
  --note "PR created and linked to Linear ${ISSUE_KEY}."
```

Do not pause here for commit, push, or PR permission. This command invocation is the permission. If a generic agent/git safety instruction says not to commit or push unless explicitly requested, treat this command as that explicit request for this workspace branch only. Never amend, force-push, or merge unless separately requested.

The PR body must include:

- OpenCode workspace id
- run ledger path
- plan path
- validation commands/results
- code review verdict
- PM review verdict
- manual evidence status
- documented out-of-scope follow-ups with evidence and tracking destination
- residual risks

## Stage 10: PR Feedback Monitor Loop

After PR creation, enter the PR feedback monitor loop. This is part of the build, not optional follow-up. The loop exits only when GitHub has no remaining P1/P2 feedback by the helper's artifact criteria.

Loop protocol:

1. Fetch all PR feedback channels: top-level issue comments, PR review summaries, inline review comments, and GraphQL review threads.
2. Treat these as blocking P1/P2 feedback when they contain `P0`, `P1`, `P2`, `critical`, `blocker`, `major`, or `must fix` and are either unresolved, non-outdated review threads or top-level PR feedback without a durable resolution artifact.
3. For each blocking item, inspect the linked code and full comment context, implement the scoped fix, run impacted validation, commit, and push.
4. For remediated review threads, reply with the fix/validation evidence and mark the GitHub thread resolved when permissions allow. If the thread cannot be resolved mechanically, rerun the checker and stop only if the artifact still reports `PR_FEEDBACK_REQUIRED` with evidence of the unresolved thread.
5. For remediated top-level comments or review summaries, write a durable resolution artifact before rerunning the checker:

```text
PR_FEEDBACK_RESOLUTION
Resolved-Feedback: issue_comment:<id>
Resolved-Feedback: review:<id>
Fix-Commit: <commit sha included in the current PR head>
Validation-Evidence: <validation command/result proving the fix>
Resolution-Evidence: <commit SHA, validation command/result, and short explanation of the fix>
```

Save it as `thoughts/reviews/pr-feedback-resolution-${FEEDBACK_RUN_ID}.md`. Do not mark a top-level P1/P2 item resolved without a real fix, validation evidence, and pushed commit.

6. After pushed remediation changes and any required resolution artifact, rerun the PR feedback check. Keep looping until the artifact first line is `PR_FEEDBACK_CLEAR`.
7. The ledger helper enforces a three-cycle limit for non-passing `CODE_REVIEW`, `PM_REVIEW`, and `PR_FEEDBACK` artifacts. If it records `BLOCKED_REVIEW_CONVERGENCE`, stop and report the unresolved items and artifacts.
8. If feedback is ambiguous, resolve it from the code, tests, PR thread, plan, and issue first. Ask the operator only for a true product/security decision that cannot be answered from available evidence.

Run the checker with a unique durable artifact path:

```bash
FEEDBACK_RUN_ID="${ISSUE_KEY}-$(date -u +%Y%m%dT%H%M%SZ)"
FEEDBACK_CHECK_STATUS=0
python3 "$HOME/.config/opencode/scripts/linear_build_pr_feedback.py" \
  --ledger "${LEDGER_PATH}" \
  --output "thoughts/reviews/pr-feedback-${FEEDBACK_RUN_ID}.md" || FEEDBACK_CHECK_STATUS=$?
```

Then record the artifact verdict. `PR_FEEDBACK_REQUIRED` is intentionally accepted so the ledger captures the feedback before remediation continues; it is not acceptable as the final state.

```bash
FEEDBACK_VERDICT_STATUS=0
python3 "$HOME/.config/opencode/scripts/linear_build_orchestrator.py" artifact-verdict \
  --ledger "${LEDGER_PATH}" \
  --stage PR_FEEDBACK \
  --artifact "thoughts/reviews/pr-feedback-${FEEDBACK_RUN_ID}.md" \
  --expect PR_FEEDBACK_CLEAR \
  --expect PR_FEEDBACK_REQUIRED || FEEDBACK_VERDICT_STATUS=$?
```

If `FEEDBACK_CHECK_STATUS` or `FEEDBACK_VERDICT_STATUS` is non-zero because the verdict is `PR_FEEDBACK_REQUIRED`, read the artifact's `## Remaining P1/P2 Feedback` section, fix every listed in-scope item, run targeted validation plus any plan-required impacted gates, commit, push, and repeat this stage from the checker invocation. Do not mark `COMPLETE` while the latest PR feedback artifact is required.

If PR feedback remediation changes product code after `CODE_REVIEW` and `PM_REVIEW`, rerun the Stage 8 Codex code review, Claude code review, and PM review artifacts before attempting completion. The `COMPLETE` guard recomputes the current implementation revision and rejects stale review artifacts.

When the latest artifact records `PR_FEEDBACK_CLEAR`, complete the run:

```bash
python3 "$HOME/.config/opencode/scripts/linear_build_orchestrator.py" guard --ledger "${LEDGER_PATH}" --next-stage COMPLETE
python3 "$HOME/.config/opencode/scripts/linear_build_orchestrator.py" stage --ledger "${LEDGER_PATH}" --stage COMPLETE --verdict COMPLETE --note "No remaining P1/P2 PR feedback."
```

## Final Output

Report:

- issue key and URL
- OpenCode workspace id and directory
- branch
- run ledger path
- plan path
- PR URL if created
- final verdict
- latest PR feedback artifact and verdict
- any blockers or manual checks still required
