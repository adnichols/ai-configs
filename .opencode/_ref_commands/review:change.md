---
description: Comprehensive review of a change (specification + tasks) for accuracy and completeness
argument-hint: "<path to spec> <path to tasks>"
---

# Change Review (Spec + Tasks)

Review the provided specification and task list as a cohesive unit. Your goal is to ensure the specification is solid and the tasks accurately reflect that specification without scope creep or error.

**Documents to review:** $ARGUMENTS

## Your Identity

If you selected a reviewer subagent, use its friendly name for comment attribution (e.g., `[REVIEW:SecurityBot]`). If no subagent is selected, use **OPENCODE**.

## Process

### 1. Analyze Context & Categorize

First, identify the provided files:
- **Specification:** Defines *what* we are building (requirements, design, scope).
- **Task List:** Defines *how* we build it (steps, implementation details).

### 2. Review Specification (Critical Spec Review)

Read the specification first. Apply a **Critical Mindset**. Don't validiate; look for problems.

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
- **GAP:** Missing requirement in spec or missing step in tasks.
- **RISK:** Security or performance concern.
- **AMBIGUITY:** Unclear instruction that will confuse the developer.

**Usage:**
- Insert tags directly into the documents.
- Use `[REVIEW:Name] Content [/REVIEW]` format.
- Be specific and actionable.
- Do not offer stylistic advice.

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
