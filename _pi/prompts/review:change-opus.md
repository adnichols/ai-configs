---
description: Run a change review using Claude Opus 4.8 Extra High
argument-hint: '<existing-plan-path | plan slug | legacy: <spec> <tasks> | legacy: <directory containing spec.md and tasks.md>'
agent: reviewer-opus
subtask: true
model: opencode/claude-opus-4-8
reasoningEffort: xhigh
---

## Execution Mode
- This prompt already runs inside the `reviewer-opus` subagent selected by frontmatter.
- Perform the review directly in this session.
- Do not try to spawn another `reviewer-opus` task just to satisfy this prompt.
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

Review the provided change plan as a cohesive unit. Your goal is to decide whether it is ready to execute within its stated goal and non-goals, flagging only blockers, material risks, or missing decisions that would change that readiness.

Documents to review: $ARGUMENTS

## Scope (Review-Only; Do Not Integrate)

This command is review-only.

- Only modify the plan by inserting inline `[REVIEW:...] ... [/REVIEW]` comments.
- HTML plans are first-class inputs; keep them as valid semantic HTML and insert review comments visibly without converting the plan to Markdown.
- Do not change any other plan content (do not fix, rewrite, or reorganize anything).
- Do not remove or resolve review comments.
- Do not run follow-up commands (including `/review:change-integrate`).
- Only add a comment for blockers, material risks, or missing decisions required to execute the plan's stated goal while honoring its non-goals.
- Do not comment on nice-to-haves, opportunistic cleanup, adjacent surfaces not required by the requested scope, or extra detail that would not change execution readiness.
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

Use the available repo exploration tools in this session to gather context.

### 2) Review Specification (Critical Spec Review)

Read the plan. Apply a critical mindset. Don't validate; look for material problems that would change whether the requested scope is ready to execute.

Look for:

- Gaps: missing requirements or edge cases.
- Risks: security, performance, or integration issues.
- Ambiguity: unclear success criteria or technical decisions.
- Technical debt: unrealistic assumptions or poor architectural choices.

Add comments:

```markdown
[REVIEW:Name] GAP: The plan mentions "user roles" but doesn't define permissions or hierarchy. [/REVIEW]
```

### 3) Review Execution Readiness (Phases + Verify + Progress)

Verify the plan is runnable and resumable:

- Phases are present (`## Phase N: ...`) and ordered.
- Each phase has:
  - `### Tests first` (behavioral evidence strong enough to catch partial implementation)
  - `### End State` (observable outcomes)
  - `### Work` (high-level guidance)
  - `### Verify` (explicit commands and/or manual checks)
- `## Progress` exists, is coarse (phase-level), and uses stable IDs.
- `## Progress` items correspond to phase headers.
- Only `## Progress` contains checkboxes.
- `Resume Instructions (Agent)` avoids stop points and enables continuous execution.
- `## Decisions / Deviations Log` exists.
- If the plan is execution-ready, it does not leave unresolved `Open Questions`, `Decision Points`, or equivalent unresolved-decision sections.
- Each unchecked phase is still a **bounded execution slice**:
  - one coherent outcome,
  - one primary verification story,
  - limited enough coupling and affected surfaces for one safe execution pass,
  - little enough remaining discovery that execution should not need semantic replanning.
- If a phase would likely require same-scope subdivision during execution just to finish safely, treat that as a plan defect to flag now.

### 4) Cross-Verification

Ensure internal consistency:

- Acceptance criteria have corresponding verification steps.
- Proposed approach matches the phase work.
- Non-goals are not accidentally reintroduced.
- The plan does not rely on executors making outcome-shaping chunking or design decisions later.
- Phase sizing matches likely effort, coupling, and verification breadth rather than bundling multiple independently verifiable outcomes behind one checkbox.

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

## Summary

After adding comments to the plan, provide a single summary:

- Plan status: ready as scoped or needs rework?
- Material blockers or readiness risks: list only the issues that would change whether execution should proceed as scoped.
- Recommendation: "Proceed as scoped" or "Major revision needed".
- Do not include brainstorming, nice-to-haves, or adjacent cleanup ideas.

---

## Manual Follow-up (User-Run Only)

If the user asks to integrate comments into a clean plan, they should run:

`/review:change-integrate <plan path | plan slug>`

Stop after the summary; do not proceed automatically.
