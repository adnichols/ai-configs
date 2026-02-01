---
description: Create or update a single-file execution plan (spec + phases + progress) from validated codebase research
argument-hint: '<slug | "short description" | thoughts/plans/<slug>.md>'
---

# Plan (Single File)

Turn the validated research from this conversation into a single resumable plan document that contains both the specification and the execution guidance.

This command produces (or updates):

- `thoughts/plans/<slug>.md`

## Inputs

Argument (`$ARGUMENTS`) is either:

- A slug (recommended), e.g. `worktree-cleanup`
- A short description (derive a slug)
- A path to an existing `.md` plan file (treat it as the plan path)

## Output Contract

Write exactly one file:

- `thoughts/plans/<slug>.md`

Do not create `spec.md`, `tasks.md`, or per-plan directories unless the user explicitly asks.

Legacy bundles:

- If a legacy bundle exists at `thoughts/plans/<slug>/spec.md` and/or `thoughts/plans/<slug>/tasks.md`, you may read it for migration.
- Do not delete or modify legacy bundle files.

## Process

### 1) Resolve Plan Path

1. If `$ARGUMENTS` looks like a path to an existing `.md` file, treat it as `plan_path`.
2. Otherwise derive `slug` from `$ARGUMENTS`.
   - Use lowercase, digits, and hyphens only.
   - If multiple plausible slugs exist, ask once with `question` and use the user's choice.
3. Set `plan_path` to `thoughts/plans/<slug>.md`.
4. Ensure `thoughts/plans/` exists (create it if missing).

### 2) Read Existing Plan (If Present)

If `plan_path` exists, read it fully.

Preserve existing state:

- Any completed checkboxes (`[x]`) in `## Progress` and their IDs (do not renumber)
- Any existing entries in `## Decisions / Deviations Log`
- Any existing entries in `## Plan Changelog` (append a new entry when regenerating)

Legacy migration support (read-only; do not delete legacy files):

- If `thoughts/plans/<slug>/spec.md` and/or `thoughts/plans/<slug>/tasks.md` exist, read them.
- Prefer the legacy spec as the source of intent.
- If legacy tasks contain completed items, convert that state into coarse phase completion in `## Progress`.
  - Do not copy long checklists into the new plan.

### 3) Deep Research and Validation

Validate key claims from the conversation by directly inspecting the codebase:

- Locate the relevant files and existing patterns
- Confirm APIs, data shapes, configuration, and constraints
- Identify integration points and risks

Use `Glob`, `Grep`, and `Read` for targeted research. Use `Task(subagent_type="explore")` only for broad searches.

### 4) Write `plan_path`

Write (or update) `plan_path` with:

- Goal / Non-goals
- Current State (Validated)
- Proposed Approach
- Phases (`## Phase 1: ...`, `## Phase 2: ...`, ...)
  - Prose-first; do not create per-step checklists inside phases.
  - Each phase MUST include:
    - `### End State` (observable outcomes)
    - `### Work` (high-level guidance)
    - `### Verify` (explicit commands and/or manual checks)
- Acceptance Criteria (observable outcomes)
- Verification Strategy
  - Tests are supporting evidence, not the definition of correctness.
  - Do not change product code merely to satisfy a failing test when acceptance criteria + observed behavior indicate correctness.
- Resume Instructions (Agent)
  - Read this document fully.
  - Identify the first unchecked item in `## Progress`.
  - Proceed autonomously phase-by-phase.
  - Update `## Progress` only when a phase is complete; do not stop after updating progress.
  - Ask the user only for an unresolvable decision.
- Progress
  - A small checkbox list (4-10 items max).
  - Stable IDs (`P1`, `P2`, ...) that correspond to phase headers.
  - Checkboxes MUST appear only in `## Progress`.
- Decisions / Deviations Log (append-only)
- Open Questions / Decision Points
- Plan Changelog (append-only; add a new entry when regenerating)

Keep scope flexible: there are no special restrictions beyond the repository's existing guardrails and the user's stated intent.

### 5) Consistency Pass

Before finishing:

- Every acceptance criterion has at least one phase `### Verify` item that provides evidence.
- Every progress checkbox corresponds to a phase header.
- Phase ordering and naming is consistent across phases, progress, and acceptance criteria.

## Next Steps

- Review the plan:
  - `/review:change thoughts/plans/<slug>.md`
- Execute:
  - `/dev:run thoughts/plans/<slug>.md`
