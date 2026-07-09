description: Run blocker-focused review-only plan review using GPT and Kimi K2.5 in parallel
argument-hint: '<existing-plan-path | plan slug | legacy: <spec> <tasks> | legacy: <directory containing spec.md and tasks.md>'
---

# Multi-Model Plan Review Process

This command orchestrates a blocker-focused review-only plan review using two independent reviewers in parallel: GPT and Kimi K2.5.

Documents to review: $ARGUMENTS

HTML plans are first-class inputs. If the argument is a slug, resolve it through repo-local active plan guidance; in this repo's browser-reviewed flow that means `thoughts/plans/<slug>.html`, not a Markdown fallback.

## Execution Mode

- Use the actual Pi subagent tool surface: launch two background agents with `Agent`.
- Each reviewer runs independently without seeing the other's work.
- Both reviewers must be launched before waiting for completions.
- Review against the plan's stated goal, non-goals, original requested scope, and validated repo evidence; comment only on blockers, materially risky gaps, or missing decisions required to execute that scope.
- Do not use this command as a broad idea-generation pass or an excuse to expand the plan into adjacent nice-to-haves.
- Do not perform any reviews directly in the primary agent.
- Do not rely on a nonexistent `subagent(...)` runner or on slash-command chaining.
- This command is review-only. Do not integrate or clean up review comments here.
- Do not trigger or imply an automatic fallback to `/review:change-claude-code`; Claude Code review remains a separate explicit opt-in command.

## Phase 1: Parallel Review (2 Reviewers)

Launch both reviews before waiting for either of them to finish.

### Subagent 1: GPT Review
- **Agent:** `reviewer-plan-gpt`
- **Model:** `openai-codex/gpt-5.6-sol`
- **Reasoning:** Medium
- **Task:** Perform blocker-only plan review per reviewer-plan-gpt instructions
- **Output:** Same plan file with `[REVIEW:GPT]` comments + summary. For HTML plans, insert comments into the semantic HTML in a visible, valid way without converting the plan to Markdown.

### Subagent 2: Kimi K2.5 Review
- **Agent:** `reviewer-plan-kimi`
- **Model:** `opencode/kimi-k2.5`
- **Reasoning:** High
- **Task:** Perform blocker-only plan review per reviewer-plan-kimi instructions
- **Output:** Same plan file with `[REVIEW:Kimi K2.5]` comments + summary. For HTML plans, insert comments into the semantic HTML in a visible, valid way without converting the plan to Markdown.

### Parallel Execution

Launch two background `Agent` calls so Pi actually runs both reviewers concurrently.

```javascript
const gpt = Agent({
  subagent_type: "reviewer-plan-gpt",
  description: "Review plan with GPT",
  prompt: "Review the plan at $ARGUMENTS. Follow your reviewer-plan-gpt instructions exactly. Treat HTML plan files as first-class plan inputs and do not convert them to Markdown. Add [REVIEW:GPT] comments only for blockers, materially risky gaps, or missing decisions required to execute the stated goal within the validated source scope, then provide a readiness summary.",
  run_in_background: true,
});

const kimi = Agent({
  subagent_type: "reviewer-plan-kimi",
  description: "Review plan with Kimi K2.5",
  prompt: "Review the plan at $ARGUMENTS. Follow your reviewer-plan-kimi instructions exactly. Treat HTML plan files as first-class plan inputs and do not convert them to Markdown. Add [REVIEW:Kimi K2.5] comments only for blockers, materially risky gaps, or missing decisions required to execute the stated goal within the validated source scope, then provide a readiness summary.",
  run_in_background: true,
});

get_subagent_result({ agent_id: gpt.agent_id ?? gpt.id, wait: true });
get_subagent_result({ agent_id: kimi.agent_id ?? kimi.id, wait: true });
```

Wait for both `get_subagent_result(..., wait: true)` calls to complete before producing any summary text.

## Review Output

The final plan file should be the same annotated plan file, in its original format, containing any `[REVIEW:...]` comments left by GPT and Kimi K2.5. For HTML plans, keep the document valid semantic HTML.

## Summary Format

After completing all reviews, provide:

```markdown
## Multi-Model Review Complete

### Reviewers:
- ✅ GPT (openai-codex/gpt-5.6-sol, medium reasoning)
- ✅ Kimi K2.5 (opencode/kimi-k2.5, high reasoning)

### Consensus Blockers:
[List issues multiple reviewers flagged that materially affect execution readiness]

### Divergent Material Risks:
[List any material disagreements between GPT and Kimi, if present]

### Unique Material Risks:
[List blocker-level or materially risky issues caught by only one reviewer]

### Final Readiness:
[Needs material revision before execution / Proceed with caution / Ready to execute]
```

## Scope

This command is review-only:

- Phase 1: GPT review-only pass
- Phase 1: Kimi K2.5 review-only pass
- The final output is an annotated plan with review comments left in place
- If the user wants integration afterward, run `/review:change-integrate <plan>`

## Execution Flow Summary

```text
Input Plan
    ↓
Phase 1: Parallel Reviews (2 reviewers)
  ├─ GPT Review → [REVIEW:GPT] comments
  ├─ Kimi K2.5 Review → [REVIEW:Kimi K2.5] comments
    ↓
Output: Annotated Plan (run /review:change-integrate before execution if you want comments resolved)
```

---

## Oh My Pi Integration Instructions

### For ALL Plan Reviews in Oh My Pi:

**This `/review:plan` command MUST be used as the standard review process for ALL plans.**

Whenever a plan is created or updated and needs review:

1. **Primary agent MUST delegate to this command** instead of performing direct review
2. **Always use the full multi-model review** - do not skip reviewers or use single-reviewer shortcuts
3. **Launch both reviewers before waiting** - GPT and Kimi should both be running in parallel
4. **Keep this command review-only** - it should stop with inline review comments still present in the plan

### Process Flow:

```text
User: "Review this plan"
Agent: Delegate to /review:plan <plan-path>
  → Agent launches GPT + Kimi reviewers in parallel
  → Each adds [REVIEW:Name] comments
  → Returns an annotated plan with review comments left in place
```

### Benefits:

- **Multiple perspectives:** Two different model architectures stress-test execution readiness from different angles
- **High reasoning mode:** All reviewers use a strong review pass
- **Parallel efficiency:** Both reviews run simultaneously for faster turnaround
- **Consistency:** Standardized blocker-focused review format across all plans

### Do NOT:

- Run single-reviewer reviews for plans
- Use lower reasoning settings to save time
- Manually review plans without delegating to this command
