# OpenCode-backed PR feedback fix cycle

Use when Aaron asks to check/fix feedback on an existing PR whose branch was produced by an OpenCode workflow.

## NOD-654 observed pattern

1. Gather every feedback surface before deciding there is no work:
   - `gh pr view <N> --json number,url,title,state,reviewDecision,mergeable,headRefName,headRefOid,comments,reviews,statusCheckRollup`
   - `gh api repos/<owner>/<repo>/pulls/<N>/comments --paginate`
   - `gh api repos/<owner>/<repo>/issues/<N>/comments --paginate`
   - `gh api repos/<owner>/<repo>/pulls/<N>/reviews --paginate`
   - GraphQL `reviewThreads` for `id` + `isResolved`; REST inline comments do not expose resolution state.
2. Route code/test remediation through the active implementer (OpenCode for OpenCode workflows), not Hermes direct edits. Give OpenCode exact thread text, paths/lines, and require a `/tmp/<slug>-pr-feedback-fix-validation.md` artifact with a first-line verdict such as `PR_FEEDBACK_FIXED`.
3. Verify the OpenCode diff and artifact, then commit and push from the PR worktree.
4. Reply to each inline thread with commit SHA and validation evidence, then resolve the thread through GraphQL.
5. Add a top-level PR comment only after the branch is pushed so the SHA is visible on GitHub.
6. Re-query `reviewThreads` and require `unresolved == []` before reporting done.
7. Re-check PR metadata and checks. `gh pr checks` may exit 1 with `no checks reported`; treat that as informational no-CI state, not a failed check.

## Pitfalls

- `gh pr view` can show only the review shell/body and omit actionable inline comments. Always query pull comments and review threads.
- A pushed fix can make a thread outdated while still unresolved. Do not confuse outdated with resolved.
- If OpenCode also updates an existing plan/handoff artifact while validating, inspect and either commit that intentional documentation update or route cleanup through OpenCode before final status.
- For Aaron's macOS GitHub auth, use `HOME=/Users/anichols zsh -lc '<gh/git command>'` when direct `gh`/push cannot see credentials.
