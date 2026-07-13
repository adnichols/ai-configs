---
description: Run adversarial second-pass plan review using parallel Claude Code and GPT review, then GPT synthesis and integration
argument-hint: '<existing-plan-path | plan slug | legacy: <spec> <tasks> | legacy: <directory containing spec.md and tasks.md>'
---

# Adversarial Plan Review Process

This command runs a second-pass adversarial review after the normal `/review:plan` flow.

It uses **two reviewers in parallel**:
- Claude Code
- GPT

After both finish, it runs a **GPT synthesis pass** and then integrates the review feedback back into the plan.

Documents to review: $ARGUMENTS

## When to use this command

Use this after the standard `/review:plan` flow when you want an explicit challenge pass focused on:

- hidden weaknesses and incomplete exploration,
- product-intent drift,
- false-completion loopholes,
- under-specified retries, fail-closed boundaries, and shipped-path verification gaps.

## Execution Mode

- Launch the Claude Code review via `/review:change-claude-code`, which owns the deterministic background `claude_review` lifecycle while the canonical launcher owns private-tmux Claude mechanics.
- Launch the GPT review via the canonical `/review:change-gpt` prompt.
- Do not use the old adversarial reviewer subagents.
- Do not run the adversarial review directly in the primary agent.
- After both reviewers finish, run the GPT synthesis reviewer.
- Then integrate the feedback into the plan and remove resolved review comments.

## Reviewer Names and Comment Formats

Claude reviewer name:
```text
CLAUDE
```

Claude comment format:
```text
[REVIEW:CLAUDE] Your critical feedback here [/REVIEW]
```

GPT reviewer name:
```text
GPT
```

GPT comment format:
```text
[REVIEW:GPT] Your critical feedback here [/REVIEW]
```

## Phase 1: Parallel Interactive Adversarial Reviews

Launch both sessions before waiting for either of them to finish.

### Shared adversarial review goals

Both reviewers should challenge the plan through these lenses:

1. hidden weaknesses and incomplete exploration,
2. product-intent drift,
3. insufficient detail for accurate execution,
4. false completion / loophole analysis,
5. boundary handling and fail-closed behavior,
6. recovery realism,
7. verification realism for the actual shipped/operator path.

Both reviewers must:

- review the plan as if it will be implemented literally,
- insert inline review comments only,
- avoid rewriting or integrating the plan,
- preserve plan structure and progress state,
- stop after a concise summary.

### Canonical reviewer transports

Do not duplicate launcher mechanics here.
Use these prompt templates as the canonical transport + lifecycle specs:

- Claude leg: `/review:change-claude-code`
- GPT leg: `/review:change-gpt`

For each leg:

- follow that prompt template's fixed background-tool and artifact lifecycle rules,
- keep the Claude Code review on the deterministic `claude_review` tool owned by `/review:change-claude-code`; do not construct launcher or shell calls,
- run exactly one review per reviewer,
- do not invent alternate launcher shapes,
- do not route the work through deprecated provider-specific reviewer prompts.

### Required adversarial reviewer prompt content

When adapting those canonical reviewer prompts for this adversarial pass, make both reviewers use adversarial instructions that:

- resolve the target plan path,
- review the plan as if it will be implemented literally,
- add inline review comments only,
- use the reviewer-specific comment tag,
- not rewrite, integrate, or remove comments,
- not modify any file other than the plan,
- preserve plan structure and progress state,
- stop after a concise summary.

Both adversarial prompts must explicitly challenge the plan for:

- hidden weaknesses,
- product-intent drift,
- ambiguity that would allow the wrong implementation,
- false-positive verify steps,
- missing fail-closed behavior,
- incomplete recovery guidance,
- and places where the plan could ship green while the real outcome is still wrong.

## Phase 1 lifecycle

- Launch both sessions first, in parallel.
- Apply the lifecycle and completion handling from the canonical prompt for each reviewer:
  - `/review:change-claude-code` for Claude,
  - `/review:change-gpt` for GPT.
- Only inspect failure details if a session exits non-zero or clearly fails to review the plan.

## Phase 2: GPT Synthesis

After both interactive reviewers complete, run the GPT synthesis reviewer on GPT-5.6 Sol high reasoning.

```javascript
Agent({
  subagent_type: "reviewer-plan-synthesis",
  description: "Synthesize adversarial review results",
  prompt: "Synthesize the existing review comments already present in the plan at $ARGUMENTS, including any [REVIEW:CLAUDE] and [REVIEW:GPT] comments. Add [REVIEW:Synthesis] comments and provide a final consolidated summary.",
})
```

Wait for the synthesis reviewer to complete before integration.

## Phase 3: Auto-Integration

After synthesis completes, integrate the review feedback into the plan.

### Integration requirements

- Read the plan and extract `[REVIEW:CLAUDE]`, `[REVIEW:GPT]`, and `[REVIEW:Synthesis]` comments.
- Apply edits directly to the plan based on the feedback.
- Remove resolved review comments.
- Update affected sections such as Locked Decisions, Acceptance Criteria, BDD scenarios, phase work, verify steps, resume instructions, and changelog.
- Resolve important open questions before finishing integration.
- Validate that no `[REVIEW:...]` comments remain and that the plan still satisfies the repo’s canonical plan structure.

## Summary Format

After review and integration, provide:

```text
## Adversarial Review Complete

### Reviewers:
- ✅ Claude Code
- ✅ GPT (gpt-5.6-sol, high reasoning)
- ✅ GPT Synthesis (gpt-5.6-sol, high reasoning)

### Highest-risk issues:
[List the most important issues found]

### Divergent views:
[List any meaningful differences between Claude and GPT]

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
