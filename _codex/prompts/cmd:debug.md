---
description: Context-preserving investigation for debugging
argument-hint: "[issue description or ticket]"
---

# Debug Investigation

Investigate issues directly in the driving session so evidence, hypotheses, and conclusions stay connected. Read-only helpers are optional, not the default.

## Input

Issue description or ticket: $ARGUMENTS

Issue context: $ARGUMENTS

## Process

### 1. Understand the Issue

Parse the provided context:
- Error messages or symptoms
- Affected components
- Recent changes
- Steps to reproduce (if known)

### 2. Investigate Directly

Use direct repository tools to gather evidence in this order:

1. Inspect recent changes and relevant history.
2. Trace the affected code path and failure boundary.
3. Check configuration, environment, and external dependency assumptions.
4. Locate existing tests and reproduce the failure when safe.

Keep one evidence ledger with exact file:line and command-output references. Use a read-only helper only for one bounded evidence question when direct targeted search is insufficient; never delegate diagnosis or fixes.

### 3. Gather Additional Evidence

If applicable, run commands to gather more context:

```bash
# Check recent logs (if log files exist)
# Check git status
git status
git log --oneline -10

# Check for error patterns
# (grep for error messages in codebase)
```

### 4. Synthesize Findings

Wait for all agents to complete, then compile:
- Root cause hypothesis
- Evidence supporting hypothesis
- Related code paths
- Potential fixes

### 4.5. User Engagement for Hypothesis Selection

When multiple viable hypotheses exist, use **`question`** to engage the user before deep-diving into a fix.

**Trade-off Questions (when hypotheses have different implications):**
```
Question: "I've identified [N] possible root causes. Which should I investigate first?"
Header: "Root cause"
Options:
- Hypothesis A: [description] - likely if [condition]
- Hypothesis B: [description] - likely if [condition]
- Investigate both directly before choosing
- Let me share more evidence first
```

**Validation Questions (confirm understanding before proceeding):**
```
Question: "Based on evidence, I believe the issue is [X]. Does this match what you're seeing?"
Header: "Validate"
Options:
- Yes, that matches the symptoms
- Partially - but also seeing [Y]
- No, the issue is different than that
```

**Scope Questions (clarify investigation depth):**
```
Question: "Should I focus on [quick fix] or [thorough investigation]?"
Header: "Approach"
Options:
- Quick fix - get it working, investigate later
- Thorough - understand root cause fully first
- Both - quick fix now, then investigate
```

**When to Engage:**
- Multiple hypotheses have similar confidence levels
- Evidence is ambiguous or incomplete
- The fix approach depends on user priorities (speed vs thoroughness)
- Investigation would require significant time/resources

**When to Proceed Without Asking:**
- Single clear hypothesis with strong evidence (high confidence)
- User already indicated preference for investigation depth
- Issue is straightforward with obvious fix

### 5. Generate Debug Report

Create document at: `thoughts/debug/YYYY-MM-DD-description.md`

```markdown
---
date: [ISO timestamp]
author: [claude]
git_commit: [Commit hash]
branch: [Branch name]
type: debug
status: [investigating|resolved|blocked]
---

# Debug Investigation: [Issue Title]

## Issue Summary
[Brief description of the problem]

## Symptoms
- [Observed behavior 1]
- [Observed behavior 2]

## Investigation Findings

### Recent Changes Analysis
[Findings from git history investigation]
- Relevant commits: [list]
- Potentially related changes: [file:line references]

### Code Path Analysis
[Findings from code analysis]
- Entry points: [file:line]
- Failure points: [file:line]
- Error handling gaps: [file:line]

### Configuration/Environment
[Findings from config investigation]
- Relevant configs: [file paths]
- Environment factors: [list]

### Test Coverage
[Findings from test analysis]
- Existing tests: [file paths]
- Coverage gaps: [areas]
- Failing tests: [if any]

## Root Cause Hypothesis

**Most Likely Cause:**
[Description of probable root cause]

**Evidence:**
- [Supporting evidence 1]
- [Supporting evidence 2]

**Confidence:** [High/Medium/Low]

## Potential Fixes

### Option 1: [Fix Title]
- Change: [Description]
- Files: [file:line references]
- Risk: [Assessment]

### Option 2: [Fix Title]
...

## Blockers

[If investigation is blocked, list what's needed]
- Need access to: [resource]
- Need user to: [action]

## Next Steps

1. [Recommended action]
2. [Follow-up action]

## Related Code
- `path/to/file.ts:123` - [Description]
- `another/file.ts:45` - [Description]
```

### 6. Present Findings

Present to user:
- Root cause hypothesis with confidence level
- Key evidence
- Recommended fixes with risk assessment
- Any blockers requiring user input

## Guidelines

- Keep the investigation in the driving session; use bounded read-only helpers only when direct search is insufficient
- Focus on gathering evidence, not making changes
- Return specific file:line references
- Present hypotheses with confidence levels
- Identify blockers that need user input

## Output

Report saved to: `thoughts/debug/YYYY-MM-DD-[issue-description].md`
