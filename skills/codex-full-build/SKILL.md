---
name: codex-full-build
description: Run the full Codex development lifecycle from a Linear issue, existing plan, or plan description through clarification, execution-ready plan creation, active-harness reviewer-subagent plan review, scoped implementation, bounded implementation review, verification, push, and ready-for-review PR creation. Use this whenever the user wants an autonomous end-to-end build from issue or plan input without babysitting.
---

# Codex Full Build

Use this skill when the user wants an end-to-end software change driven from a Linear issue, an existing plan, or a natural-language plan description. This skill is the lifecycle controller. It prepares and validates the plan, gets independent plan review from the active harness's configured reviewer subagent, then delegates implementation, scoped review, verification, commit, push, and PR creation to `$run-plan`.

The goal is autonomous execution with explicit gates. Ask the user only when product intent or scope is genuinely unclear enough that a correct execution-ready plan cannot be written.

## Inputs

Accept any of:

- Linear issue key or URL, such as `HUD-123`.
- Existing plan path or slug resolvable by repo-local active plan guidance.
- Natural-language plan description.

If the input is a Linear issue, fetch it with `ltui`. Do not use a browser or another Linear client as the primary source.

## Required Skills and Tools

Load and follow these skills as needed:

- `linear` for Linear issue fetching with `ltui`.
- `planning-workflow` for plan creation and readiness.
- Repo-recommended planning skills from `AGENTS.md`, usually `product-principles` and `tdd-test-writer` for this repo.
- `reviewed-html-plan` or the active-harness `reviewer` subagent for the single plan review.
- `run-plan` for execution, implementation review, verification, commit, push, and PR.

If a required reviewer or `ltui` is unavailable, try the documented remediation in the relevant skill first. Stop only when the required dependency cannot be restored safely.

## Non-Negotiable Rules

- Stay within repo guidance. In this repo, `AGENTS.md` is authoritative.
- Use `ltui` for Linear issue retrieval. If a Linear issue cannot be fetched after auth/profile/identifier remediation, stop and report the fetch blocker.
- Do not start implementation until the plan is execution-ready and the configured reviewer subagent returns a passing readiness verdict.
- Do not create a draft PR unless the user explicitly asked for a draft.
- Do not let reviewers edit files. The reviewer subagent is read-only.
- Do not silently choose product behavior when the input is too vague and repo evidence does not resolve it.
- Do not expand scope because a reviewer found adjacent work.
- Delegate implementation to `$run-plan`; do not duplicate its phase execution and PR workflow in this skill.

## Lifecycle

### 1. Intake and Source Resolution

Classify the input:

- `LINEAR_ISSUE`: issue key or Linear URL.
- `EXISTING_PLAN`: path or slug that resolves to a plan file.
- `PLAN_DESCRIPTION`: natural-language description.

For `LINEAR_ISSUE`:

1. Run `ltui auth list` if Linear auth has not been checked in this session.
2. Fetch the issue with detail context:
   ```bash
   ltui issues view <ISSUE_KEY> --include-comments --include-history --format detail
   ```
3. If the output starts with `ERROR:`, remediate based on the error:
   - `auth_missing`: ask for the Linear API key or configured profile, then retry through `ltui`.
   - `auth_invalid`: ask for a valid profile/key, then retry through `ltui`.
   - `not_found`: verify the issue key from the user input and, if useful, search with `ltui issues list --search`.
   - `network_error` or `api_error`: retry once, then report the blocker.
4. If attachments are present and the issue says images/screenshots are relevant, fetch them with the `IMAGE_ATTACHMENTS_*` command emitted by `ltui`.

For `EXISTING_PLAN`:

1. Resolve slugs using repo-local active plan guidance; do not infer a markdown path.
2. Read the plan fully.
3. If it is already execution-ready, still run the reviewer-subagent plan-review gate unless the plan records a passing equivalent review.
4. If it is not execution-ready, update it under the repo planning rules before review.

For `PLAN_DESCRIPTION`:

1. Read repo guidance and relevant product intent before deciding whether the description is sufficient.
2. Gather focused repo evidence needed to write a concrete plan.
3. Ask clarification questions only for unresolved product/scope decisions.

### 2. Clarification Gate

Use repo evidence first. Ask the user only when an answer changes intended behavior, scope, compatibility, data handling, security/privacy posture, or user-visible workflow.

When questions are needed:

- Ask the minimum blocking questions.
- Batch at most three concise questions.
- Use Codex's question UI when available; otherwise ask directly in chat.
- Do not ask about details that can be discovered from the repo, Linear issue, or existing plan.

Proceed once the answers are enough to write a plan with concrete acceptance criteria and verification.

### 3. Plan Creation or Update

Write or update one plan artifact following repo guidance. In this repo, default to:

```text
<plan_path>
```

Use `planning-workflow` and the repo's `AGENTS.md` required structure. For this repo, a non-trivial execution-ready plan must include:

- `Status` set to `execution-ready` only when ready.
- Goal and user-visible outcome.
- Authority and inputs, including Linear issue key or source prompt.
- Current implementation reality with evidence.
- Product intent alignment.
- Locked decisions.
- Acceptance criteria.
- BDD scenarios for happy, edge, and failure paths.
- Test coverage matrix when non-trivial.
- Phase-by-phase execution plan with `### End State`, `### Tests first`, `### Work`, `### Expected files`, and `### Verify`.
- Verification strategy with exact commands.
- Non-goals.
- Progress with stable phase IDs.
- Resume instructions for the next agent.
- Decisions / Deviations log.
- If any plan representation is rendered or delivered as HTML, it must use the standard reviewer layout: a dark-mode visual theme with explicit dark background, light foreground text, readable muted text, accessible link/accent colors, `color-scheme: dark`, and a full-width single-column page. Put a concise table of contents near the top of the document, immediately after the title/status summary and before the main plan sections. Format the ToC as a horizontal section with responsive columns so the rest of the plan keeps full width. Do not use a permanent left sidebar/rail for navigation.

If the issue or description is too broad, make the plan scope precise instead of absorbing adjacent cleanup. If important decisions remain unresolved, keep the plan in `research-ready` or `discovery` and ask/perform the next research action rather than starting review.

### 4. Plan Review

Run one read-only review through the current harness's configured `reviewer` subagent. It is GPT-5.6 Terra at medium reasoning in Pi and OpenCode, and Sonnet 5 at high effort in Claude Code. Provide a bounded packet containing:

- plan path,
- source input summary,
- repo guidance paths,
- product intent path when present,
- known non-goals,
- readiness rubric, and
- an instruction not to propose execution or adjacent implementation work.

Do not launch separate Codex or Claude Code reviewer processes or use Herdr as a required transport.

#### Plan Review Verdicts

Ask reviewers to return one of:

```text
VERDICT: PLAN_EXECUTION_READY
VERDICT: PLAN_NEEDS_REVISION
VERDICT: BLOCKED_BY_PRODUCT_QUESTION
```

Reviewer output is sometimes fuzzy. Normalize by substance:

- Treat as `PLAN_EXECUTION_READY` only when the reviewer clearly says the plan is actionable/executable and has no blocking readiness issues.
- Treat as `PLAN_NEEDS_REVISION` when the reviewer identifies missing acceptance criteria, vague scope, missing verification, missing parity expectations, unresolved decisions, or material plan defects.
- Treat as `BLOCKED_BY_PRODUCT_QUESTION` when the reviewer identifies a decision that cannot be resolved from repo evidence or source input.
- If the output is ambiguous, rerun the reviewer subagent once with a tighter prompt asking for only verdict plus blocking findings.

### 5. Integrate Plan Feedback

Triage every finding before editing the plan:

```text
Finding | Source | Classification | Decision | Evidence
```

Use these classifications:

- `READINESS_BLOCKER`: must be fixed before execution.
- `PRODUCT_QUESTION`: must be answered by the user before execution.
- `OPTIONAL_CLARITY`: helpful but not required for execution readiness.
- `OUT_OF_SCOPE_FOLLOW_UP`: real but outside this plan, not required for truthful verification, and not introduced by this work.
- `DISAGREE_REPO_EVIDENCE`: reviewer claim contradicted by repo/source evidence.

Fix `READINESS_BLOCKER` findings in the plan. Ask the user for `PRODUCT_QUESTION`. Record `OUT_OF_SCOPE_FOLLOW_UP` only with evidence and a tracking destination; do not use it for plan-required work, BDD gaps, verification gaps, or acceptance-criteria gaps.

After plan edits, rerun the reviewer subagent under the normal bounded review-cycle policy until it returns an execution-ready verdict or the workflow reaches a documented stop condition.

Stop and report a plan convergence blocker if:

- the same readiness finding recurs after two revision attempts,
- reviewers disagree and repo evidence does not resolve it,
- the plan would require a product decision the user has not answered,
- the bounded plan-review cycle budget does not converge.

### 6. Execute with Run Plan

Once the reviewer subagent returns an execution-ready verdict, invoke `$run-plan` with the finalized plan path.

The handoff must state:

- plan path,
- source input or Linear issue,
- reviewer-subagent plan-review verdict,
- any documented out-of-scope plan review notes with evidence and tracking destination,
- instruction to proceed through scoped implementation, bounded reviewer-subagent implementation review, verification, commit, push, and ready-for-review PR.

Do not reimplement the scoped runner's workflow here. `$run-plan` owns:

- scope extraction,
- phase-by-phase implementation,
- implementation review with the configured reviewer subagent,
- in-scope fix loops,
- final verification,
- commit,
- push,
- ready-for-review PR creation.

If `$run-plan` stops with a blocker, handle only blockers that are part of this lifecycle:

- If the blocker is plan ambiguity, return to plan clarification/review.
- If the blocker is reviewer/tool unavailability, remediate using the relevant skill.
- If the blocker is implementation scope expansion, ask the user before expanding scope.
- If the blocker is a failing verification outside this plan, report it as residual/pre-existing unless the scoped runner classifies it as a regression from this diff.

### 7. Final Response

Return a concise handoff with:

- PR URL.
- Plan path.
- Source input or Linear issue.
- Reviewer-subagent plan-review verdict.
- Reviewer-subagent implementation-review verdict from `$run-plan`.
- Verification commands and results.
- Changed files at a high level.
- Documented out-of-scope follow-ups with evidence and tracking destination.
- Residual risk.

If no PR was created, say exactly which gate stopped the lifecycle and what is needed next.

## Plan Review Prompt Template

Use this shape for the active-harness reviewer-subagent plan review:

```text
Read-only plan review. Do not edit files.

Plan: <plan path>
Source input: <Linear issue key/path/description summary>
Repo guidance: AGENTS.md and any plan-local guidance
Product intent: <path or "none found">

Review whether this plan is execution-ready for the stated source input.
Do not propose adjacent features, broad cleanup, or implementation work beyond the source scope.

Check:
- goal and user-visible outcome are clear
- scope and non-goals are enforceable
- acceptance criteria are concrete
- BDD scenarios cover happy, edge, and failure paths
- phase work is ordered and bounded
- tests-first expectations are practical
- each phase has exact verification commands
- required web/native/API/CLI parity is explicit when relevant
- unresolved product decisions are not hidden in execution
- final verification is sufficient for touched surfaces

Return one verdict, or a clear equivalent:
- VERDICT: PLAN_EXECUTION_READY
- VERDICT: PLAN_NEEDS_REVISION
- VERDICT: BLOCKED_BY_PRODUCT_QUESTION

For each blocking finding include:
- finding
- evidence from the plan or repo
- why it blocks execution readiness
- the smallest plan change or question needed
```

## Run Plan Handoff Template

```text
Use $run-plan to execute <plan path>.

Source input: <Linear issue key/path/description summary>
Plan review status:
- Reviewer subagent: <normalized verdict and brief evidence>

The reviewer subagent found the plan execution-ready.

Proceed through the run-plan workflow:
- preserve the plan as the scope contract
- implement phase by phase
- run bounded reviewer-subagent implementation reviews
- fix only in-scope findings
- run final verification
- commit, push, and open a ready-for-review PR
```
