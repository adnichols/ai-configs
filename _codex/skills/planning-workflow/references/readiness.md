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
- For a browser-reviewed HTML plan, obtain that decision through a prominent `Decision Required` block in the plan and Doct feedback; do not duplicate it as a chat question unless the review surface is unavailable.
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
- do not register the plan in Doct unless the user asked or repo-local guidance requires a plan review registration. When registration is required, use the Doct-backed `doct-document-ops` flow and verify the returned listener is running before browser-review handoff; use a checked-in/local plan server only when the repo or user explicitly requires that legacy surface,
- `ready for` means handoff-ready, not permission to start execution in the current command,
- if the active command is planning-only, stop after updating the plan and reporting the next suggested command,
- ensure the plan reflects repo-specific commands from `AGENTS.md`,
- keep deviations and migration notes append-only,
- do not stop with an implicit draft if the user asked for an execution-ready plan.
