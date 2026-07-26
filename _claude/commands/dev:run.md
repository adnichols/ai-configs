---
description: Execute a single-file plan with resumable progress tracking and one reviewer-subagent pass per phase
argument-hint: '<slug | existing-plan-path>'
---

# Run Plan (Single File)

Execute a single plan document (spec + phases + progress) in a straightforward, single-agent way:

- Follow the plan, but keep implementation flexibility.
- Track progress by updating `## Progress` in the plan file.
- Run exactly one read-only `reviewer` subagent pass after each phase before marking it complete.

## Inputs

`$ARGUMENTS` may be:

- A slug
- A direct path to a plan file in the repo's active plan format

## Process

### 0) Autopilot Rules

- Execute continuously; do not pause between phases.
- Do not stop after a status update (e.g., "I'm starting Phase 1" or "gathering context").
- Every response must either (a) take the next concrete action by actually invoking a tool (read/search/edit/run) or updating the plan file, or (b) ask for user input due to an unresolvable decision. Narration is not an action.
- If unsure, investigate and retry until evidence supports a decision; do not ask the user just for uncertainty.
- Use `question` only when a decision between viable options requires user input due to insufficient evidence.

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

Immediately begin execution:

- Identify the first unchecked item in `## Progress`.
- Find the corresponding phase section and start implementing it right away; do not pause to recap the plan.

### 3) Execute Phase-by-Phase

For each phase in order (as tracked by `## Progress`):

1. Implement the phase as written.
2. Run the phase `### Verify` steps.
3. Launch the repository-owned, read-only `reviewer` subagent (`claude-sonnet-5`, high effort) with the plan path, phase scope, changed files, relevant diff, and verification results. It must review the promised slice only and must not edit files or execute verification.
4. If the reviewer clears the phase, immediately flip its checkbox from `- [ ]` to `- [x]` in `## Progress`.
5. If the reviewer reports an in-scope blocker, fix it, run targeted verification, and launch one targeted rereview limited to the finding and resulting edits. A third review is permitted only when the preceding fix introduced or exposed a new concrete blocker; otherwise report the convergence or scope blocker.
6. If implementation or review required a decision or revealed a constraint, append a structured entry to `## Decisions / Deviations Log` in the plan file.

#### Autonomy / Do Not Pause

- Proceed autonomously through phases.
- If you are not blocked, do not hand control back to the user; take the next concrete action (run commands, edit files, update progress) until you either finish or hit an unresolvable decision.
- Do not stop after announcing intent, listing next steps, or completing "context gathering".
- Only stop to ask the user when you hit an unresolvable decision that cannot be answered from the plan or codebase.

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

When all items in `## Progress` are complete:

- Ensure the plan file reflects completion accurately.
- Run any verification commands listed in the plan's `Verification Strategy` and/or phase `### Verify` sections.

#### Verification Convergence Budget

Full-suite gates follow the `run-plan` skill's Verification Convergence Budget: three attempts at the same gate without a new distinct root cause, or 90 minutes of attributable gate time, whichever comes first (repo-local guidance may override; record the gate's normal green-run duration). At exhaustion, classify each residual failure — introduced vs. inherited (inherited requires reproduction at the merge-base/target, and a domain this change newly makes reachable is introduced) and functional vs. infra/cosmetic (no approved tolerance means `QUESTION`, not cosmetic). Failing tests that pass in isolation/serial while the failure point moves between runs are flake evidence: certify on the serial evidence and disclose. All residuals inherited or infra/cosmetic with targeted verification green → stop with the classification and the ship/keep-fixing question (draft-PR disposition when a PR boundary applies); any introduced or functional residual is in scope — fix it or report it as the blocker.
