---
description: Integrate review comments into a change plan (single-file spec + phases + progress)
argument-hint: '<path to plan.md | plan slug | legacy: <spec> <tasks> | legacy: <directory containing spec.md and tasks.md>'
---

# Integrate Change Review Comments (Single Plan File)

Integrate all inline review comments in the change plan, producing a clean, updated plan.

Inputs: $ARGUMENTS

## Core Rule

The plan is the authority. Integrate feedback into the plan while preserving progress state.

## Process

### 0) Resolve Inputs

Preferred input:

- A single plan file: `thoughts/plans/<slug>.md`

Accept legacy inputs for migration only:

- `<spec_path> <tasks_path>`
- A directory containing `spec.md` and `tasks.md`

Rules:

- If `$ARGUMENTS` starts with `@`, strip the leading `@` and treat as workspace-relative.
- If a single argument is an existing `.md` file, treat it as `plan_path`.
- If a single argument is a slug, resolve to `thoughts/plans/<slug>.md`.
- If the plan file does not exist but a legacy bundle exists for the slug, migrate to `thoughts/plans/<slug>.md` (do not modify legacy files) and integrate into the migrated plan.

If multiple candidates match or a required file is missing, ask for an explicit plan file path.

### 1) Read Plan

Read `plan_path` fully.

Preserve:

- Any completed checkboxes in `## Progress` and their IDs (do not renumber)

### 2) Extract Inline Review Comments

Scan for inline review tags:

```markdown
[REVIEW:Reviewer Name] comment text [/REVIEW]
[REVIEW] comment text [/REVIEW]
```

If no inline review comments exist, inform the user and abort (nothing to integrate).

### 3) Explore Codebase Only When Needed

For any feedback that depends on feasibility or existing patterns, explore the codebase to resolve it.

Use the Task tool with `subagent_type=Explore`.

### 4) Integrate Updates

- Apply edits directly to the plan.
- Remove each resolved inline review comment.
- If feedback implies adding or changing requirements, update:
  - Goal/Non-goals / Acceptance Criteria
  - The impacted phase(s) `### End State` / `### Work` / `### Verify`
  - `Resume Instructions (Agent)` if needed
- Append a new entry to `## Plan Changelog` describing what changed.

### 5) Final Validation

- No `[REVIEW:...]` comments remain.
- `## Progress` still corresponds to the phase headers.
- Each acceptance criterion has at least one verification step.

---

## Next Step

After successful integration:

```
/dev:run <plan path | plan slug>
```

Stop there; do not proceed automatically.
