---
description: Run blocker-focused review-only plan review using GPT and Kimi K2.5 in parallel
argument-hint: '<existing-plan-path | plan slug | legacy: <spec> <tasks> | legacy: <directory containing spec.md and tasks.md>'
---

# Multi-Model Plan Review Process

This command orchestrates a blocker-focused review-only plan review using two independent reviewers in parallel: GPT and Kimi K2.5.

Documents to review: $ARGUMENTS

## Execution Mode

- Use the actual OpenCode subagent tool surface: launch two review tasks in parallel.
- Each reviewer runs independently without seeing the other's work.
- Both reviewers must be launched before waiting for completions.
- Review against the plan's stated goal, non-goals, original requested scope, and validated repo evidence; comment only on blockers, materially risky gaps, or missing decisions required to execute that scope.
- Do not use this command as a broad idea-generation pass or an excuse to expand the plan into adjacent nice-to-haves.
- Do not perform any reviews directly in the primary agent.
- This command is review-only. Do not integrate or clean up review comments here.
- Do not introduce automatic Claude fallback behavior or other extra review legs.

## Process

### 0) Resolve Inputs (Plan File, Slug, or Legacy Bundle)

Preferred input:

- A single plan file in the repo's active plan format

Accept legacy inputs for migration only:

- `<spec_path> <tasks_path>`
- A directory containing `spec.md` and `tasks.md`

Resolution rules:

- If `$ARGUMENTS` starts with `@`, strip the leading `@` and treat as workspace-relative.
- If a single argument is an existing plan file, treat it as `plan_path`.
- If a single argument is a slug, resolve it using repo-local active plan guidance. Do not infer a markdown path; if guidance does not define slug resolution, ask for an explicit plan path.
- Only migrate a legacy bundle when repo-local guidance explicitly allows migration to the repo's active plan format; otherwise ask for an explicit existing plan path.

If multiple candidates match or a required file is missing, ask for an explicit plan file path.

### 1) Normalize Once

- Compute `plan_path` exactly once using the rules above.
- Use that same normalized `plan_path` for both review legs.
- Do not ask each reviewer to reinterpret the original raw argument when the normalized `plan_path` is already known.

### 2) Launch Parallel Review Legs

Use the Task tool to launch both reviewers in parallel. Do not wait for the first task before launching the second.

#### Review leg 1: GPT

```text
Task(
  subagent_type="reviewer-gpt",
  description="Review plan with GPT",
  prompt="""Review the single-file change plan at ${plan_path}.

Reuse the existing OpenCode review contract from _opencode/commands/review:change-gpt.md, with the plan path already resolved:
- Only modify the plan by inserting inline review comments.
- Do not change any other plan content.
- Do not remove or resolve review comments.
- Do not run follow-up commands, including /review:change-integrate.
- Explore the codebase for context when needed.
- Apply the same blocker-only materiality filter, execution-readiness checks, and summary style as review:change-gpt.
- After adding comments and returning the summary, stop."""
)
```

#### Review leg 2: Kimi K2.5

```text
Task(
  subagent_type="reviewer-kimi",
  description="Review plan with Kimi K2.5",
  prompt="""Review the single-file change plan at ${plan_path}.

Reuse the existing OpenCode review contract from _opencode/commands/review:change-k2.5.md, with the plan path already resolved:
- Only modify the plan by inserting inline review comments.
- Do not change any other plan content.
- Do not remove or resolve review comments.
- Do not run follow-up commands, including /review:change-integrate.
- Explore the codebase for context when needed.
- Apply the same blocker-only materiality filter, execution-readiness checks, and summary style as review:change-k2.5.
- After adding comments and returning the summary, stop."""
)
```

### 3) Wait For Both Review Legs

- Wait for both review tasks to finish before producing any wrapper summary.
- Preserve any inline review comments already added to the plan.
- Do not add a third reviewer or fallback reviewer if one leg fails; report the failing leg explicitly instead.

## Review Output

The final plan file should be an annotated plan containing any `[REVIEW:...]` comments left by GPT and Kimi.

## Summary Format

After both review legs finish, provide:

```markdown
## Multi-Model Review Complete

### Reviewers:
- ✅ GPT (openai/gpt-5.6-sol)
- ✅ Kimi K2.5 (fireworks kimi-k2p5)

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
  ├─ Kimi Review → [REVIEW:Kimi Reviewer] comments
    ↓
Output: Annotated Plan (run /review:change-integrate before execution if you want comments resolved)
```

---

## OpenCode Integration Instructions

### For all plan reviews in OpenCode

**This `/review:plan` command MUST be used as the standard review process for all plans.**

Whenever a plan is created or updated and needs review:

1. **Primary agent MUST delegate to this command** instead of performing direct review
2. **Always use the full multi-model review** — do not skip reviewers or use single-reviewer shortcuts
3. **Launch both reviewers before waiting** — GPT and Kimi should both be running in parallel
4. **Keep this command review-only** — it should stop with inline review comments still present in the plan

### Do NOT

- Run single-reviewer reviews for plans
- Use lower reasoning settings just to save time
- Manually review plans without delegating to this command
