---
name: plan-reviewer-build
description: Respond to Doct/plan-reviewer Build Plan comments by executing an explicit execution-ready plan through the run-plan workflow. Use when a registered Doct plan comment says to use plan-reviewer-build or asks to build a registered plan path.
---

# Plan Reviewer Build

Use this skill when a registered Doct plan browser action comment, usually delivered by the durable `doct-agent plans listen` dispatcher, asks the listening agent to build an explicit plan path.

Doct only requests and tracks the action through `doct-agent plans`. The listener process should dispatch the claim payload and returned commands to this worker; this worker should not replace or stop the listener. The implementation workflow is delegated to `run-plan` so PR creation, bounded review, verification, and post-PR monitoring stay in one source of truth.

## Input contract

The triggering comment should include:

```text
Use the plan-reviewer-build skill for this plan.
Plan path: thoughts/plans/<slug>.html
```

If the plan path is missing, ambiguous, or not a readable file in the current repo, stop and ask for the exact plan path. Do not infer a Markdown path.

## Required behavior

1. Read the full plan and repo guidance.
2. Invoke the installed `run-plan` workflow with the explicit plan path. This is the same execution entry point used for a direct agent request; the Build Plan button must not bypass it.
3. Pass the registered plan context to `run-plan` when available: Doct document/plan ID, workspace ID, Doct URL, triggering thread ID/claim ID, and plan path.
4. Perform only non-duplicative pre-run handoff work before delegation, such as confirming reviewer status context. Do not reimplement phase execution, review gates, verification, PR creation, or monitoring in this bridge.
5. Keep the Doct plan comment claim active until the build workflow has either started with durable run state or reported a real blocker.
6. Ack/resolve the Doct request comment only after the scoped run has durable state, a PR URL, or a clear blocker.

## Invocation

Use the local agent's native skill syntax for:

```text
run-plan <plan-path>
```

In Pi, that means following the `run-plan` skill directly with Pi todo-backed run state while using Codex as a subprocess for the Codex review leg and Claude Code Opus 4.7 xhigh for the applicable high-risk second-reviewer leg. If the reviewed plan is registered, the resulting run state must include the Doct document/plan ID and workspace ID so the `run-plan` status-alignment preflight can mark it active/in progress before code edits.

In Codex, that means following the installed shared `run-plan` skill with Codex goal/task state while honoring run-plan's Codex plus applicable Claude Code reviewer gates. Do not duplicate the scoped run workflow in this skill.

## Non-goals

- Do not run plan-readiness review here; use `plan-reviewer-execution-ready` for that.
- Do not edit the plan except for run-plan progress/deviation updates required by the execution workflow.
- Do not bypass the run-plan review, verification, PR, or post-PR monitoring requirements.
