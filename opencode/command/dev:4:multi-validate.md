---
description: Post-implementation verification using multi-agent review (GLM, Kimi, Llama Maverick)
argument-hint: "<slug | thoughts/plans/<slug>/ | path/to/tasks.md>"
---

# Multi-Agent Validation

Verify that a task list was correctly executed using parallel review from GLM 4.7, Kimi K2, and Llama Maverick.

Target: $ARGUMENTS

## Process

### 1. Locate and Read Documents

If no argument provided, search `thoughts/plans/` for the most recently modified `tasks.md`.

Read the task file completely. Extract:
- All tasks and subtasks (items starting with `- [ ]` or `- [x]`)
- Any context or requirements blocks
- "Implementation Files" or "Relevant Files" if listed
- **Source Specification** path from YAML frontmatter `spec:` (preferred), or from the document body as a fallback

Read the source specification completely to understand:
- Requirements and constraints
- Technical approach
- Explicit scope boundaries
- Success criteria

### 2. Gather Implementation Evidence

Run verification commands and capture all output:

```bash
# Git metadata
git rev-parse HEAD
git log --oneline -20

# Git changes for scope verification
git diff --stat HEAD~10

# Test results (project-specific)
# (Run the repository's primary test command(s) when available; treat as supporting evidence)

# E2E tests if available
# pnpm test:e2e  # (requires PLAYWRIGHT=True pnpm dev)

# Build status
# (Run the repository's build command when available; treat as supporting evidence)

# Lint status
# (Run the repository's lint command when available; treat as supporting evidence)
```

**Capture all output in a shared evidence block** to distribute to all reviewers.

### 3. Launch Parallel Reviewers

Launch ALL THREE reviewers in parallel using a single message with multiple Task tool calls.

**GLM 4.7 Reviewer:**
```
Task(
  subagent_type="reviewer-glm",
  description="Validate with GLM 4.7 - Architecture focus",
  prompt=f"""You are [GLM Reviewer] performing FINAL VALIDATION of an implementation.

**Task List:** {task_path}
**Source Specification:** {spec_path}
**Git Commit Hash:** {git_commit}

**Implementation Evidence:**
{evidence_block}

**Validation Process:**

1. **Read Source Documents**
   - Read the task list completely. Identify which tasks are marked complete (`[x]`)
   - Read the source specification to understand requirements, constraints, and scope

2. **Analyze Implementation Evidence**
   - Review git history to understand what was actually implemented
   - Examine test results and build status
   - Identify files that were modified/created/removed

3. **Validate Each Completed Task**
   For each task marked complete in the task list:

   a. **INCORRECT**: Implementation doesn't match spec requirements
      - Wrong technical approach
      - Wrong file paths, API shapes, or data structures
      - Inverted logic or reversed conditions
      - Wrong implementation details

   b. **SCOPE DRIFT**: Implementation beyond spec/task boundaries
      - Features added that are NOT in the specification
      - Features added that are NOT in the task list
      - Unrequested changes

   c. **MISINTERPRETATION**: Task misunderstood spec intent
      - Task description was misinterpreted
      - Requirement implemented incorrectly

   d. **CONTRADICTION**: Implementation conflicts with spec
      - Conflicts with another part of the specification
      - Contradictory technical decisions

   e. **WRONG REFERENCE**: File/API/component reference error
      - Wrong file paths in implementation
      - Wrong API endpoint or component name

   4. **Add Validation Findings as Review Tags**
   Place comments immediately after the task/subtask:
   
   [REVIEW:GLM Reviewer] INCORRECT - Task 2.3: Spec requires authentication headers (Bearer token) but implementation uses cookies. [/REVIEW]
   [REVIEW:GLM Reviewer] SCOPE DRIFT - Phase 3 added admin panel that is not in specification or task list. [/REVIEW]
   [REVIEW:GLM Reviewer] MISINTERPRETATION - Task 1.5 spec says "soft delete" but implementation does hard delete. [/REVIEW]
   [REVIEW:GLM Reviewer] CONTRADICTION - Task 4.2 implementation conflicts with specification section 5.3 which states "read-only access". [/REVIEW]
   [REVIEW:GLM Reviewer] WRONG REFERENCE - Task 2.1 references src/api/users.ts but actual path is src/services/user.service.ts. [/REVIEW]
   
   For passing validation (optional, provides confidence):
   [REVIEW:GLM Reviewer] PASS - Task 1.0: Implementation correctly matches specification requirements. [/REVIEW]

5. **Focus Your Evaluation on:**
   - Deep architectural analysis
   - System design concerns
   - Long-term technical implications
   - Scalability considerations
   - Technology choice implications

6. **Critical Flagging:**
   Mark any issue that would cause production failures, security breaches, data loss, or break core functionality as "CRITICAL":
   
   [REVIEW:GLM Reviewer] CRITICAL - Task 3.1: No authentication on API endpoint. Any user can delete data. [/REVIEW]

7. **Return Validation Summary**
   When complete, return:
   - Overall status: PASS / FAIL / PARTIAL
   - Number of issues found (by category)
   - Most critical findings (3-5 items)
   - Any immediate concerns requiring user attention
"""
)
```

**Kimi K2 Reviewer:**
```
Task(
  subagent_type="reviewer-kimi",
  description="Validate with Kimi K2 - Integration focus",
  prompt=f"""You are [Kimi Reviewer] performing FINAL VALIDATION of an implementation.

**Task List:** {task_path}
**Source Specification:** {spec_path}
**Git Commit Hash:** {git_commit}

**Implementation Evidence:**
{evidence_block}

**Validation Process:**

1. **Read Source Documents**
   - Read the task list completely. Identify which tasks are marked complete (`[x]`)
   - Read the source specification to understand requirements, constraints, and scope

2. **Analyze Implementation Evidence**
   - Review git history to understand what was actually implemented
   - Examine test results and build status
   - Identify files that were modified/created/removed

3. **Validate Each Completed Task**
   For each task marked complete in the task list:

   a. **INCORRECT**: Implementation doesn't match spec requirements
   b. **SCOPE DRIFT**: Implementation beyond spec/task boundaries
   c. **MISINTERPRETATION**: Task misunderstood spec intent
   d. **CONTRADICTION**: Implementation conflicts with spec
   e. **WRONG REFERENCE**: File/API/component reference error

   4. **Add Validation Findings as Review Tags**
   Format: [REVIEW:Kimi Reviewer] [CATEGORY] - Task X.Y: Your finding. [/REVIEW]

5. **Focus Your Evaluation on:**
   - Integration feasibility
   - Implementation details
   - Component interactions
   - API design considerations
   - Interface contracts
   - Dependencies and constraints

6. **Critical Flagging:**
   Mark production/security data loss issues as "CRITICAL".

7. **Return Validation Summary**
   - Overall status: PASS / FAIL / PARTIAL
   - Number of issues found (by category)
   - Most critical findings (3-5 items)
   - Any immediate concerns requiring user attention
"""
)
```

**Llama Maverick Reviewer:**
```
Task(
  subagent_type="reviewer-llamamav",
  description="Validate with Llama Maverick - Requirements focus",
  prompt=f"""You are [Llama Maverick Reviewer] performing FINAL VALIDATION of an implementation.

**Task List:** {task_path}
**Source Specification:** {spec_path}
**Git Commit Hash:** {git_commit}

**Implementation Evidence:**
{evidence_block}

**Validation Process:**

1. **Read Source Documents**
   - Read the task list completely. Identify which tasks are marked complete (`[x]`)
   - Read the source specification to understand requirements, constraints, and scope

2. **Analyze Implementation Evidence**
   - Review git history to understand what was actually implemented
   - Examine test results and build status
   - Identify files that were modified/created/removed

3. **Validate Each Completed Task**
   For each task marked complete in the task list:

   a. **INCORRECT**: Implementation doesn't match spec requirements
   b. **SCOPE DRIFT**: Implementation beyond spec/task boundaries
   c. **MISINTERPRETATION**: Task misunderstood spec intent
   d. **CONTRADICTION**: Implementation conflicts with spec
   e. **WRONG REFERENCE**: File/API/component reference error

   4. **Add Validation Findings as Review Tags**
   Format: [REVIEW:Llama Maverick Reviewer] [CATEGORY] - Task X.Y: Your finding. [/REVIEW]

5. **Focus Your Evaluation on:**
   - Requirements completeness
   - Edge cases and failure modes
   - User experience considerations
   - Error handling and recovery
   - Performance implications
   - Security and privacy
   - Testing and validation approaches

6. **Critical Flagging:**
   Mark production/security data loss issues as "CRITICAL".

7. **Return Validation Summary**
   - Overall status: PASS / FAIL / PARTIAL
   - Number of issues found (by category)
   - Most critical findings (3-5 items)
   - Any immediate concerns requiring user attention
"""
)
```

### 4. Wait for Completion

Wait for all three Task agents to complete. They will return their validation summaries when finished.

**Error Handling:**
- If 1 reviewer fails: Continue with remaining 2, note in report
- If 2+ reviewers fail: Inform user, show partial results, suggest retry
- If evidence gathering failed: Halt and report error

### 5. Extract and Analyze Findings

Read the task list file and extract all validation comments:

```python
task_content = read_file(task_path)

# Count comments per reviewer
glm_count = task_content.count("[REVIEW:GLM Reviewer]")
kimi_count = task_content.count("[REVIEW:Kimi Reviewer]")
llamamav_count = task_content.count("[REVIEW:Llama Maverick Reviewer]")

# Count by category
categories = ["INCORRECT", "SCOPE DRIFT", "MISINTERPRETATION", "CONTRADICTION", "WRONG REFERENCE", "PASS", "CRITICAL"]
glm_by_category = {cat: task_content.count(f"[REVIEW:GLM Reviewer] {cat}") for cat in categories}
kimi_by_category = {cat: task_content.count(f"[REVIEW:Kimi Reviewer] {cat}") for cat in categories}
llamamav_by_category = {cat: task_content.count(f"[REVIEW:Llama Maverick Reviewer] {cat}") for cat in categories}

# Extract comment locations for overlap detection
glm_comments = find_all_with_context("[REVIEW:GLM Reviewer]", task_content)
kimi_comments = find_all_with_context("[REVIEW:Kimi Reviewer]", task_content)
llamamav_comments = find_all_with_context("[REVIEW:Llama Maverick Reviewer]", task_content)
```

### 6. Identify Consensus Issues

Analyze comment locations to identify overlapping concerns from multiple reviewers:

```python
overlap_threshold = 200  # characters

consensus_issues = []
for i, (glm_start, glm_context) in enumerate(glm_comments):
  for k, (kimi_start, kimi_context) in enumerate(kimi_comments):
    if abs(glm_start - kimi_start) < overlap_threshold:
      consensus_issues.append({
        "reviewers": ["GLM Reviewer", "Kimi Reviewer"],
        "location": glm_start,
        "contexts": (glm_context, kimi_context)
      })

# Also check GLM<->Llama Maverick and Kimi<->Llama Maverick overlaps
```

### 7. Determine Overall Status

Calculate overall validation status:

- **FAIL**: 2+ reviewers agree on critical issues OR consensus failures >= 2
- **PARTIAL**: Any critical issues from single reviewer OR many single-reviewer concerns (>10)
- **PASS**: No critical issues, minimal single-reviewer concerns, consensus on successful completion

### 8. Generate Validation Report

Create document at: `thoughts/validation/YYYY-MM-DD-validation.md`

```markdown
---
date: [ISO timestamp]
author: [claude]
git_commit: [Commit hash]
type: validation
status: [pass|fail|partial]
task_file: [Path to validated task file]
spec_file: [Path to source specification]
---

# Validation Report

## Source Documents
- **Task List:** `[task_path]`
- **Specification:** `[spec_path]`
- **Git Commit:** `[commit_hash]`

## Multi-Agent Validation Results

| Reviewer | Status | Issues Found | Critical Issues | Primary Focus |
|----------|--------|--------------|-----------------|---------------|
| GLM 4.7  | {PASS/FAIL} | {N} | {N} | Architecture, Design, Scalability |
| Kimi K2  | {PASS/FAIL} | {N} | {N} | Integration, API, Component Contracts |
| Llama Maverick | {PASS/FAIL} | {N} | {N} | Requirements, Edge Cases, UX, Error Handling |

**Total Comments:** {N}

### Consensus Issues (2+ reviewers agree)
{List issues where multiple reviewers flagged the same task/area}

### Single-Reviewer Raises (requiring investigation)
{List concerns raised by only one reviewer}

### Issue Categories
- INCORRECT: {glm_count + kimi_count + minimax_count}
- SCOPE DRIFT: {total}
- MISINTERPRETATION: {total}
- CONTRADICTION: {total}
- WRONG REFERENCE: {total}
- PASS: {total}
- CRITICAL: {total}

## Validation Summary

| Task | Status | Reviewers | Notes |
|------|--------|-----------|-------|
| [Task Name] | [pass/fail] | [GLM,Kimi] | [Brief note from reviewers] |
| [Task Name] | [pass/fail] | [Llama Maverick] | [Brief note from reviewers] |

**Overall Status**: [PASS / FAIL / PARTIAL]

## Detailed Findings

### [Task Name]

**Status:** [Completed/Incomplete]

**Validation Summary:**
- [GLM]: {PASS/FAIL} - {Summary of findings}
- [Kimi]: {PASS/FAIL} - {Summary of findings}
- [Llama Maverick]: {PASS/FAIL} - {Summary of findings}

**Consensus:** {All reviewers agreed / Mixed / No consensus}

**Verification:**
- [ ] Task marked complete
- [ ] Requirements met
- [ ] Tests pass
- [ ] Code review passed

**Evidence:**
[Cite file changes or logs from git history]

**Reviewer Findings:**
[Extract review tags from task list for this task]

### [Task Name]
...

## Deviations & Issues

### Unexpected Changes (SCOPE DRIFT)
{From SCOPE DRIFT comments}

### Missing Items (INCOMPLETE)
{From INCORRECT comments}

### Conflicts (CONTRADICTION)
{From CONTRADICTION comments}

### Technical Issues (INCORRECT/WRONG REFERENCE)
{From INCORRECT and WRONG REFERENCE comments}

### Critical Issues Requiring Immediate Attention
{From CRITICAL comments}

## Manual Verification Required
- [ ] [Item 1]
- [ ] [Item 2]

## Recommendations
[Enhanced with consensus perspective and next steps]
```

### 9. User Engagement for Concerning Patterns

When validation reveals issues that require user input, use **AskUserQuestion** before finalizing the report.

**Failure Resolution Question (when validation fails):**
```
Question: "Validation found [N] issues with [N] critical. How should we proceed?"
Header: "Issues"
Options:
- Fix issues before finalizing (return to implementation)
- Mark as known issues and proceed
- Let me explain the issues in detail first
```

**Reviewers Disagree Question (NEW):**
```
Question: "Reviewers disagree on [feature/issue]:
- GLM Reviewer: [concern and rationale]
- Kimi Reviewer: [view and rationale]
- Llama Maverick Reviewer: [view if present]

How should we resolve this?"
Header: "Reviewers Disagree"
Options:
- Implement GLM's recommendation (architecture focus)
- Implement Kimi's recommendation (integration focus)
- Keep current implementation (defer to implementer)
- Get additional manual review
- Let me explain the trade-offs in detail
```

**Ambiguous Results Question:**
```
Question: "I found [behavior] but I'm uncertain if it meets the requirement. Can you clarify?"
Header: "Clarify"
Options:
- Yes, this meets the requirement
- No, this needs to be fixed
- Show me more details
```

**Scope Deviation Question:**
```
Question: "The implementation includes [unexpected change]. Should this be documented as intentional?"
Header: "Deviation"
Options:
- Yes, it's an intentional improvement
- No, it should be reverted
- Mark for follow-up review
```

**Missing Evidence Question:**
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
- Any CRITICAL issues found
- Reviewers disagree on significant findings
- Major deviations from spec found
- Evidence is ambiguous or missing

**Present Report Without Blocking:**
- All validations pass cleanly
- Minor deviations documented
- Clear evidence exists for all completed tasks
- Reviewer consensus on successful validation

### 10. Present Report

Present findings to user:
- Overall pass/fail/partial status
- Multi-agent validation summary table
- Consensus issues vs. single-reviewer concerns
- Key deviations found
- Reviewer conflicts requiring attention
- Manual tests needed
- Any engagement questions from step 9

---

## Next Steps

Based on validation status:

**PASS:**
- Proceed to commit changes
- Create pull request
- Proceed with deployment

**PARTIAL:**
- Review single-reviewer concerns
- Address CRITICAL issues if any
- Manual verification required

**FAIL:**
- Address consensus issues
- Fix implementation or adjust specification
- Re-run validation after fixes
