---
description: Show delivery ledger status or the cross-worktree delivery board
argument-hint: '[--all|--board]'
---

# /delivery:status

Show delivery progress using the installed `delivery` CLI and `delivery-run` skill doctrine (guidance, not gates).

If `$ARGUMENTS` contains `board` or `--all`, run:

```bash
delivery board
```

Otherwise, in the current worktree:

```bash
delivery status
delivery check -v
```

Summarize stage, next recommended skill, advisories, blockers, plan/PR links, and any completion/customer-impact gaps. Do not hard-block on missing recommended evidence.
