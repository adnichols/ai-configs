---
description: Arm the delivery workflow for this worktree (single entrypoint)
argument-hint: '[--from existing-implementation] [plan-path]'
---

# /delivery

This is the in-session command to arm delivery. `/prewalk`, `/run-plan`,
`execute`, and generic implementation never create a ledger. After a
non-delivery implementation, a request to run completeness, PM review, or
pre-PR is late-attach authorization even when they did not invoke this
command by name. Do the arm below. Do not ask them to recite a phrase.

1. If `/prewalk` is still armed, stop. They are mutually exclusive. Tell the
   operator to `/prewalk off` first, or keep prewalk and do not arm delivery.
2. If `.delivery/ledger.json` already exists, delivery is already armed.
   Continue from `delivery show`. Do not create a second ledger.
3. If the operator is attaching after a non-delivery implementation (review,
   completeness, and PR only):

```bash
delivery arm --from existing-implementation --plan <plan-path>
```

   Do not launch an implementation pane. Start at review.

4. Otherwise (early arm):

```bash
delivery arm --plan <plan-path>
```

Parse `--from existing-implementation` and a plan path out of `$ARGUMENTS`.
Then load `skill://delivery-run` and continue from the recommended next step.

`delivery spawn` / `/delivery:spawn` is the new-worktree form of this same arm.
