## Inputs

Accept any of:

- a natural-language plan description,
- a plan slug,
- an existing `thoughts/plans/<slug>.html` path,
- an existing Markdown plan that should be converted into the reviewed HTML flow,
- a Linear issue key or URL when the repo guidance supports Linear intake.

Resolve to one canonical HTML plan path:

```text
thoughts/plans/<slug>.html
```

Use lowercase, digits, and hyphens for the slug. If the user gave an existing Markdown plan, read it as source input but write the reviewed artifact as HTML unless they explicitly ask to preserve Markdown-only planning.

## Workflow

### 1. Intake and repo guidance

1. Read the repo root `AGENTS.md`.
2. Read product-intent guidance when present, preferring `thoughts/specs/product_intent.md`, `PRODUCT_INTENT.md`, or the repo-documented equivalent.
3. Read `thoughts/plans/AGENTS.md` when present.
4. Read any source issue, handoff, existing plan, PRD, or specification the input references.
5. Inspect the repo enough to validate important claims, file paths, commands, data shapes, and integration points. Do not rely on the user's description alone for executable plan details.

When repo evidence leaves a consequential technical decision unresolved, load `oracle-consultation`, consult once, verify the response, and record its disposition in the plan's decisions/deviations log when it affects the plan.

When repo evidence cannot resolve a decision that changes user-visible behavior, security/privacy posture, data handling, scope, or compatibility, capture it in the HTML plan as a prominent `Decision Required` block for browser feedback. Oracle may improve the option analysis, but it cannot make the product choice or authorize scope expansion. Do not ask it separately in chat unless Doct registration or browser review is unavailable.

### 2. Create or refresh the HTML plan

Write or update `thoughts/plans/<slug>.html` as semantic HTML, not Markdown renamed as HTML.

The plan should follow the `planning-workflow` execution artifact contract while using reviewer-friendly HTML structure:

- standard reviewer layout: dark-mode theme with explicit dark background, light foreground, readable muted text, accessible link/accent colors, `color-scheme: dark`, and a full-width single-column page; place a concise table of contents near the top of the document immediately after the title/status summary, and format it as a horizontal section with responsive columns so the rest of the plan keeps full width; do not use a permanent left sidebar/rail,
- stable `id` attributes on major sections, phase wrappers, acceptance criteria, BDD scenarios, diagrams, figures, and likely comment targets,
- a near-top standalone `Product-owner context` section, before implementation history and technical detail, that explains the situation in plain language for a reader with no issue/Linear context, explains why the work is needed now, and states the key conclusion unmistakably (for example, runtime/customer defect versus stale test or operational evidence); for non-trivial plans use a scannable impact table or equivalent structured block with separate `Customers`, `Runtime product behavior`, `Security / permissions`, `Testing / release confidence`, and `Deployment / migration` entries, using `No change` or `Not applicable` where appropriate; lightweight plans must use at least concise labeled prose,
- a standalone `What's new` section after Product-owner context and before Goal that satisfies the canonical `planning-workflow` contract; a mere heading or a restatement of Goal, rationale, phases, or acceptance criteria is not sufficient,
- a near-top `Decision Attention / Low-confidence Areas` section after Product-owner context, `What's new`, and Goal for blockers, required user input, unresolved decisions, and weak evidence; each unresolved product decision is a visually prominent `Decision Required` block with a stable ID, the exact question, every viable option, a thorough explanation of each option's behavior/benefits/costs/risks/implementation and compatibility implications/reversibility, and the agent's recommended option with rationale, confidence, and supporting evidence,
- a `Progress` section containing the only checkboxes,
- canonical content: status, product-owner context, What's new, goal, Decision Attention / Low-confidence Areas, why this exists, authority and inputs, current implementation reality, product intent alignment, locked decisions, acceptance criteria, BDD scenarios, phase-by-phase execution plan, verification strategy, delivery order, non-goals, resume instructions, and decisions/deviations log,
- one-to-one mapping between progress checkboxes and detailed phases,
- each phase includes `End State`, `Verification`, `Expected files`, `Work`, `Open questions / decision dependencies`, and `Verify`,
- explicit UI-impact triage with repo-appropriate design evidence for real UI-impacting work,
- exact verification commands grounded in repo reality,
- when `integration-integrity` is triggered, a `Contract and distributed-integration inventory` that maps its record into the plan. Do not add an empty inventory when no trigger applies,
- no unresolved open questions when the status is `execution-ready`; plans awaiting a reviewer choice remain non-ready and explicitly instruct the reviewer to select an option or leave a Doct comment with a custom decision.

If a prior reviewed plan exists, preserve truthful completed progress, stable IDs where possible, and append-only decisions/deviations history.

### 3. Register the plan for browser review

Use `doct-document-ops` as the sole source for current Doct registration commands and service behavior.

1. Confirm `doct-agent` auth/context for `https://doct.nodaste.com` as documented by `doct-document-ops`.
2. Register the plan through `doct-agent plans register --base-url https://doct.nodaste.com --source-format html --title '<Plan Title>'`, using `--allow-untemplated` for the handcrafted HTML plans this workflow produces. The title must match the plan file's `<title>` and top-level `<h1>`. Never hand off a browser-review draft that shows **Untitled Plan**.
3. Parse the registration JSON and preserve the returned Doct document/plan id, workspace id, canonical URL, current version, `sourceGuidance`, and full `listenerInstructions`.
4. Follow the current `doct-document-ops` listener contract immediately, including startup claim processing, host-specific supervision, restart behavior, and pre-execution ownership. Do not duplicate or weaken that contract here. Leave the plan in its registration/default board column (normally `backlog`); implementation execution workflows own the transition to `in_progress`.
5. Share the canonical Doct review URL only after the listener is running, or report a concrete listener-start blocker. Never show a loopback, local `plan-review`, Tailscale local-service URL, or relative path to the user unless they explicitly requested a legacy local reviewer.
6. Use listener-delivered events for browser comments/actions. Use `doct-agent plans queue list` and `doct-agent plans agent next --no-wait` for startup drain, recovery, or manual processing only.

If browser feedback has not yet been provided, share the Doct URL and enter the monitoring state defined by `doct-document-ops`. In Codex, keep the task active and process routed feedback as it arrives without requiring the user to say “feedback is ready”; retain listener ownership until an execution workflow moves the plan to `in_progress`, the lifecycle ends, or the user cancels.

For a browser-reviewed plan, **generic feedback is not an execution-ready review request**. Process and resolve each ordinary routed comment, then return to the browser-review loop. Do not start PM or independent Sol-medium planner readiness review because the first comment was handled, the listener is quiet, or the plan has no queued work. Start the readiness cycle only after either:

- the operator directly instructs the agent to begin execution-readiness review, or
- Doct dispatches its explicit **Request execution-ready review** action. The current toolbar action carries `routingMetadata.agentRoute.requestedSkill: "plan-reviewer-execution-ready"`; accept an explicit `routingMetadata.submitAction: "execution-ready"` when returned by the service.

A generic `routingMetadata.submitAction: "agent"` with only `targetScope: "plan-review"` is not sufficient.

### 4. Process browser feedback

Process reviewer comments/actions through the Doct plan queue. Keep the plan in browser review unless the current item is an explicit execution-ready request as defined in the preceding section.

For each listener-delivered or pending comment:

1. Use the thread id, claim id, workspace id, document id, selected context, and returned ack/resolve/release commands from the listener payload or `doct-agent plans agent next`. If no claim is available during manual recovery, inspect `doct-agent plans queue list` until it reports no pending work.
2. Read the full plan before editing.
3. Use the annotation context, heading path, quoted text, and reviewer note.
4. Classify the comment as `READINESS_BLOCKER`, `PRODUCT_QUESTION`, `OPTIONAL_CLARITY`, `OUT_OF_SCOPE_FOLLOW_UP`, `DISAGREE_REPO_EVIDENCE`, `EXECUTION_READY_REQUEST`, or `BUILD_REQUEST`.
5. Edit the plan for readiness blockers and useful clarity that preserves scope.
6. For product questions that cannot be resolved from repo evidence, add or update the plan's prominent `Decision Required` block with all viable options, thorough option explanations, and an agent recommendation; obtain the choice through Doct feedback rather than a separate chat question.
7. Ack and resolve only after the plan actually addresses the comment; after the user chooses, move the result into `Locked decisions` and append the rationale to `Decisions / Deviations log`.
8. Keep or restart the durable listener after each dispatch if more browser feedback is expected; do not leave review handoff dependent on a one-time queue check.

For `EXECUTION_READY_REQUEST`, reply/ack that the readiness cycle is beginning, record the request in the scoped review artifact, then continue to the PM and independent Sol-medium planner readiness legs below. For every other classification, complete the plan update/ack/resolve and return to the browser-review loop. Do **not** infer a readiness request from generic routed `submitAction: "agent"` feedback or a quiet listener.

If material feedback arrives before implementation starts, update the plan and clear stale readiness metadata. A fresh explicit readiness request and independent review are required. Preserve any external ledger ownership; report the changed plan to its owner through the authorized task coordination path rather than mutating that ledger.

Keep the local HTML plan authoritative for implementation and Doct authoritative for review state. After editing the local file, push updates with `doct-agent plans update` or keep `doct-agent plans watch` running during active review. `plans watch` is source sync only; it does not replace the comment listener.
