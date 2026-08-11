---
description: Create/register an HTML plan, process browser feedback, run PM plus the independent Sol-medium planner subagent review, and iterate until execution-ready
argument-hint: '<plan description | slug | thoughts/plans/<slug>.html | issue key>'
---

# Reviewed HTML Plan

Run the reviewed HTML plan workflow for: `$ARGUMENTS`

Use the `reviewed-html-plan` skill as the source of truth for this command.

## Contract

- Create or update one semantic HTML plan under `thoughts/plans/<slug>.html`.
- Follow repo `AGENTS.md`, product-intent docs, `planning-workflow`, and `doct-document-ops`; keep conditional planning evidence proportional to the task.
- Register the HTML plan in Doct with `doct-agent plans register --title '<Plan Title>'` (title required; match `<title>`/`<h1>` or Markdoc frontmatter `title:`), parse the returned `listenerInstructions`, set lifecycle active, leave the plan in its registration/default board column for browser-review handoff, drain pending comments with `agent next --no-wait`, and start `listenerInstructions.listenerCommand` (`doct-agent plans listen ... --jsonl`) in the harness background-process tool before asking for browser feedback. Do not use `agent next --wait` as the default listener. Never hand off a browser-review draft titled **Untitled Plan**.
- If browser feedback has not been provided yet, stop after registration with the monitor running and ask the user to annotate the plan before continuing.
- Process listener-delivered or manually claimed Doct plan comments/actions, ack/resolve/release with the returned commands, keep the listener running, and update the same HTML plan. A generic routed `submitAction: "agent"` comment without `agentRoute.requestedSkill` is feedback only; it must not start readiness review.
- Wait for an explicit execution-ready request before PM or technical readiness review: Doct's **Request execution-ready review** action currently emits `agentRoute.requestedSkill: "plan-reviewer-execution-ready"`; accept `submitAction: "execution-ready"` when returned by the service, or an equivalent direct operator instruction. Do not infer a request from the first feedback comment or a quiet listener.
- During plan authoring or revision, load `oracle-consultation` and invoke Oracle proactively when targeted evidence leaves a consequential technical choice or conflict with locked decisions unresolved. Oracle cannot make product choices, authorize scope expansion, or replace any readiness gate.
- Only after that request, run a PM product-intent/stage-fit review and reshape the plan directly when repo evidence supports the correction.
- Only after that request, run the read-only `planner` subagent. An earlier Oracle consultation does not satisfy this independent readiness gate. Its checked-in frontmatter pins `openai-codex/gpt-5.6-sol` at medium; do not override model or reasoning. Iterate plan edits and rerun the planner until it returns `PLAN_EXECUTION_READY` plus an implementation profile and rationale. Select `luna-xhigh` by default; select `terra-high` when correctness depends materially on technical judgment. Escalate unresolved consequential choices to Oracle rather than selecting Sol for implementation. Record the planTech evidence, profile, and rationale when delivery-managed.
- Do not start implementation or edit product code in this command.
- When the plan becomes execution-ready in a delivery-managed worktree, run `delivery stage EXECUTION_READY`. That transition automatically authorizes the exact reviewed plan, launches the dedicated planner-selected implementation agent (`openai-codex/gpt-5.6-luna` xhigh by default; `openai-codex/gpt-5.6-terra` high for judgment-heavy work), and continues through implementation, verification, review, and PR creation without another routine approval pause. The planning agent stops after handoff. Use `--hold` only for an explicit operator-requested pause or a real external dependency. For planning-only use without a delivery ledger, stop at the execution-ready plan. If material feedback changes the plan before code work, revoke authorization, return to browser review, and require a fresh explicit execution-ready request.

## Final output

Report the plan path, review URL, completed gates, material review-driven changes, and final readiness status. For a delivery-managed run, report the automatically launched implementation profile and handoff state; for planning-only use, state that no implementation was started.
