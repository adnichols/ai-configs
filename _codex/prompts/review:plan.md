---
description: Delegate blocker-focused GPT and Kimi plan review to Pi
argument-hint: '<existing-plan-path | plan slug | legacy inputs>'
---

# Pi-Delegated Plan Review

Codex exposes `/review:plan` for parity with Pi. The canonical workflow runs Pi subagents for the GPT and Kimi review legs, so do not reimplement the multi-model review locally in Codex.

Run from the same repository/worktree:

```bash
pi -p --approve "/review:plan $ARGUMENTS"
```

After Pi exits:

1. Inspect the annotated plan file and any summary Pi produced.
2. Confirm `[REVIEW:GPT]` and `[REVIEW:Kimi K2.5]` comments were inserted when findings exist.
3. Report readiness and direct the user to `/review:change-integrate <plan>` when comments need integration.

If `pi`, either reviewer subagent, or the required model route is unavailable, stop with a tooling blocker instead of substituting a Codex-only plan review.
