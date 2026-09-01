---
description: Cold-start delivery tracking in this worktree and continue from the agent brief (for newly spawned Herdr agents)
argument-hint: '[goal text] [--issue KEY] [--slug SLUG] [--plan PATH]'
---

# /delivery:bootstrap

This command does **not** arm delivery from a generic session. If `.delivery/ledger.json`
is missing and the operator did not spawn or `/delivery` this worktree, stop.
Do not invent a ledger for run-plan, prewalk, or execute.

You are likely a newly spawned agent in a Herdr worktree with little or no prior context. Refresh the delivery navigator, then continue the real work.

## 1. Refresh the ledger + agent brief

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

Read `.delivery/AGENT_BRIEF.md` fully when present. It is a generated navigator, not a hard prerequisite. If absent, continue from `delivery show`, the ledger, and the plan; optionally recreate it with `delivery bootstrap --refresh`.

Also run:

```bash
delivery show
delivery check -v
```

## 3. Continue from recommended next step

Follow the brief's **Recommended next step** by invoking the named existing skill (`reviewed-html-plan`, `run-plan`, `autoreview`, PM review, etc.). After the explicit readiness request and clean PM/Sol planner reviews, run `delivery stage EXECUTION_READY`; it automatically authorizes the exact reviewed plan and launches a dedicated Herdr Pi agent on the selected profile (GPT-5.6 Luna at xhigh by default; Terra high for judgment-heavy correctness). Do not ask for another routine approval and do not implement in the planning agent. Use `--hold` only for an explicit operator-requested pause or a real external dependency. The implementation agent verifies its runtime, enters `IMPLEMENTING`, and continues through PR creation.

Rules:

- Doctrine is **guidance, not gates** — never hard-stop only because delivery evidence is missing.
- Linear issue is optional at start; attach later with `delivery set --issue KEY --retarget-id`.
- In `PLAN_BROWSER_REVIEW`, integrate generic feedback and keep listening. Do not enter PM or technical plan review until the operator explicitly requests it through Doct's **Request execution-ready review** action (`agentRoute.requestedSkill: "plan-reviewer-execution-ready"`) or gives an equivalent direct instruction. Record `planReadinessRequest=pass` before advancing.
- `EXECUTION_READY` requires a current independent `planner` verdict recorded with reviewer `planner`, model `openai-codex/gpt-5.6-sol`, reasoning `medium`, verdict `PLAN_EXECUTION_READY`, and the implementation profile/rationale decision. Prefer `luna-xhigh` by default; use `terra-high` when correctness depends materially on technical judgment. Escalate unresolved consequential choices to Oracle rather than selecting Sol for implementation. In a delivery-managed Herdr run, entering the stage is the automatic implementation handoff unless `--hold` was explicitly requested. If material plan feedback arrives before code work, update the plan, run `delivery revoke-implementation-approval --reason "material plan feedback"`, return to browser review, and require a fresh readiness request and independent Sol-medium planner review.
- Only the dedicated implementation pane may enter `IMPLEMENTING`. It must run `delivery verify-implementation-profile`; the stage command checks the live Pi provider/model/reasoning environment against the recorded profile. The recommendation is not a prohibition: if the same recorded pane was deliberately switched to another model, use `delivery verify-implementation-profile --adopt-current-runtime --reason "..."`. Use `delivery start-implementation` only to retry an actual failed launch. A missing `.delivery/AGENT_BRIEF.md` is advisory; continue from the ledger and plan or recreate it with `delivery bootstrap --refresh`.
- Completeness is on-request. If the operator asked for a plan walk, at `COMPLETENESS_REVIEW` run `delivery completion-review`, read the visible labeled Pi/Grok 4.5 tab, fix in-plan findings, `--rerun` until `VERDICT: COMPLETE`, then `--accept`. Skip this when they did not ask; it does not block merge readiness.
- After each meaningful step: update stage/record, then `delivery bootstrap --refresh` or at least `delivery check -v`.
- Do not reimplement worker skills ad hoc.

## 4. First reply shape

Tell the operator:

1. worktree + ledger id + stage
2. whether issue is attached or still pending
3. recommended next step you are taking now
4. then take that step; at `EXECUTION_READY`, report the automatically launched implementation profile and handoff state rather than waiting for routine approval.
