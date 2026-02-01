---
description: Post-implementation verification of a Beads Epic
argument-hint: "[Epic ID]"
---

# Validate Beads Epic

Verify that a Beads Epic was correctly executed by validating all its Phase Gates and Step Tasks against implementation evidence. This provides independent verification after implementation.

**Epic:** $ARGUMENTS

## Process

### 1. Structure Discovery

1.  **Load Epic:** `beads_show(issue_id=EPIC_ID)`.
    -   Extract the "Source Specification" link from the description.
    -   Identify all child "Phase Gate" tasks (Tier 2).

2.  **Traverse Phases:**
    -   For each Phase Gate, identify all child "Step Tasks" (Tier 3).
    -   Construct a complete hierarchy map: `Epic -> Phase Gates -> Step Tasks`.

### 2. Gather Evidence

Run global verification commands to establish the codebase state:

```bash
# Recent changes context
git log --oneline -20
git diff --stat HEAD~10

# Run project verification (from CLAUDE.md)
# (Execute the standard test/lint/build commands for this repo)
```

### 3. Verify Phases (Parallel Execution)

Use the Task tool to spawn parallel verification subagents for each **Phase Gate**.

#### Subagent Delegation
For each Phase Gate, spawn a Task agent with `subagent_type="explore"`:

```
Task: Verify Phase Gate [GATE_ID] - [Gate Title]
Context:
- Parent Spec: [Link to Spec]
- Phase Gate Description (Success Criteria)
- List of Step Tasks (IDs + Acceptance Criteria)

Instructions:
1. Verify Gate Status: Is the gate closed?
2. Verify Step Tasks:
   - Are all step tasks closed?
   - For each task, does the code implementation match the Acceptance Criteria?
   - Do specific deliverables (files, functions, endpoints) exist?
3. Run Phase-Specific Tests: Execute relevant tests for this phase's scope.
4. Report:
   - Status: PASS / FAIL / PARTIAL
   - Evidence: Cite specific files/commits/logs.
   - Issues: List missing items or deviations.
```

#### Orchestrator Responsibilities
The parent agent (you) handles:
-   Running global checks.
-   Synthesizing subagent reports.
-   Generating the final document.
-   Engaging the user for resolution.

### 4. Generate Validation Report

Create document at: `thoughts/validation/YYYY-MM-DD-bd-validate-[EPIC_ID].md`

```markdown
---
date: [ISO timestamp]
author: [claude]
git_commit: [Commit hash]
type: bd-validation
epic_id: [EPIC_ID]
source_spec: [Path/Link]
status: [PASS/FAIL/PARTIAL]
---

# Validation Report: [Epic Title]

## Validation Summary

| Phase | Status | Issues | Notes |
|-------|--------|--------|-------|
| [Phase 1 Gate] | [PASS] | 0 | [Brief note] |
| [Phase 2 Gate] | [FAIL] | 1 | [Brief note] |

**Overall Status**: [PASS / FAIL / PARTIAL]

## Detailed Findings

### Phase [N]: [Gate Title]
**Gate Status:** [Closed/Open]

#### Step Tasks Verification
- [TASK-ID] [Task Name]
  - **Status:** [Closed/Open]
  - **Verification:**
    - [x] AC 1: [Evidence/Citation]
    - [ ] AC 2: [Missing Evidence]

#### Issues Found
- [Issue Description]

### Phase [M]...
...

## Recommendations
[Next steps / Fixes required]
```

### 5. User Engagement (Resolution Gates)

When validation reveals issues, use `question` to resolve them before finalizing.

**Failure Resolution (Status: FAIL/PARTIAL):**
```
Question: "Validation found [N] issues in Epic [ID]. How should we proceed?"
Header: "Validation Issues"
Options:
- Fix issues before finalizing (reopen tasks)
- Mark as known issues and proceed (pass with caveats)
- Let me explain the issues in detail
```

**Missing Evidence:**
```
Question: "I can't verify [TASK-ID]: [Task Name]. Help me locate evidence?"
Header: "Missing Evidence"
Options:
- Point me to the right location
- Task was completed differently
- Reopen the task
```

**Scope Deviation:**
```
Question: "Implementation of [TASK-ID] differs from spec. Is this intentional?"
Header: "Deviation"
Options:
- Yes, intentional improvement
- No, should be reverted
- Mark for follow-up review
```

### 6. Presentation

Present the final report summary to the user:
-   Link to the generated report file.
-   Highlight any failures or blocked items.
-   Confirm if the Epic is truly "Done".
