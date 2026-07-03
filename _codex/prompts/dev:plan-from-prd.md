---
description: Create or update a single-file execution plan from a reviewed PRD delta
argument-hint: '<prd slug | existing-prd-path>'
---

# Run Plan from PRD (Single File)

Turn a reviewed PRD delta into a single resumable execution plan document.

This command produces (or updates):

- `<plan_path>`

## Inputs

Argument (`$ARGUMENTS`) is either:

- A PRD slug, usually matching `prd-<slug>`
- A path to an existing reviewed PRD file (`.md`)

## Output Contract

Write exactly one file:

- `<plan_path>`

Do not create `spec.md`, `tasks.md`, per-plan directories, same-slug markdown/JSON companions for an HTML-plan repo, or any non-plan file unless the user explicitly asks.

## 1) Resolve PRD Path and Plan Path

1. If `$ARGUMENTS` starts with `@`, strip the leading `@` and treat it as a workspace-relative path.
2. If `$ARGUMENTS` is a path to an existing `.md` file, use it as `prd_path`.
3. Otherwise derive `slug` from `$ARGUMENTS`.
   - Use lowercase, digits, and hyphens only.
   - If the slug does not already start with `prd-`, treat the input as a PRD stem and resolve `thoughts/plans/prd-<slug>.md`.
4. Ensure `prd_path` exists.
5. Derive `prd_slug` from the PRD filename by stripping only the `.md` suffix.
6. Derive `plan_slug` from the PRD filename by stripping a leading `prd-` prefix when present.
7. Set:
   - `plan_path` = the repo-local active plan path for `plan_slug`; do not infer a markdown path
   - `review_dir` = `thoughts/validation/prd-reviews/<prd_slug>/`
   - `review_status_path` = `thoughts/validation/prd-reviews/<prd_slug>/review-status.json`

If repo guidance does not define the active plan artifact format/path, ask one targeted question and stop.

If the reviewed PRD file cannot be resolved, stop and tell the user that `/dev:plan-from-prd` requires an explicit existing reviewed PRD file or slug.

## 2) Validate the Reviewed PRD

Read `prd_path` fully and confirm it is actually review-ready.

Required checks:

- The PRD contains the required `[REQUIRED]` sections.
- No unresolved review comments remain (`[REVIEW:` tags must be gone).
- The PRD readiness decision is explicit enough to hand off to execution planning.
- `review_status_path` exists and is valid JSON.
- `review_status_path` reports:
  - `schemaVersion: 1`
  - `prdPath` exactly matching the resolved PRD path in workspace-relative form
  - `reviewDir` exactly matching `review_dir` in workspace-relative form
  - `status: "approved"`
  - `reviewersExpected: 7`
  - `reviewersCompleted: 7`
  - `integratedCount` present as a number from `0` to `7`
  - `pendingCount: 0`
  - `reviewerFilesRemoved: true`
- The review status file is not stale: its modification time must be the same as or newer than the PRD file’s modification time.

If any of these checks fail, stop and tell the user to rerun `/review:prd <prd-path>` before planning.

## 3) Plan Creation Contract

Use the reviewed PRD as the source of truth for the plan.

Planning requirements:

- Write exactly one plan file at `plan_path`.
- Preserve the single-file plan structure used by `/dev:plan`:
  - Goal / Non-goals
  - Current State (Validated)
  - Proposed Approach
  - Phases with `### End State`, `### Work`, and `### Verify`
  - Acceptance Criteria
  - Verification Strategy
  - Resume Instructions (Agent)
  - Progress
  - Decisions / Deviations Log
  - Open Questions / Decision Points
  - Plan Changelog
- Keep the plan faithful to the reviewed PRD delta and repo guidance.
- Do not broaden scope beyond the reviewed PRD.
- If the PRD is ambiguous, resolve it by inspecting the repo and the reviewed PRD before asking the user.
- Ask the user only if a decision remains genuinely unresolvable.

## 4) Completion

When the plan is complete:

- Ensure the plan file reflects the PRD-to-plan handoff accurately.
- Leave the reviewed PRD, `integration-ledger.md`, and `review-status.json` untouched except for read-only inspection.
- Provide the user with the generated plan path.
