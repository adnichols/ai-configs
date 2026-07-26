---
name: pi-workflow-orchestration
description: Manage Pi development workflows from Hermes chat with high fidelity. Treat Pi workflow documents and prompts as authoritative; orchestrate the same flow without redesigning artifacts.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [pi, workflow, orchestration, planning, review, execution]
    related_skills: [plan, writing-plans, systematic-debugging]
---

# Pi Workflow Orchestration

Use this skill when the user wants Hermes to execute a Pi development workflow through chat.

## Core rule

The Pi workflow documents are the authority.

Do **not** redesign:
- plan shape
- review protocol
- execution handoff
- artifact names
- readiness states
- workflow ordering

Your job is to manage the workflow faithfully.

## Primary sources of truth

Read these first when present:
- `_pi/dever-dev-workflow/README.remote.md`
- `_pi/dever-dev-workflow/prompts/*.md`
- `_pi/dever-dev-workflow/agents/*.md`
- `_pi/dever-dev-workflow/extensions/*`

Prefer the prompt docs for exact per-step behavior and the README for canonical sequencing.

## Canonical reviewed-plan flow

From `README.remote.md`, preserve this sequence unless the user explicitly asks for a different path:

1. `/dev:plan <plan>`
2. `/dev:pm-review <plan> plan` (optional corrective PM reshaping pass)
3. `/review:plan <plan>`
4. `/review:change-integrate <plan>`
5. `/review:plan-adversarial <plan>` (optional)
6. `/cmd:execute-plan <plan>`

Execution handoff then chooses between:
- `/dev:run <plan>`
- `/ralph:run <plan>`

## What Hermes should do

When standing in for Pi, emulate the same workflow with Hermes tools:

### Planning
- Read the exact Pi planning prompt or extension-defined plan mode behavior.
- Write/update the plan artifact in the workflow’s required format.
- Do not substitute a different structure.

### Review
- Run the review step(s) defined by Pi.
- If Pi says review is comment-only, keep it comment-only.
- If Pi requires integrating review comments before execution, perform that integration step explicitly.

### Execution
- Respect the Pi execution mode distinction:
  - `dev:run` = direct execution with one active-harness `reviewer` subagent pass after each phase
  - `ralph:run` = quality-gated repeated review/fix loops after each phase
- Continue autonomously unless truly blocked.

### Validation
- If the workflow defines a post-implementation validation step, run it.
- Treat validation as separate from implementation when the Pi prompt does.

## Fresh-session semantics

If Pi docs describe a fresh-session handoff, preserve that intent as closely as Hermes allows:
- summarize the authoritative artifact
- delegate cleanly with only the needed context
- avoid leaking planning-mode assumptions into implementation

## Ask the user only when
- the Pi docs leave a material decision unresolved,
- multiple valid execution modes exist and Pi expects an explicit choice,
- or a blocker changes external behavior / risk materially.

Otherwise proceed.

## Anti-patterns

Do not:
- translate Pi into a nicer generic Hermes framework
- replace Pi’s plan artifact with your preferred template
- skip required review/integration steps
- collapse distinct Pi steps into one because it feels simpler
- introduce new workflow states not present in Pi docs
- stop after a resumable checkpoint if Pi intends continuous execution

## Minimal operating procedure

1. Read README + exact prompt doc(s) for the requested stage.
2. Identify current stage in the Pi workflow.
3. Execute that stage faithfully.
4. Advance to the next Pi-defined stage.
5. Repeat until complete or truly blocked.

## Output style

Be brief and operational:
- say what stage you are executing,
- what artifact or review gate you updated,
- and what stage comes next.

Do not explain a replacement methodology unless the user explicitly asks for one.
