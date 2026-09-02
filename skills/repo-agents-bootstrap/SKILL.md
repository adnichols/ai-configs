---
name: repo-agents-bootstrap
description: Bootstrap or refactor repository AGENTS guidance so repo-specific rules are local while shared planning doctrine stays centralized in the planning workflow skill. Use when creating/updating `AGENTS.md`, optionally adding repo-local planning overrides, codifying plan-mode versus `dev:plan` boundaries, or aligning repos to the shared TDD/BDD planning and execution model.
---

# Repo Agents Bootstrap

## Overview

The bootstrap produces four layers:

1. **Root `AGENTS.md`**: short, pointer-first, only content an agent cannot derive or guess. Target under 200 lines. Evidence: developer-written, non-inferable context is the only kind measured to help agents; restated overview content raises inference cost without raising success (ETH Zurich, arXiv:2602.11988), and vendors cap or truncate instruction files (Claude Code targets <200 lines per file, Codex hard-caps combined docs at 32 KiB). Deep content routes to deep docs, not the root file.
2. **Instruction-file topology**: one canonical `AGENTS.md` plus thin `CLAUDE.md`/`GEMINI.md` pointer files containing `@AGENTS.md`; skip `.github/copilot-instructions.md` (shadows `AGENTS.md` for first-match resolvers like Zed) and `llms.txt` (no repo harness consumes it). Nested `AGENTS.md` per functional area: the file closest to the edited file wins.
3. **Structure-convention layer** (for example `docs/repo-structure.md`): the task-to-path map, naming vocabulary sourced from the spec/domain corpus, file budgets, import discipline, and a machine-checked concept map — plus a committed zero-dependency structure-check lever that fails CI when the map lies.
4. **Optional planning overrides file** (usually `thoughts/plans/AGENTS.md`) only when the repo needs planning rules beyond the shared `planning-workflow` skill.

The shared planning doctrine lives in the `planning-workflow` skill. This bootstrap skill makes each repo point to that shared doctrine while recording repo-specific reality: real commands, real quality gates, required docs, domain skill hints, and any explicit local deviations.

## Modes

Pick one mode before editing files:

- `audit_only`: analyze repo alignment and propose deltas without modifying repo files.
- `bootstrap_new`: create root `AGENTS.md` and any required supporting planning docs for repos with little/no prior guidance.
- `migrate_existing` (recommended default): preserve strong existing guidance, patch only misalignments, and avoid broad rewrites.

For mature repos (like doct/ccore), start in `audit_only` and present a delta plan first.

## Operating Model To Codify

Capture these behaviors as defaults:

- Shared planning doctrine lives in the `planning-workflow` skill, not duplicated into any repo file. Root `AGENTS.md` points at doctrine; it never restates it (ready bars, review budgets, REVIEW_ESCAPE mechanics, and plan-section contracts stay in the skills that own them).
- The root `AGENTS.md` is short and specific: unguessable commands, non-obvious invariants, hard boundaries framed as Always / Ask first / Never, and a task-to-path map. It excludes architecture overviews, derivable conventions, and anything a linter or script enforces.
- Instruction-file topology is part of bootstrap: canonical `AGENTS.md`; `CLAUDE.md` and `GEMINI.md` as one-line `@AGENTS.md` imports; no `.github/copilot-instructions.md`; no `llms.txt`; nested `AGENTS.md` per functional area.
- Structure conventions are a first-class bootstrap deliverable, not an afterthought: where-to-work map, domain-vocabulary naming, file budgets, import discipline, machine-checked concept map.
- Every convention names its enforcement (lint rule, script, CI gate) or is explicitly marked advisory. Bootstrap commits a runnable structure-check lever the day guidance lands, not later.
- Product intent lives in the repo's canonical spec-corpus location. Default to `thoughts/specs/product_intent.md` only when the repo has no existing spec corpus; a repo with `spec/` (or equivalent) keeps intent with the corpus and root `AGENTS.md` names the real path. Never fragment an existing corpus.
- Root-file governance: add a rule only after an observed repeated agent mistake; delete rules that tooling now enforces.
- `plan mode` is discovery-only and read-only.
- `dev:plan` is the plan-materialization step: it may write the plan artifact, but must not change code or other repo files.
- `dev:plan` must fail closed on `low-confidence` foundational decisions: it only hands off an `execution-ready` plan when those decisions are resolved, and otherwise asks the user or writes exactly one non-ready `research-ready` plan artifact with the exact next research action.
- Root `AGENTS.md` tells agents to use the shared planning skill and names any repo-specific planning inputs or overrides.
- Plan-first execution with phase checkpoints under the repo's canonical execution workflow.
- Integration integrity for every authorized implementation path, including direct fixes that do not use a plan or `run-plan`: before editing, detect exact untyped contracts and distributed production behavior; use a compact record only when a trigger applies; reread the source of truth before dependent edits; search/reconcile dependents after contract changes; and require cross-boundary or production-path proof before completion.
- In Pi-style reviewed-plan repos, the handoff stays explicit: `/review:plan` -> `/review:change-integrate` -> optional `/review:plan-adversarial` -> `/cmd:execute-plan` -> execution. Alternate reviewers such as `/review:change-claude-code` remain explicit opt-ins, not hidden fallbacks.
- Phase advancement requires no unresolved concrete in-scope blocker: unmet acceptance criteria, incomplete wiring, regressions, credible current-path security/data-loss/correctness risks, or misleading verification. Speculative future scale, ideal architecture, unrelated pre-existing defects, optional polish, and unsupported hypothetical paths do not block the phase and must not expand its scope.
- Default to one implementation review plus one targeted rereview after fixes; allow a third round only for a new blocker introduced or exposed by the fix. After that budget, assign a stable, distinct `REVIEW_ESCAPE` family+scope identifier and use exactly one bounded, read-only, advisory consultation through the configured consult/council surface, whether or not a PR exists. The consultation has no edit, fix, or implementation authority; never rename, reword, or reconsult the same family+scope; each materially separate later family+scope may receive its own one consultation before or after PR creation. Record exactly one disposition: verified reject/reclassify; authorized bounded pass; revert/narrow/defer; or user/product/scope decision. Report specifically any unresolved disposition evidence or path that current authority cannot complete. Do not reset the budget or review until clean.
- Complete the promised slice before advancement: no required stubs, TODO behavior, dead-end surfaces, missing producer/consumer wiring, fake success, or verification that bypasses the real implementation. Resize an outcome before implementation if it cannot be delivered as an independently useful complete slice.
- Resumability: `Progress` with stable IDs, explicit `Resume Instructions`, and append-only decision/deviation logs.
- Evidence-first validation: lint, unit, build, e2e (and contract tests if applicable) before claiming done.
- Reviews are scoped reliability gates, not open-ended product audits. Reviewer findings must be triaged against the accepted current slice before any fix is made.
- Execution feedback loops must reassess the original test scope and plan when substantive misses appear. Repeated or cross-surface misses trigger a scope/product decision or resize instead of automatic scope expansion.
- Commit and push discipline with rationale, not just code diffs.
- Test-first posture: define behavior before implementation wherever practical.
- Keep planning depth `complexity-aware`: simple tasks stay lightweight, while non-trivial ready plans need complete contracts plus a `test coverage matrix` strong enough to catch partial implementations.
- Product-intent anchored planning: every active plan must trace back to the repo's declared product-intent file, named in root `AGENTS.md`; default `thoughts/specs/product_intent.md` only for repos without an existing spec corpus.
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

- Shared process doctrine (plan contracts, ready bars, review budgets, integration-integrity mechanics) -> skills (`planning-workflow`, `integration-integrity`, `tdd-test-writer`)
- Repo-specific execution truth (commands, gates, boundaries, routing) -> root `AGENTS.md` (short, pointer-first)
- Instruction-file bridges -> one-line `CLAUDE.md` / `GEMINI.md` pointer files
- Area-specific rules and commands -> nested `AGENTS.md` (closest wins)
- Structure conventions and the checked concept map -> structure doc (for example `docs/repo-structure.md`) + structure-check script
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
Detect the repo's canonical spec or documentation corpus (for example `spec/`, `docs/specs/`): product intent lives with the corpus when one exists.
Detect existing instruction files and bridges: `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`, nested `AGENTS.md` files, symlinks, any `llms.txt`. Conflicting or shadowing files (`copilot-instructions.md` preceding `AGENTS.md` for first-match resolvers, checked-in copies duplicating the canonical file) are recorded as alignment gaps, never silently kept.

If a product-intent file is missing:

- mark it as a `critical` alignment gap,
- create it from `references/product_intent_template.md` at the repo's canonical spec-corpus location (default `thoughts/specs/product_intent.md` only when no spec corpus exists),
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
- product-intent path matching the repo's canonical spec corpus,
- root file size within target (doctrine restatement is the usual cause of bloat),
- instruction-file topology: bridges present and pointing at the canonical file, no shadowing duplicates, nested `AGENTS.md` where functional areas have their own rules,
- a structure layer: task-to-path map, naming-vocabulary rule, file budget, import discipline, and every convention naming enforcement or marked advisory,
- a committed structure-check lever that runs green today.

Produce a short gap matrix (count + file examples) and then propose migration policy:

- Do not rewrite historical completed plans only for formatting.
- Require full standards for all new plans.
- For active plans, add missing sections before further execution.

### 3) Write/update root AGENTS.md

Use `references/root_agents_template.md` as the base. Keep it repository-specific and executable.

Required outcomes (each a short section; the whole file targets under 200 lines):

- Safety rails and repo reality checks (secrets, encrypted env files, production constraints), framed as Always / Ask first / Never.
- Canonical command set: only commands that exist today, copy-paste-ready, near the top. Quality gates named with order and one canonical gate command; gate doctrine stays in the workflow skills.
- Where-to-work map: task-to-path table naming each functional area and its nested `AGENTS.md`. Routing is the highest-value root-file content, so it goes early.
- Workflow routing as one-line pointers: the shared `planning-workflow` skill owns plan methodology; `plan mode` is read-only discovery and the plan-materialization step (for example `dev:plan`) writes the plan artifact only; only `execution-ready` plans hand off, while unresolved `low-confidence` decisions stay in discovery or one `research-ready` artifact; reviewed-plan handoff stays explicit with no hidden fallback reviewers; the repo's canonical execution workflow executes the plan; load `integration-integrity` before changing exact untyped contracts or behavior distributed across production sites.
- Product-intent pointer: the repo's declared product-intent path; plans align or log a deviation.
- `### Verify` commands validated against real repo/package/target names before execution, and stale fixtures updated when locked contracts change (state the rule in one line; the mechanics stay in the shared skill).
- The repo's discovery-ledger destination for documented out-of-scope low-risk items (for example `thoughts/discoveries/<plan-or-feature>.md`).
- Engineering rules that are non-obvious and specific to this repo, each marked `Enforced:` (tooling), `Checked:` (structure gate), or `Advisory:` (review judgment). A rule without an enforcement designation does not ship.
- Repo-specific skill-routing hints for likely work surfaces.
- Rule governance: rules enter after observed repeated mistakes; tooling-enforced rules leave.

Forbidden in the root file (route these instead):

- Restated `planning-workflow` doctrine: ready-bar internals, review/rereview budgets, REVIEW_ESCAPE mechanics, plan-section contracts, TDD/BDD phase rules. Point in one line; restating forks the doctrine.
- Architecture overviews and file-by-file descriptions a reader can derive from the tree (measured unhelpful: arXiv:2602.11988).
- Anything the formatter, linter, or structure gate enforces.
- Non-trivial ready plans and `test coverage matrix` expectations: one pointer line to the shared skill, never the full contract.
- Repo-local plan templates and validators map the canonical semantics of the `planning-workflow` contracts (the `What's new` section and its after-Product-owner-context/before-Goal order) into their own surfaces without restating the full contract in the root file.

### 3b) Create the instruction-file topology and structure layer

Deliver every time, with content scaled to the repo:

- Bridges: `CLAUDE.md` and `GEMINI.md`, each containing exactly `@AGENTS.md` as its first content line (harness-specific additions below it only when needed). Do not create `.github/copilot-instructions.md` (shadows `AGENTS.md` for first-match resolvers like Zed) or `llms.txt` (a website-docs convention; no repo harness auto-reads it). Remove or replace checked-in copies of the canonical file.
- Nested `AGENTS.md` policy: any functional area with its own commands or rules carries a short `AGENTS.md` of its own (closest to the edited file wins); the root where-to-work map links each one.
- Structure contract (for example `docs/repo-structure.md`), sized to the repo: target layout, concept/ownership map, naming vocabulary sourced from the spec or domain corpus, file budgets, import discipline (barrels, deep imports, direction rules), per-area test layout, and an enforcement matrix (rule -> mechanism -> active date).
- Structure-check lever: a committed, zero-dependency script (for example `scripts/check-structure.mjs`) validating bridge files, concept-map paths and spec links, nested-guide presence, budgets, and area hermeticity where applicable. It must run green on delivery day, before any package manager is installed. Tool-based enforcement (boundary lint, cycle detection) may activate later; the lever covers today.

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

- Root `AGENTS.md` commands are real and current (run the structure gate; spot-run one workspace command where one exists).
- Root `AGENTS.md` sits within the length target and contains no restated shared doctrine.
- Root `AGENTS.md` tells agents to use the shared planning skill and names local planning inputs.
- Root `AGENTS.md` names the discovery-ledger destination used for documented out-of-scope low-risk findings.
- Product intent sits in the repo's canonical spec-corpus location, and root `AGENTS.md` points at it.
- Bridge files exist, are one-line imports of the canonical file, and no shadowing or duplicated instruction files remain.
- Every root rule names its enforcement or is marked advisory, and the structure-check lever runs green from a clean checkout.
- Any repo-local planning overrides reference real quality gates from root `AGENTS.md`.
- TDD + BDD requirements are explicit and testable in the skills and plan templates the repo points at.
- No contradictory guidance between root `AGENTS.md`, nested `AGENTS.md` files, optional planning overrides, and the shared planning workflow.

### 6) Deliver with change rationale

When presenting updates:

- Explain which behavioral patterns were codified.
- Call out any deliberate repo-specific deviations.
- List next steps to run a first plan through the new workflow.

## Output Expectations

For a bootstrap/refactor request, produce:

1. Updated root `AGENTS.md` (pointer-first, within the length target).
2. Instruction-file topology: `CLAUDE.md` and `GEMINI.md` pointer files; removals or replacements of shadowing/duplicated instruction files noted explicitly.
3. Structure contract doc plus committed structure-check lever, running green on delivery day.
4. Optional updated planning overrides file (`thoughts/plans/AGENTS.md` or repo equivalent) only when the repo needs local deviations.
5. Product-intent file present (new or updated) at the repo's canonical spec-corpus location.
6. Short rationale mapping each major rule to observed delivery behavior or cited evidence.
7. Optional first-pass migration notes for existing plans.

For `audit_only`, produce instead:

1. Alignment scorecard (root AGENTS + plan corpus + instruction-file topology + structure layer).
2. Misalignment list ordered by impact (`critical`, `important`, `nice-to-have`).
3. Proposed minimal patch set (no broad rewrite).
4. Adoption policy for existing plans and guidance (what must change now vs later).

## Resources

- `references/root_agents_template.md` - baseline structure for repo-root `AGENTS.md`.
- `references/plan_agents_template.md` - optional template for repo-local planning overrides.
- `references/product_intent_template.md` - baseline structure for the repo's product-intent file (`thoughts/specs/product_intent.md` only when the repo has no existing spec corpus).
