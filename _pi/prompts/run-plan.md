---
description: Execute an explicit plan through the full run-plan lifecycle
argument-hint: '<plan slug | existing-plan-path>'
---

# Run Plan

Invoke the installed `run-plan` skill with exactly this argument:

```text
$ARGUMENTS
```

This wrapper is only the ergonomic `/run-plan` entry point. Do not run a shortened workflow here. Follow the `run-plan` skill so scoped implementation, verification, durable Pi goal tracking, GPT/GLM pre-PR review, PR creation, current PR feedback snapshot, and local merge-readiness consensus all stay in the single source of truth. Do not wait for a Codex thumbs-up or external approval once local review-agent consensus is clean.

## Model routing for this wrapper

Keep GPT-5.5 medium as the normal `/run-plan` parent and code-writing route. For planning/orchestration-heavy, review-synthesis-heavy, UI-design-heavy, or long test/debug-loop runs, use one explicit scoped GLM path instead of changing the global default:

1. The operator may switch the active Pi scoped model to `opencode/glm-5.2` before invoking this wrapper.
2. A GPT-5.5 default parent may delegate a bounded planning/orchestration packet to `orchestrator-glm`.

Before delegating code, use `Explore`/`explore` for broad discovery and pass `developer-mid` a bounded packet with target files, intended behavior, relevant evidence, and verification commands. Use `developer-high` only for complex or failed scoped implementation work, and use `ui-design-glm` for UI design direction or UI/UX review.
