---
name: planning-workflow
description: Shared planning doctrine for creating or updating executable software plans. Use when moving from read-only research into writing a real plan, when you need to structure a resumable TDD/BDD-driven implementation plan, or when a command like `dev:plan` needs the canonical planning workflow plus guidance on which domain skills to load.
---

# Planning Workflow

Use this skill as the canonical source of truth for plan-writing methodology across repos. This skill has no default plan file format. Repo-local planning guidance must define the active plan artifact and serving workflow; when it says active plans are HTML or must use a checked-in plan service, follow that local contract exactly.

## Boundaries

- `plan mode` is for discovery only: inspect the codebase, validate assumptions, gather evidence, and identify ambiguities.
- `dev:plan` (or equivalent plan-materialization step) writes the actual plan file once discovery has produced enough evidence to choose the correct readiness state: `execution-ready` when foundational decisions are resolved, or a single non-ready `research-ready` artifact when further research is the next handoff. Before that handoff point, the work remains `discovery`.
- There is no default shared artifact path or extension. Resolve the single-file active plan artifact from repo-local guidance or an existing plan path supplied by the user. If local guidance does not define the active artifact and the user did not supply an existing plan path, ask one targeted question and stop. Do not assume markdown.
- `dev:plan` ends when the plan artifact is written or updated; execution starts only after a separate explicit execution command or a new user instruction.
- In Pi-style reviewed-plan workflows, keep the handoff explicit and prefer the repo's canonical workflow skill from repo-local guidance. Do not assume a hidden fallback to Claude Code or any other alternate review surface.
- During plan writing, edit only the target plan artifact unless the repo's `AGENTS.md` explicitly allows another planning-side file.
- Do not change product code, tests, app config, docs, generated files, or environment files while planning.
- Avoid side effects: no installs, codegen, migrations, formatting runs, commits, rebases, resets, or destructive commands.

## Planning inputs

Before writing a plan, read in this order:

1. Root `AGENTS.md` for repo-specific commands, quality gates, docs, and skill-routing hints.
2. `thoughts/specs/product_intent.md` when the repo requires product-intent alignment.
3. Optional `thoughts/plans/AGENTS.md` only when the repo uses local planning overrides beyond this shared skill.
4. Existing plan file, legacy plan bundle, task list, issue, or source specification that the plan must preserve.

When local guidance defines an active HTML plan workflow, also read its referenced contract/template docs before writing the plan. Do not create markdown companions for a repo whose active plan authority is HTML.

If required repo guidance or product intent is missing, stop and ask the user or tell them the repo bootstrap needs to be completed first.

## Skill routing

Always consider which additional skills are needed before writing the plan.

- Load `html-plan-reviewer` before writing, serving, registering, linking, or monitoring any `thoughts/plans/*.html` artifact. Use its `plan-review` tooling instructions for reviewer-facing HTML plans.
- Load `product-principles` for planning work that affects user/operator/agent workflows, defaults, onboarding, recovery behavior, error handling, architecture, or regression strategy. Use it to define the golden path, safe defaults, self-healing expectations, actionable error guidance, and a quick dissonance audit against repo guidance (`AGENTS.md`, product-intent docs, onboarding docs, config/status surfaces, and tests).
- Load `tdd-test-writer` when phases will rely on tests-first delivery or when the RED-phase contract needs strengthening.
- Load repo-recommended skills from `AGENTS.md` for the relevant surface or stack.
- Load domain-specific skills when the planned work clearly spans those domains (frontend, React/Next, Rust, MCP, browser automation, UI review, etc.).

The plan should reflect the behavior those skills require, not merely mention them.

When product work touches interactions, commands, processes, or operator/agent workflows, the plan should encode these default beliefs unless repo evidence explicitly requires a different constraint:

- the product should do the obvious right thing by default,
- routine faults should be detected and healed inside the normal requested flow,
- normal workflows should not depend on users discovering and running separate status or remediation commands,
- errors should assume a capable agent is reading them and should explain what happened, what the system already tried, why automation stopped, and what to do next,
- fail-closed behavior is reserved for ambiguous or high-risk situations such as data loss, security/privacy risk, or identity/authority uncertainty.

## Research standard

Validate important claims directly against repo reality before writing the plan:

- locate existing files, routes, registries, commands, and patterns,
- confirm data shapes, schemas, contracts, and constraints,
- identify integration points, parity surfaces, and likely risks,
- verify command names, package names, and file paths used in `### Verify` sections,
- identify the simplest supported workflow and which inputs should be optional because the system can infer or heal them,
- identify which manual status-check or repair steps currently exist and whether they should instead become built-in behavior on the normal path,
- check whether repo guidance, onboarding docs, config defaults, status surfaces, and tests are aligned with that default-path contract.

Use targeted `Glob`, `Grep`, and `Read` first. Delegate broad codebase discovery only when targeted search is not enough.

## Canonical plan contract

Write plans as execution artifacts, not brainstorming notes. A ready plan must be executable by another agent without inventing missing semantics.

- Preserve the validated source scope. A ready plan should include only work that is critical to achieving the stated goal and verifying it.
- When the requested scope is vague, tighten it by sharpening the Goal / Non-goals or other scoped language instead of widening the phase list to absorb adjacent surfaces.
- Do not promote adjacent cleanup, optional follow-ups, broader parity not required by the source intent, or extra explicitness that does not materially change go/no-go confidence into required plan work unless source requirements or validated repo evidence show they are necessary for success.
- When a plan is rendered or delivered as HTML, load `html-plan-reviewer` and use a dark-mode visual theme by default. Set an explicit dark background, light foreground text, readable muted text, accessible link/accent colors, and `color-scheme: dark`; do not leave the plan to browser, OS, or agent-selected light/dark defaults.
- When a plan is rendered, delivered, served, or reviewed as HTML, delegate service details to `html-plan-reviewer`: register through `plan-review` with truthful readiness metadata, parse and follow returned `agentInstructions`, open/share the canonical full review URL, and start the queue-backed comment monitor using the harness background-process tool. Treat low-level `plan-review watch` streams as debug-only unless the service instructions say otherwise.
- Every user-facing HTML plan URL must follow the canonical URL rules from `html-plan-reviewer`; private health checks may use loopback URLs only when that skill allows them.

Required sections for new plans unless repo-local overrides say otherwise:

1. Title
2. Status
3. Goal
4. Decision Attention / Low-confidence Areas
5. Why this plan exists
6. Authority and inputs
7. Current implementation reality
8. Progress
9. Resume instructions (agent)
10. Product intent alignment
11. Locked decisions
12. Acceptance criteria
13. BDD scenarios
14. Phase-by-phase execution plan
15. Verification strategy
16. Delivery order
17. Non-goals
18. Decisions / Deviations log

Decision Attention must appear near the top of every non-trivial plan. It indexes blockers, required user input, unresolved or low-confidence decisions, and areas where repo evidence is weak. If none remain, say `None` or `No product decision required` explicitly; do not omit the section or bury the answer in later phases.

Legacy heading aliases may be preserved in historical plans, but new plans should use canonical headings unless the repo explicitly says otherwise.

## TDD + BDD rules

For every acceptance area:

- define acceptance in observable user or system outcomes,
- define what the system should do automatically before asking the user or agent to intervene,
- add `Given/When/Then` scenarios for happy path, failure path, and relevant edge cases,
- add counterexample or ambiguity scenarios when matching, routing, identity, parsing, refs, or policies could yield misleading passes,
- add boundary or scale scenarios when volume, fan-out, or aggregation could change correctness,
- add cross-surface parity scenarios when behavior must match across HTTP/CLI/MCP/UI or similar interfaces.

For workflow and product-surface planning, include scenarios that distinguish:

- routine recoverable faults that should self-heal,
- ambiguous or high-risk faults that should fail closed,
- and the exact agent-legible error or inline guidance expected when automation must stop.

For every phase:

- start with failing tests first when practical,
- map tests to acceptance criteria and BDD scenario IDs,
- make the RED-phase contract strong enough to catch partial or misleading implementations,
- if strict TDD is not practical, state why and define compensating verification.

## Phase template

Every phase must include:

- `### End State`
- `### Tests first`
- `### Work`
- `### Expected files`
- `### Open questions / decision dependencies`
- `### Verify`

Use `None` for phase-specific questions only when there are no unresolved decisions. If a dependency changes scope, behavior, data handling, security/privacy posture, or compatibility, resolve it before marking the plan execution-ready instead of deferring it to implementation.

Phase guidance:

- keep phases coarse and outcome-oriented,
- do not hide task lists inside phases,
- make multi-surface parity inventory explicit in `### Expected files` or `### Work`,
- lock canonical contracts, schemas, fixtures, payloads, or evidence sources before downstream phases depend on them.

## Resumability rules

- `## Progress` contains the only checkboxes in the plan.
- Use stable IDs like `P1`, `P2`, ... and keep them aligned to phase headers.
- Enforce a one-to-one phase/progress mapping: every progress checkbox maps to exactly one detailed phase, and every detailed phase maps back to exactly one progress checkbox.
- Preserve completed items and append-only deviation/history sections when regenerating a plan.
- `Resume instructions` must tell the next agent to read the document fully, identify the first unchecked progress item, continue phase-by-phase, and ask the user only for truly unresolvable decisions.

## Ready bar

An `execution-ready` plan is ready only when all of the following are true:

- important questions are resolved,
- Decision Attention is near the top and truthfully reports blockers, user-input needs, and low-confidence areas,
- required plan work stays faithful to the validated source scope, with optional adjacent improvements excluded or called out as non-goals rather than required phases,
- acceptance criteria and BDD scenarios are concrete,
- every progress checkbox has exactly one matching phase and every phase has exactly one matching progress checkbox,
- every phase includes explicit `Open questions / decision dependencies`, with `None` only when true,
- phase `### Verify` steps are executable and current for the real repo,
- product-intent alignment is explicit when required,
- parity expectations are explicit for multi-surface work,
- self-healing expectations and fail-closed boundaries are explicit for workflow-affecting work,
- plans do not normalize routine manual remediation when the product should absorb that burden instead,
- UI impact is explicitly triaged and is not `unknown`,
- UI-impacting work includes repo-appropriate existing/target design evidence and verification gates,
- no unresolved `Open Questions` remain in a ready plan,
- no unresolved low-confidence decisions remain,
- foundational decisions are not deferred into later execution phases,
- progress and resume instructions are present,
- review-gated plans have fresh independent, non-self sign-off after the latest material edit and no later non-pass review.

If any item above is still missing, the plan is `not ready`: stay in `discovery` while evidence is still being gathered, or emit a `research-ready` artifact when research is the explicit next handoff.

## Readiness states

- `discovery` means planning evidence is still being gathered and the work is not yet plan-finalization-ready; it is a pre-handoff state, not a substitute for a written research handoff.
- `research-ready` means exactly one non-ready plan artifact may be written once discovery has established that research is the next handoff; that artifact must capture unresolved decisions, the next research step, and the condition for later promotion.
- `execution-ready` means the plan can hand off to execution without inventing missing contracts, rollout semantics, compatibility rules, or other foundational behavior.
- A plan is `not ready` when foundational decisions are deferred into later execution phases, even if the phase list itself looks complete.

## Low-confidence decision workflow

- Treat any materially outcome-shaping unknown as a `low-confidence` decision: contracts, migrations, rollout semantics, compatibility behavior, safety constraints, or cross-surface behavior.
- Resolve low-confidence decisions from repo evidence first.
- If repo evidence is insufficient and the choice changes intended behavior, ask the user before finalizing the plan.
- If the answer is researchable without user intent input, delegate research immediately or emit a non-ready `research-ready` research plan artifact.
- A non-ready plan artifact must list the unresolved low-confidence decisions, make the exact next research action explicit, and stay clearly separate from an `execution-ready` handoff.
- Never bury low-confidence decisions inside future execution phases or assume implementation will resolve them later.

## UI-impact triage

Every non-trivial plan must state whether it changes UI, reviewer-facing artifacts, operator-facing command output, generated docs, visual design, or interaction behavior.

Use these defaults:

- `UI impact: no` only when no visible/operator-facing surface changes.
- `UI impact: text-only` when the visible change is prose, guidance, command output, or plan-artifact structure without runtime UI or styling changes.
- `UI impact: yes` when the work changes screens, flows, browser artifacts, navigation, forms, visual hierarchy, or interaction behavior.
- `UI impact: unknown` blocks execution-ready status until resolved.

For `UI impact: yes`, include high-fidelity existing and target mocks or screenshots when the repo surface supports them, plus repo-appropriate design evidence and verification gates. For `text-only`, include a concise current/target textual rendition and the inspection commands or review checks that prove the guidance changed.

## Complexity-aware completeness

- Keep the doctrine `complexity-aware` and domain-agnostic: scale planning depth to the real task shape, not the stack.
- Simple local wiring or narrow refactor tasks should stay `lightweight`; do not force heavyweight schema, protocol, or rollout sections when they do not improve confidence.
- Non-trivial, migration-heavy, compatibility-sensitive, or multi-surface work requires complete contracts before it can be `execution-ready`.
- Every non-trivial ready plan must include a `test coverage matrix` that maps acceptance criteria and BDD scenarios to planned test layers, intended suites or files, and `### Verify` commands strong enough to catch partial implementations.
- If task complexity is uncertain, bias toward more explicit contracts and acceptance-to-test mapping until evidence justifies a lighter plan.

## Verification ownership

- Phase `### Verify` checks are agent-run execution gates: they must be runnable during implementation, grounded in repo reality, and expanded with compensating checks when strict TDD is not practical.
- Final completion still requires a semantic coherence review across the shared files touched by the work so reviewers confirm the doctrine means the same thing everywhere, not just that strings appear.

## Handoff to execution

When the plan is complete:

- leave the repo ready for the repo's canonical execution workflow,
- if repo-local guidance requires serving the plan over HTTP, use the checked-in plan server it names; reuse an already-running instance for the target plan and do not start ad hoc replacement servers,
- `ready for` means handoff-ready, not permission to start execution in the current command,
- if the active command is planning-only, stop after updating the plan and reporting the next suggested command,
- ensure the plan reflects repo-specific commands from `AGENTS.md`,
- keep deviations and migration notes append-only,
- do not stop with an implicit draft if the user asked for an execution-ready plan.
