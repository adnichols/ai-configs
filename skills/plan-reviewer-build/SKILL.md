---
name: plan-reviewer-build
description: Respond to plan-reviewer Build Plan comments by executing an explicit execution-ready plan through the scoped-plan-run workflow. Use when a plan-review browser comment says to use plan-reviewer-build or asks to build a registered plan path.
---

# Plan Reviewer Build

Use this skill when a `plan-review` browser action comment asks the listening agent to build an explicit plan path.

The plan-reviewer service only requests the action. The implementation workflow is delegated to `scoped-plan-run` so PR creation, bounded review, verification, and post-PR monitoring stay in one source of truth.

## Input contract

The triggering comment should include:

```text
Use the plan-reviewer-build skill for this plan.
Plan path: thoughts/plans/<slug>.html
```

If the plan path is missing, ambiguous, or not a readable file in the current repo, stop and ask for the exact plan path. Do not infer a Markdown path.

## Required behavior

1. Read the full plan and repo guidance.
2. Invoke the installed `scoped-plan-run` workflow with the explicit plan path.
3. Keep the plan-review comment claim active until the build workflow has either started with durable run state or reported a real blocker.
4. Ack/resolve the plan-reviewer request comment only after the scoped run has durable state, a PR URL, or a clear blocker.

## Invocation

Use the local agent's native skill syntax for:

```text
scoped-plan-run <plan-path>
```

In Pi, that means following the `scoped-plan-run` skill directly with Pi todo-backed run state and Pi quality-reviewer subagent gates.

In Codex, that means following the installed shared `scoped-plan-run` skill with Codex goal/task state and Codex-native review prompts. Do not duplicate the scoped run workflow in this skill.

## Non-goals

- Do not run plan-readiness review here; use `plan-reviewer-execution-ready` for that.
- Do not edit the plan except for scoped-plan-run progress/deviation updates required by the execution workflow.
- Do not bypass the scoped-plan-run review, verification, PR, or post-PR monitoring requirements.
