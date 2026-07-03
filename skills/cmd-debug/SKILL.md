---
name: cmd-debug
description: Context-preserving investigation for debugging. Uses parallel subagents to gather evidence while preserving working context.
---

# Debug Investigation

Investigate issues without burning main context. Uses parallel subagents to gather evidence while preserving your working context.

## Usage

```
/skill:cmd-debug [issue description or ticket]
```

## Process

### 1. Understand the Issue

Parse the provided context:
- Error messages or symptoms
- Affected components
- Recent changes
- Steps to reproduce (if known)

### 2. Launch Parallel Investigations

Spawn subagents with `debugger` to investigate different aspects concurrently. In Codex, use Codex's native parallel task mechanism when it can preserve the same evidence-gathering shape; when Pi subagent parity is required, delegate the investigation to Pi from the same repo/worktree:

```bash
pi -p --approve "/skill:cmd-debug <issue description>"
```

Codex should then read the generated `thoughts/debug/...` artifact and continue from the evidence, not redo the same searches unless a gap is clear.

**Agent 1: Recent Changes**
```
Investigate recent git changes that might relate to [issue].
- Check git log for relevant commits
- Look for changes to affected files
- Identify when issue might have been introduced
Return: Timeline of relevant changes with file:line references
```

**Agent 2: Code Analysis**
```
Analyze the code paths related to [issue].
- Trace execution flow
- Identify potential failure points
- Look for error handling gaps
Return: Code analysis with specific file:line references
```

**Agent 3: Configuration/Environment**
```
Check configuration and environment factors.
- Look for relevant config files
- Check for environment variable usage
- Identify external dependencies
Return: Configuration findings relevant to the issue
```

**Agent 4: Test Coverage** (if applicable)
```
Check test coverage for affected code.
- Find existing tests for the component
- Identify gaps in test coverage
- Look for failing tests
Return: Test analysis with file:line references
```

### 3. Gather Additional Evidence

If applicable, run commands to gather more context:

```bash
# Check git status
git status
git log --oneline -10

# Check for error patterns (adjust grep pattern as needed)
grep -r "error_message_pattern" --include="*.py" --include="*.ts" --include="*.js" .
```

### 4. Synthesize Findings

Wait for all agents to complete, then compile:
- Root cause hypothesis
- Evidence supporting hypothesis
- Related code paths
- Potential fixes

### 5. User Engagement for Hypothesis Selection

When multiple viable hypotheses exist, ask the user before deep-diving into a fix.

Present options clearly:
- Hypothesis A: [description] - likely if [condition]
- Hypothesis B: [description] - likely if [condition]
- Investigate both in parallel
- Share more evidence first

### 6. Generate Debug Document

Create `thoughts/debug/YYYY-MM-DD-[description].md`:

```markdown
---
date: [timestamp]
issue: [brief description]
type: debug
status: [investigating|resolved|needs-user-input]
---

# Debug: [Issue Title]

## Symptoms
[What was observed]

## Investigation Timeline
[Steps taken with timestamps]

## Evidence Gathered

### Recent Changes
[Git commits that might be relevant]

### Code Analysis
[File:line references to relevant code]

### Configuration Findings
[Environment/config factors]

## Root Cause Hypothesis
[Most likely explanation with evidence]

## Potential Fixes
[Options for resolution]

## Next Steps
[Recommended action]
```

### 7. Recommend Fix (if clear)

If root cause is clear and fix is straightforward:
- Recommend specific fix
- Provide code reference
- Suggest verification steps

If root cause unclear:
- Ask clarifying questions
- Suggest additional logging/instrumentation
- Propose hypothesis testing approach

## Output

- Debug document at `thoughts/debug/YYYY-MM-DD-[description].md`
- Summary of findings
- Recommended next steps
