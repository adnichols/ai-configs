---
name: autoreview
description: Run a bounded pre-PR implementation review with the active harness's configured reviewer subagent, fix or disposition blocking findings, and stop instead of entering non-converging review loops. Use this before opening pull requests, after an implementation is complete, or inside run-plan; inside run-plan this gate hands back to PR creation rather than waiting for external approval.
---

# Autoreview

Use this skill to catch implementation issues that would otherwise appear during pull request review. It is a code-review-and-fix loop, not a plan review, not a general cleanup pass, and not the end of `run-plan`.

The gate passes when the active harness's configured reviewer subagent finds no unresolved in-scope P1/P2 findings. This is local review-agent consensus, not a requirement to wait for a PR bot comment, PR-hosted thumbs-up, `reviewDecision: APPROVED`, or any other external approval. P3 findings are non-blocking unless they are plan-required, verification-required, or regressions caused by this change; you are not required to fix optional polish merely because it is cheap.

**Explicit operator override:** PR creation and a clean review verdict are separate decisions. If the operator explicitly instructs the agent to open, create, or publish the PR regardless of review status or coverage, obey immediately and do not delay PR creation for another review attempt, missing reviewer coverage, an unusable review artifact, or unresolved review findings. Preserve the requested draft/ready state. Record the override and disclose the actual review status, incomplete coverage, infrastructure failures, and known unresolved findings in the PR body; never relabel the gate as clean or claim merge readiness.

When invoked from `run-plan`, a passing result means `OPEN_PR_READY`, not `DONE`. It is only a handoff after the caller has satisfied run-plan's implementation-stage PM review; base freshness may still be pending until final verification and the scoped commit make a safe rebase possible. Return the final gate status, artifact path, target branch/base context, caller-reported base freshness status or pending status, and any known rebase-triggered rerun requirement to the `run-plan` caller so it can rerun final verification if needed, complete base freshness safely, commit, push, open the PR, inspect the current PR snapshot for actionable feedback/mergeability, and complete once local merge-readiness consensus is proven. Do not tell the caller to wait for a bot or human approval after local review-agent consensus is clean.

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

When no plan is present, treat issues introduced by the current diff as in scope. You are not required to fix unrelated pre-existing issues; capture them as findings unless the user explicitly expands scope.

### What "out of scope" may not hide

A finding is in scope — regardless of whether the affected code predates this branch — when any of these hold:

- This diff creates, extends, or routes new inputs to a shared primitive (collector, rewriter, mapper, scanner, serializer, validator). That primitive's correctness across every input this diff can now feed it is in scope. "Not introduced by this branch" does not apply to a primitive whose reachable input domain this branch changed.
- The issue is a fail-closed/bail/reject path reachable by valid, schema-conformant input. Failing closed on valid input is an in-scope correctness/reliability regression, not a deferrable follow-up. "Fail-closed" justifies deferral only when the closed path is reachable solely by invalid input.

A finding may be classified `OUT_OF_SCOPE_FOLLOW_UP` when evidence shows it is not required for the accepted current behavior, truthful verification, or a regression caused by this diff. Evidence may come from the product contract, supported-path definition, code reachability, or existing tests; you are not required to add implementation or tests solely to prove a scenario is out of scope.

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
- the initial changed files, including committed, staged, unstaged, and untracked changes.

When the scope crosses an exact contract the type system cannot fully verify or behavior distributed across production sites, add the executor's **integration-integrity record** to the packet: source of truth; producer/consumer or source-search-backed operation inventory; dependent docs/examples; declared exhaustive-by-site, exhaustive-by-family, or justified-representative scope; required cross-boundary/production-path proof; and reconciliation status. Do not invent an inventory when neither trigger applies; record the source-search basis for that conclusion instead. The reviewer validates the supplied evidence and cited searches read-only; it never becomes the inventory owner.

Also import or reconstruct the unified review-cycle ledger before launching any reviewer:

- When called by `run-plan`, require the caller's ledger and preserve its cycle numbers.
- When invoked independently, inspect current run notes and durable review artifacts for usable implementation-review passes over this scoped change. Equivalent runtime-native/pre-PR evidence over the same unchanged diff counts once; each later materially new reviewer pass counts as another cycle.
- Record completed cycles, the diff/fix that triggered each one, verdicts, and remaining budget in the autoreview artifact. If prior review evidence exists but the consumed budget cannot be determined safely, stop for clarification rather than assuming zero.
- If no cycle remains, do not launch reviewers. Return the convergence/review-budget outcome and smallest next decision exactly as required by the global policy, regardless of whether a PR exists.

Use this scope baseline and ledger for every slice, triage decision, fix, and rereview. A later finding may expose a concrete reachable path within the baseline, but it may not silently widen the accepted behavior or ownership boundary.

### 2. Run the active-harness reviewer

Run exactly one bounded, read-only `reviewer` subagent pass for every review cycle. This replaces the former Codex-primary and conditional-Claude dual-review policy, including for high-risk changes. Give the reviewer a compact packet with the plan or scope, base/comparison range, changed files, diff summary, verification already run, touched surfaces, and the specific failure families to inspect.

Use the native subagent mechanism for the current harness:

- **Pi:** invoke the repository-owned `reviewer` via `Agent`; it is `openai-codex/gpt-5.6-terra` at medium reasoning effort.
- **Claude Code:** invoke the repository-owned `reviewer` subagent; it is `claude-sonnet-5` at high effort.
- **OpenCode:** invoke the configured `reviewer` subagent; it is `cliproxyapi/gpt-5.6-terra` at medium reasoning effort.

#### Candidate visibility contract (mandatory)

Required read-only reviewers must review the candidate in **whatever worktree state exists**: committed, staged, unstaged, untracked, clean, dirty, detached, or isolated. Worktree state is review provenance, not a gate. A reviewer must render findings whenever the candidate code is visible.

**Pi launch rule:** before spending a model call, run the installed deterministic review-transport probe when available and fail closed if it reports incompatible effective isolation, planner/reviewer profile, or target-checkout handling. The `Agent` call **must omit the `isolation` property entirely**. Never set `isolation: "worktree"` for an autoreview reviewer. Before submitting the tool call, inspect its arguments and remove the property if present. The live checkout naturally exposes staged, unstaged, and untracked edits. `TARGET_CHECKOUT` remains a safety fallback only when the harness itself isolates despite the omitted property; it is not permission for the coordinator to request isolation.

The workflow must remain resilient if the harness isolates anyway:

- Put `TARGET_CHECKOUT: <absolute path>` in every reviewer packet, plus the coordinator's `HEAD` and `git status --short` snapshot and the changed/untracked path list.
- If launch CWD differs from `TARGET_CHECKOUT`, the reviewer must inspect the target directly with path-qualified reads and commands such as `git -C <target> ...`. A temporary or isolated launch CWD is never by itself a review failure.
- If the target checkout is unavailable but the launch checkout contains the requested commit/range, review that visible code and disclose any staged/unstaged/untracked content that could not be examined. Do not refuse to review the committed candidate on a cleanliness technicality.
- In Pi, use this launch shape. The absence of an `isolation` property is mandatory:

```javascript
const review = Agent({
  subagent_type: "reviewer",
  description: "Pre-PR implementation review",
  prompt: "<bounded review packet>",
  // REQUIRED: launch from the current checkout.
  // Cursor Grok/Composer: always background + join (bridge also forces background).
  run_in_background: true,
});
const verdict = get_subagent_result({
  agent_id: review.agent_id ?? review.id,
  wait: true,
});
```

On non-Cursor parents, foreground `Agent` without `run_in_background` remains acceptable. On Cursor Grok or Composer, background + join is required: foreground bridged `Agent` shares the parent MCP CallTool abort signal and can be marked stopped with a false "STOPPED BY THE USER" label while the parent turn dies with empty `Operation aborted`.

- Before accepting a verdict, the parent must confirm what content the reviewer actually inspected. For a dirty candidate, valid evidence is either `REVIEW_ROOT` pointing at the target checkout or a supplied patch/diff that covers the listed staged, unstaged, and untracked paths.
- Do not discard an otherwise valid review because it ran from `/tmp`, an isolated checkout, a detached HEAD, or a clean/dirty worktree. If dirty content was omitted, keep the findings over the visible committed candidate and run at most one targeted follow-up with `TARGET_CHECKOUT` or an explicit patch for the missing paths; do not label the completed visible-code review an infrastructure failure.
- Require the reviewer to return a short provenance block: launch `CWD`, `REVIEW_ROOT`, `HEAD`, `git status --short` (or `EMPTY`), `REVIEW_SOURCE`, and any unavailable candidate content.

Do not launch Codex or Claude Code as a separate review leg, and do not use Herdr as the transport for this **autoreview code-review** gate. A delivery run separately performs its selected profile's plan-completeness review after autoreview: OMP Lite uses the request-bound `@completeness` envelope from `xai/grok-4.5:high`, while Pi Full uses the visible labeled-tab Pi/Grok reviewer. Neither replaces this gate. The reviewer is static inspection only: it must not edit files or run tests, builds, linters, typechecks, benchmarks, verification scripts, or other executable checks. The coordinating agent exclusively owns verification and fixes. If the configured reviewer is unavailable, report `REVIEW_INFRASTRUCTURE_FAILURE` unless the user waives the gate or directs opening the PR regardless.

For every quality reviewer, use bounded scope and bounded exploration. Give each reviewer a concrete review packet: plan scope, changed files, diff summary, verification results, named touched surfaces, and the specific failure families to check. Tool outputs should be narrow: prefer exact file reads with offsets/limits and `rg -n` on changed files over repo-wide dumps. Do not use parent-side `max_turns` as the primary bounding mechanism for reviewer completion; bound the assigned scope instead.

If any reviewer cannot complete the assigned scope, it must return `VERDICT: REVIEW_INCOMPLETE_RERUN_NEEDED` with completed checks, remaining checks, and the exact recommended follow-up slice. The parent may run at most one narrowed follow-up for that reviewer in that cycle. If that follow-up is still incomplete or unusable, stop with a review-budget blocker or ask the user to waive/narrow the gate; do not keep launching slices.

Split a review only when the diff has more than 20 changed files, more than 2000 diff lines, or clearly independent product surfaces that one bounded slice cannot review. Use at most two slices per reviewer in the initial cycle, chosen by concrete surface/risk. Do not split a small or medium diff merely to get more opinions, and do not create generic failure-family slices unless the diff actually touches those failure families.

Each reviewer slice must use the same severity, scope, budget, and verdict format. The parent synthesizes all slice results; do not ask one subagent to deeply inspect every slice and synthesize the whole PR.

Use this prompt shape for each reviewer:

```text
Read-only pre-PR implementation review. Do not edit files.
Do not run or invoke tests, test suites, builds, linters, typechecks, benchmarks, verification scripts, validation commands, or any other executable checks intended to validate behavior. Inspect test code and the caller-supplied verification results only; the calling/coordinating agent exclusively owns test and verification execution. Read-only inspection commands such as git diff, rg, and file reads are allowed.

Reviewer: <active-harness reviewer subagent>
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

TARGET_CHECKOUT: <absolute path to the candidate checkout>
COORDINATOR_HEAD: <short sha>
COORDINATOR_STATUS_SHORT: <git status --short one line, semicolon-separated, or EMPTY>
Review committed, staged, unstaged, and untracked changes visible at `TARGET_CHECKOUT`. If your launch CWD differs, inspect `TARGET_CHECKOUT` directly with path-qualified reads and `git -C`; do not refuse the review because of the launch directory or worktree state. If some requested content is unavailable, still review all visible code and disclose the missing portion under `Not examined:`.

Provenance (required at the top of your reply for every successful or incomplete review):
- CWD: <absolute launch cwd>
- REVIEW_ROOT: <absolute checkout or artifact path actually reviewed>
- HEAD: <short sha>
- STATUS_SHORT: <git status --short one line, semicolon-separated, or EMPTY>
- REVIEW_SOURCE: <target-live-worktree | launch-checkout | supplied-diff>
Treat clean, dirty, staged, unstaged, untracked, detached, and isolated states as valid review inputs. None is grounds for `REVIEW_INFRASTRUCTURE_FAILURE` by itself.

Completion contract for every reviewer: stay within the assigned scope and review budget. Use at most the tool budget in the review instructions; do not broaden into unrelated whole-product review. Return a final verdict even when coverage is incomplete. If the assigned scope is incomplete, return `VERDICT: REVIEW_INCOMPLETE_RERUN_NEEDED` with completed checks, remaining checks, and the exact single follow-up slice the parent should run next.

Report all known in-scope P1/P2 failure families in the initial pass. Detail at most the five highest-impact findings. If more known blockers remain, include the overflow count and name each remaining failure family; do not withhold known blockers to reveal them one per later cycle.

Classify every finding with:
- Severity: P1, P2, or P3
- Scope: IN_PLAN, PLAN_PREREQUISITE, REGRESSION_FROM_THIS_DIFF, OUT_OF_SCOPE_FOLLOW_UP, or QUESTION

Every in-scope P1/P2 finding blocks a clean ready-for-PR verdict until it is fixed, rejected as a false positive with evidence, or reclassified as a true out-of-scope follow-up with evidence and a tracking destination. P3 findings block only when they are plan-required, verification-required, or regression-caused; otherwise return them as non-blocking follow-ups.

For a blocking P1/P2 finding, evidence must include the triggering input or state, reachable path, observable impact, and relationship to this diff. For a claim that depends on framework, library, CLI, protocol, or platform behavior, cite authoritative documentation, types, schemas, or source for the relevant version.

Recommend the smallest correct fix at the existing ownership boundary. When the correct fix would require a new protocol, config, storage format, migration, public API or contract, release process, ownership move, or unrelated refactor, report that and flag the decision it needs rather than silently assuming that expansion.

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
- exact-contract evidence: the cited source of truth, actual producer-to-consumer boundary, dependent docs/examples, and post-change stale-reference reconciliation
- distributed-behavior evidence: whether the source-search-backed call-site inventory is reconciled at the declared scope and whether every required path has meaningful dimensions; helpers, middleware, wrappers, and event-existence tests are not completion proof by themselves
- contractual documented CLI forms executed through the actual parser rather than only asserted in help text or documentation
- sibling instances of any discovered failure pattern, in this diff and the inverse direction of any boundary it touches — enumerate the family, not just the first instance

Return exactly one verdict:
- VERDICT: FINDINGS_TO_RESOLVE
- VERDICT: PASS
- VERDICT: BLOCKED_BY_QUESTION
- VERDICT: REVIEW_INCOMPLETE_RERUN_NEEDED
- VERDICT: REVIEW_INFRASTRUCTURE_FAILURE

A `PASS` verdict must include a `Not examined:` line disclosing what the review did not exercise (`Not examined: none` when the full surface was covered). Legacy green verdicts (`CLEAN_FOR_PR`, `CLEAN`) are still accepted as green when read.

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
- Document `OUT_OF_SCOPE_FOLLOW_UP` findings with evidence and a tracking destination; you are not required to add code or tests to dispose of a merely-discovered finding.
- Verify reviewer claims against the code before changing anything; false positives should be recorded as rejected with evidence.
- Apply the fix-shape governor before editing: keep the fix at the same ownership boundary, or stop before protocol, config, storage, migration, public API, release process, ownership, or unrelated-refactor expansion and request the smallest necessary decision.

### 4. Fix, verify, and run one targeted rereview

After applying any in-scope fix—and only because that fix changed verification-relevant state:

1. Run the smallest meaningful targeted tests for the touched code.
2. Rerun only plan-required verification invalidated by the fix. Reuse and record still-valid passing results instead of rerunning unchanged checks merely because a review cycle completed.
3. Rerun the same active-harness reviewer once against only the changed files, prior blocking findings, and resulting edits, not as a fresh whole-diff hunt for unrelated new issues.
4. Allow a third total review cycle only when that targeted rereview identifies a new concrete blocker introduced or exposed by the fix. Otherwise stop after the targeted rereview with either `PASS` or a convergence/scope blocker. Count this budget across the scoped change, not from the moment this skill was invoked: creating a PR does not reset, extend, reduce, or otherwise alter the limit, and a post-PR `REVIEW_ESCAPE` consumes an otherwise permitted remaining cycle rather than creating a new one.

Absent an explicit operator instruction to open the PR regardless, do not stop while any applicable reviewer has an unresolved blocking in-scope P1/P2 finding and do not open or proceed to a PR with those findings unresolved. An explicit operator override ends this prohibition: open the PR as directed, disclose the non-clean review state, and do not represent it as `PASS` or merge-ready. If invoked from `run-plan`, do not end the workflow at `PASS`; hand control back for final verification, commit, push, PR creation, and local merge-readiness checking. The pre-PR gate must not require a later bot thumbs-up after its local review is clean.

The ordinary local review budget is exhausted when any of these is true:

- two fix attempts do not resolve the same finding or same failure family,
- a narrow/optional component keeps producing new edge-case findings after two cycles, indicating it should be reverted, deferred, or redesigned instead of patched through review,
- three total review cycles have run for the scoped change across pre-PR and post-PR review; the third cycle is permitted only for a new concrete blocker introduced or exposed by the prior fix, and PR existence never resets or changes this budget,
- a P1/P2 fix requires a product or scope decision,
- reviewers disagree on whether a finding is in scope and the plan does not resolve it,
- required reviewer infrastructure is unavailable and the user has not waived it or directed opening the PR regardless,
- verification cannot run for reasons the agent cannot resolve.

Do not immediately return a convergence blocker merely because no PR exists. When the unresolved condition is review non-convergence, a recurring finding/failure family, or reviewer scope disagreement, mark it as a pre-PR `REVIEW_ESCAPE`. Assign a stable consultation identifier to the distinct failure family and affected scope on the fixed artifact, comparison range, and complete fingerprint, then require exactly one bounded, read-only, independent external consultation through the harness's configured consultation surface before returning control. The configured Pi consultation surface is the `oracle` subagent, pinned by checked-in frontmatter to `openai-codex/gpt-5.6-sol` with high reasoning and invoked with `subagent_type: "oracle"`; it is the advisory consultation, not another review pass. Launch with only `subagent_type`, a short description, and the consultation packet — omit caller-side `model`, `thinking`, `reasoningEffort`, `inherit_context`, and `isolation` (`inherit_context: false` and `isolation: "worktree"` are workflow violations). Record the identifier, packet, and final disposition (`accepted` / `partially-accepted` / `rejected` / `escalated`) with why. The one-consult budget belongs to that distinct family/scope disagreement: never consult again for the same unresolved identifier, and never use renamed or reworded findings to restart its budget. A materially separate later failure-family/scope identifier may receive its own one consultation whether discovered pre-PR, during an authorized adversarial pass, or from later PR feedback. This route is available for a candidate branch/diff whether or not a PR exists. It is advisory only: it may not edit files, apply fixes, become implementation authority, or route implementation through another persona.

The consultation packet must name its identifier and the unresolved finding/failure family or scope disagreement; the fixed artifact, comparison range, and complete fingerprint; prior fix attempts and the reviewer disagreement; verification evidence; and one narrow arbitration question. Ask the consultation to recommend exactly one disposition:

- reject or reclassify the finding with evidence,
- authorize one further bounded adversarial fix/review pass within the accepted plan,
- revert, narrow, or defer the unstable slice,
- request a user/product/scope decision.

The coordinator must verify the consultation's evidence and consume the recorded disposition exactly once. A verified rejection or reclassification clears that escaped finding/failure family and permits the gate to continue without an adversarial pass; record the evidence and resulting scope/severity classification. A revert, narrow, or defer disposition follows that stated path under the normal scope rules. A user/product/scope-decision disposition stops for that decision. Only an explicit `authorize one further bounded adversarial fix/review pass` disposition starts the adversarial pass. If proposed rejection/reclassification evidence cannot be verified, the stated revert/narrow/defer cannot be completed within authority, or a requested decision remains unanswered, report that specific unresolved blocker rather than treating every non-authorization as convergence failure.

When and only when the consultation authorizes the further pass, the coordinating implementation authority may make one bounded fix attempt and run one adversarial active-harness reviewer pass over the fixed candidate branch/diff and named failure family, before or after PR creation. If that pass finds an in-scope issue and fixes are applied, repeat the same adversarial active-harness reviewer pass once after those fixes; do not consult again, restart the ordinary three-cycle budget, or review until clean. If the bounded adversarial pass remains unresolved, report the convergence blocker and the recommended smallest path. This generalized `REVIEW_ESCAPE` route reuses the run-plan adversarial escalation loop; actionable PR feedback remains another trigger, but a PR URL or PR feedback is never required for pre-PR convergence consultation.

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
- each review cycle's active-harness reviewer verdict and any reviewer-infrastructure failure or operator waiver,
- the triage table,
- fixes applied for blocking P1/P2 issues and any fixed P3 issues,
- verification commands and results after fixes,
- remaining out-of-scope follow-ups with evidence and tracking destination,
- any `REVIEW_INCOMPLETE_RERUN_NEEDED` handoff, the single allowed rerun slice, and whether the gate stopped for review budget,
- any pre-PR `REVIEW_ESCAPE` consultation packet, Oracle/consultation disposition, authorized adversarial pass, and final unresolved or cleared state,
- final gate result and whether it is `OPEN_PR_READY` for a caller such as `run-plan`, explicitly noting that no external thumbs-up is required beyond the clean local reviewer artifact.

If the repo has a different validation-artifact convention, use that convention and keep the same information.

## Passing result

The final summary must include:

- selected review surface: active-harness `reviewer` subagent,
- reviewer model and reasoning effort,
- `Reviewer verdict: PASS` (with its `Not examined:` disclosure) or equivalent no-unresolved-blocking-in-scope-P1/P2 result,
- base freshness context from the caller and any rebase-triggered rerun requirement,
- verification rerun after the last fix,
- artifact path,
- reviewer-result capture status and any infrastructure failure or operator waiver,
- any remaining non-blocking out-of-scope follow-ups with evidence and tracking destination,
- `Next step: OPEN_PR_READY` when invoked from `run-plan`, so the caller continues to final verification, commit, push, PR creation, and local merge-readiness checking instead of concluding or waiting for external approval.
