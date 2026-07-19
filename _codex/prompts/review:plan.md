---
description: Delegate blocker-focused GPT plan review to Pi
argument-hint: '<existing-plan-path | plan slug | legacy inputs>'
---

# Pi-Delegated Plan Review

Codex exposes `/review:plan` for parity with Pi. The canonical workflow runs the repository-owned GPT plan reviewer through Pi, so do not reimplement the review locally in Codex.

Run from the same repository/worktree:

```bash
pi -p --approve "/review:plan $ARGUMENTS"
```

After Pi exits:

1. Inspect the annotated plan file and any summary Pi produced.
2. Confirm `[REVIEW:GPT]` comments were inserted when findings exist.
3. Report readiness and direct the user to `/review:change-integrate <plan>` when comments need integration.

If `pi` or the GPT reviewer subagent is unavailable, stop with a tooling blocker instead of substituting a Codex-only plan review.
