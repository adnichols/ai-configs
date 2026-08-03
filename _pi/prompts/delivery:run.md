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
- keep the read-only `oracle` subagent available as advisory decision support across planning, implementation, review, and recovery. Invoke it once when targeted evidence leaves a consequential technical choice or drift from locked decisions genuinely ambiguous; verify its claims and record the accepted or rejected disposition. It never replaces product decisions or required review gates.
- do not reimplement `reviewed-html-plan`, `run-plan`, `autoreview`, PM review, or `qa:run`
- missing recommended evidence is recorded as gap/pending and work may continue
- in `PLAN_BROWSER_REVIEW`, generic feedback only updates the plan; wait for Doct's explicit **Request execution-ready review** action (`agentRoute.requestedSkill: "plan-reviewer-execution-ready"`) before PM or technical plan review, then record `planReadinessRequest=pass`. Run the independent `planner` subagent with its checked-in `openai-codex/gpt-5.6-sol` medium profile. It returns `PLAN_EXECUTION_READY` plus an implementation choice: `terra-high` when deterministic tests strongly validate the work, or `sol-medium` when meaningful correctness is hard to validate or technically critical. Record the artifact, profile, and rationale with `delivery record planTech ...`. `delivery` binds both records to the current plan and refuses `EXECUTION_READY` without them.
- after the explicit readiness request and clean PM/Sol reviews, run `delivery stage EXECUTION_READY`. In Herdr that transition automatically authorizes the exact reviewed plan, launches and prompts a dedicated Pi agent using the planner recommendation—normally `openai-codex/gpt-5.6-terra` high, or `openai-codex/gpt-5.6-sol` medium for hard-to-validate/critical work—and continues toward PR creation without another routine approval pause. The planning agent must not implement. Use `--hold` only for an explicit operator-requested pause or real external dependency. The new agent runs `delivery verify-implementation-profile`, enters `IMPLEMENTING`, and invokes run-plan. If the recorded implementation pane was deliberately switched to another model, record that choice with `delivery verify-implementation-profile --adopt-current-runtime --reason "..."`. These readiness, review, handoff, and implementation-profile requirements are the exceptions to delivery's otherwise advisory evidence.
- before local merge readiness in a Herdr delivery worktree, set `COMPLETENESS_REVIEW`, run `delivery completion-review`, read the visible labeled Pi tab on `xai/grok-4.5:high`, fix in-plan findings, and run `delivery completion-review --rerun` until `VERDICT: COMPLETE`. After that verdict, run `delivery completion-review --accept` to capture the artifact and validate the plan/worktree fingerprint. This visible plan-completeness loop complements, not replaces, `$autoreview`.
