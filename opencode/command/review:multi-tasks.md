---
description: Launch parallel multi-agent change plan review (Qwen, Kimi, DeepSeek)
argument-hint: '<path to plan.md | plan slug>'
---

# Multi-Agent Change Plan Review

Orchestrate parallel plan reviews from Qwen3-Thinking, Kimi K2, and DeepSeek.

Target: $ARGUMENTS

## Process

### 1) Resolve and Read Plan

Resolve `plan_path`:

- If a slug: `thoughts/plans/<slug>.md`
- If a path: use the provided file

Read the plan to confirm it exists.

### 2) Launch Parallel Reviewers

Launch ALL THREE reviewers in parallel using Task tool calls.

Each reviewer should:

- Read `plan_path` fully
- Leave inline `[REVIEW:<Name>] ... [/REVIEW]` tags for issues
- Focus on: INCORRECT, GAP, RISK, AMBIGUITY, WRONG REFERENCE, SCOPE DRIFT

### 3) Next Step

After reviews complete, integrate the corrections:

```
/review:change-integrate <plan path | plan slug>
```
