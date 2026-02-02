---
description: Process a Beads Epic through execution, review, and integration cycles
argument-hint: "[epic_id] [instructions]"
---

# Process Beads Epic

Systematically execute a Beads Epic: implement step tasks, manage phase gates, and run the review/integrate loop.

**Input:** $ARGUMENTS

## Process

### 1. Assessment
1.  **Load:** `beads_show(issue_id=EPIC_ID)`.
2.  **Find Work:** `beads_ready` (filter for descendants of this Epic).

### 2. Execution Loop
Prioritize **Step Tasks** over **Phase Gates**.

#### A. Execute Step Tasks (Workers)
1.  **Claim:** `beads_update(status="in_progress")`.
2.  **Implement:** Code, Test, Verify (Apply user instructions).
3.  **Close:** `beads_close(reason="completed")`.

#### B. Process Phase Gates (Managers)
*Target: Tasks identified as "Gate: Phase X".*
*Condition: Only ready when all step tasks are closed.*

1.  **Review Protocol:**
    *   Self-review the phase work.
    *   *Implicitly runs `/dev:3:bd-review` logic.*
2.  **Integrate Findings:**
    *   If gaps found: Create new Step Tasks.
    *   **Crucial:** Use `/dev:3:bd-integrate` logic:
        *   New tasks must be children of the Gate (`parent-child`).
        *   The Gate must be BLOCKED BY the new tasks (`blocks`).
    *   *Result:* Gate becomes blocked. Loop back to Step A.
3.  **Close Gate:**
    *   If clean: `beads_close(reason="completed")`.
    *   *Effect:* Unblocks next Phase Gate.

### 3. Completion
When "Gate: Final Validation" is closed:
1.  **Verify:** Run validation command (`/dev:5:bd-validate <EPIC_ID>`).
2.  **Close Epic:** `beads_close(issue_id=EPIC_ID, reason="completed")`.
