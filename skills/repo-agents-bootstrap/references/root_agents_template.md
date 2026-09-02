# Root AGENTS.md Template

Baseline for `<repo>/AGENTS.md`. Replace bracketed placeholders. Keep the file
pointer-first: it answers "what would make an agent fail here that it cannot
learn from the code?" and routes everything else. Target under 200 lines; if a
section grows past that, move detail into a deep doc and link it.

## 1) Header and precedence

- Name this file the canonical instruction file. Note that `CLAUDE.md` and
  `GEMINI.md` import it and must be edited here, not in the pointers.
- State precedence: the nested `AGENTS.md` closest to the edited files wins;
  explicit user instructions override everything.
- Note any legacy rule files (`.cursorrules`, checked-in copies) this file
  supersedes.

## 2) Repo reality checks

- Secrets policy (`.env*`, encrypted env files, commit restrictions).
- Local vs production safety boundaries.
- Repo-specific "never do" commands.

## 3) Hard boundaries (Always / Ask first / Never)

- Always: invariants every change must hold (checked-file updates, doc-link
  upkeep, gate execution before the stated point of completion).
- Ask first: irreversible or spec/config-level changes (schema, API contracts,
  ADR-governed documents, new dependencies, new top-level directories).
- Never: hard violations (commit secrets, bypass named boundaries, disable
  gates, restate derivable content in this file).

## 4) Where to work

- Task-to-path table: each functional area, its owning path, and its nested
  `AGENTS.md` when it has one. This is the highest-value section; put it
  early. Names here and names in code are the same strings.

## 5) Commands

- Only commands that exist today, copy-paste-ready, with install/dev/build,
  lint/format, full + single-test invocations, and the structure/quality gate.
- One canonical gate command (for example `pnpm quality:gates` or
  `node scripts/check-structure.mjs`) and the moment it must run.
- If commands live in workspaces, say so once and defer to each workspace's
  nested `AGENTS.md`; never duplicate workspace scripts at root.

## 6) Engineering rules

- Only non-obvious, repo-specific rules. Each marked `Enforced:` (lint/tool),
  `Checked:` (structure gate), or `Advisory:` (review judgment).
- A rule without an enforcement designation does not ship.

## 7) Workflow routing (pointers, one line each)

- Plan methodology: the shared `planning-workflow` skill. Never restate its
  ready bar, review economics, or plan contract here.
- Plan boundary: discovery mode is read-only; the plan-materialization step
  (for example `dev:plan`) writes the plan artifact only; the repo's canonical
  execution workflow executes the plan; reviewed-plan handoff stays explicit
  with no hidden fallback reviewers.
- Readiness: only `execution-ready` plans hand off to execution; unresolved
  `low-confidence` foundational decisions stay in discovery or in one
  non-ready `research-ready` artifact with the exact next research action.
- Product intent: path to the repo's product-intent file; plans align to it or
  log a deviation.
- Discovery ledger: destination for documented out-of-scope low-risk findings
  (for example `thoughts/discoveries/<topic>.md`).
- Integration-integrity: load `integration-integrity` before changing exact
  untyped contracts or behavior distributed across production sites.
- Optional repo-local planning overrides file (for example
  `thoughts/plans/AGENTS.md`): link it when it exists.
- Testing doctrine: name the expectation (tests-first where practical, the
  required scenarios, the `test coverage matrix` for non-trivial plans) and
  point to where the full doctrine lives.
- Skill-routing hints: which skills to load for likely surfaces (frontend,
  Rust, browser automation, MCP, data tooling).

## 8) Commits and handoff

- Commit messages carry rationale, not only what changed.
- Delivery evidence to return: changed files, gate summary, residual risks.
- Phase progress and resumable handoff notes live in the plan artifact, not
  here.

## 9) Environment notes (only when non-obvious)

- Worktree env-file sync. Local dependency bootstrap. Toolchain pins that
  differ from the machine default. Otherwise omit.

## 10) Rule governance

- Rules enter this file after an observed repeated agent mistake.
- Rules leave when lint, scripts, or CI start enforcing them.
