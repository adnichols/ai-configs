---
name: cmd-research
description: Research codebase area without planning commitment. Creates standalone research documents documenting how things work.
---

# Research Codebase

Conduct comprehensive research across the codebase to document how things work. Creates standalone research documents without committing to implementation.

## Usage

```
/skill:cmd-research [area or topic to research]
```

## Critical Rule: Document, Don't Evaluate

Your job is to document the codebase **as it exists today**:
- DO NOT suggest improvements or changes unless explicitly asked
- DO NOT perform root cause analysis unless explicitly asked
- DO NOT propose future enhancements unless explicitly asked
- DO NOT critique the implementation or identify problems
- ONLY describe what exists, where it exists, how it works, and how components interact

## Process

### 1. Read Mentioned Files First

If the user mentions specific files, read them FULLY before spawning sub-tasks to ensure full context.

### 2. Analyze and Decompose

Break down the research question into:
- Components to investigate
- Patterns to find
- Connections to trace
- Directories and files to explore

### 3. Spawn Parallel Research Tasks

Use `subagent` with the `codebase-analyzer` agent to research different aspects concurrently. In Codex, use Codex's native parallel task mechanism when it can preserve the same research shape; when Pi subagent parity is required, delegate the research run to Pi from the same repo/worktree:

```bash
pi -p --approve "/skill:cmd-research <area or topic>"
```

Codex should then read the generated `thoughts/research/...` artifact and continue from that evidence, not duplicate the same discovery work unless a gap is clear.

**Task 1: Find WHERE components live**
- Search for file patterns
- Locate key modules and entry points

**Task 2: Understand HOW code works**
- Read specific implementations
- Trace data flow

**Task 3: Find PATTERNS**
- Look for similar implementations
- Document conventions used

Each task should return specific file:line references.

### 4. Synthesize Findings

Wait for ALL sub-agents to complete, then:
- Compile all findings
- Connect findings across components
- Include specific file paths and line numbers
- Document patterns and architecture

### 5. Generate Research Document

Gather metadata:
```bash
git rev-parse HEAD              # Commit hash
git branch --show-current       # Branch
date -u +"%Y-%m-%dT%H:%M:%SZ"   # Timestamp
```

Create document at: `thoughts/research/YYYY-MM-DD-description.md`

Use this template:

```markdown
---
date: [ISO timestamp]
author: pi
git_commit: [Commit hash]
branch: [Branch name]
repository: [Repository name]
type: research
status: complete
tags: [relevant, tags]
last_updated: [YYYY-MM-DD]
---

# Research: [Topic]

## Research Question
[Original query]

## Summary
[High-level documentation of findings]

## Detailed Findings

### [Component/Area 1]
- Description of what exists
- How it connects to other components
- Current implementation details
- File references: `path/to/file.ts:123`

### [Component/Area 2]
...

## Code References
- `path/to/file.py:123` - Description
- `another/file.ts:45-67` - Description

## Architecture Documentation
[Patterns, conventions, and design found]

## Related Documents
[Links to specs, plans, or other research]

## Open Questions
[Areas needing further investigation]
```

### 6. Present Findings

Present a concise summary:
- Key discoveries
- Important file references
- Open questions
- Ask if follow-up needed

### 7. Handle Follow-ups

If user has follow-up questions:
- Append to same document
- Update `last_updated` in frontmatter
- Add new section: `## Follow-up Research [timestamp]`
- Spawn new sub-agents as needed

## Output Location

`thoughts/research/YYYY-MM-DD-description.md`

This document can later be referenced when creating specs or PRDs if implementation is decided.

## Next Steps

When ready to proceed with implementation, consider:
- `/skill:spec-create-spec` for specification-driven development
- `/skill:dev-plan` for plan materialization
