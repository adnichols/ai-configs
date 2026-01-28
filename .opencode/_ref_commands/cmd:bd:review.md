---
description: Review a Beads epic and all subtasks against the spec review protocol
argument-hint: "[epic_id]"
---

# Beads Epic & Task Review

Review the specified Beads epic and all its subtasks (dependents) to provide critical feedback.

**Epic ID:** $ARGUMENTS

## Your Identity

If you selected a reviewer subagent, use its friendly name for comment attribution. If no subagent is selected, use **OPENCODE** as the reviewer name.

## Process

### 1. Analyze the Work Scope

1. Run `beads_show(issue_id="$ARGUMENTS")` to retrieve the epic and identify its child tasks.
2. Run `beads_show(issue_id=child_id)` for every child task to get their full descriptions and acceptance criteria.
3. Construct a mental model of the entire deliverable.

### 2. Explore Context

Before providing feedback, explore the codebase and documentation:
- Read any specification files linked or referenced in the issues.
- Search for relevant existing code (patterns, components, stores) that informs feasibility.
- Check for existing tests or similar features.

### 3. Analyze Critically (The Review Protocol)

Your role is to find problems, not just validate. Look for:
- **Gaps:** Missing requirements or edge cases (e.g., error handling, empty states).
- **Feasibility:** Technical approaches that contradict the codebase or are over-complex.
- **Integration:** Conflicts with other systems (e.g., auth, routing, real-time store).
- **Risks:** Security, performance, or data integrity risks.
- **Protocol:** violations of the spec (e.g., "no client cascades", "server-side only").

### 4. Output: Feedback via Beads

For each issue (Epic or Task) where you have concerns:

1. Draft a structured note using the review tag format.
2. **Execute** the update using the `beads_update` tool:
   - `issue_id`: <id>
   - `notes`: "[REVIEW:REVIEWER_NAME] ... your feedback ... [/REVIEW]"

### 5. Summary

Conclude with a summary:
- Total issues reviewed.
- Key risks identified.
- Recommendation (Proceed / Block / Needs Info).

---

## Example Feedback Note

```python
beads_update(
    issue_id="NOD-123",
    notes="[REVIEW:OPENCODE] Performance: The no-store policy on GET /api/docs may increase latency. Verify DB query performance. [/REVIEW]"
)
```
