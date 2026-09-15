## Canonical plan contract

When discovery finds an exact contract that types cannot fully verify or behavior required across multiple production sites, load integration-integrity and add a Contract and distributed-integration inventory. Record the source of truth, producers/consumers or site/family inventory, dependent docs/examples, coverage declaration, required cross-boundary or production-path proof, and reconciliation state. Omit an empty inventory when neither trigger applies. Verify contractual documented CLI forms through the actual parser.

Write plans as execution artifacts, not brainstorming notes. A ready plan must be executable by another agent without inventing missing semantics.

- Keep required plan work faithful to the validated source scope as defined in the Scope section above.
- Plan complete promised slices, not skeletons. Every claimed functional outcome must be connected, usable, and verifiable within its stated scope, without required stubs, TODO behavior, dead-end surfaces, missing producer/consumer wiring, fake success, or verification that bypasses the real implementation.
- If the requested outcome cannot be completed safely in one change, resize it before implementation to a smaller independently useful complete slice. Independent future enhancements, scale work, optional hardening, and polish may remain out of scope; work required for the current slice to function as claimed may not.
- Define the complete promised slice at the **PR boundary**: code, tests, docs, migration definitions, release configuration, and buildable artifacts that can truthfully be reviewed before merge. An environment deployment, promotion, merge, production observation window, or post-merge smoke check is delivery/operations work, not missing implementation in the PR slice.
- Deployment must never be a prerequisite for creating or publishing a PR. Do not make preview/staging/production deployment evidence, post-merge rollout, or production validation a phase completion criterion, progress checkbox, acceptance gate, or `### Verify` command that must finish before PR creation. Put such work in a clearly labeled non-blocking `Post-merge delivery / operations` section with owner, trigger, evidence, rollback/observation guidance, and any separate workflow that will execute it.
- If source requirements genuinely require deployment or production observation, preserve that requirement as a post-merge delivery obligation without representing it as PR readiness or implementation completeness. A plan may require deployable configuration and truthful pre-merge verification; it may not require the deployment event itself before the PR exists.
- When a plan is rendered or delivered as HTML, use the standard reviewer layout by default: a dark-mode visual theme with explicit dark background, light foreground text, readable muted text, accessible link/accent colors, `color-scheme: dark`, plus a full-width single-column page. Put a concise table of contents near the top of the document, immediately after the title/status summary and before the main plan sections. Format the ToC as a horizontal section with responsive columns so reviewers can scan links without sacrificing plan body width. Do not use a permanent left sidebar/rail for navigation. Do not leave color mode or navigation layout to browser, OS, or agent-selected defaults.
- When the user explicitly requests Doct publication or review, use doct-document-ops for HTML publishing, title consistency, canonical URLs, listener startup, and state updates.
- If a plan is registered in Doct, every user-facing URL must be the canonical Doct URL from `https://doct.nodaste.com`; do not share local `plan-review`, loopback, or Tailscale service URLs unless the user explicitly requested a legacy local review service.

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

For an HTML plan under browser review, put every product-shaping question in Decision Attention as a prominent `Decision Required` block instead of moving the question into chat. Give each decision a stable ID and include:

- the exact decision question and why it blocks readiness,
- every viable option supported by current evidence (do not present a partial shortlist while hiding a known viable choice),
- a thorough explanation of each option: resulting behavior, benefits, costs/risks, implementation and compatibility implications, and reversibility or migration consequences,
- the agent's recommended option, rationale, confidence level, and the evidence that drove the recommendation,
- an explicit browser-feedback instruction telling the reviewer to select an option or add a Doct comment with a custom decision.

Use a visually distinct warning/callout style and link each unresolved decision from the near-top table of contents or summary so it cannot be missed. Keep the plan non-execution-ready until the reviewer resolves every required decision. After feedback arrives, replace the unresolved block with the chosen decision in `Locked decisions` and append the choice and rationale to `Decisions / Deviations log`.

Legacy heading aliases may be preserved in historical plans, but new plans should use canonical headings unless the repo explicitly says otherwise.

## Phase template

Every phase must include:

- `### End State`
- `### Verification`
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
