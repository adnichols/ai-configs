---
description: Convert specification into a Beads Epic with parallel execution phases and review gates
argument-hint: "[Specification File Path]"
---

# Rule: Convert Specification to Beads Epic

## Goal

Translate a Specification Document into a live Beads Execution Graph. This graph must support **parallel work** where possible and enforce **review gates** between phases to capture learnings.

## Input

**Specification File:** $ARGUMENTS

## Process

### 1. Structure: 3 Tiers Per Spec

You will create exactly three tiers of issues. Do not flatten the graph.

**Tier 1: Epic (The Container)**
-   **Type:** `epic`
-   **Role:** Represents the entire specification.
-   **Children:** Contains ONLY "Phase Gate" tasks as direct children.

**Tier 2: Phase Gate Tasks (The Managers)**
-   **Type:** `task`
-   **Role:** Represents phase completion, success criteria, and the review gate.
-   **Parent:** The Epic (Tier 1).
-   **Dependencies:**
    -   Blocked by ALL "Step Tasks" (Tier 3) within its phase.
    -   Blocked by the *Previous Phase Gate* (Tier 2).

**Tier 3: Step Tasks (The Workers)**
-   **Type:** `task` (or `bug`)
-   **Role:** Atomic work items.
-   **Parent:** The "Phase Gate" task (Tier 2) for their specific phase.
-   **Dependencies:**
    -   Blocked by the *Previous Phase Gate* (Tier 2).
    -   Parallel Execution: Step tasks within a phase do NOT block each other unless strictly necessary.

### 2. Relationship Semantics (Non-negotiable)

Beads has two distinct relationship types. They are **NOT** interchangeable.

1.  **Structural Parentage (Non-blocking):**
    -   Use `beads_dep(..., dep_type="parent-child")` to represent parent/child.
    -   **CRITICAL:** This must NEVER be represented using `deps` on `beads_create`.
    -   **CRITICAL:** Do NOT make any task depend on its parent (no child should be blocked by its parent).

2.  **Blocking Dependencies (Execution Ordering):**
    -   Use `deps: [...]` on `beads_create` (or `beads_dep` with `dep_type="blocks"`) ONLY for "blocked by" relationships.
    -   **WARNING:** `beads_dep` defaults to `blocks` if `dep_type` is omitted. Always specify `dep_type` explicitly.

### 3. Execution Steps

Use the `task` tool with `subagent_type="beads-task-agent"` to perform the following operations strictly in order.

#### Step A: Create the Epic (Tier 1)
1.  Create the container Epic.
2.  **Title:** Same as Spec Title.
3.  **Type:** `epic`
4.  **Description:**
    > **Source Specification:** [Link to Spec File]($ARGUMENTS)
    >
    > **Summary:**
    > [Brief summary of the spec]
5.  *Capture the Epic ID.*

#### Step B: Phase 0 (Infrastructure)
*If spec has prerequisites:*
1.  **Create Phase 0 Gate:**
    -   **Title:** "Gate: Phase 0 (Infrastructure)"
    -   **Type:** `task`
    -   **Link to Epic:** `beads_dep(issue_id=<gate_id>, depends_on_id=<epic_id>, dep_type="parent-child")`
2.  **Create Step Tasks:**
    -   Create `task` issues for verification items.
    -   **Link to Phase Gate:** `beads_dep(issue_id=<step_id>, depends_on_id=<gate_id>, dep_type="parent-child")`
    -   **Blockers:** The Phase Gate is BLOCKED BY all these Step Tasks.
        `beads_dep(issue_id=<gate_id>, depends_on_id=<step_id>, dep_type="blocks")`

#### Step C: Implementation Phases (Iterate 1 to N)
For each Phase $N$:

1.  **Create Phase $N$ Gate (Tier 2):**
    -   **Title:** "Gate: Phase $N$"
    -   **Type:** `task`
    -   **Description:**
        > **Goal:** [Phase Goal]
        > **Success Criteria:** [List from Spec]
        > **Retrospective:**
        > 1. Review completed work against Spec Phase $N$.
        > 2. Identify deviations, decisions, or new constraints.
        > 3. Update Graph if learnings affect Phase $N+1$.
    -   **Link to Epic:** `beads_dep(issue_id=<gate_id>, depends_on_id=<epic_id>, dep_type="parent-child")`
    -   **Blockers:**
        -   Blocked by **Phase $(N-1)$ Gate**. (Enforces strict sequencing of phases).
        `beads_dep(issue_id=<gate_id>, depends_on_id=<prev_gate_id>, dep_type="blocks")`

2.  **Create Step Tasks (Tier 3):**
    -   Create issues for atomic work items.
    -   **Link to Phase Gate:** `beads_dep(issue_id=<step_id>, depends_on_id=<gate_id>, dep_type="parent-child")`
    -   **Blockers:**
        -   Blocked by **Phase $(N-1)$ Gate**. (Ensures steps don't start until previous phase is signed off).
        `beads_dep(issue_id=<step_id>, depends_on_id=<prev_gate_id>, dep_type="blocks")`
        -   The **Phase $N$ Gate** is BLOCKED BY these Step Tasks.
        `beads_dep(issue_id=<gate_id>, depends_on_id=<step_id>, dep_type="blocks")`

#### Step D: Final Validation
Treat "Final Validation" as the final Phase.
1.  **Create Final Gate:**
    -   **Title:** "Gate: Final Validation"
    -   **Type:** `task`
    -   **Link to Epic:** `beads_dep(issue_id=<gate_id>, depends_on_id=<epic_id>, dep_type="parent-child")`
    -   **Blockers:** Blocked by **Phase $N$ (Last Implementation) Gate**.
2.  **Create Validation Step:**
    -   **Title:** "Run Validation Command"
    -   **Description:** "Run validation using `/dev:5:bd-validate <EPIC_ID>`"
    -   **Type:** `task`
    -   **Link to Final Gate:** `beads_dep(issue_id=<step_id>, depends_on_id=<final_gate_id>, dep_type="parent-child")`
    -   **Blockers:** Blocked by **Phase $N$ (Last Implementation) Gate**.
    -   **Note:** The Final Gate is blocked by this step.

#### Step E: Handover
1.  Verify the graph structure using `beads_show(issue_id=<epic_id>)`.
2.  Instruct the user: "Graph created. To begin execution, run: `/dev:4:bd-process <EPIC_ID>`"
