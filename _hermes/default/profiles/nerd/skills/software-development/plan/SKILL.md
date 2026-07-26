---
name: plan
description: Plan mode for Hermes — inspect context, write a markdown plan into the active workspace's `.hermes/plans/` directory, and do not execute the work.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [planning, plan-mode, implementation, workflow]
    related_skills: [writing-plans]
---

# Plan Mode

Use this skill when the user wants a plan instead of execution.

## Core behavior

For this turn, you are planning only.

- Do not implement code.
- Do not edit project files except the plan markdown file.
- Do not run mutating terminal commands, commit, push, or perform external actions.
- You may inspect the repo or other context with read-only commands/tools when needed.
- Your deliverable is a markdown plan saved inside the active workspace under `.hermes/plans/`.

## Output requirements

Write the plan in the format required by the active project/workflow.

If the repository or workflow bundle already defines the planning artifact shape, sections, readiness criteria, review flow, or handoff format, treat those artifacts as authoritative. Do not invent a replacement format.

Your job in plan mode is to:
- inspect context,
- follow the repo/workflow-defined planning contract,
- write or update the required plan artifact at the requested path,
- and ask a brief clarifying question only when the workflow cannot proceed without one.

For every implementation plan, put a standalone product-owner context section near the top, before implementation history, current-code detail, tasks, or verification mechanics. Assume the reader has no prior issue, Linear, incident, or repository context. Explain the situation in plain language, explain why the work is needed now, and state the key conclusion unmistakably—especially whether this is a customer/runtime defect, a stale test or evidence problem, an operational/documentation gap, or a combination. Separately cover `Customers`, `Runtime product behavior`, `Security / permissions`, `Testing / release confidence`, and `Deployment / migration`, saying `No change` or `Not applicable` for unaffected dimensions. Lightweight plans must use at least concise labeled prose; non-trivial plans require a scannable impact table or equivalent structured block. Preserve any required dark full-width HTML layout, Decision Attention, TDD/BDD, readiness, and Doct listener contracts.
Follow the shared `planning-workflow` `What's new` contract after Product-owner context and before Goal; require a distinct audience-visible product delta, not a heading or restatement.
When discovery finds an exact untyped contract or distributed production behavior, follow the shared `planning-workflow` integration-integrity planning contract: add the Contract and distributed-integration inventory with source-search evidence, or record `None identified, based on <source search>` when neither trigger applies.

If the task is code-related, include exact file paths, likely test targets, and verification steps when the active workflow expects them.

## Save location

Save the plan with `write_file` under:
- `.hermes/plans/YYYY-MM-DD_HHMMSS-<slug>.md`

Treat that as relative to the active working directory / backend workspace. Hermes file tools are backend-aware, so using this relative path keeps the plan with the workspace on local, docker, ssh, modal, and daytona backends.

If the runtime provides a specific target path, use that exact path.
If not, create a sensible timestamped filename yourself under `.hermes/plans/`.

## Interaction style

- If the request is clear enough, write the plan directly.
- If no explicit instruction accompanies `/plan`, infer the task from the current conversation context.
- If it is genuinely underspecified, ask a brief clarifying question instead of guessing.
- After saving the plan, reply briefly with what you planned and the saved path.
