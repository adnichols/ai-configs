---
description: Execute an explicit plan through the full run-plan lifecycle
argument-hint: '<plan slug | existing-plan-path>'
---

# Run Plan

Invoke the installed `run-plan` skill with exactly this argument:

```text
$ARGUMENTS
```

This wrapper is only the ergonomic `/run-plan` entry point. Do not run a shortened workflow here. Follow the `run-plan` skill so scoped implementation, verification, durable Pi goal tracking, active-harness reviewer-subagent pre-PR review, base freshness, PR creation, current PR feedback snapshot, and local merge-readiness consensus all stay in the single source of truth. Do not wait for external approval once local review-agent consensus is clean.

Supervision is opt-in. Do **not** launch a supervisor for `/run-plan` unless the operator explicitly asks for supervision; in that case, follow `skills/supervise/SKILL.md`.

## Model routing for this wrapper

Keep GPT-5.6 Luna xhigh as the normal `/run-plan` parent and code-writing route. Use GPT-5.6 Terra high when correctness depends materially on technical judgment; unresolved consequential choices can escalate to Oracle rather than routing implementation through Sol.

Perform implementation directly in the driving session with native repository tools. Prefer direct targeted inspection before editing; use `scout` only for bounded read-only discovery when broad isolated evidence gathering materially helps. Do not delegate code edits, test changes, fixes, verification, or repository management to a subagent or developer persona.
