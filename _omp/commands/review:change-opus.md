---
description: Run a change review using Claude Opus 4.8 Extra High
argument-hint: '<existing-plan-path | plan slug | legacy: <spec> <tasks> | legacy: <directory containing spec.md and tasks.md>'
agent: reviewer-opus
subtask: true
model: opencode/claude-opus-4-8
reasoningEffort: xhigh
---

## Execution Mode
- Run this review by delegating to the Task tool with `agent: reviewer-opus` and exactly one task.
- Do not perform the review directly in the primary agent.
- Pass the complete review requirements from this command to that subagent and wait for completion before responding.
Your reviewer name is CLAUDE 

Use this comment format:
```
[REVIEW:CLAUDE] Your critical feedback here [/REVIEW]
```

To respond to other reviewers:
```
[REVIEW:CLAUDE] RE: [OtherReviewer] - Your response [/REVIEW]
```

# Change Review (Single Plan File)

Review the provided change plan as a cohesive unit. Your goal is to ensure the plan is solid and executable without scope creep or error. Flag only blockers, material risks, or missing decisions required to execute the plan's stated goal and non-goals.

Documents to review: $ARGUMENTS

## Scope (Review-Only; Do Not Integrate)

This command is review-only.

- Only modify the plan by inserting inline `[REVIEW:...] ... [/REVIEW]` comments.
- Do not change any other plan content (do not fix, rewrite, or reorganize anything).
- Do not remove or resolve review comments.
- Do not run follow-up commands (including `/review:change-integrate`).
- Do not leave comments for nice-to-haves, opportunistic cleanup, adjacent surfaces not required by the requested scope, or extra detail that would not change execution readiness.
- After adding comments and providing the summary, stop.


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

### 1) Explore Codebase for Context (When Needed)

Before leaving extensive feedback, explore the codebase to confirm:

- Existing patterns and conventions
- Feasibility and integration constraints
- Correct file paths, APIs, and data structures referenced by the plan

Use the Task tool with `subagent_type=Explore` to efficiently gather context.

### 2) Review Specification (Critical Spec Review)

Read the plan. Apply a critical, materiality-first mindset. Don't validate; look for problems that would block execution, create a material risk, or force an unresolved decision within the plan's stated goal and non-goals.

Look for, but only when they materially affect readiness for the requested scope:

- Gaps: missing requirements or edge cases required for the stated scope.
- Risks: security, performance, or integration issues that would materially change readiness.
- Ambiguity: unclear success criteria or technical decisions that must be resolved before execution.
- Technical debt: unrealistic assumptions or poor architectural choices only when they would prevent or materially distort the requested change.

Add comments:

```markdown
[REVIEW:Name] GAP: The plan mentions "user roles" but doesn't define permissions or hierarchy. [/REVIEW]
```

### 3) Review Execution Readiness (Phases + Verify + Progress)

Verify the plan is runnable and resumable:

- Phases are present (`## Phase N: ...`) and ordered.
- Each phase has:
  - `### End State` (observable outcomes)
  - `### Work` (high-level guidance)
  - `### Verify` (explicit commands and/or manual checks)
- `## Progress` exists, is coarse (phase-level), and uses stable IDs.
- `## Progress` items correspond to phase headers.
- Only `## Progress` contains checkboxes.
- `Resume Instructions (Agent)` avoids stop points and enables continuous execution.

### 4) Cross-Verification

Ensure internal consistency:

- Acceptance criteria have corresponding verification steps.
- Proposed approach matches the phase work.
- Non-goals are not accidentally reintroduced.

## Comment Guidelines

Types of issues to flag:

- INCORRECT
- SCOPE DRIFT
- GAP
- RISK
- AMBIGUITY
- WRONG REFERENCE

Usage:

- Insert tags directly into the plan document.
- Use `[REVIEW:Name] Content [/REVIEW]` format.
- Be specific and actionable.
- Do not flag nice-to-haves, opportunistic cleanup, adjacent surfaces outside the stated scope, or extra detail that would not change readiness.

## Summary

After adding comments to the plan, provide a single summary:

- Plan status: solid or needs rework for the requested scope?
- Critical issues: list only the blockers, material risks, or missing decisions required before execution.
- Recommendation: "Proceed with caution" or "Major revision needed".
- Keep the summary focused on readiness for the requested scope, not optional improvements or broader idea generation.

---

## Manual Follow-up (User-Run Only)

If the user asks to integrate comments into a clean plan, they should run:

`/review:change-integrate <plan path | plan slug>`

Stop after the summary; do not proceed automatically.
