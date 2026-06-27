# Command Workflow Documentation

## Overview

This directory contains a comprehensive set of commands that support a complete development workflow from requirements to implementation and quality assurance. All commands are at the root level with colon-delimited namespacing.

### Core Workflow Commands

**PRD Workflow:**
1. **`prd:1:create-prd.md`** - Create Product Requirements Documents with strict scope preservation
2. **`prd:2:gen-tasks.md`** - Convert PRDs to task lists using fidelity-preserving approach

**Specification Workflow:**
3. **`spec:1:create-spec.md`** - Research ideas and produce specification documents
4. **`spec:2:gen-tasks.md`** - Convert specifications directly to tasks with 100% fidelity

**Task Processing (Unified):**
5. **`3:process-tasks.md`** - Process task lists autonomously with fidelity agents (works for both PRD and spec workflows)

### Documentation Commands
6. **`doc:fetch.md`** - Fetch documentation for a single library/framework
7. **`doc:fetch-batch.md`** - Batch fetch documentation from markdown lists
8. **`doc:update.md`** - Post-implementation documentation generation

### Test Orchestration Commands
9. **`test:run-playwright.md`** - Run Playwright in PTY, stream failures, and spawn live fixer subagents
10. **`test:run-playwright:all.md`** - Run full Playwright suite (`test:e2e:all`) in PTY with live fixer orchestration

### Simplification Commands
11. **`simplify:1:create-plan.md`** - Generate code simplification plans
12. **`simplify:2:process-plan.md`** - Execute approved simplification plans

### Git Utility Commands
13. **`cmd:commit-push.md`** - Commit all changes and push to GitHub
14. **`cmd:create-pr.md`** - Create a pull request
15. **`cmd:start-linear-issue.md`** - Bootstrap a Linear issue as an OpenCode workspace-backed build environment
16. **`cmd:linear-build-workspace.md`** - Deterministic Linear issue build runner using OpenCode workspaces plus the enforced `linear_build_orchestrator.py` run ledger
17. **`cmd:start-linear-issue-branch.md`** - Start a Linear issue on a new branch (no workspace/worktree) and draft a first-pass plan
18. **`cmd:execute-plan.md`** - Reviewed-plan handoff that routes into `/run-plan` or `/dev:run`
19. **`cmd:review-pr-comments.md`** - Review and address GitHub PR comments since last commit

### Workflow Skills
20. **`run-plan`** - Full lifecycle reviewed-plan execution through PR creation and monitoring
21. **`adn-dev-wf`** - Broader reviewed-plan workflow skill for plan refresh, review integration, direct execution, and PM follow-up
22. **`ralph:review-gpt5.5.md`** - Run `/review` in a loop (GPT-5.5), apply quick fixes, stop when no straightforward fixes remain
23. **`ralph:review-opus.md`** - Run `/review` in a loop (Opus), apply quick fixes, stop when no straightforward fixes remain

## Command Workflows

### Workflow 0: Plan-First Execution (Shared Default)
`[plan mode discovery] → /dev:plan → [execution-ready → optional /dev:pm-review <plan> plan → /review:plan <plan> → /review:change-integrate <plan> → /cmd:execute-plan <plan> → choose /run-plan <plan> or /dev:run <plan>] | [research-ready / blocking question → next research or answer → /dev:plan]`
```text
[plan mode discovery] → /dev:plan → [execution-ready → optional /dev:pm-review <plan> plan → /review:plan <plan> → /review:change-integrate <plan> → /cmd:execute-plan <plan> → choose /run-plan <plan> or /dev:run <plan>] | [research-ready / blocking question → next research or answer → /dev:plan]
```
- Read-only plan mode gathers evidence, resolves `low-confidence` decisions, and prepares inputs for plan materialization.
- `/dev:plan` fails closed: it only writes an `execution-ready` plan when foundational decisions are resolved; otherwise it asks the user or writes exactly one non-ready `research-ready` artifact with the next research action.
- `/dev:pm-review` is the optional corrective PM reshaping pass before execution and may also be used after implementation to reopen missing completion work.
- `/review:plan` is the standard multi-model review pass for plans, and `/review:change-integrate` resolves those inline comments back into the same plan before execution.
- Only `execution-ready` reviewed plans move into `/cmd:execute-plan`; the handoff preserves the reviewed plan argument and asks whether to continue with `/run-plan` or `/dev:run`.
- `/run-plan` is the full lifecycle reviewed-plan continuation through PR creation and monitoring; `/dev:run` remains the direct execution path with one `quality-reviewer` pass after each phase.
- Pi is the only maintained surface that promises context cleanup before dispatch; OpenCode shares the wrapper name and choice flow without claiming Pi-only context behavior.

### Workflow 0B: Linear Issue Build In OpenCode Workspace
`/cmd:linear-build-workspace NOD-123 origin/develop → OpenCode workspace row → enforced run ledger → plan → plan gates → implementation → validation → evidence → code/PM review → PR`
```
/cmd:linear-build-workspace NOD-123 origin/develop
```
- This workflow uses OpenCode workspaces as the build unit, not naked git worktrees, so each Linear build appears in the OpenCode workspace list.
- `create_linear_workspace.py` creates or reuses the workspace row and workspace-backed worktree.
- `linear_build_orchestrator.py` initializes a Markdown run ledger with embedded JSON state, guards stage transitions, records exact artifact verdicts, logs commands, records blockers, and stores manual/native evidence status.
- Agents must not advance after missing or non-passing prior stages; the helper exits non-zero for blocked evidence and blocker records.

### Workflow 1: PRD-Based Development (Fidelity-Preserving)
```
/prd:1:create-prd → /prd:2:gen-tasks → /3:process-tasks → /cmd:commit-push → /cmd:create-pr
```
- Create a PRD for a feature with exact scope preservation
- Generate task list using fidelity-preserving approach
- Process tasks using unified task processor with fidelity agents
- Commit changes and create pull request

### Workflow 2: Specification-Driven Development (Full Fidelity)
```
/spec:1:create-spec → /spec:2:gen-tasks → /3:process-tasks → /cmd:commit-push → /cmd:create-pr
```
- Research and create detailed specification
- Convert specification directly to executable tasks (preserves 100% fidelity)
- Process tasks using unified task processor with fidelity-preserving agents
- Commit and create pull request

### Workflow 3: Code Simplification
```
/simplify:1:create-plan → [Review/Approval] → /simplify:2:process-plan → /cmd:commit-push
```
- Analyze codebase for simplification opportunities
- Get approval for changes from quality-reviewer or stakeholders
- Execute the approved simplification plan
- Commit changes

### Workflow 4: Documentation Management
```
/doc:fetch [library] → [Development] → /doc:update
```
- Fetch library documentation for AI-friendly reference
- Use during development for better context
- Update project documentation after implementation

## Key Features

### Unified Task Processing
The **`/3:process-tasks`** command works for both PRD and spec workflows:
- **Auto-detects** source type (PRD vs specification) from YAML front-matter
- Uses fidelity-preserving agents (developer, quality-reviewer)
- Supports complexity levels (simple/standard/comprehensive) for specs
- Supports both "Relevant Files" (PRD) and "Implementation Files" (spec) sections
- Validates based on source document requirements

### Fidelity-Preserving Approach
All workflow commands follow strict fidelity preservation:
- **Exact Scope Implementation**: Build only what's specified in source documents
- **No Scope Creep**: Zero additions beyond explicit requirements
- **Fidelity Agents**: Always use developer and quality-reviewer
- **Question Ambiguity**: Ask for clarification rather than making assumptions
- **Source Reference**: Constantly reference source document to prevent drift

### Execution-Ready Planning Defaults
Plans and specifications should describe behavioral tests in plain terms around what a user, operator, or agent will be able to do after the work is complete that they could not do before.

- Use TDD where practical: describe tests first, then implement code to make those tests pass.
- If TDD is not appropriate for a phase, the plan should say why.
- A plan is only `execution-ready` when important questions and `low-confidence` foundational decisions are resolved with evidence.
- If research is still the next handoff, `/dev:plan` writes one non-ready `research-ready` artifact instead of pretending execution can safely start.
- `/dev:pm-review <plan> plan` is the optional corrective PM pass before execution; `/dev:pm-review <plan> implementation` is the corrective PM pass after implementation.
- `/review:plan` is the standard plan review pass, and `/review:change-integrate` should clean those inline comments before `/cmd:execute-plan`.
- `/dev:run` applies one `quality-reviewer` pass after each phase. A phase only advances after review receives `VERDICT: PASS_NO_ISSUES`, or `VERDICT: PASS_LOW_RISK_ONLY` with each remaining item proven out-of-scope, low-risk, not required for truthful verification, and logged in `thoughts/discoveries/<plan-or-feature>.md` (or the repo's documented equivalent) plus the plan's `## Decisions / Deviations Log`.
- `/run-plan` can resume from a reviewed plan, keep the plan truthfully aligned with execution, run pre-PR review gates, create the PR, and monitor post-PR feedback.

### Standardized Format
All commands use consistent:
- **Phase Structure**: `Phase N: [Name] (Timeframe)` (optional)
- **Task Format**: `N.0 [Parent]` → `N.1, N.2, N.3 [Sub-tasks]`
- **Commit Messages**: `git commit -m "feat: [summary]" -m "Related to Phase X.Y"`
- **YAML Front-matter**: Metadata tracking for validation and fidelity

## Usage Guidelines

### When to Use Each Command

**`/prd:1:create-prd`**:
- New feature development from scratch
- Clear, scoped requirements needed
- Business stakeholder collaboration
- Need to ask clarifying questions about requirements

**`/prd:2:gen-tasks`**:
- Converting PRDs to actionable development tasks
- Creating task lists that implement only specified requirements
- Using fidelity-preserving approach
- No scope expansion beyond PRD content

**`/spec:1:create-spec`**:
- Research-driven development
- Complex technical implementations
- Architecture-heavy projects
- Collaborative specification creation

**`/spec:2:gen-tasks`**:
- Converting specifications to executable tasks
- Direct conversion with 100% fidelity preservation
- Supports complexity levels (simple/standard/comprehensive)
- Preserves all technical context and rationale
- Should preserve any tests-first / TDD expectations already present in the source document

**`/3:process-tasks`**:
- Process any task list (PRD or spec-based)
- Automatically detects source type
- Uses fidelity-preserving agents
- Requires git branch (not main)
- Supports `NOSUBCONF` flag for autonomous processing
- Implements only what's specified in source documents
- Should implement behavioral tests and TDD steps when they are specified in source documents

**`/doc:fetch` & `/doc:fetch-batch`**:
- Fetch library/framework documentation
- Convert to AI-friendly Markdown format
- Support version-specific docs
- Enable better code suggestions during development

**`/doc:update`**:
- Post-implementation documentation
- Update README, TESTING, CLAUDE.md
- Generated after feature completion
- Uses technical-writer agent

**`/simplify:1:create-plan`** & `/simplify:2:process-plan`**:
- Code complexity reduction
- Technical debt management
- Refactoring legacy systems
- Performance optimization through simplification

**`/cmd:commit-push`**:
- Commit all changes with conventional commit format
- Push to remote repository
- Creates descriptive commit messages

**`/cmd:create-pr`**:
- Create pull request from current branch
- Auto-generates PR description from commits
- Includes test plan and summary

**`/cmd:start-linear-issue`**:
- Bootstrap work on Linear issues with OpenCode workspace management
- Creates/reuses an OpenCode workspace row so the build appears in the workspace picker
- Creates a workspace-backed git worktree and issue branch for isolated development
- Uses Linear CLI for issue metadata

**`/cmd:linear-build-workspace`**:
- Runs the deterministic Linear issue build lifecycle from workspace creation through plan, reviews, implementation, validation, evidence, PR, and Linear handoff
- Uses a durable `thoughts/runs/<issue-slug>.md` ledger as the authoritative orchestration state
- Handles adversity explicitly: test timeouts, native evidence gaps, PR feedback, rebase conflicts, repeated blockers, and unresolved product decisions

## Fidelity-Preserving Agents

### developer
- Implements EXACTLY what's specified in source documents
- Adds NO tests, security, or features beyond specification requirements
- When source documents specify tests-first or TDD behavior, those tests are part of the required implementation scope
- Questions ambiguity rather than making assumptions
- Used by all task processing workflows

### quality-reviewer
- Reviews implementation against specification requirements ONLY
- Does NOT require additional security, testing, or compliance beyond specification
- Validates fidelity preservation and prevents scope creep
- Used by all task processing workflows

## Best Practices

1. **Always work on feature branches** (not main)
2. **One sub-task at a time** unless `NOSUBCONF` specified
3. **Validate before commit** - commands enforce validation based on source requirements
4. **Context preservation** - task lists maintain full context from source documents
5. **Progress tracking** - regular task list updates required (mandatory checkpoint system)
6. **Fidelity first** - constantly reference source documents during implementation

## File Structure

All commands are flat at the root level:
```
commands/
├── 3:process-tasks.md (unified processor)
├── test:run-playwright:all.md
├── test:run-playwright.md
├── prd:1:create-prd.md
├── prd:2:gen-tasks.md
├── spec:1:create-spec.md
├── spec:2:gen-tasks.md
├── doc:fetch.md
├── doc:fetch-batch.md
├── doc:update.md
├── simplify:1:create-plan.md
├── simplify:2:process-plan.md
├── cmd:commit-push.md
├── cmd:create-pr.md
├── cmd:start-linear-issue.md
├── cmd:start-linear-issue-branch.md
├── cmd:review-pr-comments.md
├── cmd:execute-plan.md
├── ralph:review-gpt5.5.md
├── ralph:review-opus.md
└── _lib/ (helper scripts)
```

## File Outputs

All working artifacts are stored in the `thoughts/` directory:

- **PRDs**: `thoughts/plans/prd-[feature-name].md`
- **Specifications**: `thoughts/specs/spec-[idea-name].md`
- **Task Lists**: `thoughts/plans/tasks-[source-name].md`
- **Simplification Plans**: `thoughts/plans/simplify-plan-[target].md`
- **Research Documents**: `thoughts/research/YYYY-MM-DD-[description].md`
- **Discovery Ledgers**: `thoughts/discoveries/[plan-or-feature].md`
- **Handoffs**: `thoughts/handoffs/[TICKET]/YYYY-MM-DD_HH-MM-SS_description.md`
- **Validation Reports**: `thoughts/validation/YYYY-MM-DD-[description].md`
- **Debug Investigations**: `thoughts/debug/YYYY-MM-DD-[description].md`
- **Linear Notes**: `thoughts/linear/[ISSUE-KEY].md`

Completed features are graduated to permanent documentation:
- **spec/architecture/[feature].md**: Feature architecture documents
- **spec/architecture/README.md**: Architecture index table
- **spec/adr-log.md**: Architectural decision records
- **CHANGELOG.md**: Implementation summaries

## Integration Notes

All commands integrate with:
- Git workflow and branching
- Test commands from `TESTING.md` or `CLAUDE.md`
- Conventional commit formatting
- Security and performance validation (only as specified in source documents)
- YAML front-matter for metadata tracking

## Command Naming Convention

Commands use colon-delimited namespacing:
- `prd:[phase]:` - PRD workflow commands (e.g., `prd:1:create-prd`)
- `spec:[phase]:` - Specification workflow commands (e.g., `spec:1:create-spec`)
- `doc:` - Documentation commands
- `test:` - Test orchestration commands
- `simplify:[phase]:` - Code simplification commands (e.g., `simplify:1:create-plan`)
- `cmd:` - Git and utility commands (e.g., `cmd:commit-push`, `cmd:start-linear-issue`)
- `[number]:` - Cross-workflow phase commands (e.g., `3:process-tasks`)

This flat structure ensures compatibility with all AI coding agents that don't traverse subdirectories.
