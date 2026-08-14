---
description: Cold-start delivery tracking in this worktree and continue from the agent brief (for newly spawned Herdr agents)
argument-hint: '[goal text] [--issue KEY] [--slug SLUG] [--plan PATH]'
---

# /delivery:bootstrap

This command does **not** arm delivery from a generic session. If `.delivery/ledger.json`
is missing and the operator did not spawn or `delivery arm` this worktree, stop.
Do not invent a ledger for run-plan, prewalk, or execute.

You are likely a newly spawned agent in a Herdr worktree with little or no prior context. Refresh the delivery navigator, then continue the real work:

```bash
delivery show
delivery check -v
```

Track the goal text and any `--issue` / `--slug` / `--plan` in `$ARGUMENTS` against the ledger; do not create a ledger if one is absent. If `.delivery/AGENT_BRIEF.md` exists, read it and continue from the recommended next step through plan ↔ review → run-plan → autoreview → PR.
