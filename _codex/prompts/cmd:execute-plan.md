---
description: Execute a specified plan through the authorized completion boundary.
argument-hint: '<plan path | slug> [--target run-plan|dev:run]'
---

Execute the plan in $ARGUMENTS using the Codex run-plan skill. Resolve an explicit path or an unambiguous repository-defined slug and inspect the plan's readiness, constraints, and unfinished phases.

Preserve the user's authorization:

- `--target run-plan` requests the implementation-through-PR lifecycle.
- The legacy `--target dev:run` means execution through local verification only. It does not invoke a retired prompt.
- Without a target, honor an already specified completion boundary; otherwise execute through local verification only. Do not add commit, push, PR, merge, or deployment authority.

Choose routine implementation details from the plan and repository evidence. Ask only when the target is ambiguous or an unresolved decision changes the promised behavior. Continue through the authorized outcome and report verification or the concrete blocker.
