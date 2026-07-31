# Agent Catalog

Current Pi subagent roster and Claude/Codex execution boundaries defined in this repository.

## Pi Subagents (Exact Three-Agent Roster)
Located under `_pi/agents/` and invoked through Pi's subagent system:

- `planner` (GPT-5.6 Sol, medium; `_pi/agents/planner.md`) — planning-only authority; it may write only the caller-named plan artifact.
- `reviewer` (GPT-5.6 Terra, medium; `_pi/agents/reviewer.md`) — read-only materiality-focused review authority, except for an explicitly named review artifact when the caller authorizes comments or output there.
- `scout` (GPT-5.6 Terra, low; `_pi/agents/scout.md`) — bounded read-only local/web discovery and evidence gathering.

`_pi/agents/Explore.md` is not an active persona. It is the required `enabled: false` override for the bundled Explore persona. Pi has no repository-owned implementation subagent: the driving agent performs code changes, test changes, fixes, and repository management directly.

Every caller packet must name the artifact or allowed surfaces, task-specific lens, output destination/format, authority boundary, verification evidence, and stop/verdict contract. Permanent agent prompts define capability and authority; callers own workflow-specific meaning.

`/cmd:start-linear-issue` is a direct deterministic driving-agent workflow. It validates Linear/Git state and creates the exact issue branch and sibling worktree without delegating repository management to a Pi subagent.

### Pi Subagent Reasoning-Effort Policy

- Agent frontmatter is authoritative: planning uses GPT-5.6 Sol medium; review uses GPT-5.6 Terra medium; scout uses GPT-5.6 Terra low.
- Do not pass caller-side reasoning overrides merely because a task appears difficult.
- Development stays in the driving session. Do not route code-writing, tests, fixes, or repository operations through any Pi persona; use subagents only for bounded planning, read-only discovery, or read-only review.
- GPT-5.4 and GPT-5.4-mini are retired from Pi-owned agents, the managed `openai-codex` model catalog, and Pi settings aliases. This is an exact Pi-only retirement and does not rewrite caller-owned providers or models.

## Claude and Codex Execution Model

- Claude's driving session performs discovery, planning, implementation, testing, documentation, and repository management directly with native tools.
- The sole repository-owned Claude subagent is `_claude/agents/reviewer.md`: a read-only `claude-sonnet-5` reviewer at `high` effort. Commands may invoke it only for bounded plan or code review; they must not delegate implementation, testing, fixes, or repository management.
- Required independent reviews run through the active harness's configured `reviewer` subagent. Do not make Codex, Claude Code, or Herdr tabs a required review transport.
- On Cursor Grok or Composer parents, launch required reviewers with `run_in_background: true` and join via `get_subagent_result` (`wait: true`). The vendored `pi-cursor-sdk` bridge also forces background for `Agent` on those models.
- Codex driving agents likewise implement authorized changes directly with their native repository tools.

## Tool Selection Priority (Codex Environment)

When agents run within Codex, they MUST prioritize native Codex tools over MCP server tools:

**DO:**
- Use native `Grep` tool (not `claude.Grep`)
- Use native `Glob` tool (not `claude.Glob`)
- Use native `Read` tool (not `claude.Read`)
- Use direct bash commands (`rg`, `find`, etc.) when appropriate

**DO NOT:**
- Call MCP-prefixed tools for basic filesystem operations
- Route through Claude Code MCP server for searches or file reads
- Use `claude.*` tool variants when native equivalents exist

**Rationale:** MCP tool wrapping introduces unnecessary latency and may produce inconsistent results. Native Codex tools are optimized for the local filesystem and provide superior performance.

## Review Safeguards

- `reviewer` (GPT-5.6 Terra medium; `_pi/agents/reviewer.md`) is the repository-owned read-only Pi material-review persona.
- Claude uses its repository-owned `reviewer` subagent (`claude-sonnet-5`, high effort) for independent plan and code reviews.
- Repository and worktree management remain in the driving session; no reviewer subagent may own state-changing work.

## Fidelity & Execution House Rules (Template for Project Repos)

Many of the Codex prompts in this repo assume that application repositories define their own fidelity and execution rules in a project-level `AGENTS.md`. The following block can be copied and adapted into those repos.

### Fidelity

- Treat the source document (user requirements, PRD, specification, or task file) as the single source of truth.
- Do not add requirements, tests, or security work beyond what is explicitly specified.
- When something is ambiguous or missing, ask for clarification instead of guessing; understanding and protecting existing behavior around the change is never a scope violation — only unrequested product change is (see the `planning-workflow` Scope section).
- Preserve stated constraints and limitations unless the project’s AGENTS.md explicitly allows widening them.

### Execution

- In this repo, operate directly on `main`; do not create feature branches or worktrees unless the user explicitly asks for them.
- This is an intentional repo-specific exception to the usual branch-first guidance used in many other repos. Do not "correct" this back to a branch workflow unless the user explicitly asks to change the protocol.
- Run the repository’s primary test command(s) before committing any change that touches behavior, plus any additional checks (lint, build, etc.) defined in the project’s AGENTS.md or TESTING.md.
- For BDD/TDD phase plans, review the implemented slice for concrete in-scope failures: unmet acceptance criteria, incomplete wiring, regressions, credible current-path security/data-loss/correctness risks, or misleading verification. You are not required to expand the change for speculative future scale, ideal architecture, unrelated pre-existing defects, optional polish, or unsupported hypothetical paths; capture those as findings.
- Default to one implementation review plus one targeted rereview after fixes. A third review is allowed only when the prior fix introduced or exposed a new concrete blocker. After three total rounds, require exactly one bounded, read-only, advisory external consultation through the harness's configured consult/council surface before reporting review non-convergence; this applies to a fixed candidate branch/diff with or without a PR. Only when that consultation authorizes it, allow one scope-bound `REVIEW_ESCAPE` adversarial reviewer-pair pass plus the existing single pass-after-fixes allowance. Do not consult repeatedly or review until clean.
- Complete the promised PR-reviewable slice before claiming success: no required stubs, TODO behavior, dead-end surfaces, missing producer/consumer wiring, fake success, or tests that avoid the real implementation. If the promised outcome cannot be completed safely, resize it before implementation to a smaller independently useful complete slice.
- Deployment, promotion, merge-dependent smoke checks, production observation, and rollback-window closure are post-merge delivery/operations work. They must never block PR creation or be used as pre-PR phase/progress/acceptance/verification gates; preserve them as explicit non-blocking handoff obligations with truthful evidence status.
- Validate planned verification commands against real repo/package/target names before execution; correct obvious drift in the plan immediately instead of carrying stale commands forward.
- When a phase spans multiple required surfaces (HTTP/CLI/MCP/UI/etc.), make parity expectations explicit and treat missing registry/dispatcher/wrapper wiring as implementation work, not optional cleanup.
- When locked schemas, payloads, response shapes, or evidence sources change, update stale fixtures/tests in the touched scope during the same run rather than leaving contract drift for a later phase.
- When working from task lists or simplification plans:
  - After completing a listed sub-task or step, immediately change its checkbox from `[ ]` to `[x]` in the same file.
  - Verify that the change is reflected in the file (do not batch updates at the end).
  - Keep any “Relevant Files” or similar sections accurate as files are created or modified.
- Prefer repository-specific guidance for tools, security, and performance; this central file is only a baseline.

Projects should copy this section into their own `AGENTS.md` and adjust details (branch naming, test commands, security expectations) to match local norms.
## Fidelity & Execution Rules  <!-- PREPOPULATED, TUNE PER PROJECT -->

These rules apply to fidelity-oriented workflows (PRDs/specs → tasks → implementation, simplification plans, etc.).

### Fidelity

- Treat the source document (user requirements, PRD, specification, or task file) as the single source of truth.
- Do not add requirements, tests, or security work beyond what is explicitly specified, unless this project section explicitly allows it.
- When something is ambiguous or missing, ask for clarification instead of guessing; understanding and protecting existing behavior around the change is never a scope violation — only unrequested product change is (see the `planning-workflow` Scope section).
- Preserve stated constraints and limitations unless this file explicitly authorizes changing them.

### Execution

- **Branches**
  - In this repo, work directly on `main` by default.
  - Do not create feature branches or worktrees for normal ai-configs changes unless the user explicitly requests that workflow.
  - This is intentionally contradictory to branch-first guidance you may see in shared/global instructions. For `ai-configs`, the repo rule wins: stay on `main` unless the user explicitly asks otherwise.

- **Testing & Validation**
  - Primary test command(s): `TODO` (e.g., `npm test`, `pytest`, `cargo test`).
  - Additional checks (fill in as relevant):
    - Lint: `TODO` (e.g., `npm run lint`)
    - Typecheck: `TODO`
    - Build: `TODO`
    - Security / SAST: `TODO`
  - Before committing behavior changes, run the primary tests and any required additional checks for the touched area.

- **Task Lists & Plans**
  - When working from markdown task lists or simplification plans:
    - After completing a listed sub-task or step, immediately change its checkbox from `[ ]` to `[x]` in the same file.
    - Verify that the change is present in the file (avoid batching updates at the end).
    - Keep any “Relevant Files” / “Changed Files” sections accurate as files are created or modified.
  - For BDD/TDD execution plans:
    - Review for concrete in-scope failures; you are not required to widen the change for speculative risks, unrelated architecture work, or polish.
    - Use one implementation review plus one targeted rereview after fixes by default. Allow a third round only for a new concrete blocker introduced or exposed by the fix. Before reporting review non-convergence, require exactly one bounded, read-only, advisory external consultation through the harness's configured consult/council surface for the fixed candidate branch/diff whether or not a PR exists; only if authorized, run one scope-bound `REVIEW_ESCAPE` adversarial reviewer-pair pass plus the existing single pass-after-fixes allowance. Do not consult repeatedly or review until clean.
    - Require a complete promised PR-reviewable slice: no required stubs, TODO behavior, dead-end surfaces, missing wiring, fake success, or verification that bypasses the real implementation. Resize incomplete outcomes before implementation rather than shipping a partial skeleton.
    - Keep deployment, promotion, merge-dependent smoke checks, production observation, and rollback-window closure outside pre-PR phase/progress/acceptance/verification gates. They are non-blocking post-merge delivery obligations and never prevent PR creation.
    - Validate `### Verify` commands against actual repo/package/target names before execution.
    - Make multi-surface parity expectations explicit when behavior must match across HTTP/CLI/MCP/UI or similar interfaces.
    - Update stale fixtures/tests when locked contracts, payloads, schemas, or evidence sources change.

## Security & Data Handling  <!-- PROJECT-SPECIFIC -->

- **Data classifications:** TODO (what data is sensitive, PII, etc.)
- **Forbidden behaviors:** TODO (e.g., never log secrets, never write to certain directories)
- **AuthN/AuthZ expectations:** TODO (e.g., always enforce permission checks in certain layers)
- **External services / secrets management:** TODO (e.g., how to access APIs, where secrets live)

## Testing Philosophy  <!-- PROJECT-SPECIFIC, WITH HINTS -->

- **Preferred test types:** TODO (unit vs integration vs e2e)
- **Coverage expectations:** TODO (e.g., “no new code without tests near 80%+ coverage in this module”)
- **Flaky / slow tests:** TODO (list known problematic suites, how to handle them)
- **BDD/TDD quality bar:** Behavioral tests should be strong enough to catch partial or misleading implementations by covering happy path, guardrail/failure behavior, counterexamples/ambiguity, and boundary/scale or cross-surface parity where applicable. Use `tdd-test-writer` when available to pressure-test the RED-phase contract.

## Git & Review Workflow  <!-- PROJECT-SPECIFIC -->

- **Branch protection rules:** TODO (what’s protected, and how)
- **Commit style:** TODO (e.g., Conventional Commits)
- **Review expectations:** TODO (e.g., when to request a human review, which files are high-risk)
- **CI / CD:** TODO (what pipelines run on PRs, what must be green before merge)
- **Index lock recovery:** For `add`/`commit`/other index-mutating git ops, use `git-with-index-lock`. On a new host/session, bootstrap first with `scripts/ensure-git-with-index-lock` (installs to `~/.agents/scripts` + `~/.local/bin` and prints the absolute path). Set `AI_CONFIGS_ROOT` if this checkout is not ai-configs. Do not thrash on raw `git` when `.git/index.lock` exists, do not delete a live lock, and do not silently skip the wrapper when bootstrap fails.

## Documentation & Task Files  <!-- PROJECT-SPECIFIC -->

- **Key docs:** TODO (e.g., `README.md`, `TESTING.md`, `ARCHITECTURE.md`, any API docs)
- **Task / PRD locations:** TODO (e.g., `/tasks/prd-*.md`, `/tasks/tasks-*.md`)
- **Doc update expectations:** TODO (e.g., "update README and API docs whenever public behavior changes")

## Dependency Selection & Reuse Policy  <!-- PROJECT-SPECIFIC -->

**Bias strongly toward reusing well-maintained third-party libraries over custom implementations.**

- **Default position**: Search for and use existing libraries
- **Vetting required**: All dependencies must meet quality criteria (maintenance, security, reputation)
- **Approval required for custom implementations**:
  - Any custom code >100 lines requires user approval
  - Document rationale: why no library was suitable
  - Include evaluation of at least 3 candidates
- **Trusted sources** (crates.io / npm):
  - Tier 1: `serde`, `tokio`, `axum`, `sqlx`, `reqwest`, `chrono`, `uuid`, `tracing`, `clap`, `thiserror`, `ed25519-dalek`, `argon2` (and ecosystem equivalents)
  - Prefer mature, well-documented, actively maintained packages
- **Forbidden**: Custom cryptographic primitives, custom JSON parsers, custom async runtimes, custom HTTP stacks
- **Load skill**: Use `dependency-selection` skill for vetting criteria and approval workflow

---

Agents should treat this `AGENTS.md` as authoritative for project-specific rules and combine it with any instructions in prompt files that are invoked from Codex. When in doubt, prefer the stricter rule (safer choice) and surface ambiguities to the human operator.


## Pi Configuration (New)

### Interaction authority boundary

Pi's global `APPEND_SYSTEM.md` uses request-type-first authority. Questions, explanations, inspection, research, comparison, diagnosis, review, planning discussion, and status requests authorize read-only work and a response, not implementation. File edits, state-changing commands, external actions, and execution todos require an explicit change/build/implement/fix request or an unambiguous continuation of an already authorized implementation. Persistence language changes how long Pi works within scope; it never expands that scope. Workflow-specific autonomy instructions apply only after the corresponding execution workflow has been explicitly invoked.

The installed doctrine records `Doctrine-Version: YYYY-MM-DD+<git-sha>` and adds `-dirty` when `APPEND_SYSTEM.md` differs from the recorded commit. Use that value with `git log -- APPEND_SYSTEM.md` when investigating behavior regressions.

The `_pi/` directory provides Pi prompt templates, subagents, and extensions. Repo-owned shared Pi skills live under `skills/`, while `skills/install-matrix.json` also inventories package-backed shared skills fetched via `npx skills`. `_pi/prompts/` contains slash-command prompt templates and `_pi/agents/` contains the maintained pi-subagents-compatible agent definitions.

### Quick Reference

Pi now supports both:
- direct prompt-template commands like `/cmd:debug`, `/dev:plan`, `/review:change`, `/run-plan`
- skill commands like `/skill:run-plan`

```bash
# Per-worktree delivery board / stage ledger (guidance, not gates)
# Tracks plan <-> review -> run-plan -> autoreview -> PR without hard-blocking
# From any Pi session: create Herdr worktree + start delivery (plain language; no flags needed)
/delivery:spawn <freeform request; Linear key optional in the text>
delivery spawn -- "honest auto-sync status"
delivery spawn -- "NOD-123 one login path"   # issue/slug inferred

# Already inside a worktree: navigator brief only
/delivery:bootstrap [goal] [--issue KEY] [--slug SLUG]
/delivery:run [issue|plan]
/delivery:status
/skill:delivery-run
delivery bootstrap --slug my-feature --goal "..."
delivery set --issue NOD-123 --retarget-id   # Linear optional; attach later
delivery reflect --trigger end-of-run --friction "..." --improvement "..." --mark-done
# reflections land in ~/.pi/DELIVERY_REFLECTIONS.md + delivery-reflections.jsonl (outside worktree)
delivery board
delivery check -v

# Full reviewed-plan implementation through ready PR:
# implementation, PM review, applicable pre-PR review, base freshness,
# PR creation, local merge-readiness consensus, and safe auto-rebase
/run-plan <thoughts/plans/<plan>.html | plan-slug>
/skill:run-plan <thoughts/plans/<plan>.html | plan-slug>

# Browser-reviewed HTML plan gate
/dev:reviewed-html-plan <task | plan-slug | thoughts/plans/<plan>.html>
/skill:reviewed-html-plan <task | plan-slug | thoughts/plans/<plan>.html>

# Planning-only / direct execution-only escape hatches
/skill:dev-plan "feature-name"
/dev:run thoughts/plans/<plan>.html

# Git & Linear
/skill:cmd-create-pr

# Development
# Active-harness reviewer subagent review
/skill:autoreview thoughts/plans/<plan>.html

# Context
/skill:cmd-create-handoff "pausing work"
/skill:cmd-resume-handoff <ticket>
```

See `_pi/README.md` for complete documentation.

When creating a PR for Linear-backed work, the PR title must start with the
Linear issue key and include the Linear issue title, for example
`NOD-632: Ccore health auth guidance`. Do not rely on the latest commit subject
unless it already satisfies that format.

Expected Pi reviewed-plan flow in this repo:
- Active browser-reviewed plans are semantic HTML files under `thoughts/plans/<slug>.html`; do not create Markdown companions for that flow.
- `/delivery:run` / `/skill:delivery-run` keeps a per-worktree stage ledger and board for the plan ↔ review → run-plan → autoreview → PR cycle. Doctrine is guidance, not gates: `delivery check` advisories never hard-block continuation.
- `/run-plan <plan>` / `/skill:run-plan <plan>` is the full implementation-through-ready-PR workflow for an existing execution-ready reviewed plan: implementation, implementation-stage PM review, the active-harness reviewer-subagent pre-PR review, base freshness, PR creation, current PR feedback snapshot, and local merge-readiness consensus without waiting for external approval.
- `/dev:reviewed-html-plan <task | plan>` / `/skill:reviewed-html-plan <task | plan>` is the browser-reviewed HTML pre-execution gate for Doct plan feedback plus PM and active-harness reviewer-subagent plan review; it must register through `doct-agent plans register`, follow returned `listenerInstructions`, and start the durable queue-backed listener before browser-review handoff.
- `skills/doct-document-ops/SKILL.md` is the sole source for concrete Doct plan commands, HTML/Markdoc/Markdown plan publishing guidance, listener startup, readiness metadata, canonical URL rules, and comment mechanics; other planning skills should reference it instead of duplicating command recipes.
- `/skill:dev-plan <task>` remains available for planning-only work.
- `/dev:run <plan>` remains available when you already have an execution-ready reviewed plan and want direct execution only.

Legacy external review commands remain explicit opt-in tools. They are not hidden fallbacks inside plan mode or execution.

## Linear Integration (ltui)

`ltui` is the token-efficient Linear CLI for AI agents (replaces the legacy linear CLI/MCP). Use it for all Linear interactions.

### Setup
1. Get a Linear API key: https://linear.app/settings/api
2. Configure authentication:
   ```bash
   ltui auth add --name default --key <api-key>
   ltui auth list
   ltui teams list
   ```

### Project Alignment (.ltui.json)
Create a `.ltui.json` in the repo root so agents target the right team/project by default:
```json
{
  "profile": "default",
  "team": "ENG",
  "project": "Doc Thingy",
  "defaultIssueState": "Todo",
  "defaultLabels": ["bug"],
  "defaultAssignee": "me"
}
```
Commit this file so everyone shares the defaults.

### Common Commands
```bash
ltui --format detail issues view <ISSUE_KEY>
ltui issues create --team <TEAM> --project "Project Name" --title "Issue title" --description "Description" --state "Backlog" --label bug
ltui issues update <ISSUE_KEY> --state "In Review"
ltui issues comment <ISSUE_KEY> --body "Comment text"
ltui issues link <ISSUE_KEY> --url <pr-url> --title "PR #123"
```

For more, run `ltui --help` or see the ltui README in this configuration repo.

## Pi Skills (pi Agent)

This repository includes Pi-specific prompt templates under `_pi/prompts/`, pi-subagents-compatible agent definitions under `_pi/agents/`, and shared installable skills declared by `skills/install-matrix.json` (with repo-owned payloads under `skills/`). Pi is an alternative AI coding agent that uses prompt templates plus the [Agent Skills specification](https://agentskills.io/specification).

### Available Skills

**Git & Linear:**
- `/skill:cmd-create-pr` — Create GitHub pull request

**Development:**
- `/skill:dev-plan` — Materialize execution plan
- `/skill:cmd-graduate` — Graduate completed work to spec/
- `/skill:sentry-cli` — Investigate Sentry issues/events and safely mute, resolve, or unresolve issues after confirmation

**Context Management:**
- `/skill:cmd-create-handoff` — Create handoff document
- `/skill:cmd-resume-handoff` — Resume from handoff

**Reviews:**
- `/skill:reviewed-html-plan` — Create/register browser-reviewed HTML plans in Doct, start the returned durable listener, process Doct plan feedback, run PM plus the active-harness reviewer-subagent plan review, and stop at execution-ready handoff
- `/skill:delivery-run` — Per-worktree delivery stage ledger and board for plan ↔ review → run-plan → autoreview → PR. Guidance not gates; `delivery check` advisories never hard-block.
- `/skill:autoreview` — Canonical bounded active-harness reviewer-subagent pre-PR implementation review with one targeted rereview after fixes; a third round is reserved for a new blocker introduced or exposed by the fix. Inside `run-plan` it returns `OPEN_PR_READY` and hands back to mandatory PR creation instead of concluding or waiting for external approval.
- `/skill:pre-pr-implementation-review` — Indefinite compatibility alias for `/skill:autoreview`; it preserves arguments and the same `OPEN_PR_READY` handoff semantics.
- `/skill:run-plan` — Execute an explicit plan through implementation, implementation-stage PM review, applicable pre-PR review, base freshness, verification, PR creation, current PR feedback snapshot, local merge-readiness consensus, and safe auto-rebase when needed.

### Configuration

Pi auto-discovers project-local resources from `.pi/prompts/`, `.pi/skills/`, and `.pi/agents/`. In this repo, repo-owned shared installable skills live under `skills/`, `skills/install-matrix.json` inventories the full shared skill set, and `install.sh` installs Pi prompt templates, agents, and extensions from `_pi/` into `~/.pi/agent/` while syncing shared skills into `~/.agents/skills`. See `_pi/README.md` for details.

For local development in this repo, add the repo-owned shared skill tree to your Pi settings:
```json
{
  "skills": ["skills"]
}
```
## Hermes Configuration Source of Truth

- Managed Hermes configuration lives in `_hermes/default` and is synchronized by `scripts/hermes_config_sync.py`.
- For any change to live Hermes configuration (`~/.hermes` skills, config, hooks, plugins, scripts, cron jobs, memories, or profile-local equivalents), also run `python3 scripts/hermes_config_sync.py export` from this repo, then `python3 scripts/hermes_config_sync.py verify`.
- Prefer source-first edits in `_hermes/default`; preview install with `python3 scripts/hermes_config_sync.py install --dry-run`, then apply with `python3 scripts/hermes_config_sync.py install --apply` when live Hermes should be updated.
- After synchronization and verification, commit and push the `ai-configs` changes so the repo copy stays authoritative. Do not commit secrets or runtime state; the sync tool excludes those surfaces.

## Supervisor workflow

The trajectory-guarding supervisor is opt-in. Do **not** attach one automatically for `run-plan`, `dev:run`, or any other plan-execution workflow. Launch it only when the operator explicitly requests supervision, using `skills/supervise/SKILL.md`. The worker owns technical judgment; the supervisor owns trajectory (outcome aim, expansion reasoning, disclosure honesty). Product-changing expansions escalate to the human; the supervisor never approves them.
