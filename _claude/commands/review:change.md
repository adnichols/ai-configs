---
description: Comprehensive review of a change plan (single-file spec + phases + progress) for accuracy and completeness
argument-hint: '<existing-plan-path | plan slug | legacy: <spec> <tasks> | legacy: <directory containing spec.md and tasks.md>'
---

# Change Review (Single Plan File)

Review the provided change plan as a cohesive unit. Your goal is to ensure the plan is solid and executable without scope creep or error.

Documents to review: $ARGUMENTS

## Scope (Review-Only; Do Not Integrate)

This command is review-only.

- Launch the repository-owned `reviewer` subagent to perform the substantive review. It is pinned to `claude-sonnet-5` at high effort and must remain read-only.
- Give it the resolved plan path, this command's review criteria, and the requirement to return only concrete findings with file/line evidence.
- The driving session may transcribe validated findings as inline `[REVIEW:CLAUDE] ... [/REVIEW]` comments, but must not add findings of its own.
- Do not change any other plan content (do not fix, rewrite, or reorganize anything), remove or resolve review comments, or run follow-up commands (including `/review:change-integrate`).
- After recording the reviewer findings and providing the summary, stop.


## Reviewer Identity

Use `CLAUDE` for inline comment attribution, while recording that the independent reviewer was the `reviewer` subagent (`claude-sonnet-5`, high effort).

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

Use native Glob, Grep, Read, and read-only shell commands to gather the required context directly.

### 2) Review Specification (Critical Spec Review)

Read the plan. Apply a critical mindset. Don't validate; look for problems.

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

- Plan status: solid or needs rework?
- Critical issues: list the most important blockers.
- Recommendation: "Proceed with caution" or "Major revision needed".

---

## Manual Follow-up (User-Run Only)

If the user asks to integrate comments into a clean plan, they should run:

`/review:change-integrate <plan path | plan slug>`

Stop after the summary; do not proceed automatically.
