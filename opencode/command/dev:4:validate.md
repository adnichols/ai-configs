---
description: Post-implementation verification against task list
argument-hint: "[task file path]"
---

# Validate Implementation

Verify that a task list was correctly executed. This provides independent verification after implementation.

Task file: $ARGUMENTS

## Process

### 1. Locate and Read Task List

If no argument provided, use the current active task list or search `thoughts/` for the most recent `task.md`.

Read the task file completely. Extract:
- All tasks and subtasks (items starting with `- [ ]` or `- [x]`)
- Any context or requirements blocks
- "Relevant Files" if listed

### 2. Gather Implementation Evidence

Run verification commands:

```bash
# Git history for changes
git log --oneline -20
git diff --stat HEAD~10

# Check for test results
# (Run project-specific test commands from CLAUDE.md)

# Check for build success
# (Run project-specific build commands from CLAUDE.md)
```

### 3. Verify Tasks

For each top-level task in the list:

1. **Check Completion Status**
   - Is the task marked as completed (`[x]`)?
   - Are all subtasks completed?

2. **Verify Deliverables**
   - If the task implies creating code, does that code exist?
   - If the task implies a fix, is there a regression test?

3. **Run Automated Verification**
   - Execute relevant tests
   - Verify build passes

4. **Assess Scope**
   - Did the implementation stay within the scope of the task?
   - Are there unrequested changes?

### Parallel Verification Strategy

Use the Task tool to spawn parallel verification subagents for efficient task-by-task validation.

#### Subagent Delegation

For each major task/phase, spawn a Task agent with `subagent_type=explore`:

```
Task: Verify Phase [N] - [Phase Name]
- Check all subtasks marked complete
- Verify code changes exist for specified files
- Run relevant tests for this phase
- Confirm implementation matches spec requirements
- Report: status, evidence, issues found
```

#### Orchestrator Responsibilities

The parent agent (you) handles:
- Running global verification commands (build, lint)
- Coordinating per-phase verification subagents  
- Synthesizing individual reports into final validation
- Generating the validation report document

Wait for ALL verification subagents to complete before synthesizing the final report.

### 4. Generate Validation Report

Create document at: `thoughts/validation/YYYY-MM-DD-validation.md`

```markdown
---
date: [ISO timestamp]
author: [claude]
git_commit: [Commit hash]
type: validation
status: [pass|fail|partial]
task_file: [Path to validated task file]
---

# Validation Report

## Source Task List
`[Path to task file]`

## Validation Summary

| Task | Status | Notes |
|------|--------|-------|
| [Task Name] | [pass/fail] | [Brief note] |
| [Task Name] | [pass/fail] | [Brief note] |

**Overall Status**: [PASS / FAIL / PARTIAL]

## Detailed Findings

### [Task Name]

**Status:** [Completed/Incomplete]

**Verification:**
- [ ] Task marked complete
- [ ] Requirements met
- [ ] Tests pass

**Evidence:**
- [Cite file changes or logs]

### [Task Name]
...

## Deviations & Issues

### Unexpected Changes
- [Changes not in task list]

### Missing Items
- [Tasks marked complete but missing evidence]

## Manual Verification Required
- [ ] [Item 1]

## Recommendations
[Next steps]
```

### 5. User Engagement for Concerning Patterns

When validation reveals issues that require user input, use **`question`** before finalizing the report.

**Failure Resolution Question (when validation fails):**
```
Question: "Validation found [N] issues. How should we proceed?"
Header: "Issues"
Options:
- Fix issues before finalizing (return to implementation)
- Mark as known issues and proceed
- Let me explain the issues in detail first
```

**Ambiguous Results Question (when evidence is unclear):**
```
Question: "I found [behavior] but I'm uncertain if it meets the requirement. Can you clarify?"
Header: "Clarify"
Options:
- Yes, this meets the requirement
- No, this needs to be fixed
- Show me more details
```

**Scope Deviation Question (when implementation differs from plan):**
```
Question: "The implementation includes [unexpected change]. Should this be documented as intentional?"
Header: "Deviation"
Options:
- Yes, it's an intentional improvement
- No, it should be reverted
- Mark for follow-up review
```

**Missing Evidence Question (when deliverables can't be verified):**
```
Question: "I can't find evidence for [task]. Help me locate it or confirm status?"
Header: "Missing"
Options:
- Point me to the right location
- The task was completed differently
- The task wasn't completed (reopen it)
```

### When to Engage During Validation

**Always Engage:**
- Validation status is FAIL or PARTIAL
- Major deviations from spec found
- Evidence is ambiguous or missing
- User decisions are needed to classify findings

**Present Report Without Blocking:**
- All validations pass cleanly
- Minor deviations documented in Deviations Log
- Clear evidence exists for all completed tasks

### 6. Present Report

Present findings to user:
- Overall pass/fail status
- Key deviations found
- Manual tests needed
- Any engagement questions from step 5
