---
description: Run a change review using GPT
argument-hint: '<existing-plan-path | plan slug | legacy: <spec> <tasks> | legacy: <directory containing spec.md and tasks.md>'
agent: reviewer-gpt
subtask: true
model: openai-codex/gpt-5.5
---

## Execution Mode
- This prompt already runs inside the `reviewer-gpt` subagent selected by frontmatter.
- Perform the review directly in this session.
- Do not try to spawn another `reviewer-gpt` task just to satisfy this prompt.
Your reviewer name is GPT

Use this comment format:
```
[REVIEW:GPT] Your critical feedback here [/REVIEW]
```

To respond to other reviewers:
```
[REVIEW:GPT] RE: [OtherReviewer] - Your response [/REVIEW]
```

# Change Review (Single Plan File)

Review the provided change plan as a cohesive unit. Your goal is to ensure the plan is solid, executable, and faithful to the source plan's stated goal, non-goals, acceptance criteria, and validated scope.

Documents to review: $ARGUMENTS

## Scope (Review-Only; Do Not Integrate)

This command is review-only.

- Only modify the plan by inserting inline `[REVIEW:...] ... [/REVIEW]` comments.
- HTML plans are first-class inputs; keep them as valid semantic HTML and insert review comments visibly without converting the plan to Markdown.
- Do not change any other plan content (do not fix, rewrite, or reorganize anything).
- Do not remove or resolve review comments.
- Do not run follow-up commands (including `/review:change-integrate`).
- After adding comments and providing the summary, stop.

## Materiality Filter

Review against the plan's stated goal, non-goals, acceptance criteria, and validated source scope.

- Flag only blockers, material risks, or missing decisions required to execute that stated scope correctly.
- Flag scope gaps when the plan's own stated scope requires missing work.
- Do not leave comments for nice-to-haves, opportunistic cleanup, adjacent surfaces outside the stated scope, or extra detail that would not change execution readiness.
- If an issue would not change readiness, leave it out.


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

### 2) Review Specification (Blocker-Oriented Spec Review)

Read the plan with a blocker-oriented mindset. Do not hunt for every possible improvement. Comment only when something would block, materially derail, or wrongly expand execution of the stated scope.

Look for:

- Gaps: missing required work or edge cases that would break the stated goal or acceptance criteria.
- Risks: material security, correctness, performance, or integration issues that threaten readiness.
- Ambiguity: missing success criteria or technical decisions required to execute the plan as written.
- Scope drift: work that expands beyond the stated goal, non-goals, or validated source scope.

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
- Optional adjacent work is not promoted into required scope without support from the plan's stated scope.

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

- Plan status: ready or needs rework?
- Material blockers: list only blockers, material risks, or required missing decisions.
- Recommendation: "Ready to execute" or "Revision required before execution".

---

## Manual Follow-up (User-Run Only)

If the user asks to integrate comments into a clean plan, they should run:

`/review:change-integrate <plan path | plan slug>`

Stop after the summary; do not proceed automatically.
