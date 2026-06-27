---
description: Integrate review comments into a change plan (single-file spec + phases + progress)
argument-hint: '<existing-plan-path | plan slug | legacy: <spec> <tasks> | legacy: <directory containing spec.md and tasks.md>'
---

# Integrate Change Review Comments (Single Plan File)

Integrate all inline review comments in the change plan, producing a clean, updated plan.

Inputs: $ARGUMENTS

## Core Rule

The plan is the authority. Integrate only material review feedback needed to execute the stated goal while preserving non-goals and progress state.

## Process

### 0) Resolve Inputs

Preferred input:

- A single plan file in the repo's active plan format

Accept legacy inputs for migration only:

- `<spec_path> <tasks_path>`
- A directory containing `spec.md` and `tasks.md`

Rules:

- If `$ARGUMENTS` starts with `@`, strip the leading `@` and treat as workspace-relative.
- If a single argument is an existing plan file, treat it as `plan_path`.
- If a single argument is a slug, resolve it using repo-local active plan guidance. Do not infer a markdown path; if guidance does not define slug resolution, ask for an explicit plan path.
- Only migrate a legacy bundle when repo-local guidance explicitly allows migration to the repo's active plan format; otherwise ask for an explicit existing plan path.

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

- Apply edits directly to the plan with `edit` unless a deliberate full-file rewrite is required.
- Remove each resolved inline review comment.
- Only incorporate review findings that expose blockers, material risks, or missing decisions required for the plan's stated goal and non-goals.
- Do not expand required scope for nice-to-haves, opportunistic cleanup, adjacent surfaces, or extra detail that does not change readiness.
- If an optional comment is worth preserving, record it as explicit non-goal or follow-up context rather than new required plan scope.
- If material feedback implies adding or changing requirements, update:
  - Goal/Non-goals / Acceptance Criteria
  - The impacted phase(s) `### End State` / `### Work` / `### Verify`
  - `Resume Instructions (Agent)` if needed
- Append a new entry to `## Plan Changelog` describing what changed.

### 5) Final Validation

- No `[REVIEW:...]` comments remain.
- `## Progress` still corresponds to the phase headers.
- Each acceptance criterion has at least one verification step.
- Any new required scope is justified by a material review finding that changes readiness.

### 6) Overall Plan State

- Identify only open questions or decisions that materially block execution or readiness.
- Do not surface low-confidence suggestions or optional improvements as required plan changes.
- If you have specific issues you know, with high confidence that you need input from the user on, then ask those using the question tool.
- If you've asked questions with the question tool, incorporate those answers into the final plan and re-assess whether there are more open questions.
---

## Next Step

After successful integration:

```
/cmd:execute-plan <plan path | plan slug>
```

If the user already knows they want full lifecycle execution, `/run-plan <plan path | plan slug>` is the default next step. `/dev:run <plan path | plan slug>` remains the direct execution-only path.

Stop there; do not proceed automatically.
