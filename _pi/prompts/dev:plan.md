---
description: Create or update a single-file execution plan (spec + phases + progress) from validated codebase research
argument-hint: '<slug | "short description" | existing-plan-path>'
---

# Plan (Single File)

Turn the validated research from this conversation into a single resumable plan document that contains both the specification and the execution guidance.

This prompt has no default plan file format. Determine the active plan artifact from repo-local guidance (`AGENTS.md`, `thoughts/plans/AGENTS.md`, local planning skills, or an existing plan path supplied by the user). If local guidance says active plans are HTML or names a checked-in plan server/validator, obey that local contract exactly.

If repo guidance does not define the active plan artifact format/path and the user did not supply an existing plan path, ask one targeted question and stop. Do not assume markdown.

## Model routing

GPT-5.6 Sol medium is the normal repository-owned Pi route for planning and coding-plan work.

Use `scout` for bounded, read-only broad repository discovery before asking implementation agents to reason over files.

## Inputs

Argument (`$ARGUMENTS`) is either:

- A slug (recommended), e.g. `worktree-cleanup`
- A short description (derive a slug)
- A path to an existing plan file (treat it as the plan path)

## Output Contract

Write exactly one file: `plan_path`, resolved from repo-local guidance or an existing plan path supplied by the user.

Do not create `spec.md`, `tasks.md`, per-plan directories, same-slug markdown/JSON companions for an HTML-plan repo, or any non-plan file unless the user explicitly asks.

Plan readiness rules:

- If the work is ready to execute without inventing missing semantics, write `Status: execution-ready`.
- If foundational questions still remain but the next safe handoff is more research, write `Status: research-ready` and make the next research action explicit.
- If a foundational decision needs new user intent and the active artifact is an HTML plan with browser review, write a non-ready plan with a prominent `Decision Required` block so the user can decide through plan feedback. Include every viable option, a thorough explanation of each option's behavior/benefits/costs/risks/implementation and compatibility implications/reversibility, and the agent's recommendation with rationale, confidence, and evidence.
- If no browser-reviewed plan surface is available, ask exactly one targeted question directly and stop without writing the plan.

Legacy bundles:

- If a legacy bundle exists at `thoughts/plans/<slug>/spec.md` and/or `thoughts/plans/<slug>/tasks.md`, you may read it for migration.
- Do not delete or modify legacy bundle files.

## Process

### 1) Resolve Plan Path

1. If `$ARGUMENTS` looks like a path to an existing plan file, treat it as `plan_path`.
2. Otherwise derive `slug` from `$ARGUMENTS`.
   - Use lowercase, digits, and hyphens only.
   - If multiple plausible slugs exist, choose the clearest faithful slug from the request and repo conventions; mention the derived slug in the final planning summary.
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

If local guidance names an HTML plan contract, template, validator, or plan server, read those docs now. Use the checked-in tooling they name; do not create markdown companions for an HTML-plan repo and do not substitute an ad hoc plan server.

Validate key claims from the conversation by directly inspecting the codebase:

- Locate the relevant files and existing patterns
- Confirm APIs, data shapes, configuration, and constraints
- Identify integration points and risks
- Verify commands, paths, targets, and package names that later `### Verify` steps will rely on

Use `Glob`, `Grep`, and `Read` for targeted research. Keep discovery in the driving session by default; use `Task(subagent_type="scout")` only for a bounded read-only broad-search packet that materially benefits from isolated context and names the discovery question, allowed surfaces, evidence format, and stop condition.

### 4) Choose the Correct Readiness State

Before writing the plan, decide whether it is actually executable.

Treat these as foundational planning questions:

- missing contracts, migrations, rollout behavior, or compatibility behavior,
- unresolved acceptance criteria or externally visible semantics,
- missing verification commands or targets,
- uncertainty about how the work should be chunked into bounded execution slices.

Do not bury those unknowns in later phases just to keep the plan moving.

If you cannot mostly accurately estimate how much effort a phase involves from repo evidence, then the planning is not deep enough yet.

### 5) Write `plan_path`

Write (or update) `plan_path` with:

- Title
- Status
- Product-owner context near the top, before implementation history and technical detail. For non-trivial plans, use a scannable impact table or equivalent structured block that explains the plain-language situation for a reader with no issue/Linear context, why the work is needed now, the unmistakable conclusion (runtime/customer defect versus stale test or operational evidence), and separate impact on Customers, Runtime product behavior, Security / permissions, Testing / release confidence, and Deployment / migration. Lightweight plans must use at least concise labeled prose; say `No change` or `Not applicable` for unaffected dimensions.
- Apply the canonical `planning-workflow` `What's new` contract after Product-owner context and before Goal; a heading or surrounding-section restatement is insufficient.
- Apply the canonical `planning-workflow` integration-integrity planning contract: when triggered, load `integration-integrity` and include its Contract and distributed-integration inventory; do not add an empty inventory when no trigger applies.
- Apply its conditional planning-evidence checkpoint: triggered consumer/sibling evidence, moving-ground checks, falsification and production-path proof, residual risk, and expansion disposition belong in existing review sections. Do not require a standalone Socratic questionnaire.
- Goal / Non-goals
- Current State (Validated)
- Proposed Approach
- Acceptance Criteria (observable outcomes)
- Phases (`## Phase 1: ...`, `## Phase 2: ...`, ...)
  - Prose-first; do not create per-step checklists inside phases.
  - Each phase MUST be a **bounded execution slice**:
    - one coherent outcome,
    - one primary verification story,
    - limited enough coupling and affected surfaces that execution should usually finish without semantic replanning,
    - small enough that an executor should not need to invent missing semantics or split it just to understand what to do.
  - Break phases by effort, coupling, uncertainty, and verification breadth — not by work type labels.
  - If a phase contains multiple independently verifiable outcomes, materially different verification stories, or broad repo rediscovery, split it during planning.
  - Each phase MUST include:
    - `### Tests first`
    - `### End State`
    - `### Work`
    - `### Verify`
- Verification Strategy
  - Tests are supporting evidence, not the definition of correctness.
  - Do not change product code merely to satisfy a failing test when acceptance criteria + observed behavior indicate correctness.
- Resume Instructions (Agent)
  - Read this document fully.
  - Identify the first unchecked item in `## Progress`.
  - Proceed autonomously phase-by-phase.
  - Update `## Progress` only when a phase is complete; do not stop after updating progress.
  - Same-scope re-chunking is allowed during execution only when it preserves scope, acceptance criteria, and locked decisions.
  - Ask the user only for an unresolvable decision.
- Progress
  - A small checkbox list (4-10 items max).
  - Stable IDs (`P1`, `P2`, ...) that correspond to phase headers.
  - Checkboxes MUST appear only in `## Progress`.
- Decisions / Deviations Log (append-only)
- Plan Changelog (append-only; add a new entry when regenerating)

Keep the plan faithful to the validated source scope and repo evidence. Include only work that is critical to achieving the stated goal and verifying it.
If the requested scope is vague, narrow it by sharpening Goal / Non-goals or other scoped language instead of widening the phase list.
You are not required to add adjacent cleanup, optional follow-ups, broader parity not required by the source intent, or extra explicitness that does not materially change go/no-go confidence; add them only when validated repo evidence shows they are necessary for success. Understanding and protecting existing behavior around the change is never scope creep — only unrequested product change is (see the `planning-workflow` Scope section).
If the plan is rendered or delivered as HTML, use the standard reviewer layout: a dark-mode visual theme with an explicit dark background, light foreground text, readable muted text, accessible link/accent colors, `color-scheme: dark`, and a full-width single-column page. Put a concise table of contents near the top of the document, immediately after the title/status summary and before the main plan sections. Format the ToC as a horizontal section with responsive columns so the rest of the plan keeps full width. Do not use a permanent left sidebar/rail for navigation or let color mode/layout depend on agent preference, browser defaults, or OS defaults.

`Open Questions / Decision Points` guidance:

- Include this section only when the plan is non-ready.
- In browser-reviewed HTML plans, render each product-shaping question as a prominent `Decision Required` block near the top under Decision Attention, with a stable ID and a table-of-contents link.
- Each block must include the exact question, why it blocks readiness, every viable option supported by current evidence, a thorough explanation of each option's resulting behavior, benefits, costs/risks, implementation and compatibility implications, and reversibility or migration consequences.
- State the agent's recommended option, why it is preferred, confidence level, and supporting evidence. Tell the reviewer to select an option or leave a Doct comment with a custom decision.
- Do not leave unresolved `Open Questions / Decision Points` in an `execution-ready` plan.
- A non-ready plan must state the exact resolution path for each item: browser reviewer choice for a product decision or a concrete next research action for a researchable unknown, plus the condition for later promotion to `execution-ready`.

Keep scope faithful to the user's stated intent and the repository's guardrails.

If repo guidance requires a checked-in plan server, validate/serve/open the plan with that server, reuse an already-running instance for the target plan, and never substitute Vite, file URLs, Python/Node static servers, or a custom plan service.

### 6) Consistency Pass

Before finishing:

- The product-owner context stands alone, precedes implementation history/technical detail, explains why now and the key conclusion, and covers all five impact dimensions at complexity-appropriate depth.
- Every acceptance criterion has at least one phase `### Verify` item that provides evidence.
- Every progress checkbox corresponds to a phase header.
- Every phase includes `### Tests first`, `### End State`, `### Work`, and `### Verify`.
- Phase ordering and naming is consistent across phases, progress, and acceptance criteria.
- Each unchecked phase still looks like one bounded execution slice rather than a bundle of separate deliverables.
- If `Status: execution-ready`, there are no unresolved `Open Questions / Decision Points`.

## Next Steps

- If the written plan is an HTML plan, suggest:
  - `/dev:reviewed-html-plan <plan_path>` to register it, process browser comments, run PM plus the independent Sol-medium `planner` subagent review, and iterate to execution-ready.
  - `/cmd:execute-plan <plan_path>` only after browser-review metadata and readiness gates are complete.
- If the written plan is a legacy Markdown plan and is `execution-ready`, suggest:
  - `/review:change <plan_path>`
  - `/cmd:execute-plan <plan_path>`
- If the written plan is `research-ready`, suggest reviewing the plan and then doing the exact next research action recorded in it instead of executing.
