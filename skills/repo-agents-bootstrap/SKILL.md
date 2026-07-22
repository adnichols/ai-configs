---
name: repo-agents-bootstrap
description: Bootstrap or refactor repository AGENTS guidance so repo-specific rules are local while shared planning doctrine stays centralized in the planning workflow skill. Use when creating/updating `AGENTS.md`, optionally adding repo-local planning overrides, codifying plan-mode versus `dev:plan` boundaries, or aligning repos to the shared TDD/BDD planning and execution model.
---

# Repo Agents Bootstrap

## Overview

Create one required repo guidance layer and one optional override layer:

1. Root `AGENTS.md` for repository-specific commands, safety rails, and quality gates.
2. Optional planning overrides file (usually `thoughts/plans/AGENTS.md`) only when the repo needs planning rules beyond the shared `planning-workflow` skill.

The shared planning doctrine now lives in the `planning-workflow` skill. This bootstrap skill makes each repo point to that shared doctrine while recording repo-specific reality: real commands, real quality gates, required docs, domain skill hints, and any explicit local deviations.

## Modes

Pick one mode before editing files:

- `audit_only`: analyze repo alignment and propose deltas without modifying repo files.
- `bootstrap_new`: create root `AGENTS.md` and any required supporting planning docs for repos with little/no prior guidance.
- `migrate_existing` (recommended default): preserve strong existing guidance, patch only misalignments, and avoid broad rewrites.

For mature repos (like doct/ccore), start in `audit_only` and present a delta plan first.

## Operating Model To Codify

Capture these behaviors as defaults:

- Shared planning doctrine lives in the `planning-workflow` skill, not duplicated into every repo.
- `plan mode` is discovery-only and read-only.
- `dev:plan` is the plan-materialization step: it may write the plan artifact, but must not change code or other repo files.
- `dev:plan` must fail closed on `low-confidence` foundational decisions: it only hands off an `execution-ready` plan when those decisions are resolved, and otherwise asks the user or writes exactly one non-ready `research-ready` plan artifact with the exact next research action.
- Root `AGENTS.md` tells agents to use the shared planning skill and names any repo-specific planning inputs or overrides.
- Plan-first execution with phase checkpoints under the repo's canonical execution workflow.
- In Pi-style reviewed-plan repos, the handoff stays explicit: `/review:plan` -> `/review:change-integrate` -> optional `/review:plan-adversarial` -> `/cmd:execute-plan` -> execution. Alternate reviewers such as `/review:change-claude-code` remain explicit opt-ins, not hidden fallbacks.
- Phase advancement requires no unresolved concrete in-scope blocker: unmet acceptance criteria, incomplete wiring, regressions, credible current-path security/data-loss/correctness risks, or misleading verification. Speculative future scale, ideal architecture, unrelated pre-existing defects, optional polish, and unsupported hypothetical paths do not block the phase and must not expand its scope.
- Default to one implementation review plus one targeted rereview after fixes. A third round is allowed only when the prior fix introduced or exposed a new concrete blocker; after three total rounds, stop with a convergence blocker.
- Complete the promised slice before advancement: no required stubs, TODO behavior, dead-end surfaces, missing producer/consumer wiring, fake success, or verification that bypasses the real implementation. Resize an outcome before implementation if it cannot be delivered as an independently useful complete slice.
- Resumability: `Progress` with stable IDs, explicit `Resume Instructions`, and append-only decision/deviation logs.
- Evidence-first validation: lint, unit, build, e2e (and contract tests if applicable) before claiming done.
- Reviews are scoped reliability gates, not open-ended product audits. Reviewer findings must be triaged against the accepted current slice before any fix is made.
- Execution feedback loops must reassess the original test scope and plan when substantive misses appear. Repeated or cross-surface misses trigger a scope/product decision or resize instead of automatic scope expansion.
- Commit and push discipline with rationale, not just code diffs.
- Test-first posture: define behavior before implementation wherever practical.
- Keep planning depth `complexity-aware`: simple tasks stay lightweight, while non-trivial ready plans need complete contracts plus a `test coverage matrix` strong enough to catch partial implementations.
- Product-intent anchored planning: every active plan must trace back to `thoughts/specs/product_intent.md`.
- Validate `### Verify` commands against real repo/package/target names before execution.
- Make multi-surface parity expectations explicit when phases span HTTP/CLI/MCP/UI or similar interfaces.
- Update stale fixtures/tests when locked contracts, payloads, schemas, or evidence sources change.
- Repo-local planning overrides stay additive: they can tighten the shared defaults, but they must not replace or relax the central doctrine.

## TDD + BDD Rules

For every phase in a plan:

1. Define acceptance criteria in user outcomes, not implementation terms.
2. Add BDD scenarios (`Given/When/Then`) for happy path, edge path, and failure path.
3. Add counterexample/ambiguity, boundary/scale, and cross-surface parity scenarios whenever the phase can fail in those ways.
4. Write failing tests first (RED) where practical.
5. Implement the smallest real slice to pass tests (GREEN).
6. Refactor safely while preserving behavioral coverage (REFACTOR).

If strict TDD is skipped, require an explicit reason in the phase and add compensating checks.

Use the `tdd-test-writer` skill when available to harden the RED-phase contract.

## Boundary Model To Codify

Bootstrap repos around these responsibilities:

- Shared planning doctrine -> `planning-workflow` skill
- Repo-specific execution truth -> root `AGENTS.md`
- Optional repo-local planning deviations -> `thoughts/plans/AGENTS.md`
- Read-only research/discovery -> `plan mode`
- Plan materialization -> `dev:plan`
- Explicit reviewed-plan handoff -> `/review:plan` -> `/review:change-integrate` -> optional `/review:plan-adversarial` -> `/cmd:execute-plan`
- Quality-gated execution -> repo-specific execution workflow

Do not make a repo-local planning overrides file the default source of truth when root `AGENTS.md` plus the shared planning skill are sufficient.

## Bootstrap Workflow

### 1) Gather repository truth

- Read existing `AGENTS.md`, `.cursor/rules/*`, package/tool configs, and test scripts.
- Build an authoritative command list for:
  - install/dev/build,
  - lint/format,
  - unit tests (including single-test invocations),
  - e2e/contract tests,
  - full quality gate command.
- Detect repo surfaces and likely skill-routing hints (frontend, React/Next, Rust, browser automation, MCP, etc.).

Also detect whether a repo-local planning overrides file already exists (for example `thoughts/plans/AGENTS.md`).
Also detect whether `thoughts/specs/product_intent.md` exists.

If `product_intent.md` is missing:

- mark it as a `critical` alignment gap,
- create it from `references/product_intent_template.md`,
- block bootstrap completion until the file exists.

### 2) Gather historical delivery patterns (optional but recommended)

When prior OpenCode sessions exist, review patterns with `opencode db`:

```bash
opencode db "select id, directory, title, time_created, summary_files, summary_additions, summary_deletions from session where directory = '/path/to/repo' or directory like '/path/to/repo/%' order by time_created desc limit 40;" --format tsv
```

Look for repeated titles like:

- `Implement phase ...`
- `Review phase ...` / `Re-review ...`
- `Run Plan (Quality-Gated Loop)`
- `AGENTS.md review ...`

Use those patterns to tune gate strictness, validation expectations, and handoff style.

### 2b) Audit current plan corpus against standards (required for `audit_only` and `migrate_existing`)

For repos with existing plan files, audit heading/structure coverage before proposing rewrites.

Minimum checks:

- `Progress`
- `Resume Instructions (Agent)`
- `Acceptance Criteria`
- `Tests first` under each phase
- `BDD scenarios` or explicit `Given/When/Then`
- `Decisions / Deviations Log`
- `Open Questions` only in non-ready plans (`draft`, `discovery`, or `research-ready`), never in `execution-ready` plans

Also check repo guidance for:

- explicit mention of the shared planning skill,
- clear plan-mode versus `dev:plan` boundary,
- repo-specific skill-routing hints,
- product-intent path and required supporting docs.

Produce a short gap matrix (count + file examples) and then propose migration policy:

- Do not rewrite historical completed plans only for formatting.
- Require full standards for all new plans.
- For active plans, add missing sections before further execution.

### 3) Write/update root AGENTS.md

Use `references/root_agents_template.md` as the base. Keep it repository-specific and executable.

Required outcomes:

- Safety rails and repo reality checks (secrets, encrypted env files, production constraints).
- Canonical command set with copy-paste-ready commands.
- Explicit quality gates and ordering.
- Planning boundary rules:
  - `plan mode` is read-only discovery
  - `dev:plan` writes the plan only
  - reviewed-plan handoff stays explicit and does not rely on hidden fallback reviewers
  - the repo's canonical execution workflow executes the plan
- Instruction to use the shared `planning-workflow` skill for plan creation.
- Instruction to map the canonical semantics of the `What's new` contract and after-Product-owner-context/before-Goal order into any repo-local plan template and validator so local tooling enforces behavior, not only a heading.
- The shared fail-closed ready bar: only `execution-ready` plans hand off to implementation, while unresolved `low-confidence` decisions stay in discovery or move into a single `research-ready` artifact.
- The shared expectation that non-trivial ready plans include a `test coverage matrix`.
- The shared execution feedback loop: substantive review misses reassess the `original test scope` and original plan, and repeated or cross-surface misses widen coverage before phase advance.
- The repo's discovery-ledger destination for documented out-of-scope low-risk items (for example `thoughts/discoveries/<plan-or-feature>.md`).
- Repo-specific skill-routing hints for likely work surfaces.
- Any repo-specific rules that override stale rule files.

### 4) Add repo-local planning overrides only when needed

Use `references/plan_agents_template.md` only when the repo truly needs local planning overrides beyond the shared `planning-workflow` skill.

Required outcomes:

- Document only repo-local planning differences, not the entire shared doctrine again.
- Keep repo-local overrides additive to the shared `execution-ready` / `research-ready` readiness model, `low-confidence` decision closure, `test coverage matrix` default, and execution-feedback reassessment loop.
- Point back to the shared `planning-workflow` skill as the default authority.
- Record required local docs, section additions, plan locations, or quality-gate deviations if they exist.
- When the repo owns plan templates or validators, map the canonical semantics from `planning-workflow` into those surfaces without restating the full shared contract here.
- Keep product-intent linkage and any repo-specific plan requirements explicit.

Migration rule for legacy repos:

- Allow heading aliases in old plans (`Objective` for `Goal`, `Metadata` for `Authority and inputs`, `Current State` for `Current implementation reality`) but require canonical headings in all new plans unless the repo documents a deliberate override.
- Only allow `Open Questions` when plan status is explicitly `draft`, `discovery`, or `research-ready`; `execution-ready` plans must resolve them.

### 5) Validate coherence

Before finalizing, verify:

- Root `AGENTS.md` commands are real and current.
- Root `AGENTS.md` tells agents to use the shared planning skill and names local planning inputs.
- Root `AGENTS.md` names the discovery-ledger destination used for documented out-of-scope low-risk findings.
- Any repo-local planning overrides reference real quality gates from root `AGENTS.md`.
- TDD + BDD requirements are explicit and testable.
- No contradictory guidance between root `AGENTS.md`, optional planning overrides, and the shared planning workflow.

### 6) Deliver with change rationale

When presenting updates:

- Explain which behavioral patterns were codified.
- Call out any deliberate repo-specific deviations.
- List next steps to run a first plan through the new workflow.

## Output Expectations

For a bootstrap/refactor request, produce:

1. Updated root `AGENTS.md`.
2. Optional updated planning overrides file (`thoughts/plans/AGENTS.md` or repo equivalent) only when the repo needs local deviations.
3. `thoughts/specs/product_intent.md` present (new or updated).
4. Short rationale mapping each major rule to observed delivery behavior.
5. Optional first-pass migration notes for existing plans.

For `audit_only`, produce instead:

1. Alignment scorecard (root AGENTS + plan corpus).
2. Misalignment list ordered by impact (`critical`, `important`, `nice-to-have`).
3. Proposed minimal patch set (no broad rewrite).
4. Adoption policy for existing plans (what must change now vs later).

## Resources

- `references/root_agents_template.md` - baseline structure for repo-root `AGENTS.md`.
- `references/plan_agents_template.md` - optional template for repo-local planning overrides.
- `references/product_intent_template.md` - baseline structure for `thoughts/specs/product_intent.md`.
