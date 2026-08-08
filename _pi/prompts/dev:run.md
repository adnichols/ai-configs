---
description: Execute a single-file plan directly with high reasoning plus one post-phase quality review
argument-hint: '<slug | existing-plan-path>'
---

# Run Plan (Single File)

Execute a single plan document (spec + phases + progress) directly in this session.

- Follow the plan, but keep implementation flexibility.
- Use high reasoning throughout the run.
- Track progress by updating `## Progress` in the plan file.
- Run exactly one `reviewer` pass after each phase before marking it complete.
- Allow same-scope dynamic re-chunking when a phase is too large to execute safely in one pass.

## Model routing

Keep GPT-5.6 Sol medium as the normal direct-execution parent and code-writing route.

Use `scout` before implementation whenever target files or contracts are not already known. Each scout call must receive one evidence question; named allowed files/directories, commands, or authoritative sources; explicit exclusions; and a stop condition. Its authority is read-only: no edits, diagnosis, synthesis, or recommendations. It must return concise evidence with file:line, command-output, or source citations plus any concrete blocker directly to the driving session, create no artifact, and stop when the question is answered or blocked. The driving agent owns synthesis and implementation decisions.

The driving agent performs all implementation directly with native repository tools. Do not delegate code edits, test changes, fixes, verification, or repository management to a subagent or developer persona. Prefer direct targeted inspection; use `scout` only as the bounded read-only exception described above.

When the plan plus targeted inspection leave one consequential implementation decision unresolved, load `oracle-consultation` and invoke Oracle proactively before locking the direction. Oracle cannot authorize scope expansion, make a product choice, replace the required phase `reviewer`, or serve as routine discovery.

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
- If unsure, investigate and retry until evidence supports a decision; do not ask the user just for uncertainty. When the remaining uncertainty is a consequential technical judgment rather than missing routine evidence, consult `oracle` once before choosing or escalating.
- Ask the user directly only when a decision between viable options requires product/scope input after targeted investigation and, when applicable, bounded Oracle advice.
- You may re-chunk work only when the split preserves the plan's scope, acceptance criteria, locked decisions, and overall end state.

Unresolvable decision examples:

- Conflicting requirements in the plan with no priority rule.
- A security/billing/production-risk choice that materially changes behavior and is not specified.
- Multiple viable interpretations that change external behavior and cannot be resolved by existing code patterns.

### 0.5) Optional Supervision

Do **not** launch a supervisor for `/dev:run`. Supervision is opt-in: only when the operator explicitly asks to supervise this run, follow `skills/supervise/SKILL.md`.

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
3. Delegate exactly one post-implementation review pass to `reviewer`.
4. Run any missing `### Verify` steps again after the review pass.
5. If the review pass clears the phase, immediately flip its checkbox from `- [ ]` to `- [x]` in `## Progress`.
6. If implementation or review required a decision, revealed a constraint, or identified a true out-of-scope low-risk follow-up, append a structured entry with evidence and tracking destination to `## Decisions / Deviations Log` in the plan file. Do not defer plan-required work, verification gaps, BDD gaps, or regressions.
7. Re-read `## Progress`; if another unchecked item remains and you are not blocked, immediately start the next phase instead of returning a progress summary.

#### Required post-implementation review pass

After implementing the phase, delegate exactly one read-only `reviewer` pass with this prompt:

> Read-only review of phase N of this plan: `<plan_path>`. Do not edit files.
>
> Read the plan file fully. Find phase N and its `### Tests first`, `### Work`, `### End State`, and `### Verify` sections. Report only concrete blockers within the promised slice: unmet acceptance criteria, incomplete wiring, regressions, credible current-path security/data-loss/correctness risks, or misleading verification.
>
> You are not required to fix or expand the change for speculative future scale, ideal architecture, unrelated pre-existing defects, optional polish, unsupported hypothetical paths, or test coverage beyond what the plan specifies or clearly implies; note any you find as non-blocking follow-ups rather than withholding them.
>
> Confirm that the promised slice is complete: no required stubs, TODO behavior, dead-end surfaces, missing producer/consumer wiring, fake success, or verification that bypasses the real implementation.
>
> If the real problem is that the phase cannot deliver an independently useful complete slice without changing scope, return a scope decision instead of expanding it.
>
> Start the final summary with exactly one of:
> - `Phase clear.`
> - `Blocking findings.`
> - `Phase needs scope decision.`
>
> List independent future enhancements only when useful, and state explicitly that they do not block or expand the current phase.

#### Review pass handling

- `Phase clear.` -> the phase may advance after any missing verification is run.
- `Blocking findings.` -> verify and fix only concrete in-scope blockers, run targeted verification, then run one targeted rereview limited to the findings and resulting edits.
- `Phase needs scope decision.` -> keep the phase unchecked and ask one blocking scope/product question; do not widen the phase automatically.
- A third review round is allowed only when the previous fix introduced or exposed a new concrete blocker. After three total rounds, the ordinary local review budget is exhausted.
- Before reporting a convergence blocker for review non-convergence, a recurring finding/failure family, or reviewer scope disagreement, record a stable `REVIEW_ESCAPE` identifier, the distinct family and affected scope, and the fixed artifact/range/fingerprint. Use exactly one bounded, read-only consultation for that identifier, whether or not a PR exists. The configured Pi consultation surface is the `oracle` subagent, pinned to `openai-codex/gpt-5.6-sol` with high reasoning. The consultation is advisory only: it may not edit or apply fixes, become implementation authority, or reroute implementation through another persona. Record its disposition; never repeat consultation for the same unresolved identifier or rename the family to restart the budget. A materially separate later failure-family/scope identifier may receive its own one consultation whether discovered pre-PR, during an authorized adversarial pass, or from later PR feedback.
- Verify and consume the disposition exactly once. Verified reject/reclassify evidence clears that family and permits the phase to continue without an adversarial pass. Revert/narrow/defer follows its stated path. A user/product/scope disposition stops for that decision. Only `authorize one further bounded adversarial fix/review pass` starts the pass. If disposition evidence cannot be verified or its stated path cannot be completed within current authority, report that specific unresolved blocker.
- When authorized, audit the fixed candidate branch/diff for sibling instances in the named family: the same assumption, edge case, API contract, missing validation, lifecycle/state transition, analogous callsites, and tests that should have failed but did not. Use the existing read-only `reviewer` for the adversarial pass at every risk level. Run one bounded pass over the named family, allow the driving agent one bounded fix attempt for in-scope findings, and run the same reviewer pass once after fixes. This route has no PR prerequisite. Do not restart the ordinary three-round budget or review until clean.
- Independent future enhancements, architecture improvements, polish, and unrelated defects do not block phase advancement and must not expand the change.

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

#### Verification Convergence Budget

Full-suite gates follow the `run-plan` skill's Verification Convergence Budget: three attempts at the same gate without a new distinct root cause, or 90 minutes of attributable gate time, whichever comes first (repo-local guidance may override; record the gate's normal green-run duration). At exhaustion, classify each residual failure — introduced vs. inherited (inherited requires reproduction at the merge-base/target, and a domain this change newly makes reachable is introduced) and functional vs. infra/cosmetic (no approved tolerance means `QUESTION`, not cosmetic). Failing tests that pass in isolation/serial while the failure point moves between runs are flake evidence: certify on the serial evidence and disclose. All residuals inherited or infra/cosmetic with targeted verification green → stop with the classification and the ship/keep-fixing question (draft-PR disposition when a PR boundary applies); any introduced or functional residual is in scope — fix it or report it as the blocker.
