---
description: Reflect on a completed phase and propagate decisions into future phases (bundle-aware)
argument-hint: "<slug | thoughts/plans/<slug>/ | path/to/tasks.md> [--phase N] [--dry-run]"
---

# Phase Reflection (Bundle)

After a phase is completed, evaluate what changed versus the plan and update `spec.md` and `tasks.md` to reflect reality.

This is adapted from `claude/commands/dev:5:phase-review.md`, but operates on a single `spec.md` + `tasks.md` bundle.

## Inputs

`$ARGUMENTS` may include:

- A slug, bundle directory, or `tasks.md` path
- Optional `--phase N`
- Optional `--dry-run`

## Process Flow

```
PARSE -> READ -> GATHER_EVIDENCE -> EXTRACT_DECISIONS -> ANALYZE_IMPACT -> PROPOSE_UPDATES -> APPROVAL -> APPLY
```

## Process

### 1) Resolve Bundle and Phase

Resolve:

- `spec_path`: `thoughts/plans/<slug>/spec.md`
- `tasks_path`: `thoughts/plans/<slug>/tasks.md`

Determine the completed phase:

- If `--phase N` provided, use Phase N.
- Otherwise pick the highest phase where all tasks are `[x]`.

### 2) Read Files

Read fully:

- `spec_path`
- `tasks_path`

Extract:

- The Phase N section from `spec.md`
- The Phase N tasks and any Phase N entries in `## Deviations Log` from `tasks.md`

### 3) Gather Evidence

Prioritize:

1. `tasks.md` Deviations Log entries for the phase
2. Git history/diff relevant to the phase (recent commits, changed files)
3. Any linked artifacts (handoffs, validation reports)

### 4) Extract Decisions

Extract decisions in these categories:

- Uncertainty Resolved
- Scope Adjusted
- Pattern Discovered
- Constraint Identified
- API Contract Defined

If decisions are not explicitly logged, infer them carefully and mark them low-confidence.

### 5) Propose Updates

Update the bundle in a way that reduces future ambiguity:

A) Phase Retrospective (append to `spec.md`)

- Append (or update) a `## Phase Retrospective` section in `spec.md` containing:
  - Phase N status: completed as specified / completed with modifications / partially completed
  - Key decisions + rationale
  - Evidence pointers (paths/commits)
  - Learnings for next phases

B) Propagate to Future Phases (in `spec.md`)

For each future phase section impacted by a decision, insert an inline HTML annotation above the affected subsection:

```html
<!-- PROPAGATED from Phase N (YYYY-MM-DD):
Decision: D#: <title>
Impact: <what changed>
Action: <what future implementer should do>
Source: <tasks.md or commit/handoff>
-->
```

C) Update Future Tasks (in `tasks.md`)

- Add, clarify, or reorder future-phase tasks to align with the propagated reality.
- NEVER change already-completed tasks.
- Preserve task IDs; only append new IDs.

### 6) Approval and Apply

If `--dry-run`, print an inventory of exact edits and stop.

Otherwise:

- Auto-apply high-confidence updates grounded in Deviations Log.
- Use `question` for low-confidence updates, scope changes, or requirement-affecting decisions.

## Output

- `spec.md` updated with Phase Retrospective and propagated annotations
- `tasks.md` updated for future phases (if needed)
