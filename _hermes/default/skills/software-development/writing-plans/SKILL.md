---
name: writing-plans
description: Use when creating or updating executable software plans. For Aaron-facing plan requests, create a Doct-registered HTML/Markdoc plan by default, start/verify the comment listener, and do not use Markdown/text docs unless explicitly requested or repo guidance forbids HTML.
version: 2.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [planning, design, implementation, workflow, documentation, doct, html-plans]
    related_skills: [planning-workflow, doct-document-ops, reviewed-html-plan, test-driven-development]
---

# Writing Implementation Plans

Use this skill as the canonical source of truth for writing executable implementation plans across repos.

## Aaron default: plans are Doct-registered HTML/Markdoc

When Aaron says “create a plan”, “post a plan”, “make a plan”, “publish a plan”, or otherwise asks for an implementation/development plan, the default artifact is a reviewer-facing HTML or Markdoc plan registered in Doct with `doct-agent plans`, not a Markdown/text Doct document and not a chat-only plan. This default applies even when the user does not explicitly say “HTML”.

Only use a non-HTML/Markdoc plan when one of these is true:

- Aaron explicitly asks for Markdown/text/no Doct/no comments;
- an existing non-HTML plan path is supplied and the task is only to update that artifact;
- repo-local guidance explicitly forbids Doct HTML/Markdoc plans for this workflow.

If repo-local guidance is absent or ambiguous, do not ask which format to use: create `thoughts/plans/<slug>.html` in a repo context, or a temporary handcrafted HTML source for standalone/non-repo planning, then register it through Doct. After registration, start or verify the Doct plan comment listener/queue watcher and report both the canonical Doct review URL and listener status.

Repo-local planning guidance may refine the source path or choose Markdoc over handcrafted HTML, but it does not weaken the default that Aaron-facing plans must be browser-reviewable and commentable.

## Boundaries

- `plan mode` is for discovery only: inspect the codebase, validate assumptions, gather evidence, and identify ambiguities.
- `dev:plan` (or equivalent plan-materialization step) writes the actual plan file once discovery has produced enough evidence to choose the correct readiness state: `execution-ready` when foundational decisions are resolved, or a single non-ready `research-ready` artifact when further research is the next handoff. Before that handoff point, the work remains `discovery`.
- Default shared artifact for Aaron-facing plans is a Doct-registered HTML/Markdoc plan. Resolve the exact source path from repo-local guidance or an existing plan path supplied by the user. If local guidance does not define the active artifact and the user did not supply an existing plan path, use `thoughts/plans/<slug>.html` in a repo context or a temporary handcrafted HTML source for standalone planning. Do not ask which format to use unless Aaron explicitly requests a non-HTML format or repo guidance conflicts.
- `dev:plan` ends when the plan artifact is written or updated; execution starts only after a separate explicit execution command or a new user instruction.
- In Pi-style reviewed-plan workflows, keep the handoff explicit and prefer the repo's canonical workflow skill from repo-local guidance. For HTML plans, prefer Doct registration through `doct-agent plans` on `https://doct.nodaste.com`; do not assume a hidden fallback to Claude Code, a local `plan-review` service, or any other alternate review surface.
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

- Load `doct-document-ops` before writing, registering, linking, updating, or monitoring any reviewer-facing `thoughts/plans/*.html` or `thoughts/plans/*.markdoc` artifact. Use its Doct-backed `doct-agent plans` instructions for reviewer-facing HTML/Markdoc plans, with `https://doct.nodaste.com` as the default registration endpoint.
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
- When a plan is rendered or delivered as HTML/Markdoc, load `doct-document-ops` and use the standard reviewer layout by default: a dark-mode visual theme with explicit dark background, light foreground text, readable muted text, accessible link/accent colors, `color-scheme: dark`, plus a full-width single-column page. Put a concise table of contents near the top of the document, immediately after the title/status summary and before the main plan sections. Format the ToC as a horizontal section with responsive columns so reviewers can scan links without sacrificing plan body width. Do not use a permanent left sidebar/rail for navigation. Do not leave color mode or navigation layout to browser, OS, or agent-selected defaults.
- When a plan is rendered, delivered, registered, or reviewed as HTML/Markdoc, delegate service details to `doct-document-ops`: register through `doct-agent plans register --base-url https://doct.nodaste.com --source-format <html|markdoc>`, update through `doct-agent plans update`, share the canonical Doct URL, and process comments/actions through `doct-agent plans queue/agent/ack/resolve`.
- Every user-facing HTML plan URL must be the canonical Doct URL from `https://doct.nodaste.com`; do not share local `plan-review`, loopback, or Tailscale service URLs unless the user explicitly requested a legacy local review service.

### Product-owner context contract

Near the top of every implementation plan, before implementation history, current-code detail, progress, phases, or verification mechanics, include a standalone product-owner context section. Write it for a product owner who has no prior issue, Linear, incident, or repository context. It must:

- explain the situation in plain language, defining unavoidable domain terms instead of leading with file paths, symbols, request traces, or issue chronology,
- explain why the change is needed now and what new evidence, failure, decision, or timing makes the work timely,
- state the key conclusion unmistakably, especially whether the plan addresses a customer/runtime product defect, a stale test or evidence problem, an operational/documentation gap, or a combination,
- separate the impact on `Customers`, `Runtime product behavior`, `Security / permissions`, `Testing / release confidence`, and `Deployment / migration`; explicitly say `No change` or `Not applicable` rather than silently omitting an unaffected dimension,
- distinguish observed facts from proposed work so a reviewer does not confuse a failing test with a shipped-product failure.

Keep this complexity-aware. A lightweight plan must satisfy the contract with concise labeled prose. A non-trivial plan must use a clearly scannable impact table or an equivalent structured block with those five impact dimensions. This is an authoring and review contract, not a Doct renderer requirement; preserve the standard dark full-width layout and fit the section into that layout.

Required sections for new plans unless repo-local overrides say otherwise:

1. Title
2. Status
3. Product-owner context (situation, why now, key conclusion, and impact breakdown)
4. Goal
5. Decision Attention / Low-confidence Areas
6. Why this plan exists
7. Authority and inputs
8. Current implementation reality
9. Progress
10. Resume instructions (agent)
11. Product intent alignment
12. Locked decisions
13. Acceptance criteria
14. BDD scenarios
15. Phase-by-phase execution plan
16. Verification strategy
17. Delivery order
18. Non-goals
19. Decisions / Deviations log

Decision Attention must appear near the top of every non-trivial plan, immediately after the product-owner context and goal/status framing. It indexes blockers, required user input, unresolved or low-confidence decisions, and areas where repo evidence is weak. If none remain, say `None` or `No product decision required` explicitly; do not omit the section or bury the answer in later phases.

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
- the near-top product-owner context is standalone, plain-language, explicit about why now and the key conclusion, and separates all five impact dimensions,
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
- Simple local wiring or narrow refactor tasks should stay `lightweight`; they may use concise labeled prose for product-owner context and should not be forced into heavyweight schema, protocol, rollout, or tabular sections when those do not improve confidence.
- Non-trivial, migration-heavy, compatibility-sensitive, or multi-surface work requires complete contracts before it can be `execution-ready`, including a scannable product-owner impact table or equivalent structured block.
- Every non-trivial ready plan must include a `test coverage matrix` that maps acceptance criteria and BDD scenarios to planned test layers, intended suites or files, and `### Verify` commands strong enough to catch partial implementations.
- If task complexity is uncertain, bias toward more explicit contracts and acceptance-to-test mapping until evidence justifies a lighter plan.

## Verification ownership

- Phase `### Verify` checks are agent-run execution gates: they must be runnable during implementation, grounded in repo reality, and expanded with compensating checks when strict TDD is not practical.
- Final completion still requires a semantic coherence review across the shared files touched by the work so reviewers confirm the doctrine means the same thing everywhere, not just that strings appear.

## Handoff to execution

When the plan is complete:

- leave the repo ready for the repo's canonical execution workflow,
- if repo-local guidance requires a plan review registration, prefer the Doct-backed `doct-document-ops` flow; use a checked-in/local plan server only when the repo or user explicitly requires that legacy surface,
- `ready for` means handoff-ready, not permission to start execution in the current command,
- if the active command is planning-only, stop after updating the plan and reporting the next suggested command,
- ensure the plan reflects repo-specific commands from `AGENTS.md`,
- keep deviations and migration notes append-only,
- do not stop with an implicit draft if the user asked for an execution-ready plan.
