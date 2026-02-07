---
description: Process and execute a code simplification plan created by simplify:create-plan.md. Usage: [Plan file path] [Options: NOSUBCONF]
---

# Instructions

Execute the code simplification plan step by step according to the Plan Processing Protocol below.
$ARGUMENTS. Think harder.

<skip_subtask_confirmation>
If $ARGUMENTS contains NOSUBCONF then ignore step confirmation in plan execution below
</skip_subtask_confirmation>

<plan_file_tracking>
CRITICAL: Always track and update the plan file throughout execution:
- Extract plan file path from first argument
- Store plan file path as PLAN_FILE variable
- Update checkboxes using search_replace tool after each completed step
- Verify checkbox updates by reading back the plan file
- Never lose track of which plan file you're processing
</plan_file_tracking>

# Plan Processing Protocol

Guidelines for safely executing code simplification plans while preserving functionality and tracking progress.

## Critical Safety Requirements

### Functionality Preservation Protocol
1. **Baseline Establishment:**
   - Run full test suite BEFORE any changes
   - Document current system state and behavior
   - Establish performance benchmarks
   - Record current test coverage metrics

2. **Change Validation:**
   - Run full test suite AFTER each major step
   - Compare results to baseline - ANY degradation = STOP
   - Validate integration points remain functional
   - Verify performance regressions are within acceptable bounds

3. **Failure Response:**
   - If ANY test fails that previously passed: **STOP IMMEDIATELY**
   - Do not continue to next step
   - Alert user with specific failure details
   - Provide rollback instructions
   - Wait for user decision before proceeding

## Plan Execution Rules

### Branch Management
- Do not proceed unless you are on a git branch other than main
- If needed, create a branch specifically for this simplification work
- Branch naming: `simplify/[area-name]-[date]`

### Step-by-Step Execution
- **Execute steps IN ORDER:** Follow the checklist sequence exactly
- **One step at a time:** Complete current step fully before starting next
- **No delegation:** Do NOT delegate execution to subagents - execute directly
- **IMMEDIATE Progress tracking:** Update checkbox to `[x]` using search_replace tool THE MOMENT each sub-task is done
- **NO BATCHING:** Never wait until end of phase to update multiple checkboxes - update each one immediately
- **Real-time visibility:** User should see progress in real-time by checking the plan file

### Confirmation Protocol
- **Stop after each major step** and wait for user's go-ahead
- **UNLESS NOSUBCONF is specified:** Then proceed automatically between steps
- **Always stop after phases complete:** Wait for user confirmation between phases
- **Always stop on any test failure:** Immediate user notification required

## Checkbox Update Protocol

### CRITICAL: Plan File Checkbox Management

**Before Starting Any Plan Processing:**
1. **Extract Plan File Path:** Get the plan file path from the first argument
2. **Store as Variable:** Maintain PLAN_FILE variable throughout execution
3. **Initial Verification:** Read the plan file to understand current state

**For Each Completed Step:**
1. **Identify Target Checkbox:** Locate the specific `- [ ]` checkbox for the completed step
2. **Use search_replace Tool:** Replace `- [ ]` with `- [x]` for that specific step
3. **Include Sufficient Context:** Use enough surrounding text to make the replacement unique
4. **Verify Update:** Read back the modified section to confirm checkbox was updated
5. **Handle Nested Checkboxes:** For sub-items, update both the sub-item and parent as appropriate

**Example Real-Time Checkbox Update Workflow:**
```
# Step 1: Start sub-task
"I'm now working on P2.1 - Create tests/debug/ directory"

# Step 2: Complete the sub-task
[Execute: mkdir tests/debug/]

# Step 3: IMMEDIATELY update checkbox (DO NOT WAIT)
[Use search_replace to change:]
Old: "- [ ] Create `tests/debug/` directory"
New: "- [x] Create `tests/debug/` directory"

# Step 4: Verify update worked
[Read plan file to confirm checkbox is now [x]]

# Step 5: Move to next sub-task
"Now I'm working on the next sub-task: Copy test files"

# WRONG APPROACH:
"I'll complete all the file operations and then update all checkboxes at once"

# CORRECT APPROACH:
Complete one thing → Update one checkbox → Complete next thing → Update next checkbox
```

**Troubleshooting Failed Updates:**
- If search_replace fails, read the plan file again to see current state
- Check for formatting differences (spaces, indentation, text variations)
- Use more specific context to make the target unique
- Try updating sub-items first, then parent items
- If still failing, try updating with more surrounding context lines
- **NEVER SKIP CHECKBOX UPDATES** - if all else fails, ask user for help with the specific update
- Document the exact error and what you tried for user assistance

## Step Processing Workflow

### For Each Step in the Plan:

1. **Pre-Step Verification:**
   ```
   - [ ] Current step: [Step Description]
   - [ ] Verify all prerequisite steps are complete
   - [ ] Run baseline tests if this is a code-changing step
   - [ ] Document current state
   ```

2. **Step Execution:**
   ```
   - [ ] Execute the specific step actions
   - [ ] For code changes: Implement changes directly (no subagent delegation)
   - [ ] For test creation: Write tests directly
   - [ ] For verification: Run specified validation
   - [ ] IMMEDIATELY after completion: Update checkbox from [ ] to [x] using search_replace
   - [ ] Verify the checkbox update was successful by reading the plan file
   ```

3. **Post-Step Validation:**
   ```
   - [ ] Mark step as completed [x] in plan file using search_replace tool
   - [ ] Verify checkbox update by reading plan file section
   - [ ] Run test suite if code was modified
   - [ ] Compare results to baseline
   - [ ] Document any changes or observations
   - [ ] Update "Relevant Files" section
   ```

4. **Safety Gate:**
   ```
   - [ ] All tests pass (or explain any expected changes)
   - [ ] No functionality regressions detected
   - [ ] Performance within acceptable bounds
   - [ ] Integration points still functional
   ```

5. **Progress Update:**
   ```
   - [ ] Update plan file with completed step
   - [ ] Add any newly discovered issues or risks
   - [ ] Note time taken and any challenges encountered
   ```

**MANDATORY CHECKPOINT - DO NOT PROCEED TO NEXT STEP UNTIL:**
- [ ] Current step checkbox is marked [x] in the plan file
- [ ] Checkbox update has been verified by reading the plan file back
- [ ] User can see progress by checking the plan file

**ANTI-BATCHING ENFORCEMENT:**
- ❌ WRONG: Complete 5 sub-tasks, then update all 5 checkboxes at once
- ✅ CORRECT: Complete sub-task 1 → Update checkbox 1 → Complete sub-task 2 → Update checkbox 2 → etc.
- ❌ WRONG: "I'll update all the checkboxes after I finish this phase"
- ✅ CORRECT: "I just completed task X, let me update its checkbox immediately"

## Phase Completion Protocol

When all steps in a phase are marked `[x]`:

1. **Full Validation:**
   - Run complete test suite as defined in TESTING.md or CLAUDE.md
   - Verify all functionality preservation requirements
   - Check performance benchmarks
   - Validate integration points

2. **Git Management:**
   - Stage changes: `git add .`
   - Clean up temporary files and artifacts
   - Commit with descriptive message using conventional format:
     ```
     git commit -m "refactor: [phase description]" -m "- [key changes made]" -m "- [preservation verifications]" -m "Related to simplify-plan-[area-name]"
     ```

3. **Documentation:**
   - Update plan file with phase completion
   - Document any lessons learned or issues encountered
   - Update risk assessment if needed

4. **User Confirmation:**
   - Always stop and wait for user approval before next phase
   - Provide summary of phase accomplishments
   - Highlight any concerns or deviations from plan

## Progress Tracking

### Plan File Maintenance
1. **Real-time Updates:**
   - Mark steps `[x]` immediately upon completion using search_replace tool
   - Verify each checkbox update by reading the modified section back
   - Add newly discovered tasks as they emerge
   - Update risk assessments based on findings
   - NEVER skip checkbox updates - they are required for progress tracking

2. **Relevant Files Section:**
   - List every file created, modified, or deleted
   - Provide one-line description of changes made
   - Track test files separately from implementation files

3. **Issues and Risks Section:**
   - Document any unexpected challenges
   - Record deviations from original plan
   - Note any functionality concerns discovered

## Error Handling and Recovery

### Test Failure Response
1. **Immediate Actions:**
   - Stop all further execution
   - Document the exact test failure details
   - Identify what changed since last successful test run
   - Capture system state for debugging

2. **User Communication:**
   - Alert user with clear failure description
   - Provide specific error messages and logs
   - Suggest potential rollback options
   - Wait for explicit user decision on how to proceed

3. **Recovery Options:**
   - Rollback last change and retry
   - Debug and fix the issue before continuing
   - Skip problematic step and mark as deferred
   - Abort simplification plan entirely

### Git Safety Net
- Each phase should be a clean commit point
- Easy rollback to any previous stable state
- Clear commit messages for easy navigation
- Branch isolation from main codebase

## Success Criteria

A step is considered complete when:
- [ ] All step actions have been executed
- [ ] Step is marked `[x]` in plan file using search_replace tool
- [ ] Checkbox update verified by reading plan file back
- [ ] All tests pass (or degradation is explained and approved)
- [ ] No functionality regressions detected
- [ ] User has confirmed (unless NOSUBCONF specified)

A phase is considered complete when:
- [ ] All steps in phase are marked `[x]`
- [ ] Full test suite passes
- [ ] Git commit created with changes
- [ ] Documentation updated
- [ ] User approval received for next phase

The entire plan is complete when:
- [ ] All phases marked complete
- [ ] Final integration testing passed
- [ ] Performance benchmarks maintained
- [ ] All temporary artifacts cleaned up
- [ ] Completion documented in plan file

## Plan Processing Initialization

### REQUIRED: Start of Plan Processing Workflow

**Step 1: Plan File Setup**
```bash
# Extract plan file path from arguments
PLAN_FILE="$1"  # First argument should be plan file path
echo "Processing plan file: $PLAN_FILE"
```

**Step 2: Initial Plan File Analysis**
- Read the entire plan file to understand current state
- Identify which phases/steps are already completed `[x]`
- Identify the next uncompleted step to work on `[ ]`
- Verify file is writable and accessible

**Step 3: Establish Progress Tracking**
- Create a system for tracking which step you're currently working on
- Note the exact text of checkboxes that need updating
- Plan the search/replace strings for checkbox updates

**Step 4: Begin Step-by-Step Execution**
- Follow the Step Processing Workflow below
- Update checkboxes after each completed step
- Never proceed without updating progress in plan file

## AI Instructions for Plan Processing

When processing simplification plans, the AI must:

1. **Follow the safety protocol absolutely:**
   - Never skip test validation
   - Never continue after test failures
   - Never delegate execution to subagents
   - **CRITICAL: Never skip checkbox updates - this is MANDATORY for progress tracking**

2. **Maintain detailed progress tracking:**
   - Update plan file after every significant action using search_replace tool
   - Mark steps complete immediately with `[x]` checkbox updates
   - Verify each checkbox update by reading the modified section
   - Document issues and deviations promptly
   - Never proceed to next step without updating current step checkbox

3. **Execute steps directly:**
   - Implement code changes personally
   - Write tests directly
   - Run validations without delegation

4. **Preserve functionality unconditionally:**
   - Validate preservation after every change
   - Stop immediately on any regression
   - Prioritize safety over speed

5. **Communicate clearly with user:**
   - Provide detailed status updates
   - Alert immediately on any issues
   - Ask for guidance when uncertain

6. **CRITICAL: Prevent checkbox batching behavior:**
   - Update ONE checkbox immediately after completing ONE sub-task
   - Never accumulate multiple completed tasks before updating checkboxes
   - Think: "Task done → Update checkbox → Next task" not "All tasks done → Update all checkboxes"
   - This provides real-time progress visibility to the user

Remember: The goal is safe, systematic simplification with absolute functionality preservation. Speed is secondary to safety and correctness.
