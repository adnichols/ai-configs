---
name: run-plan
description: Execute an existing implementation plan persistently through code changes, bounded scoped quality reviews, the Codex plus applicable Claude Code pre-PR implementation review, fixes or dispositions for blocking findings, verification, commit, push, PR creation, and PR monitoring until feedback is addressed and the PR is mergeable without expanding beyond the plan's stated scope.
---

# Run Plan

Use this skill when the user has a plan file and wants it implemented all the way to a pull request with the runtime's scoped quality-review gates and the Codex plus applicable Claude Code pre-PR review gate, while preventing reviewer-driven scope creep.

The plan is the contract. Reviews can reveal adjacent problems, but they do not expand the contract unless the user explicitly approves that expansion.

The Codex/Claude pre-PR gate is not a terminal phase. Once implementation is complete, verification is passing, and reviewer consensus says there are no unresolved blocking in-scope P1/P2 findings, the next mandatory action is to commit, push, and open the PR in this same scoped run. A "ready for PR" closeout without a PR URL is incomplete unless a concrete blocker prevented PR creation.

This skill is runtime-state-backed. A scoped plan run is not complete at PR creation; it remains active until the PR satisfies the post-PR completion criteria. In Pi, back this with the todo tool plus explicit working notes/handoff state. In Codex, back this with Codex goal/task state and the installed Codex prompts so the monitoring obligation survives normal turn-to-turn execution.

## Invocation

```text
Use $run-plan to execute an explicit plan path or a slug resolvable by repo-local active plan guidance
```

Accept either a plan path or a slug. For a slug, resolve using repo-local active plan guidance; do not infer a markdown path.

## Non-Negotiable Rules

- Do not implement if the request is plan-only, review-only, or investigation-only.
- Do not run destructive git commands unless the user explicitly requested them.
- Do not fix adjacent issues just because a reviewer found them.
- Do not let reviewer subagents edit files during review. Reviews are read-only.
- Do not ask reviewers to review the whole product for open-ended problems.
- Do not proceed past a blocked plan decision by silently choosing a larger scope.
- Do not silently defer work that is required by the plan, required for verification, or introduced by this branch; fix it before merge or stop with a blocker.
- Do not create a PR until verification appropriate to the touched surfaces has run or a blocker is clearly reported.
- Do not create a PR until an implementation-stage PM review has checked the implemented outcome against the plan's product intent, or a concrete blocker prevents that review.
- Do not create a PR until the Codex plus applicable Claude Code pre-PR implementation review gate has passed with no unresolved blocking in-scope P1/P2 findings, the Claude Code leg is truthfully recorded as skipped for a low-risk/docs-only scope, or the user explicitly waives that gate.
- Do not stop after the Codex/Claude pre-PR gate passes; that gate returns `OPEN_PR_READY`, and the scoped run must continue through final verification, commit, push, PR creation, and monitoring.
- Do not create a PR until base freshness and mergeability risk have been checked against the target branch; fetch, rebase safely, and rerun invalidated verification/reviews before PR creation when the branch is stale.
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
- a required runtime-native review gate is unavailable and the user has not waived it. This means Codex review infrastructure, `claude-code-review` when the high-risk second-reviewer trigger or explicit override applies, and the `pre-pr-implementation-review` skill.

## Scope Classification

Every requested change and every reviewer finding must be classified before implementation:

- `IN_PLAN`: directly required by the plan's acceptance criteria, phase work, or verification.
- `PLAN_PREREQUISITE`: not named in the plan, but the plan cannot work or verify without it.
- `REGRESSION_FROM_THIS_DIFF`: caused by the current implementation and must be fixed before PR.
- `OUT_OF_SCOPE_FOLLOW_UP`: real issue, but not required for this plan, not required to make verification truthful, and not introduced by this branch.
- `QUESTION`: requires user/product decision before implementation.

Only implement `IN_PLAN`, `PLAN_PREREQUISITE`, and `REGRESSION_FROM_THIS_DIFF`. Treat BDD gaps, verification gaps, implicit-only coverage, misleading evidence, or any finding tied to a plan acceptance criterion as in-scope until proven otherwise.

Use this acceptance test for any non-obvious finding:

1. Which exact plan line, acceptance criterion, or verification command requires this?
2. Would the planned feature be incorrect or unverifiable if this remained unchanged?
3. Was the issue introduced by this branch?

If the answer to all three is no, it may be left out of this PR only after it is documented as an `OUT_OF_SCOPE_FOLLOW_UP` with evidence, owner/destination, and a durable record in the PR body plus the plan deviation log or repo discovery ledger. If any answer is yes, fix it now; do not label it deferred.

Two refinements override a naive "not introduced by this branch" reading of question 3:

- If this diff creates, extends, or routes new inputs to a shared primitive (collector, rewriter, mapper, scanner, serializer, validator), that primitive's correctness across every input this diff can now feed it is in scope even if the primitive predates the branch.
- A fail-closed/bail/reject path reachable by valid, schema-conformant input is in scope when this diff can route valid input to it; "it fails closed" is not a reason to defer. Deferral on fail-closed grounds is valid only when the closed path is reachable solely by invalid input.

A finding may be deferred as `OUT_OF_SCOPE_FOLLOW_UP` only when you can cite an existing test — or add one — proving the deferred input class is handled or genuinely unreachable. A "fail-closed" or "pre-existing" deferral without that evidence is not valid.

## Workflow

### 1. Establish Run State

1. Check whether a run-plan task/goal state is already active.
2. If no compatible run state is active, create an explicit lifecycle task set before implementation. In Pi, use the todo tool and keep exactly one active item at a time. In Codex, use Codex goal/task state. Include a final post-PR monitoring item that cannot be marked done until all completion criteria are satisfied.
3. The objective must require both:
   - executing the specified plan through implementation, verification, runtime-native scoped review, the Codex plus applicable Claude Code pre-PR review with no unresolved blocking in-scope P1/P2 findings, commit, push, and PR creation;
   - monitoring the PR after creation until the post-PR completion criteria are satisfied.
4. If an active run state already exists and it is compatible with this scoped plan run, continue under it and state the compatibility in working notes.
5. If an active run state exists but conflicts with this scoped plan run, stop and ask the user whether to finish, block, or abandon the existing run before creating a new one.

Use this objective shape:

```text
Execute <plan path> through scoped implementation, verification, runtime-native scoped quality reviews, the Codex plus applicable Claude Code pre-PR implementation review with no unresolved blocking in-scope P1/P2 findings, commit, push, PR creation, and persistent post-PR monitoring. Do not stop at `OPEN_PR_READY`; open the PR unless a concrete blocker prevents it. Do not mark complete until all PR feedback has been addressed and repeatedly rechecked and the PR is mergeable with <target branch>. Do not stop or mark blocked merely because review feedback takes a long time to arrive.
```

Runtime state expectation: keep the task/goal state and working notes current with the plan path, PR URL once known, target branch, latest verification status, latest reviewer-pair state, feedback state, and mergeability. In Pi this state lives in todo/working notes; in Codex it lives in Codex goal/task state. Do not clear or complete the run state until the same completion criteria are satisfied.

#### Registered Doct plan status alignment

For a reviewed HTML/Markdoc plan, align Doct plan state before code edits. Resolve the Doct document/plan ID, workspace ID, canonical Doct URL, and current version from registration output, the explicit Doct review URL, or `doct-agent plans show --id <document-id> --json`; if the plan is not registered and repo guidance expects reviewed plans, register it through `doct-document-ops` with `doct-agent plans register --base-url https://doct.nodaste.com --source-format <html|markdoc>` before proceeding.

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

Run the Codex review leg. In Codex, use a Codex subagent/native review task when available; otherwise use `codex-review-partner` in `implementation-review` mode. In Pi, run Codex as a subprocess through the installed `codex-review-partner` wrapper. Use a bounded prompt that names the plan path, comparison range, changed files, scope contract, and verdict format. Do not let any reviewer edit files.

The review prompt must include:

- the plan path,
- the base branch or comparison range,
- the changed files,
- the scope contract,
- instructions to classify every finding using `IN_PLAN`, `PLAN_PREREQUISITE`, `REGRESSION_FROM_THIS_DIFF`, `OUT_OF_SCOPE_FOLLOW_UP`, or `QUESTION`,
- instructions not to propose unrelated improvements.

Required verdict format:

```text
VERDICT: PASS_SCOPED
VERDICT: PASS_WITH_DOCUMENTED_OUT_OF_SCOPE_FOLLOW_UPS
VERDICT: FIX_IN_SCOPE_FINDINGS
VERDICT: BLOCKED_BY_SCOPE_QUESTION
VERDICT: REVIEW_INCOMPLETE_RERUN_NEEDED
```

Reject malformed reviews and rerun once with a tighter prompt. `PASS_WITH_DOCUMENTED_OUT_OF_SCOPE_FOLLOW_UPS` is valid only when every remaining finding is classified `OUT_OF_SCOPE_FOLLOW_UP` and includes evidence plus a tracking destination; otherwise treat the review as `FIX_IN_SCOPE_FINDINGS` or `BLOCKED_BY_SCOPE_QUESTION` by substance.

### 6. Applicable Claude Code scoped review

Before launching Claude Code, classify the review scope using the high-risk second-reviewer policy. Use Claude Code when the diff touches data loss risk, auth/security, concurrency/locking, migrations/persistence, release-risk, release-blocking CI behavior, or another explicit P1/P2 risk surface. Skip Claude Code by default for docs-only, low-risk UI copy, low-risk tests, and narrow follow-ups unless the operator provides an explicit override reason; record the skip in the review ledger.

When this shared workflow is surfaced through Pi reviewer profiles instead of the Codex/Claude Code gate, preserve the current applicable GLM routing: use `glm5.2-high` for normal high-risk bounded review, reserve `glm5.2-xhigh` for final or exceptional-risk review, and treat `quality-reviewer-glm` as a legacy xhigh compatibility alias only. For low-risk/docs-only/UI-copy/tests/narrow follow-ups, record the GLM skipped classification rather than inventing a GLM verdict.

When the Claude Code leg applies, use `claude-code-review` through its canonical private-tmux interactive launcher, pinned to Opus 4.7 on Extra High. Do not use Pi `quality-reviewer`, GLM reviewer profiles, GPT subagents, Kimi, OMP, OpenCode, or other model-subagent substitutes for this review. If a required Claude Code review is unavailable, stop with a clear blocker instead of claiming the scoped run is reviewed.

The second reviewer must receive a bounded review packet, not an open-ended whole-product prompt. The packet must include the plan path, base branch or comparison range, changed files, scope contract, self scope audit, latest verification results, touched surfaces, and the specific failure families to inspect. It must not edit files. It must return findings in chat, classified with the same scope categories.

For every reviewer, use bounded scope and bounded exploration. Give each reviewer a concrete review packet: plan scope, changed files, diff summary, verification results, named touched surfaces, and the specific failure families to check. Tool outputs should be narrow: prefer exact file reads with offsets/limits and `rg -n` on changed files over repo-wide dumps. Do not use parent-side `max_turns` as the primary bounding mechanism for reviewer completion; hard turn caps can truncate the final verdict and produce unusable output. Bound the assigned scope instead.

If any reviewer cannot complete the assigned scope, it must return `REVIEW_INCOMPLETE_RERUN_NEEDED` with completed checks, remaining checks, and the recommended follow-up slice.

Split a normal review only when a diff has more than 20 changed files, more than 2000 diff lines, or clearly independent product surfaces that one bounded slice cannot review. Use at most two slices per reviewer in the initial cycle. Do not split a small or medium diff merely to get more opinions, and do not create generic failure-family slices unless the diff actually touches those failure families.

Empty output, tool-only output, provider errors, or transcripts ending in tool use are review infrastructure failures, not passes. Rerun once with a narrower bounded prompt; do not fix empty reviewer output by adding or lowering parent-side turn limits. If the narrowed rerun is still unusable, stop with a review-infrastructure blocker unless the user explicitly waives the gate.

If either reviewer reports broad adjacent risks, keep them out of the PR only when they satisfy the `OUT_OF_SCOPE_FOLLOW_UP` definition and are documented. If the risk maps to the plan, verification, or this diff, treat it as in-scope and fix it.

### 7. Triage Reviews Before Fixing

Create a short triage table in your working notes:

```text
Finding | Source | Classification | Decision | Evidence
```

For each scoped reviewer finding:

- Fix `IN_PLAN`, `PLAN_PREREQUISITE`, and `REGRESSION_FROM_THIS_DIFF`.
- Record `OUT_OF_SCOPE_FOLLOW_UP` without fixing it only after documenting why it is outside this plan, where it will be tracked, and a cited test proving the deferred input class is handled or unreachable. Without that test evidence, treat it as in scope.
- Stop and ask the user for `QUESTION`.

Do not implement fixes directly from reviewer prose. Convert them through this triage step first.

### 8. Repeat Review Loop

After fixing in-scope findings:

1. Rerun targeted tests for touched code.
2. Rerun the first scoped quality review with the previous findings and current diff.
3. Rerun the second scoped quality review with the same bounded scope.
4. If any reviewer returns `REVIEW_INCOMPLETE_RERUN_NEEDED`, run at most one narrowed follow-up slice for that cycle and append the result to a coverage ledger. If that follow-up is still incomplete or unusable, stop with a review-budget blocker or ask the user to waive/narrow the gate.
5. Repeat until Codex and any applicable Claude Code reviewer return `PASS_SCOPED` or `PASS_WITH_DOCUMENTED_OUT_OF_SCOPE_FOLLOW_UPS` and the coverage ledger shows no incomplete required slices within the review budget.

The coverage ledger must record completed slices, the single allowed incomplete rerun slice, and final synthesized gate status.

Stop and report a convergence blocker if:

- the same finding or same failure family recurs after two fix attempts,
- a narrow/optional component keeps producing new edge-case findings after two cycles and should be reverted, deferred, or redesigned instead of patched through review,
- reviewers disagree on scope and the plan does not resolve it,
- a needed fix would clearly expand the plan,
- three total review cycles have run since the first scoped review.

### 9. Implementation-Stage PM Review

After phase implementation and the runtime-native scoped quality-review loop have no unresolved blocking in-scope findings, run an implementation-stage PM review before the pre-PR implementation gate and before PR creation.

Use the local PM review surface when available:

```text
/dev:pm-review <plan path> implementation
```

If the exact prompt template is unavailable in the current runtime, perform the equivalent PM check yourself and record that substitution in the review ledger. The PM review must be product-outcome focused, not a general code review:

- compare the implemented behavior, docs, tests, and verification evidence against the plan goal, acceptance criteria, BDD scenarios, locked decisions, and non-goals;
- identify plan-required outcome gaps, misleading completion evidence, missing phase work, or required plan corrections;
- classify every issue with the normal run-plan scope labels before acting.

For PM review results:

1. Fix `IN_PLAN`, `PLAN_PREREQUISITE`, and `REGRESSION_FROM_THIS_DIFF` PM findings before continuing.
2. If the PM review reshapes the plan, update the source plan with the correction, push the update to Doct for reviewed HTML/Markdoc plans, execute the added plan-required work, and rerun verification or scoped reviews invalidated by the change.
3. Stop for user input on `QUESTION` findings that require a product or scope decision.
4. Record true `OUT_OF_SCOPE_FOLLOW_UP` findings only with evidence and a tracking destination; do not let PM review broaden the PR beyond the plan contract.

The PM gate is clean only when the implemented outcome satisfies the plan by substance, all in-scope PM findings have been fixed or blocked by a real decision, and any plan/Doct progress updates are synchronized. Record the PM verdict, artifact or notes location, plan-update status, and any rerun requirements for the PR body.

### 10. Codex/Claude Pre-PR Review Gate

After phase implementation and the runtime-native scoped quality-review loop has no unresolved blocking in-scope findings, satisfy the Codex and applicable Claude Code pre-PR gate before final PR preparation.

Do not run redundant full reviewer gates over an unchanged diff. If the latest runtime-native scoped Codex and applicable Claude Code reviews already ran after the last code change, used the current base/comparison range, covered the current changed files, and have no unresolved blocking in-scope P1/P2 findings, record that evidence as the pre-PR gate result and continue. If Claude Code is skipped because the current PR is docs-only, low-risk UI copy, low-risk tests, or a narrow follow-up, record the low-risk classification and any override decision. Run `$pre-pr-implementation-review <plan path>` only when current reviewer evidence is missing, stale, incomplete, or materially narrower than the PR diff.

When the standalone pre-PR gate is required, it must use:

- Codex for the primary review leg. In Codex, use a Codex subagent/native review task when available; in Pi, run Codex as a subprocess through the installed `codex-review-partner` wrapper.
- Claude Code via `claude-code-review` when the high-risk second-reviewer trigger or an explicit override applies, pinned to Opus 4.7 on Extra High.

For Pi-only GPT/GLM pre-PR surfaces that wrap this same lifecycle, the equivalent route is GPT plus applicable GLM using `glm5.2-high` for normal high-risk bounded review and `glm5.2-xhigh` for final or exceptional-risk review. Preserve truthful low-risk GLM skip records and do not route new work through the legacy `quality-reviewer-glm` alias except for compatibility with older independent GLM gates.

In Codex, satisfy this gate directly rather than delegating back to Pi. Run the Codex leg as a subagent/native review task when available and run the applicable Claude Code leg through the canonical launcher. If a subprocess Codex leg is needed, use:

```bash
~/.agents/skills/codex-review-partner/scripts/run-review.sh \
  --mode implementation-review \
  --input /tmp/pre-pr-codex-review.md \
  --cwd /path/to/repo \
  --output thoughts/validation/pre-pr-reviews/<date-branch>-codex.md
```

When running from Pi, use the same wrapper to run Codex as a subprocess; do not use a Pi GPT subagent for the Codex leg. Run Claude Code only when applicable:

```bash
python3 "$HOME/.agents/skills/claude-code-review/scripts/claude_interactive_review.py" \
  --cwd /path/to/repo \
  --prompt-file /tmp/pre-pr-claude-review.md \
  --output thoughts/validation/pre-pr-reviews/<date-branch>-claude.md \
  --review-name claude-pre-pr-review \
  --timeout-seconds 3600
```

The coordinating agent must consume the Codex and Claude Code review artifacts/verdicts, triage findings under this run-plan scope contract, apply only in-scope fixes itself or through the active implementation flow, and rerun the same applicable reviewer set after material fixes. If Codex or a required Claude Code reviewer is unavailable, stop with a review-infrastructure blocker unless the user explicitly waives the Codex/Claude gate.

Pass the plan path, base/comparison range, changed files, scope contract, and latest verification results. The reviewers must classify findings by P1/P2/P3 severity and by the normal scope categories.

Treat every in-scope P1/P2 finding as blocking a clean ready-for-PR conclusion. Triage findings before editing, fix only `IN_PLAN`, `PLAN_PREREQUISITE`, and `REGRESSION_FROM_THIS_DIFF` blocking P1/P2 issues, rerun targeted verification, and rerun all applicable reviewers within the bounded pre-PR review budget until they return no unresolved blocking in-scope P1/P2 findings. P3 findings block only when they are plan-required, verification-required, regression-caused, or cheap and safe enough to fix immediately; otherwise document them as non-blocking follow-ups with evidence and a tracking destination.

If the gate applies fixes after final verification has already run, rerun final verification before commit/PR. If Codex review infrastructure or a required Claude Code Opus 4.7 xhigh review is unavailable, stop unless the user explicitly waives this pre-PR gate.

When the gate reports `OPEN_PR_READY` or equivalent clean consensus, continue immediately to final verification, commit, push, and PR creation. Do not return a final run-plan response at this point.

Record the Codex verdict, Claude Code verdict or skip record, artifact path, waived/not-run status, and any documented non-blocking follow-ups for the PR body.

## Final Verification

Run the plan's final verification commands after the Codex/Claude pre-PR review gate is clean for all blocking in-scope P1/P2 findings, or after the applicable Claude Code leg is truthfully skipped under the low-risk policy. If the plan does not specify enough verification, run the smallest repo-appropriate gate for the changed surfaces and report the gap as a plan defect.

Do not hide failures. Fix failures when they are in scope, required for truthful verification, or caused by this branch. Otherwise, report them as pre-existing or documented out-of-scope follow-ups with evidence and tracking destination.

## Base Freshness and Mergeability Gate

Before push and PR creation, verify the branch is fresh enough against the target branch that the PR will not immediately open stale or obviously unmergeable. Run the first freshness check before committing when possible, but do not rebase a dirty worktree by default.

1. Resolve the target branch from the plan, existing PR metadata, or repo default integration branch.
2. Fetch the target branch.
3. Check whether the current branch is behind, diverged, or likely conflicted with the fetched target branch.
4. If the branch is behind or diverged while scoped edits are still uncommitted, commit the scoped changes after final verification, then rebase the committed branch onto the fetched target branch before pushing. Use autostash only when repo policy explicitly permits it, and record exactly what was stashed, reapplied, and reverified.
5. If the branch is behind or diverged after commit, rebase onto the fetched target branch when conflicts are absent or limited to scoped files and can be resolved without a product decision.
6. If conflicts affect out-of-scope files, require unclear product decisions, or cannot be resolved without destructive git operations, stop with a base freshness blocker.
7. After any rebase, autostash replay, or conflict resolution, rerun the verification invalidated by the changed diff context.
8. Rerun scoped quality reviews, PM review, or the Codex/Claude pre-PR gate when the rebase materially changes the PR diff, touched files, acceptance evidence, or reviewer assumptions.

Record the target branch, fetch result, rebase/skip decision, rerun verification, and any stale-review reruns in the PR body. A clean `OPEN_PR_READY` review verdict is not enough by itself if the branch became stale before PR creation.

## Commit, Push, and PR

When implementation, scoped reviews, implementation-stage PM review, the applicable Codex/Claude pre-PR review gate status, final verification, and base freshness pass or are ready to complete immediately after the scoped commit, PR creation is mandatory in the same run:

1. Review `git diff --stat` and `git diff --name-only`.
2. Commit only the scoped changes.
3. If the freshness check found the target branch stale before commit, rebase the committed branch now, rerun invalidated verification/reviews, and stop on unsafe conflicts.
4. Push the branch.
5. Open a PR to the plan's target branch, or the repo's normal integration branch.

Do not end with "ready to open a PR." If `gh` authentication, branch protection, missing remote, or another concrete issue prevents PR creation, report that exact blocker and leave the run state active; otherwise produce a PR URL.

The PR body must include:

- plan path,
- in-scope summary,
- verification commands and results,
- first scoped quality-review verdict,
- second scoped quality-review verdict,
- implementation-stage PM review verdict and any plan/Doct updates,
- Codex/Claude pre-PR review verdicts and artifact path, or explicit waived/not-run status,
- Pi GPT/GLM pre-PR verdicts when that surface is used, including the applicable GLM verdict or truthful GLM skipped classification,
- base freshness and mergeability/rebase status before PR creation,
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
- The branch has been rebased or otherwise updated against the destination branch as needed, with affected verification rerun after the update.
- GitHub reports the PR as mergeable with the destination branch.

### Monitoring Loop

Repeat this loop until the completion criteria are met or a true blocker is reached. Slow or absent reviewer feedback and pending checks are not true blockers by themselves; they require continued polling.

1. Inspect PR reviews, review threads, comments, status checks, review decision, and mergeability on every poll.
2. Classify every new feedback item using the same scope categories.
3. If any actionable feedback arrives after the local scoped review gates already passed, mark the cycle as a `REVIEW_ESCAPE` in working notes. Fixing only the mentioned line is insufficient.
4. Fix `IN_PLAN`, `PLAN_PREREQUISITE`, and `REGRESSION_FROM_THIS_DIFF` feedback.
5. Record or report `OUT_OF_SCOPE_FOLLOW_UP` feedback with evidence and tracking destination without expanding the PR.
6. Stop for user input on `QUESTION` feedback.
7. For each `REVIEW_ESCAPE`, run the adversarial escalation loop below before considering the feedback addressed.
8. Rerun the smallest meaningful verification for any changes.
9. Commit and push fixes to the PR branch.
10. Rebase onto the destination branch when GitHub reports the branch out of date, stale, conflicted, blocked by base freshness, or not mergeable, but only when conflicts are absent or limited to scoped files and do not require a product decision.
11. After any post-PR rebase or conflict resolution, rerun affected verification, rerun scoped reviews when the PR diff changed materially, and push with lease.
12. Stop with a scope question when rebase conflicts affect out-of-scope files, require unclear product decisions, or cannot be resolved without destructive git operations.
13. Recheck until GitHub shows the PR as mergeable and no new actionable feedback remains.
14. If a poll finds no new feedback but checks or mergeability are still pending, report the latest PR state briefly, keep the run state active, wait, and poll again. Do not end the scoped-plan run or mark the run state blocked for review latency alone.

### Adversarial Escalation Loop

A `REVIEW_ESCAPE` means the previous review prompt was not thorough enough for this PR state. After applying the direct fix, broaden the next local review cycle within the plan's scope:

1. Write down the missed-defect pattern: reviewer, feedback URL, affected file/line, why earlier review missed it, and the failure family it represents.
2. Audit the PR diff for sibling instances: same assumption, same edge case, same API contract, same missing validation, same lifecycle/state transition, analogous callsites, and tests that should have failed but did not.
3. Run read-only adversarial implementation reviews with Codex and, when the high-risk second-reviewer trigger or explicit override applies, Claude Code. In Codex, run the Codex leg as a subagent/native review task when available; in Pi, run Codex as a subprocess through `codex-review-partner`. Run Claude Code through `claude-code-review` on Opus 4.7 xhigh when applicable. If the escaped issue is a low-risk docs/UI/test-only follow-up, record why Claude Code remains skipped or provide the explicit override reason. Review the current PR diff, the plan scope contract, the direct PR feedback, and the sibling-audit notes. Ask reviewers to actively look for additional missed issues in the same failure family and nearby plan-bound surfaces, not to re-approve the one fix. For every reviewer, use one bounded adversarial slice focused on the escaped failure family; use a second slice only when the escaped issue spans clearly separate surfaces. Each reviewer slice must return a verdict or `REVIEW_INCOMPLETE_RERUN_NEEDED`; the parent records completed slices, the single allowed incomplete rerun slice, and final synthesized gate status in the coverage ledger.
4. Triage new adversarial findings using the normal scope classifications. Fix in-scope findings, document true out-of-scope follow-ups, and stop for questions.
5. Repeat the adversarial reviewer-pair pass once after fixes if it finds any in-scope issue. Return to the normal monitoring loop only after both adversarial passes report no additional in-scope findings or only documented out-of-scope follow-ups.

Keep this escalation scope-bound: it should search harder around the PR's implementation, assumptions, and failure modes, not turn into an unrelated whole-product audit.

### Polling Persistence

When the run has reached post-PR monitoring, the agent must persist across session turns:

- Keep polling the PR until actionable feedback is resolved, required checks have settled, and the PR is mergeable.
- Poll every 60 seconds while waiting for PR feedback, checks, or mergeability unless the user explicitly asks to reduce polling frequency.
- Continue monitoring even after current feedback is addressed, because late feedback can still arrive before mergeability/checks settle.
- Do not treat "no new feedback", "review still pending", or "checks still running" as completion, failure, or a blocker.
- In Pi, leave the monitoring todo active and summarize the latest PR URL, mergeability, feedback state, and reviewer-pair state in any handoff or final-in-turn status.
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
3. Resolve only conflicts in scoped files, and only when no product decision is needed.
4. Stop with a scope question when conflicts affect out-of-scope files, require unclear product decisions, or cannot be resolved without destructive git operations.
5. Rerun verification affected by the rebase.
6. Rerun scoped reviews when the PR diff changed materially.
7. Push with lease.

Do not use destructive git commands to force mergeability. If conflicts require decisions outside the plan, stop with a scope question.

### Run State Closure

Only after the completion criteria are all satisfied, mark the runtime monitoring task/goal complete. In Pi, complete the monitoring todo; in Codex, complete the Codex goal/task state. Do not mark the run state blocked for a slow reviewer, no new feedback, pending review, or pending checks; those are polling wait states. Mark the run state blocked only for a real actionable blocker that prevents meaningful polling or scoped fixes, and report the exact blocker with the latest PR state.

## Reviewer Prompt Template

Use this shape for Codex and any applicable Claude Code reviewer. When the reviewer is Claude Code, include the exact risk question and bounded high-risk packet that caused the high-risk second-reviewer trigger to apply; do not rely on the generic prompt alone.

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

Do not recommend unrelated cleanup, hardening, new features, or broad product audits.
For an adjacent problem, first decide its severity and whether this diff can reach it, then classify. A problem this diff can trigger — including through a primitive it extends, or a fail-closed path reachable by valid input — is in scope even if the affected code predates the branch. Only problems genuinely unreachable from this diff go under OUT_OF_SCOPE_FOLLOW_UP, with the reason, a tracking destination, and a cited test showing the input is handled or unreachable.
Do not put IN_PLAN, PLAN_PREREQUISITE, REGRESSION_FROM_THIS_DIFF, QUESTION, BDD gaps, verification gaps, implicit-only coverage, or plan-required work in a deferred/out-of-scope section.

Return one verdict:
- VERDICT: PASS_SCOPED
- VERDICT: PASS_WITH_DOCUMENTED_OUT_OF_SCOPE_FOLLOW_UPS
- VERDICT: FIX_IN_SCOPE_FINDINGS
- VERDICT: BLOCKED_BY_SCOPE_QUESTION

This additional verdict is allowed for every reviewer when the assigned scope cannot be completed:
- VERDICT: REVIEW_INCOMPLETE_RERUN_NEEDED

For every reviewer slice, use bounded scope and bounded exploration. Do not use parent-side `max_turns` as the primary bounding mechanism for reviewer completion; hard turn caps can truncate the final verdict and produce unusable output. Reserve enough time/context for a final response, and do not broaden into unrelated whole-product review. If incomplete, return `REVIEW_INCOMPLETE_RERUN_NEEDED` with completed checks, remaining checks, and the exact single follow-up slice the parent should run next.

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
Actionable PR feedback arrived after our local reviewer-pair gates had passed. Treat that as evidence the prior review was not thorough enough.

Escaped feedback:
- Reviewer/comment URL: <url>
- Direct issue: <summary>
- Direct fix: <summary or commit>
- Suspected failure family: <edge case / contract / callsite / validation / state / security / data-loss / test-gap pattern>

Do not merely verify the direct fix. Search the current PR diff for additional missed issues in the same failure family and nearby plan-bound surfaces:
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
- implementation-stage PM review verdict,
- Codex/Claude pre-PR review verdicts or waived/not-run status,
- Pi GPT/GLM pre-PR verdicts when that surface is used, including applicable GLM verdict or truthful GLM skipped classification,
- base freshness and rebase status,
- PR feedback monitoring result,
- PR mergeability result,
- documented out-of-scope follow-ups with evidence and tracking destination,
- any residual risk.

Keep the closeout concise and evidence-based.
