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

Supervision is opt-in. Do **not** launch a supervisor for `/run-plan` unless the operator explicitly asks for supervision; in that case, follow `skills/supervise/SKILL.md`.
