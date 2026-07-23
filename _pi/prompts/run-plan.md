---
description: Execute an explicit plan through the full run-plan lifecycle
argument-hint: '<plan slug | existing-plan-path>'
---

# Run Plan

Invoke the installed `run-plan` skill with exactly this argument:

```text
$ARGUMENTS
```

This wrapper is only the ergonomic `/run-plan` entry point. Do not run a shortened workflow here. Follow the `run-plan` skill so scoped implementation, verification, durable Pi goal tracking, Codex plus applicable Claude Code pre-PR review, PR creation, current PR feedback snapshot, and local merge-readiness consensus all stay in the single source of truth. Do not wait for a Codex thumbs-up or external approval once local review-agent consensus is clean.

Run the skill's startup supervisor step (step 0): attach a trajectory-guarding supervisor per `skills/supervise/SKILL.md` in an adjacent Herdr pane, or record `SUPERVISOR: none — <reason>` in the plan's expansion log. Clear the two blocking checkpoints — plan-ready before implementation and pre-PR before push — with the correlated-id handshake, and send fire-and-forget `PHASE COMPLETE` pings at phase boundaries.

## Model routing for this wrapper

Keep GPT-5.6 Sol medium as the normal `/run-plan` parent and code-writing route.

Perform implementation directly in the driving session with native repository tools. Prefer direct targeted inspection before editing; use `scout` only for bounded read-only discovery when broad isolated evidence gathering materially helps. Do not delegate code edits, test changes, fixes, verification, or repository management to a subagent or developer persona.
