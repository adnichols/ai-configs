---
description: Research codebase area without planning commitment
argument-hint: "[area or topic to research]"
---

# Research Codebase

Conduct comprehensive research across the codebase to document how things work. This command creates standalone research documents without committing to implementation.

Research topic: $ARGUMENTS

## Critical Rule: Document, Don't Evaluate

Your job is to document the codebase **as it exists today**:
- DO NOT suggest improvements or changes unless explicitly asked
- DO NOT perform root cause analysis unless explicitly asked
- DO NOT propose future enhancements unless explicitly asked
- DO NOT critique the implementation or identify problems
- ONLY describe what exists, where it exists, how it works, and how components interact

## Process

### 1. Read Mentioned Files First

If the user mentions specific files:
- Read them fully before broader research
- This ensures full context before decomposing the question

### 2. Analyze and Decompose

Break down the research question into:
- Components to investigate
- Patterns to find
- Connections to trace
- Directories and files to explore

Create a research plan using `todowrite`.

### 3. Research Directly

Use native Glob, Grep, Read, and read-only shell commands in the driving session. Organize the investigation into focused passes:

- Find where components live and identify key entry points.
- Read implementations and trace data flow.
- Find comparable patterns and document conventions.

Capture specific file and line references as evidence. Parallelize independent native tool calls when useful, but do not invoke Claude subagents.

### 4. Synthesize Findings

After the focused passes:
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
author: [Your name or "claude"]
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
- Perform any additional focused research directly

## Guidelines

- Use native tools directly; Claude has no subagent research path
- Focus on concrete file paths and line numbers
- Document cross-component connections
- Research documents should be self-contained
- Keep the driving session responsible for both evidence and synthesis
- Document patterns and usage as they exist

## Output Location

`thoughts/research/YYYY-MM-DD-description.md`

This document can later be referenced by `/dev:1:create-spec` or `/dev:0:create-prd` if implementation is decided.

---

## ➡️ Next Command

When ready to proceed with implementation, run:
```
/dev:1:create-spec
```
