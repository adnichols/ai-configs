---
description: Execute a single-file plan directly with high reasoning plus one post-phase quality review
argument-hint: '<slug | existing-plan-path>'
model: openai/gpt-5.5
---

# Run Plan (Single File)

Execute a single plan document (spec + phases + progress) directly in this session.

- Follow the plan, but keep implementation flexibility.
- Use high reasoning throughout the run.
- Track progress by updating `## Progress` in the plan file.
- Run exactly one `quality-reviewer` pass after each phase before marking it complete.
- Allow same-scope dynamic re-chunking when a phase is too large to execute safely in one pass.

## Inputs

`$ARGUMENTS` may be:

- A slug
- A direct path to a plan file in the repo's active plan format

## Process

### 0) Autopilot Rules

- Execute continuously; do not pause between phases.
- A phase boundary is not a stopping point; if unchecked `## Progress` items remain, immediately continue to the next one.
- Interpret repo guidance like "advance one phase at a time" as serial execution order within this run: complete one phase, then start the next. It does **not** mean stop and wait after each phase.
- Do not stop after a status update (e.g., "I'm starting Phase 1" or "gathering context").
- Do not stop after completing a phase unless you are genuinely blocked.
- Do not hand control back merely because the plan is now in a resumable state; keep executing until all `## Progress` items are complete or a real blocker requires one targeted question.
- Every response must either (a) take the next concrete action by actually invoking a tool (read/search/edit/run) or updating the plan file, or (b) ask for user input due to an unresolvable decision. Narration is not an action.
- If unsure, investigate and retry until evidence supports a decision; do not ask the user just for uncertainty.
- Use `question` only when a decision between viable options requires user input due to insufficient evidence.
- You may re-chunk work only when the split preserves the plan's scope, acceptance criteria, locked decisions, and overall end state.

Unresolvable decision examples:

- Conflicting requirements in the plan with no priority rule.
- A security/billing/production-risk choice that materially changes behavior and is not specified.
- Multiple viable interpretations that change external behavior and cannot be resolved by existing code patterns.

### 1) Resolve Plan Path

Resolve to:

- `plan_path`

Rules:

- If `$ARGUMENTS` starts with `@`, treat it as a workspace-relative path and strip the leading `@`.
- If `$ARGUMENTS` is a path to an existing file, use it as `plan_path`.
- If `$ARGUMENTS` is a slug, resolve it using repo-local active plan guidance. Do not infer a markdown path. If repo guidance does not define slug-to-plan-path resolution, ask for the explicit existing plan path and stop.

Legacy migration support (do not delete legacy files):

- Only migrate legacy bundles when repo-local guidance explicitly allows migration to the repo's active plan format.

### 2) Read Plan

Read `plan_path` fully.

Before execution, confirm the plan is actually executable:

- `## Progress` exists and has at least one unchecked item or all items are already complete.
- `Resume Instructions (Agent)` exists.
- Each active phase includes `### Tests first`, `### End State`, `### Work`, and `### Verify`.
- If the plan declares `Status: research-ready` or equivalent non-ready status, do not start implementation.
- The plan does not contain unresolved `Open Questions`, `Decision Points`, or equivalent unresolved-decision sections when it is intended for execution.

Immediately begin execution:

- Identify the first unchecked item in `## Progress`.
- Find the corresponding phase section and start implementing it right away; do not pause to recap the plan.
- If that phase is obviously too large for one safe execution pass, re-chunk it before making code changes.
- After each phase, loop back to `## Progress` and continue until no unchecked items remain.

### 2.5) Same-Scope Re-Chunking Protocol

A phase may be re-chunked only when the split preserves:

- scope,
- acceptance criteria,
- locked decisions and externally visible semantics,
- and the parent phase's overall end state.

Use same-scope re-chunking when a phase shows one or more of these signals:

- multiple independently verifiable outcomes are bundled into one checkbox,
- materially different verification stories are mixed together,
- the likely work spans too many loosely related files, surfaces, or contracts for one safe pass,
- execution would require broad rediscovery just to decide how to proceed,
- a prior implementation attempt showed the slice was too large rather than blocked on one specific issue.

When re-chunking:

1. Change only the current unchecked phase and the unchecked progress bookkeeping that must correspond to it.
2. Replace the current progress item with smaller child items using stable suffixes such as `P2a`, `P2b`, `P2c`.
3. Replace the parent phase with matching child phases, each with `### Tests first`, `### End State`, `### Work`, and `### Verify`.
4. Preserve completed phase IDs and append a structured note to `## Decisions / Deviations Log` explaining why the split was needed.
5. Continue immediately with the first new child phase.

If a safe split would require changing scope, acceptance criteria, or missing semantics, do not re-chunk. Ask exactly one blocking question instead.

### 3) Execute Phase-by-Phase

For each phase in order (as tracked by `## Progress`):

1. Implement the phase as written.
2. Run the phase `### Verify` steps.
3. Delegate exactly one post-implementation review pass to `quality-reviewer`.
4. Run any missing `### Verify` steps again after the review pass.
5. If the review pass clears the phase, immediately flip its checkbox from `- [ ]` to `- [x]` in `## Progress`.
6. If implementation or review required a decision, revealed a constraint, or identified a true out-of-scope low-risk follow-up, append a structured entry with evidence and tracking destination to `## Decisions / Deviations Log` in the plan file. Do not defer plan-required work, verification gaps, BDD gaps, or regressions.
7. Re-read `## Progress`; if another unchecked item remains and you are not blocked, immediately start the next phase instead of returning a progress summary.

#### Required post-implementation review pass

After implementing the phase, delegate exactly one `quality-reviewer` pass with this prompt:

> Review the implementation of phase N of this plan: `<plan_path>`
>
> Read the plan file fully. Find phase N and its `### Tests first`, `### Work`, `### End State`, and `### Verify` sections. Review the implementation for gaps, regressions, plan fidelity issues, missing counterexample/boundary/parity coverage, stale verify commands, stale fixtures/contracts, unresolved evidence-source mismatches, or phase-sizing defects that would make the phase unsafe to advance.
>
> Do NOT flag style preferences, speculative enhancements, or test coverage beyond what the plan specifies or clearly implies.
>
> Fix every non-low-risk issue directly during this pass. Do not just report issues.
>
> If the real problem is that the phase bundles too much work to converge safely as one slice, say so plainly instead of brute-forcing more edits.
>
> Start the final summary with exactly one of:
> - `No issues found.`
> - `Only low-risk items remain.`
> - `Phase needs same-scope split.`
>
> If only low-risk items remain, list them briefly with why each is outside the phase's required end state and where it should be tracked. Do not include plan-required work, verification gaps, BDD gaps, or regressions in this category.

#### Review pass handling

- `No issues found.` -> the phase may advance after any missing verification is run.
- `Only low-risk items remain.` -> first verify each item is outside the phase's required end state, planned tests, and verification truthfulness; log each item with evidence and tracking destination in `## Decisions / Deviations Log`, then the phase may advance after any missing verification is run.
- `Phase needs same-scope split.` -> re-chunk the phase, log the split, and restart at the first new child phase.
- Any other review result or failed verification -> keep the phase unchecked, investigate whether a same-scope split resolves it, and otherwise ask exactly one blocking question.

#### Hard rule: never mark a failed phase complete

If any of the following is true, the checkbox must stay unchecked:

- verification failed
- the review pass did not clear the phase
- you do not have evidence that the plan's `### End State` was reached

#### Autonomy / Do Not Pause

- Proceed autonomously through phases.
- If you are not blocked, do not hand control back to the user; take the next concrete action (run commands, edit files, update progress) until you either finish or hit an unresolvable decision.
- Do not stop after announcing intent, listing next steps, or completing "context gathering".
- Only stop to ask the user when you hit an unresolvable decision that cannot be answered from the plan or codebase.
- If execution reveals that the current phase should be split, prefer a same-scope re-chunk before escalating to the user.

When you must ask:

- Ask exactly one targeted question (batch sub-choices into that one question).
- Provide a recommended default and say what would change with each option.

When you do not need to ask:

- Choose the most conservative, plan-aligned default.
- Log the decision in `## Decisions / Deviations Log` with evidence (files/commands) and proceed.

#### Tests Policy

- You MAY add/update tests when behavior changes.
- You MAY refactor for testability.
- You MUST NOT change product code merely to satisfy a failing test if acceptance criteria + observed behavior indicate the code is correct.
  - In that case, fix the test or update the test assumptions (and log the decision).

### 4) Completion

Only enter this section when all items in `## Progress` are complete.

- Ensure the plan file reflects completion accurately.
- Run any verification commands listed in the plan's `Verification Strategy` and/or phase `### Verify` sections.
- Only now return a final summary of completed phases, final verification, and any logged deviations.
