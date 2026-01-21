---
description: Review a Beads epic and all subtasks against the spec review protocol
argument-hint: "[issue_id]"
---

# Beads Review Protocol

Review the specified Beads issue (Epic, Phase Gate, or Task) and its dependents to provide critical feedback.

**Target Issue:** $ARGUMENTS

## Process

### 1. Analyze Scope
1.  Run `beads_show(issue_id="$ARGUMENTS")`.
2.  If it's an Epic or Phase Gate, also run `beads_show` on its children to understand the full context.

### 2. Context & Codebase
Before commenting:
-   Read linked specs.
-   Search codebase for existing patterns/constraints.

### 3. Critical Review (The Protocol)
Find problems, gaps, and risks.
-   **Gaps:** Missing error handling, edge cases.
-   **Feasibility:** Is the approach viable?
-   **Integration:** Conflicts with other systems?
-   **Protocol:** Violations of spec rules.

### 4. Output: Feedback
For each concern, use `beads_update` to append a structured note.

**Format:**
`[REVIEW:REVIEWER_NAME] ...feedback... [/REVIEW]`

**Example:**
```python
beads_update(
    issue_id="NOD-123",
    notes="[REVIEW:OPENCODE] Performance: Verify DB index on user_id. [/REVIEW]"
)
```

### 5. Summary
Conclude with a recommendation: Proceed, Block, or Needs Info.
