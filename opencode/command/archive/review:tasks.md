---
description: Review task list for accuracy against source specification
argument-hint: "<path to task list>"
---

# Task List Accuracy Review

Review the task list to ensure it accurately reflects the source specification. Focus on **incorrect details** that would lead to wrong implementations.

**Task list to review:** $ARGUMENTS

## Your Identity

You are **Claude** reviewing this task list. All comments you add must be clearly attributed to you.

## Critical Focus: Accuracy Over Completeness

This review is NOT about finding missing tasks or gaps. Missing details can be filled in from the spec during implementation.

This review IS about finding **incorrect details** that would cause the implementation to diverge from what the specification actually requires:

- Misinterpreted requirements
- Wrong technical approaches that contradict the spec
- Scope drift (tasks that go beyond what spec specifies)
- Inverted logic or reversed conditions
- Wrong file paths, API shapes, or data structures
- Contradictions between task descriptions and spec intent

## Process

### 1. Read Both Documents

First, read the task list completely. Determine the **Source Specification** path using one of:

- YAML frontmatter key `spec:` (preferred)
- A "Source Specification:" line in the document body (fallback).

Then read the source specification in full to understand:
- The exact requirements as written
- Technical decisions and constraints
- Explicit scope boundaries
- Success criteria

### 2. Compare Line by Line

For each task and subtask, verify:
- Does the task description match the specification's intent?
- Are technical details (file paths, API shapes, data types) correct?
- Does the scope stay within specification boundaries?
- Are conditions and logic correctly interpreted?

### 3. Add Comments for Inaccuracies

Insert review tags directly into the task list document for any inaccuracies found:

```markdown
[REVIEW:Claude] INCORRECT: Task says "create new auth middleware" but spec says
"extend existing auth middleware in src/middleware/auth.ts". [/REVIEW]

[REVIEW:Claude] SCOPE DRIFT: This task adds rate limiting but the specification
explicitly excludes rate limiting from this phase. [/REVIEW]

[REVIEW:Claude] MISINTERPRETATION: Spec requires "soft delete" (set deleted_at)
but task describes "hard delete" (remove from database). [/REVIEW]
```

### Comment Types

**INCORRECT** - Factually wrong compared to spec
**SCOPE DRIFT** - Task goes beyond specification boundaries
**MISINTERPRETATION** - Task misunderstands the spec's intent
**CONTRADICTION** - Task conflicts with another part of the spec
**WRONG REFERENCE** - File path, API, or component reference is wrong

### 4. Respond to Other Reviewers

If you see comments from other reviewers (Gemini, Codex, GPT, etc.):

```markdown
[REVIEW:Claude] RE: [Gemini] - I agree this is incorrect. The spec clearly states... [/REVIEW]
```

## Comment Guidelines

**DO:**
- Flag tasks that would produce wrong implementations
- Identify misinterpretations of specification intent
- Point out scope drift beyond specification
- Catch wrong technical details (paths, APIs, types)
- Note contradictions with the source specification

**DON'T:**
- Add comments about missing tasks (spec can fill those in)
- Suggest improvements beyond what spec requires
- Modify or delete comments from other reviewers
- Make stylistic suggestions about task wording

## Comment Placement

Place comments:
- **Immediately after the incorrect task** - for task-specific issues
- **Under phase headers** - for phase-level inaccuracies
- **At the end** - for cross-cutting accuracy concerns

## Example Comments

```markdown
[REVIEW:Claude] INCORRECT: Task 2.3 says "add JWT validation" but spec section 3.2
explicitly states "use session-based auth, not JWT". [/REVIEW]

[REVIEW:Claude] WRONG REFERENCE: Task references "src/services/userService.ts" but
codebase analysis shows this is "src/services/user.service.ts". [/REVIEW]

[REVIEW:Claude] SCOPE DRIFT: The specification's "Excluded" section lists "admin
dashboard" but Task 4.2 includes admin UI components. [/REVIEW]

[REVIEW:Claude] MISINTERPRETATION: Spec says "cache for 5 minutes" but task says
"cache indefinitely with manual invalidation". [/REVIEW]

[REVIEW:Claude] RE: [Codex] - Confirmed. The API response shape in Task 3.1 doesn't
match the interface defined in the specification's Technical Details section. [/REVIEW]
```

## Summary

After adding all comments, provide a brief summary to the user:
- Number of inaccuracies found
- Critical errors that would cause wrong implementations
- Tasks that should be corrected before implementation
- Whether the task list is safe to proceed with (after corrections)

---

## ➡️ Next Command

After all reviewers complete their task list reviews, integrate the corrections:
```
/review:tasks-integrate <path to task list>
```

Then proceed with implementation:
```
/dev:3:process-tasks <path to task list>
```
