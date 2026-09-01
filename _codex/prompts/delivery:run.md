---
description: Guide a worktree through plan ↔ review → run-plan → autoreview → PR using the delivery ledger (guidance, not gates)
argument-hint: '[issue-key | plan-path | plan-slug]'
---

# /delivery:run

This command does **not** arm delivery. If `.delivery/ledger.json` is missing
and the operator asked for completeness, PM review, or pre-PR after
implementation, late-attach with `delivery arm --from existing-implementation`
and continue. Otherwise tell them to `/delivery` or `delivery arm`. Do not require a spoken phrase.
Do not run `delivery init` or `delivery bootstrap` to create a ledger.

If a ledger already exists, load the installed `delivery-run` skill
(`skills/delivery-run/SKILL.md`) and operate the shared delivery state machine
for the issue/plan/slug in `$ARGUMENTS`.

Keep the per-worktree delivery ledger current while calling existing worker skills:
`run-plan`, `reviewed-html-plan`, `autoreview`, PM review, `qa:run`. Doctrine is
**guidance, not gates**:

- use `delivery init/show/stage/record/check/board`
- treat `delivery check` advisories as a to-do list, never a hard stop
- load `oracle-consultation` and invoke Oracle proactively when targeted evidence leaves a consequential technical choice or drift from locked decisions unresolved; it never replaces product decisions or required review gates
- do not reimplement `reviewed-html-plan`, `run-plan`, `autoreview`, PM review, or `qa:run`
- missing recommended evidence is recorded as gap/pending and work may continue
- the ledger's recorded runtime profile governs implementation-pane launch and completeness; follow it exactly and record any deliberate model/reasoning override with a reason

Completeness is on-request. Do not block local merge readiness on a missing completeness artifact. Reflect at the end.
