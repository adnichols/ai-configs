---
name: pre-pr-implementation-review
description: Run Pi's pre-PR implementation review loop with both GPT-5.5 and OpenCode Zen GLM-5 quality reviewers, then continue fixing and rereviewing until every in-scope P1/P2/P3 finding is addressed. Use this before opening pull requests, after an implementation is complete, inside scoped-plan-run, or whenever the user asks for GPT plus GLM code review of a branch/diff; inside scoped-plan-run this gate hands back to PR creation rather than concluding the workflow.
---

# Pre-PR Implementation Review

Use this skill to catch implementation issues that would otherwise appear during pull request review. It is a code-review-and-fix loop, not a plan review, not a general cleanup pass, and not the end of a scoped plan run.

The gate passes only when both reviewers agree by substance that the current implementation has no unresolved in-scope P1/P2/P3 findings. Lower-severity P3 findings still need an explicit disposition before merge readiness: fix them when they are in scope, reject false positives with evidence, or document true out-of-scope follow-ups with a tracking destination.

When invoked from `scoped-plan-run`, a passing result means `OPEN_PR_READY`, not `DONE`. Return the final gate status and artifact path to the scoped runner so it can rerun final verification if needed, commit, push, open the PR, and continue post-PR monitoring.

## Inputs

Accept any of:

```text
/skill:pre-pr-implementation-review
/skill:pre-pr-implementation-review <plan path>
/skill:pre-pr-implementation-review <base branch or comparison range>
/skill:pre-pr-implementation-review <plan path> --base <branch-or-range>
```

If invoked from `scoped-plan-run`, use that plan path, target branch/base branch, scope contract, changed files, and latest verification results.

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
- `P3`: lower-severity improvement, maintainability concern, or minor gap. In-scope P3 findings are not allowed to disappear into the summary; fix them, reject them with evidence, or document them as true out-of-scope follow-ups before declaring the branch merge-ready.

Also classify every finding with the scoped-plan-run labels when a plan is present:

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

### 2. Run both reviewers in parallel

Use Pi subagents directly. Launch both in the same turn when possible:

- `quality-reviewer` for the GPT-5.5 pass.
- `quality-reviewer-glm` for the OpenCode Zen GLM-5 pass.

Both reviews are read-only. If `quality-reviewer-glm` is unavailable, stop and report that the OpenCode Zen GLM-5 gate cannot run; do not silently substitute another model.

Use this prompt shape for each reviewer:

```text
Read-only pre-PR implementation review. Do not edit files.

Reviewer: <GPT-5.5 | OpenCode Zen GLM-5>
Plan/scope: <plan path or standalone scope summary>
Base/comparison: <base branch or range>
Changed files:
<changed files>

Review committed, staged, and unstaged changes in this worktree. Focus on issues a pull-request reviewer would reasonably ask to fix, justify, or track before merge.

Classify every finding with:
- Severity: P1, P2, or P3
- Scope: IN_PLAN, PLAN_PREREQUISITE, REGRESSION_FROM_THIS_DIFF, OUT_OF_SCOPE_FOLLOW_UP, or QUESTION

Every in-scope P1/P2/P3 finding blocks a clean ready-for-PR verdict until it is fixed, rejected as a false positive with evidence, or reclassified as a true out-of-scope follow-up with evidence and a tracking destination. Do not use P3 severity to leave in-scope work unresolved.

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

For every finding include: severity, scope classification, file/line, evidence, impact, recommended fix, and whether it blocks the pre-PR gate. In-scope P1/P2/P3 findings block the gate; true out-of-scope follow-ups must include the evidence and tracking destination that make them non-blocking.
```

### 3. Triage before editing

Combine both review outputs into a short triage table:

```text
Finding | Reviewer | Severity | Scope | Decision | Evidence
```

For each finding:

- Fix `P1`/`P2`/`P3` findings classified `IN_PLAN`, `PLAN_PREREQUISITE`, or `REGRESSION_FROM_THIS_DIFF`; prioritize P1/P2 first, then clear P3 before declaring merge readiness.
- Stop for user input on `QUESTION` findings that affect whether a finding should be fixed, deferred, or excluded from this PR.
- Document `OUT_OF_SCOPE_FOLLOW_UP` findings with evidence, a tracking destination, and a cited test proving the deferred input class is handled or genuinely unreachable. If you cannot cite or add such a test, treat the finding as in scope rather than deferring it.
- Verify reviewer claims against the code before changing anything; false positives should be recorded as rejected with evidence.

### 4. Fix, verify, and rereview until clean

After applying any in-scope fix:

1. Run the smallest meaningful targeted tests for the touched code.
2. Rerun any plan-required verification invalidated by the fix.
3. Rerun both GPT-5.5 and OpenCode Zen GLM-5 reviewers against the current diff.
4. Repeat until both reviewers return `CLEAN_FOR_PR` by substance with no unresolved in-scope P1/P2/P3 findings.

Do not stop after a single reviewer is clean. Do not open or proceed to a PR while either reviewer has an unresolved in-scope P1/P2/P3 finding. If invoked from `scoped-plan-run`, do not end the workflow at `CLEAN_FOR_PR`; hand control back for final verification, commit, push, PR creation, and post-PR monitoring.

Stop with a blocker only when:

- a P1/P2/P3 fix requires a product or scope decision,
- the same in-scope P1/P2/P3 finding recurs after two materially different fix attempts,
- required reviewer infrastructure is unavailable and the user has not waived it,
- verification cannot run for reasons the agent cannot resolve.

## Review artifact

Maintain a durable note under:

```text
thoughts/validation/pre-pr-reviews/<YYYY-MM-DD>-<branch>.md
```

Include:

- base/range and plan path or standalone scope,
- changed files summary,
- each review cycle's GPT and GLM verdicts,
- the triage table,
- fixes applied for P1/P2/P3 issues,
- verification commands and results after fixes,
- remaining out-of-scope follow-ups with evidence and tracking destination,
- final gate result and whether it is `OPEN_PR_READY` for a caller such as `scoped-plan-run`.

If the repo has a different validation-artifact convention, use that convention and keep the same information.

## Passing result

The final summary must include:

- `GPT verdict: CLEAN_FOR_PR` or equivalent no-unresolved-in-scope-P1/P2/P3 result,
- `GLM verdict: CLEAN_FOR_PR` or equivalent no-unresolved-in-scope-P1/P2/P3 result,
- verification rerun after the last fix,
- artifact path,
- any remaining non-blocking out-of-scope follow-ups with evidence and tracking destination,
- `Next step: OPEN_PR_READY` when invoked from `scoped-plan-run`, so the caller continues to final verification, commit, push, PR creation, and post-PR monitoring instead of concluding.
