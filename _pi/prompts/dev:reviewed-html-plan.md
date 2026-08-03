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
- Only after that request, run a PM product-intent/stage-fit review and reshape the plan directly when repo evidence supports the correction.
- Only after that request, run the read-only `planner` subagent. Its checked-in frontmatter pins `openai-codex/gpt-5.6-sol` at medium; do not override model or reasoning. Iterate plan edits and rerun the planner until it returns `PLAN_EXECUTION_READY` plus an implementation profile and rationale. Select `deepseek-flash` when deterministic tests strongly validate the meaningful behavior; select `sol-medium` when that behavior is hard to validate or technically critical. Record the planTech evidence, profile, and rationale when delivery-managed.
- Do not start implementation or edit product code in this command.
- When the plan becomes execution-ready, keep the listener active and pause. Give the operator the current plan/review status, a concise description of the customer-visible and technical changes implementation will make, the planner-selected implementation profile and rationale (`opencode/deepseek-v4-flash` max normally; `openai-codex/gpt-5.6-sol` medium for hard-to-validate/critical work), and the remaining implementation/test/review/verification/PR steps. Ask whether to proceed. Execution-ready is not authorization to invoke `run-plan`; a direct operator approval is required first. In delivery, `approve-implementation` launches the dedicated agent using the recommendation by default; deliberate manual model/reasoning overrides are allowed when recorded with a reason, and the planning agent stops. If the plan changes after approval, return it to browser review and require a fresh explicit execution-ready request.

## Final output

Report the plan path, review URL, completed gates, material review-driven changes, and final readiness status. If the plan is execution-ready, provide the operator-approval summary and ask whether to proceed; do not give an automatic execution handoff command.
