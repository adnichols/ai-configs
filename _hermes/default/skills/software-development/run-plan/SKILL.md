---
name: run-plan
description: Execute an existing implementation plan persistently through code changes, bounded scoped quality reviews, the GPT plus applicable Claude Code pre-PR implementation review, fixes or dispositions for blocking findings, verification, commit, push, PR creation, and PR monitoring until feedback is addressed and the PR is mergeable without expanding beyond the plan's stated scope.
---

# Run Plan

Use this skill when the user has a plan file and wants it implemented all the way to a pull request with the runtime's scoped quality-review gates and the GPT plus applicable Claude Code pre-PR review gate, while preventing reviewer-driven scope creep.

The plan is the contract. Reviews can reveal adjacent problems, but they do not expand the contract unless the user explicitly approves that expansion.

The GPT/Claude Code pre-PR gate is not a terminal phase. Once implementation is complete, verification is passing, and reviewer consensus says there are no unresolved blocking in-scope P1/P2 findings, the next mandatory action is to commit, push, and open the PR in this same scoped run. A "ready for PR" closeout without a PR URL is incomplete unless a concrete blocker prevented PR creation.

This skill is runtime-state-backed. A scoped plan run is not complete at PR creation; it remains active until the PR satisfies the post-PR completion criteria. In Pi, back this with the todo tool plus explicit working notes/handoff state. In Codex, back this with Codex goal/task state and the installed Codex prompts so the monitoring obligation survives normal turn-to-turn execution.

## Invocation

```text
Use $run-plan to execute an explicit plan path or a slug resolvable by repo-local active plan guidance
```

Accept either a plan path or a slug. For a slug, resolve using repo-local active plan guidance; do not infer a markdown path.

## Non-Negotiable Rules

- Do not implement if the request is plan-only, review-only, or investigation-only.
- Do not run destructive git commands unless the user explicitly requested them.
- Do not let reviewer subagents edit files during review. Reviews are read-only.
- Do not ask reviewers to review the whole product for open-ended problems.
- Do not proceed past a blocked plan decision by silently choosing a larger scope.
- Complete the promised slice before merge: no required stubs, TODO behavior, dead-end surfaces, missing producer/consumer wiring, fake success, or verification that bypasses the real implementation.
- If the promised outcome cannot be completed safely, stop and resize it to a smaller independently useful complete slice rather than shipping a partial skeleton.
- Do not create a PR until verification appropriate to the touched surfaces has run or a blocker is clearly reported.
- Do not create a PR until the GPT plus applicable Claude Code pre-PR implementation review gate has passed with no unresolved blocking in-scope P1/P2 findings, the Claude Code leg is truthfully skipped under the low-risk policy, or the user explicitly waives that gate.
- Do not stop after the GPT/Claude Code pre-PR gate passes; that gate returns `OPEN_PR_READY`, and the scoped run must continue through final verification, commit, push, PR creation, and monitoring.
- Do not mark the active run state complete just because the implementation PR exists.
- Do not mark the active run state complete until PR feedback has been monitored and addressed and the PR is mergeable with the destination branch.
- Treat actionable PR feedback after local reviews as a review escape: the earlier review cycle missed something, so the next local review cycle must become scope-bound adversarial review instead of only patching the commented issue.
- Do not mark the active run state blocked or stop monitoring merely because PR feedback is slow to arrive. Treat slow review response as a wait state that requires continued polling, not as a blocker.

## Scope Contract

Before editing, read the full plan and extract:

- Goal and user-visible outcome
- Explicit in-scope files, surfaces, phases, and acceptance criteria
- Explicit out-of-scope items
- Required tests and verification commands
- Base branch and PR target, if stated
- Open questions, unresolved decisions, or readiness status

Stop before implementation if:

- the plan is not execution-ready,
- acceptance criteria are vague enough that scope cannot be enforced,
- required user decisions remain unresolved,
- the current branch contains unrelated dirty changes that make isolation unsafe,
- a required runtime-native review gate is unavailable and the user has not waived it. This means `quality-reviewer`, `claude-code-review` when the high-risk second-reviewer policy applies, and the `autoreview` skill.

## Scope Classification

Scope follows the canonical Scope doctrine: understanding and protecting existing behavior around your change is the cost of the change, while making something new happen needs its own plan and, when product-changing, owner approval. The disposition rule decides each finding:

> **A regression this change causes is in scope wherever it appears. When this change routes new valid inputs into a shared primitive or expands its reachable domain, correctness across that newly reachable domain is part of this change even where defects predate it. A defect this change merely discovers — and does not cause or newly expose — is a finding: capture it and keep going.**

Classify every requested change and every reviewer finding:

- `IN_PLAN`: directly required by the plan's acceptance criteria, phase work, or verification.
- `PLAN_PREREQUISITE`: not named in the plan, but the plan cannot work or verify without it.
- `REGRESSION_FROM_THIS_DIFF`: caused or newly exposed by the current implementation, including correctness across a domain this change newly makes reachable; fix it before PR.
- `OUT_OF_SCOPE_FOLLOW_UP`: a defect this change merely discovers and does not cause or newly expose; capture it as a finding with its tracking destination and keep going.
- `QUESTION`: requires user/product decision before implementation.

Fix `IN_PLAN`, `PLAN_PREREQUISITE`, and `REGRESSION_FROM_THIS_DIFF`. Treat BDD gaps, verification gaps, implicit-only coverage, misleading evidence, or any finding tied to a plan acceptance criterion as in-scope until proven otherwise.

## Evidence Placement

Evidence lives in the coverage ledger (working notes), the plan file's progress and deviation sections, and ultimately the PR body. Do not create repository commits whose sole content is recording verification, certification, review, or deferral status; fold plan-progress updates into at most one bookkeeping commit per completed phase. Never commit a "debt" record for an in-scope failure — fix it or report the blocker. A run's commit history should read as the change, not as a diary of the process that produced it.

## Verification Convergence Budget

Full-suite verification and certification gates get a convergence budget. Track attempts per delivery head: gate name, attempt number, failure signature, and whether the root cause is new or a repeat. A repeated full-gate attempt is justified only by a new distinct root cause; rerunning to "get a clean one" is not one. Three attempts at the same gate without a new distinct root cause, or 90 minutes of attributable gate time, whichever comes first, exhausts the budget (repo-local guidance may override; record the gate's normal green-run duration).

At exhaustion, classify each residual failure with evidence: **introduced** (caused or newly exposed by this branch — a domain this change newly makes reachable counts as introduced) vs. **inherited** (reproduced at the merge-base or target branch, not inferred from age), and **functional** vs. **infra/cosmetic** (an unexplained delta with no approved tolerance is a `QUESTION`, not cosmetic). A full-run failure whose failing tests pass in isolation/serial while the failure point moves between attempts is infrastructure-flake evidence: certify on the serial evidence and disclose the parallel-run state.

Disposition: all residuals inherited or infra/cosmetic with targeted verification green → open the PR as a draft with the classification disclosed and stop on the ship/keep-fixing question (the unattended terminal state); any introduced or functional residual is in scope — fix it or stop with a blocker naming it. An operator ship or stop directive ends this budget immediately: discard queued and in-flight gate attempts, open the PR in the state the operator named, and disclose the truthful gate state.

## Workflow

### 1. Establish Run State

1. Check whether a run-plan task/goal state is already active.
2. If no compatible run state is active, create an explicit lifecycle task set before implementation. In Pi, use the todo tool and keep exactly one active item at a time. In Codex, use Codex goal/task state. Include a final post-PR monitoring item that cannot be marked done until all completion criteria are satisfied.
3. The objective must require both:
   - executing the specified plan through implementation, verification, runtime-native scoped review, the GPT plus applicable Claude Code pre-PR review with no unresolved blocking in-scope P1/P2 findings, commit, push, and PR creation;
   - monitoring the PR after creation until the post-PR completion criteria are satisfied.
4. If an active run state already exists and it is compatible with this scoped plan run, continue under it and state the compatibility in working notes.
5. If an active run state exists but conflicts with this scoped plan run, stop and ask the user whether to finish, block, or abandon the existing run before creating a new one.

Use this objective shape:

```text
Execute <plan path> through scoped implementation, verification, runtime-native scoped quality reviews, the GPT plus applicable Claude Code pre-PR implementation review with no unresolved blocking in-scope P1/P2 findings, commit, push, PR creation, and persistent post-PR monitoring. Do not stop at `OPEN_PR_READY`; open the PR unless a concrete blocker prevents it. Do not mark complete until all PR feedback has been addressed and repeatedly rechecked and the PR is mergeable with <target branch>. Do not stop or mark blocked merely because review feedback takes a long time to arrive.
```

Runtime state expectation: keep the task/goal state and working notes current with the plan path, PR URL once known, target branch, latest verification status, latest applicable-reviewer state, feedback state, and mergeability. In Pi this state lives in todo/working notes; in Codex it lives in Codex goal/task state. Do not clear or complete the run state until the same completion criteria are satisfied.

#### Registered Doct plan status alignment

For a reviewed HTML/Markdoc plan, align Doct plan state before code edits. Resolve the Doct document/plan ID, workspace ID, canonical Doct URL, and current version from registration output, the explicit Doct review URL, or `doct-agent plans show --id <document-id> --json`; if the plan is not registered and repo guidance expects reviewed HTML/Markdoc plans, register it through `doct-document-ops` with `doct-agent plans register --base-url https://doct.nodaste.com --source-format <html|markdoc>` before proceeding.

Before implementation starts:

1. Run `doct-agent plans lifecycle --base-url https://doct.nodaste.com --document-id <document-id> --workspace-id <workspace-id> --state active --json` when the plan is not already active.
2. Run `doct-agent plans board list --base-url https://doct.nodaste.com --workspace-id <workspace-id> --json` and inspect the available board columns.
3. If a visible `in_progress` column exists, run `doct-agent plans board set --base-url https://doct.nodaste.com --document-id <document-id> --workspace-id <workspace-id> --column in_progress --json`.
4. If `in_progress` is absent, hidden, or ambiguous, stop with an actionable status-sync blocker unless repo/service configuration explicitly identifies an equivalent in-progress column.

Do not treat a disk progress checkbox update as sufficient reviewer-state alignment. After each completed phase, update the source plan `Progress`, push the updated HTML through `doct-agent plans update` or verify an active `doct-agent plans watch`, and inspect Doct evidence (`plans show`, board/list output, or returned update metadata) before advancing.

### 2. Prepare

1. Read repo instructions and the plan file.
2. Check git status and current branch.
3. Identify the base branch from the plan, or use the repo's normal integration branch.
4. Create or confirm a task branch if needed.
5. Read repo-local execution policy from `AGENTS.md` and any referenced local guidance before editing.
6. If repo guidance requires a Linear issue before execution, identify the issue key from plan metadata/text, branch name, or explicit user input; verify it with `ltui --format detail issues view <KEY>`; stop before code edits if the issue is required but missing or unverifiable.
7. Record the scope contract in your working notes before editing.

If the worktree is dirty, preserve unrelated changes. Do not clean them up for convenience.

### 3. Implement Phase by Phase

For each unfinished phase:

1. Write or update only the tests required by the phase.
2. Implement the smallest product change that satisfies the phase.
3. Run the phase's targeted verification.
4. Update the source plan progress only when that phase is actually complete.
5. Verify Doct reflects that source progress through `doct-agent plans update`, an active `doct-agent plans watch`, or `doct-agent plans show`/board evidence before advancing.
6. Record only documented out-of-scope discoveries in the plan's deviation log or the repo's discovery ledger. In-scope findings are not discoveries to defer; fix them before advancing.

If a phase exposes a broader product problem, classify it. Fix it only if it is a plan prerequisite or a regression from this diff.

### 4. Self Scope Audit

Before reviewer subagent review, inspect the diff against the plan:

```bash
git diff --stat
git diff --name-only
```

For every changed file, answer: why does this file need to change for this plan?

If a changed file has no plan-bound reason, revert only your own edits to that file or split the work into a separate follow-up branch. Never revert user changes.

### 5. First scoped quality review

In Pi, use the Pi subagent `quality-reviewer` for a read-only GPT-5.6 Sol high implementation review. In Codex, use the installed Codex-native `quality-reviewer`/implementation-review mechanism for the first read-only scoped review. Do not let any reviewer edit files.

The review prompt must include:

- the plan path,
- the base branch or comparison range,
- the changed files,
- the scope contract,
- instructions to classify every finding using `IN_PLAN`, `PLAN_PREREQUISITE`, `REGRESSION_FROM_THIS_DIFF`, `OUT_OF_SCOPE_FOLLOW_UP`, or `QUESTION`,
- instructions to apply the disposition rule and capture adjacent problems as findings rather than expanding the change.

Required verdict format:

```text
VERDICT: PASS
VERDICT: FINDINGS_TO_RESOLVE
VERDICT: BLOCKED_BY_QUESTION
VERDICT: REVIEW_INCOMPLETE_RERUN_NEEDED
```

A `PASS` verdict must carry a `Not examined:` line disclosing what the review did not exercise (`Not examined: none` when the full surface was covered). Reject malformed reviews and rerun once with a tighter prompt. Legacy green verdicts (`PASS_SCOPED`, `PASS_WITH_DOCUMENTED_OUT_OF_SCOPE_FOLLOW_UPS`) are still accepted as green when read; treat a review as `FINDINGS_TO_RESOLVE` or `BLOCKED_BY_QUESTION` by substance when unresolved in-scope findings or a product question remain.

### 6. Applicable Claude Code scoped review

Use Claude Code when the diff touches data loss risk, auth/security, concurrency/locking, migrations/persistence, release-risk, release-blocking CI behavior, or another explicit P1/P2 risk surface. Skip Claude Code by default for docs-only, low-risk UI copy, low-risk tests, and narrow follow-ups unless the operator provides an explicit override reason; record the skip in the review ledger.

When Claude Code applies, use `claude-code-review`; the canonical launcher owns model, effort, and private-tmux mechanics. The reviewer must receive a bounded review packet, not an open-ended whole-product prompt. The packet must include the plan path, base branch or comparison range, changed files, scope contract, self scope audit, latest verification results, touched surfaces, and the specific failure families to inspect. It must not edit files. It must return findings in chat, classified with the same scope categories.

Use bounded scope and bounded exploration. If the reviewer cannot complete the assigned scope, it must return `REVIEW_INCOMPLETE_RERUN_NEEDED` with completed checks, remaining checks, and the recommended follow-up slice. Split review only when a diff has more than 20 changed files, more than 2000 diff lines, or clearly independent product surfaces that one bounded slice cannot review. Use at most two slices in the initial cycle.

Empty output, tool-only output, provider errors, or transcripts ending in tool use are review infrastructure failures, not passes. Rerun once with a narrower bounded prompt; if the narrowed rerun is still unusable, stop with a review-infrastructure blocker unless the user explicitly waives the gate.

If either reviewer reports broad adjacent risks, keep them out of the PR only when they satisfy the `OUT_OF_SCOPE_FOLLOW_UP` definition and are documented. If the risk maps to the plan, verification, or this diff, treat it as in-scope and fix it.

### 7. Triage Reviews Before Fixing

Create a short triage table in your working notes:

```text
Finding | Source | Classification | Decision | Evidence
```

For each scoped reviewer finding:

- Fix `IN_PLAN`, `PLAN_PREREQUISITE`, and `REGRESSION_FROM_THIS_DIFF`.
- Record `OUT_OF_SCOPE_FOLLOW_UP` without fixing it after documenting why it is outside this plan and where it will be tracked. Do not create code or tests solely to dispose of speculative future risks, unsupported paths, unrelated architecture work, or polish.
- Stop and ask the user for `QUESTION`.

Do not implement fixes directly from reviewer prose. Convert them through this triage step first.

### 8. Targeted Rereview

After fixing in-scope findings:

1. Rerun targeted tests for touched code.
2. Rerun the first scoped quality review with the previous findings and current diff.
3. Rerun the applicable Claude Code scoped review with the same bounded scope, or preserve the recorded low-risk skip when it still applies.
4. If any reviewer returns `REVIEW_INCOMPLETE_RERUN_NEEDED`, run at most one narrowed follow-up slice for that cycle and append the result to a coverage ledger. If that follow-up is still incomplete or unusable, stop with a review-budget blocker or ask the user to waive/narrow the gate.
5. Stop after this targeted rereview when GPT and any applicable Claude Code reviewer return `PASS` (or a legacy green verdict), or report the remaining convergence/scope blocker. Run a third total review cycle only when the targeted rereview identifies a new concrete blocker introduced or exposed by the fix.

The coverage ledger must record completed slices, the single allowed incomplete rerun slice, and final synthesized gate status.

The ordinary local review budget is exhausted when:

- the same finding or same failure family recurs after two fix attempts,
- a narrow/optional component keeps producing new edge-case findings after two cycles and should be reverted, deferred, or redesigned instead of patched through review,
- reviewers disagree on scope and the plan does not resolve it,
- a needed fix would clearly expand the plan,
- three total review cycles have run since the first scoped review; the third cycle is permitted only for a new concrete blocker introduced or exposed by the prior fix.

Do not report the convergence blocker yet solely because no PR exists. Mark review non-convergence, a recurring failure family, or unresolved scope disagreement as a pre-PR `REVIEW_ESCAPE`, then run the single bounded external consultation and, only if authorized, the bounded adversarial applicable-reviewer-pair pass defined below. This route applies to a fixed candidate branch/diff before or after PR creation and does not require a PR URL or PR feedback.

### 9. GPT/Claude Code Pre-PR Review Gate

After phase implementation and the runtime-native scoped quality-review loop has no unresolved blocking in-scope findings, satisfy the GPT plus applicable Claude Code pre-PR gate before final PR preparation.

Do not run redundant full reviewer gates over an unchanged diff. If the latest runtime-native scoped GPT and applicable Claude Code reviews already ran after the last code change, used the current base/comparison range, covered the current changed files, and have no unresolved blocking in-scope P1/P2 findings, record that evidence as the pre-PR gate result and continue. If Claude Code was skipped under the low-risk policy, record the classification and any override decision. Run `$autoreview <plan path>` only when current reviewer evidence is missing, stale, incomplete, or materially narrower than the PR diff. Follow the canonical autoreview policy, including its pre-review scope baseline, concrete blocker evidence, smallest-fix ownership boundary, behavioral-verification separation, dependency evidence, known-blocker overflow, and release freeze discipline; do not duplicate or weaken those rules here.

When the standalone pre-PR gate is required, it must use:

- GPT-5.6 Sol high via Pi's `quality-reviewer` subagent or the runtime's equivalent primary review mechanism,
- Claude Code via `claude-code-review` when the high-risk second-reviewer trigger or an explicit override applies.

Pass the plan path, base/comparison range, changed files, scope contract, and latest verification results. The reviewers must classify findings by P1/P2/P3 severity and by the normal scope categories.

Treat every in-scope P1/P2 finding as blocking a clean ready-for-PR conclusion. Triage findings before editing, fix only `IN_PLAN`, `PLAN_PREREQUISITE`, and `REGRESSION_FROM_THIS_DIFF` blocking P1/P2 issues, rerun targeted verification, and run one targeted rereview limited to the findings and resulting edits. A third total review cycle is allowed only for a new concrete blocker introduced or exposed by the fix; otherwise return clean consensus or a convergence/scope blocker. P3 findings block only when they are plan-required, verification-required, or regression-caused; otherwise document them as non-blocking follow-ups with evidence and a tracking destination.

If the gate applies fixes after final verification has already run, rerun final verification before commit/PR. If GPT review infrastructure or a required Claude Code review is unavailable, stop unless the user explicitly waives this pre-PR gate.

When the gate reports `OPEN_PR_READY` or equivalent clean consensus, continue immediately to final verification, commit, push, and PR creation. Do not return a final run-plan response at this point.

Record the GPT verdict, Claude Code verdict or low-risk skip, artifact path, waived/not-run status, and any documented non-blocking follow-ups for the PR body.

## Final Verification

Run the plan's final verification commands after the GPT/Claude Code pre-PR review gate is clean for all blocking in-scope P1/P2 findings, or after the Claude Code leg is truthfully skipped under the low-risk policy. If the plan does not specify enough verification, run the smallest repo-appropriate gate for the changed surfaces and report the gap as a plan defect. Full-gate reruns are governed by the Verification Convergence Budget; a failure with an already-classified root cause never by itself requires another full run.

Do not hide failures. Fix failures when they are in scope, required for truthful verification, or caused by this branch. Otherwise, report them as pre-existing or documented out-of-scope follow-ups with evidence and tracking destination.

## Commit, Push, and PR

When implementation, scoped reviews, the applicable GPT/Claude Code pre-PR review gate status, and final verification pass, PR creation is mandatory in the same run:

1. Review `git diff --stat` and `git diff --name-only`.
2. Commit only the scoped changes.
3. Push the branch.
4. Open a PR to the plan's target branch, or the repo's normal integration branch.

Do not end with "ready to open a PR." If `gh` authentication, branch protection, missing remote, or another concrete issue prevents PR creation, report that exact blocker and leave the run state active; otherwise produce a PR URL.

The PR body must include:

- plan path,
- in-scope summary,
- verification commands and results,
- first scoped quality-review verdict,
- applicable Claude Code scoped-review verdict or recorded low-risk skip,
- GPT/Claude Code pre-PR review verdicts and artifact path, or explicit waived/not-run status,
- documented out-of-scope follow-ups with evidence and tracking destination,
- known residual risks.

Do not include memory citations in PR messages.

## Post-PR Completion Loop

After the PR is open, keep the active runtime task/goal state active and monitor the PR until all completion criteria are satisfied. In Pi this is the active todo/run state; in Codex this is the active Codex goal/task state.

### Completion Criteria

The run state can be marked complete only when all of these are true:

- All actionable PR feedback has been addressed.
- PR feedback has been checked repeatedly after fixes, not just once immediately after PR creation.
- If PR feedback required code changes, both runtime-native scoped quality reviews have rerun over the current PR diff and cleared any in-scope findings.
- The branch has been rebased or otherwise updated against the destination branch as needed.
- GitHub reports the PR as mergeable with the destination branch.

### Monitoring Loop

Repeat this loop until the completion criteria are met or a true blocker is reached. Slow or absent reviewer feedback and pending checks are not true blockers by themselves; they require continued polling.

1. Inspect PR reviews, review threads, comments, status checks, and mergeability.
2. Classify every new feedback item using the same scope categories.
3. If any actionable feedback arrives after the local scoped review gates already passed, mark the cycle as a `REVIEW_ESCAPE` in working notes. Fixing only the mentioned line is insufficient.
4. Fix `IN_PLAN`, `PLAN_PREREQUISITE`, and `REGRESSION_FROM_THIS_DIFF` feedback.
5. Record or report `OUT_OF_SCOPE_FOLLOW_UP` feedback with evidence and tracking destination without expanding the PR.
6. Stop for user input on `QUESTION` feedback.
7. For each `REVIEW_ESCAPE`, use an ordinary adversarial/targeted cycle when one remains and the normal third-cycle condition is satisfied. When the ordinary three-cycle budget is exhausted, route the stable `REVIEW_ESCAPE` failure-family/scope identifier through the one-per-family consultation section before reporting convergence; only that consultation's explicit authorization permits its single bounded adversarial pass and existing one pass-after-fixes allowance. No fourth or renamed pass is allowed except that consultation-authorized bounded exception, and PR existence is never authorization for an extra pass.
8. Rerun the smallest meaningful verification for any changes.
9. Commit and push fixes to the PR branch.
10. Rebase onto the destination branch when GitHub reports the branch out of date, conflicted, or not mergeable.
11. Recheck until GitHub shows the PR as mergeable and no new actionable feedback remains.
12. If a poll finds no new feedback but checks or mergeability are still pending, report the latest PR state briefly, keep the run state active, wait, and poll again. Do not end the scoped-plan run or mark the run state blocked for review latency alone.

### Review Escape Consultation and Adversarial Escalation Loop

A `REVIEW_ESCAPE` means either (a) bounded local review did not converge on a candidate branch/diff, including before PR creation, or (b) actionable PR feedback proved the previous review prompt was not thorough enough. A PR URL or PR feedback is not required for this route.

Before a convergence blocker is returned, assign a stable consultation identifier to the distinct escaped failure family and affected scope on the fixed artifact, comparison range, and complete fingerprint. Run exactly one bounded, read-only, independent external consultation for that identifier through the harness's configured consult/council surface, and record the identifier, packet, and final disposition. Never repeat consultation for the same unresolved family/scope identifier or use new wording to restart its budget. A materially separate later failure-family/scope identifier may receive its own one consultation whether discovered pre-PR, during an authorized adversarial pass, or from later PR feedback. The consultation is advisory only: it may not edit, apply fixes, become implementation authority, or route implementation through another persona. Its packet must name the identifier and unresolved finding/failure family or scope disagreement; the fixed artifact, comparison range, and complete fingerprint; prior fix attempts and reviewer disagreement; verification evidence; and one narrow arbitration question. It may recommend only: reject/reclassify with evidence; authorize one further bounded adversarial fix/review pass within the accepted plan; revert/narrow/defer; or a user/product/scope decision.

The coordinator verifies the consultation evidence and consumes its disposition exactly once. Verified rejection or reclassification clears that escaped finding/failure family and allows the run to continue without an adversarial pass; record the evidence and resulting scope/severity classification. Revert, narrow, or defer follows the stated path under the normal scope rules. A user/product/scope-decision disposition stops for that decision. Only an explicit authorization starts the bounded adversarial pass. If disposition evidence cannot be verified or its stated path cannot be completed within current authority, report that specific unresolved blocker; do not convert every non-authorization into a convergence blocker.

If and only if the consultation authorizes the further adversarial pass, run it before or after PR creation as follows:

1. Write down the escaped-defect pattern: reviewer, affected file/line, why earlier review missed or disputed it, and the failure family it represents. Include a feedback URL only when PR feedback is the trigger.
2. Audit the fixed candidate branch/diff for sibling instances: same assumption, same edge case, same API contract, same missing validation, same lifecycle/state transition, analogous callsites, and tests that should have failed but did not.
3. Run read-only adversarial implementation reviews with GPT and, when the high-risk second-reviewer trigger or an explicit override applies, Claude Code. Review the current candidate branch/diff, the plan scope contract, the consultation disposition, any direct PR feedback when present, and the sibling-audit notes. Ask reviewers to actively look for additional missed issues in the same failure family and nearby plan-bound surfaces, not to re-approve one fix. Use one bounded adversarial slice focused on the escaped failure family; use a second slice only when the escaped issue spans clearly separate surfaces. Each reviewer slice must return a verdict or `REVIEW_INCOMPLETE_RERUN_NEEDED`; the parent records completed slices, the single allowed incomplete rerun slice, and final synthesized gate status in the coverage ledger.
4. Triage new adversarial findings using the normal scope classifications. The driving agent may make one bounded fix attempt for in-scope findings; document true out-of-scope follow-ups and stop for questions.
5. Repeat the same adversarial applicable-reviewer pass once after those fixes if it found any in-scope issue. Then return to the normal workflow only if the pass is clean; otherwise return control with the convergence blocker or requested decision.

Keep this escalation scope-bound: one consultation per distinct failure-family/scope identifier and, only when authorized, one bounded adversarial applicable-reviewer pass with the existing single pass-after-fixes allowance are the limit. Do not repeat consultation for an unresolved identifier, restart the ordinary three-cycle budget, review until clean, or turn the escalation into an unrelated whole-product audit.

### Polling Persistence

When the run has reached post-PR monitoring, the agent must persist across session turns:

- Keep polling the PR until actionable feedback is resolved, required checks have settled, and the PR is mergeable.
- Poll every 60 seconds while waiting for PR feedback, checks, or mergeability unless the user explicitly asks to reduce polling frequency.
- Continue monitoring even after current feedback is addressed, because late feedback can still arrive before mergeability/checks settle.
- Do not treat "no new feedback", "review still pending", or "checks still running" as completion, failure, or a blocker.
- In Pi, leave the monitoring todo active and summarize the latest PR URL, mergeability, feedback state, and applicable-reviewer state in any handoff or final-in-turn status.
- A true blocker must be something the agent cannot resolve by continued polling or scoped fixes, such as lost GitHub authentication, a closed/deleted PR, a force-push/base-branch conflict requiring a product decision, or `QUESTION` feedback that needs the user.
- If a true blocker is reached, report the exact blocker and the latest PR state. Otherwise, keep the active run state open and continue polling.

Use GitHub product surfaces for this check:

- PR issue comments via `gh pr view ... --json comments` and/or `GET /repos/<owner>/<repo>/issues/<pr>/comments`.
- PR reviews via `gh pr view ... --json reviews`.
- Inline review comments via `GET /repos/<owner>/<repo>/pulls/<pr>/comments`.
- Status/mergeability via `gh pr view ... --json mergeable,mergeStateStatus,statusCheckRollup,reviewDecision`.

Reference implementation for Pi: write this to `/tmp/monitor-pr-<pr>.sh`, start it with the `process` tool, and set `logWatches` for `FEEDBACK_CHANGED`. It polls every 60 seconds, stores snapshots, and reports comment/review/status changes.

```bash
#!/usr/bin/env bash
set -euo pipefail

repo="${1:?owner/repo required}"
pr="${2:?pr number required}"
interval_seconds="${PR_MONITOR_INTERVAL_SECONDS:-60}"
state_dir="${PR_MONITOR_STATE_DIR:-/tmp/pr-monitor-${repo//\//-}-${pr}}"
mkdir -p "$state_dir"

fetch_state() {
  gh pr view "$pr" --repo "$repo" \
    --json url,number,state,baseRefName,headRefName,headRefOid,mergeable,mergeStateStatus,reviewDecision,statusCheckRollup,comments,reviews \
    > "$state_dir/pr.json"
  gh api --paginate --slurp "repos/$repo/issues/$pr/comments" | jq 'add' > "$state_dir/issue-comments.json"
  gh api --paginate --slurp "repos/$repo/pulls/$pr/comments" | jq 'add' > "$state_dir/review-comments.json"
}

snapshot_feedback() {
  jq -S '{
    pr: {
      state, mergeable, mergeStateStatus, reviewDecision,
      checks: [.statusCheckRollup[]? | {name, status, conclusion}],
      reviews: [.reviews[]? | {id, author:.author.login, state, submittedAt, body}]
    },
    prComments: [.comments[]? | {id, author:.author.login, createdAt, updatedAt, body}],
    issueComments: input | [.[]? | {id, author:.user.login, createdAt:.created_at, updatedAt:.updated_at, body}],
    reviewComments: input | [.[]? | {id, author:.user.login, path, position, createdAt:.created_at, updatedAt:.updated_at, body}]
  }' "$state_dir/pr.json" "$state_dir/issue-comments.json" "$state_dir/review-comments.json" > "$state_dir/feedback.current.json"
}

while true; do
  ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  if ! fetch_state; then
    echo "$ts MONITOR_ERROR failed to fetch PR state; retrying in ${interval_seconds}s"
    sleep "$interval_seconds"
    continue
  fi
  snapshot_feedback

  if [ -f "$state_dir/feedback.previous.json" ] && ! cmp -s "$state_dir/feedback.previous.json" "$state_dir/feedback.current.json"; then
    echo "$ts FEEDBACK_CHANGED snapshot=$state_dir/feedback.current.json"
  fi

  merge=$(jq -r '(.mergeable // "UNKNOWN") + "/" + (.mergeStateStatus // "UNKNOWN")' "$state_dir/pr.json")
  comments=$(jq 'length' "$state_dir/issue-comments.json")
  review_comments=$(jq 'length' "$state_dir/review-comments.json")
  reviews=$(jq '.reviews | length' "$state_dir/pr.json")
  echo "$ts PR_MONITOR merge=$merge issue_comments=$comments review_comments=$review_comments reviews=$reviews"

  cp "$state_dir/feedback.current.json" "$state_dir/feedback.previous.json"
  sleep "$interval_seconds"
done
```

Start it like this from Pi, leaving it running in the background:

```text
process.start name="pr-<number>-monitor" command="bash /tmp/monitor-pr-<number>.sh <owner>/<repo> <number>" logWatches=[FEEDBACK_CHANGED]
```

### Rebase Guidance

When rebase is needed:

1. Fetch the destination branch.
2. Rebase the PR branch onto the destination branch.
3. Resolve only conflicts in scoped files or conflicts required to preserve this plan's implementation.
4. Rerun verification affected by the rebase only when the rebase changed the content of the diff against the merge-base (committed, staged, unstaged, or untracked content); a rebase that changes only commit SHAs invalidates neither verification nor accepted review evidence.
5. Push with lease.

Do not use destructive git commands to force mergeability. If conflicts require decisions outside the plan, stop with a scope question.

### Run State Closure

Only after the completion criteria are all satisfied, mark the runtime monitoring task/goal complete. In Pi, complete the monitoring todo; in Codex, complete the Codex goal/task state. Do not mark the run state blocked for a slow reviewer, no new feedback, pending review, or pending checks; those are polling wait states. Mark the run state blocked only for a real actionable blocker that prevents meaningful polling or scoped fixes, and report the exact blocker with the latest PR state.

## Reviewer Prompt Template

Use this shape for GPT and any applicable Claude Code reviewer. When the reviewer is Claude Code, include the exact risk question and bounded high-risk packet that caused the second-reviewer trigger to apply.

```text
Read-only implementation review. Do not edit files.

Plan: <plan path>
Base/comparison: <base branch or range>
Changed files:
<files>
Diff summary:
<what changed and why>
Latest verification results:
<commands and outcomes>
Touched surfaces:
<API/CLI/MCP/UI/data/tests/docs/etc.>
Assigned failure families:
<security/auth/privacy, data loss/persistence, contract parity, async/resource lifecycle, verification truthfulness, or other scoped slice>

Scope contract:
<goal, acceptance criteria, in-scope, out-of-scope, verification>

Review only whether this diff correctly implements the plan.
Treat the plan/scope, any author summary, and prior verification results as product intent and claims to verify — not proof of implementation correctness. Re-derive the key invariant from the code, schema, and types.

On this first pass (not only after an escape), also check:
- generic key-name matching/remapping/rewriting where the key name may not uniquely determine the value's type or target — construct non-target counterexamples (numbers, booleans, objects, unrelated strings) and confirm each is handled
- fail-closed/bail paths reachable by valid, schema-conformant input
- producer/consumer and round-trip parity (import vs export, encode vs decode, rewrite vs collect)
When you find one instance, enumerate its siblings (other call sites, other shapes, the inverse direction of the boundary) and report the family.

Classify every finding as exactly one of:
- IN_PLAN
- PLAN_PREREQUISITE
- REGRESSION_FROM_THIS_DIFF
- OUT_OF_SCOPE_FOLLOW_UP
- QUESTION

Stay within the assigned bounded scope rather than auditing the whole product; investigating and reporting adjacent problems you find is never out of bounds.
Apply the disposition rule: a regression this diff causes or newly exposes — including through a primitive it extends, a domain it newly makes reachable, or a fail-closed path reachable by valid input — is in scope even if the affected code predates the branch. A defect this diff merely discovers goes under `OUT_OF_SCOPE_FOLLOW_UP` with the reason and tracking destination.
Do not put IN_PLAN, PLAN_PREREQUISITE, REGRESSION_FROM_THIS_DIFF, QUESTION, BDD gaps, verification gaps, implicit-only coverage, or plan-required work in a deferred/out-of-scope section.

Return one verdict:
- VERDICT: PASS (with a `Not examined:` line)
- VERDICT: FINDINGS_TO_RESOLVE
- VERDICT: BLOCKED_BY_QUESTION

This additional verdict is allowed when the assigned scope cannot be completed:
- VERDICT: REVIEW_INCOMPLETE_RERUN_NEEDED

Use bounded scope and bounded exploration. Reserve enough time and context for a final response, and do not broaden into unrelated whole-product review. If incomplete, return `REVIEW_INCOMPLETE_RERUN_NEEDED` with completed checks, remaining checks, and the exact single follow-up slice the parent should run next.

Return format for reviewer slices:
1. Scope checked
2. Coverage table: file/surface, check performed, result, complete/incomplete
3. Findings, if any
4. Remaining checks and recommended follow-up slice, only when incomplete
5. Final verdict

For each finding include: file/line, classification, evidence, and why it is or is not required by the plan. Return at most five findings, prioritized by P1/P2 impact. For each OUT_OF_SCOPE_FOLLOW_UP or non-blocking P3, include the durable tracking destination that should receive it.
```

## Adversarial Reviewer Prompt Add-on

Append this when a `REVIEW_ESCAPE` occurred:

```text
Adversarial escalation context:
Trigger: <pre-PR bounded review non-convergence | actionable PR feedback after local applicable-reviewer gates passed>. Treat the consultation disposition and any direct fix as claims to verify, not proof.

Escaped finding/failure family or scope disagreement:
- Fixed artifact/comparison/fingerprint: <artifact, range, complete fingerprint>
- Reviewer/comment URL: <url only when PR feedback exists; otherwise none>
- Prior fix attempts and reviewer disagreement: <summary>
- Verification evidence: <commands/results>
- External consultation disposition: <reject/reclassify | authorize bounded adversarial pass | revert/narrow/defer | user/product/scope decision>
- Narrow arbitration question and answer: <question and advisory answer>
- Suspected failure family: <edge case / contract / callsite / validation / state / security / data-loss / test-gap pattern>

Do not merely re-approve one fix. Search the current candidate branch/diff for additional missed issues in the same failure family and nearby plan-bound surfaces:
- sibling callsites or analogous code paths
- repeated assumptions or partial fixes
- tests that should have caught the escaped issue but still would not
- boundary, lifecycle, concurrency, auth, migration, or data-loss variants relevant to this plan
- evidence that the fix closes the root cause rather than one symptom

Stay within the scope contract. Classify every finding with the normal scope labels and return the same verdict format.
```

## Final Response

Only give the run-plan final response after a PR exists or a concrete PR-creation blocker has been reported. If the run reached clean blocking P1/P2 review consensus and final verification passed, a final response without a PR URL is invalid.

Report:

- PR URL,
- run-state status (Pi todo or Codex goal/task),
- changed files at a high level,
- verification run,
- runtime-native scoped quality-review verdicts,
- GPT/Claude Code pre-PR review verdicts or waived/not-run status,
- PR feedback monitoring result,
- PR mergeability result,
- documented out-of-scope follow-ups with evidence and tracking destination,
- any residual risk.

Keep the closeout concise and evidence-based.
