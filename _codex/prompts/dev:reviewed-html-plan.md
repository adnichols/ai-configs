---
description: Create/register an HTML plan and run PM plus GPT/GLM Pi subagent plan reviews until execution-ready
argument-hint: '<plan description | slug | thoughts/plans/<slug>.html | issue key>'
---

# Pi-Delegated Command

Codex exposes this prompt for parity with Pi, but the underlying workflow depends on Pi prompt templates, Pi subagents, or Pi-managed model routing. Do not reimplement it locally in Codex. Delegate to Pi from the same repository/worktree.

Run:

```bash
pi -p --approve "/dev:reviewed-html-plan $ARGUMENTS"
```

After Pi exits:

1. Inspect the files or artifacts Pi reports it changed or created.
2. Verify the expected plan/review/status artifact exists when this command promises one.
3. Summarize Pi's result and any blocker.

If `pi` is unavailable, the prompt template is missing, or a required Pi subagent/model fails, stop with a tooling blocker instead of substituting a Codex-only review.
