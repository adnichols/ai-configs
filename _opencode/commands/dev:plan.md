---
description: Materialize or update the actual single-file plan artifact after discovery, using shared planning doctrine plus repo-specific guidance
argument-hint: '<slug | "short description" | existing-plan-path>'
---

# Materialize Plan

You are leaving read-only discovery mode and entering plan-materialization mode. This is still non-execution work: synthesize validated research into the actual plan artifact.

This command has no default plan file format. Determine the active plan artifact from repo-local guidance (`AGENTS.md`, `thoughts/plans/AGENTS.md`, local planning skills, or an existing plan path supplied by the user). If local guidance says active plans are HTML or names a checked-in plan server/validator, obey that local contract exactly. If repo guidance does not define the active plan artifact format/path and the user did not supply an existing plan path, ask one targeted question and stop. Do not assume markdown.

Treat this command as planning-only work even though normal file writes are available. You may inspect the repo and write the plan artifact, but you must not change product code, tests, app config, docs, generated files, or environment files.

Your job ends after writing or updating the single plan file and reporting the result. If safe plan materialization is blocked on new user intent, ask one targeted question and stop without writing the plan. Do not create execution todos, do not begin implementation, and do not run execution-oriented verification once the plan file is complete.

This command produces (or updates) exactly one `plan_path`, resolved from repo-local guidance or an existing plan path supplied by the user.

## Inputs

Argument (`$ARGUMENTS`) is either:

- A slug (recommended), e.g. `worktree-cleanup`
- A short description (derive a slug)
- A path to an existing plan file (treat it as the plan path)

## Output Contract

When plan materialization is safe in this invocation, write exactly one file:

- `plan_path`, resolved from repo-local guidance or an existing plan path supplied by the user
- If unresolved foundational decisions remain, still preserve the single-file contract by writing exactly one non-ready `research-ready` plan artifact at `plan_path` instead of pretending the work is `execution-ready`.
- The written non-ready artifact must set `Status:` to `research-ready`, explicitly list the unresolved decisions, the exact next research action, and the condition for later promotion to `execution-ready`.
- If a foundational decision needs new user intent before any safe plan can be written, ask exactly one targeted question and stop without writing `plan_path`.

Do not create `spec.md`, `tasks.md`, per-plan directories, same-slug markdown/JSON companions for an HTML-plan repo, or any non-plan file unless the user explicitly asks.

Completion condition for this command when a plan artifact can be written safely:

- Exactly one plan file at `plan_path` is written or updated.
- No non-plan file is modified.
- The final response reports the plan path and readiness state, then suggests follow-up work that matches that state without running anything.
- Only suggest `/cmd:execute-plan <plan_path>` when the written plan is `execution-ready`.
- For a written `research-ready` artifact, point the user to the exact next research action captured in the plan instead of suggesting execution.
- Then stop and wait for a new user instruction.

Blocking question behavior:

- If a foundational decision needs new user intent, ask exactly one targeted question, explain why the plan is not yet safe to materialize, and do not write or partially rewrite `plan_path`.

Forbidden transitions for this command:

- Do not create a new execution todo list after the plan is complete.
- Do not switch into build, run, or implementation mode.
- Do not edit any file except `plan_path` unless the user explicitly broadens scope.
- Do not run lint, tests, build, e2e, migrations, or other execution-oriented verification.
- Do not invoke `/review:change`, `/cmd:execute-plan`, `/ralph:run`, or any other follow-up command from this command; only suggest them.

Legacy bundles:

- If a legacy bundle exists at `thoughts/plans/<slug>/spec.md` and/or `thoughts/plans/<slug>/tasks.md`, you may read it for migration.
- Do not delete or modify legacy bundle files.

## Process

### 1) Resolve Plan Path

1. If `$ARGUMENTS` looks like a path to an existing plan file, treat it as `plan_path`.
2. Otherwise derive `slug` from `$ARGUMENTS`.
   - Use lowercase, digits, and hyphens only.
   - If multiple plausible slugs exist, ask the user exactly one targeted question, explain the slug ambiguity, and stop; use the answer on the next invocation.
3. Set `plan_path` to the repo's active plan path from local guidance. If local guidance does not define one and the user did not supply an existing plan path, ask one targeted question and stop. Do not infer a markdown path.
4. Ensure the parent directory for `plan_path` exists (create it if missing).

### 2) Re-establish Planning Context

Before writing the plan:

1. Read the repo root `AGENTS.md`.
2. Read `thoughts/specs/product_intent.md` if the repo uses it.
3. Read `thoughts/plans/AGENTS.md` only if it exists and the repo uses it for local planning overrides.
4. If local guidance names an HTML plan contract, template, validator, or plan service, read those docs before writing and use the checked-in tooling they name. Do not substitute an ad hoc plan server.
5. Load the shared `planning-workflow` skill.
6. Load the shared `product-principles` skill whenever the plan affects workflows, defaults, onboarding, recovery behavior, error handling, architecture, or regression strategy. Use it to define the golden path, safe defaults, self-healing expectations, actionable error guidance, and a quick dissonance audit against repo guidance/tests.
7. Load any repo-recommended or surface-specific skills that are clearly relevant to the plan being written.
   - Use `tdd-test-writer` when the phases will depend on tests-first delivery.
   - When the planned work introduces or replaces non-trivial functionality with real build-vs-buy choices, perform an explicit dependency/library evaluation during planning by naming the official SDKs and well-maintained libraries considered, even if no dedicated repo skill covers that check.
   - Use frontend, React/Next, Rust, MCP, browser, or other domain skills when the work clearly spans those domains.

If required planning guidance is missing and the repo cannot be planned confidently without it, ask the user instead of guessing.

### 3) Read Existing Plan (If Present)

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

### 4) Validate Repo Reality

Validate key claims from the conversation by directly inspecting the codebase:

- Locate the relevant files and existing patterns
- Confirm APIs, data shapes, configuration, and constraints
- Identify integration points and risks
- Verify actual commands, targets, package names, and paths that the plan will reference
- Identify the simplest supported workflow and which inputs should be optional because the system can infer or heal them
- Audit repo guidance (`AGENTS.md`, product-intent docs, onboarding/install docs, config/status surfaces, and tests) for dissonance with that default-path contract

Use `Glob`, `Grep`, and `Read` for targeted research. If broad discovery is still needed, continue with additional targeted passes yourself or delegate read-only planning research only through helpers that actually exist in the current runtime.

Do not run side-effecting commands while doing this validation.

### 5) Choose readiness state before writing

Before writing `plan_path`, explicitly choose the correct readiness state.

- Treat unresolved contracts, migrations, rollout semantics, compatibility behavior, safety constraints, and other materially outcome-shaping unknowns as `low-confidence` foundational decisions.
- Fail closed: do not mark the plan `execution-ready` while any foundational decision remains unresolved.
- If repo evidence is insufficient and the decision needs user intent, ask the user before finalizing the plan and do not write or update `plan_path` until that decision is resolved.
- If the gap is researchable without new user intent, continue with targeted planning research yourself or delegate read-only planning research only if it can still resolve the decision in this invocation before writing.
- If research still remains the next handoff after that validation, write a non-ready `research-ready` plan artifact whose next handoff is that research.
- Do not end `dev:plan` by delegating or suggesting follow-up research without writing `plan_path` when research is still the next handoff.
- Never bury a low-confidence decision inside a later execution phase just to keep the plan moving.

### 6) Write `plan_path`

Write (or update) `plan_path` by following the shared `planning-workflow` skill, the repo's `AGENTS.md`, and any explicit repo-local planning overrides.

Before any write or side-effecting action, verify it only updates `plan_path` or creates the missing parent directory needed for `plan_path`. If it would touch any other file or begin execution, do not do it under `dev:plan`.

Complexity and completeness rules:

- Keep simple local wiring or narrow refactor work `lightweight`; do not force heavyweight schema, protocol, or rollout sections when they do not improve confidence.
- Require complete contracts and a `test coverage matrix` only for non-trivial, migration-heavy, compatibility-sensitive, or multi-surface work before calling the plan `execution-ready`.
- For non-trivial ready plans, map acceptance criteria and BDD scenarios to intended test layers, planned suites or files, and `### Verify` commands strong enough to catch partial implementations.

Non-negotiable compatibility requirements:

- Write exactly one plan file at `plan_path`.
- Preserve prior progress and append-only logs when regenerating.
- `## Progress` contains the only checkboxes and uses stable IDs (`P1`, `P2`, ...).
- Each phase includes `### End State`, `### Tests first`, `### Expected files`, `### Work`, and `### Verify`.
- Ready plans do not leave unresolved `Open Questions` or equivalent unresolved-decision sections.
- `### Verify` steps are copy/paste ready and match actual repo reality.
- The plan is resumable by another agent without inventing missing semantics.
- If the plan is rendered or delivered as HTML, use the standard reviewer layout: a dark-mode visual theme with an explicit dark background, light foreground text, readable muted text, accessible link/accent colors, `color-scheme: dark`, and a two-column page with a concise sections navbar in a left sidebar and plan content on the right. The left navbar must remain available while reading long plans by being sticky and independently scrollable (`max-height` plus `overflow-y: auto`) and must collapse to one column on narrow screens. Do not let color mode or navigation layout depend on agent preference, browser defaults, or OS defaults.
- When the change introduces or replaces non-trivial functionality, the plan includes a dedicated dependency/library evaluation section or equivalent explicit checkpoint that names the official SDKs and well-maintained libraries considered, records the chosen option and why it is acceptable, or explains why custom implementation is justified.
- When no dependency/library scan is needed, the plan still includes a brief statement explaining why the work is trivial or purely local wiring.

Before considering the plan complete:

- Use product intent if the repo requires it, and make the alignment explicit in the plan.
- For product-facing work, make the default workflow, inferred defaults, self-healing expectations, actionable error guidance, and any repo-guidance/test updates explicit in the plan.
- Resolve every important question before finalizing an `execution-ready` plan.
- If the codebase or docs answer a question with high confidence, answer it directly in the plan.
- If confidence is not high enough, ask the user when intent is required; otherwise either close the gap with additional targeted planning research in this invocation, delegate read-only planning research that can still close it now, or produce a non-ready `research-ready` artifact instead of forcing an `execution-ready` handoff.
- Use `tdd-test-writer` when available to improve the `### Tests first` sections.
- Make `### Tests first` strong enough to catch partial or misleading implementations by covering happy path, guardrail/failure behavior, counterexamples or ambiguity cases, and boundary/scale or parity cases when applicable.
- Lock canonical contracts, payloads, schemas, or evidence sources in the plan before phases that depend on them.
- Plans that require dependency/library evaluation are not ready until that checkpoint is documented; a missing official-SDK/library decision keeps the work in a non-ready state rather than silently treating it as `execution-ready`.

### 7) Consistency Pass

Before finishing:

- The chosen readiness state is explicit and internally consistent.
- A research-first handoff uses `Status: research-ready` so the written artifact cannot be mistaken for an `execution-ready` plan.
- The plan structure follows the shared planning workflow and any repo-local planning overrides.
- Every acceptance criterion has at least one phase `### Verify` item that provides evidence.
- Every progress checkbox corresponds to a phase header.
- Phase ordering and naming is consistent across phases, progress, and acceptance criteria.
- Every phase has a `### Tests first` section.
- The `### Tests first` sections describe user-visible behavioral outcomes, not only implementation mechanics.
- BDD scenarios or equivalent `Given/When/Then` coverage are explicit when required by repo guidance.
- Multi-surface phases make parity expectations explicit in `### Tests first`, `### Work`, or `### Expected files`.
- `### Verify` commands are copy/paste ready and match current repo/package/target names.
- There are no unresolved foundational decisions hiding inside later execution phases.
- There are no unresolved decision points left in an `execution-ready` plan; a `research-ready` artifact keeps them explicit as unresolved next-handoff items.
- If non-trivial build-vs-buy choices are in scope, the dependency/library evaluation checkpoint is present; otherwise the plan briefly states why no scan was needed.
- No non-plan file was modified.

## Next Steps For The User

These are suggestions for the user to run after this command finishes. Do not run them as part of `dev:plan`.

- If the written plan is `execution-ready`, suggest:
  - `/review:change <plan_path>`
  - `/cmd:execute-plan <plan_path>`
- If the written plan is `research-ready`, suggest reviewing the plan and then doing the exact next research action recorded in that artifact instead of `/cmd:execute-plan`.
