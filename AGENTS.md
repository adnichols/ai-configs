# Agent Catalog

Current roster of bespoke Claude and Codex agents defined in this repository. All briefs live under `claude/agents/`, and templates for new roles live in `claude/agents/templates/` (if applicable).

## Implementation & Architecture
- `developer` (sonnet; `claude/agents/developer.md`) — Implements specs with tests and enforces zero linting violations.
- `developer` (sonnet; `opencode/agents/developer.md`) — Architectural specification implementation with tests and zero linting violations.
- `developer-fidelity` (sonnet; `claude/agents/developer-fidelity.md`) — Implements specifications with absolute fidelity—no extra tests, features, or safeguards.
- `simplify-planner` (opus; `claude/agents/simplify-planner.md`) — Refactor planning specialist who produces cleanup plans that preserve existing behaviour.

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

## Review & Fidelity Safeguards
- `quality-reviewer` (sonnet; `opencode/agents/quality-reviewer.md`) — Reviews code for real issues (security, data loss, performance) with measurable impact focus.
- `quality-reviewer` (inherits workspace default model; `claude/agents/quality-reviewer.md`) — Production safety review covering security, data loss, regressions, and performance.
- `quality-reviewer-fidelity` (sonnet; `claude/agents/quality-reviewer-fidelity.md`) — Ensures code matches specification requirements exactly with no scope expansion.
- `fidelity-reviewer` (opus; `claude/agents/fidelity-reviewer.md`) — Compares generated task lists against source specifications and researches discrepancies.

## Debugging Support
- `debugger` (sonnet; `claude/agents/debugger.md`) — Evidence-driven debugger who gathers logs, forms hypotheses, and recommends fixes without modifying production code.

## Documentation
- `technical-writer` (sonnet; `claude/agents/technical-writer.md`) — Produces concise post-implementation documentation with tight token limits.

## Utility Agents
These agents are typically invoked by other agents or for specific tool-use tasks:

- `codebase-analyzer` (`claude/agents/codebase-analyzer.md`) — Explains how code works, traces execution paths and data flows.
- `codebase-locator` (`claude/agents/codebase-locator.md`) — Finds where things are in the codebase.
- `codebase-pattern-finder` (`claude/agents/codebase-pattern-finder.md`) — Identifies architectural patterns and conventions.
- `explore` (temperature 0.1; `opencode/agents/explore.md`) — Fast code exploration using Serena tools for search and analysis.
- `multi-reviewer` (glm-4.7; `opencode/agents/multi-reviewer.md`) — Reviews specifications and writes structured feedback to a file.
- `playwright-runner` (`opencode/agents/playwright-runner.md`) — Runs E2E tests in isolated PTY sessions with real-time failure streaming.
- `thoughts-analyzer` (`claude/agents/thoughts-analyzer.md`) — Synthesizes context from plans, specs, and research in `thoughts/`.
- `thoughts-locator` (`claude/agents/thoughts-locator.md`) — Finds relevant documentation within `thoughts/`.
- `web-search-researcher` (`claude/agents/web-search-researcher.md`) — Finds external information using web search.
- `worktree-creator` (`claude/agents/worktree-creator.md`) — Manages git worktrees for parallel execution.
- `worktree-creator` (deepinfra/MiniMaxAI/MiniMax-M2.1; `opencode/agents/worktree-creator.md`) — Creates git worktrees for Linear issues.

---

When adding new agents, create the brief in `claude/agents/` and update this catalog so downstream installations discover the new capability.

## Fidelity & Execution House Rules (Template for Project Repos)

Many of the Codex prompts in this repo assume that application repositories define their own fidelity and execution rules in a project-level `AGENTS.md`. The following block can be copied and adapted into those repos.

### Fidelity

- Treat the source document (user requirements, PRD, specification, or task file) as the single source of truth.
- Do not add requirements, tests, or security work beyond what is explicitly specified.
- Do not broaden scope; when something is ambiguous or missing, ask for clarification instead of guessing.
- Preserve stated constraints and limitations unless the project’s AGENTS.md explicitly allows widening them.

### Execution

- Prefer working on a branch for larger or riskier changes, but committing directly to `main` is acceptable for small, low-risk updates in this repo.
- Run the repository’s primary test command(s) before committing any change that touches behavior, plus any additional checks (lint, build, etc.) defined in the project’s AGENTS.md or TESTING.md.
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
- Do not broaden scope; when something is ambiguous or missing, ask for clarification instead of guessing.
- Preserve stated constraints and limitations unless this file explicitly authorizes changing them.

### Execution

- **Branches**
  - Branches are recommended for larger changes, but commits directly to `main` are allowed in this repo.
  - If using a branch, naming convention: `TODO` (e.g., `feature/<short-summary>`, `issue/<ticket-id>`).

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

## Security & Data Handling  <!-- PROJECT-SPECIFIC -->

- **Data classifications:** TODO (what data is sensitive, PII, etc.)
- **Forbidden behaviors:** TODO (e.g., never log secrets, never write to certain directories)
- **AuthN/AuthZ expectations:** TODO (e.g., always enforce permission checks in certain layers)
- **External services / secrets management:** TODO (e.g., how to access APIs, where secrets live)

## Testing Philosophy  <!-- PROJECT-SPECIFIC, WITH HINTS -->

- **Preferred test types:** TODO (unit vs integration vs e2e)
- **Coverage expectations:** TODO (e.g., “no new code without tests near 80%+ coverage in this module”)
- **Flaky / slow tests:** TODO (list known problematic suites, how to handle them)

## Git & Review Workflow  <!-- PROJECT-SPECIFIC -->

- **Branch protection rules:** TODO (what’s protected, and how)
- **Commit style:** TODO (e.g., Conventional Commits)
- **Review expectations:** TODO (e.g., when to request a human review, which files are high-risk)
- **CI / CD:** TODO (what pipelines run on PRs, what must be green before merge)

## Documentation & Task Files  <!-- PROJECT-SPECIFIC -->

- **Key docs:** TODO (e.g., `README.md`, `TESTING.md`, `ARCHITECTURE.md`, any API docs)
- **Task / PRD locations:** TODO (e.g., `/tasks/prd-*.md`, `/tasks/tasks-*.md`)
- **Doc update expectations:** TODO (e.g., “update README and API docs whenever public behavior changes”)

---

Agents should treat this `AGENTS.md` as authoritative for project-specific rules and combine it with any instructions in prompt files that are invoked from Codex. When in doubt, prefer the stricter rule (safer choice) and surface ambiguities to the human operator.


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
ltui issues view <ISSUE_KEY> --format detail
ltui issues create --team <TEAM> --project "Project Name" --title "Issue title" --description "Description" --state "Backlog" --label bug
ltui issues update <ISSUE_KEY> --state "In Review"
ltui issues comment <ISSUE_KEY> --body "Comment text"
ltui issues link <ISSUE_KEY> --url <pr-url> --title "PR #123"
```

For more, run `ltui --help` or see the ltui README in this configuration repo.
