---
description: Reflect on a completed phase and propagate decisions into future phases (single plan file)
argument-hint: '<slug | thoughts/plans/<slug>.md | path/to/plan.md> [--phase N] [--dry-run]'
---

# Phase Reflection (Single Plan File)

After a phase is completed, evaluate what changed versus the plan and update the plan file to reflect reality.

## Inputs

`$ARGUMENTS` may include:

- A slug or plan path
- Optional `--phase N`
- Optional `--dry-run`

## Process Flow

```
PARSE -> READ -> GATHER_EVIDENCE -> EXTRACT_DECISIONS -> ANALYZE_IMPACT -> PROPOSE_UPDATES -> APPROVAL -> APPLY
```

## Process

### 1) Resolve Plan and Phase

Resolve:

- `plan_path`: `thoughts/plans/<slug>.md` (or the provided path)

Determine the completed phase:

- If `--phase N` provided, use Phase N.
- Otherwise pick the highest phase that is marked complete in `## Progress`.

### 2) Read Plan

Read `plan_path` fully. Extract:

- The Phase N section
- Any Phase N-related entries in `## Decisions / Deviations Log`
- The phase verify steps

### 3) Gather Evidence

Prioritize:

1. `## Decisions / Deviations Log` entries relevant to the phase
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

Update the plan to reduce future ambiguity:

A) Phase Retrospective (within the phase section)

- Add (or update) a `### Retrospective` subsection in the Phase N section containing:
  - Status: completed as specified / completed with modifications / partially completed
  - Key decisions + rationale
  - Evidence pointers (paths/commits)
  - Learnings for next phases

B) Propagate to Future Phases

For each future phase impacted by a decision, insert an inline HTML annotation above the affected subsection:

```html
<!-- PROPAGATED from Phase N (YYYY-MM-DD):
Decision: D#: <title>
Impact: <what changed>
Action: <what future implementer should do>
Source: <plan log entry or commit/handoff>
-->
```

C) Update Progress/Verification Text

- If the phase verify steps were wrong or incomplete, correct them.
- Do not uncheck completed progress items.

### 6) Approval and Apply

If `--dry-run`, print an inventory of exact edits and stop.

Otherwise:

- Auto-apply high-confidence updates grounded in logged decisions and evidence.
- Use `question` for low-confidence updates, scope changes, or requirement-affecting decisions.

## Output

- `plan_path` updated with phase retrospective and propagated annotations
