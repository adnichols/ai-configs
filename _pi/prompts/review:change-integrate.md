---
description: Integrate review comments into a change plan (single-file spec + phases + progress)
argument-hint: '<existing-plan-path | plan slug | legacy: <spec> <tasks> | legacy: <directory containing spec.md and tasks.md>'
---

# Integrate Change Review Comments (Single Plan File)

Integrate all inline review comments in the change plan, producing a clean, updated plan.

Inputs: $ARGUMENTS

## Core Rule

The plan is the authority. Integrate only material feedback into the plan while preserving progress state.

## Materiality Filter

Treat review comments as required only when they identify a blocker, material risk, incorrect assumption, or missing decision/work needed to execute the plan's stated goal, non-goals, acceptance criteria, or validated source scope.

- Do not expand required scope to satisfy optional comments, opportunistic cleanup, adjacent surfaces, or extra detail that would not change readiness.
- If optional feedback is worth retaining, record it as an explicit non-goal or documented out-of-scope follow-up instead of turning it into required plan work. Never mark plan-required work, verification gaps, or acceptance-criteria gaps as optional/deferred.

## Tooling Discipline

- Use `edit` for targeted plan mutations.
- Use `write` only for an intentional whole-file rewrite after reading the full plan, and only when `edit` is genuinely impractical.
- Treat `bash` as read-only in this workflow.
- Do not modify the plan via mutation scripts (`python`, `python3`, `node`, `perl`, `ruby`, `sed -i`, `awk`, heredoc rewrites, or similar).
- If an `edit` call fails, reread the relevant span and retry with a more specific `oldText`; do not fall back to a mutation script.

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

Use the available repo exploration tools in this session.

### 4) Integrate Updates

- Classify each review comment as material or optional before editing the plan.
- Apply edits directly to the plan with `edit` unless a deliberate full-file rewrite is required.
- HTML plans are first-class inputs; preserve valid semantic HTML while integrating and removing review comments.
- Remove each resolved inline review comment.
- Integrate only material findings that affect readiness for the stated scope.
- If feedback implies adding or changing requirements, do so only when the plan's stated goal, non-goals, acceptance criteria, or validated source scope require it. Then update:
  - Goal/Non-goals / Acceptance Criteria
  - The impacted phase(s) `### Tests first` / `### End State` / `### Work` / `### Verify`
  - `## Progress` if a review finding requires splitting an oversized unchecked phase into smaller same-scope slices
  - `Resume Instructions (Agent)` if needed
- Preserve scope when integrating chunking feedback: reviewers may tighten or split the plan, but must not expand the work.
- For optional or nice-to-have comments, remove the inline comment without expanding plan scope. If preserving the note helps later work, record it as a concise non-goal or documented out-of-scope follow-up note with evidence and a tracking destination instead of required work.
- Append a new entry to `## Plan Changelog` describing what changed.

### 5) Final Validation

- No `[REVIEW:...]` comments remain.
- `## Progress` still corresponds to the phase headers.
- Each phase still includes `### Tests first`, `### End State`, `### Work`, and `### Verify`.
- Each acceptance criterion has at least one verification step.
- Optional feedback was not converted into new required scope, and required plan/verification work was not mislabeled as optional or deferred.

### 6) Overall Plan State

- Identify only open questions or decisions that materially affect readiness for the stated scope.
- Provide only low-confidence decisions that would change execution readiness, not optional idea backlog.
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
