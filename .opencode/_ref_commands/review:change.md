---
description: Comprehensive review of a change (specification + tasks) for accuracy and completeness
argument-hint: "<path to spec> <path to tasks> | <directory containing spec.md and tasks.md> | <plan slug>"
---

# Change Review (Spec + Tasks)

Review the provided specification and task list as a cohesive unit. Your goal is to ensure the specification is solid and the tasks accurately reflect that specification without scope creep or error.

**Documents to review:** $ARGUMENTS

## Your Identity

If you selected a reviewer subagent, use its friendly name for comment attribution (e.g., `[REVIEW:SecurityBot]`). If no subagent is selected, use **OPENCODE**.

## Process

### 0. Resolve Inputs (Files, Directory, or Slug)

`$ARGUMENTS` can be:
- Two explicit file paths: `<spec_path> <tasks_path>`
- A single directory path containing both files (recommended): `<dir_path>`
- A single plan slug (recommended): `<slug>` (example: `drizzle-prod-migrations-hardening`)

Normalize inputs:
- If an argument starts with `@`, treat it as a workspace-relative path and strip the leading `@`.
- If an argument ends with `/`, treat it as a directory path.

Resolution rules:
- If two arguments are provided and both are files, use them as-is.
- If a single argument is provided and it is a directory, find the spec and tasks files inside it (non-recursive) using these defaults:
  - Spec candidates (priority order): `spec.md`, `specification.md`
  - Tasks candidates (priority order): `tasks.md`, `task.md`, `task-list.md`
- If a single argument is provided and it is a file:
  - If it looks like a spec file (`spec*.md`), infer tasks from the same directory using the tasks candidate list.
  - If it looks like a tasks file (`tasks*.md` or `task*.md`), infer spec from the same directory using the spec candidate list.
- If a single argument is provided and it does not resolve to an existing file/directory, treat it as a slug and resolve to a directory:
  - First try `thoughts/plans/<slug>/`
  - Otherwise search under `thoughts/` for a directory named `<slug>`

If multiple candidates match or a file is missing, ask the user for two explicit file paths and list the candidates you found.
If exactly one spec and one tasks file are found, proceed without asking for confirmation, and restate the resolved paths at the top of your response.

### 1. Analyze Context & Categorize

First, identify the provided files:
- **Specification:** Defines *what* we are building (requirements, design, scope).
- **Task List:** Defines *how* we build it (steps, implementation details).

### 1.5 Explore Codebase for Context (When Needed)

Before leaving extensive feedback, explore the codebase to confirm:
- Existing patterns and conventions
- Feasibility and integration constraints
- Correct file paths, APIs, and data structures referenced by the spec/tasks

Use the Task tool with `subagent_type=Explore` to efficiently gather context.

### 1.6 Ask Clarifying Questions (When Needed)

If the spec is ambiguous or decisions are underspecified, ask clarifying questions *before* adding lots of inline comments. Batch related questions to minimize churn.

### 2. Review Specification (Critical Spec Review)

Read the specification first. Apply a **Critical Mindset**. Don't validate; look for problems.

**Look for:**
- **Gaps:** Missing requirements or edge cases.
- **Risks:** Security, performance, or integration issues.
- **Ambiguity:** Unclear success criteria or technical decisions.
- **Technical Debt:** Unrealistic assumptions or poor architectural choices.

**Add Comments:**
```markdown
[REVIEW:Name] SPEC GAPS: The spec mentions "user roles" but doesn't define permissions or hierarchy. [/REVIEW]
```

### 3. Review Tasks (Accuracy & Fidelity Check)

Now read the task list and **compare it line-by-line** against the specification.

**Verify:**
- **Fidelity:** Does the task list implement *exactly* what is specified?
- **No Scope Creep:** Flag tasks that add features not in the spec.
- **Correctness:** Are file paths, API shapes, and data structures consistent with the spec?
- **Logic:** Are the steps ordered correctly to match dependency requirements?

**Critical focus:** Accuracy over completeness.
- Do not add "missing task" comments just because the task list is incomplete.
- Only flag missing steps when their absence would cause an incorrect implementation (e.g., required dependency/order), or when it reveals a requirement missing/unclear in the spec.

**Add Comments:**
```markdown
[REVIEW:Name] INCORRECT: Task 2.3 adds "rate limiting" but the Spec explicitly excludes it in Section 4. [/REVIEW]
```

### 4. Cross-Verification

Ensure the two documents are in sync.
- If the spec changes (based on your feedback), the tasks will need to change. note this connection.
- If tasks reveal implementation details that contradict the high-level design, flag the discrepancy.

## Comment Guidelines

**Types of Issues to Flag:**
- **INCORRECT:** Factually wrong compared to spec or codebase.
- **SCOPE DRIFT:** Task goes beyond specification boundaries.
- **GAP (Spec):** Missing requirement, constraint, edge case, or success criteria in the specification.
- **RISK:** Security, performance, or integration concern.
- **AMBIGUITY:** Unclear requirement/decision that will confuse the developer.
- **MISINTERPRETATION (Tasks):** Task misunderstands the spec's intent.
- **CONTRADICTION (Tasks):** Task conflicts with another part of the spec.
- **WRONG REFERENCE (Tasks):** Incorrect file path, API, type, or component reference.

**Usage:**
- Insert tags directly into the documents.
- Use `[REVIEW:Name] Content [/REVIEW]` format.
- Be specific and actionable.
- Do not offer stylistic advice.

**Responding to other reviewers:**
- If you see comments from other reviewers, you may add your own comment agreeing/disagreeing or adding context.
- Format: `[REVIEW:Name] RE: [OtherReviewer] - <your response> [/REVIEW]`

## Example Comments

```markdown
[REVIEW:Claude] RISK: The spec allows public read access to /users, which exposes PII. Consider restricting to auth'd users. [/REVIEW]

[REVIEW:Claude] SCOPE DRIFT: Task mentions "implementing dark mode toggle", but the Spec "UI Requirements" section only mentions "inheriting system preference". [/REVIEW]

[REVIEW:Claude] INCORRECT: Task references `src/auth/login.ts`, but codebase analysis shows the file is `src/features/auth/login.tsx`. [/REVIEW]
```

## Summary

After adding comments to both files, provide a single summary to the user:
- **Spec status:** solid or needs rework?
- **Task status:** accurate reflection of spec or needs alignment?
- **Critical issues:** List the most important blockers.
- **Recommendation:** "Proceed with caution" or "Major revision needed".

---

## ➡️ Next Commands

Once reviews are complete, integrate the feedback:

```
/review:change-integrate <path to spec> <path to tasks>
```
