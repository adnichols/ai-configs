---
name: planning-workflow
description: Shared planning doctrine for creating or updating executable software plans, including the default preference to register HTML plans in Doct through `doct-agent plans` on `https://doct.nodaste.com`. Use when moving from read-only research into writing a real plan, structuring a resumable TDD/BDD implementation plan, or when a command like `dev:plan` needs canonical planning workflow and skill-routing guidance.
---

# Planning Workflow

Use this skill as the canonical source of truth for plan-writing methodology across repos. This skill has no default plan file format. Repo-local planning guidance must define the active plan artifact and serving workflow; when it says active plans are HTML or must use a checked-in plan service, follow that local contract exactly.

## Scope

> **Scope creep is changing what the product does beyond the promised outcome.** Building unrequested features, redesigning working systems, polishing things nobody asked about — that needs its own plan and, when product-changing, owner approval.
>
> **Understanding and protecting existing behavior around your change is never scope creep — it is the cost of the change.** When you change a contract, its consumers are part of your change whether or not the plan names them. When you fix one instance of a pattern, its siblings are part of the question you were asked. Reading, tracing, and reporting **within authorized surfaces — code, tests, documentation, and supported diagnostics; never secrets, production data, or private persistence** — is always free.
>
> The test, when unsure: is this work making something *new* happen, or keeping something *existing* working while I make my change? The first needs an expansion-log entry — and owner approval if it changes product behavior, public contracts, persistence, ownership, or release behavior. The second is yours.

The disposition rule:

> **A regression this change causes is in scope wherever it appears. When this change routes new valid inputs into a shared primitive or expands its reachable domain, correctness across that newly reachable domain is part of this change even where defects predate it. A defect this change merely discovers — and does not cause or newly expose — is a finding: capture it and keep going.**

## Boundaries

- `plan mode` is for discovery only: inspect the codebase, validate assumptions, gather evidence, and identify ambiguities.
- `dev:plan` (or equivalent plan-materialization step) writes the actual plan file once discovery has produced enough evidence to choose the correct readiness state: `execution-ready` when foundational decisions are resolved, or a single non-ready `research-ready` artifact when further research is the next handoff. Before that handoff point, the work remains `discovery`.
- There is no default shared artifact path or extension. Resolve the single-file active plan artifact from repo-local guidance or an existing plan path supplied by the user. If local guidance does not define the active artifact and the user did not supply an existing plan path, ask one targeted question and stop. Do not assume markdown.
- `dev:plan` ends when the plan artifact is written or updated; execution starts only after a separate explicit execution command or a new user instruction.
- In Pi-style reviewed-plan workflows, keep the handoff explicit and prefer the repo's canonical workflow skill from repo-local guidance. For HTML plans, prefer Doct registration through `doct-agent plans` on `https://doct.nodaste.com`; do not assume a hidden fallback to Claude Code, a local `plan-review` service, or any other alternate review surface.
- During plan writing, edit only the target plan artifact unless the repo's `AGENTS.md` explicitly allows another planning-side file.
- Do not change product code, tests, app config, docs, generated files, or environment files while planning.
- Avoid unrelated side effects: no installs, codegen, migrations, formatting runs, rebases, resets, or destructive commands. Commit the plan artifact when the repository workflow requires it.

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

- Load `doct-document-ops` before writing, registering, linking, updating, or monitoring any reviewer-facing `thoughts/plans/*.html` or `thoughts/plans/*.markdoc` artifact. Use its Doct-backed `doct-agent plans` instructions for reviewer-facing plans, with `https://doct.nodaste.com` as the default registration endpoint. After registration, follow the returned `listenerInstructions` and start the durable listener before browser-review handoff.
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

## Integration-integrity planning contract

When discovery identifies either an exact contract that the type system cannot fully verify (for example, serialized fields, positional layouts, configuration keys, flags, paths, headers, payloads, migrations, or documented command forms) or behavior required across multiple production sites, make that evidence explicit in the plan. This is a planning representation of the common execution rule, not a reason to require a plan for otherwise lightweight work.

Add a **Contract and distributed-integration inventory** section when either trigger applies. For every exact contract, record the source of truth, producer, consumer, dependent documentation/examples, and the real cross-boundary test. Prefer one shared executable definition, typed schema, or single contract artifact over duplicated fixtures or copied prose. Before planning dependent edits, reread the current source definition.

For distributed behavior, record the source-search basis, each site or operation family, the required behavior and meaningful dimensions, its production-path verification, and reconciliation status. Declare coverage as **exhaustive-by-site**, **exhaustive-by-family**, or **justified representative**; a representative claim must explain why its evidence covers the omitted sites. A helper, middleware, wrapper, or event-existence assertion demonstrates infrastructure only. It cannot close a distributed acceptance criterion without reconciliation and proof through the required production path.

When neither trigger applies, write `None identified, based on <source search>` rather than manufacturing an inventory. When a documented CLI invocation is part of the requested contract, its evidence must execute the actual parser; help-text or documentation-string assertions alone are not sufficient.

## Canonical plan contract

Write plans as execution artifacts, not brainstorming notes. A ready plan must be executable by another agent without inventing missing semantics.

- Keep required plan work faithful to the validated source scope as defined in the Scope section above.
- Plan complete promised slices, not skeletons. Every claimed functional outcome must be connected, usable, and verifiable within its stated scope, without required stubs, TODO behavior, dead-end surfaces, missing producer/consumer wiring, fake success, or verification that bypasses the real implementation.
- If the requested outcome cannot be completed safely in one change, resize it before implementation to a smaller independently useful complete slice. Independent future enhancements, scale work, optional hardening, and polish may remain out of scope; work required for the current slice to function as claimed may not.
- Define the complete promised slice at the **PR boundary**: code, tests, docs, migration definitions, release configuration, and buildable artifacts that can truthfully be reviewed before merge. An environment deployment, promotion, merge, production observation window, or post-merge smoke check is delivery/operations work, not missing implementation in the PR slice.
- Deployment must never be a prerequisite for creating or publishing a PR. Do not make preview/staging/production deployment evidence, post-merge rollout, or production validation a phase completion criterion, progress checkbox, acceptance gate, or `### Verify` command that must finish before PR creation. Put such work in a clearly labeled non-blocking `Post-merge delivery / operations` section with owner, trigger, evidence, rollback/observation guidance, and any separate workflow that will execute it.
- If source requirements genuinely require deployment or production observation, preserve that requirement as a post-merge delivery obligation without representing it as PR readiness or implementation completeness. A plan may require deployable configuration and truthful pre-merge verification; it may not require the deployment event itself before the PR exists.
- When a plan is rendered or delivered as HTML/Markdoc, load `doct-document-ops` and use the standard reviewer layout by default: a dark-mode visual theme with explicit dark background, light foreground text, readable muted text, accessible link/accent colors, `color-scheme: dark`, plus a full-width single-column page. Put a concise table of contents near the top of the document, immediately after the title/status summary and before the main plan sections. Format the ToC as a horizontal section with responsive columns so reviewers can scan links without sacrificing plan body width. Do not use a permanent left sidebar/rail for navigation. Do not leave color mode or navigation layout to browser, OS, or agent-selected defaults.
- When a plan is rendered, delivered, registered, or reviewed as HTML/Markdoc, delegate service details to `doct-document-ops`: register through `doct-agent plans register --base-url https://doct.nodaste.com --source-format <html|markdoc>`, preserve `listenerInstructions`, start the returned durable listener before asking for browser feedback, update through `doct-agent plans update`, share the canonical Doct URL, and process comments/actions through Doct listener/queue/agent/ack/resolve commands.
- Every user-facing HTML plan URL must be the canonical Doct URL from `https://doct.nodaste.com`; do not share local `plan-review`, loopback, or Tailscale service URLs unless the user explicitly requested a legacy local review service.

### Product-owner context contract

Near the top of every implementation plan, before implementation history, current-code detail, progress, phases, or verification mechanics, include a standalone product-owner context section. Write it for a product owner who has no prior issue, Linear, incident, or repository context. It must:

- explain the situation in plain language, defining unavoidable domain terms instead of leading with file paths, symbols, request traces, or issue chronology,
- explain why the change is needed now and what new evidence, failure, decision, or timing makes the work timely,
- state the key conclusion unmistakably, especially whether the plan addresses a customer/runtime product defect, a stale test or evidence problem, an operational/documentation gap, or a combination,
- separate the impact on `Customers`, `Runtime product behavior`, `Security / permissions`, `Testing / release confidence`, and `Deployment / migration`; explicitly say `No change` or `Not applicable` rather than silently omitting an unaffected dimension,
- distinguish observed facts from proposed work so a reviewer does not confuse a failing test with a shipped-product failure.

Keep this complexity-aware. A lightweight plan must satisfy the contract with concise labeled prose. A non-trivial plan must use a clearly scannable impact table or an equivalent structured block with those five impact dimensions. This is an authoring and review contract, not a Doct renderer requirement; preserve the standard dark full-width layout and fit the section into that layout.

### What's new contract

Immediately after Product-owner context and before Goal, every full implementation plan must include a standalone `What's new` section. Give it a behavior-focused headline and a one-sentence promise, then state the concrete audience-visible changes, before/after workflow, observable result, and preserved guarantees. It must not restate Goal, rationale, phases, or acceptance criteria; a heading without a distinct product delta does not satisfy the contract. This adds no new lightweight-plan requirement: only work already exempt from a full execution plan is exempt from `What's new`.

### Socratic plan questions

Every full implementation plan must answer these eight questions in prose. Validators check that each is present and non-empty, not the wording of the answer; `Not applicable because <evidence>` is a legitimate answer.

1. **First hour** — what a customer on the previous shipped version experiences in the first hour after the update.
2. **Consumers** — which contracts this change alters, who consumes each today, and how you will know each still works.
3. **Siblings** — the other instances of the pattern you are fixing.
4. **Moving ground** — what merged since the plan was scoped and any in-flight work on the same contracts; re-answer this per rebase.
5. **Falsification** — what would make this change wrong, and which test catches it.
6. **Proof** — the test that proves the customer-visible outcome from customer behavior, not from implementation pathways.
7. **Untested** — what this environment cannot verify and the residual risk, which feeds the review "Not examined:" list.
8. **Expansion log** — a living record of where you went beyond the ask and why it protects the outcome.

Required sections for new plans unless repo-local overrides say otherwise:

1. Title
2. Status
3. Product-owner context (situation, why now, key conclusion, and impact breakdown)
4. What's new (standalone product change and preserved guarantees)
5. Goal
6. Decision Attention / Low-confidence Areas
7. Why this plan exists
8. Authority and inputs
9. Current implementation reality
10. Progress
11. Resume instructions (agent)
12. Product intent alignment
13. Locked decisions
14. Acceptance criteria
15. BDD scenarios
16. Phase-by-phase execution plan
17. Verification strategy
18. Delivery order
19. Non-goals
20. Decisions / Deviations log

Decision Attention must appear near the top of every non-trivial plan, immediately after the Product-owner context, `What's new`, and goal/status framing. It indexes blockers, required user input, unresolved or low-confidence decisions, and areas where repo evidence is weak. If none remain, say `None` or `No product decision required` explicitly; do not omit the section or bury the answer in later phases.

For an HTML/Markdoc plan under browser review, put every product-shaping question in Decision Attention as a prominent `Decision Required` block instead of moving the question into chat. Give each decision a stable ID and include:

- the exact decision question and why it blocks readiness,
- every viable option supported by current evidence (do not present a partial shortlist while hiding a known viable choice),
- a thorough explanation of each option: resulting behavior, benefits, costs/risks, implementation and compatibility implications, and reversibility or migration consequences,
- the agent's recommended option, rationale, confidence level, and the evidence that drove the recommendation,
- an explicit browser-feedback instruction telling the reviewer to select an option or add a Doct comment with a custom decision.

Use a visually distinct warning/callout style and link each unresolved decision from the near-top table of contents or summary so it cannot be missed. Keep the plan non-execution-ready until the reviewer resolves every required decision. After feedback arrives, replace the unresolved block with the chosen decision in `Locked decisions` and append the choice and rationale to `Decisions / Deviations log`.

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
- lock canonical contracts, schemas, fixtures, payloads, or evidence sources before downstream phases depend on them,
- include only PR-bound implementation and verification work in executable phases and `Progress`; place deployment, promotion, merge-dependent validation, and production observation outside the phase/progress mapping as non-blocking post-merge delivery work.

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
- the standalone `What's new` section appears immediately after Product-owner context and before Goal, and is not missing, late, vague, or duplicative of Goal, rationale, phases, or acceptance criteria,
- Decision Attention is near the top and truthfully reports blockers, user-input needs, and low-confidence areas,
- required plan work stays faithful to the validated source scope as defined in the Scope section,
- the PR boundary is explicit, and deployment/promotion/post-merge observation is separated into non-blocking delivery guidance rather than a PR-readiness phase or progress gate,
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
- If repo evidence is insufficient and the choice changes intended behavior, obtain the user's decision before finalizing the plan.
- For a browser-reviewed HTML/Markdoc plan, obtain that decision through a prominent `Decision Required` block in the plan and Doct feedback; do not duplicate it as a chat question unless the review surface is unavailable.
- For a non-browser plan, ask the user directly.
- If the answer is researchable without user intent input, delegate research immediately or emit a non-ready `research-ready` research plan artifact.
- A non-ready plan artifact must list unresolved low-confidence decisions and the exact action that resolves each one: reviewer selection for product decisions or a concrete research action for researchable unknowns. Keep it clearly separate from an `execution-ready` handoff.
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

- Phase `### Verify` checks are agent-run pre-PR execution gates: they must be runnable during implementation, grounded in repo reality, and expanded with compensating checks when strict TDD is not practical. They may validate deployability, packaging, configuration, or dry-run behavior, but must not require an environment deployment, promotion, merge, or production observation before PR creation.
- Post-merge deployment and operational checks have separate ownership and evidence. Their pending state does not make the implementation plan unready, the PR slice incomplete, or PR creation blocked.
- Final completion still requires a semantic coherence review across the shared files touched by the work so reviewers confirm the doctrine means the same thing everywhere, not just that strings appear.

## Handoff to execution

When the plan is complete:

- leave the repo ready for the repo's canonical execution workflow,
- if repo-local guidance requires a plan review registration, prefer the Doct-backed `doct-document-ops` flow and verify the returned listener is running before browser-review handoff; use a checked-in/local plan server only when the repo or user explicitly requires that legacy surface,
- `ready for` means handoff-ready, not permission to start execution in the current command,
- if the active command is planning-only, stop after updating the plan and reporting the next suggested command,
- ensure the plan reflects repo-specific commands from `AGENTS.md`,
- keep deviations and migration notes append-only,
- do not stop with an implicit draft if the user asked for an execution-ready plan.
