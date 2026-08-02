---
description: Cold-start delivery tracking in this worktree and continue from the agent brief (for newly spawned Herdr agents)
argument-hint: '[goal text] [--issue KEY] [--slug SLUG] [--plan PATH]'
---

# /delivery:bootstrap

You are likely a newly spawned agent in a Herdr worktree with little or no prior context. Bootstrap the delivery navigator, then continue the real work.

## 1. Bootstrap the ledger + agent brief

From the worktree root, run one of:

```bash
# No Linear yet (common):
delivery bootstrap --slug <short-slug> --goal "$ARGUMENTS"

# Linear known:
delivery bootstrap --issue <KEY> --goal "$ARGUMENTS"

# Existing ledger — refresh brief only:
delivery bootstrap --refresh --goal "$ARGUMENTS"
```

Parse flags out of `$ARGUMENTS` when present (`--issue`, `--slug`, `--plan`, `--stage`). Treat remaining text as `--goal`.

If `delivery` is missing from PATH, use:

```bash
python3 ~/.agents/skills/delivery-run/scripts/delivery bootstrap ...
# or repo checkout:
python3 skills/delivery-run/scripts/delivery bootstrap ...
```

## 2. Read the brief

Read `.delivery/AGENT_BRIEF.md` fully. It is the navigation contract for this worktree.

Also run:

```bash
delivery show
delivery check -v
```

## 3. Continue from recommended next step

Follow the brief's **Recommended next step** by invoking the named existing skill (`reviewed-html-plan`, `run-plan`, `autoreview`, PM review, etc.), except at `EXECUTION_READY`. At that stage, do not invoke `run-plan` or edit product code. Give the operator the approval summary specified in the brief — plan/review status, expected implementation changes, fixed `openai-codex/gpt-5.6-sol` medium profile, and remaining steps — and ask whether to proceed. Record direct approval with `delivery approve-implementation --source chat --summary "..."`; it launches a dedicated pinned Herdr Pi agent. The planning agent stops rather than moving itself to `IMPLEMENTING`.

Rules:

- Doctrine is **guidance, not gates** — never hard-stop only because delivery evidence is missing.
- Linear issue is optional at start; attach later with `delivery set --issue KEY --retarget-id`.
- In `PLAN_BROWSER_REVIEW`, integrate generic feedback and keep listening. Do not enter PM or technical plan review until the operator explicitly requests it through Doct's **Request execution-ready review** action (`agentRoute.requestedSkill: "plan-reviewer-execution-ready"`) or gives an equivalent direct instruction. Record `planReadinessRequest=pass` before advancing.
- `EXECUTION_READY` is eligibility only, not an automatic implementation handoff. It also requires a current independent `planner` verdict recorded with reviewer `planner`, model `openai-codex/gpt-5.6-sol`, reasoning `medium`, and verdict `PLAN_EXECUTION_READY`. If material plan feedback arrives before code work, update the plan, run `delivery revoke-implementation-approval --reason "material plan feedback"`, return to browser review, and require a fresh readiness request and Sol-medium review.
- Only the dedicated implementation agent may enter `IMPLEMENTING`. It must run `delivery verify-implementation-profile`; the stage command checks the live Pi provider/model/reasoning environment. Use `delivery start-implementation` to retry a failed launch.
- At `COMPLETENESS_REVIEW`, run `delivery completion-review`. Read the adjacent visible Pi/Grok 4.5 review, fix every in-plan finding, and issue `delivery completion-review --rerun` until it returns `VERDICT: COMPLETE`; run `delivery completion-review --accept` to capture its response artifact before local merge readiness.
- After each meaningful step: update stage/record, then `delivery bootstrap --refresh` or at least `delivery check -v`.
- Do not reimplement worker skills ad hoc.

## 4. First reply shape

Tell the operator:

1. worktree + ledger id + stage
2. whether issue is attached or still pending
3. recommended next step you are taking now
4. then take that step — except when `EXECUTION_READY`, where the next action is to present the required approval summary and wait for the operator.
