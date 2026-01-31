---
description: Integrate review comments into a change (specification + tasks) and re-align tasks to the integrated spec
argument-hint: "<path to spec> <path to tasks>"
---

# Integrate Change Review Comments (Spec + Tasks)

Integrate all inline review comments across the specification and task list, producing a clean spec and a task list that accurately reflects the updated spec.

**Inputs:** $ARGUMENTS

## Core Rule

The **specification is the authority**. Integrate spec feedback first, then update tasks to match the integrated spec.

## Process

### 0. Resolve Inputs

Parse `$ARGUMENTS` into:
- `spec_path` (first argument)
- `tasks_path` (second argument)

If either path is missing/ambiguous, ask the user for the exact two paths before proceeding.

### 1. Read Both Documents

Read `spec_path` fully, then read `tasks_path` fully.

While reading, note:
- Any inline review tags
- Any references from the tasks file back to the spec (frontmatter `spec:` or "Source Specification:" line)

If the task list references a different spec path than `spec_path`, treat `spec_path` as canonical and plan to update the task list's reference to match it.

### 2. Extract Inline Review Comments (Both Files)

Scan both files for inline review tags (accept all of these):

Section-anchored (preferred for specs):
```markdown
[REVIEW:Reviewer Name] SECTION "Section Title": comment text [/REVIEW]
```

Line-anchored (preferred for tasks):
```markdown
[REVIEW:Reviewer Name] LINE 42: comment text [/REVIEW]
```

Fallback:
```markdown
[REVIEW:Reviewer Name] comment text [/REVIEW]
[REVIEW] comment text [/REVIEW]
```

Anchoring rules:
- Spec comments without `SECTION "..."`: attach to the nearest following header.
- Task comments without `LINE N`: attach to the nearest following task line.

If no inline review comments exist in either file, inform the user and abort (nothing to integrate).

### 3. Build a Single Working Catalog

Create one working list of all feedback items with:
- File (`spec` or `tasks`)
- Reviewer (or `Unspecified`)
- Anchor (SECTION/LINE/nearest header/nearest task)
- Category (use whatever the reviewer wrote; normalize mentally to: GAP / RISK / AMBIGUITY / INCORRECT / SCOPE DRIFT / MISINTERPRETATION / CONTRADICTION / WRONG REFERENCE)
- What must change (spec text change, task correction, or both)

Important: if a task comment reveals a spec ambiguity or missing requirement, treat that as a spec integration item first.

### 4. Explore Codebase Only When Needed

For any feedback that depends on feasibility or existing patterns, explore the codebase to resolve it.
Use the Task tool with `subagent_type=Explore` for fast repo research.

### 5. Triage by Confidence + Batch Questions

High confidence: resolve autonomously.
Low confidence (scope/product decisions, competing tradeoffs, spec ambiguity): batch into a single set of user questions (group related items).

### 6. Integrate Into the Specification (First)

For each spec-side item (and any task-side item that implies a spec change):
1. Locate the referenced section (or the nearest header anchor).
2. Update the spec to address the concern directly (add missing requirements, clarify success criteria, resolve contradictions).
3. Optionally add a short integration marker at the start of the section:
   ```markdown
   [REVIEW:Integrated feedback] {1-sentence description of what was resolved} [/REVIEW]
   ```
4. Remove the original inline review comment once resolved.

### 7. Update the Task List to Match the Integrated Spec (Second)

Now treat the integrated spec as the source of truth and update `tasks_path`:

1. Ensure the task list's source-spec reference matches `spec_path` (update frontmatter `spec:` if present, otherwise update/add the "Source Specification:" line).
2. For each task comment:
   - Verify against the integrated spec
   - Apply the appropriate fix (rewrite/remove/correct references) so the task matches the spec exactly
   - Remove the inline review comment once resolved
3. Do an additional pass over the tasks to catch silent drift introduced by spec integration (tasks that are now incorrect even if no comment exists).

### 8. Final Validation (Both Files)

Re-read both documents and verify:
- No `[REVIEW:...]` comments remain in either file
- The task list matches the integrated spec (no scope drift, no contradictions)
- Any spec changes that affect task ordering/dependencies are reflected in task sequencing

If integration fails mid-way, keep remaining inline review comments so the user can manually reconcile.

### 9. Summary Report

Report:
- Paths integrated (`spec_path`, `tasks_path`)
- Total comments processed, split by file and reviewer
- Key autonomous decisions made (brief)
- Any user decisions requested/used
- Confirmation that inline review comments were removed from both files
- Whether the change is now ready for implementation

---

## ➡️ Next Step

After successful integration:
```
/dev:3:process-tasks <path to tasks>
```

Stop there; do not proceed automatically.
