---
name: run-plan
description: Execute an existing implementation plan persistently through code changes, bounded scoped quality reviews, active-harness pre-PR review, runtime-specific completeness review, verification, commit, push, PR creation, and local merge-readiness consensus without expanding beyond the plan's stated scope.
---

# Run Plan

Use this skill when the user has a plan file and wants it implemented all the way to a pull request with the runtime's scoped quality-review gates, active-harness reviewer-subagent pre-PR review gate, and runtime-specific plan-completeness review, while preventing reviewer-driven scope creep.

## ADN execution discipline

On OMP, load the installed `adn-mode` skill before any other run-plan step and keep it active through closeout. `run-plan` owns the lifecycle, plan scope, runtime routing, review budgets, and PR closeout. `adn-mode` owns the applicable principles, playbook discipline, implementation style, and reply discipline. If the contracts conflict, follow `run-plan` for lifecycle and scope. Follow `adn-mode` for how the work is performed.

Do not load or emulate `adn-mode` on another harness. ADN is the OMP adaptation of poteto mode. Non-OMP runtimes continue with their native run-plan contracts.

When `.delivery/ledger.json` exists, read `runtime` and `workflowProfile` before applying runtime-specific instructions. `omp / omp-lite` keeps implementation, scoped review, and PM outcome review in the current `xai-oauth/grok-4.6:high` OMP session; use `openai-codex/gpt-5.6-terra:high` when correctness depends materially on technical judgment. It uses the request-bound `@completeness` envelope from `xai/grok-4.5:high`, produced by `delivery completion-review --prepare`; it does not require a dedicated Pi pane, Pi model-profile verification, Pi slash commands, or a Grok tab. `pi / pi-full` retains the dedicated implementation pane, planner-selected profile, and visible labeled-tab Grok completeness loop. Never convert an existing ledger between profiles.

The plan is the contract. Reviews can reveal adjacent problems, but they do not expand the contract unless the user explicitly approves that expansion.

PR authority is repository-bound. This workflow may create a PR only for the current task repository against its owner-approved integration remote. It must never create, reopen, update, comment on, or coordinate a PR against a third-party repository from a fork unless the operator explicitly authorizes that exact repository and action. If the plan depends on third-party source changes, keep them local/downstream, report the dependency, and stop for operator direction rather than treating the mandatory-PR step as upstream permission.

The executable contract ends at the PR-reviewable slice. Deployment, promotion, merge-dependent smoke checks, production observation, and rollback execution are post-merge delivery/operations work. They may remain documented obligations, but they never block committing, pushing, or creating the PR and they do not keep the run-plan lifecycle open after local merge readiness is established.

PR creation is not hostage to deployment. Never wait for preview, staging, canary, or production deployment evidence before opening the PR. Validate deployability pre-merge where practical through configuration checks, builds, dry runs, artifact inspection, or other non-deployment evidence, then disclose any pending post-merge delivery checks in the PR body.

PR creation is not hostage to testing or review coverage. If the operator explicitly says to open, create, or publish the PR regardless of verification or review status, open it without further testing or review delay. That one instruction overrides both remaining review gates — autoreview and completeness — plus verification. Preserve the requested draft/ready state and disclose the real verification and gate status, skipped or failing checks, missing coverage, infrastructure failures, and unresolved findings in the PR body. Do not claim passing verification, clean review consensus, or local merge readiness when it has not been established.

The active-harness reviewer pre-PR gate is not a terminal phase. Once implementation is complete, verification is passing, reviewer consensus says there are no unresolved blocking in-scope P1/P2 findings, and completeness has returned `VERDICT: COMPLETE` or an explicit operator waiver/override is recorded, the next mandatory action is to commit, push, and open the PR in this same scoped run. A "ready for PR" closeout without a PR URL is incomplete unless a concrete blocker prevented PR creation.

This skill is runtime-state-backed. A scoped plan run is not complete at PR creation; it remains active until the implementation has local merge-readiness consensus: final verification is passing, all applicable review agents agree by substance that there are no unresolved blocking in-scope findings, the branch is current enough to merge, the PR exists, and the latest PR snapshot has no actionable feedback already present. Do not wait for a PR-hosted Codex approval, thumbs-up, or any other explicit external approval after local review-agent consensus is clean. In Pi, back this with the goal extension as the durable run state, plus the `todo` tool's `create`/`update` actions and explicit working notes for phase progress. In Codex, back this with Codex goal/task state and the installed Codex prompts so the readiness obligation survives normal turn-to-turn execution. In Devin, back this with the `todo_write` task list and explicit working notes; keep the readiness obligations in the task list so they survive normal turn-to-turn execution.

## Invocation

```text
Use $run-plan to execute an explicit plan path or a slug resolvable by repo-local active plan guidance
```

Accept either a plan path or a slug. For a slug, resolve using repo-local active plan guidance; do not infer a markdown path.

## Non-Negotiable Rules

- Do not implement if the request is plan-only, review-only, or investigation-only.
- Never treat run-plan invocation, a fork remote, cross-repository dependency work, or normal PR authority as permission to interact with a third-party upstream PR. Exact operator permission naming the third-party repository and action is required.
- Do not run destructive git commands unless the user explicitly requested them.
- Do not let reviewer subagents edit files during review. Reviews are read-only.
- Do not ask reviewers to review the whole product for open-ended problems.
- Do not proceed past a blocked plan decision by silently choosing a larger scope.
- Complete the PR-reviewable promised slice before claiming local merge readiness: no required stubs, TODO behavior, dead-end surfaces, missing producer/consumer wiring, fake success, or verification that bypasses the real implementation.
- Do not treat deployment, promotion, merge-dependent smoke checks, production observation, or rollback execution as part of the PR-reviewable promised slice. Pending post-merge delivery work must be disclosed and handed off, never used to block PR creation.
- If the PR-reviewable outcome cannot be completed safely, stop and resize it to a smaller independently useful complete slice rather than shipping a partial skeleton.
- Do not create a PR until verification appropriate to the touched surfaces has run or a blocker is clearly reported, unless the operator explicitly instructs the agent to open the PR regardless of testing status. That explicit instruction is controlling: stop retrying or waiting on verification, open the PR, and disclose skipped, incomplete, unavailable, or failing checks without calling them passing.
- Verification convergence is budgeted. When the Verification Convergence Budget is exhausted and every residual failure classifies as inherited or infra/cosmetic with targeted verification green, opening the draft PR with disclosure and stopping on the ship/keep-fixing question is the required next action, not a policy violation.
- Do not create a PR until an implementation-stage PM review has checked the implemented outcome against the plan's product intent, a concrete blocker prevents that review, or the operator explicitly instructs the agent to open the PR regardless of review status.
- Do not create a PR until the active-harness reviewer-subagent pre-PR implementation review gate has passed with no unresolved blocking in-scope P1/P2 findings, or the operator explicitly instructs the agent to open the PR regardless. That explicit instruction is controlling: stop retrying review coverage, open the PR, and disclose the non-clean gate state without calling it approval.
- Do not create a PR until the runtime-specific completeness review has returned `VERDICT: COMPLETE` against the current plan and live worktree, or the operator explicitly instructs the agent to open the PR regardless. Completeness is a pre-PR gate for every run-plan, not only Herdr delivery and not only local merge-readiness. Do not arm delivery just to run it. When a delivery ledger already exists, use that runtime's completion-review transport. When no ledger exists, load the `completeness` skill and use its standalone packet. OMP Lite accepts only a current request-bound `@completeness` envelope from `xai/grok-4.5:high`; Pi Full with a ledger requires the visible labeled-tab reviewer running `xai/grok-4.5:high`; Devin uses the standalone packet reviewed by the repository-owned `completeness` subagent profile (`~/.config/devin/agents/completeness.md`) launched via `run_subagent`. Fix every in-plan finding and request rereview; the driving agent owns fixes and verification.
- Do not stop after the reviewer-subagent pre-PR gate passes; that gate returns `OPEN_PR_READY`. Next run completeness, unless the operator has already instructed opening the PR regardless. Only after both gates pass — or an explicit operator override is recorded — continue through final verification, commit, push, PR creation, and monitoring.
- Do not create a PR until base freshness and mergeability risk have been checked against the target branch; fetch, rebase safely, and rerun invalidated verification/reviews before PR creation when the branch is stale.
- Never delay PR creation for deployment or post-merge operational evidence, even when an older plan places that evidence in a phase or completion checklist. Reclassify it as a non-blocking delivery obligation and preserve it in the PR body/plan deviation log.
- Do not mark the active run state complete just because the implementation PR exists.
- Do not mark the active run state complete until local merge-readiness consensus is established: final verification passed, applicable review agents agree by substance that there are no unresolved blocking in-scope findings, scoped PR feedback already present has been addressed, and the PR is mergeable with the destination branch or has no known merge conflict when GitHub cannot provide a final mergeability value.
- Treat actionable PR feedback that is already present after local reviews as a review escape: the earlier review cycle missed something, so the next local review cycle must become scope-bound adversarial review instead of only patching the commented issue.
- Do not wait for slow or absent PR feedback, a Codex PR thumbs-up, `APPROVED` reviewDecision, or any other explicit external approval once local review-agent consensus and merge-readiness evidence are clean.
- On Heddle (detect `.agents/skills/heddle-permanent-docs/SKILL.md`, `docs/DEV_DOCUMENTATION_ARCHIVE.md`, or `changelog/unreleased/README.md`), do not start scoped quality review, implementation-stage PM review, autoreview, or completeness until permanent-document disposition and any required permanent-doc capture are recorded per `heddle-permanent-docs`. Do not open a PR until that disposition is still true, claimed paths are present for path-bearing dispositions, and the PR body includes the Permanent documentation section—unless the operator explicitly waives permanent docs with disclosure. Non-Heddle repos are unchanged unless a repo-local `*-permanent-docs` skill exists.

## Scope Contract

Before editing, read the full plan and extract:

- Goal and user-visible outcome
- Explicit in-scope files, surfaces, phases, and acceptance criteria
- The PR-reviewable implementation phases versus any deployment, promotion, merge-dependent validation, production observation, or rollback steps that must be reclassified as non-blocking post-merge delivery/operations work
- Explicit out-of-scope items
- Required tests and verification commands
- Base branch and PR target, if stated
- Open questions, unresolved decisions, or readiness status

Stop before implementation if:

- the plan is not execution-ready,
- a `pi-full` delivery ledger exists and is not being entered from the dedicated implementation pane with the recorded runtime profile—or it lacks a current explicit readiness request, independent Sol-medium planner verdict for the exact plan, automatic workflow authorization, and successful implementation-agent launch record. The planner recommends `openai-codex/gpt-5.6-luna` at xhigh by default and `openai-codex/gpt-5.6-terra` at high when correctness depends materially on technical judgment; unresolved consequential choices can escalate to Oracle, but Sol is not used for implementation. A deliberate manual model/reasoning choice is allowed when recorded with a reason. `delivery stage EXECUTION_READY` performs the normal authorization and launch without another operator approval pause. Run `delivery verify-implementation-profile` before code work; if this already-recorded pane was deliberately switched, use `delivery verify-implementation-profile --adopt-current-runtime --reason "..."`. OMP Lite deliberately remains in the coordinating OMP session and does not launch a dedicated implementation pane. Never treat readiness metadata, a generic Doct comment/action, or a quiet listener as readiness authorization,
- acceptance criteria are vague enough that scope cannot be enforced,
- required user decisions remain unresolved,
- the current branch contains unrelated dirty changes that make isolation unsafe,
- a required runtime-native review gate is unavailable and the user has not waived it or explicitly directed opening the PR regardless. This means the active-harness reviewer-subagent infrastructure, the `autoreview` skill, and the runtime-specific completeness review (the `completeness` skill's standalone packet, or the delivery completion-review transport when a ledger already exists).

## Oracle decision support

In Pi Full, load `oracle-consultation` and invoke Oracle proactively when the reviewed plan plus targeted evidence still leave one consequential implementation choice unresolved. In Devin, use the `oracle-consultation` skill's Devin launch contract (the `oracle` subagent profile via `run_subagent`) the same way. Consult before locking the choice, changing a public contract, or escalating. Record the verified disposition in the coverage ledger and plan decisions/deviations log when it changes the execution path.

Oracle cannot authorize scope expansion, make a product choice, or replace readiness, PM, reviewer, completeness, or test evidence. OMP Lite has no Oracle requirement; ask the operator when repository evidence cannot settle a consequential product or scope decision.

## Integration-integrity record

When the plan or implementation triggers exact-contract or distributed-production work, load `integration-integrity` before the first dependent edit and keep its record in the coverage ledger. Map contract or coverage review findings to the relevant plan acceptance criterion, phase, and record row before editing.

Do not create a negative record when no trigger applies. Completion requires the evidence defined by `integration-integrity`, not reviewer prose or helper-only tests.

## Scope Classification

Scope follows the canonical Scope section in `planning-workflow`: understanding and protecting existing behavior around your change is the cost of the change, while making something new happen needs its own plan and, when product-changing, owner approval. The disposition rule decides each finding:

> **A regression this change causes is in scope wherever it appears. When this change routes new valid inputs into a shared primitive or expands its reachable domain, correctness across that newly reachable domain is part of this change even where defects predate it. A defect this change merely discovers — and does not cause or newly expose — is a finding: capture it and keep going.**

Classify every requested change and every reviewer finding:

- `IN_PLAN`: directly required by the plan's acceptance criteria, phase work, or verification.
- `PLAN_PREREQUISITE`: not named in the plan, but the plan cannot work or verify without it.
- `REGRESSION_FROM_THIS_DIFF`: caused or newly exposed by the current implementation, including correctness across a domain this change newly makes reachable; fix it before PR.
- `OUT_OF_SCOPE_FOLLOW_UP`: a defect this change merely discovers and does not cause or newly expose; capture it as a finding with its tracking destination and keep going.
- `QUESTION`: requires user/product decision before implementation.

Fix `IN_PLAN`, `PLAN_PREREQUISITE`, and `REGRESSION_FROM_THIS_DIFF`. Treat BDD gaps, verification gaps, implicit-only coverage, misleading evidence, or any finding tied to a plan acceptance criterion as in-scope until proven otherwise. Actual environment deployment and post-merge observation are not implementation findings; preserve them as delivery obligations without making them PR gates.

## Evidence Placement

Evidence lives in the coverage ledger (working notes), the plan file's progress and deviation sections, and ultimately the PR body. Do not create repository commits whose sole content is recording verification, certification, review, or deferral status; fold plan-progress updates into at most one bookkeeping commit per completed phase. Never commit a "debt" record for a failure the disposition rule makes in scope — fix it or report the blocker. A run's commit history should read as the change, not as a diary of the process that produced it.

## Unified Review-Cycle Budget

The three-cycle implementation-review limit is global to the scoped change, not to a workflow stage or PR state.

- Count one cycle when the applicable implementation reviewers inspect a materially current diff and return usable verdicts. Runtime-native scoped review and a reused pre-PR gate over the same unchanged diff are one cycle, not two; a later materially new review pass is another cycle.
- The normal budget is the initial cycle plus one targeted rereview after fixes. A third total cycle is allowed only when the preceding fix introduced or exposed a new concrete blocker.
- Creating a PR does not reset, extend, reduce, or otherwise change this budget. The same rule applies before and after PR creation.
- Actionable PR feedback is evidence to triage, not automatic permission for an extra review. A `REVIEW_ESCAPE` uses an ordinary adversarial/targeted cycle only when one remains and the normal third-cycle condition is satisfied. When the ordinary three-cycle budget is exhausted, route the stable `REVIEW_ESCAPE` failure-family/scope identifier through the one-per-family consultation section before reporting convergence. Conversely, the absence of a PR does not prevent an otherwise permitted ordinary cycle or consultation route.
- Direct feedback fixes and targeted verification do not themselves consume a review cycle; the subsequent reviewer pass does. Track cycle number, triggering diff/fix, verdicts, and remaining budget in the coverage ledger.
- When the ordinary budget is exhausted, do not launch a renamed, post-PR, “final clean,” adversarial, or alternate-reviewer cycle to continue review. No fourth or renamed pass is allowed except the single explicitly consultation-authorized bounded pass and its existing one pass-after-fixes allowance. After the applicable one-per-stable-family consultation route is consumed without clearing the risk or authorizing that exception, report the convergence/review-budget blocker and request the smallest user decision (accept disclosed residual review risk, narrow/revert the unstable slice, or revise scope). PR existence must not influence consultation eligibility or authorize any extra pass.

Apply the disposition rule in the Scope Classification section to each finding: a regression this change causes or newly exposes, including newly reachable-domain correctness, is in scope; a defect this change merely discovers is captured as a finding and does not block.

## Strict-suite preflight and bounded failure inventory

Before the repository's full strict suite, discover and run any repo-defined high-signal partitions in this order when present: predecessor/upgrade compatibility; hygiene/format/static checks; convergence/locking/concurrency; and profile/transport/configuration. Do not invent partitions a repository does not expose. Record each gate, command, base/head SHA, and result in the coverage ledger before the full suite.

For a long suite with multiple failures, allow exactly one bounded no-fail-fast inventory pass per delivery head. Cap detailed distinct signatures at five by default (repo guidance may set another explicit cap), count overflow families, and suppress repeated notifications for a signature already recorded. Reproduce one representative from each material family narrowly. Classification as inherited requires the same signature reproduced at `git merge-base <base> HEAD` or the target branch, not age or intuition. Record functional versus infra/cosmetic classification and terminal disposition; never serially reveal one known family per rerun.

## Owned scratch contract

Use only a repository-declared scratch root or runner-provided temporary root. Every run-owned root must contain an ownership marker with run ID, creator PID/process identity when available, and creation time. Before cleanup, report file count and bytes plus owner/lock diagnostics. Remove owned scratch on green. Preserve it on red with the exact inspection and cleanup command. Refuse deletion when the marker is missing, mismatched, or another live owner/lock is present; never clean broad shared temp paths by pattern.

## Verification Convergence Budget

Full-suite verification and certification gates get a convergence budget, exactly as reviews do. Track attempts per delivery head in the coverage ledger: gate name, attempt number, failure signature, introduced/inherited evidence, functional/infra classification, notification count, scratch ownership, and whether the root cause is new or a repeat.

- A repeated full-gate attempt is justified only by a new distinct root cause — a failure this attempt will address that previous attempts did not. Rerunning to "get a clean one" is not a root cause.
- Three full attempts at the same gate without a new distinct root cause exhaust the budget, or 90 minutes of attributable gate time on one delivery head — whichever comes first. Record the gate's normal green-run duration in the ledger so a legitimately slow, still-progressing gate is not misread as a loop; repo-local guidance may override these thresholds. When the budget is exhausted, the loop is over: classify every residual failure and dispose of it as below. Do not launch another attempt, a renamed certification, or a "final clean" serial lap to avoid the classification.

Classify each residual failure on two axes, with evidence:

- **Introduced** (caused or newly exposed by this branch) vs. **inherited** (reproducible at the merge-base or on the target branch). Inherited requires reproduction evidence at the merge-base or on the target branch, not inference from the failure's age — and the disposition rule still governs: a failure in a domain this change newly makes reachable is introduced regardless of where the defect predates the branch.
- **Functional** (customer-visible behavior wrong) vs. **infra/cosmetic** (harness contention, environment flake, rendering deltas within an approved tolerance). Where no approved tolerance exists, the delta is not classifiable as cosmetic — it is a `QUESTION`.

**Flake disposition:** a full-run failure is infrastructure-flake evidence, not a delivery blocker, when the failing tests pass in isolation or serial rerun and the failure point moves between attempts. Certify on the serial/isolated evidence and disclose the parallel-run state in the PR body. You are never required to keep spending budget chasing a clean parallel run.

Disposition when the budget is exhausted:

- Every residual is inherited or infra/cosmetic (with the evidence above), and targeted verification of the changed surfaces is green → **open the PR as a draft** with the two-axis classification and evidence in the PR body, then mark the run state blocked-on-operator with the ship/keep-fixing question. This is the terminal state for unattended runs: the finished branch is preserved and disclosed, and converting the draft to ready is an operator decision. Open it ready-for-review instead only when the operator has explicitly authorized that for this run or repo guidance documents an exception path.
- Any residual is introduced or functional → it is in scope: fix it, or stop with a blocker naming it.
- The classification itself needs a product judgment (for example, a rendering delta with no approved tolerance) → that is a `QUESTION` for the operator, presented with the two-axis classification. Never resolve it by choosing maximal strictness on the operator's behalf.

An operator ship or stop directive ends this budget immediately wherever it stands: discard queued and in-flight gate attempts, open the PR in the state the operator named (ready by default when they said "ship"), and disclose the truthful gate state.

## Workflow

### 0. Optional Supervision

Do **not** launch a supervisor as part of `run-plan`. Supervision is opt-in: only when the operator explicitly asks to supervise this run, follow `skills/supervise/SKILL.md`. Otherwise, continue without supervisor checkpoints, phase pings, or expansion-log entries.

### 0b. Delivery ledger and visible completeness review

Use the delivery ledger only when delivery was explicitly armed for this run
(an active `.delivery/ledger.json` created by `/delivery`, `delivery arm`,
`delivery spawn`, or the operator saying "arm our delivery workflow").
Do not initialize a delivery ledger merely because the `delivery` CLI
or `delivery-run` skill is available. A generic run-plan, `/prewalk`,
`execute`, or other execution trigger does not arm delivery. Never run
`delivery init`, `delivery bootstrap`, or `delivery arm` from this skill.
If `/prewalk` is armed, implement in this session; prewalk and delivery
are mutually exclusive.

If no ledger exists, implement here. Prewalk may switch models at the
first `edit`/`write`. Skip the rest of this subsection.

When a ledger is already active, keep it current as soft progress tracking.
The implementation authorization remains mandatory before code work.
Completeness review is mandatory before PR creation on every run-plan. In a
`pi-full` Herdr delivery worktree, use the visible labeled-tab Pi/Grok
reviewer. In an `omp-lite` run, stay in the coordinating OMP session and use
request-bound packet acceptance. With no ledger, use `skill://completeness`
standalone. Other ledger evidence remains advisory.

```bash
# Only when `.delivery/ledger.json` already exists. Do not create one here.
delivery set --issue <KEY> --retarget-id         # attach Linear later when it exists
# Pi Full: this authorizes and launches the dedicated Herdr implementation agent.
# OMP Lite: this records authorization and remains in the coordinating OMP session.
delivery stage EXECUTION_READY
# Use `delivery stage EXECUTION_READY --hold` only for an explicit pause or real external dependency.
# Pi Full only, in the newly launched implementation agent:
delivery verify-implementation-profile
# If this recorded implementation pane was deliberately switched to another model:
delivery verify-implementation-profile --adopt-current-runtime --reason "manual choice for this run"
delivery stage IMPLEMENTING
delivery stage SCOPED_REVIEW|IMPL_PM_OUTCOME|AUTOREVIEW|COMPLETENESS_REVIEW|PR_OPEN|MERGE_READY|DONE
# Before PR creation:
delivery stage COMPLETENESS_REVIEW
# Pi Full:
delivery completion-review
delivery completion-review --rerun  # after in-plan fixes, until VERDICT: COMPLETE
delivery completion-review --accept
# OMP Lite:
delivery completion-review --prepare --reviewer-identity omp-completeness-grok-4.5-high
delivery completion-review --accept --artifact <artifact> --response-id <id>
delivery record <key> --status pass|skip|gap|na --artifact <path> --summary "..."
delivery check -v   # advisories only; always exit 0
```

Missing ledger quality evidence must not block run-plan. Do not stop solely because `delivery check` reports gaps. Missing, stale, or invalid readiness authorization is different: it stops pre-code execution **when a delivery ledger is already active**. When a ledger is already active, Pi Full additionally requires its independent Sol-medium plan review, Luna/Terra implementation-profile recommendation, automatic workflow authorization, dedicated-agent launch, recorded Herdr-pane identity, and live recorded-runtime evidence. A Pi Full model mismatch is recoverable: switch to the recorded model, or deliberately adopt the current model in the same implementation pane with `--adopt-current-runtime --reason`. Retry a failed Pi Full launch with `delivery start-implementation`; delivery first reconciles an expected live Pi agent in the recorded pane. OMP Lite has no dedicated-agent launch or implementation-profile requirement and intentionally plans and implements in one coordinating session. For any delivery run, a missing validated completeness result after implementation prevents a local merge-readiness claim unless the operator explicitly waives it: Pi Full uses the visible labeled-tab review; OMP Lite uses the exact request-bound acceptance envelope. If material Doct feedback arrives before code changes, update the plan, run `delivery revoke-implementation-approval --reason "material plan feedback"`, and return to browser review for a fresh readiness request.

When the scoped run reaches local merge-readiness or a durable stop (DONE/blocked handoff), best-effort log a process reflection outside the worktree:

```bash
delivery reflect --trigger end-of-run --outcome done|pr-opened|blocked \
  --friction "..." --rework "..." --improvement "..." --mark-done
```

This appends to `~/.pi/DELIVERY_REFLECTIONS.md` and `~/.pi/delivery-reflections.jsonl` (like vent). Skip only when there is nothing process-shaped to capture; never hard-block PR completion on reflection.

### 1. Establish Run State

1. Check whether a compatible run-plan state is already active in the available runtime tracking surface.
2. If no compatible run state is active, create an explicit lifecycle task set before implementation. In Pi, use the `todo` tool's `create` and `update` actions, keeping exactly one task `in_progress` at a time. In Codex, use Codex goal/task state. Include a final post-PR readiness task that cannot be marked complete until all completion criteria are satisfied.
3. The objective must require both:
   - executing every unfinished PR-reviewable phase of the specified plan through implementation, verification, implementation-stage PM review, runtime-native scoped review, the active-harness reviewer-subagent pre-PR review with no unresolved blocking in-scope P1/P2 findings or an explicit recorded waiver, the runtime-specific completeness review to `VERDICT: COMPLETE` or an explicit waiver, base freshness checks, commit, push, and PR creation, while preserving deployment/post-merge work as non-blocking delivery obligations;
   - checking the PR after creation for existing actionable feedback and mergeability evidence, without waiting for a Codex thumbs-up or other external approval after local review-agent consensus is clean.
4. If an active run state already exists and it is compatible with this scoped plan run, continue under it and state the compatibility in working notes.
5. If an active run state exists but conflicts with this scoped plan run, stop and ask the user whether to finish, block, or abandon the existing run before replacing its task set.

Use this objective shape:

```text
Execute <plan path> through the full scoped run-plan lifecycle without expanding beyond the plan contract: establish scope, align any registered Doct plan state, implement every unfinished PR-reviewable in-scope phase, preserve deployment/promotion/post-merge validation as non-blocking delivery obligations, run required targeted and final pre-merge verification, complete implementation-stage PM review, complete runtime-native scoped quality review, complete the active-harness reviewer-subagent pre-PR implementation review with no unresolved blocking in-scope P1/P2 findings or an explicit recorded waiver, complete the runtime-specific completeness review to `VERDICT: COMPLETE` or an explicit recorded waiver, check base freshness, commit only scoped changes, push, open a PR against <target branch or the plan's/repository's normal integration branch>, inspect the PR for existing actionable feedback and mergeability evidence, and finish only when local merge-readiness consensus is satisfied. Do not stop at implementation complete, review clean, `OPEN_PR_READY`, or PR created. Do not mark complete until fresh evidence proves all actionable PR feedback already present has been addressed, any feedback-triggered code changes have rerun required verification and review gates, the branch is current or safely rebased as needed, and applicable review agents agree by substance that the current change is ready to merge locally. Do not wait for slow or absent external feedback, a Codex PR thumbs-up, `APPROVED` reviewDecision, or another explicit approval after local review-agent consensus is clean.
```

Runtime state expectation: keep the task state and working notes current with the plan path, PR URL once known, target branch, latest verification status, latest reviewer-pair state, feedback state, and mergeability. In Pi, this state lives in the task extension and working notes; in Codex, it lives in Codex goal/task state. Do not clear or complete the run state until the same completion criteria are satisfied.

#### Registered Doct plan status alignment

For a reviewed HTML plan, align Doct plan state before code edits. Resolve the Doct document/plan ID, workspace ID, canonical Doct URL, and current version from registration output, the explicit Doct review URL, or `doct-agent plans show --id <document-id> --json`; if the plan is not registered and repo guidance expects reviewed plans, register it through `doct-document-ops` with `doct-agent plans register --base-url https://doct.nodaste.com --source-format html --title '<Plan Title>'` (title required; must match plan content title) before proceeding.

Before implementation starts:

1. Run `doct-agent plans lifecycle --base-url https://doct.nodaste.com --document-id <document-id> --workspace-id <workspace-id> --state active --json` when the plan is not already active.
2. Run `doct-agent plans board list --base-url https://doct.nodaste.com --workspace-id <workspace-id> --json` and inspect the available board columns.
3. If a visible `in_progress` column exists, run `doct-agent plans board set --base-url https://doct.nodaste.com --document-id <document-id> --workspace-id <workspace-id> --column in_progress --json`.
4. If `in_progress` is absent, hidden, or ambiguous, stop with an actionable status-sync blocker unless repo/service configuration explicitly identifies an equivalent in-progress column.

Do not treat a disk progress checkbox update as sufficient reviewer-state alignment. During implementation, keep phase progress in the delivery/coverage ledger so the reviewed plan hash remains stable. Immediately before completeness review, apply one truthful progress/status-only update to the source plan, publish it through `doct-agent plans update` or an active `doct-agent plans watch`, and inspect Doct evidence (`plans show`, board/list output, or returned update metadata). Material contract changes still require revocation and a fresh readiness cycle.

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

For each unfinished **PR-reviewable** phase:

1. Write or update only the tests required by the phase.
2. Implement the smallest product change that satisfies the phase.
3. Run the phase's targeted verification.
4. Record completed phase progress in the delivery/coverage ledger; do not mutate the reviewed source plan after each phase because the plan content hash anchors the live implementation authorization.
5. Immediately before completeness review, synchronize all truthful progress checkboxes to the source plan and Doct in one bookkeeping update, verify the change is progress/status-only, and preserve the active implementation handoff. A material contract edit instead requires revocation and a fresh readiness cycle.
6. Record only documented out-of-scope discoveries in the plan's deviation log or the repo's discovery ledger. In-scope findings are not discoveries to defer; fix them before advancing.

If an existing plan phase requires deployment, promotion, merge-dependent validation, production observation, or rollback execution, split the boundary rather than executing or waiting on that operation: complete and check off only the PR-reviewable implementation portion when truthful, move/preserve the operational portion as a non-blocking post-merge obligation, sync that clarification to Doct, and continue toward PR creation.

If a phase exposes a broader product problem, classify it. Fix it only if it is a plan prerequisite or a regression from this diff.

### 3b. Permanent-document disposition (Heddle / repo-local permanent-docs)

After PR-reviewable implementation stabilizes and **before** Self Scope Audit and the first scoped quality review:

1. If the worktree is Heddle (or another repo with a local permanent-docs skill), load `.agents/skills/heddle-permanent-docs/SKILL.md` (or the local equivalent).
2. Record exactly one disposition: `none` | `patch <paths>` | `new-record <path>` | `ADR <path>` | `deferred-to-final-plan-slice` (deferred must name final slice/issue and interim source of truth).
3. Capture any required permanent docs into the candidate now so scoped review, PM, autoreview, and completeness all see them.
4. Reject hollow stubs (empty templates, TODO bodies, “see plan” only) for `patch` / `new-record` / `ADR`.
5. When a delivery ledger exists: `delivery record permanentDocs --status pass|skip|gap --summary "disposition=..."`.
6. For in-flight authorized plans that lack a disposition phase, record disposition externally (ledger + later PR body); do not mutate the authorized plan solely to inject the phase.
7. Include disposition, paths, and hollow-doc notes in every subsequent review packet.

Final pre-PR step is **assertion only** (disposition still accurate; claimed paths present; changelog fragment/exemption intact). If permanent docs change materially after a review pass, rerun targeted review/completeness—do not treat final verification as doc-quality review. Plan archive and CCore packages remain post-merge and non-blocking.

### 4. Self Scope Audit

Before reviewer subagent review, inspect the diff against the plan:

```bash
git diff --stat
git diff --name-only
```

For every changed file, answer: why does this file need to change for this plan?

If a changed file has no plan-bound reason, revert only your own edits to that file or split the work into a separate follow-up branch. Never revert user changes.

### 5. First scoped quality review

Run the active-harness `reviewer` subagent with a bounded prompt that names the plan path, comparison range, changed files, scope contract, verification results, and verdict format. Do not let the reviewer edit files or execute verification. Capture the result into `thoughts/validation/<slug>-run-plan-review.md`.

The review prompt must include:

- the plan path,
- the base branch or comparison range,
- the permanent-document disposition and claimed paths when the Heddle/local permanent-docs gate applies,
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

### 6. Reviewer scope

Use the same single reviewer for every risk level. High-risk changes receive a more specific bounded packet, not a second external reviewer. The packet must include the plan path, base branch or comparison range, changed files, scope contract, self scope audit, latest verification results, touched surfaces, and the specific failure families to inspect. When the integration-integrity rule is triggered, it must also include the integration record: source of truth; producer/consumer or source-derived operation inventory; coverage declaration; reconciliation state; boundary or production-dispatch proof; stale-reference search result; and actual-parser proof for a contractual documented CLI form. It must not edit files. It must return findings in chat, classified with the same scope categories.

A prior runtime-native review may satisfy this gate only when its packet included the triggered integration-integrity evidence and explicitly checked it. Otherwise, run the reviewer with that evidence before treating the pre-PR review gate as satisfied.

For every reviewer, use bounded scope and bounded exploration. Give each reviewer a concrete review packet: plan scope, changed files, diff summary, verification results, named touched surfaces, the specific failure families to check, and `TARGET_CHECKOUT` with the coordinator's HEAD/status snapshot. Every Pi `Agent` reviewer call must omit the `isolation` property entirely; never set `isolation: "worktree"`. Inspect the final tool arguments and remove that property before launch. Staged, unstaged, and untracked changes must be visible from the live checkout. If the harness itself isolates despite omission, do not refuse or discard the review: the reviewer must inspect `TARGET_CHECKOUT` directly. Tool outputs should be narrow: prefer exact file reads with offsets/limits and `rg -n` on changed files over repo-wide dumps. Do not use parent-side `max_turns` as the primary bounding mechanism for reviewer completion; hard turn caps can truncate the final verdict and produce unusable output. Bound the assigned scope instead.

If any reviewer cannot complete the assigned scope, it must return `REVIEW_INCOMPLETE_RERUN_NEEDED` with completed checks, remaining checks, and the recommended follow-up slice.

Split a normal review only when a diff has more than 20 changed files, more than 2000 diff lines, or clearly independent product surfaces that one bounded slice cannot review. Use at most two slices per reviewer in the initial cycle. Do not split a small or medium diff merely to get more opinions, and do not create generic failure-family slices unless the diff actually touches those failure families.

Empty output, tool-only output, provider errors, or transcripts ending in tool use are review infrastructure failures, not passes. Rerun once with a narrower bounded prompt; do not fix empty reviewer output by adding or lowering parent-side turn limits. If the narrowed rerun is still unusable, stop with a review-infrastructure blocker unless the user explicitly waives the gate or directs opening the PR regardless.

If either reviewer reports broad adjacent risks, keep them out of the PR only when they satisfy the `OUT_OF_SCOPE_FOLLOW_UP` definition and are documented. If the risk maps to the plan, verification, or this diff, treat it as in-scope and fix it.

### 7. Triage Reviews Before Fixing

Create a short triage table in your working notes:

```text
Finding | Source | Classification | Decision | Evidence
```

For each scoped reviewer finding:

- Fix `IN_PLAN`, `PLAN_PREREQUISITE`, and `REGRESSION_FROM_THIS_DIFF`.
- Record `OUT_OF_SCOPE_FOLLOW_UP` as a captured finding with why it is outside this plan and where it will be tracked; you are not required to add code or tests to dispose of it.
- Stop and ask the user for `QUESTION`.

Do not implement fixes directly from reviewer prose. Convert them through this triage step first.

### 8. Targeted Rereview

After fixing in-scope findings:

1. Rerun targeted tests for touched code.
2. Rerun the first scoped quality review with the previous findings and current diff.
3. Rerun the same reviewer with the same bounded scope.
4. If any reviewer returns `REVIEW_INCOMPLETE_RERUN_NEEDED`, run at most one narrowed follow-up slice for that cycle and append the result to a coverage ledger. If that follow-up is still incomplete or unusable, stop with a review-budget blocker or ask the user to waive/narrow the gate.
5. Stop after this targeted rereview when the active-harness reviewer returns `PASS` (or a legacy green verdict), or report the remaining convergence/scope blocker. Run a third total review cycle only when the targeted rereview identifies a new concrete blocker introduced or exposed by the fix and the unified review-cycle ledger shows that the third cycle remains available.

The coverage ledger must record completed slices, the single allowed incomplete rerun slice, review cycle numbers across the entire run (including later PR feedback), remaining budget, and final synthesized gate status.

The ordinary local review budget is exhausted when:

- the same finding or same failure family recurs after two fix attempts,
- a narrow/optional component keeps producing new edge-case findings after two cycles and should be reverted, deferred, or redesigned instead of patched through review,
- reviewers disagree on scope and the plan does not resolve it,
- a needed fix would clearly expand the plan,
- three total implementation-review cycles have run for this scoped change, regardless of whether they occurred before or after PR creation; the third cycle is permitted only for a new concrete blocker introduced or exposed by the prior fix.

Do not report the convergence blocker yet solely because no PR exists. Mark review non-convergence, a recurring failure family, or unresolved scope disagreement as a pre-PR `REVIEW_ESCAPE`, then run the single bounded external consultation and, only if authorized, the bounded adversarial active-harness reviewer pass defined below. This route applies to a fixed candidate branch/diff before or after PR creation and does not require a PR URL or PR feedback.

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
2. If the PM review reshapes the plan, update the source plan with the correction, push the update to Doct for reviewed HTML plans, execute the added plan-required work, and rerun verification or scoped reviews invalidated by the change.
3. Stop for user input on `QUESTION` findings that require a product or scope decision.
4. Record true `OUT_OF_SCOPE_FOLLOW_UP` findings only with evidence and a tracking destination; do not let PM review broaden the PR beyond the plan contract.

The PM gate is clean only when the implemented outcome satisfies the plan by substance, all in-scope PM findings have been fixed or blocked by a real decision, and any plan/Doct progress updates are synchronized. Record the PM verdict, artifact or notes location, plan-update status, and any rerun requirements for the PR body.

### 10. Active-Harness Pre-PR Review Gate

After phase implementation and the runtime-native scoped quality-review loop has no unresolved blocking in-scope findings, satisfy the active-harness reviewer-subagent pre-PR gate before final PR preparation.

Do not run redundant full reviewer gates over an unchanged diff. If the latest runtime-native reviewer pass already ran after the last code change, used the current base/comparison range, covered the current changed files, and has no unresolved blocking in-scope P1/P2 findings, record that evidence as the pre-PR gate result and continue. Run `$autoreview <plan path>` only when current reviewer evidence is missing, stale, incomplete, or materially narrower than the PR diff. Follow the canonical autoreview policy, including its pre-review scope baseline, concrete blocker evidence, smallest-fix ownership boundary, behavioral-verification separation, dependency evidence, known-blocker overflow, and release freeze discipline; do not duplicate or weaken those rules here.

Run exactly one bounded, static inspection with the active harness's configured `reviewer` subagent. In Pi it is GPT-5.6 Terra at medium reasoning effort; in Claude Code it is Sonnet 5 at high effort; in OpenCode it is GPT-5.6 Terra at medium reasoning effort. Do not create separate Codex or Claude Code review legs. This code-review gate itself does not use Herdr; the separate completeness review below is required before PR creation. Pass the plan path, base/comparison range, changed files, scope contract, and latest verification results. The reviewer must classify findings by P1/P2/P3 severity and by the normal scope categories. It must not execute tests, builds, linters, typechecks, benchmarks, verification scripts, validation commands, or other executable behavior checks.

**Launch in the live checkout:** follow the autoreview candidate-visibility contract for every run-plan reviewer launch (scoped quality review, pre-PR gate, targeted rereview, and adversarial pass). In Pi, omit the `isolation` property entirely from every reviewer `Agent` call; requesting `isolation: "worktree"` is a workflow violation. Every packet must still name the absolute `TARGET_CHECKOUT` as a safety fallback; if the harness itself isolates despite omission, the reviewer inspects that target directly. Never turn a visible-code review into an infrastructure failure solely because of CWD or worktree state. If a dirty portion is genuinely unavailable, preserve the findings over visible code and run at most one targeted follow-up over the missing patch/paths.

Treat every in-scope P1/P2 finding as blocking a clean ready-for-PR conclusion. Triage findings before editing, fix only `IN_PLAN`, `PLAN_PREREQUISITE`, and `REGRESSION_FROM_THIS_DIFF` blocking P1/P2 issues, rerun targeted verification, and run one targeted rereview limited to the findings and resulting edits. Apply the unified review-cycle ledger: reuse equivalent current evidence instead of double-counting a gate, and allow a third total review cycle only for a new concrete blocker introduced or exposed by the fix. PR creation never resets or changes this budget; otherwise return clean consensus or a convergence/scope blocker. P3 findings block only when they are plan-required, verification-required, or regression-caused; otherwise document them as non-blocking follow-ups with evidence and a tracking destination.

If the gate applies fixes after final verification has already run, rerun final verification before commit/PR. If the active-harness reviewer is unavailable, stop unless the user explicitly waives this pre-PR gate or explicitly directs opening the PR regardless; in the latter case, open it and disclose the infrastructure failure and missing coverage.

When the gate reports `OPEN_PR_READY` or equivalent clean consensus, run the completeness review next. Do not open a PR until completeness returns `VERDICT: COMPLETE` or the operator explicitly overrides. Do not return a final run-plan response at this point.

Record the reviewer model/effort, verdict, artifact path, waived/not-run status, and any documented non-blocking follow-ups for the PR body.

### 10a. Runtime-owned Completeness Review

This is a second review of **whether the implementation completes the plan**, not a replacement for the active-harness code reviewer. It is a hard pre-PR gate for every run-plan. Autoreview `OPEN_PR_READY` is not permission to skip it. Do not create a PR until this review returns `VERDICT: COMPLETE` against the current plan and live worktree, or the operator explicitly waives it or instructs opening the PR regardless.

Load `skill://completeness` and follow it. Do not arm delivery just to run this gate.

When `.delivery/ledger.json` already exists, use that runtime's completion-review transport:

For Pi Full, start the visible labeled-tab review from the driving agent's pane:

```bash
delivery stage COMPLETENESS_REVIEW
delivery completion-review
```

`delivery completion-review` creates a short-lived labeled **witness** tab in the same Herdr workspace (not the workspace owner), starts a new interactive Pi on that tab's root pane in the same live worktree with `--model xai/grok-4.5:high`, and sends its full visible review prompt. The reviewer may read the plan, current diff, status, and validation artifacts but must not edit files or execute verification. Workspace ownership stays on the implementation tab; after `--accept` or `--waive`, delivery closes the witness tab. Closed TUIs are not evidence—use the written completeness artifact and ledger thereafter.

While the completeness tab is live, the driving agent must read its verdict. For every `FINDINGS_TO_RESOLVE` item that is `IN_PLAN`, `PLAN_PREREQUISITE`, or `REGRESSION_FROM_THIS_DIFF`, make the smallest in-scope correction, run invalidated verification, and request the same named reviewer's next round:

```bash
delivery completion-review --rerun
```

Repeat until it returns `VERDICT: COMPLETE`, with an AC/BDD coverage table and `Not examined:` disclosure. Capture the visible response in `thoughts/validation/<slug>-completeness.md` and record it:

```bash
delivery completion-review --accept
```

For OMP Lite, stay in the coordinating OMP session:

```bash
delivery stage COMPLETENESS_REVIEW
delivery completion-review --prepare --reviewer-identity omp-completeness-grok-4.5-high
# Send the emitted packet unchanged to @completeness (xai/grok-4.5:high).
# Save exactly one seven-line response envelope to the requested artifact.
delivery completion-review --accept --artifact <artifact> --response-id <id>
```

OMP Lite acceptance is request-bound. The response ID, reviewer identity, plan SHA-256, worktree fingerprint, and exact `VERDICT: COMPLETE` envelope must match the pending request; stale, replayed, interrupted, malformed, Pi-origin, or `INCOMPLETE` artifacts are rejected without partial ledger mutation. Fix in-plan findings and prepare a fresh request rather than reusing an accepted or invalid artifact.

When no ledger exists, use the completeness skill standalone path: write a packet JSON with `artifact`, `requiredEnvelope`, and `requiredIncompleteVerdict`; launch `@completeness` on `xai/grok-4.5:high` with `TARGET_CHECKOUT`, the plan, and the packet path; accept only a current `VERDICT: COMPLETE` artifact. Do not call `delivery completion-review`. If the completeness reviewer is unavailable, stop unless the user explicitly waives this gate or directs opening the PR regardless; in the latter case, open it and disclose the missing coverage.

This loop is separate from the active-harness reviewer-cycle budget because it checks plan completion rather than re-running the same code-review gate. If the same plan-completeness disagreement remains unresolved after three correction/rereview rounds, stop with the concrete criterion and smallest required operator decision; do not fabricate consensus. An explicit operator waiver may permit PR creation, but record it as waived/missing completeness coverage and never claim local merge readiness as clean.

## Final Verification

Establish passing final-verification evidence after the latest verification-relevant change and before PR creation. This is pre-merge verification only: it may prove buildability, deployability, migration definitions, configuration, dry-run behavior, and artifact integrity, but must not require an actual environment deployment, promotion, merge-dependent smoke check, or production observation. Reuse the latest passing results when the same commands already ran against the current code, tests, dependencies, configuration, generated artifacts, and base context, and no intervening action invalidated them. A read-only reviewer-subagent review does not invalidate passing verification and is never, by itself, a reason to rerun it. Record reused commands, outcomes, and the unchanged-state basis in the run notes and PR body.

Rerun only checks invalidated by an implementation or review fix, dependency/configuration/generated-artifact change, rebase or conflict resolution that changed the content identity, relevant environment change, prior failure, or an explicit plan requirement that demands a fresh run at this point. If the plan does not specify enough verification, run the smallest repo-appropriate gate for the changed surfaces and report the gap as a plan defect. Full-gate reruns are governed by the Verification Convergence Budget; a failure with an already-classified root cause never by itself requires another full run. An exhausted convergence budget with all residuals classified inherited or infra/cosmetic and targeted verification green satisfies this section's evidence requirement for the draft-PR disposition — record the classification as the final-verification result rather than calling the gate passing. If the operator explicitly directs opening the PR regardless of testing status, do not delay PR creation for further verification; record exactly which checks passed, failed, were skipped, or could not run.

Do not hide failures. Fix failures when they are in scope, required for truthful verification, or caused by this branch. Otherwise, report them as pre-existing or documented out-of-scope follow-ups with evidence and tracking destination.

## Base Freshness and Mergeability Gate

Before push and PR creation, verify the branch is fresh enough against the target branch that the PR will not immediately open stale or obviously unmergeable. Run the first freshness check before committing when possible, but do not rebase a dirty worktree by default.

The **content identity** of a candidate is the combined hash of: the committed diff against the merge-base with the target branch (`git diff "$(git merge-base origin/<target> HEAD)"..HEAD`), the staged diff, the unstaged diff, and a deterministic untracked-path manifest (sorted paths with type/mode and content hash). This reviewer fingerprint uses the merge-base diff hash rather than a HEAD commit component: it identifies the change content — committed or not — while ignoring commit SHAs. Two candidates with equal content identity carry the same change; a rebase that alters only SHAs leaves it unchanged.

1. Resolve the target branch from the plan, existing PR metadata, or repo default integration branch.
2. Fetch the target branch.
3. Check whether the current branch is behind, diverged, or likely conflicted with the fetched target branch.
4. If the branch is behind or diverged while scoped edits are still uncommitted, commit the scoped changes after final verification, then rebase the committed branch onto the fetched target branch before pushing. Use autostash only when repo policy explicitly permits it, and record exactly what was stashed, reapplied, and reverified.
5. If the branch is behind or diverged after commit, rebase onto the fetched target branch when conflicts are absent or limited to scoped files and can be resolved without a product decision.
6. If conflicts affect out-of-scope files, require unclear product decisions, or cannot be resolved without destructive git operations, stop with a base freshness blocker.
7. After any rebase, autostash replay, or conflict resolution, compare the content identity before and after. If it is unchanged, prior verification and review evidence remains current — record the rebase and the unchanged hash. If it changed, rerun only the verification the changed hunks invalidate, and record why the remainder stays current.
8. Review evidence follows the same content identity: rerun full scoped quality reviews, PM review, or the reviewer-subagent pre-PR gate only when the rebase materially changed the content diff, touched files, acceptance evidence, or reviewer assumptions. An unchanged content identity never by itself stales accepted review evidence.

Record the target branch, fetch result, rebase/skip decision, rerun verification, and any stale-review reruns in the PR body. A clean `OPEN_PR_READY` review verdict is not enough by itself if the branch became stale before PR creation.

## Final committed-candidate checklist

Immediately before PR creation, after the final scoped commit and any rebase:

1. Resolve `MERGE_BASE="$(git merge-base <base> HEAD)"` and run `git diff --check "$MERGE_BASE"..HEAD`; an unstaged-only check is insufficient.
2. Audit `git status --short`, including untracked paths, and confirm every changed file is plan-bound.
3. Confirm every PR-reviewable plan phase/progress item is complete and the registered Doct source/version reflects the current plan.
4. Fetch/recompare the target base after the final commit; safely rebase when required and rerun checks invalidated by changed content identity.
5. Search changed files in the committed range for unresolved release/PR placeholders including `PR #TBD`, `TODO-PR`, and `CHANGELOG_PLACEHOLDER`; stop with exact file/line and remediation command on a hit.
6. When the Heddle/local permanent-docs gate applies: disposition is recorded; for `patch` / `new-record` / `ADR` every claimed path appears in the candidate; `deferred-to-final-plan-slice` names final slice/issue; no false `graduated-plan/...` retrieval claim without a verified receipt; PR body will include the Permanent documentation section—or an explicit operator waiver is disclosed.

## Commit, Push, and PR

When implementation, scoped reviews, implementation-stage PM review, the applicable reviewer-subagent pre-PR gate status, completeness review, final verification, and base freshness pass or are ready to complete immediately after the scoped commit, PR creation is mandatory in the same run. An explicit operator instruction to open the PR regardless of testing or review status bypasses only those testing/review gates and requires truthful disclosure; it does not turn skipped or failing evidence into a passing or merge-ready result.

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
- implementation-stage PM review verdict, artifact/notes location, any plan/Doct updates, and any PM-triggered rerun requirements,
- reviewer-subagent pre-PR review verdict and artifact path, or explicit waived/not-run status,
- completeness-review verdict/artifact, or explicit operator waiver,
- **Permanent documentation** section when the Heddle/local permanent-docs gate applies (disposition, paths/reason/final slice, changelog fragment, plan source retained, archive post-merge only)—or explicit waiver disclosure,
- base freshness and mergeability/rebase status before PR creation,
- documented out-of-scope follow-ups with evidence and tracking destination,
- known residual risks,
- pending non-blocking post-merge deployment, promotion, observation, or rollback obligations, including owner/trigger/evidence when the plan specifies them.

Do not include memory citations in PR messages.

## Post-PR Local Merge-Readiness Check

After the PR is open, keep the active runtime task state active only until the local merge-readiness criteria are satisfied. In Pi this is the active readiness task/run state; in Codex this is the active Codex goal/task state. This phase checks real PR state, but it does not wait for a Codex thumbs-up, a human approval, or slow/absent external feedback once the local review agents have reached consensus.

### Completion Criteria

The run state can be marked complete only when all of these are true:

- Final verification for the touched surfaces has passed after the latest code change, or the Verification Convergence Budget disposition applies: targeted verification is green, every residual failure is classified inherited or infra/cosmetic with evidence, and the classification is disclosed in the PR body. In the draft-PR disposition the run state does not complete — it is blocked-on-operator with the ship/keep-fixing question until the operator answers.
- Runtime-native scoped quality review, implementation-stage PM review, and the reviewer-subagent pre-PR gate all agree by substance that the current diff has no unresolved blocking in-scope findings; skipped/waived gates are recorded truthfully.
- When the Heddle/local permanent-docs gate applies, permanent-document disposition is satisfied or explicitly waived with disclosure, and the PR body Permanent documentation section matches the candidate.
- The runtime-specific completeness review returned `VERDICT: COMPLETE` against the current plan/live worktree (delivery `--accept` when a ledger exists; standalone completeness artifact when it does not), or an explicit operator waiver is disclosed. Do not treat a hidden autoreview subagent verdict as a substitute.
- All actionable PR feedback already present in the latest snapshot has been addressed.
- If PR feedback required code changes, the applicable review agents have rerun over the current PR diff and cleared any in-scope findings.
- The branch has been rebased or otherwise updated against the destination branch as needed, with affected verification rerun after the update.
- GitHub reports the PR as mergeable with the destination branch, or GitHub mergeability is unavailable/unknown but a fresh base-freshness check shows no known merge conflict.

Deployment, promotion, merge-dependent smoke checks, production observation, and rollback-window closure are not completion criteria for run-plan. Record them as the next delivery handoff when applicable; do not hold the PR or run state open for them.

Do not require `reviewDecision: APPROVED`, a Codex PR comment saying LGTM, or any other external thumbs-up to complete the run.

### Monitoring Loop

Repeat this loop until the completion criteria are met or a true blocker is reached. Slow or absent reviewer feedback is not a blocker and does not require continued polling after local merge-readiness consensus is clean. Pending or failing required checks should be handled only when they affect the stated merge-readiness criteria.

A run in the convergence-budget draft-PR disposition does not loop: it reports the ship/keep-fixing question with the classification and waits on the operator. Failing required checks that reproduce the already-classified inherited/infra residuals are part of that disclosure, not new work.

1. Inspect PR reviews, review threads, comments, status checks, review decision, and mergeability for the current snapshot.
2. Classify every new feedback item using the same scope categories.
3. If any actionable feedback arrives after the local scoped review gates already passed, mark the cycle as a `REVIEW_ESCAPE` in working notes. Fixing only the mentioned line is insufficient.
4. Fix `IN_PLAN`, `PLAN_PREREQUISITE`, and `REGRESSION_FROM_THIS_DIFF` feedback.
5. Record or report `OUT_OF_SCOPE_FOLLOW_UP` feedback with evidence and tracking destination without expanding the PR.
6. Stop for user input on `QUESTION` feedback.
7. For each `REVIEW_ESCAPE`, consult the unified review-cycle ledger. Use an ordinary adversarial/targeted cycle when one remains and the normal third-cycle condition is satisfied; otherwise, route the stable failure-family/scope identifier through the one-per-family bounded consultation section below before reporting convergence. Only that consultation's explicit authorization permits its single bounded adversarial pass and existing one pass-after-fixes allowance after ordinary budget exhaustion. PR existence is never authorization for an ordinary or consultation-authorized extra pass.
8. Rerun the smallest meaningful verification for any changes.
9. Commit and push fixes to the PR branch.
10. Rebase onto the destination branch when GitHub reports the branch out of date, stale, conflicted, or blocked by base freshness, but only when conflicts are absent or limited to scoped files and do not require a product decision.
11. After any post-PR rebase or conflict resolution, rerun affected verification, rerun scoped reviews when the PR diff changed materially, and push with lease.
12. Stop with a scope question when rebase conflicts affect out-of-scope files, require unclear product decisions, or cannot be resolved without destructive git operations.
13. Recheck once after fixes or rebase to confirm GitHub shows the PR as mergeable, or that mergeability is unavailable/unknown with no known conflict from the fresh base-freshness check.
14. If a snapshot has no actionable feedback and local review-agent consensus is clean, do not keep polling just to obtain a Codex thumbs-up, human approval, or reviewDecision change. Complete the run when the completion criteria above are satisfied.

### Review Escape Consultation and Adversarial Escalation Loop

A `REVIEW_ESCAPE` means either (a) bounded local review did not converge on a candidate branch/diff, including before PR creation, or (b) actionable PR feedback proved the previous review prompt was not thorough enough. A PR URL or PR feedback is not required for this route.

Before a convergence blocker is returned, assign a stable consultation identifier to the distinct escaped failure family and affected scope on the fixed artifact, comparison range, and complete fingerprint. Run exactly one bounded, read-only consultation through the configured consult/council surface. In Pi, load `oracle-consultation` and use Oracle; do not launch another reviewer or an external Codex/Claude session as a substitute. Record the identifier, packet, and verified disposition. Never repeat consultation for the same unresolved family/scope identifier or use new wording to restart its budget. A materially separate later failure-family/scope identifier may receive its own one consultation whether discovered pre-PR, during an authorized adversarial pass, or from later PR feedback. The packet must also name prior fix attempts, reviewer disagreement, verification evidence, and the allowed dispositions: reject/reclassify with evidence; authorize one bounded adversarial fix/review pass; revert/narrow/defer; or request a user/product/scope decision.

The coordinator verifies the consultation evidence and consumes its disposition exactly once. Verified rejection or reclassification clears that escaped finding/failure family and allows the run to continue without an adversarial pass; record the evidence and resulting scope/severity classification. Revert, narrow, or defer follows the stated path under the normal scope rules. A user/product/scope-decision disposition stops for that decision. Only an explicit authorization starts the bounded adversarial pass. If disposition evidence cannot be verified or its stated path cannot be completed within current authority, report that specific unresolved blocker; do not convert every non-authorization into a convergence blocker.

If and only if the consultation authorizes the further adversarial pass, run it before or after PR creation as follows:

1. Write down the escaped-defect pattern: reviewer, affected file/line, why earlier review missed or disputed it, and the failure family it represents. Include a feedback URL only when PR feedback is the trigger.
2. Audit the fixed candidate branch/diff for sibling instances: same assumption, same edge case, same API contract, same missing validation, same lifecycle/state transition, analogous callsites, and tests that should have failed but did not.
3. Run one read-only adversarial implementation review with the active-harness `reviewer` subagent. Review the current candidate branch/diff, the plan scope contract, the consultation disposition, any direct PR feedback when present, and the sibling-audit notes. Ask the reviewer to actively look for additional missed issues in the same failure family and nearby plan-bound surfaces, not to re-approve one fix. Use one bounded adversarial slice focused on the escaped failure family; use a second slice only when it spans clearly separate surfaces. The reviewer must return a verdict or `REVIEW_INCOMPLETE_RERUN_NEEDED`; the parent records completed slices, the single allowed incomplete rerun slice, and final synthesized gate status in the coverage ledger.
4. Triage new adversarial findings using the normal scope classifications. The driving agent may make one bounded fix attempt for in-scope findings; document true out-of-scope follow-ups and stop for questions.
5. Repeat the same adversarial reviewer pass once after those fixes if it found any in-scope issue. Then return to the normal workflow only if the pass is clean; otherwise return control with the convergence blocker or requested decision.

Keep this escalation scope-bound: one consultation per distinct failure-family/scope identifier and, only when authorized, one bounded adversarial reviewer pass with the existing single pass-after-fixes allowance are the limit. Do not repeat consultation for an unresolved identifier, restart the ordinary three-cycle budget, review until clean, or turn the escalation into an unrelated whole-product audit.

### Snapshot Persistence

When the run has reached post-PR readiness checking, the agent must persist only until the completion criteria are satisfied:

- Check the PR snapshot after creation and after every pushed fix/rebase for actionable feedback, required check failures that affect merge readiness, and mergeability.
- Do not poll indefinitely for absent feedback, a pending review, `reviewDecision: APPROVED`, or a Codex PR thumbs-up after local review-agent consensus is clean.
- If checks or mergeability are temporarily unavailable, perform the freshest practical local/base-freshness check and record the uncertainty instead of waiting solely for an external approval signal.
- In Pi, complete the readiness task with the `todo` tool's `update` action and the goal once the evidence-backed local merge-readiness criteria are satisfied; summarize the latest PR URL, mergeability/base-freshness state, feedback snapshot, and reviewer-pair consensus in the final status.
- A true blocker must be something the agent cannot resolve by scoped fixes or a fresh local/base-freshness check, such as lost GitHub authentication, a closed/deleted PR, a force-push/base-branch conflict requiring a product decision, failing required checks caused by this branch, `QUESTION` feedback that needs the user, or an exhausted unified review-cycle budget with unresolved blocking review risk. Pending deployment or post-merge observation is not a run-plan blocker.
- If a true blocker is reached, report the exact blocker and the latest PR state. Otherwise, complete the active run state when local merge-readiness consensus is proven.

Use GitHub product surfaces for this check:

- PR issue comments via `gh pr view ... --json comments` and/or `GET /repos/<owner>/<repo>/issues/<pr>/comments`.
- PR reviews via `gh pr view ... --json reviews`.
- Inline review comments via `GET /repos/<owner>/<repo>/pulls/<pr>/comments`.
- Status/mergeability via `gh pr view ... --json mergeable,mergeStateStatus,statusCheckRollup,reviewDecision`.

Reference implementation for Pi: write this to `/tmp/snapshot-pr-<pr>.sh` and run it once with `bash` to capture the current PR feedback/mergeability snapshot. Use a background `process` monitor only when mergeability or required checks are temporarily unavailable and you need a bounded wait for those merge-readiness signals; do not run it just to wait for a Codex thumbs-up or human approval.

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

ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
fetch_state
snapshot_feedback
merge=$(jq -r '(.mergeable // "UNKNOWN") + "/" + (.mergeStateStatus // "UNKNOWN")' "$state_dir/pr.json")
comments=$(jq 'length' "$state_dir/issue-comments.json")
review_comments=$(jq 'length' "$state_dir/review-comments.json")
reviews=$(jq '.reviews | length' "$state_dir/pr.json")
echo "$ts PR_SNAPSHOT merge=$merge issue_comments=$comments review_comments=$review_comments reviews=$reviews snapshot=$state_dir/feedback.current.json"
```

Run the snapshot like this from Pi:

```text
bash /tmp/snapshot-pr-<number>.sh <owner>/<repo> <number>
```

If a required check or GitHub mergeability is temporarily unavailable and a bounded wait is needed, start a short-lived `process` monitor for that signal only; stop it once merge-readiness can be determined.

### Rebase Guidance

When rebase is needed:

1. Fetch the destination branch.
2. Rebase the PR branch onto the destination branch.
3. Resolve only conflicts in scoped files, and only when no product decision is needed.
4. Stop with a scope question when conflicts affect out-of-scope files, require unclear product decisions, or cannot be resolved without destructive git operations.
5. Rerun verification affected by the rebase only when the content identity changed; rerun only what the changed hunks invalidate.
6. Rerun scoped reviews when the content diff changed materially; a rebase that leaves the content identity unchanged does not invalidate accepted review evidence.
7. Push with lease.

Do not use destructive git commands to force mergeability. If conflicts require decisions outside the plan, stop with a scope question.

### Run State Closure

Only after the completion criteria are all satisfied, mark the runtime readiness task complete. In Pi, use the `todo` tool's `update` action to complete the readiness task only after a fresh evidence-backed completion audit. In Codex, complete the Codex goal/task state after the same audit. Do not keep the run state open for a slow reviewer, no new feedback, pending review, or missing Codex thumbs-up once local review-agent consensus is clean. Mark the run state blocked only for a real actionable blocker that prevents scoped fixes or a truthful local merge-readiness conclusion, and report the exact blocker with the latest PR state.

## Reviewer Prompt Template

Use this shape for the active-harness reviewer. Include the exact risk question and bounded high-risk packet when the diff touches a high-risk surface; do not rely on the generic prompt alone.

```text
Read-only implementation review. Do not edit files.
Do not run or invoke tests, builds, linters, typechecks, benchmarks, verification scripts, validation commands, or other executable behavior checks. Inspect source and caller-supplied verification evidence only; the coordinator owns execution.

TARGET_CHECKOUT: <absolute path to the candidate checkout>
COORDINATOR_HEAD: <short sha>
COORDINATOR_STATUS_SHORT: <git status --short one line, semicolon-separated, or EMPTY>

Provenance (required at the top of every successful or incomplete review):
- CWD: <absolute launch cwd>
- REVIEW_ROOT: <absolute checkout or artifact path actually reviewed>
- HEAD: <short sha>
- STATUS_SHORT: <git status --short one line, semicolon-separated, or EMPTY>
- REVIEW_SOURCE: <target-live-worktree | launch-checkout | supplied-diff>
Review visible candidate code in any clean, dirty, staged, unstaged, untracked, detached, or isolated state. If launch CWD differs from `TARGET_CHECKOUT`, inspect the target directly with path-qualified reads and `git -C`. Never return `REVIEW_INFRASTRUCTURE_FAILURE` solely because of launch CWD or worktree state; disclose genuinely unavailable portions under `Not examined:` while still reviewing available code.

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

Integration-integrity evidence (when triggered):
<source of truth; producer/consumer or source-derived inventory; coverage declaration; reconciliation state; real boundary or production-dispatch proof; stale-reference search result; and actual-parser proof for each contractual documented CLI form>

Review only whether this diff correctly implements the plan.
Treat the plan/scope, any author summary, and prior verification results as product intent and claims to verify — not proof of implementation correctness. Re-derive the key invariant from the code, schema, and types.

On this first pass (not only after an escape), also check:
- generic key-name matching/remapping/rewriting where the key name may not uniquely determine the value's type or target — construct non-target counterexamples (numbers, booleans, objects, unrelated strings) and confirm each is handled
- fail-closed/bail paths reachable by valid, schema-conformant input
- producer/consumer and round-trip parity (import vs export, encode vs decode, rewrite vs collect)
- when integration-integrity evidence is supplied, validate its source of truth, declared inventory/coverage/reconciliation, real boundary or production-dispatch proof, stale-reference result, and actual-parser CLI proof; do not accept helper-only, wrapper-only, middleware-only, or event-existence-only evidence as completion proof
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
- VERDICT: REVIEW_INCOMPLETE_RERUN_NEEDED
- VERDICT: REVIEW_INFRASTRUCTURE_FAILURE

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
Trigger: <pre-PR bounded review non-convergence | actionable PR feedback after local reviewer-pair gates passed>. Treat the consultation disposition and any direct fix as claims to verify, not proof.

Escaped finding/failure family or scope disagreement:
- Fixed artifact/comparison/fingerprint: <artifact, range, complete fingerprint>
- Reviewer/comment URL: <url only when PR feedback exists; otherwise none>
- Prior fix attempts and reviewer disagreement: <summary>
- Verification evidence: <commands/results>
- Oracle/consultation disposition: <reject/reclassify | authorize bounded adversarial pass | revert/narrow/defer | user/product/scope decision>
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
- run-state status (Pi goal plus task extension, or Codex goal/task),
- changed files at a high level,
- verification run,
- runtime-native scoped quality-review verdicts,
- implementation-stage PM review verdict,
- reviewer-subagent pre-PR review verdict or waived/not-run status,
- completeness-review verdict/artifact or waived/not-run status,
- base freshness and rebase status,
- PR feedback snapshot result,
- PR mergeability or base-freshness result,
- documented out-of-scope follow-ups with evidence and tracking destination,
- any residual risk.

Keep the closeout concise and evidence-based.
