# Command Workflow Documentation

## Overview

This directory contains a comprehensive set of commands that support a complete development workflow from requirements to implementation and quality assurance. All commands are at the root level with colon-delimited namespacing.

### Documentation Commands
1. **`doc:fetch.md`** - Fetch documentation for a single library/framework
2. **`doc:fetch-batch.md`** - Batch fetch documentation from markdown lists
3. **`doc:update.md`** - Post-implementation documentation generation

### Test Orchestration Commands
4. **`test:run-playwright.md`** - Run Playwright in PTY, stream failures, and apply scoped fixes directly
5. **`test:run-playwright:all.md`** - Run full Playwright suite (`test:e2e:all`) in PTY with live fixer orchestration

### Simplification Commands
6. **`simplify:1:create-plan.md`** - Generate code simplification plans
7. **`simplify:2:process-plan.md`** - Execute approved simplification plans

### Git Utility Commands
8. **`cmd:commit-push.md`** - Commit all changes and push to GitHub
9. **`cmd:create-pr.md`** - Create a pull request
10. **`cmd:start-linear-issue.md`** - Start work on a Linear issue with branch management
11. **`cmd:start-linear-issue-branch.md`** - Start a Linear issue on a new branch (no worktree) and draft a first-pass plan
12. **`cmd:review-pr-comments.md`** - Review and address GitHub PR comments since last commit

### Autopilot Loop Commands
13. **`run-plan`** - Full lifecycle reviewed-plan execution through PR creation and monitoring
14. **`ralph:review-gpt.md`** - Run `/review` in a loop (GPT-5.6 Sol), apply quick fixes, stop when no straightforward fixes remain
15. **`ralph:review-opus.md`** - Run `/review` in a loop (Opus), apply quick fixes, stop when no straightforward fixes remain

## Command Workflows

### Workflow 1: Code Simplification
```
/simplify:1:create-plan → [Review/Approval] → /simplify:2:process-plan → /cmd:commit-push
```
- Analyze codebase for simplification opportunities
- Review the plan directly and obtain stakeholder approval
- Execute the approved simplification plan
- Commit changes

### Workflow 2: Documentation Management
```
/doc:fetch [library] → [Development] → /doc:update
```
- Fetch library documentation for AI-friendly reference
- Use during development for better context
- Update project documentation after implementation

## Key Features

### Standardized Format
All commands use consistent:
- **Phase Structure**: `Phase N: [Name] (Timeframe)` (optional)
- **Task Format**: `N.0 [Parent]` → `N.1, N.2, N.3 [Sub-tasks]`
- **Commit Messages**: `git commit -m "feat: [summary]" -m "Related to Phase X.Y"`
- **YAML Front-matter**: Metadata tracking for validation and fidelity

## Usage Guidelines

### When to Use Each Command

**`/doc:fetch` & `/doc:fetch-batch`**:
- Fetch library/framework documentation
- Convert to AI-friendly Markdown format
- Support version-specific docs
- Enable better code suggestions during development

**`/doc:update`**:
- Post-implementation documentation
- Update README, TESTING, CLAUDE.md
- Generated after feature completion
- Updates documentation directly in the driving session

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
- Bootstrap work on Linear issues with worktree management
- Creates dedicated branch and worktree for isolated development
- Copies local config and MCP servers
- Uses Linear CLI for issue metadata

## Claude Execution Model

The driving session performs discovery, planning, implementation, testing, documentation, and ordinary review directly. The repository-owned `reviewer` subagent is the only exception: it may perform bounded, read-only plan and code reviews at `claude-sonnet-5` high effort.

When policy requires an independent Claude review, use this `reviewer` subagent rather than an external Codex or Claude session or a required Herdr workflow.

## Best Practices

1. **Always work on feature branches** (not main)
2. **Validate before commit** - commands enforce validation based on source requirements
3. **Context preservation** - task lists maintain full context from source documents
4. **Progress tracking** - regular task list updates required (mandatory checkpoint system)

## File Structure

All commands are flat at the root level:
```
commands/
├── test:run-playwright:all.md
├── test:run-playwright.md
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
├── ralph:review-gpt.md
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
- `doc:` - Documentation commands
- `test:` - Test orchestration commands
- `simplify:[phase]:` - Code simplification commands (e.g., `simplify:1:create-plan`)
- `cmd:` - Git and utility commands (e.g., `cmd:commit-push`, `cmd:start-linear-issue`)

This flat structure ensures compatibility with all AI coding agents that don't traverse subdirectories.
