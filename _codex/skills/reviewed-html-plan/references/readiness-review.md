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

Default behavior is corrective: reshape the HTML plan directly when the right direction is inferable from repo evidence. When a product-shaping decision remains low-confidence, keep the plan blocked and surface the decision prominently in the HTML plan for Doct feedback, with all viable options, thorough explanations, and the agent's recommendation. An independent Oracle consultation may challenge a low-confidence technical recommendation before it is presented, but Oracle does not count as PM or product-owner approval.

After material PM edits, ensure the review URL still points at the latest plan and the plan remains browser-reviewable.

### 6. Independent Sol-medium planner review

An earlier Oracle consultation does not satisfy, skip, or modify this gate. Oracle answers a bounded decision question; the `planner` independently evaluates the whole current plan for execution readiness without selecting the implementation runtime.

After the explicit execution-ready request and PM pass, request one bounded read-only native Codex planner. Use the runtime contract for model selection and dispatch. The planner returns an independent readiness verdict over the exact plan and does not select or launch an implementation runtime.

- For data loss, auth/security, concurrency/locking, migrations/persistence, release-blocking CI behavior, release-risk, or another P1/P2 risk surface, give the reviewer a compact readiness packet with named files/surfaces, the exact risk question, relevant plan excerpts, verification expectations, and outcome limits.
- For lower-risk plans, retain the same bounded readiness packet without broadening into a second opinion.
- For small, low-stakes plan changes (clarity edits, typo fixes, minor scope restatements), run one planner pass. If the verdict is `PLAN_EXECUTION_READY` with only `OPTIONAL_CLARITY` or `DISAGREE_REPO_EVIDENCE` observations, mark the plan execution-ready. Rerun only once if a material edit is required, and stop if the same finding recurs.

Request the planner through the native collaboration tool. Include TARGET_CHECKOUT, HEAD/status, changed and untracked plan paths, requirements, and verification evidence. The driver writes the returned review to thoughts/validation/<slug>-plan-review.md. Read the target directly even if launch CWD differs. Missing evidence limits the verdict; it does not justify refusing visible artifacts. Allow at most one narrowed retry for invalid or incomplete review output. Do not invoke an external client or manufacture a named-agent parameter unsupported by the tool.

The coordinating agent may integrate plan edits, but after material edits it must rerun the independent planner review (the configured Codex planner) before marking the plan execution-ready. If the configured planner is unavailable, leave the plan blocked on review infrastructure.

Record the verdict, actual reviewer model, reasoning effort, plan fingerprint, and evidence limitations in the scoped review artifact. Any material plan edit invalidates the prior readiness verdict. Preserve the selected driving model.

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
- whether verification exercises the important correctness risks and exposes remaining uncertainty,
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
```

Record the actual reviewer model and evidence with a ready verdict. Implementation model selection remains with the user.

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

Require each planner pass to return the complete bounded blocker set it found, not one representative blocker.

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
- an active phase is missing `End State`, `Verification`, `Expected files`, `Work`, `Open questions / decision dependencies`, or `Verify`,
- UI impact is missing, `unknown`, or lacks required design evidence for real UI-impacting work,
- verification commands are stale or not copy/paste ready,
- the independent Sol-medium planner did not agree by substance that the plan is ready,
- PM review left unresolved product-intent or user-impact gaps,
- PM and Sol-medium planner readiness review began without an explicit execution-ready request (unless the operator directly requested that review).

Do not implement product code while the workflow is still in its planning-only authority. Publish the execution-ready plan and stop. If the user already authorized execution after readiness, return to the native Codex implementation workflow in this driving session. Do not advance an external delivery ledger or launch another runtime.

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
<State whether the task stops at the reviewed plan or already authorizes native Codex execution.>
```

If the plan is blocked, replace the execution handoff with a pointer to the unresolved `Decision Required` block(s) in the canonical Doct plan and ask the user to select an option or comment there. Do not restate an abbreviated option list in chat, and do not suggest a Markdown-only execution command unless the repo explicitly supports converting the reviewed HTML plan back to Markdown.
