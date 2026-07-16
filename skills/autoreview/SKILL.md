---
name: autoreview
description: Run a bounded pre-PR implementation review with a Codex review leg and an applicable Claude Code review leg, fix or disposition blocking findings, and stop instead of entering non-converging review loops. Use this before opening pull requests, after an implementation is complete, inside run-plan, or whenever the user asks for Codex plus applicable Claude Code code review of a branch/diff; inside run-plan this gate hands back to PR creation rather than waiting for any Codex PR thumbs-up.
---

# Autoreview

Use this skill to catch implementation issues that would otherwise appear during pull request review. It is a code-review-and-fix loop, not a plan review, not a general cleanup pass, and not the end of `run-plan`.

The gate passes when Codex and any applicable Claude Code reviewer agree by substance that the current implementation has no unresolved in-scope P1/P2 findings. This is local review-agent consensus, not a requirement to wait for a Codex PR bot comment, PR-hosted thumbs-up, `reviewDecision: APPROVED`, or any other external approval. If Claude Code is skipped under the low-risk policy, the gate must record that skip instead of requiring a Claude Code verdict. P3 findings are non-blocking unless they are plan-required, verification-required, or regressions caused by this change; do not fix optional polish merely because it is cheap.

When invoked from `run-plan`, a passing result means `OPEN_PR_READY`, not `DONE`. It is only a handoff after the caller has satisfied run-plan's implementation-stage PM review; base freshness may still be pending until final verification and the scoped commit make a safe rebase possible. Return the final gate status, artifact path, target branch/base context, caller-reported base freshness status or pending status, and any known rebase-triggered rerun requirement to the `run-plan` caller so it can rerun final verification if needed, complete base freshness safely, commit, push, open the PR, inspect the current PR snapshot for actionable feedback/mergeability, and complete once local merge-readiness consensus is proven. Do not tell the caller to wait for a Codex thumbs-up or human approval after local review-agent consensus is clean.

## Inputs

Accept any of:

```text
/skill:autoreview
/skill:autoreview <plan path>
/skill:autoreview <base branch or comparison range>
/skill:autoreview <plan path> --base <branch-or-range>
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
- `P2`: PR-blocking correctness/reliability risk on the accepted current behavior: user-visible regression, missing required supported-path edge-case handling, important error-handling gap, significant current-path performance issue, API/contract mismatch, or tests that would allow a materially incomplete implementation to pass.
- `P3`: lower-severity improvement, maintainability concern, polish, or minor gap. P3 findings require an explicit disposition, but block only when they are plan-required, verification-required, or regression-caused.

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

A finding may be classified `OUT_OF_SCOPE_FOLLOW_UP` when evidence shows it is not required for the accepted current behavior, truthful verification, or a regression caused by this diff. Evidence may come from the product contract, supported-path definition, code reachability, or existing tests; do not add implementation or tests solely to prove speculative future scale or another unsupported scenario is out of scope.

### Evidence threshold for blocking findings

Every blocking P1/P2 finding must identify all of:

- the triggering input, runtime state, or operator action;
- the reachable path from that trigger through the changed or newly exposed behavior;
- the observable impact on an accepted current behavior;
- the diff relationship: why this change introduces the failure, exposes a previously unreachable failure, or makes existing verification materially false.

Do not block on a hypothetical hazard without this evidence. A dependency or platform claim must be checked against authoritative documentation, published types or schemas, or source for the relevant version before it is accepted as a finding. Reviewer memory, convention, and analogy are leads to verify, not sufficient evidence.

### Fix-shape and ownership boundary

Prefer the smallest correct fix at the existing ownership boundary. A review finding does not grant authority to redesign adjacent systems. Stop and request an explicit product or scope decision before a fix would introduce or change a protocol, configuration surface, storage format, migration, public API or contract, release process, ownership move, or unrelated refactor.

This governor cannot hide a concrete current-path regression covered by the valid-input or shared primitive protections above. When the correct in-scope fix cannot remain within the same ownership boundary, use the stop-before protocol and report the trigger, required expansion, affected contract, and smallest decision needed from the user.

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

Before launching reviewers, record a pre-review scope baseline containing:

- the task or plan and intended behavior;
- supported paths and explicit non-goals;
- existing owner boundaries and product surfaces in scope;
- the initial changed files, including committed, staged, and unstaged changes.

Use this scope baseline for every slice, triage decision, fix, and rereview. A later finding may expose a concrete reachable path within the baseline, but it may not silently widen the accepted behavior or ownership boundary.

### 2. Classify Claude Code need, then run reviewers

Before launching Claude Code, classify the review scope using the high-risk second-reviewer policy:

- **Use Claude Code** when the PR touches data loss risk, auth/security, concurrency/locking, migrations/persistence, release-risk, release-blocking CI behavior, or another explicit P1/P2 risk surface.
- **Skip Claude Code by default** for docs-only, low-risk UI copy, low-risk tests, and narrow follow-ups unless the operator provides an explicit override reason.
- Use a compact Claude Code packet with named files, the exact risk question, relevant diff excerpts, verification already run, and outcome limits. Do not send broad context when a packet is sufficient.

Launch applicable reviewers in the same turn when possible:

- **Codex** is the primary review leg. In Codex, run it as a Codex subagent/native review task when that facility is available; otherwise use `codex-review-partner` in `implementation-review` mode. In Pi, run Codex as a subprocess through the installed `codex-review-partner` wrapper.
- **Claude Code** is the high-risk second-reviewer leg when the high-risk trigger or an explicit override applies. Use `claude-code-review`; the canonical launcher owns model, effort, and private-tmux mechanics.

Do not use alternate model-subagent reviewers to satisfy the Codex/Claude Code gate described in this section.

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

Run Claude Code only when applicable. In Pi, write the bounded prompt file and call:

```text
claude_review({
  action: "start",
  cwd: "/path/to/repo",
  promptFile: "/tmp/pre-pr-claude-review.md",
  output: "thoughts/validation/pre-pr-reviews/<date-branch>-claude.md"
})
```

Do not poll while the originating Pi session remains active. Consume the completion notification and read the artifact; after reload/restart, recover the persisted job with `claude_review` list/status. In non-Pi runtimes, follow `claude-code-review` and call the canonical Python launcher directly.

The coordinating agent consumes the Codex and Claude artifacts/verdicts, triages findings, applies in-scope fixes in the active worktree, and reruns the same applicable reviewer set after material fixes. If Codex or the required Claude Code reviewer is unavailable, report `REVIEW_INFRASTRUCTURE_FAILURE` unless the user explicitly waives the gate.

Launcher transport validity does not universally require a `VERDICT:` line, but this pre-PR workflow does require one of its locked final verdicts. A non-empty artifact with launcher metadata may therefore be valid transport yet still be unusable for this gate if its workflow verdict is missing. Treat empty output, missing launcher metadata, tool-only output, provider errors, or a transcript ending in tool use as `REVIEW_INFRASTRUCTURE_FAILURE`, not `CLEAN_FOR_PR`. Rerun once with a narrower scoped prompt. Do not fix empty reviewer output by adding or lowering parent-side turn limits; hard turn caps can truncate the final verdict and produce another unusable result. If the narrowed rerun is still unusable, stop with a review-infrastructure blocker unless the user explicitly waives the gate.

For every quality reviewer, use bounded scope and bounded exploration. Give each reviewer a concrete review packet: plan scope, changed files, diff summary, verification results, named touched surfaces, and the specific failure families to check. Tool outputs should be narrow: prefer exact file reads with offsets/limits and `rg -n` on changed files over repo-wide dumps. Do not use parent-side `max_turns` as the primary bounding mechanism for reviewer completion; bound the assigned scope instead.

If any reviewer cannot complete the assigned scope, it must return `VERDICT: REVIEW_INCOMPLETE_RERUN_NEEDED` with completed checks, remaining checks, and the exact recommended follow-up slice. The parent may run at most one narrowed follow-up for that reviewer in that cycle. If that follow-up is still incomplete or unusable, stop with a review-budget blocker or ask the user to waive/narrow the gate; do not keep launching slices.

Split a review only when the diff has more than 20 changed files, more than 2000 diff lines, or clearly independent product surfaces that one bounded slice cannot review. Use at most two slices per reviewer in the initial cycle, chosen by concrete surface/risk. Do not split a small or medium diff merely to get more opinions, and do not create generic failure-family slices unless the diff actually touches those failure families.

Each reviewer slice must use the same severity, scope, budget, and verdict format. The parent synthesizes all slice results; do not ask one subagent to deeply inspect every slice and synthesize the whole PR.

Use this prompt shape for each reviewer:

```text
Read-only pre-PR implementation review. Do not edit files.

Reviewer: <Codex | Claude Code>
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

Report all known in-scope P1/P2 failure families in the initial pass. Detail at most the five highest-impact findings. If more known blockers remain, include the overflow count and name each remaining failure family; do not withhold known blockers to reveal them one per later cycle.

Classify every finding with:
- Severity: P1, P2, or P3
- Scope: IN_PLAN, PLAN_PREREQUISITE, REGRESSION_FROM_THIS_DIFF, OUT_OF_SCOPE_FOLLOW_UP, or QUESTION

Every in-scope P1/P2 finding blocks a clean ready-for-PR verdict until it is fixed, rejected as a false positive with evidence, or reclassified as a true out-of-scope follow-up with evidence and a tracking destination. P3 findings block only when they are plan-required, verification-required, or regression-caused; otherwise return them as non-blocking follow-ups.

For a blocking P1/P2 finding, evidence must include the triggering input or state, reachable path, observable impact, and relationship to this diff. For a claim that depends on framework, library, CLI, protocol, or platform behavior, cite authoritative documentation, types, schemas, or source for the relevant version.

Recommend the smallest correct fix at the existing ownership boundary. Stop before recommending a new protocol, config, storage format, migration, public API or contract, release process, ownership move, or unrelated refactor unless the user has explicitly expanded scope.

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

For every finding include: severity, scope classification, file/line, triggering input or state, reachable path, observable impact, diff relationship, evidence, recommended fix, and whether it blocks the pre-PR gate. Return at most five detailed findings, prioritized by P1/P2 impact. Also report the overflow count and failure families for every additional known in-scope P1/P2 blocker. True out-of-scope or non-blocking P3 follow-ups must include the evidence and tracking destination that make them non-blocking.
```

### 3. Triage before editing

Combine both review outputs into a short triage table:

```text
Finding | Reviewer | Severity | Scope | Decision | Evidence
```

For each finding:

- Fix `P1`/`P2` findings classified `IN_PLAN`, `PLAN_PREREQUISITE`, or `REGRESSION_FROM_THIS_DIFF`. Fix P3 only when plan-required, verification-required, or regression-caused; otherwise document it as a non-blocking follow-up.
- Stop for user input on `QUESTION` findings that affect whether a finding should be fixed, deferred, or excluded from this PR.
- Document `OUT_OF_SCOPE_FOLLOW_UP` findings with evidence and a tracking destination. Do not create code or tests solely to dispose of speculative future risks, unsupported paths, unrelated architecture work, or polish.
- Verify reviewer claims against the code before changing anything; false positives should be recorded as rejected with evidence.
- Apply the fix-shape governor before editing: keep the fix at the same ownership boundary, or stop before protocol, config, storage, migration, public API, release process, ownership, or unrelated-refactor expansion and request the smallest necessary decision.

### 4. Fix, verify, and run one targeted rereview

After applying any in-scope fix:

1. Run the smallest meaningful targeted tests for the touched code.
2. Rerun any plan-required verification invalidated by the fix.
3. Rerun Codex and any applicable Claude Code reviewer once against only the changed files, prior blocking findings, and resulting edits, not as a fresh whole-diff hunt for unrelated new issues.
4. Allow a third total review cycle only when that targeted rereview identifies a new concrete blocker introduced or exposed by the fix. Otherwise stop after the targeted rereview with either `CLEAN_FOR_PR` or a convergence/scope blocker.

Do not stop while any applicable reviewer has an unresolved blocking in-scope P1/P2 finding. Do not open or proceed to a PR while any applicable reviewer has an unresolved blocking in-scope P1/P2 finding. If invoked from `run-plan`, do not end the workflow at `CLEAN_FOR_PR`; hand control back for final verification, commit, push, PR creation, and local merge-readiness checking. The pre-PR gate must not require a later Codex PR thumbs-up after its own Codex review leg is clean.

Hard stop the review loop when any of these is true:

- two fix attempts do not resolve the same finding or same failure family,
- a narrow/optional component keeps producing new edge-case findings after two cycles, indicating it should be reverted, deferred, or redesigned instead of patched through review,
- three total review cycles have run since the initial pre-PR packet; the third cycle is permitted only for a new concrete blocker introduced or exposed by the prior fix,
- a P1/P2 fix requires a product or scope decision,
- reviewers disagree on whether a finding is in scope and the plan does not resolve it,
- required reviewer infrastructure is unavailable and the user has not waived it,
- verification cannot run for reasons the agent cannot resolve.

On a hard stop, report the convergence blocker and recommend the smallest path: revert/defer the unstable slice, narrow the PR, or ask the user for an explicit scope decision. Do not launch “final clean gate” review cycles beyond the budget.

## Behavioral verification is separate

A clean source review does not replace required behavioral verification. For UI, CLI, HTTP, MCP, generated artifacts, and other operator-visible surfaces, run the plan-required verification or the smallest appropriate behavioral check even when both reviewer legs return clean. Record source-review consensus and behavioral verification as separate evidence; neither may be used to fabricate the other.

## Release freeze discipline

Apply release freeze discipline for release, beta/stable promotion, hotfix, backport, signing, packaging, deployment, or release-infrastructure work: freeze the lane to release-critical correctness and truthful verification. Treat concrete P1/P2 defects, regressions caused by the release change, broken acceptance criteria, invalid artifacts, and false release evidence as blocking under the normal scope rules.

Do not use the release lane to introduce non-blocking design changes, speculative hardening, optional polish, ownership moves, new protocols or configuration, unrelated refactors, or release-process changes that are not required to make the current release safe and truthful. Disposition those as `OUT_OF_SCOPE_FOLLOW_UP` with evidence and a tracking destination, or stop for an explicit scope decision when they are genuinely required.

## Review artifact

Maintain a durable note under:

```text
thoughts/validation/pre-pr-reviews/<YYYY-MM-DD>-<branch>.md
```

Include:

- base/range and plan path or standalone scope,
- target branch/base context, caller-reported base freshness status, and any rebase-triggered rerun requirement when invoked from `run-plan`,
- changed files summary,
- the pre-review scope baseline,
- each review cycle's Codex verdict and Claude Code verdict when Claude Code applied, or the recorded low-risk Claude Code skip classification and any override decision,
- the triage table,
- fixes applied for blocking P1/P2 issues and any fixed P3 issues,
- verification commands and results after fixes,
- remaining out-of-scope follow-ups with evidence and tracking destination,
- any `REVIEW_INCOMPLETE_RERUN_NEEDED` handoff, the single allowed rerun slice, and whether the gate stopped for review budget,
- final gate result and whether it is `OPEN_PR_READY` for a caller such as `run-plan`, explicitly noting that no Codex PR thumbs-up is required beyond the clean local Codex review artifact.

If the repo has a different validation-artifact convention, use that convention and keep the same information.

## Passing result

The final summary must include:

- selected review surface: `Codex/Claude Code`,
- `Codex verdict: CLEAN_FOR_PR` or equivalent no-unresolved-blocking-in-scope-P1/P2 result,
- `Claude Code verdict: CLEAN_FOR_PR` or equivalent no-unresolved-blocking-in-scope-P1/P2 result when Claude Code applied, or `Claude Code skipped: <low-risk classification and override decision>` when Claude Code was truthfully skipped,
- base freshness context from the caller and any rebase-triggered rerun requirement,
- verification rerun after the last fix,
- artifact path,
- any remaining non-blocking out-of-scope follow-ups with evidence and tracking destination,
- `Next step: OPEN_PR_READY` when invoked from `run-plan`, so the caller continues to final verification, commit, push, PR creation, and local merge-readiness checking instead of concluding or waiting for a Codex thumbs-up.
