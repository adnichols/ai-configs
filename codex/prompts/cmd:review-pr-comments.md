---
description: Review and address PR comments since last commit
argument-hint: ""
---

# Review PR Comments

Process recent PR comments, verify them, track as a todo list, and implement fixes.

## Process

### 1. Identify Context
1.  **Get Branch & PR**:
    *   Get the current branch name: `git rev-parse --abbrev-ref HEAD`
    *   Find the associated PR: `gh pr list --head [branch] --json number,title,body,url`
2.  **Get Timestamp**:
    *   Get the timestamp of the last local commit: `git log -1 --format=%cI`

### 2. Fetch & Filter Comments
1.  Fetch comments and reviews for the PR:
    ```bash
    gh pr view [number] --json comments,reviews
    ```
2.  Filter for comments created **after** the last commit timestamp.
    *   Include top-level comments and review comments.
    *   Ignore comments made by CI/CD bots (e.g., github-actions), but **include** comments from reviewer agents (specifically 'claude' or 'github-actions[bot]' if it's a linter report).

### 3. Triage & Task List Creation
1.  **Analyze**: Read the referenced code and the comment for each filtered item.
2.  **Draft Tasks**: Identify distinct actionable tasks.
3.  **Create Todos**:
    *   Use the `TodoWrite` tool to populate the session's todo list with all identified tasks.
    *   **Content**: Brief description of the fix needed (e.g., "Fix typo in auth.ts", "Refactor user validation").
    *   **Priority**: 'high' for bugs/blockers, 'medium' for suggestions, 'low' for nits.
    *   **Status**: 'pending'.

### 4. Resolution Loop
For each item in the todo list:
1.  **Claim**: Update the specific todo item status to `in_progress`.
2.  **Plan**: Analyze the specific file and issue.
3.  **Implement**: specific code changes.
4.  **Verify**: Run relevant tests or linters.
5.  **Complete**: Update the todo item status to `completed`.
6.  **Next**: Move to the next pending item.

## Output
- Use the `TodoWrite` tool to keep the user informed of progress.
