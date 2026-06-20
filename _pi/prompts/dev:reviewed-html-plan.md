---
description: Create/register an HTML plan, process browser feedback, run PM plus GPT/GLM Pi subagent plan reviews, and iterate until execution-ready
argument-hint: '<plan description | slug | thoughts/plans/<slug>.html | issue key>'
---

# Reviewed HTML Plan

Run the reviewed HTML plan workflow for: `$ARGUMENTS`

Use the `reviewed-html-plan` skill as the source of truth for this command.

## Contract

- Create or update one semantic HTML plan under `thoughts/plans/<slug>.html`.
- Follow repo `AGENTS.md`, product-intent docs, `planning-workflow`, and `html-plan-reviewer`.
- Register the HTML plan in the local `plan-review` tool with required execution-readiness metadata, parse returned `agentInstructions`, share the canonical review URL, drain pending comments, and start the queue-backed `agent next --wait` monitor in the harness background-process tool.
- If browser feedback has not been provided yet, stop after registration with the monitor running and ask the user to annotate the plan before continuing.
- When feedback is ready, claim/process/ack/resolve plan-review comments and update the same HTML plan.
- Run a PM product-intent/stage-fit review and reshape the plan directly when repo evidence supports the correction.
- Run read-only GPT and GLM Pi subagent plan reviews, then iterate plan edits and rerun both reviewers until both agree by substance that the plan is execution-ready.
- Do not start implementation or edit product code in this command.

## Final output

Report the plan path, review URL, completed gates, material review-driven changes, final readiness status, and the explicit execution handoff command only if the plan is execution-ready.
