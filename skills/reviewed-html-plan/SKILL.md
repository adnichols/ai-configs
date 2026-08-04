---
name: reviewed-html-plan
description: Create and gate execution-ready HTML development plans through Doct plan registration via `doct-agent plans` on `https://doct.nodaste.com`. For browser-reviewed plans, integrate comments but wait for an explicit execution-ready review request before PM and independent Sol-medium planner readiness review. Use this whenever the user asks for the plan review process, a reviewed HTML plan, a pre-execution plan gate, or wants a plan created from a description and registered in Doct for browser feedback before implementation.
---

# Reviewed HTML Plan Workflow

Use this skill when the user wants the planning and review process completed before implementation starts. The output is a single reviewed HTML plan that is registered in Doct through `doct-agent plans` on `https://doct.nodaste.com` and either marked execution-ready or explicitly blocked on a product/scope decision.

The planning agent stops before product-code execution and may edit only the plan artifact. In a delivery-managed Herdr run, its final `EXECUTION_READY` transition automatically launches a separate dedicated implementation agent; in planning-only use, no implementation agent is launched.

## Required companion skills

Load and follow these skills when this workflow reaches their surface:

- `planning-workflow` for the plan-writing contract and execution-readiness bar.
- `doct-document-ops` for HTML/Markdoc plan structure, dark-mode requirements, Doct registration, canonical Doct URLs, mandatory post-registration listener startup, plan updates, comment/action queue handling, claim/ack/resolve behavior, Markdown/text fallback publishing, and source sync/watch behavior.
- `product-principles` for workflow, defaults, recovery, status, error handling, product-intent, and early-stage scope review.
- In Pi, the `planner` subagent for the single independent read-only plan-review leg. Its checked-in frontmatter pins `openai-codex/gpt-5.6-sol` at medium reasoning. Do not pass a caller-side model or thinking override. Non-Pi harnesses use their configured planning persona only when it provides equivalent independent read-only review; a Pi delivery ledger cannot reach `EXECUTION_READY` without the fixed Sol-medium review evidence.
- In Pi, the `oracle` subagent is optional bounded decision support during plan authoring or revision. Use it proactively when targeted repo inspection leaves competing technical approaches, ownership boundaries, compatibility tradeoffs, or drift from locked decisions genuinely ambiguous — do not wait for the operator to request it. Launch with only `subagent_type: "oracle"`, a short description, and the decision packet; omit caller-side `model`, `thinking`, `inherit_context`, and `isolation`. Oracle is advisory only and never replaces browser feedback, product-owner decisions, PM review, or the independent Sol-medium planner readiness verdict.
- Domain skills required by the target repository guidance, stack, or plan surface.

If a required review tool is unavailable, follow the relevant skill's remediation first. Stop only when the dependency cannot be restored safely or the next step requires a real product decision.

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

When repo evidence leaves a consequential technical decision ambiguous, the Pi planning agent should consult `oracle` once with the bounded decision, inherited constraints, evidence, credible options, its current recommendation and uncertainty, and one narrow question ending with `?`. Omit caller-side model/thinking/inherit_context/isolation overrides. Verify the response against current sources and record disposition (`accepted` / `partially-accepted` / `rejected` / `escalated`) with why in the plan's decisions/deviations log when it affects the plan. Do not use Oracle for routine discovery or to rubber-stamp a preferred option.

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
- the conditional planning evidence required by `planning-workflow` when exact-contract, distributed-behavior, or material-uncertainty triggers apply: consumer/sibling inventory, moving-ground checks, falsification and production-path proof, residual risk, and expansion disposition in the existing sections where reviewers act on them; do not require a standalone questionnaire,
- canonical content: status, product-owner context, What's new, goal, Decision Attention / Low-confidence Areas, why this exists, authority and inputs, current implementation reality, product intent alignment, locked decisions, acceptance criteria, BDD scenarios, phase-by-phase execution plan, verification strategy, delivery order, non-goals, resume instructions, and decisions/deviations log,
- one-to-one mapping between progress checkboxes and detailed phases,
- each phase includes `End State`, `Tests first`, `Expected files`, `Work`, `Open questions / decision dependencies`, and `Verify`,
- explicit UI-impact triage with repo-appropriate design evidence for real UI-impacting work,
- exact verification commands grounded in repo reality,
- when discovery finds an exact contract that types cannot fully verify or behavior distributed across production sites, a `Contract and distributed-integration inventory` with the source of truth; producer/consumer or source-search-backed operation rows; dependent docs/examples; cross-boundary or production-path proof; reconciliation status; and an exhaustive-by-site, exhaustive-by-family, or justified-representative coverage declaration. The plan must say `None identified, based on <source search>` when neither trigger applies. Helpers, wrappers, middleware, and event-existence tests do not close a distributed outcome; contractual documented CLI forms execute through the actual parser,
- no unresolved open questions when the status is `execution-ready`; plans awaiting a reviewer choice remain non-ready and explicitly instruct the reviewer to select an option or leave a Doct comment with a custom decision.

If a prior reviewed plan exists, preserve truthful completed progress, stable IDs where possible, and append-only decisions/deviations history.

### 3. Register the plan for browser review

Use `doct-document-ops` as the sole source for current Doct registration commands and service behavior.

1. Confirm `doct-agent` auth/context for `https://doct.nodaste.com` as documented by `doct-document-ops`.
2. Register the plan through `doct-agent plans register --base-url https://doct.nodaste.com --source-format html --title '<Plan Title>'`, using `--allow-untemplated` for the handcrafted HTML plans this workflow normally produces. The title must match the plan file's `<title>` and top-level `<h1>` (or Markdoc frontmatter `title:` when the source is Markdoc). Never hand off a browser-review draft that shows **Untitled Plan**.
3. Parse the registration JSON and preserve the returned Doct document/plan id, workspace id, canonical URL, current version, `sourceGuidance`, and full `listenerInstructions`.
4. Follow the current `doct-document-ops` listener contract immediately, including startup claim processing, host-specific supervision, restart behavior, and pre-execution ownership. Do not duplicate or weaken that contract here. Leave the plan in its registration/default board column (normally `backlog`); implementation execution workflows own the transition to `in_progress`.
5. Share the canonical Doct review URL only after the listener is running, or report a concrete listener-start blocker. Never show a loopback, local `plan-review`, Tailscale local-service URL, or relative path to the user unless they explicitly requested a legacy local reviewer.
6. Use listener-delivered events for browser comments/actions. Use `doct-agent plans queue list` and `doct-agent plans agent next --no-wait` for startup drain, recovery, or manual processing only.

If browser feedback has not yet been provided, share the Doct URL and enter the monitoring state defined by `doct-document-ops`. In Codex, keep the task active and process routed feedback as it arrives without requiring the user to say “feedback is ready”; retain listener ownership until an execution workflow moves the plan to `in_progress`, the lifecycle ends, or the user cancels.

For a browser-reviewed plan, **generic feedback is not an execution-ready review request**. Process and resolve each ordinary routed comment, then return to the browser-review loop. Do not start PM or independent Sol-medium planner readiness review because the first comment was handled, the listener is quiet, or the plan has no queued work. Start the readiness cycle only after either:

- the operator directly instructs the agent to begin execution-readiness review, or
- Doct dispatches its explicit **Request execution-ready review** action. The current toolbar action carries `routingMetadata.agentRoute.requestedSkill: "plan-reviewer-execution-ready"`; accept an explicit `routingMetadata.submitAction: "execution-ready"` when returned by the service.

A generic `routingMetadata.submitAction: "agent"` with only `targetScope: "plan-review"` is not sufficient. When this workflow runs under delivery, record `planReadinessRequest=pass` before advancing from `PLAN_BROWSER_REVIEW`; `delivery` binds the record to the current plan content and rejects PM/technical review and `EXECUTION_READY` stages without a current authorization record.

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

For `EXECUTION_READY_REQUEST`, reply/ack that the readiness cycle is beginning, record delivery evidence when a ledger exists, then continue to the PM and independent Sol-medium planner readiness legs below. For every other classification, complete the plan update/ack/resolve and return to the browser-review loop. Do **not** infer a readiness request from generic routed `submitAction: "agent"` feedback or a quiet listener.

If a material comment arrives after the plan was marked execution-ready but before implementation starts, reply and update the plan, clear its execution-ready metadata, and return the delivery ledger to `PLAN_BROWSER_REVIEW`. When a delivery ledger exists, run `delivery revoke-implementation-approval --reason "material plan feedback"`. The correction requires a fresh explicit execution-ready request and a fresh readiness review; a prior ready verdict does not survive a material plan edit.

Keep the local HTML plan authoritative for implementation and Doct authoritative for review state. After editing the local file, push updates with `doct-agent plans update` or keep `doct-agent plans watch` running during active review. `plans watch` is source sync only; it does not replace the comment listener.

### 5. PM product-intent review

Run an adversarial PM review only after the explicit execution-ready request opened the readiness cycle. Do not run it merely because browser feedback was processed.

The PM pass evaluates whether the plan will satisfy the intended user/operator outcome, not merely whether the phases are internally coherent. Use `product-principles` and repo product intent to check:

- the real user impact and intended job-to-be-done,
- whether the near-top product-owner context stands alone without issue history, explains why now, separates the five impact dimensions, and makes the runtime-defect-versus-evidence-problem conclusion impossible to miss,
- whether `What's new` is missing, late, vague, or duplicative of surrounding sections; treat any such defect as blocking and do not issue an execution-ready verdict until the section satisfies the canonical `planning-workflow` contract (a heading alone is not compliance),
- golden-path usability,
- safe defaults and inferred inputs,
- routine self-healing versus fail-closed boundaries,
- truthful status, docs, help text, and agent-legible errors,
- early-stage stage fit and the smallest complete slice,
- whether verification proves the shipped workflow, not just helper behavior,
- whether triggered planning evidence appears in the contract inventory, acceptance/BDD, verification/residual-risk, and decisions/deviations sections rather than being replaced by a standalone questionnaire.

Default behavior is corrective: reshape the HTML plan directly when the right direction is inferable from repo evidence. When a product-shaping decision remains low-confidence, keep the plan blocked and surface the decision prominently in the HTML plan for Doct feedback, with all viable options, thorough explanations, and the agent's recommendation. In Pi, an Oracle consultation may challenge a low-confidence technical recommendation before it is presented, but Oracle does not count as PM or product-owner approval.

After material PM edits, ensure the review URL still points at the latest plan and the plan remains browser-reviewable.

### 6. Independent Sol-medium planner review

An earlier Oracle consultation does not satisfy, skip, or modify this gate. Oracle answers a bounded decision question; the `planner` independently evaluates the whole current plan for execution readiness and selects the implementation profile.

After the explicit execution-ready request and PM pass, run exactly one Pi `planner` subagent before execution and keep it read-only. The checked-in planner frontmatter pins `openai-codex/gpt-5.6-sol` at medium reasoning, so this independent pass happens regardless of the model that authored the plan or started delivery. Do not pass a model or thinking override. The planner also selects the implementation profile: choose `terra-high` by default when deterministic tests can strongly validate the changed behavior; choose `sol-medium` when meaningful correctness is hard to validate before merge or depends materially on critical technical judgment. The same planner is used at every risk level; high-risk plans receive a more focused review packet, not a second external review leg:

- For data loss, auth/security, concurrency/locking, migrations/persistence, release-blocking CI behavior, release-risk, or another P1/P2 risk surface, give the reviewer a compact readiness packet with named files/surfaces, the exact risk question, relevant plan excerpts, verification expectations, and outcome limits.
- For lower-risk plans, retain the same bounded readiness packet without broadening into a second opinion.

Invoke Pi's native `planner` subagent with `subagent_type: "planner"` and capture the returned result in `thoughts/validation/<slug>-plan-review.md`. The planner is read-only for this call: the coordinating agent writes the returned review artifact and remains the only authority that may edit the plan. Do not launch separate Codex or Claude Code sessions and do not require Herdr transport. Launch `planner` via `Agent` with the `isolation` property omitted entirely; never set `isolation: "worktree"`. Inspect the final tool arguments and remove that property before launch. The review must still work in any clean, dirty, detached, or isolated state if the harness itself changes the launch topology. Reuse the candidate-visibility contract from `skills/autoreview/SKILL.md`: put the absolute `TARGET_CHECKOUT`, coordinator HEAD/status, and changed/untracked plan paths in the packet; require provenance (`CWD`, `REVIEW_ROOT`, `HEAD`, `STATUS_SHORT`, and `REVIEW_SOURCE`). If launch CWD differs, the reviewer must inspect `TARGET_CHECKOUT` directly with path-qualified reads and `git -C`. Never discard or refuse a visible plan review solely because the launch checkout is temporary, isolated, clean, or dirty. If a genuinely unavailable dirty portion matters, preserve findings over visible content and run at most one narrowed follow-up with the missing patch or target paths. The reviewer must return a concrete readiness verdict; invalid, empty, tool-only, provider-error, or incomplete output is a review-infrastructure failure and receives at most one narrower rerun.

The coordinating agent may integrate plan edits, but after material edits it must rerun the Sol-medium planner before marking the plan execution-ready. If the configured planner is unavailable, leave the plan blocked on review infrastructure.

When a delivery ledger exists, record the final current-plan verdict with the fixed provenance fields before entering `EXECUTION_READY`:

```bash
delivery record planTech --status pass \
  --artifact thoughts/validation/<slug>-plan-review.md \
  --summary "independent Sol medium plan-readiness review" \
  --reviewer planner --model openai-codex/gpt-5.6-sol \
  --reasoning-level medium --verdict PLAN_EXECUTION_READY \
  --implementation-profile terra-high|sol-medium \
  --implementation-rationale "why the normal Terra profile applies, or why Sol is warranted"
delivery stage EXECUTION_READY
```

`delivery` fingerprints the current plan and validates the artifact, reviewer identity, model, reasoning level, verdict, optional profile selection, and selection rationale. New reviews should always record the profile decision. Legacy reviews without these fields remain on Sol medium rather than being silently moved to a new profile. Any plan edit or fresh readiness request invalidates the prior review.

#### Reviewer packet

The reviewer input should include:

- `TARGET_CHECKOUT`: the absolute candidate checkout path,
- `COORDINATOR_HEAD`: the coordinator's current short commit SHA,
- `COORDINATOR_STATUS_SHORT`: the coordinator's `git status --short` snapshot or `EMPTY`,
- changed paths, explicitly including staged, unstaged, and untracked plan/artifact paths,
- required reply provenance: `CWD`, `REVIEW_ROOT`, `HEAD`, `STATUS_SHORT`, and `REVIEW_SOURCE`,
- plan path and review URL,
- source request or issue summary,
- repo guidance paths,
- product-intent path when present,
- readiness rubric,
- known non-goals,
- instruction to avoid adjacent implementation expansion,
- instruction not to edit files.

For the single plan-review pass, stay limited to readiness concerns, including at least:

- whether `What's new` is missing, late, vague, or duplicative/restated; it must be present immediately after product-owner context and before goal, with a behavior-focused headline, one-sentence product promise, concrete audience-visible changes, before/after workflow, observable result, and preserved guarantees; it does not restate goal, rationale, phases, or acceptance criteria; instruct the reviewer not to return an execution-ready verdict until the canonical section is distinct and correctly placed,
- whether the plan has executable phases,
- whether acceptance criteria and verification are testable,
- whether deterministic tests exercise enough of the meaningful behavior to use `terra-high`; otherwise require `sol-medium`, especially for critical technical work where correctness depends on judgment, environment behavior, concurrency, persistence, security, or another result that cannot be confidently established by pre-merge tests,
- whether scope and non-goals prevent expansion,
- whether unresolved product questions remain,
- whether the plan has enough file/surface specificity for implementation,
- whether architecture/dependency risks are resolved enough to execute,
- whether any triggered Contract and distributed-integration inventory names an actual source of truth, source-search-backed producer/consumer or production-site set, meaningful dimensions, cross-boundary or real-dispatch proof, and an honest coverage declaration; reject helper-only, wrapper-only, middleware-only, or event-existence-only completion claims,
- whether recovery/operator/error behavior is specified when relevant.

For every reviewer, use bounded scope rather than parent-side turn caps. Do not cap tool calls or lower `max_turns` to force completion; hard caps can truncate the final verdict and produce unusable output. Give each reviewer a concrete readiness packet and require a final verdict. If any reviewer cannot complete the assigned readiness scope, it must return a non-ready result with completed checks, remaining checks, and the exact follow-up slice the parent should run next. If the caller explicitly supports `REVIEW_INCOMPLETE_RERUN_NEEDED`, use that verdict; otherwise map incomplete coverage to `VERDICT: PLAN_NEEDS_REVISION` with the same completed-checks, remaining-checks, and follow-up-slice fields.

Non-empty review content, an allowed readiness verdict, and complete assigned coverage are required. Empty output, unclassifiable verdicts, tool-only output, provider errors, contradictory verdict/body content, or incomplete coverage do not count as independent readiness review. Rerun once with a narrower bounded readiness prompt only when the review output itself is unusable; do not fix empty reviewer output by adding or lowering parent-side turn limits. If the narrowed rerun is still unusable, stop with a tooling blocker and leave the plan not execution-ready.

Do not confuse an accepted plan-review verdict with an implementation-specific aggregate token. When each required leg is nonce-valid, fingerprint-valid, complete, and returns `PLAN_EXECUTION_READY`, the plan-review gate passes by substance even if a generic helper mistakenly reports infrastructure failure because it only recognizes an implementation green token such as `PASS` (or legacy `CLEAN_FOR_PR`). Record that condition as an orchestrator profile mismatch, preserve the accepted per-leg evidence, and do not rerun completed reviewers solely to satisfy the helper. Non-blocking `OPTIONAL_CLARITY`, `OUT_OF_SCOPE_FOLLOW_UP`, or `DISAGREE_REPO_EVIDENCE` observations may coexist with `PLAN_EXECUTION_READY`; readiness requires no blocking gap and complete assigned coverage, not an observation-free response.

Split a readiness review into focused passes when a plan spans three or more product surfaces, or when the readiness scope is otherwise too broad for one concrete readiness packet. Use focused passes such as product intent and scope boundaries, BDD/verification adequacy, architecture/dependency risks, and recovery/operator/error behavior. The parent must synthesize all slice verdicts and cannot mark the plan execution-ready until every required slice is complete or explicitly blocked.

Ask each applicable reviewer for one of these verdicts:

```text
VERDICT: PLAN_EXECUTION_READY
VERDICT: PLAN_NEEDS_REVISION
VERDICT: BLOCKED_BY_PRODUCT_QUESTION
VERDICT: REVIEW_INCOMPLETE_RERUN_NEEDED
IMPLEMENTATION_PROFILE: terra-high|sol-medium
IMPLEMENTATION_RATIONALE: <one concise evidence-based sentence>
```

Require the implementation profile and rationale with a ready verdict. Use `terra-high` when the planned deterministic tests strongly exercise the meaningful behavior. Use `sol-medium` when they do not, or when critical correctness depends materially on technical judgment beyond the available test evidence.

Normalize fuzzy reviewer output by substance, but never normalize empty, tool-only, provider-error, or incomplete-coverage output into a ready verdict. Treat a review as ready only when it finds no blocking readiness gaps and all required slices are complete.

### 7. Integrate and iterate to execution-ready

For every reviewer finding, triage before editing:

```text
Finding | Source | Classification | Decision | Evidence
```

Use these classifications:

- `READINESS_BLOCKER`: fix before execution.
- `PRODUCT_QUESTION`: ask the user before execution.
- `OPTIONAL_CLARITY`: integrate only when it improves execution confidence without widening scope.
- `OUT_OF_SCOPE_FOLLOW_UP`: do not add to this plan only when it is outside the plan, not required for truthful verification, and not an acceptance-criteria/BDD gap; record it with evidence and a tracking destination if useful.
- `DISAGREE_REPO_EVIDENCE`: do not change the plan; record the evidence if the disagreement matters.

After fixing readiness blockers, rerun the Sol-medium planner. If it returns incomplete coverage, launch the recommended follow-up slice, record completed checks, remaining checks, rerun slices, and final synthesized readiness status, then continue until the required coverage is complete or explicitly blocked. When the planner agrees by substance that the plan is execution-ready, update the same Doct-registered HTML plan and status/board metadata using the current `doct-document-ops` Doct flow.

#### Independent sign-off gate (do not self-certify)

The closing ready verdict that marks a plan `execution-ready` must come from the independent Sol-medium `planner` subagent, not the plan author/self. For this workflow, `PLAN_EXECUTION_READY` is the required ready verdict. The plan author may *integrate* review findings but may **never self-certify** execution readiness:

- A `plan-author` / `plan-owner` / `pi` / `self` review verdict does not clear the gate, even if it is the latest review.
- If any independent review returns `BLOCKED`, `PLAN_NEEDS_REVISION`, or raises in-scope findings, run a **fresh independent review after integrating** the fixes. The integration edit itself does not clear the gate; only a new independent ready verdict does.
- The independent ready verdict must not be followed by any later non-pass review, and should post-date the last material plan edit. If you edit the plan after the independent pass, re-review.
- Record reviews truthfully in the `review-record` section with the real reviewer identity. Do not relabel a self-review as a planner-subagent review to satisfy the gate — actually run the independent Sol-medium planner.

This workflow enforces the gate through the reviewer loop and truthful Doct plan state/metadata. Do not claim a local mechanical validator exists unless the target repo actually provides one; in repos without such a validator, the PM/reviewer gates and Doct review state are the enforcement surface.

Stop and report a convergence blocker if:

- the same readiness finding recurs after two revision attempts,
- reviewers disagree and repo evidence does not resolve the disagreement,
- a product question remains unanswered,
- three full review cycles do not converge.

Require each planner pass to return the complete bounded blocker set it found, not one representative blocker. In a delivery-managed run, each `planTech=gap` record consumes one planning-review cycle and the CLI refuses a fourth ordinary gap cycle; record a blocker or obtain an explicit operator decision instead of renaming or restarting the review loop.

If AI reviews materially reshape product intent, run one final PM check before declaring the plan execution-ready.

### 8. Final readiness gate

Before final output, inspect the HTML plan for obvious handoff blockers:

- unresolved browser-review comments remain in the queue, or the required listener was never started after registration,
- the Doct registered plan has not been updated after a successful Sol-medium planner plan review, or its lifecycle/board/readiness state is stale,
- unresolved inline review markers or unresolved question sections remain,
- status is not `execution-ready`,
- the near-top product-owner context is missing, assumes prior issue knowledge, buries why-now or the key conclusion, or fails to separate customer, runtime, security/permissions, testing/release, and deployment/migration impact,
- near-top Decision Attention is missing or hides unresolved decisions,
- `Progress` or resume instructions are missing,
- progress checkboxes and detailed phases do not map one-to-one,
- an active phase is missing `End State`, `Tests first`, `Expected files`, `Work`, `Open questions / decision dependencies`, or `Verify`,
- UI impact is missing, `unknown`, or lacks required design evidence for real UI-impacting work,
- verification commands are stale or not copy/paste ready,
- the independent Sol-medium planner did not agree by substance that the plan is ready,
- PM review left unresolved product-intent or user-impact gaps,
- PM and Sol-medium planner readiness review began without an explicit execution-ready request (unless the operator directly requested that review).

Do not implement product code in the planning agent. In a delivery-managed run, the final action of this skill is the automatic handoff below; the dedicated implementation agent owns all code, tests, fixes, Git, and PR work.

### 8b. Automatic execution-ready handoff

For a delivery-managed run, `execution-ready` authorizes the reviewed plan to proceed automatically. After the explicit execution-ready review request, PM readiness, and independent Sol-medium `PLAN_EXECUTION_READY` verdict are current for the exact plan, enter `EXECUTION_READY`:

```bash
delivery stage EXECUTION_READY
```

That transition records workflow authorization, launches and prompts a dedicated Herdr Pi agent on the planner-selected profile, and continues toward implementation, verification, review, and PR creation without another routine operator approval. The planning agent stops after the handoff. Use `--hold` only when the operator explicitly requests a pause or a real external dependency prevents execution.

The planner's profile remains a workflow default, not a prohibition. A deliberate manual model/reasoning override may be recorded through the compatibility `approve-implementation` command after `delivery stage EXECUTION_READY --hold`, or from the already-recorded implementation pane with `delivery verify-implementation-profile --adopt-current-runtime --reason "..."`. If material plan feedback arrives before code work, revoke the authorization and return to browser review for a fresh readiness request and review.

For planning-only use without a delivery ledger, stop after publishing the execution-ready plan; do not create an implementation worktree or edit product code.

## Final output

Use this structure:

```markdown
## Reviewed HTML Plan Ready

Plan: thoughts/plans/<slug>.html
Review URL: <canonical Doct URL>

### Gates completed
- Browser feedback: <processed / skipped by request / blocked>
- Execution-ready request: <Doct action / direct operator instruction>
- PM review: <ready / reshaped plan / blocked>
- Active-harness reviewer: <model/effort and verdict>

### Changes made during review
- ...

### Final status
<execution-ready / blocked>

### Execution handoff
<For a delivery-managed run: report the planner-selected implementation profile and confirm that `delivery stage EXECUTION_READY` automatically launched the dedicated implementation agent, then stop the planning agent. For planning-only use: state that the plan is ready and no implementation was started.>
```

If the plan is blocked, replace the execution handoff with a pointer to the unresolved `Decision Required` block(s) in the canonical Doct plan and ask the user to select an option or comment there. Do not restate an abbreviated option list in chat, and do not suggest a Markdown-only execution command unless the repo explicitly supports converting the reviewed HTML plan back to Markdown.
