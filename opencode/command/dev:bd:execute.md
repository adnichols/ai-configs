---
description: Execute a Beads Epic by working through its ready tasks and phase gates
argument-hint: "[Epic ID] [Instructions]"
---

# Execute Beads Epic

Systematically execute a Beads Epic, handling implementation of step tasks and management of phase gates.

**Input:** $ARGUMENTS

## Process

### 1. Assessment

1.  **Parse Input:** Separate the Epic ID from any additional instructions.
2.  **Load Epic:** Use `beads_show(issue_id=EPIC_ID)` to understand the goal.
3.  **Find Work:** Use `beads_ready` to find unblocked tasks.
    *   **Filter:** Select only tasks that are descendants of the target Epic (check `parent` field or traverse down from Epic).

### 2. Execution Loop

Iterate through "Ready" tasks. **PRIORITIZE Step Tasks (Tier 3) over Phase Gates (Tier 2).**

#### A. Execute Step Tasks (The Workers)
*Target: Tasks that are NOT Phase Gates.*

1.  **Claim:** `beads_update(issue_id=TASK_ID, status="in_progress")`.
2.  **Context:** Read the task Description & Acceptance Criteria.
    *   *Apply User Instructions:* Incorporate any specific constraints or directives provided in the command arguments.
3.  **Implement:**
    *   Write Code.
    *   Write/Run Tests.
    *   Verify against Acceptance Criteria.
4.  **Close:**
    *   If successful: `beads_close(issue_id=TASK_ID, reason="completed")`.

#### B. Execute Phase Gates (The Managers)
*Target: Tasks identified as "Gate: Phase X".*

*Note: A Phase Gate only becomes "Ready" when all its Step Tasks are closed (because they block it).*

1.  **Review Protocol:**
    *   Perform a self-review of the phase's completed work.
    *   Check if the "Success Criteria" defined in the Gate task are met.
2.  **Integrate Findings:**
    *   **If gaps are found:** Create new Step Tasks (Tier 3) to fix them.
        *   Use `beads_create` + `beads_dep(dep_type="parent-child", depends_on=GATE_ID)`.
        *   **Crucial:** These new tasks must BLOCK the Gate (add `deps=[GATE_ID]` implies the gate waits for them? No, the *gate* depends on *tasks*).
        *   *Correction:* When creating the new fix task, add a blocking dependency: `beads_dep(issue_id=GATE_ID, depends_on_id=FIX_TASK_ID, dep_type="blocks")`.
        *   *Result:* The Gate becomes BLOCKED again. Loop back to Step A.
3.  **Close Gate:**
    *   If Review passes and no new work is needed: `beads_close(issue_id=GATE_ID, reason="completed")`.
    *   *Effect:* This unblocks the next Phase Gate (and thus the next phase's Step Tasks).

### 3. Handling Blockers

If `beads_ready` returns no relevant tasks but the Epic is not closed:
1.  **Diagnose:** Check `beads_blocked` or `beads_show` on the current Phase Gate.
2.  **Fix:**
    *   Are dependencies missing?
    *   Did a task fail to close?
    *   Resolve the blocker or ask the user.

### 4. Completion

When the "Gate: Final Validation" is closed:
1.  **Verify:** Run the final validation command mentioned in the gate description.
2.  **Close Epic:** `beads_close(issue_id=EPIC_ID, reason="completed")`.

## Agent Instructions

-   **Autonomy:** You are authorized to write code, run tests, and manage issue state.
-   **Safety:** Always run tests before closing a Step Task.
-   **Structure:** Respect the 3-Tier structure. New tasks must be children of their Phase Gate.
-   **Review:** Treat Phase Gates as serious checkpoints. Do not close them if the phase's work is incomplete or buggy.
