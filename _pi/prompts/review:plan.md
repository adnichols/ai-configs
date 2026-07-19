---
description: Run a blocker-focused review-only plan review using the GPT plan reviewer
argument-hint: '<existing-plan-path | plan slug | legacy: <spec> <tasks> | legacy: <directory containing spec.md and tasks.md>'
---

# GPT Plan Review Process

Run one bounded, blocker-focused review of the existing plan with the repository-owned GPT plan reviewer.

Document to review: $ARGUMENTS

HTML plans are first-class inputs. If the argument is a slug, resolve it through repo-local active plan guidance; in this repo's browser-reviewed flow that means `thoughts/plans/<slug>.html`, not a Markdown fallback.

## Execution Mode

- Use the actual Pi subagent tool surface: launch `reviewer-plan-gpt` with `Agent`.
- Review against the plan's stated goal, non-goals, original requested scope, and validated repo evidence.
- Comment only on blockers, materially risky gaps, or missing decisions required to execute that scope.
- Do not use this command as a broad idea-generation pass or expand the plan into adjacent nice-to-haves.
- Do not perform the review directly in the primary agent.
- Do not rely on a nonexistent `subagent(...)` runner or slash-command chaining.
- This command is review-only. Do not integrate or clean up review comments here.
- Do not trigger or imply an automatic fallback to `/review:change-claude-code`; Claude Code review remains a separate explicit opt-in command.

## Review Execution

```javascript
const review = Agent({
  subagent_type: "reviewer-plan-gpt",
  description: "Review plan with GPT",
  prompt: "Review the plan at $ARGUMENTS. Follow your reviewer-plan-gpt instructions exactly. Treat HTML plan files as first-class plan inputs and do not convert them to Markdown. Add [REVIEW:GPT] comments only for blockers, materially risky gaps, or missing decisions required to execute the stated goal within the validated source scope, then provide a readiness summary.",
  run_in_background: true,
});

get_subagent_result({ agent_id: review.agent_id ?? review.id, wait: true });
```

Wait for the reviewer to complete before producing summary text.

## Review Output

The final plan file should remain in its original format and contain any `[REVIEW:GPT]` comments left by the reviewer. Keep HTML plans valid semantic HTML.

## Summary Format

```markdown
## GPT Plan Review Complete

### Reviewer:
- ✅ GPT (`openai-codex/gpt-5.6-terra`, high reasoning)

### Blocking or Material Findings:
[List blocker-level or materially risky findings]

### Final Readiness:
[Needs material revision before execution / Proceed with caution / Ready to execute]
```

If comments need integration afterward, run `/review:change-integrate <plan>`.
