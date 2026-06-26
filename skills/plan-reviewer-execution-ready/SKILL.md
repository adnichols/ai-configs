---
name: plan-reviewer-execution-ready
description: Respond to plan-reviewer execution-ready request comments by coordinating GPT and GLM readiness review, resolving disagreements into plan improvements, applying those improvements to the HTML plan, and rerunning review until both reviewers agree the plan is execution-ready or a real blocker remains. Use when a plan-review browser comment says to use plan-reviewer-execution-ready or requests an execution-ready review for a plan path.
---

# Plan Reviewer Execution-Ready

Use this skill when a `plan-review` browser action comment asks the listening agent to run an execution-ready review for an explicit plan path.

The plan-reviewer service only owns the comment lifecycle. Reviewer selection and review mechanics live here, in the installed agent configuration.

## Input contract

The triggering comment should include:

```text
Use the plan-reviewer-execution-ready skill for this plan.

Review thoughts/plans/<slug>.html with GPT and GLM. Debate and improve the correctness of this plan and any fixes until both agents are at consensus on the recommended changes, apply those changes, and the plan is execution-ready.

Plan path: thoughts/plans/<slug>.html
```

If the plan path is missing, ambiguous, or not a readable file in the current repo, stop and ask for the exact plan path. Do not infer a Markdown path.

## Required behavior

1. Read the full plan and repo guidance.
2. Confirm the plan is intended for execution readiness review, not direct implementation.
3. Run product-intent / PM readiness checks using the repo's product-intent guidance when present.
4. Run two independent read-only plan reviews using the active runtime's native mechanism.
5. Compare GPT and GLM findings, force disagreements through repo/product evidence, and identify the consensus set of changes required for correctness and execution readiness.
6. Apply the agreed in-scope improvements directly to the HTML plan. The primary deliverable is an improved plan, not a findings report.
7. Rerun GPT and GLM after material edits until both agree by substance that the latest plan is execution-ready, or stop with a specific product/tooling blocker.
8. Re-register the same plan through `plan-review register ... --execution-ready true` only after the gates clear.
9. Ack and resolve the plan-reviewer request comment only after the plan is actually updated and rereviewed, or the blocker is reported.

Do not edit product code, tests, generated files, local environment files, or unrelated docs while using this skill.

## Pi implementation

In Pi, run two read-only Pi subagent plan reviews:

- `quality-reviewer` for the GPT-5.5 review leg.
- `quality-reviewer-glm` for the GLM-5 review leg, using `thinking: "xhigh"` when the harness supports it. The `opencode-zen/glm-5` value is only the Pi model provider/model ID in that subagent; do not run the `opencode` CLI, OMP, OpenCode, or any non-Pi agent for this leg.

Launch both reviewers independently. Keep the review agents read-only; the coordinating agent must synthesize their recommendations, drive convergence, and edit the plan. The prompt to each reviewer must include:

- the plan path,
- the user request or browser action context,
- repo guidance and product-intent paths,
- the readiness rubric,
- explicit instruction not to edit files,
- explicit instruction to flag only readiness blockers, product questions, materially risky gaps, or missing decisions required to execute the stated scope.

Ask each reviewer for one verdict:

```text
VERDICT: PLAN_EXECUTION_READY
VERDICT: PLAN_NEEDS_REVISION
VERDICT: BLOCKED_BY_PRODUCT_QUESTION
```

Treat fuzzy output by substance. The plan is ready only when both independent reviewer results clear the plan after the latest material edit. Do not conclude after merely summarizing reviewer findings; if the findings are actionable within scope, apply them to the plan and rerun both reviewers.

## Codex implementation

In Codex, use the Codex-native reviewed-plan path installed with ai-configs:

```text
/review:plan <plan-path>
/review:change-integrate <plan-path>
```

Then apply the agreed changes with `/review:change-integrate <plan-path>` or direct scoped edits, and rerun `/review:plan <plan-path>` after material edits until the review result clears by substance. If the active Codex install provides a newer equivalent multi-review plan command, use that instead. Do not stop at a findings report when the fixes are inferable and in scope.

Codex must not claim execution readiness if it cannot run or delegate two independent read-only plan reviews. In that case, ack with a blocker explaining the missing command or reviewer capability and leave the plan not execution-ready.

## Review triage

Classify every finding before editing:

- `READINESS_BLOCKER`: fix before execution.
- `PRODUCT_QUESTION`: ask the user before execution.
- `OPTIONAL_CLARITY`: integrate only when it improves execution confidence without widening scope.
- `OUT_OF_SCOPE_FOLLOW_UP`: do not add to this plan unless it is required for truthful verification or an acceptance-criteria gap.
- `DISAGREE_REPO_EVIDENCE`: do not change the plan; record the evidence when useful.

Do not let reviewer suggestions expand the plan beyond the user's requested scope.

## Completion

Complete the request only when one of these is true:

- The plan has been updated, independent reviews clear, and the plan is re-registered with `--execution-ready true`.
- A product question or tooling blocker prevents readiness; the blocker is reported clearly and the plan remains not execution-ready.
