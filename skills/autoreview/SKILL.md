---
name: autoreview
description: Run a bounded pre-PR implementation review with a Codex review leg and an applicable Claude Code review leg, fix or disposition blocking findings, and stop instead of entering non-converging review loops. Use this before opening pull requests, after an implementation is complete, inside run-plan, or whenever the user asks for Codex plus applicable Claude Code code review of a branch/diff; inside run-plan this gate hands back to PR creation rather than waiting for any Codex PR thumbs-up.
---

# Autoreview

Use this skill to catch implementation issues that would otherwise appear during pull request review. It is a code-review-and-fix loop, not a plan review, not a general cleanup pass, and not the end of `run-plan`.

The gate passes when Codex and any applicable Claude Code reviewer agree by substance that the current implementation has no unresolved in-scope P1/P2 findings. This is local review-agent consensus, not a requirement to wait for a Codex PR bot comment, PR-hosted thumbs-up, `reviewDecision: APPROVED`, or any other external approval. If Claude Code is skipped under the low-risk policy, the gate must record that skip instead of requiring a Claude Code verdict. P3 findings are non-blocking unless they are plan-required, verification-required, or regressions caused by this change; do not fix optional polish merely because it is cheap.

**Explicit operator override:** PR creation and a clean review verdict are separate decisions. If the operator explicitly instructs the agent to open, create, or publish the PR regardless of review status or coverage, obey immediately and do not delay PR creation for another review attempt, missing reviewer coverage, an unusable review artifact, or unresolved review findings. Preserve the requested draft/ready state. Record the override and disclose the actual review status, incomplete coverage, infrastructure failures, and known unresolved findings in the PR body; never relabel the gate as clean or claim merge readiness.

When invoked from `run-plan`, a passing result means `OPEN_PR_READY`, not `DONE`. It is only a handoff after the caller has satisfied run-plan's implementation-stage PM review; base freshness may still be pending until final verification and the scoped commit make a safe rebase possible. Return the final gate status, artifact path, target branch/base context, caller-reported base freshness status or pending status, and any known rebase-triggered rerun requirement to the `run-plan` caller so it can rerun final verification if needed, complete base freshness safely, commit, push, open the PR, inspect the current PR snapshot for actionable feedback/mergeability, and complete once local merge-readiness consensus is proven. Do not tell the caller to wait for a Codex thumbs-up or human approval after local review-agent consensus is clean.

## Inputs

Accept any of:

```text
/skill:autoreview
/skill:autoreview <plan path>
/skill:autoreview <base branch or comparison range>
/skill:autoreview <plan path> --base <branch-or-range>
```

If invoked from `run-plan`, use that plan path, target branch/base branch, scope contract, changed files, latest verification results, PM review status, caller-reported base freshness status or pending status, any known rebase-triggered rerun requirement, and the unified implementation-review cycle ledger (completed cycles, triggering diffs/fixes, verdicts, and remaining budget). Do not start a fresh autoreview budget at invocation.

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

Also import or reconstruct the unified review-cycle ledger before launching any reviewer:

- When called by `run-plan`, require the caller's ledger and preserve its cycle numbers.
- When invoked independently, inspect current run notes and durable review artifacts for usable implementation-review passes over this scoped change. Equivalent runtime-native/pre-PR evidence over the same unchanged diff counts once; each later materially new reviewer pass counts as another cycle.
- Record completed cycles, the diff/fix that triggered each one, verdicts, and remaining budget in the autoreview artifact. If prior review evidence exists but the consumed budget cannot be determined safely, stop for clarification rather than assuming zero.
- If no cycle remains, do not launch reviewers. Return the convergence/review-budget outcome and smallest next decision exactly as required by the global policy, regardless of whether a PR exists.

Use this scope baseline and ledger for every slice, triage decision, fix, and rereview. A later finding may expose a concrete reachable path within the baseline, but it may not silently widen the accepted behavior or ownership boundary.

### 2. Classify Claude Code need, then run reviewers

Before launching Claude Code, classify the review scope using the high-risk second-reviewer policy:

- **Use Claude Code** when the PR touches data loss risk, auth/security, concurrency/locking, migrations/persistence, release-risk, release-blocking CI behavior, or another explicit P1/P2 risk surface.
- **Skip Claude Code by default** for docs-only, low-risk UI copy, low-risk tests, and narrow follow-ups unless the operator provides an explicit override reason.
- Use a compact Claude Code packet with named files, the exact risk question, relevant diff excerpts, verification already run, and outcome limits. Do not send broad context when a packet is sufficient.

Launch applicable reviewers in adjacent Herdr tabs in the same workspace and exact worktree:

- **Codex** is the primary review leg. In Pi, follow `herdr-reviewers` and `codex-review-partner`; use a visible interactive Codex tab with the workflow's bounded implementation-review packet.
- **Claude Code** is the high-risk second-reviewer leg when the high-risk trigger or an explicit override applies. In Pi, follow `herdr-reviewers` and `claude-code-review`; use a visible interactive Claude tab with the compact risk packet.

Do not use alternate model-subagent reviewers, the disabled `codex_review`/`claude_review` tools, private tmux launchers, or non-interactive CLI modes to satisfy this gate.

Both reviews are static, read-only inspection only. Reviewers must never run tests, test suites, builds, linters, typechecks, benchmarks, verification scripts, validation commands, or other executable checks intended to validate behavior. They may inspect test code and consume the verification results supplied in the review packet. The calling/coordinating agent exclusively owns all test and verification execution. If Codex or a required Claude Code review is unavailable, report `REVIEW_INFRASTRUCTURE_FAILURE` unless the user explicitly waives the gate or directs opening the PR regardless; do not silently substitute another model.

### Runtime launch rules

In Pi, follow `herdr-reviewers` for both legs and run the installed shared state machine with `~/.agents/scripts/review_orchestration.py run --request <request.json> --output <receipt.json>`. The command uses the production Herdr CLI adapter; deterministic fakes exercise the same state machine in tests. Do not replace it with an ad hoc shell loop that serializes prompt-and-wait operations.

1. Discover the parent Pi workspace from the exact current worktree.
2. Create one no-focus adjacent tab per applicable reviewer and start Codex and Claude with the skill-defined model/reasoning and read-only arguments.
3. Capture one complete candidate fingerprint after tabs are ready and before any prompt submission. Every applicable leg in the cycle receives that exact fingerprint.
4. Prepare each bounded prompt with its own unique nonce and exact pre-PR verdict contract.
5. Submit and confirm acceptance of all applicable initial prompts before beginning the first wait. For dual review, never submit Codex, wait for Codex, and only then submit Claude (or the inverse).
6. Settle applicable legs independently/concurrently. Validate each leg's state, nonce boundary, exact verdict, non-empty content, and returned fingerprint without allowing one clean leg to hide a failed, incomplete, timed-out, invalid, or stale sibling.
7. Aggregate only after every applicable leg has reached a terminal outcome. The helper's `all_prompts_submitted_before_first_wait`, per-leg elapsed times, candidate wall time, and phase-local events are required review evidence.
8. Write the normal durable artifact before cleanup. Only after it is durable may the coordinator run `~/.agents/scripts/review_orchestration.py cleanup --request <request.json> --receipt <receipt.json> --artifact-written`; that explicit gate closes the recorded coordinator-owned tab IDs only. Keep tabs available while findings, follow-up slices, fixes, targeted rereviews, validation failures, or operator takeover remain pending. Reviewers never close their own tabs.

Do not use a Pi GPT subagent, `interactive_shell`, the disabled managed review tools, private tmux, `codex exec`, or Claude print mode. If the parent session is interrupted, rediscover the visible reviewer tab and validate its nonce/fingerprint manually; this initial transport has no automatic detached completion delivery.

The coordinating agent consumes the Codex and Claude artifacts/verdicts, triages findings, applies in-scope fixes in the active worktree, and reruns the same applicable reviewer set after material fixes. If Codex, Herdr, or the required Claude Code reviewer is unavailable, report `REVIEW_INFRASTRUCTURE_FAILURE` unless the user explicitly waives the gate or directs opening the PR regardless.

The Herdr transport requires matching nonce boundaries, non-empty review content, the exact locked workflow verdict as the final non-empty line inside the boundary, a settled reviewer state, and an unchanged complete worktree fingerprint. Treat empty output, missing or mismatched boundaries, invalid verdicts, tool-only output, provider errors, transcripts ending in tool use, or stale fingerprints as `REVIEW_INFRASTRUCTURE_FAILURE`, not `CLEAN_FOR_PR`. The shared orchestration helper permits exactly one narrower retry only for unusable output on the affected leg and only while the complete candidate fingerprint is unchanged. It must not retry provider/auth/permission failures, timeouts, stale results, or a valid `REVIEW_INCOMPLETE_RERUN_NEEDED` verdict as if they were malformed output; it must not reset the sibling leg or the broader review-cycle budget. Do not fix empty reviewer output by adding or lowering parent-side turn limits; hard turn caps can truncate the final verdict and produce another unusable result. If the narrowed retry is still unusable, stop with a review-infrastructure blocker unless the user explicitly waives the gate or directs opening the PR regardless.

For every quality reviewer, use bounded scope and bounded exploration. Give each reviewer a concrete review packet: plan scope, changed files, diff summary, verification results, named touched surfaces, and the specific failure families to check. Tool outputs should be narrow: prefer exact file reads with offsets/limits and `rg -n` on changed files over repo-wide dumps. Do not use parent-side `max_turns` as the primary bounding mechanism for reviewer completion; bound the assigned scope instead.

If any reviewer cannot complete the assigned scope, it must return `VERDICT: REVIEW_INCOMPLETE_RERUN_NEEDED` with completed checks, remaining checks, and the exact recommended follow-up slice. The parent may run at most one narrowed follow-up for that reviewer in that cycle. If that follow-up is still incomplete or unusable, stop with a review-budget blocker or ask the user to waive/narrow the gate; do not keep launching slices.

Split a review only when the diff has more than 20 changed files, more than 2000 diff lines, or clearly independent product surfaces that one bounded slice cannot review. Use at most two slices per reviewer in the initial cycle, chosen by concrete surface/risk. Do not split a small or medium diff merely to get more opinions, and do not create generic failure-family slices unless the diff actually touches those failure families.

Each reviewer slice must use the same severity, scope, budget, and verdict format. The parent synthesizes all slice results; do not ask one subagent to deeply inspect every slice and synthesize the whole PR.

Use this prompt shape for each reviewer:

```text
Read-only pre-PR implementation review. Do not edit files.
Do not run or invoke tests, test suites, builds, linters, typechecks, benchmarks, verification scripts, validation commands, or any other executable checks intended to validate behavior. Inspect test code and the caller-supplied verification results only; the calling/coordinating agent exclusively owns test and verification execution. Read-only inspection commands such as git diff, rg, and file reads are allowed.

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

After applying any in-scope fix—and only because that fix changed verification-relevant state:

1. Run the smallest meaningful targeted tests for the touched code.
2. Rerun only plan-required verification invalidated by the fix. Reuse and record still-valid passing results instead of rerunning unchanged checks merely because a review cycle completed.
3. Rerun Codex and any applicable Claude Code reviewer once against only the changed files, prior blocking findings, and resulting edits, not as a fresh whole-diff hunt for unrelated new issues.
4. Allow a third total review cycle only when that targeted rereview identifies a new concrete blocker introduced or exposed by the fix. Otherwise stop after the targeted rereview with either `CLEAN_FOR_PR` or a convergence/scope blocker. Count this budget across the scoped change, not from the moment this skill was invoked: creating a PR does not reset, extend, reduce, or otherwise alter the limit, and a post-PR `REVIEW_ESCAPE` consumes an otherwise permitted remaining cycle rather than creating a new one.

Absent an explicit operator instruction to open the PR regardless, do not stop while any applicable reviewer has an unresolved blocking in-scope P1/P2 finding and do not open or proceed to a PR with those findings unresolved. An explicit operator override ends this prohibition: open the PR as directed, disclose the non-clean review state, and do not represent it as `CLEAN_FOR_PR` or merge-ready. If invoked from `run-plan`, do not end the workflow at `CLEAN_FOR_PR`; hand control back for final verification, commit, push, PR creation, and local merge-readiness checking. The pre-PR gate must not require a later Codex PR thumbs-up after its own Codex review leg is clean.

The ordinary local review budget is exhausted when any of these is true:

- two fix attempts do not resolve the same finding or same failure family,
- a narrow/optional component keeps producing new edge-case findings after two cycles, indicating it should be reverted, deferred, or redesigned instead of patched through review,
- three total review cycles have run for the scoped change across pre-PR and post-PR review; the third cycle is permitted only for a new concrete blocker introduced or exposed by the prior fix, and PR existence never resets or changes this budget,
- a P1/P2 fix requires a product or scope decision,
- reviewers disagree on whether a finding is in scope and the plan does not resolve it,
- required reviewer infrastructure is unavailable and the user has not waived it or directed opening the PR regardless,
- verification cannot run for reasons the agent cannot resolve.

Do not immediately return a convergence blocker merely because no PR exists. When the unresolved condition is review non-convergence, a recurring finding/failure family, or reviewer scope disagreement, mark it as a pre-PR `REVIEW_ESCAPE`. Assign a stable consultation identifier to the distinct failure family and affected scope on the fixed artifact, comparison range, and complete fingerprint, then require exactly one bounded, read-only, independent external consultation through the harness's configured consult/council surface before returning control. Record the identifier, packet, and final disposition. The one-consult budget belongs to that distinct family/scope disagreement: never consult again for the same unresolved identifier, and never use renamed or reworded findings to restart its budget. A materially separate later failure-family/scope identifier may receive its own one consultation whether discovered pre-PR, during an authorized adversarial pass, or from later PR feedback. This route is available for a candidate branch/diff whether or not a PR exists. It is advisory only: it may not edit files, apply fixes, become implementation authority, or route implementation through another persona.

The consultation packet must name its identifier and the unresolved finding/failure family or scope disagreement; the fixed artifact, comparison range, and complete fingerprint; prior fix attempts and the reviewer disagreement; verification evidence; and one narrow arbitration question. Ask the consultation to recommend exactly one disposition:

- reject or reclassify the finding with evidence,
- authorize one further bounded adversarial fix/review pass within the accepted plan,
- revert, narrow, or defer the unstable slice,
- request a user/product/scope decision.

The coordinator must verify the consultation's evidence and consume the recorded disposition exactly once. A verified rejection or reclassification clears that escaped finding/failure family and permits the gate to continue without an adversarial pass; record the evidence and resulting scope/severity classification. A revert, narrow, or defer disposition follows that stated path under the normal scope rules. A user/product/scope-decision disposition stops for that decision. Only an explicit `authorize one further bounded adversarial fix/review pass` disposition starts the adversarial pass. If proposed rejection/reclassification evidence cannot be verified, the stated revert/narrow/defer cannot be completed within authority, or a requested decision remains unanswered, report that specific unresolved blocker rather than treating every non-authorization as convergence failure.

When and only when the consultation authorizes the further pass, the coordinating implementation authority may make one bounded fix attempt and run one adversarial applicable-reviewer-pair pass over the fixed candidate branch/diff and named failure family, before or after PR creation. If that pass finds an in-scope issue and fixes are applied, repeat the same adversarial reviewer-pair pass once after those fixes; do not consult again, restart the ordinary three-cycle budget, or review until clean. If the bounded adversarial pass remains unresolved, report the convergence blocker and the recommended smallest path. This generalized `REVIEW_ESCAPE` route reuses the run-plan adversarial escalation loop; actionable PR feedback remains another trigger, but a PR URL or PR feedback is never required for pre-PR convergence consultation.

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
- any pre-PR `REVIEW_ESCAPE` consultation packet, consult/council disposition, authorized adversarial pass, and final unresolved or cleared state,
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
- reviewer-tab cleanup result, including any preserved or unsuccessfully closed tab IDs,
- any remaining non-blocking out-of-scope follow-ups with evidence and tracking destination,
- `Next step: OPEN_PR_READY` when invoked from `run-plan`, so the caller continues to final verification, commit, push, PR creation, and local merge-readiness checking instead of concluding or waiting for a Codex thumbs-up.
