---
description: Integrate review feedback into Beads issues
argument-hint: "[issue_id]"
---

# Integrate Beads Feedback

Process review notes (tagged `[REVIEW:...]`) into actual issue updates or new work items.

**Target Issue:** $ARGUMENTS

## Process

### 1. Retrieve & Extract
1.  Run `beads_show` on the target and its dependents.
2.  Find `[REVIEW:...]` blocks in `notes` or recent activity.

### 2. Resolution Strategy

#### A. Updates (Clarification)
If feedback is about clarity or constraints:
1.  Verify against codebase/spec.
2.  Use `beads_update(acceptance_criteria="...")` to append the constraint.
3.  Add a resolution note.

#### B. New Scope (New Tasks)
If feedback requires new work (e.g., "Fix X", "Add Y"):
1.  **Create:** `beads_create` a new task.
2.  **Link Structure (Parent-Child):**
    `beads_dep(issue_id=NEW_TASK_ID, depends_on_id=TARGET_ID, dep_type="parent-child")`
3.  **Link Scheduling (Blocking):**
    *If the Target is a Phase Gate or Epic that must wait for this work:*
    `beads_dep(issue_id=TARGET_ID, depends_on_id=NEW_TASK_ID, dep_type="blocks")`
    *(Crucial: The Gate is blocked BY the new task).*

#### C. Dispute / Low Confidence
-   If unsure, use the `question` tool to ask the user.

### 3. Execution
Perform the updates using `beads_update`, `beads_create`, and `beads_dep`.

### 4. Summary
Report what was updated and any new tasks created.
