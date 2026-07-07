---
name: reviewed-html-plan
description: Create and gate execution-ready HTML development plans through Doct plan registration via `doct-agent plans` on `https://doct.nodaste.com`, PM product-intent review, and read-only GPT plus GLM Pi subagent plan reviews. Use this whenever the user asks for the plan review process, a reviewed HTML plan, a pre-execution plan gate, or wants a plan created from a description and registered in Doct for browser feedback before implementation.
---

# Reviewed HTML Plan Workflow

Use this skill when the user wants the planning and review process completed before implementation starts. The output is a single reviewed HTML plan that is registered in Doct through `doct-agent plans` on `https://doct.nodaste.com` and either marked execution-ready or explicitly blocked on a product/scope decision.

This workflow stops before product-code execution. It may edit the plan artifact, but it must not change product code, tests, app config, generated files, or environment files.

## Required companion skills

Load and follow these skills when this workflow reaches their surface:

- `planning-workflow` for the plan-writing contract and execution-readiness bar.
- `doct-document-ops` for HTML/Markdoc plan structure, dark-mode requirements, Doct registration, canonical Doct URLs, mandatory post-registration listener startup, plan updates, comment/action queue handling, claim/ack/resolve behavior, Markdown/text fallback publishing, and source sync/watch behavior.
- `product-principles` for workflow, defaults, recovery, status, error handling, product-intent, and early-stage scope review.
- Pi `quality-reviewer` for the read-only GPT plan-review pass.
- Pi `glm5.2-high` for normal high-risk read-only GLM plan review, `glm5.2-xhigh` for final or exceptional-risk review, and `quality-reviewer-glm` only as the legacy xhigh compatibility alias.
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

Ask at most one short batch of blocking questions only when repo evidence cannot resolve a decision that changes user-visible behavior, security/privacy posture, data handling, scope, or compatibility.

### 2. Create or refresh the HTML plan

Write or update `thoughts/plans/<slug>.html` as semantic HTML, not Markdown renamed as HTML.

The plan should follow the `planning-workflow` execution artifact contract while using reviewer-friendly HTML structure:

- standard reviewer layout: dark-mode theme with explicit dark background, light foreground, readable muted text, accessible link/accent colors, `color-scheme: dark`, and a full-width single-column page; place a concise table of contents near the top of the document immediately after the title/status summary, and format it as a horizontal section with responsive columns so the rest of the plan keeps full width; do not use a permanent left sidebar/rail,
- stable `id` attributes on major sections, phase wrappers, acceptance criteria, BDD scenarios, diagrams, figures, and likely comment targets,
- a near-top `Decision Attention / Low-confidence Areas` section for blockers, required user input, unresolved decisions, and weak evidence,
- a `Progress` section containing the only checkboxes,
- canonical content: status, goal, Decision Attention / Low-confidence Areas, why this exists, authority and inputs, current implementation reality, product intent alignment, locked decisions, acceptance criteria, BDD scenarios, phase-by-phase execution plan, verification strategy, delivery order, non-goals, resume instructions, and decisions/deviations log,
- one-to-one mapping between progress checkboxes and detailed phases,
- each phase includes `End State`, `Tests first`, `Expected files`, `Work`, `Open questions / decision dependencies`, and `Verify`,
- explicit UI-impact triage with repo-appropriate design evidence for real UI-impacting work,
- exact verification commands grounded in repo reality,
- no unresolved open questions when the status is `execution-ready`.

If a prior reviewed plan exists, preserve truthful completed progress, stable IDs where possible, and append-only decisions/deviations history.

### 3. Register the plan for browser review

Use `doct-document-ops` as the sole source for current Doct registration commands and service behavior.

1. Confirm `doct-agent` auth/context for `https://doct.nodaste.com` as documented by `doct-document-ops`.
2. Register the plan through `doct-agent plans register --base-url https://doct.nodaste.com --source-format html`, using `--allow-untemplated` for the handcrafted HTML plans this workflow normally produces.
3. Parse the registration JSON and preserve the returned Doct document/plan id, workspace id, canonical URL, current version, `sourceGuidance`, and full `listenerInstructions`.
4. Follow the returned `listenerInstructions` immediately: set lifecycle active, leave the plan in its registration/default board column (normally `backlog`), drain pending comments/actions with `agent next --no-wait` until empty, then start the durable listener with the harness background-process tool. Use `listenerInstructions.listenerCommand` (`doct-agent plans listen ... --jsonl`); do not use `agent next --wait` as the default listener. Do not move the plan to `in_progress` during browser-review setup; implementation execution workflows own that transition.
5. Share the canonical Doct review URL only after the listener is running, or report a concrete listener-start blocker. Never show a loopback, local `plan-review`, Tailscale local-service URL, or relative path to the user unless they explicitly requested a legacy local reviewer.
6. Use listener-delivered events for browser comments/actions. Use `doct-agent plans queue list` and `doct-agent plans agent next --no-wait` for startup drain, recovery, or manual processing only.

If browser feedback has not yet been provided, stop after sharing the Doct URL with the listener running and tell the user to annotate the plan and then say feedback is ready. Do not proceed to GPT/GLM or PM gates until the user says feedback is ready, unless the user explicitly says to skip human browser feedback.

### 4. Process browser feedback

When feedback is ready, process reviewer comments/actions through the Doct plan queue.

For each listener-delivered or pending comment:

1. Use the thread id, claim id, workspace id, document id, selected context, and returned ack/resolve/release commands from the listener payload or `doct-agent plans agent next`. If no claim is available during manual recovery, inspect `doct-agent plans queue list` until it reports no pending work.
2. Read the full plan before editing.
3. Use the annotation context, heading path, quoted text, and reviewer note.
4. Classify the comment as `READINESS_BLOCKER`, `PRODUCT_QUESTION`, `OPTIONAL_CLARITY`, `OUT_OF_SCOPE_FOLLOW_UP`, or `DISAGREE_REPO_EVIDENCE`.
5. Edit the plan for readiness blockers and useful clarity that preserves scope.
6. Ask the user for product questions that cannot be resolved from repo evidence.
7. Ack and resolve only after the plan actually addresses the comment.
8. Keep or restart the durable listener after each dispatch if more browser feedback is expected; do not leave review handoff dependent on a one-time queue check.

Keep the local HTML plan authoritative for implementation and Doct authoritative for review state. After editing the local file, push updates with `doct-agent plans update` or keep `doct-agent plans watch` running during active review. `plans watch` is source sync only; it does not replace the comment listener.

### 5. PM product-intent review

Run an adversarial PM review before independent AI plan review.

The PM pass evaluates whether the plan will satisfy the intended user/operator outcome, not merely whether the phases are internally coherent. Use `product-principles` and repo product intent to check:

- the real user impact and intended job-to-be-done,
- golden-path usability,
- safe defaults and inferred inputs,
- routine self-healing versus fail-closed boundaries,
- truthful status, docs, help text, and agent-legible errors,
- early-stage stage fit and the smallest complete slice,
- whether verification proves the shipped workflow, not just helper behavior.

Default behavior is corrective: reshape the HTML plan directly when the right direction is inferable from repo evidence. Stop for a focused question only when a product-shaping decision remains low-confidence.

After material PM edits, ensure the review URL still points at the latest plan and the plan remains browser-reviewable.

### 6. Read-only GPT and applicable GLM Pi subagent plan reviews

Run the GPT reviewer before execution, and keep all reviewers read-only. Before launching GLM, classify the plan scope:

- **Use GLM** when the plan touches data loss risk, auth/security, concurrency/locking, migrations/persistence, release-blocking CI behavior, release-risk, or another explicit P1/P2 risk surface.
- **Skip GLM by default** for docs-only plans, low-risk UI copy, low-risk tests, and narrow follow-ups unless the operator or Doct reviewer provides an explicit override reason.
- When GLM applies, give it a compact readiness packet with named files/surfaces, the exact risk question, relevant plan excerpts, verification expectations, and outcome limits.

In Codex, delegate this reviewer leg to Pi from the same repo/worktree instead of substituting Codex-native reviewers. Invoke Pi with an explicit bounded prompt asking it to run `quality-reviewer` and, when GLM applies, the applicable GLM reviewer profile read-only against the current HTML plan, return the required verdicts, and write reviewer artifacts under `thoughts/validation/`:

```bash
pi -p --approve "Run the reviewed-html-plan reviewer gate for <plan-path>. Read-only review only: use Pi subagent quality-reviewer, and use the applicable GLM reviewer profile only when the plan has a high-risk trigger or explicit override: glm5.2-high for normal high-risk bounded plan review, or glm5.2-xhigh for final/exceptional-risk plan review. If GLM is skipped, record the low-risk classification and override decision. Require PLAN_EXECUTION_READY / PLAN_NEEDS_REVISION / BLOCKED_BY_PRODUCT_QUESTION / REVIEW_INCOMPLETE_RERUN_NEEDED verdicts, and write artifacts under thoughts/validation/. Do not edit product code."
```

Codex may integrate plan edits, but after material edits it must rerun the same applicable reviewer set before marking the plan execution-ready. If Pi, `quality-reviewer`, or a required GLM subagent is unavailable, leave the plan blocked on review infrastructure.

#### GPT

Use the Pi `quality-reviewer` subagent for the GPT review leg. The review input should include:

- plan path and review URL,
- source request or issue summary,
- repo guidance paths,
- product-intent path when present,
- readiness rubric,
- known non-goals,
- instruction to avoid adjacent implementation expansion,
- instruction not to edit files.

#### GLM

Use the active Pi GLM reviewer profile only when the plan has a high-risk trigger or explicit override. Use `glm5.2-high` for normal high-risk bounded plan review. Use `glm5.2-xhigh` for final or exceptional-risk plan review, including security boundary changes, irreversible data-loss risk, difficult concurrency/locking correctness, migrations, release-blocking ambiguity, or any `glm5.2-high` incomplete/ambiguous result. Give GLM a bounded readiness prompt, not open-ended repo exploration. Do not ask GLM to edit files.

For both plan review legs, stay limited to readiness concerns, including at least:

- whether the plan has executable phases,
- whether acceptance criteria and verification are testable,
- whether scope and non-goals prevent expansion,
- whether unresolved product questions remain,
- whether the plan has enough file/surface specificity for implementation,
- whether architecture/dependency risks are resolved enough to execute,
- whether recovery/operator/error behavior is specified when relevant.

For every quality reviewer, use bounded scope rather than parent-side turn caps. Do not cap tool calls or lower `max_turns` to force completion; hard caps can truncate the final verdict and produce unusable output. Give each reviewer a concrete readiness packet and require a final verdict. If any reviewer cannot complete the assigned readiness scope, it must return a non-ready result with completed checks, remaining checks, and the exact follow-up slice the parent should run next. If the caller explicitly supports `REVIEW_INCOMPLETE_RERUN_NEEDED`, use that verdict; otherwise map incomplete coverage to `VERDICT: PLAN_NEEDS_REVISION` with the same completed-checks, remaining-checks, and follow-up-slice fields.

Empty output, tool-only output, provider errors, or transcripts ending in tool use do not count as independent readiness review. Rerun once with a narrower bounded readiness prompt; do not fix empty reviewer output by adding or lowering parent-side turn limits. If the narrowed rerun is still unusable, stop with a tooling blocker and leave the plan not execution-ready.

Split a readiness review into focused passes when a plan spans three or more product surfaces, or when the readiness scope is otherwise too broad for one concrete readiness packet. Use focused passes such as product intent and scope boundaries, BDD/verification adequacy, architecture/dependency risks, and recovery/operator/error behavior. The parent must synthesize all slice verdicts and cannot mark the plan execution-ready until every required slice is complete or explicitly blocked.

Ask each applicable reviewer for one of these verdicts:

```text
VERDICT: PLAN_EXECUTION_READY
VERDICT: PLAN_NEEDS_REVISION
VERDICT: BLOCKED_BY_PRODUCT_QUESTION
VERDICT: REVIEW_INCOMPLETE_RERUN_NEEDED
```

Normalize fuzzy reviewer output by substance, but never normalize empty, tool-only, provider-error, or incomplete-coverage output into a ready verdict. Treat a review as ready only when it finds no blocking readiness gaps and all required slices are complete.

### 7. Integrate and iterate to execution-ready

For every GPT/GLM finding, triage before editing:

```text
Finding | Source | Classification | Decision | Evidence
```

Use these classifications:

- `READINESS_BLOCKER`: fix before execution.
- `PRODUCT_QUESTION`: ask the user before execution.
- `OPTIONAL_CLARITY`: integrate only when it improves execution confidence without widening scope.
- `OUT_OF_SCOPE_FOLLOW_UP`: do not add to this plan only when it is outside the plan, not required for truthful verification, and not an acceptance-criteria/BDD gap; record it with evidence and a tracking destination if useful.
- `DISAGREE_REPO_EVIDENCE`: do not change the plan; record the evidence if the disagreement matters.

After fixing readiness blockers, rerun GPT and the applicable GLM plan review when GLM applies. If any reviewer returns incomplete coverage, launch the recommended follow-up slice, record completed checks, remaining checks, rerun slices, and final synthesized readiness status, then continue until all required slices are complete or explicitly blocked. Repeat until all applicable reviewers agree by substance that the plan is execution-ready. When they do, update the same Doct-registered HTML plan and status/board metadata using the current `doct-document-ops` Doct flow.

#### Independent sign-off gate (do not self-certify)

The closing ready verdict that marks a plan `execution-ready` must come from an **independent reviewer** — any reviewer other than the plan author/self. For this workflow, `PLAN_EXECUTION_READY` is the expected ready verdict; an equivalent approved `PASS_NO_ISSUES` verdict from another independent plan reviewer may also clear the gate by substance. The plan author may *integrate* review findings but may **never self-certify** execution readiness:

- A `plan-author` / `plan-owner` / `pi` / `self` review verdict does not clear the gate, even if it is the latest review.
- If any independent review returns `BLOCKED`, `PLAN_NEEDS_REVISION`, or raises in-scope findings, run a **fresh independent review after integrating** the fixes. The integration edit itself does not clear the gate; only a new independent ready verdict does.
- The independent ready verdict must not be followed by any later non-pass review, and should post-date the last material plan edit. If you edit the plan after the independent pass, re-review.
- Record reviews truthfully in the `review-record` section with the real reviewer identity. Do not relabel a self-review as `codex`/`claude-code` to satisfy the gate — actually run the independent tool.

This workflow enforces the gate through the reviewer loop and truthful Doct plan state/metadata. Do not claim a local mechanical validator exists unless the target repo actually provides one; in repos without such a validator, the PM/GPT/GLM gates and Doct review state are the enforcement surface.

Stop and report a convergence blocker if:

- the same readiness finding recurs after two revision attempts,
- reviewers disagree and repo evidence does not resolve the disagreement,
- a product question remains unanswered,
- three full review cycles do not converge.

If AI reviews materially reshape product intent, run one final PM check before declaring the plan execution-ready.

### 8. Final readiness gate

Before final output, inspect the HTML plan for obvious handoff blockers:

- unresolved browser-review comments remain in the queue, or the required listener was never started after registration,
- the Doct registered plan has not been updated after successful GPT and applicable GLM plan reviews, or its lifecycle/board/readiness state is stale,
- unresolved inline review markers or unresolved question sections remain,
- status is not `execution-ready`,
- near-top Decision Attention is missing or hides unresolved decisions,
- `Progress` or resume instructions are missing,
- progress checkboxes and detailed phases do not map one-to-one,
- an active phase is missing `End State`, `Tests first`, `Expected files`, `Work`, `Open questions / decision dependencies`, or `Verify`,
- UI impact is missing, `unknown`, or lacks required design evidence for real UI-impacting work,
- verification commands are stale or not copy/paste ready,
- GPT or GLM did not agree by substance that the plan is ready,
- PM review left unresolved product-intent or user-impact gaps.

Do not start implementation as part of this skill.

## Final output

Use this structure:

```markdown
## Reviewed HTML Plan Ready

Plan: thoughts/plans/<slug>.html
Review URL: <canonical Doct URL>

### Gates completed
- Browser feedback: <processed / skipped by request / blocked>
- PM review: <ready / reshaped plan / blocked>
- GPT review: <verdict>
- GLM review: <verdict>

### Changes made during review
- ...

### Final status
<execution-ready / blocked>

### Execution handoff
<Only when execution-ready: name the repo's preferred execution command for this explicit HTML plan path from repo-local guidance.>
```

If the plan is blocked, replace the execution handoff with the single blocking question or blocker summary needed to continue. Do not suggest a Markdown-only execution command unless the repo explicitly supports converting the reviewed HTML plan back to Markdown.
