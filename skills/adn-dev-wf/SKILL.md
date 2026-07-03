---
name: adn-dev-wf
description: "Canonical end-to-end reviewed-plan development workflow for this repo. Use when the user wants the standard process from a feature request, issue, or existing plan: create or update the single-file plan, optionally reshape it against product intent, run blocker-only inline plan review, integrate the review comments, execute directly phase-by-phase with one post-phase quality review, rerun bounded implementation-stage PM loops, and leave the branch validation-complete."
---

# ADN Dev Workflow

Use this as the repo's default workflow for non-trivial software changes.

Do not use it for trivial one-file edits, pure Q&A, or isolated code-review-only requests.
Use `dev-plan` when the user explicitly wants planning only, and use `review-change` when the user explicitly wants code review only.

## Inputs

Accept any of these starting points:
- a raw task description
- a plan slug
- a path to the repo's active plan artifact

Resolve the input to a single canonical plan file under `thoughts/plans/`.
If the user gives a raw request or a slug without an existing plan, create or update the plan first.
If the user gives an existing plan, continue from the first incomplete workflow stage rather than restarting from scratch.

## First reads

Before doing workflow work, read:
1. `AGENTS.md`
2. `thoughts/specs/product_intent.md` when relevant
3. `thoughts/plans/AGENTS.md` when present
4. the target plan if it already exists

Use `skills/planning-workflow/SKILL.md` as the planning doctrine and `references/stages.md` for the exact stage contract in this workflow.
Load `doct-document-ops` whenever the canonical plan file is an HTML/Markdoc plan or should be registered for browser review; use its Doct-backed `doct-agent plans` flow on `https://doct.nodaste.com`, follow returned `listenerInstructions` and start the durable listener after registration, process unresolved Doct plan comments/actions before execution, and keep registered plan state truthful.
Load `product-principles` when the work affects workflows, defaults, onboarding, recovery behavior, operator or agent UX, status surfaces, or architecture.

## Workflow contract

- Keep one canonical plan file in the repo's active plan format
- Keep all plan checkboxes in `## Progress` only
- Keep review comments inline as `[REVIEW:...] ... [/REVIEW]` until integrated
- Do not begin implementation while the plan still has unresolved inline review comments, unresolved Doct plan comments/actions, stale/non-ready registered Doct plan state, or non-ready status
- Do not use hidden fallback reviewers or resurrect retired execution paths
- Prefer direct execution with one post-phase `quality-reviewer` pass over multi-pass review-loop orchestration

## Stages

### 1. Materialize or refresh the plan

If the plan does not already exist or is clearly stale, create or update it using the single-file planning contract.
This stage is planning-only: do not modify product code.

### 2. Optional plan-stage PM reshape

When the work is product-facing, workflow-heavy, or likely to drift from user intent, reshape the plan before execution.
This stage edits the plan directly to tighten scope, defaults, recovery behavior, and verification.

### 3. Blocker-only plan review

Review the plan and write only material inline `[REVIEW:...]` comments.
Do not integrate comments during this stage.

### 4. Integrate review comments

Resolve all inline review comments back into the same plan file.
Keep scope faithful to the plan's goal and validated repo evidence.
Remove all inline review comments before moving on.

### 5. Validate execution readiness

Only proceed when the plan is execution-ready:
- no unresolved inline review comments
- `## Progress` exists
- `Resume Instructions (Agent)` exists
- active phases include `### Tests first`, `### End State`, `### Work`, `### Expected files`, `### Open questions / decision dependencies`, and `### Verify`
- progress checkboxes and detailed phases map one-to-one
- UI impact is explicitly triaged and is not `unknown`
- no unresolved open questions that materially change behavior
- for HTML plans: the closing ready verdict comes from an **independent reviewer**, not the plan author/self. Treat `PLAN_EXECUTION_READY` from `reviewed-html-plan` or an equivalent approved `PASS_NO_ISSUES` verdict as ready by substance. Integrating review findings does not self-certify readiness; an independent `BLOCKED`/findings requires a fresh independent review after integration. See `reviewed-html-plan` (Independent sign-off gate). Do not claim local mechanical validator enforcement unless that validator exists in the target repo; otherwise rely on the documented reviewer gate and truthful Doct plan state/metadata.

### 6. Execute directly

Execute phase-by-phase directly from the plan.
After each phase:
- run its `### Verify` steps
- delegate exactly one `quality-reviewer` pass
- rerun any impacted verification
- update the phase checkbox immediately if the phase cleared
- log decisions and only true out-of-scope low-risk follow-ups in `## Decisions / Deviations Log`, with evidence and a tracking destination; fix plan-required work immediately

Continue until all plan progress items are complete or a real blocking decision requires the user.

### 7. Implementation-stage PM review

After execution and validation, review whether the implementation actually satisfies the intended outcome.
If the PM pass reshapes the plan, rerun the review and integration stages, continue execution as needed, and cap that post-execution loop at three passes.

### 8. Finish cleanly

Run the repo's full validation bar.
Leave the branch and plan in a truthful completed state.
If the user asked to publish or open a PR, hand off to `cmd-create-pr` only after the workflow is complete.

## Operating rules

- Skip already-satisfied stages when repo evidence shows they are complete
- When in doubt, choose the conservative, plan-aligned path and log the decision
- Ask the user only for decisions that materially change external behavior and cannot be resolved from repo evidence
- Do not stop after updating the plan or finishing one phase if further unchecked workflow work remains

For the exact stage-level rules, review comment format, PM loop behavior, and execution semantics, read `references/stages.md` before proceeding.
