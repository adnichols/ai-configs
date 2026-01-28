# Command Workflow Documentation

## Overview

This directory contains a comprehensive set of commands that support a complete development workflow from requirements to implementation and quality assurance. All commands are at the root level with colon-delimited namespacing.

## Antigravity (Global Workflows)

To use these commands as Antigravity `/...` workflows, generate global workflow wrappers:

```bash
python3 opencode/scripts/sync_antigravity_workflows.py
```

This writes workflows to `~/.gemini/antigravity/global_workflows/` using safer names:

- Command `cmd:research.md` becomes Antigravity workflow `/oc-cmd-research`
- `:` is replaced with `-` and all workflows are prefixed with `oc-` to avoid collisions

Restart Antigravity after syncing so it reloads the global workflows.

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

### Simplification Commands
9. **`simplify:1:create-plan.md`** - Generate code simplification plans
10. **`simplify:2:process-plan.md`** - Execute approved simplification plans

### Git Utility Commands
11. **`cmd:commit-push.md`** - Commit all changes and push to GitHub
12. **`cmd:create-pr.md`** - Create a pull request
13. **`cmd:start-linear-issue.md`** - Start work on a Linear issue with branch management
14. **`cmd:review-pr-comments.md`** - Review and address GitHub PR comments since last commit

## Command Workflows

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

**`/3:process-tasks`**:
- Process any task list (PRD or spec-based)
- Automatically detects source type
- Uses fidelity-preserving agents
- Requires git branch (not main)
- Supports `NOSUBCONF` flag for autonomous processing
- Implements only what's specified in source documents

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
- Bootstrap work on Linear issues with worktree management
- Creates dedicated branch and worktree for isolated development
- Copies local config and MCP servers
- Uses Linear CLI for issue metadata

## Fidelity-Preserving Agents

### developer
- Implements EXACTLY what's specified in source documents
- Adds NO tests, security, or features beyond specification requirements
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
├── cmd:review-pr-comments.md
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
- `prd:[phase]:` - PRD workflow commands (e.g., `prd:1:create-prd`)
- `spec:[phase]:` - Specification workflow commands (e.g., `spec:1:create-spec`)
- `doc:` - Documentation commands
- `simplify:[phase]:` - Code simplification commands (e.g., `simplify:1:create-plan`)
- `cmd:` - Git and utility commands (e.g., `cmd:commit-push`, `cmd:start-linear-issue`)
- `[number]:` - Cross-workflow phase commands (e.g., `3:process-tasks`)

This flat structure ensures compatibility with all AI coding agents that don't traverse subdirectories.
