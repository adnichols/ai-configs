# Root AGENTS.md Template

Use this as a starting point for `<repo>/AGENTS.md`. Replace bracketed placeholders.

## 1) Purpose and scope

- State that this file is the authoritative repo-specific guide for coding agents.
- Clarify precedence if `.cursorrules` or other rule files diverge.

## 2) Repo reality checks

- Secrets policy (`.env*`, encryption, commit restrictions).
- Local vs production safety boundaries.
- Any "never do" commands specific to the repo.

## 3) Build / lint / test commands

Provide copy-paste-ready commands:

- install/dev/build
- lint/format
- unit test full suite + single-file + single-test pattern
- e2e and/or contract tests

## 4) Quality gates

Define the exact gate order (example):

1. lint
2. unit
3. build
4. e2e
5. contract (if relevant)

Include one canonical command if available (for example `pnpm quality:gates`).

## 5) Plan execution mode

Codify the planning and execution boundaries:

- `plan mode` is for read-only discovery and research.
- `dev:plan` is the plan-materialization step and may write the plan artifact only.
- The repo's canonical execution workflow executes the plan with the repo's real quality gates.
- If the repo uses Pi-style reviewed-plan handoff, codify it explicitly and name the canonical continuation. In this repo that is `/run-plan <plan>` after review integration for full lifecycle execution through PR creation and monitoring, with `/dev:run <plan>` reserved for direct execution-only handoff.
- Keep alternate reviewers such as Claude Code explicit and manual; do not describe them as hidden fallbacks inside plan mode or execution.

Add the shared fail-closed ready bar:

- only `execution-ready` plans can hand off to execution
- unresolved `low-confidence` foundational decisions stay in read-only discovery or move into a single non-ready `research-ready` plan artifact with the exact next research action
- only `execution-ready` plans should continue into review/execution commands; `research-ready` artifacts should send the agent to the recorded next research action and then back through `dev:plan`

Tell agents to load the shared `planning-workflow` skill for plan creation and regeneration.

If the repo needs additional planning rules beyond the shared skill, reference the optional local overrides file (for example `thoughts/plans/AGENTS.md`). Keep that file additive rather than duplicating the full planning doctrine.

Codify the quality-gated loop:

- implement one complete promised slice
- run one scoped review for concrete current-path failures
- fix in-scope blockers and run one targeted rereview of the findings and resulting edits
- allow a third review only for a new blocker introduced or exposed by the fix; after that budget, assign a stable, distinct `REVIEW_ESCAPE` family+scope identifier and use exactly one bounded, read-only, advisory consultation through the configured consult/council surface, whether or not a PR exists; it has no edit, fix, or implementation authority
- never rename, reword, or reconsult the same family+scope; each materially separate later family+scope may receive its own one consultation before or after PR creation
- record one disposition: verified reject/reclassify; authorized bounded pass; revert/narrow/defer; or user/product/scope decision; report specifically unresolved evidence or any path current authority cannot complete; do not reset the budget or review until clean
- do not expand the change for speculative future scale, ideal architecture, unrelated defects, or polish
- only then move to the next phase

Require the repo guidance to name the canonical discovery-ledger destination explicitly so documented out-of-scope low-risk findings always have a durable home.

Require non-trivial ready plans to include a `test coverage matrix` that maps acceptance criteria and scenarios to intended tests and verify commands.

Codify the execution feedback loop: substantive review misses must reassess the original test scope and plan, and repeated or cross-surface misses must trigger a scope/product decision or resize instead of automatic scope expansion.

Require phase-level progress updates and resumable handoff notes.

Codify a concise **Integration integrity** rule for every authorized change, build, implementation, or fix—not only plan execution:

- Before editing, determine whether the work crosses an exact contract the type system cannot fully verify (for example serialized fields, flags, configuration keys, paths, headers, migrations, or documented command examples) or requires behavior at multiple production sites.
- When neither trigger applies, record that brief conclusion in the active work state. When either applies, record the source of truth; producers/consumers or the source-derived site/family inventory; dependent docs/examples; required cross-boundary or production-path verification; and reconciliation status.
- Reopen the source of truth before editing a dependent side. After changing a shared contract, search/update/retest/search readers, writers, importers, string references, and documented examples. Reopen the record after a handoff or resume.
- Do not accept a helper, wrapper, middleware, or event-existence test as proof that distributed behavior is complete. Completion requires reconciled inventory rows and the applicable real boundary or production-path evidence.
- Keep this behavior rule concise and distinct from the shared planning/review lifecycle. Repo-local guidance supplies domain-specific contracts, source searches, and commands; it must not claim to update arbitrary external repositories that have not adopted the template.

Require a product-intent source-of-truth file at `thoughts/specs/product_intent.md`.

- If missing, create it before plan execution.
- Treat plan updates that conflict with product intent as blocking until resolved.

Require tests-first behavior for plan phases where practical and call out expected RED->GREEN evidence in handoffs.

List repo-specific skill-routing hints for common work surfaces (for example frontend, React/Next, Rust, MCP, browser automation, data tooling).

## 6) Commit and handoff rules

- Commit messages capture rationale, not only what changed.
- Require push before marking work complete (unless user asks otherwise).
- Include what evidence should be returned (changed files + gate summary + residual risks).

## 7) Style and architecture guardrails

- Formatter/linter authority.
- Import/type conventions.
- Error-handling expectations.
- Where to look for subsystem docs before non-trivial edits.

## 8) Worktree and environment notes

- Worktree env file sync steps.
- Any bootstrapping commands for local dependencies.

## 9) Fast triage commands (optional)

Useful quick commands for diagnostics, status, and targeted tests.
