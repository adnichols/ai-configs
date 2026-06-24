---
name: dev-plan
description: Materialize or update a single-file execution plan after discovery. Planning-only work - synthesizes validated research into an actual execution plan without modifying product code.
---

# Materialize Plan

You are leaving read-only discovery mode and entering plan-materialization mode. This is still non-execution work: synthesize validated research into the actual execution plan file.

This shared skill has no default plan file format. Determine the active plan artifact from repo-local guidance (`AGENTS.md`, `thoughts/plans/AGENTS.md`, local planning skills, or an existing plan path supplied by the user). Follow the local artifact format exactly; do not create markdown companions for an HTML-plan repo. If repo guidance does not define the active plan artifact format/path and the user did not supply an existing plan path, ask one targeted question and stop. Do not assume markdown.

Treat this command as planning-only work even though normal file writes are available. You may inspect the repo and write the plan artifact, but you must not change product code, tests, app config, docs, generated files, or environment files.

Your job ends after writing or updating the single plan file and reporting the result. Do not create execution todos, do not begin implementation, and do not run execution-oriented verification once the plan file is complete.

## Usage

```
/skill:dev-plan <slug | "short description" | existing-plan-path>
```

## Output

Output: exactly one `plan_path`, resolved from repo-local guidance or an existing plan path supplied by the user.

## Process

### 1) Resolve Plan Path

1. If arguments look like a path to an existing plan file, treat it as `plan_path`.
2. Otherwise derive `slug` from arguments (lowercase, digits, hyphens only).
3. Set `plan_path` to the repo's active plan path from local guidance. If local guidance does not define one and the user did not supply an existing plan path, ask one targeted question and stop. Do not infer a markdown path.
4. Ensure the parent directory for `plan_path` exists (create it if missing).

### 2) Re-establish Planning Context

Before writing the plan:

1. Read the repo root `AGENTS.md`.
2. Read `thoughts/specs/product_intent.md` if the repo uses it.
3. Read `thoughts/plans/AGENTS.md` only if it exists for local planning overrides.
4. If local guidance names an HTML plan contract, template, validator, or plan service, read those docs before writing and use the checked-in tooling they name.
5. Load relevant skills:
   - `html-plan-reviewer` before writing, serving, registering, linking, or monitoring any `thoughts/plans/*.html` artifact; use its `plan-review` workflow for reviewer-facing HTML plans
   - `product-principles` when the plan affects workflows, defaults, onboarding, recovery behavior, error handling, architecture, or regression strategy; use it to define the golden path, self-healing expectations, fail-closed boundaries, agent-legible errors, and to audit repo guidance/tests for dissonance
   - `tdd-test-writer` when phases will depend on tests-first delivery
   - `dependency-selection` when introducing non-trivial functionality
   - Domain-specific skills (frontend, React/Next, Rust, etc.)

If required planning guidance is missing, ask the user instead of guessing.

### 3) Read Existing Plan (If Present)

If `plan_path` exists, read it fully.

Preserve existing state:
- Any completed checkboxes (`[x]`) in `## Progress` and their IDs
- Existing entries in `## Decisions / Deviations Log`
- Existing entries in `## Plan Changelog` (append when regenerating)

Legacy migration (read-only; do not delete):
- If `thoughts/plans/<slug>/spec.md` and/or `thoughts/plans/<slug>/tasks.md` exist, read them.
- Prefer the legacy spec as the source of intent.

### 4) Validate Repo Reality

Validate key claims by directly inspecting the codebase:
- Locate relevant files and existing patterns
- Confirm APIs, data shapes, configuration, and constraints
- Identify integration points and risks
- Verify actual commands, targets, package names, and paths
- Identify the simplest supported workflow and which inputs should be optional because the system can infer or heal them
- Identify any routine manual remediation or status-check steps that should instead be absorbed into the normal product flow
- Audit `AGENTS.md`, product-intent docs, onboarding/install docs, config/status surfaces, and tests for dissonance with that golden path

Use `bash` with `find`, `rg`, and `read` for targeted research. Use `subagent` with exploration agents only for broad searches.

Do not run side-effecting commands while doing this validation.

### 5) Write plan_path

Write (or update) `plan_path` following shared planning workflow and repo-specific guidance.

Non-negotiable requirements:
- Write exactly one plan file at `plan_path`
- Preserve prior progress and append-only logs when regenerating
- `## Progress` contains the only checkboxes with stable IDs (`P1`, `P2`, ...)
- Each phase includes `### End State`, `### Tests first`, `### Expected files`, `### Work`, and `### Verify`
- Ready plans have no unresolved `Open Questions`
- `### Verify` steps are copy/paste ready and match actual repo reality
- The plan is resumable by another agent without inventing missing semantics
- If the plan is rendered or delivered as HTML, load `html-plan-reviewer` and use the standard reviewer layout: a dark-mode visual theme with an explicit dark background, light foreground text, readable muted text, accessible link/accent colors, `color-scheme: dark`, and a two-column page with a concise sections navbar in a left sidebar and plan content on the right. The left navbar must remain available while reading long plans by being sticky and independently scrollable (`max-height` plus `overflow-y: auto`) and must collapse to one column on narrow screens. Do not let the agent choose light mode or an alternate navigation layout.
- If the plan is rendered, served, registered, linked, or monitored as HTML, use `html-plan-reviewer` as the sole source for current `plan-review` commands: service health, registration, readiness metadata, returned `agentInstructions`, canonical URLs, comment monitoring, ack/resolve, and final readiness re-registration.
- Every user-facing HTML plan URL must follow the canonical URL rules from `html-plan-reviewer`; private health checks may use loopback URLs only when that skill allows them.
- For product-facing work, the plan explicitly documents the default workflow, inferred defaults, self-healing expectations, fail-closed boundaries, actionable agent-legible error guidance, and any repo-doc/test updates needed to stay aligned
- When a repo uses a reviewed-plan flow, the plan assumes explicit handoff to the canonical continuation named in repo-local guidance rather than hidden recovery paths.
- If repo guidance requires a checked-in plan server, validate/serve/open the plan with that server, reuse an already-running instance for the target plan, and never substitute Vite, file URLs, Python/Node static servers, or a custom plan service.
- The plan does not normalize routine "run this other command to inspect/fix it" operator loops unless the work is explicitly about a high-risk or ambiguous exception path

### 6) Consistency Pass

Before finishing:
- Every acceptance criterion has at least one phase `### Verify` item
- Every progress checkbox corresponds to a phase header
- Phase ordering and naming is consistent
- Every phase has a `### Tests first` section describing user-visible outcomes
- `### Verify` commands are copy/paste ready and match current repo/package/target names
- No non-plan file was modified

## Forbidden Actions

- Do not create a new execution todo list after the plan is complete
- Do not switch into build, run, or implementation mode
- Do not edit any file except `plan_path` unless scope is explicitly broadened
- Do not run lint, tests, build, e2e, migrations, or other execution-oriented verification
- Do not invoke other skills as part of this command; only suggest them

## Suggested Next Steps

After this skill completes, suggest only next steps supported by repo-local guidance. For reviewed-plan repos, name the canonical continuation from `AGENTS.md` or the repo's planning overrides; do not invent a fallback review or execution command.
