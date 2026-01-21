---
description: Review and address PR comments since last commit
argument-hint: "[epic-id] [severity]"
---

# Review PR Comments

Process recent PR comments, verify them, track as issues, and implement fixes.

## Process

### 1. Identify Context
1.  **Check Arguments**: Check if an Epic ID (e.g., `doct-bx3`) was provided as a command argument.
2.  **Get Branch & PR**:
    *   Get the current branch name: `git rev-parse --abbrev-ref HEAD`
    *   Find the associated PR: `gh pr list --head [branch] --json number,title,body,url`
3.  **Determine Epic ID**:
    *   If provided in args, use it.
    *   If not, extract from PR body (look for "Epic: [ID]" or similar).
    *   If not found, ask the user.
4.  **Verify Epic**:
    *   Run `beads show [Epic ID] --brief` to confirm it exists and check its status.
    *   If the status is `closed`, run `beads reopen [Epic ID]` to ensure new child issues can be properly tracked.
    *   **STOP**: Do not run further commands to explore the epic or its other tasks. You only need the ID to parent new issues.
5.  **Get Timestamp**:
    *   Get the timestamp of the last local commit: `git log -1 --format=%cI`

### 2. Fetch & Filter Comments
1.  Fetch comments and reviews for the PR:
    ```bash
    gh pr view [number] --json comments,reviews
    ```
2.  Filter for comments created **after** the last commit timestamp.
    *   Include top-level comments and review comments.
    *   Ignore comments made by CI/CD bots (e.g., github-actions, railway-app), but **include** comments from reviewer agents (specifically 'claude').

### 3. Triage & Verification
For each filtered comment:
1.  **Analyze**: Read the referenced code and the comment.
2.  **Verify**: Determine if the issue is legitimate.
    *   If not legitimate, note why (but maybe don't create an issue, or create one and close it as "wontfix").
3.  **Create Issue**: If legitimate, create a `beads` issue.
    *   **Title**: Summary of the feedback.
    *   **Description**: Full comment text + link to comment + technical details of the fix.
    *   **Type**: `bug` or `task` (depending on nature).
    *   **Parent**: IMMEDIATELY link the new issue to the Epic ID.
        *   Use `beads_dep` tool.
        *   `issue_id`: The ID of the issue you just created.
        *   `depends_on_id`: The Epic ID.
        *   `dep_type`: "parent-child".
    *   **Severity**: Assess severity (P0-P3).

### 4. Severity Selection
1.  Check if `severity` was provided in the command prompt.
2.  If not provided, list the created issues grouped by severity and ask the user which severity level to process (e.g., "P1", "P2", "all").

### 5. Resolution Loop
For each issue matching the selected severity (sorted by priority):
1.  **Claim**: Update issue status to `in_progress`.
2.  **Plan**: strict analysis of the problem.
3.  **Implement**: specific code changes.
4.  **Verify**: Run relevant tests.
5.  **Close**: Mark the `beads` issue as `closed` (reason: `completed`).
6.  **Next**: Move to the next issue.

## Output
- List of new issues created.
- Summary of fixes applied.
- Status of remaining issues.
