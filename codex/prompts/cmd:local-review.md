---
description: Isolated code review in separate worktree
argument-hint: "[username:branch]"
---

# Local Code Review

Create an isolated worktree for reviewing a colleague's branch. This keeps review context separate from your main development work.

Branch to review: $ARGUMENTS

Format: `username:branchname` or just `branchname`

## Process

### 1. Parse Input

Extract from argument:
- Remote name (default: `origin`)
- Branch name
- Create short name for worktree

Example: `colleague:feature-auth` → remote `colleague`, branch `feature-auth`

### 2. Verify Prerequisites

```bash
# Ensure clean working tree
git status --porcelain=v1

# Fetch latest refs
git fetch --all --prune
```

If working tree is dirty, stop and ask user to commit or stash.

### 3. Create Worktree

Compute paths:
```bash
# Get repo root and parent
REPO_ROOT=$(git rev-parse --show-toplevel)
REPO_NAME=$(basename "$REPO_ROOT")
REPO_PARENT=$(dirname "$REPO_ROOT")

# Create worktree path outside repo
WORKTREE_PATH="$REPO_PARENT/${REPO_NAME}-review-${BRANCH_SHORT}"
```

Create worktree:
```bash
git worktree add "$WORKTREE_PATH" "origin/$BRANCH_NAME"
```

### 4. Copy Local Configuration

Copy ignored config files to worktree:
- `.env*` files
- `.envrc`
- `.claude/mcp-servers.json` (if exists)

```bash
# Find and copy ignored config files
for file in .env .env.local .env.development .envrc; do
    if [ -f "$file" ] && git check-ignore -q "$file" 2>/dev/null; then
        cp "$file" "$WORKTREE_PATH/"
    fi
done

# Copy Claude config if exists
if [ -d ".claude" ]; then
    mkdir -p "$WORKTREE_PATH/.claude"
    cp -r .claude/mcp-servers.json "$WORKTREE_PATH/.claude/" 2>/dev/null
fi
```

### 5. Create Review Notes

Create `thoughts/prs/review-YYYY-MM-DD-branch.md` in the worktree:

```markdown
---
date: [ISO timestamp]
reviewer: [claude]
branch: [branch name]
type: code-review
status: in_progress
---

# Code Review: [Branch Name]

## Review Context
- **Branch**: [branch name]
- **Author**: [if known]
- **Worktree**: [worktree path]

## Changes Overview
[Summary of what the PR/branch does]

## Files Changed
[List of modified files from `git diff --stat main...HEAD`]

## Review Findings

### [File 1]
- Line XX: [Finding]
- Line YY: [Finding]

### [File 2]
...

## Summary

### Strengths
- [Positive aspects]

### Concerns
- [Issues or questions]

### Suggestions
- [Optional improvements]

## Verdict
[Approve / Request Changes / Comment]
```

### 6. Switch Context

Change working directory to worktree:
```bash
cd "$WORKTREE_PATH"
```

### 7. Present Review Setup

Print ready-state checklist:

```
Review Environment Ready
========================

Worktree: [path]
Branch: [branch name]
Base: [main/master]

Config files copied:
  ✓ .env
  ✓ .claude/mcp-servers.json

To see changes:
  git diff main...HEAD
  git log main...HEAD --oneline

Review notes at:
  thoughts/prs/review-YYYY-MM-DD-branch.md

When done, clean up with:
  git worktree remove [worktree-path]
```

## After Review

When review is complete:
1. Update review notes with findings
2. Return to main repo
3. Clean up worktree: `git worktree remove [path]`

## Guidelines

- Keep review isolated from main development
- Copy necessary config files for testing
- Document findings in review notes
- Clean up worktree after review

## Output

- Worktree created at: `../[repo]-review-[branch]/`
- Review notes at: `thoughts/prs/review-YYYY-MM-DD-[branch].md`
