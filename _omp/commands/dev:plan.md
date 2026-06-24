---
description: Create or update a single-file execution plan (spec + phases + progress) from validated codebase research
argument-hint: '<slug | "short description" | existing-plan-path>'
---

# Plan (Single File)

Turn the validated research from this conversation into a single resumable plan document that contains both the specification and the execution guidance.

This command has no default plan file format. Determine the active plan artifact from repo-local guidance (`AGENTS.md`, `thoughts/plans/AGENTS.md`, local planning skills, or an existing plan path supplied by the user). If local guidance says active plans are HTML or names a checked-in plan server/validator, obey that local contract exactly.

If repo guidance does not define the active plan artifact format/path and the user did not supply an existing plan path, ask one targeted question and stop. Do not assume markdown.

## Inputs

Argument (`$ARGUMENTS`) is either:

- A slug (recommended), e.g. `worktree-cleanup`
- A short description (derive a slug)
- A path to an existing plan file (treat it as the plan path)

## Output Contract

Write exactly one active plan file: `plan_path`, resolved from repo-local guidance or an existing plan path supplied by the user.

Do not create `spec.md`, `tasks.md`, per-plan directories, same-slug markdown/JSON companions for an HTML-plan repo, or any non-plan file unless the user explicitly asks.

Legacy bundles:

- If a legacy bundle exists at `thoughts/plans/<slug>/spec.md` and/or `thoughts/plans/<slug>/tasks.md`, you may read it for migration.
- Do not delete or modify legacy bundle files.

## Process

### 1) Resolve Plan Path

1. If `$ARGUMENTS` looks like a path to an existing plan file, treat it as `plan_path`.
2. Otherwise derive `slug` from `$ARGUMENTS`.
   - Use lowercase, digits, and hyphens only.
   - If multiple plausible slugs exist, ask once with `question` and use the user's choice.
3. Set `plan_path` to the repo's active plan path from local guidance. If local guidance does not define one and the user did not supply an existing plan path, ask one targeted question and stop. Do not infer a markdown path.
4. Ensure the parent directory for `plan_path` exists (create it if missing).

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

If local guidance names an HTML plan contract, template, validator, or plan service, read those docs now. Use the checked-in tooling they name; do not create markdown companions for an HTML-plan repo and do not substitute an ad hoc plan server.

Validate key claims from the conversation by directly inspecting the codebase:

- Locate the relevant files and existing patterns
- Confirm APIs, data shapes, configuration, and constraints
- Identify integration points and risks
- Load the shared `product-principles` skill when the work affects workflows, defaults, onboarding, recovery behavior, error handling, architecture, or regression strategy
- Identify the simplest supported workflow and which inputs should be optional because the system can infer or heal them
- Audit `AGENTS.md`, product-intent docs, onboarding/install docs, config/status surfaces, and tests for dissonance with that default-path contract

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

Keep the plan faithful to the validated source scope and repo evidence. Include only work that is critical to achieving the stated goal and verifying it.
If the requested scope is vague, narrow it by sharpening Goal / Non-goals or other scoped language instead of widening the phase list.
Do not add adjacent cleanup, optional follow-ups, broader parity not required by the source intent, or extra explicitness that does not materially change go/no-go confidence unless validated repo evidence shows they are necessary for success.
If the plan is rendered or delivered as HTML, use the standard reviewer layout: a dark-mode visual theme with an explicit dark background, light foreground text, readable muted text, accessible link/accent colors, `color-scheme: dark`, and a two-column page with a concise sections navbar in a left sidebar and plan content on the right. The left navbar must remain available while reading long plans by being sticky and independently scrollable (`max-height` plus `overflow-y: auto`) and must collapse to one column on narrow screens. Do not let color mode or navigation layout depend on agent preference, browser defaults, or OS defaults.

For product-facing work, make the plan explicit about the default workflow, inferred defaults, self-healing behavior, actionable error guidance, and any repo-doc/test updates required to stay aligned.

### 5) Consistency Pass

Before finishing:

- Every acceptance criterion has at least one phase `### Verify` item that provides evidence.
- Every progress checkbox corresponds to a phase header.
- Phase ordering and naming is consistent across phases, progress, and acceptance criteria.

## Next Steps

- Review the plan:
  - `/review:change <plan_path>`
- After the reviewed plan is ready to continue, use the canonical handoff:
  - `/cmd:execute-plan <plan_path>`
