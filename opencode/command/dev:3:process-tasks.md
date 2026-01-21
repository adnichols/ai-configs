---
description: Process tasks in a task list with fidelity-preserving agent selection
argument-hint: "[Files]"
---

# Instructions

Process the task list using the fidelity-preserving approach to maintain exact scope as specified in the source document. This command uses developer and quality-reviewer agents to implement only what's explicitly specified, without additions or scope expansions.
$ARGUMENTS. Think harder.

## CRITICAL: Orchestrator-Only Mode

**You (the parent session) are an ORCHESTRATOR, not an implementer.**

- **NEVER** use Edit, Write, or MultiEdit tools to modify code files
- **NEVER** implement features, fix bugs, or write code directly
- **ALWAYS** delegate ALL code changes to sub-agents via the Task tool

Your job is to coordinate, track progress, run validations, and manage git—NOT to write code.

## Autopilot Rules

- Execute the task list continuously; do not pause between subtasks.
- Stop only when a decision between viable options requires user input due to insufficient evidence.
- If unsure, investigate, retry, and delegate until evidence supports a decision; do not ask the user just for uncertainty.
- Use `question` for required decisions; otherwise proceed automatically.
- Run quality review after each phase (parent task), not after each subtask.

## Fidelity Preservation Process

Before starting task implementation:

1. **Parse Task File Metadata:** Extract fidelity information from task file YAML front-matter
2. **Check for Phase 0 (Infrastructure Verification):** If the task file contains a Phase 0:
   - **Phase 0 is BLOCKING** - no other phases can start until Phase 0 passes
   - Complete all Phase 0 subtasks (version checks, smoke tests, documentation)
   - Only proceed to Phase 1+ after Phase 0 is fully validated and committed
3. **Use Fidelity Agents:** Always use fidelity-preserving agents for implementation:
   - Developer agent: `@developer`
   - Quality reviewer: `@quality-reviewer`
4. **Apply Only Specified Validation:** Include only the testing and validation explicitly specified in the source document:
   - Review source document for testing requirements
   - Implement only specified security measures
   - Do not add tests or validation beyond what's explicitly required

## Sub-Agent Delegation Protocol

When processing tasks, use the Task tool to spawn specialized sub-agents for implementation work. This preserves orchestrator context and ensures fidelity-focused execution.

### For Implementation Tasks

Delegate actual code implementation to the **developer** agent using the Task tool:

**Task prompt template:**
```
Implement subtask [X.Y]: [subtask description]

Specification requirements:
- [Requirement 1 from source spec]
- [Requirement 2 from source spec]

Files: [relevant file paths]
Context: [relationship to other components]

IMPORTANT: Implement ONLY what's specified above. No additional features, tests, or security beyond requirements.
```

### For Quality Reviews

When all subtasks under a parent are complete, spawn a **quality-reviewer** agent via Task tool:

**Task prompt template:**
```
Review Phase [N] implementation for specification fidelity.

Source specification: [path to spec/task file]
Modified files:
- [file1.ts]
- [file2.ts]

Verify: Implementation matches spec exactly, no scope creep, no unauthorized additions.
```

**Quality Review Outcomes:**
- If issues are found, spawn a **developer** agent to fix them and re-run the quality review; repeat until clean.
- Stop and use `question` only when the reviewer identifies multiple viable interpretations or a decision is required.

### Orchestrator Responsibilities (Do NOT Delegate)

The parent agent (you) handles coordination tasks directly:
- Git branch creation and management
- Task list updates (`[ ]` → `[x]`) in markdown files
- User input prompts when required
- Phase transitions and commits
- Validation command execution (lint, build, tests)
- Reading files for context gathering
- Running Bash commands for git, npm, validation

### What You MUST Delegate (NEVER Do Directly)

**All code changes go to sub-agents.** This includes:
- Creating new files (use developer agent)
- Editing existing code (use developer agent)
- Writing tests (use developer agent)
- Refactoring (use developer agent)
- Code review (use quality-reviewer agent)

If you find yourself about to use Edit/Write/MultiEdit on a code file, STOP and spawn a sub-agent instead.



# Task List Management

Guidelines for managing task lists in markdown files to track progress on completing source document implementations

## Task Implementation

## Critical Task Update Protocol

After a sub-agent completes ANY subtask:

1. Declare completion.
2. Update the markdown task list (`[ ]` → `[x]`) and show the edit.
3. Verify the updated section and continue immediately.

If the update was delayed, self-correct immediately, verify, and proceed without pausing.
- Check current branch: `git branch --show-current`
- If on `main`, create a new branch for this phase of work
- If already on a non-main branch, **DO NOT create a new branch** - proceed with current branch
- Parent agent (you) are responsible for git branch creation, not subagents
- **One sub-task at a time:** Spawn a **developer** sub-agent via Task tool for each subtask. Proceed immediately to the next subtask; pause only for user decisions per Autopilot Rules.
- **Completion protocol:**

  1. When a **sub-agent completes** a subtask, immediately update the markdown file `[ ]` → `[x]` and confirm the update was successful.

  2. If **all** subtasks underneath a parent task are now `[x]`, follow this sequence:

  - **First**: Run standard validation checks (lint, build, secrets scan, unit tests). If any fail, delegate fixes and re-run until they pass.
  - **Stage changes** (`git add .`) once validations pass.
  - **Quality Review**: Spawn a **quality-reviewer** sub-agent via Task tool with the source specification and list of modified files for fidelity validation. If issues are found, delegate fixes and re-run the review until clean; stop only for a required user decision.
  - **Clean up**: Remove any temporary files and temporary code before committing
  - **Commit**: Use a descriptive commit message that:

    - Uses conventional commit format (`feat:`, `fix:`, `refactor:`, etc.)
    - Summarizes what was accomplished in the parent task
    - Lists key changes and additions
    - References the phase number and source context
    - **Formats the message as a single-line command using `-m` flags**, e.g.:

      ```
      git commit -m "feat: add payment validation logic" -m "- Validates card type and expiry" -m "- Adds unit tests for edge cases" -m "Related to Phase 2.1"
      ```

  3. Once all the subtasks are marked completed and changes have been committed, mark the **parent task** as completed.

- After parent tasks complete, run validations, quality review, and commit changes, then continue.

## Task List Maintenance

1. **Update the task list as you work:**

   - Mark tasks and subtasks as completed (`[x]`) per the protocol above.
   - Add new tasks as they emerge.

2. **Maintain the "Relevant Files" section:**

   - List every file created or modified during implementation.
   - Update descriptions as implementation progresses.
   - Add new files discovered during implementation.

3. **Context Validation (for rich execution plans):**
   - Ensure implementation stays true to source document's technical specifications.
   - Validate security requirements are being followed.
   - Confirm performance benchmarks are being met.

## Handling Discoveries During Implementation

If a discovery creates multiple viable options or requires scope interpretation, stop and use `question` to ask the user. Otherwise, resolve autonomously, document any deviation, and continue.

Use `question` when you need a decision between viable paths due to insufficient evidence. When no decision is required, keep investigating, retrying, and delegating until evidence supports a clear choice.

### Question Templates

**Validation Question:**
```
Question: "I discovered [X] during implementation. This affects [phases/tasks]. Is my assessment correct?"
Header: "Impact"
Options:
- Yes, your assessment is correct
- Impact is larger than you think
- Impact is smaller - proceed as planned
- Need more information before deciding
```

**Trade-off Question:**
```
Question: "I found an issue with the planned approach. Which direction should we take?"
Header: "Approach"
Options:
- Option A: [description with trade-offs]
- Option B: [description with trade-offs]
- Pause implementation while I investigate further
```

**Scope Question:**
```
Question: "This discovery means [feature] would require [significantly more work/different approach]. How should we adjust?"
Header: "Scope"
Options:
- Expand scope to handle this properly
- Defer this aspect to a follow-up task
- Simplify the approach (describe what changes)
- Let's discuss before deciding
```

## Deviations Log Protocol

**MANDATORY:** When a discovery leads to a decision that differs from the original spec/plan, you MUST log it in the task file for downstream propagation to future phases.

### When to Log

Log a deviation when:
- The spec was ambiguous and you chose a specific implementation path
- A planned approach was changed due to discovered constraints
- Scope was adjusted (feature deferred, modified, or dropped)
- An API contract or pattern was established that future phases depend on
- A technical constraint was discovered that affects future work

### How to Log

After user approval for a deviation, append to the task file's `## Deviations Log` section (create if it doesn't exist):

```markdown
## Deviations Log

### D[N]: [Brief Decision Title] - [YYYY-MM-DD]
- **Category:** [Uncertainty Resolved | Scope Adjusted | Pattern Discovered | Constraint Identified | API Contract Defined]
- **Discovery:** [What was found that differed from spec/plan]
- **Spec/Plan Said:** [Quote or summary of original requirement]
- **Decision Made:** [What was actually implemented]
- **Rationale:** [Why this choice was made]
- **User Approved:** [Yes | No - autonomous decision]
- **Future Phases Affected:** [Phase 2, Phase 3, etc. | None | Unknown]
```

### Example Entry

```markdown
### D1: Use Partial Unique Index Instead of Trigger - 2025-12-27
- **Category:** Uncertainty Resolved
- **Discovery:** PostgreSQL partial unique indexes are more performant than triggers for conditional uniqueness
- **Spec/Plan Said:** "Ensure unique workspace slugs per user" (implementation unspecified)
- **Decision Made:** Used `CREATE UNIQUE INDEX ... WHERE deleted_at IS NULL` instead of trigger-based approach
- **Rationale:** Partial indexes are database-native, faster, and require less maintenance
- **User Approved:** Yes
- **Future Phases Affected:** Phase 3 (migration must preserve index), Phase 5 (cleanup can remove old trigger code)
```

### Logging Autonomous Decisions

For high-confidence decisions made without user input (e.g., obvious technical choices), still log them but mark as:
```
- **User Approved:** No - autonomous decision (high confidence)
```

This ensures `dev:5:phase-review` can still propagate these decisions to future phases.

## AI Instructions

As the orchestrator, you must:

1. **Delegate all code work** - Spawn sub-agents for every subtask that involves code changes
2. **Track progress** - Update task list markdown after each sub-agent completes
3. **Follow completion protocol:**
   - Mark each finished **sub‑task** `[x]` after sub-agent reports completion
   - Mark the **parent task** `[x]` once **all** its subtasks are `[x]`
4. **Manage git** - Handle branching, staging, and commits directly
5. **Run validations** - Execute lint, build, and test commands directly via Bash
6. **Coordinate quality reviews** - Spawn quality-reviewer after phases complete
7. **Maintain context** - Keep "Relevant Files" section accurate based on sub-agent reports
8. **Gate progress** - Pause only when user input is required; always use `question` for decisions, clarifications, or trade-offs
9. **CRITICAL CHECKPOINT:** After each subtask, immediately declare completion, update markdown, confirm the update, and continue unless user input is required

**Remember: You orchestrate, sub-agents implement. Never write code directly.**

---

## ➡️ Next Command

When all tasks are complete, run:
```
/dev:4:validate [path-to-tasks]
```
