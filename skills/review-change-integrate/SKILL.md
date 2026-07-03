---
name: review-change-integrate
description: Apply fixes from review findings. Works with review-change output to address issues systematically, including adversarial follow-up when PR feedback reveals a missed-review issue.
---

# Review Change - Integrate Fixes

Apply fixes based on review findings from `/skill:review-change`. Addresses issues systematically.

## Usage

```
/skill:review-change-integrate [review-file-path]
```

If no review file provided, looks for most recent review in `thoughts/validation/`.

## Process

### 1. Load Review Findings

If review file provided:
```bash
# Read the review file
cat [review-file-path]
```

Otherwise find most recent:
```bash
ls -t thoughts/validation/*.md | head -1
```

### 2. Prioritize Issues

Sort issues by:
1. **Critical** (security, data loss, crashes)
2. **Important** (performance, correctness)
3. **Minor** (style, optimizations)

### 3. Create Fix Plan

Generate task list from issues:

```markdown
## Fix Tasks

### Critical
- [ ] Fix [issue description] in `file:line`
- [ ] Fix [issue description] in `file:line`

### Important
- [ ] Fix [issue description] in `file:line`

### Minor (optional)
- [ ] Fix [issue description] in `file:line`
```

### 4. Execute Fixes

For each critical/important issue:

1. **Read** the affected code fully
2. **Understand** the problem from review
3. **Implement** the fix
4. **Verify** with appropriate tests/commands

Use `subagent` with `developer` agent for parallel fixes when safe. In Codex, use native scoped editing for fixes; if the integration step requires Pi subagent parity, delegate only the implementation slice to Pi with an explicit bounded prompt and verify the actual diff before proceeding.

If the review findings came from Codex PR feedback after a previous local review passed, treat it as a review escape. After the direct fix, run an adversarial follow-up review before declaring the issue resolved:

- inspect the full PR diff for sibling instances and related failure modes
- run `/skill:review-change` in adversarial posture or `codex-review-partner --mode adversarial-implementation-review`
- fix any new in-scope findings, not just the original comment
- document true out-of-scope findings with evidence and a tracking destination

### 5. Update Review Status

After addressing issues:

```markdown
---
date: [original timestamp]
updated: [current timestamp]
branch: [branch name]
type: review
status: [resolved|partially-resolved]
---

# Code Review: [Branch/Scope]

## Original Findings
[Link to original or summary]

## Resolution Status

### Critical Issues
- [x] [Issue 1] - Fixed in commit [sha]
- [x] [Issue 2] - Fixed in commit [sha]

### Important Issues
- [x] [Issue 3] - Fixed in commit [sha]
- [ ] [Issue 4] - Documented out of scope: [reason and tracking destination]

## Summary
[What was fixed, what remains, any trade-offs made]
```

### 6. Report Results

- Issues fixed vs documented out-of-scope follow-ups
- Commits created
- Recommendation for next review

## Safety Guidelines

- Only fix issues you fully understand
- When in doubt, ask the user
- Run tests after each critical fix
- Commit incrementally for easy rollback

## Integration

Part of the review workflow:
1. `/skill:review-change` - Find issues
2. `/skill:review-change-integrate` - Fix issues
3. Commit or share the fixes using your preferred git workflow
