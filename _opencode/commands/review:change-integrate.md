---
description: Integrate review comments into a change plan (single-file spec + phases + progress)
argument-hint: '<existing-plan-path | plan slug | legacy: <spec> <tasks> | legacy: <directory containing spec.md and tasks.md>'
---

# Integrate Change Review Comments (Single Plan File)

Integrate all inline review comments in the change plan, producing a clean, updated plan.

Inputs: $ARGUMENTS

## Core Rule

The plan is the authority. Integrate feedback into the plan while preserving progress state.

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

- Apply edits directly to the plan.
- Remove each resolved inline review comment.
- If feedback implies adding or changing requirements, update:
  - Locked Decisions
  - Goal/Non-goals / Acceptance Criteria
  - `## Progress` if phase structure changes
  - The impacted phase(s) `### End State` / `### Work` / `### Verify`
  - `### Tests first` sections so they still describe the intended user-visible behavior
  - `Resume Instructions (Agent)` if needed
- If review feedback establishes that a dependency/library evaluation checkpoint was missing or under-specified, preserve or add that decision explicitly in the cleaned plan.
- If a review comment shows that custom implementation was proposed without adequate library research, integrate the requirement to evaluate official SDKs / well-maintained libraries instead of silently resolving or deleting the issue.
- Append a new entry to `## Plan Changelog` describing what changed.

### 5) Final Validation

- No `[REVIEW:...]` comments remain.
- `## Progress` still corresponds to the phase headers.
- Each acceptance criterion has at least one verification step.
- Each phase has `### End State`, `### Tests first`, `### Work`, and `### Verify`.
- The plan has `Resume Instructions (Agent)` and `## Decisions / Deviations Log`.
- Required dependency/library evaluation decisions established during review remain present in the final clean plan.
- The plan does not leave unresolved `Open Questions`, `Decision Points`, or equivalent unresolved-decision sections.

### 6) Overall Plan State

- Resolve every important question before considering integration complete.
- If the codebase, existing specs, product-intent docs, or plan context answer a question with high confidence, answer it directly in the plan.
- If a question cannot be answered with high confidence, ask the user with the `question` tool.
- Incorporate the user's answer into the plan and re-check the whole document for any downstream phase updates needed.
- Do not leave an `Open Questions` section or any unresolved-decision placeholder in the final plan.
- If review established that non-trivial build-vs-buy work needs a dependency/library evaluation checkpoint, the final plan is not complete until that decision is documented.
---

## Next Step

After successful integration:

```
/cmd:execute-plan <plan path | plan slug>
```

If the user already knows they want full lifecycle execution, `/run-plan <plan path | plan slug>` is the default next step. `/dev:run <plan path | plan slug>` remains the direct execution-only path.

Stop there; do not proceed automatically.
