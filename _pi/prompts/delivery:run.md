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
- in `PLAN_BROWSER_REVIEW`, generic feedback only updates the plan; wait for Doct's explicit **Request execution-ready review** action (`agentRoute.requestedSkill: "plan-reviewer-execution-ready"`) before PM or technical plan review, then record `planReadinessRequest=pass`. Run the independent `planner` subagent with its checked-in `openai-codex/gpt-5.6-sol` medium profile and record its `PLAN_EXECUTION_READY` artifact with `delivery record planTech ...`. `delivery` binds both records to the current plan and refuses `EXECUTION_READY` without them.
- in `EXECUTION_READY`, pause before product-code work. Summarize plan/review status, expected changes, the fixed implementation profile (`openai-codex/gpt-5.6-sol`, medium), and remaining steps; then ask the operator whether to proceed. Only after direct approval, run `delivery approve-implementation --source chat --summary "..."`. That command launches and prompts a dedicated pinned Herdr Pi agent; the planning agent must not implement. The new agent runs `delivery verify-implementation-profile`, enters `IMPLEMENTING`, and invokes run-plan. These readiness, review, handoff, and implementation-profile requirements are the exceptions to delivery's otherwise advisory evidence.
- before local merge readiness in a Herdr delivery worktree, set `COMPLETENESS_REVIEW`, run `delivery completion-review`, read the adjacent visible Pi session on `xai/grok-4.5:high`, fix in-plan findings, and run `delivery completion-review --rerun` until `VERDICT: COMPLETE`. After that verdict, run `delivery completion-review --accept` to capture the artifact and validate the plan/worktree fingerprint. This visible plan-completeness loop complements, not replaces, `$autoreview`.
