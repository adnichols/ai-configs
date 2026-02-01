---
description: Loop multi-agent change plan review and integration until convergence
argument-hint: '<path to plan.md | plan slug>'
---

# Multi-Agent Change Review Loop

Keep reviewing and integrating corrections until the change plan converges (no new corrections).

Target: $ARGUMENTS

## Configuration

- Max iterations: 5
- Convergence criteria: 0 new review comments in an iteration
- Reviewers: Qwen3-Thinking, Kimi K2, DeepSeek

## Loop Process

### 0) Resolve Plan Path

Resolve `plan_path`:

- If a slug: `thoughts/plans/<slug>.md`
- If a path: use the provided file

### 1) Iteration

For each iteration:

1. Run multi-agent plan review (use separate temporary comment files if you want to avoid touching the plan during review).
2. Count new review comments.
3. If 0, stop (converged).
4. Integrate comments into the plan file using:

```
/review:change-integrate <plan path | plan slug>
```

Repeat until convergence or iteration limit.

## Final Output

- A converged plan file with no remaining `[REVIEW:...]` comments.
