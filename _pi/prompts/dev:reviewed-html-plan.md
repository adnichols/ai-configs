---
description: Create/register an HTML plan, process browser feedback, run PM plus Codex and applicable Claude Code plan reviews, and iterate until execution-ready
argument-hint: '<plan description | slug | thoughts/plans/<slug>.html | issue key>'
---

# Reviewed HTML Plan

Run the reviewed HTML plan workflow for: `$ARGUMENTS`

Use the `reviewed-html-plan` skill as the source of truth for this command.

## Contract

- Create or update one semantic HTML plan under `thoughts/plans/<slug>.html`.
- Follow repo `AGENTS.md`, product-intent docs, `planning-workflow`, and `doct-document-ops`.
- Register the HTML plan in Doct with `doct-agent plans register`, parse the returned `listenerInstructions`, set lifecycle active, leave the plan in its registration/default board column for browser-review handoff, drain pending comments with `agent next --no-wait`, and start `listenerInstructions.listenerCommand` (`doct-agent plans listen ... --jsonl`) in the harness background-process tool before asking for browser feedback. Do not use `agent next --wait` as the default listener.
- If browser feedback has not been provided yet, stop after registration with the monitor running and ask the user to annotate the plan before continuing.
- When feedback is ready, process listener-delivered or manually claimed Doct plan comments/actions, ack/resolve/release with the returned commands, keep the listener running, and update the same HTML plan.
- Run a PM product-intent/stage-fit review and reshape the plan directly when repo evidence supports the correction.
- Run read-only Codex and applicable Claude Code plan reviews, then iterate plan edits and rerun all applicable reviewers until they agree by substance that the plan is execution-ready.
- Do not start implementation or edit product code in this command.

## Final output

Report the plan path, review URL, completed gates, material review-driven changes, final readiness status, and the explicit execution handoff command only if the plan is execution-ready.
