---
description: Run adversarial second-pass plan review using GPT and Opus 4.8 Extra High after the standard multi-model review
argument-hint: '<existing-plan-path | plan slug | legacy: <spec> <tasks> | legacy: <directory containing spec.md and tasks.md>'
---

# Adversarial Plan Review Process

This command runs a second-pass adversarial review after the normal `/review:plan` flow. It uses two challengers in parallel, then a synthesis pass, then integrates the feedback back into the plan.

Documents to review: $ARGUMENTS

## When to use this command

Use this after the standard multi-model review when you want an explicit challenge pass focused on:

- hidden weaknesses and incomplete exploration,
- product-intent drift,
- false-completion loopholes,
- under-specified retries, fail-closed boundaries, and shipped-path verification gaps.

## Execution Mode

- Run two adversarial reviews in parallel using the Task tool.
- Each reviewer works independently.
- After both complete, run the synthesis reviewer.
- Then integrate the review feedback and remove resolved review comments.
- Do not perform the review directly in the primary agent.

## Phase 1: Parallel Adversarial Review (2 Subagents)

### Subagent 1: Adversarial GPT
- **Agent:** `reviewer-plan-adversarial-gpt5.5`
- **Model:** `openai-codex/gpt-5.5`
- **Reasoning:** High
- **Output:** Plan file with `[REVIEW:Adversarial GPT]` comments + summary

### Subagent 2: Adversarial Opus 4.8 Extra High
- **Agent:** `reviewer-plan-adversarial-opus`
- **Model:** `opencode-zen/claude-opus-4-8`
- **Reasoning:** Extra High
- **Output:** Plan file with `[REVIEW:Adversarial Opus 4.8]` comments + summary
- **Gate classification:** optional model-provider review, not a required Claude Code CLI review gate.

### Parallel Execution

```text
Task(
  subagent_type="reviewer-plan-adversarial-gpt5.5",
  description="Challenge plan with Adversarial GPT",
  prompt="Review the plan at $ARGUMENTS. Follow your reviewer-plan-adversarial-gpt5.5 instructions exactly. Add [REVIEW:Adversarial GPT] comments to the plan file and provide a summary."
)

Task(
  subagent_type="reviewer-plan-adversarial-opus",
  description="Challenge plan with Adversarial Opus 4.8",
  prompt="Review the plan at $ARGUMENTS. Follow your reviewer-plan-adversarial-opus instructions exactly. Add [REVIEW:Adversarial Opus 4.8] comments to the plan file and provide a summary."
)
```

Launch both tasks in parallel and wait for them to complete.

## Phase 2: Synthesis Review

Run the synthesis reviewer after the adversarial reviewers complete.

```text
Task(
  subagent_type="reviewer-plan-gpt5.5",
  description="Synthesize adversarial plan reviews",
  prompt="Read the plan at $ARGUMENTS and synthesize the existing review comments, including any adversarial review comments. Add [REVIEW:Synthesis] comments to the plan file and provide a final consolidated summary."
)
```

## Phase 3: Auto-Integration

After synthesis completes, integrate the review feedback into the plan.

### Integration requirements

- Read the plan and extract `[REVIEW:Adversarial GPT]`, `[REVIEW:Adversarial Opus 4.8]`, and `[REVIEW:Synthesis]` comments.
- Apply edits directly to the plan based on the feedback.
- Remove resolved review comments.
- Update any affected sections such as Locked Decisions, Acceptance Criteria, BDD scenarios, phase work, verify steps, resume instructions, and changelog.
- Resolve important open questions before finishing integration.
- Validate that no `[REVIEW:...]` comments remain and that the plan still satisfies the repo’s canonical plan structure.

## Summary Format

After review and integration, provide:

```text
## Adversarial Review Complete

### Reviewers:
- ✅ Adversarial GPT
- ✅ Adversarial Opus 4.8
- ✅ Synthesis

### Highest-risk issues:
[List the most important issues found]

### Changes integrated:
[List the important plan changes made]

### Recommendation:
[Major revision needed / Proceed with caution / Ready to execute]
```

## Intended workflow

Typical flow:

1. `/review:plan <plan>`
2. `/review:plan-adversarial <plan>`
3. `/cmd:execute-plan <plan>`
