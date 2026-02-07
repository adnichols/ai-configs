---
description: Post-implementation verification against task list. Usage: [task file path]
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

### 4. Verify Each Phase

For each major task/phase:
- Check all subtasks marked complete
- Verify code changes exist for specified files
- Run relevant tests for this phase
- Confirm implementation matches spec requirements
- Report: status, evidence, issues found

### 5. Generate Validation Report

Create document at: `thoughts/validation/YYYY-MM-DD-validation.md`

```markdown
---
date: [ISO timestamp]
author: [codex]
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

### 6. Present Report

Present findings to user:
- Overall pass/fail status
- Key deviations found
- Manual tests needed
