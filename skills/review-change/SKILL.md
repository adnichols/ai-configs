---
name: review-change
description: Review code changes with quality-reviewer agents. Checks for issues, security, data loss, and performance with measurable impact focus; escalates to adversarial review when PR feedback shows earlier reviews missed issues.
---

# Review Change

Review code changes using quality-reviewer agents. Checks for real issues (security, data loss, regressions, performance) with measurable impact focus.

## Usage

```
/skill:review-change [optional: specific files or scope]
```

## Process

### 1. Determine Review Scope

If no arguments provided, review all changes since the base branch.

```bash
# Get changed files
git diff --name-only origin/main...HEAD
# Or use origin/develop if that's the base
```

### 2. Choose Review Posture

Default to normal quality review. Switch to adversarial review when PR feedback, especially Codex PR feedback, found actionable issues after a previous local review had already passed. That feedback is a signal the prior review was not thorough enough.

In adversarial posture:
- review the full current PR diff, not just the commented file
- start from the escaped feedback and search for sibling failures, repeated assumptions, partial fixes, missing tests, and analogous callsites
- keep the search scope-bound to the current change and its acceptance criteria
- do not turn the pass into unrelated whole-product cleanup

Regardless of posture, every reviewer must also run these checks on the first pass — not only after an escape:
- generic key-name matching/remapping/rewriting where the key name may not uniquely determine the value's type or target (test non-target variants: numbers, booleans, objects, unrelated strings)
- fail-closed/bail paths reachable by valid, schema-conformant input (failing closed on valid input is a real failure, not a safe deferral)
- producer/consumer and round-trip parity (import vs export, encode vs decode, rewrite vs collect)
When one instance is found, enumerate siblings (other call sites, other shapes, the inverse direction of the boundary) and report the family, not just the first instance.

### 3. Spawn Quality Reviewers

Use `subagent` with `quality-reviewer` agent:

**Reviewer 1: Security & Data Loss**
```
Review changed files for:
- Security vulnerabilities (injection, exposure, auth gaps)
- Data loss risks (deletions without backup, migration issues)
- Input validation gaps
Return: Specific issues with file:line references and severity
```

**Reviewer 2: Performance & Correctness**
```
Review changed files for:
- Performance issues (N+1 queries, unnecessary loops)
- Logic errors or edge cases
- Error handling gaps
Return: Specific issues with file:line references and severity
```

**Reviewer 3: Architecture & Maintainability**
```
Review changed files for:
- Code duplication
- SOLID principle violations
- API contract consistency
Return: Specific issues with file:line references
```

When running adversarial posture, include this extra instruction in each reviewer prompt:

```text
This is an adversarial follow-up because PR feedback found issues after earlier review passed. Do not merely validate the direct fix. Look for additional missed issues in the same failure family across the current diff and plan-bound surfaces.
```

### 4. Synthesize Results

Compile findings into categories:
- **Critical**: Must fix (security, data loss, crashes)
- **Important**: Should fix (performance, correctness)
- **Minor**: Nice to have (style, minor optimizations)

### 5. Generate Review Report

Create `thoughts/validation/YYYY-MM-DD-review-[branch].md`:

```markdown
---
date: [timestamp]
branch: [branch name]
commit: [HEAD commit]
type: review
status: complete
---

# Code Review: [Branch/Scope]

## Summary
- Files reviewed: [N]
- Issues found: [N critical, N important, N minor]
- Overall: [pass/needs-work]

## Critical Issues

### [Issue 1 Title]
- **Location**: `file:line`
- **Problem**: [description]
- **Impact**: [specific consequence]
- **Fix**: [recommended change]

## Important Issues
[Similar format]

## Minor Issues
[Similar format]

## Positive Findings
[What was done well]

## Action Items
- [ ] Fix critical issue 1
- [ ] Fix critical issue 2
- [ ] Consider important issues
```

Include whether the review used normal or adversarial posture, and if adversarial, the escaped feedback that triggered it.

### 6. Present to User

Summarize findings:
- Number of issues by severity
- Most critical issues requiring immediate attention
- Recommendation (approve / fix required)

If issues found, offer to:
- Create fix tasks
- Run `/skill:review-change-integrate` to address issues

## Integration

Pairs with:
- `/skill:review-change-integrate` to apply fixes
- Your preferred git workflow after fixes
- Can be used after `adn-dev-wf` or as a standalone code-review workflow
