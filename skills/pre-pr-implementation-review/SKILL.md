---
name: pre-pr-implementation-review
description: Run a bounded pre-PR implementation review with a Codex review leg and an applicable Claude Code Opus 4.7 xhigh review leg, fix or disposition blocking findings, and stop instead of entering non-converging review loops. Use this before opening pull requests, after an implementation is complete, inside run-plan, or whenever the user asks for Codex plus applicable Claude Code code review of a branch/diff; inside run-plan this gate hands back to PR creation rather than concluding the workflow.
---

# Pre-PR Implementation Review

Use this skill to catch implementation issues that would otherwise appear during pull request review. It is a code-review-and-fix loop, not a plan review, not a general cleanup pass, and not the end of `run-plan`.

The gate passes when Codex and any applicable Claude Code reviewer agree by substance that the current implementation has no unresolved in-scope P1/P2 findings. If Claude Code is skipped under the low-risk policy, the gate must record that skip instead of requiring a Claude Code verdict. P3 findings must be triaged, but they are not automatically PR-blocking: fix them only when they are plan-required, verification-required, regression-caused, or a small safe cleanup; otherwise document them as non-blocking follow-ups with evidence.

When invoked from `run-plan`, a passing result means `OPEN_PR_READY`, not `DONE`. It is only a handoff after the caller has satisfied run-plan's implementation-stage PM review; base freshness may still be pending until final verification and the scoped commit make a safe rebase possible. Return the final gate status, artifact path, target branch/base context, caller-reported base freshness status or pending status, and any known rebase-triggered rerun requirement to the `run-plan` caller so it can rerun final verification if needed, complete base freshness safely, commit, push, open the PR, and continue post-PR monitoring.

## Inputs

Accept any of:

```text
/skill:pre-pr-implementation-review
/skill:pre-pr-implementation-review <plan path>
/skill:pre-pr-implementation-review <base branch or comparison range>
/skill:pre-pr-implementation-review <plan path> --base <branch-or-range>
```

If invoked from `run-plan`, use that plan path, target branch/base branch, scope contract, changed files, latest verification results, PM review status, caller-reported base freshness status or pending status, and any known rebase-triggered rerun requirement.

If invoked independently, resolve the comparison in this order:

1. explicit `--base` or explicit comparison range from the user,
2. the plan's target/base branch,
3. an existing PR base for the current branch, when `gh pr view` can identify one,
4. the repo's normal integration branch (`origin/main`, `origin/master`, or `origin/develop`, preferring repo guidance when present).

Do not use the current branch's same-named upstream as the PR base; that usually points at the feature branch and can make the committed PR diff empty. If the base is ambiguous and materially affects the diff, ask one short clarification before reviewing.

## Severity and scope

Reviewers must use these severities:

- `P1`: PR-blocking production failure risk: security exposure, data loss, crash, broken core acceptance criterion, corrupt migration, dangerous concurrency/resource leak, or verification evidence that is materially false.
- `P2`: PR-blocking correctness/reliability risk: user-visible regression, missing required edge-case handling, important error-handling gap, significant performance issue, API/contract mismatch, or tests that would allow a materially incomplete implementation to pass.
- `P3`: lower-severity improvement, maintainability concern, or minor gap. P3 findings require an explicit disposition, but only block the gate when they are plan-required, verification-required, regression-caused, or cheap and safe enough to fix immediately.

Also classify every finding with the run-plan labels when a plan is present:

- `IN_PLAN`
- `PLAN_PREREQUISITE`
- `REGRESSION_FROM_THIS_DIFF`
- `OUT_OF_SCOPE_FOLLOW_UP`
- `QUESTION`

When no plan is present, treat issues introduced by the current diff as in scope. Do not fix unrelated pre-existing issues unless the user explicitly expands scope.

### What "out of scope" may not hide

A finding is in scope — regardless of whether the affected code predates this branch — when any of these hold:

- This diff creates, extends, or routes new inputs to a shared primitive (collector, rewriter, mapper, scanner, serializer, validator). That primitive's correctness across every input this diff can now feed it is in scope. "Not introduced by this branch" does not apply to a primitive whose reachable input domain this branch changed.
- The issue is a fail-closed/bail/reject path reachable by valid, schema-conformant input. Failing closed on valid input is an in-scope correctness/reliability regression, not a deferrable follow-up. "Fail-closed" justifies deferral only when the closed path is reachable solely by invalid input.

A finding may be classified `OUT_OF_SCOPE_FOLLOW_UP` only when you can cite an existing test — or add one — proving the deferred input class is actually handled or genuinely unreachable. A deferral whose justification is "fail-closed" or "pre-existing," without that evidence, is not valid; treat it as in scope.

## Review loop

### 1. Prepare the review packet

Capture:

```bash
git status --short --branch
# If you resolved a base branch/ref:
git diff --stat <base>...HEAD
git diff --name-only <base>...HEAD
# If the user supplied a full comparison range containing .. or ..., use it exactly:
git diff --stat <comparison-range>
git diff --name-only <comparison-range>
# Always include uncommitted working-tree changes separately:
git diff --stat
git diff --name-only
```

Distinguish a base ref from a full comparison range. Never append `...HEAD` to an argument that already contains `..` or `...`.

Also note staged changes with `git diff --cached --stat` when present. The implementation may be uncommitted; include committed, staged, and unstaged changes in the review scope.

Read the plan or user-provided scope if available. Extract the acceptance criteria, non-goals, required verification, and any intentionally deferred items so reviewers do not convert adjacent work into this PR.

### 2. Classify Claude Code need, then run reviewers

Before launching Claude Code, classify the review scope using the high-risk second-reviewer policy:

- **Use Claude Code** when the PR touches data loss risk, auth/security, concurrency/locking, migrations/persistence, release-risk, release-blocking CI behavior, or another explicit P1/P2 risk surface.
- **Skip Claude Code by default** for docs-only, low-risk UI copy, low-risk tests, and narrow follow-ups unless the operator provides an explicit override reason.
- Use a compact Claude Code packet with named files, the exact risk question, relevant diff excerpts, verification already run, and outcome limits. Do not send broad context when a packet is sufficient.

Some runtimes expose an explicit Pi GPT/GLM wrapper for this same lifecycle. That wrapper is an alternate Pi review surface, not a silent substitute for the Codex/Claude Code gate below. When that wrapper is the selected surface, preserve the current applicable GLM routing: use `glm5.2-high` for normal high-risk bounded review, reserve `glm5.2-xhigh` for final or exceptional-risk review, and keep `quality-reviewer-glm` as a legacy xhigh compatibility alias only. Low-risk/docs-only/UI-copy/tests/narrow follow-ups must record `GLM skipped` with the classification instead of inventing a GLM verdict. Report those results as Pi GPT/GLM verdicts, not Codex or Claude Code verdicts.

Launch applicable reviewers in the same turn when possible:

- **Codex** is the primary review leg. In Codex, run it as a Codex subagent/native review task when that facility is available; otherwise use `codex-review-partner` in `implementation-review` mode. In Pi, run Codex as a subprocess through the installed `codex-review-partner` wrapper.
- **Claude Code** is the high-risk second-reviewer leg when the high-risk trigger or an explicit override applies. Use `claude-code-review` and its canonical private-tmux interactive launcher, pinned to Opus 4.7 on Extra High.

Do not use Pi `quality-reviewer`, GLM reviewer profiles, GPT subagents, Kimi, OMP, OpenCode, or other model-subagent substitutes to satisfy the Codex/Claude Code gate described in this section. If the explicit Pi GPT/GLM wrapper is the selected surface, use the wrapper route above and label its output as Pi GPT/GLM evidence.

Both reviews are read-only. If Codex or a required Claude Code review is unavailable, report `REVIEW_INFRASTRUCTURE_FAILURE` unless the user explicitly waives the gate; do not silently substitute another model.

### Runtime launch rules

When this skill is invoked from Codex, run the Codex leg as a subagent/native review task when available, then run the applicable Claude Code leg through the canonical launcher. If a subprocess Codex leg is needed, use the same worktree and pass the resolved plan/scope and base/range:

```bash
~/.agents/skills/codex-review-partner/scripts/run-review.sh \
  --mode implementation-review \
  --input /tmp/pre-pr-codex-review.md \
  --cwd /path/to/repo \
  --output thoughts/validation/pre-pr-reviews/<date-branch>-codex.md
```

When this skill is invoked from Pi for the Codex/Claude Code route, run the Codex leg as a subprocess with that same wrapper; do not use a Pi GPT subagent for the Codex leg.

Run Claude Code only when applicable:

```bash
python3 "$HOME/.agents/skills/claude-code-review/scripts/claude_interactive_review.py" \
  --cwd /path/to/repo \
  --prompt-file /tmp/pre-pr-claude-review.md \
  --output thoughts/validation/pre-pr-reviews/<date-branch>-claude.md \
  --review-name claude-pre-pr-review \
  --timeout-seconds 3600
```

The coordinating agent consumes the Codex and Claude artifacts/verdicts, triages findings, applies in-scope fixes in the active worktree, and reruns the same applicable reviewer set after material fixes. If Codex or the required Claude Code reviewer is unavailable, report `REVIEW_INFRASTRUCTURE_FAILURE` unless the user explicitly waives the gate.

A reviewer result with no final verdict is not a review result. Treat empty output, tool-only output, provider errors, or a transcript ending in tool use as `REVIEW_INFRASTRUCTURE_FAILURE`, not `CLEAN_FOR_PR`. Rerun once with a narrower scoped prompt. Do not fix empty reviewer output by adding or lowering parent-side turn limits; hard turn caps can truncate the final verdict and produce another unusable result. If the narrowed rerun is still unusable, stop with a review-infrastructure blocker unless the user explicitly waives the gate.

For every quality reviewer, use bounded scope and bounded exploration. Give each reviewer a concrete review packet: plan scope, changed files, diff summary, verification results, named touched surfaces, and the specific failure families to check. Tool outputs should be narrow: prefer exact file reads with offsets/limits and `rg -n` on changed files over repo-wide dumps. Do not use parent-side `max_turns` as the primary bounding mechanism for reviewer completion; bound the assigned scope instead.

If any reviewer cannot complete the assigned scope, it must return `VERDICT: REVIEW_INCOMPLETE_RERUN_NEEDED` with completed checks, remaining checks, and the exact recommended follow-up slice. The parent may run at most one narrowed follow-up for that reviewer in that cycle. If that follow-up is still incomplete or unusable, stop with a review-budget blocker or ask the user to waive/narrow the gate; do not keep launching slices.

Split a review only when the diff has more than 20 changed files, more than 2000 diff lines, or clearly independent product surfaces that one bounded slice cannot review. Use at most two slices per reviewer in the initial cycle, chosen by concrete surface/risk. Do not split a small or medium diff merely to get more opinions, and do not create generic failure-family slices unless the diff actually touches those failure families.

Each reviewer slice must use the same severity, scope, budget, and verdict format. The parent synthesizes all slice results; do not ask one subagent to deeply inspect every slice and synthesize the whole PR.

Use this prompt shape for each reviewer:

```text
Read-only pre-PR implementation review. Do not edit files.

Reviewer: <Codex | Claude Code Opus 4.7 xhigh>
Plan/scope: <plan path or standalone scope summary>
Base/comparison: <base branch or range>
Changed files:
<changed files>
Diff summary:
<what changed and why>
Latest verification results:
<commands and outcomes>
Touched surfaces:
<API/CLI/MCP/UI/data/tests/docs/etc.>
Assigned failure families:
<security/auth/privacy, data loss/persistence, contract parity, async/resource lifecycle, verification truthfulness, or other scoped slice>

Review committed, staged, and unstaged changes in this worktree. Focus on issues a pull-request reviewer would reasonably ask to fix, justify, or track before merge.

Completion contract for every reviewer: stay within the assigned scope and review budget. Use at most the tool budget in the review instructions; do not broaden into unrelated whole-product review. Return a final verdict even when coverage is incomplete. If the assigned scope is incomplete, return `VERDICT: REVIEW_INCOMPLETE_RERUN_NEEDED` with completed checks, remaining checks, and the exact single follow-up slice the parent should run next.

Classify every finding with:
- Severity: P1, P2, or P3
- Scope: IN_PLAN, PLAN_PREREQUISITE, REGRESSION_FROM_THIS_DIFF, OUT_OF_SCOPE_FOLLOW_UP, or QUESTION

Every in-scope P1/P2 finding blocks a clean ready-for-PR verdict until it is fixed, rejected as a false positive with evidence, or reclassified as a true out-of-scope follow-up with evidence and a tracking destination. P3 findings block only when they are plan-required, verification-required, regression-caused, or cheap and safe enough to fix immediately; otherwise return them as non-blocking follow-ups.

Check especially:
- security, auth, data loss, and privacy risks
- crashes, data corruption, migration/compatibility failures
- async/concurrency/resource lifecycle bugs
- API contract, schema, CLI, MCP, UI, or test fixture drift
- missing error handling or misleading verification
- acceptance criteria that are only partially implemented
- generic key-name matching/remapping/rewriting where the key name may not uniquely determine the value's type or target (construct non-target counterexamples: numbers, booleans, objects, unrelated strings)
- fail-closed/bail paths reachable by valid, schema-conformant input
- producer/consumer and round-trip parity (import vs export, encode vs decode, rewrite vs collect)
- sibling instances of any discovered failure pattern, in this diff and the inverse direction of any boundary it touches — enumerate the family, not just the first instance

Return exactly one verdict:
- VERDICT: FINDINGS_TO_RESOLVE
- VERDICT: CLEAN_FOR_PR
- VERDICT: BLOCKED_BY_QUESTION
- VERDICT: REVIEW_INCOMPLETE_RERUN_NEEDED

Return format:
1. Scope checked
2. Coverage table: file/surface, check performed, result, complete/incomplete
3. Findings, if any
4. Remaining checks and recommended follow-up slice, only when incomplete
5. Final verdict

For every finding include: severity, scope classification, file/line, evidence, impact, recommended fix, and whether it blocks the pre-PR gate. Return at most five findings, prioritized by P1/P2 impact. True out-of-scope or non-blocking P3 follow-ups must include the evidence and tracking destination that make them non-blocking.
```

### 3. Triage before editing

Combine both review outputs into a short triage table:

```text
Finding | Reviewer | Severity | Scope | Decision | Evidence
```

For each finding:

- Fix `P1`/`P2` findings classified `IN_PLAN`, `PLAN_PREREQUISITE`, or `REGRESSION_FROM_THIS_DIFF`. Fix P3 only when plan-required, verification-required, regression-caused, or cheap and safe; otherwise document as a non-blocking follow-up.
- Stop for user input on `QUESTION` findings that affect whether a finding should be fixed, deferred, or excluded from this PR.
- Document `OUT_OF_SCOPE_FOLLOW_UP` findings with evidence, a tracking destination, and a cited test proving the deferred input class is handled or genuinely unreachable. If you cannot cite or add such a test, treat the finding as in scope rather than deferring it.
- Verify reviewer claims against the code before changing anything; false positives should be recorded as rejected with evidence.

### 4. Fix, verify, and rereview until clean

After applying any in-scope fix:

1. Run the smallest meaningful targeted tests for the touched code.
2. Rerun any plan-required verification invalidated by the fix.
3. Rerun Codex and any applicable Claude Code reviewer against only the changed files and prior blocking findings, not as a fresh whole-diff hunt for unrelated new issues.
4. Repeat until all applicable reviewers return `CLEAN_FOR_PR` by substance with no unresolved blocking in-scope P1/P2 findings, or until Codex is clean and Claude Code is truthfully skipped under the low-risk policy.

Do not stop while any applicable reviewer has an unresolved blocking in-scope P1/P2 finding. Do not open or proceed to a PR while any applicable reviewer has an unresolved blocking in-scope P1/P2 finding. If invoked from `run-plan`, do not end the workflow at `CLEAN_FOR_PR`; hand control back for final verification, commit, push, PR creation, and post-PR monitoring.

Hard stop the review loop when any of these is true:

- two fix attempts do not resolve the same finding or same failure family,
- a narrow/optional component keeps producing new edge-case findings after two cycles, indicating it should be reverted, deferred, or redesigned instead of patched through review,
- three total review cycles have run since the initial pre-PR packet,
- a P1/P2 fix requires a product or scope decision,
- reviewers disagree on whether a finding is in scope and the plan does not resolve it,
- required reviewer infrastructure is unavailable and the user has not waived it,
- verification cannot run for reasons the agent cannot resolve.

On a hard stop, report the convergence blocker and recommend the smallest path: revert/defer the unstable slice, narrow the PR, or ask the user for an explicit scope decision. Do not launch “final clean gate” review cycles beyond the budget.

## Review artifact

Maintain a durable note under:

```text
thoughts/validation/pre-pr-reviews/<YYYY-MM-DD>-<branch>.md
```

Include:

- base/range and plan path or standalone scope,
- target branch/base context, caller-reported base freshness status, and any rebase-triggered rerun requirement when invoked from `run-plan`,
- changed files summary,
- each review cycle's Codex verdict and Claude Code verdict when Claude Code applied, or the recorded low-risk Claude Code skip classification and any override decision,
- the triage table,
- fixes applied for blocking P1/P2 issues and any fixed P3 issues,
- verification commands and results after fixes,
- remaining out-of-scope follow-ups with evidence and tracking destination,
- any `REVIEW_INCOMPLETE_RERUN_NEEDED` handoff, the single allowed rerun slice, and whether the gate stopped for review budget,
- final gate result and whether it is `OPEN_PR_READY` for a caller such as `run-plan`.

If the repo has a different validation-artifact convention, use that convention and keep the same information.

## Passing result

The final summary must include:

- selected review surface: `Codex/Claude Code` or `Pi GPT/GLM wrapper`,
- for the Codex/Claude Code route: `Codex verdict: CLEAN_FOR_PR` or equivalent no-unresolved-blocking-in-scope-P1/P2 result,
- for the Codex/Claude Code route: `Claude Code verdict: CLEAN_FOR_PR` or equivalent no-unresolved-blocking-in-scope-P1/P2 result when Claude Code applied, or `Claude Code skipped: <low-risk classification and override decision>` when Claude Code was truthfully skipped,
- for the explicit Pi GPT/GLM wrapper route: Pi GPT verdict plus applicable GLM verdict, or `GLM skipped: <low-risk classification>` when GLM is not applicable, labeled as Pi GPT/GLM evidence rather than Codex/Claude Code evidence,
- base freshness context from the caller and any rebase-triggered rerun requirement,
- verification rerun after the last fix,
- artifact path,
- any remaining non-blocking out-of-scope follow-ups with evidence and tracking destination,
- `Next step: OPEN_PR_READY` when invoked from `run-plan`, so the caller continues to final verification, commit, push, PR creation, and post-PR monitoring instead of concluding.
