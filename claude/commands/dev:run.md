---
description: Execute a plan bundle task list with lightweight tracking (no orchestrator-only rigor)
argument-hint: "<slug | thoughts/plans/<slug>/ | path/to/tasks.md>"
---

# Run Plan Tasks

Execute `thoughts/plans/<slug>/tasks.md` in a straightforward, single-agent way:

- Follow the plan, but keep implementation flexibility.
- Keep the task list accurately checked off.
- After each phase, perform a reflection step that updates spec/tasks.

## Inputs

`$ARGUMENTS` may be:

- A slug
- A bundle directory path (`thoughts/plans/<slug>/`)
- A direct path to `tasks.md`

## Process

### 1) Resolve Bundle

Resolve to:

- `bundle_dir`
- `spec_path` (must be `spec.md`)
- `tasks_path` (must be `tasks.md`)

Rules:

- If `$ARGUMENTS` is a directory: use `<dir>/spec.md` and `<dir>/tasks.md`.
- If `$ARGUMENTS` is `tasks.md`: read YAML frontmatter and use `spec:`.
- If `$ARGUMENTS` is a slug: use `thoughts/plans/<slug>/spec.md` and `thoughts/plans/<slug>/tasks.md`.

### 2) Read Plan

Read both files fully:

- `spec_path`
- `tasks_path`

Use `spec.md` as the source of intent. Use `tasks.md` as the progress tracker.

### 3) Execute Tasks Phase-by-Phase

For each phase in order:

1. Implement tasks as written.
2. After completing each task, immediately flip it from `- [ ]` to `- [x]` in `tasks.md`.
3. If implementation requires a decision or reveals a constraint, append an entry to `## Deviations Log` in `tasks.md`.

#### Tests Policy

- You MAY add/update tests when behavior changes.
- You MAY refactor for testability.
- You MUST NOT change product code merely to satisfy a failing test if acceptance criteria + observed behavior indicate the code is correct.
  - In that case, fix the test or update the test assumptions (and log the decision).

### 4) Reflection After Each Completed Phase

When all tasks in a phase are checked:

- Run the reflection step described by `/dev:reflect` against this bundle.
- Apply high-confidence updates (based on Deviations Log and direct evidence).
- Ask the user only when changes affect requirements/scope or when there are multiple viable interpretations.

Then continue to the next phase.

### 5) Completion

When all phases are complete:

- Ensure `tasks.md` reflects completion accurately.
- Consider running `/dev:4:validate <slug>` for independent verification.
