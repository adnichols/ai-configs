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

## Model routing for this wrapper

Keep GPT-5.6 Sol medium as the normal `/run-plan` parent and code-writing route.

Before delegating code, use `Explore`/`explore` for broad discovery and pass `developer-mid` a bounded packet with target files, intended behavior, relevant evidence, and verification commands. Use `developer-high` only for complex or failed scoped implementation work.
