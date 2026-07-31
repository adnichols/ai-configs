---
description: Guide a worktree through plan ↔ review → run-plan → autoreview → PR using the delivery ledger (guidance, not gates)
argument-hint: '[issue-key | plan-path | plan-slug]'
---

# /delivery:run

Invoke the installed `delivery-run` skill with:

```text
$ARGUMENTS
```

Keep the per-worktree delivery ledger current while calling existing worker skills. Doctrine is **guidance, not gates**:

- use `delivery init/show/stage/record/check/board`
- treat `delivery check` advisories as a to-do list, never a hard stop
- do not reimplement `reviewed-html-plan`, `run-plan`, `autoreview`, PM review, or `qa:run`
- missing recommended evidence is recorded as gap/pending and work may continue
