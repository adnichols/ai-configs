<!--
description: Integrate review feedback into Beads issues (Epic & Tasks)
-->

# Integrate Beads Review Feedback

Integrate review feedback notes (tagged blocks) from a Beads epic and its subtasks into the actual issue descriptions and acceptance criteria, or create new tasks for out-of-scope feedback.

**Target Issue/Epic:** $ARGUMENTS

## Process

### 1. Retrieve Context

1. Run `beads_show(issue_id="$ARGUMENTS")` to get the target issue.
2. If it is an Epic, also run `beads_show(issue_id=child_id)` for all its dependents to find feedback on them.
3. **Crucial:** Look for the `notes` field or recent activity containing feedback blocks starting with `[REVIEW:`.

### 2. Extract Feedback

For each issue with feedback notes:
1. Parse the feedback points from the review blocks (e.g., `[REVIEW:OPENCODE] ... [/REVIEW]`).
2. Categorize each point:
   - **Clarification/Constraint:** Needs update to `description` or `acceptance_criteria`.
   - **New Scope:** Needs a new dependent task.
   - **Open Question:** Needs user input.

### 3. Resolution Strategy

#### A. High Confidence (Autonomous)
- **Codebase/Pattern Checks:** If feedback asks to "verify X" or "ensure Y", use your tools (`grep`, `read`) to verify it against the codebase.
- **Spec Verification:** If feedback claims conflict with requirements, check any linked spec documents or the parent Epic description.
- **Updates:** If verified, use the `beads_update` tool to update the issue.
  - *Tip:* Append clarifications to "Acceptance Criteria" for visibility.

#### B. Dispute Resolution
- If reviewers disagree or feedback contradicts the current state:
  1. **Investigate Codebase:** Check the actual code implementation to see which reviewer/claim is factually correct.
  2. **Check Specifications:** Check linked specs or parent issues for authoritative requirements.
  3. **Escalate:** If neither code nor specs resolve the conflict, treat this as Low Confidence and ask the user.

#### C. New Scope (Create Tasks)
- If feedback requires significant new work (e.g., "Add a new endpoint", "Create a migration script") that doesn't fit the current task:
  1. **Create:** Use `beads_create` to make the new task.
  2. **Link:** Use `beads_dep` to link it to the parent:
     - `issue_id`: <new_task_id>
     - `depends_on_id`: "$ARGUMENTS" (or the appropriate parent ID)
     - `dep_type`: "parent-child"
     - **CRITICAL:** Do NOT use the default blocking dependency for parentage. The Epic/Parent should NOT be blocked by this new task unless it is a strict prerequisite for the parent's completion.

#### D. Low Confidence (Ask User)
- If feedback involves product decisions (e.g., "Should we allow X?"), ambiguous requirements, or conflicting information:
  1. Use the `question` tool to ask the user for clarification.
  2. Use the answer to determine the correct resolution.

## Decision-Making Guidelines

**When to ask the user:**
- **Ambiguity:** If the feedback is unclear or can be interpreted in multiple ways.
- **Conflict:** If the feedback contradicts the existing specification or other instructions.
- **Product Decisions:** If the feedback suggests a change in product behavior that isn't purely technical (e.g., "Remove this feature").
- **Scope Creep:** If the feedback requests significant new functionality that might belong in a future epic.

**Always use the `question` tool to resolve these uncertainties before proceeding with updates.**

### 4. Integration Execution

For each issue, use the native Beads tools.

**Example Update:**
```python
# Append to Acceptance Criteria
new_ac = "- Original AC...\n- [Integrated Feedback] New constraint verified against codebase."
beads_update(issue_id=id, acceptance_criteria=new_ac)
```

**Example Resolution Note:**
After updating, add a resolution note to track history:
```python
beads_update(issue_id=id, notes="Resolution: Integrated [REVIEW:OPENCODE] feedback into Acceptance Criteria.")
```

### 5. Summary

Provide a report:
- **Issues Updated:** List IDs and what changed.
- **New Tasks:** List any new tasks created.
- **Open Questions:** Any items waiting on user input.

---

## ➡️ Next Steps

If all feedback is integrated:
- Run `beads_ready` to see what is unblocked.
- Start coding!
