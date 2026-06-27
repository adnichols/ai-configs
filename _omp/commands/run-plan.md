---
description: Execute an explicit plan through the full run-plan lifecycle
argument-hint: '<plan slug | existing-plan-path>'
---

# Run Plan

Use the installed shared `run-plan` workflow from `~/.agents/skills/run-plan/SKILL.md` with exactly this argument:

```text
$ARGUMENTS
```

This wrapper is only the ergonomic `/run-plan` entry point. Do not run a shortened workflow here. Follow the global shared `run-plan` skill so scoped implementation, verification, implementation review, PR creation, and post-PR monitoring all stay in the single source of truth. If that shared skill is unavailable, stop and tell the operator to run `install.sh --skills`.
