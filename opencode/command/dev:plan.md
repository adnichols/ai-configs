---
description: Create or update a plan bundle (spec + tasks) from validated codebase research
argument-hint: "<slug | \"short description\">"
---

# Plan Bundle (Spec + Tasks)

Turn the validated research from this conversation into a plan bundle containing a phased specification and an executable task list.

This command produces (or updates) a directory:

- `thoughts/plans/<slug>/spec.md`
- `thoughts/plans/<slug>/tasks.md`

## Inputs

Argument (`$ARGUMENTS`) is either:

- A slug (recommended), e.g. `worktree-cleanup`
- A short description (derive a slug)

## Output Contract

All files for this change live under a single directory:

- `thoughts/plans/<slug>/spec.md`
- `thoughts/plans/<slug>/tasks.md`

Filenames are fixed. Do not create additional plan files unless the user explicitly asks.

## Process

### 1) Resolve Bundle Directory

1. If `$ARGUMENTS` looks like a path to an existing directory, treat it as the bundle directory.
2. Otherwise derive `slug` from `$ARGUMENTS`.
   - Use lowercase, digits, and hyphens only.
   - If multiple plausible slugs exist, ask once with `question` and use the user's choice.
3. Set bundle directory to `thoughts/plans/<slug>/`.
4. Ensure the directory exists (create it if missing).

### 2) Read Existing Bundle (If Present)

If either file exists, read both:

- `thoughts/plans/<slug>/spec.md`
- `thoughts/plans/<slug>/tasks.md`

If `tasks.md` contains any completed checkboxes (`[x]`), you MUST preserve completed tasks and their IDs. Do not renumber tasks.

### 3) Deep Research and Validation

Validate key claims from the conversation by directly inspecting the codebase:

- Locate the relevant files and existing patterns
- Confirm APIs, data shapes, configuration, and constraints
- Identify integration points and risks

Use `Glob`, `Grep`, and `Read` for targeted research. Use `Task(subagent_type="explore")` only for broad searches.

### 4) Write `spec.md`

Write (or update) `thoughts/plans/<slug>/spec.md` with:

- Goal / Non-goals
- Current State (Validated)
- Proposed Approach
- Phases (`## Phase 1: ...`, `## Phase 2: ...`, ...)
- Acceptance Criteria (observable outcomes)
- Verification Strategy
  - Tests are supporting evidence, not the definition of correctness.
  - Do not change product code merely to satisfy a failing test when acceptance criteria + observed behavior indicate correctness.
- Open Questions / Decision Points
- Plan Changelog (append-only; add a new entry when regenerating)

Keep scope flexible: there are no special restrictions beyond the repository's existing guardrails and the user's stated intent.

### 5) Write `tasks.md`

Write (or update) `thoughts/plans/<slug>/tasks.md` as an executable checklist that matches `spec.md` phases.

Requirements:

- Include YAML frontmatter with:
  - `slug: <slug>`
  - `spec: ./spec.md`
- Use the same phase headers as `spec.md`.
- Each task line is a checkbox (`- [ ]` / `- [x]`) with a stable ID (e.g. `P1.1`, `P1.2`).
- Each phase contains at least one explicit verification task (manual verification is first-class).
- Include `## Deviations Log` (empty initially). Implementation will append structured entries here.

### 6) Consistency Pass

Before finishing:

- Every acceptance criterion has at least one task that provides evidence.
- Every task is justified by something in `spec.md`.
- Phase ordering and naming is consistent across both files.

## Next Steps

- Review the bundle:
  - `/review:spec thoughts/plans/<slug>/spec.md`
  - `/review:tasks thoughts/plans/<slug>/tasks.md`
- Execute tasks:
  - `/dev:run <slug>`
