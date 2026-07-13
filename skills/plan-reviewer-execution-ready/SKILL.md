---
name: plan-reviewer-execution-ready
description: Respond to Doct/plan-reviewer execution-ready request comments by coordinating Codex and applicable Claude Code readiness review, resolving disagreements into plan improvements, applying those improvements to the HTML plan, and rerunning review until all applicable reviewers agree the plan is execution-ready or a real blocker remains. Use when a registered Doct plan comment says to use plan-reviewer-execution-ready or requests an execution-ready review for a plan path.
---

# Plan Reviewer Execution-Ready

Use this skill when a registered Doct plan browser action comment asks the listening agent to run an execution-ready review for an explicit plan path.

Doct owns registration and the comment lifecycle through `doct-agent plans`. The default browser-review listener is the returned durable `listenerInstructions.listenerCommand`, normally `doct-agent plans listen ... --jsonl`, run with the harness background-process tool. A routed browser action or `doct-agent plans comments add --submit-action agent ...` creates the queued work item; ordinary conversation comments do not. This worker receives the claim payload and returned reply/ack/resolve/release commands from that listener. It should not start, replace, or stop the listener itself.

## Input contract

The triggering comment should include:

```text
Use the plan-reviewer-execution-ready skill for this plan.

Review thoughts/plans/<slug>.html with Codex and applicable Claude Code. Debate and improve the correctness of this plan and any fixes until all applicable reviewers are at consensus on the recommended changes, apply those changes, and the plan is execution-ready.

Plan path: thoughts/plans/<slug>.html
```

If the plan path is missing, ambiguous, or not a readable file in the current repo, stop and ask for the exact plan path. Do not infer a Markdown path.

## Required behavior

1. Read the full plan and repo guidance.
2. Confirm the plan is intended for execution readiness review, not direct implementation.
3. Run product-intent / PM readiness checks using the repo's product-intent guidance when present.
4. Run the independent Codex plan review and the Claude Code plan review only when the high-risk second-reviewer trigger or an explicit override applies.
5. Compare applicable reviewer findings, force disagreements through repo/product evidence, and identify the consensus set of changes required for correctness and execution readiness.
6. Apply the agreed in-scope improvements directly to the HTML plan. The primary deliverable is an improved plan, not a findings report.
7. Rerun Codex and applicable Claude Code after material edits until all applicable reviewers agree by substance that the latest plan is execution-ready, or stop with a specific product/tooling blocker.
8. Update the same registered Doct plan through `doct-agent plans update` and set truthful lifecycle/board/readiness state only after the gates clear.
9. Ack and resolve the Doct plan request comment only after the plan is actually updated and rereviewed, or the blocker is reported.

Do not edit product code, tests, generated files, local environment files, or unrelated docs while using this skill.

## Reviewer implementation

Run these independent read-only readiness review legs:

- **Codex** is the primary review leg. In Codex, run it as a Codex subagent/native review task when that facility is available; otherwise use `codex-review-partner` in `plan-review` mode. In Pi, run Codex as a subprocess through the installed `codex-review-partner` wrapper.
- **Claude Code** is the high-risk second-reviewer leg. Run it only when the high-risk policy applies: data loss risk, auth/security, concurrency/locking, migrations/persistence, release-blocking CI behavior, release-risk, another explicit P1/P2 risk surface, or an explicit override. Use `claude-code-review`; the canonical launcher owns model, effort, and private-tmux mechanics.

Do not use Pi `quality-reviewer`, GLM reviewer profiles, GPT subagents, Kimi, OMP, OpenCode, or other model-subagent substitutes for this gate. If Codex or a required Claude Code review is unavailable, stop with a tooling blocker and leave the plan not execution-ready unless the user explicitly waives the missing reviewer. If Claude Code is skipped under the low-risk policy, record the skip and override decision.

Launch the reviewers independently when possible. Keep the review agents read-only; the coordinating agent must synthesize their recommendations, drive convergence, and edit the plan. Empty output, tool-only output, provider errors, or transcripts ending in tool use do not count as independent readiness review. Rerun once with a narrower bounded readiness prompt; if the narrowed rerun is still unusable, stop with a tooling blocker and leave the plan not execution-ready.

For every reviewer, use bounded scope rather than parent-side turn caps. Do not cap tool calls or lower `max_turns` to force completion; hard caps can truncate the final verdict and produce unusable output. Give each reviewer a concrete readiness packet and require a final verdict. If any reviewer cannot complete the assigned readiness scope, it must return a non-ready result with completed checks, remaining checks, and the exact follow-up slice the coordinating agent should run next. If the caller explicitly supports `REVIEW_INCOMPLETE_RERUN_NEEDED`, use that verdict; otherwise map incomplete coverage to `VERDICT: PLAN_NEEDS_REVISION` with the same completed-checks, remaining-checks, and follow-up-slice fields.

Split a readiness review into focused passes when a plan spans three or more product surfaces, or when the readiness scope is otherwise too broad for one concrete readiness packet. Use focused passes such as product intent and scope boundaries, BDD/verification adequacy, architecture/dependency risks, and recovery/operator/error behavior. The coordinating agent must synthesize all slice verdicts and cannot mark the plan execution-ready until every required slice is complete or explicitly blocked.

The prompt to each reviewer must include:

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
VERDICT: REVIEW_INCOMPLETE_RERUN_NEEDED
```

Treat fuzzy output by substance, but never normalize empty, tool-only, provider-error, or incomplete-coverage output into a ready verdict. The plan is ready only when all applicable independent reviewer results clear the plan after the latest material edit and all required review slices are complete. Do not conclude after merely summarizing reviewer findings; if the findings are actionable within scope, apply them to the plan and rerun all applicable reviewers. If a reviewer returns incomplete coverage, run the recommended follow-up slice, record completed checks, remaining checks, rerun slices, and final synthesized readiness status, then continue until all required slices are complete or explicitly blocked.

## Codex implementation

In Codex, run the Codex review leg as a subagent/native review task when available. If a subprocess review is needed, use the same repo/worktree and the installed wrapper:

```bash
~/.agents/skills/codex-review-partner/scripts/run-review.sh \
  --mode plan-review \
  --input /tmp/plan-readiness-review.md \
  --cwd /path/to/repo \
  --output thoughts/validation/<slug>-codex-plan-review.md
```

Run Claude Code only when the high-risk second-reviewer trigger or an explicit override applies. In Pi, write the bounded prompt file and call:

```text
claude_review({
  action: "start",
  cwd: "/path/to/repo",
  promptFile: "/tmp/claude-plan-readiness-review.md",
  output: "thoughts/validation/<slug>-claude-plan-review.md"
})
```

Do not poll. Consume the completion notification and read the artifact. In non-Pi runtimes, follow `claude-code-review` and call the canonical Python launcher directly.

After material plan edits, rerun the Codex leg and any required Claude Code leg until all applicable reviewers clear by substance. Codex must not claim execution readiness if Codex independent review or a required Claude Code review is unavailable; ack with a tooling blocker and leave the plan not execution-ready.

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

- The plan has been updated, independent reviews clear, and the registered Doct plan has been updated with truthful status/metadata.
- A product question or tooling blocker prevents readiness; the blocker is reported clearly and the plan remains not execution-ready.
