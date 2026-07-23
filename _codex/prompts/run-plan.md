---
description: Execute an explicit plan through the full run-plan lifecycle
argument-hint: '<plan slug | existing-plan-path>'
model: openai/gpt-5.6-sol
model_reasoning_effort: medium
---

# Run Plan

Invoke the installed `run-plan` skill with exactly this argument:

```text
$ARGUMENTS
```

This wrapper is only the ergonomic `/run-plan` entry point. Do not run a shortened workflow here. Follow the `run-plan` skill so scoped implementation, verification, Codex plus applicable Claude Code pre-PR review, PR creation, and post-PR monitoring all stay in the single source of truth.

Run the skill's startup supervisor step (step 0): attach a trajectory-guarding supervisor per `skills/supervise/SKILL.md` in an adjacent Herdr pane, or record `SUPERVISOR: none — <reason>` in the plan's expansion log. Clear the two blocking checkpoints — plan-ready before implementation and pre-PR before push — with the correlated-id handshake, and send fire-and-forget `PHASE COMPLETE` pings at phase boundaries.
