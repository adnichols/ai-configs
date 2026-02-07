---
description: Process tasks in a task list with fidelity-preserving approach. Usage: [Files]
---

# Instructions

Process the task list using the fidelity-preserving approach to maintain exact scope as specified in the source document. Implement only what's explicitly specified, without additions or scope expansions.

$ARGUMENTS

## CRITICAL: Orchestrator-Only Mode

**You (the parent session) are an ORCHESTRATOR, not an implementer.**

- **NEVER** implement features, fix bugs, or write code in bulk without verification
- **ALWAYS** work incrementally, one subtask at a time
- Your job is to coordinate, track progress, run validations, and manage git

## Fidelity Preservation Process

Before starting task implementation:

1. **Parse Task File Metadata:** Extract fidelity information from task file YAML front-matter
2. **Check for Phase 0 (Infrastructure Verification):** If the task file contains a Phase 0:
   - **Phase 0 is BLOCKING** - no other phases can start until Phase 0 passes
   - Complete all Phase 0 subtasks (version checks, smoke tests, documentation)
   - Only proceed to Phase 1+ after Phase 0 is fully validated and committed
3. **Apply Only Specified Validation:** Include only the testing and validation explicitly specified in the source document

## Task Implementation Protocol

When processing tasks:

1. **Work one subtask at a time**
2. **After completing each subtask:**
   - Mark it as completed by changing `[ ]` to `[x]`
   - Confirm the update was successful
   - Request permission to proceed (unless NOSUBCONF specified)

<skip_subtask_confirmation>
If $ARGUMENTS contains NOSUBCONF then ignore subtask confirmation in task implementation below
</skip_subtask_confirmation>

## Critical Task Update Protocol

**MANDATORY CHECKPOINT SYSTEM:** After completing ANY subtask, follow this exact sequence:

1. **Declare completion:**
   "✅ Subtask [X.Y] [task name] completed.
   🔄 UPDATING MARKDOWN FILE NOW..."

2. **Immediately perform the markdown update:**
   - Change `- [ ] X.Y [task name]` to `- [x] X.Y [task name]`

3. **Confirm update completion:**
   "✅ Markdown file updated: [ ] → [x] for subtask X.Y
   📋 Task list is now current."

4. **Request permission to proceed (unless NOSUBCONF specified):**
   "Ready to proceed to next subtask. May I continue? (y/n)"

## Task Processing Rules

- Do not proceed with tasks unless you are on a git branch other than main
- If needed, create a branch for the phase of work you are implementing
- **One sub-task at a time:** Complete each subtask before starting the next
- **Completion protocol:**

  1. When a subtask is complete, immediately mark it as completed by changing `[ ]` to `[x]`

  2. If **all** subtasks underneath a parent task are now `[x]`, follow this sequence:

  - **First**: Run standard validation checks (lint, build, tests)
  - **Only if all validations pass**: Stage changes (`git add .`)
  - **Review**: Verify implementation matches specification
  - **Clean up**: Remove any temporary files before committing
  - **Commit**: Use a descriptive commit message with conventional commit format

  3. Once all subtasks are marked completed and changes committed, mark the **parent task** as completed

- Stop after each sub-task and wait for the user's go-ahead UNLESS NOSUBCONF is specified
- Always stop after parent tasks complete, run test suite, and commit changes

## Task List Maintenance

1. **Update the task list as you work:**

   - Mark tasks and subtasks as completed (`[x]`) per the protocol above
   - Add new tasks as they emerge

2. **Maintain the "Relevant Files" section:**

   - List every file created or modified during implementation
   - Update descriptions as implementation progresses

3. **Context Validation (for rich execution plans):**
   - Ensure implementation stays true to source document's technical specifications.
   - Validate security requirements are being followed.
   - Confirm performance benchmarks are being met.

## Handling Discoveries During Implementation

**When you discover something that invalidates or significantly changes the plan:**

1. **Stop** - Do not continue implementing based on outdated assumptions
2. **Report** - Explain what you discovered and how you found it
3. **Assess Impact** - Identify which phases/tasks are affected
4. **Ask** - Present options and ask how to proceed before continuing

Examples of discoveries requiring this protocol:
- A dependency doesn't work as documented
- An existing implementation already covers part of the plan
- A technical constraint makes a phase impossible or unnecessary
- New information suggests a different approach would be better
- The plan conflicts with existing code patterns
- **Phase 0 infrastructure verification fails** (version mismatch, connectivity issues)
- **Paired dependencies are incompatible** (client/server version conflict)

**Do not** silently adjust the plan or continue with an approach you know is suboptimal.

### Proactive User Engagement for Discoveries

Use **AskUserQuestion** to engage the user when discoveries warrant input.

**Validation Question (confirm impact assessment):**
```
Question: "I discovered [X] during implementation. This affects [phases/tasks]. Is my assessment correct?"
Header: "Impact"
Options:
- Yes, your assessment is correct
- Impact is larger than you think
- Impact is smaller - proceed as planned
- Need more information before deciding
```

**Trade-off Question (present alternatives):**
```
Question: "I found an issue with the planned approach. Which direction should we take?"
Header: "Approach"
Options:
- Option A: [description with trade-offs]
- Option B: [description with trade-offs]
- Pause implementation while I investigate further
```

**Scope Question (adjust plan boundaries):**
```
Question: "This discovery means [feature] would require [significantly more work/different approach]. How should we adjust?"
Header: "Scope"
Options:
- Expand scope to handle this properly
- Defer this aspect to a follow-up task
- Simplify the approach (describe what changes)
- Let's discuss before deciding
```

### When to Surface vs Proceed Autonomously

**Always Surface (user engagement required):**
- Plan assumptions are invalidated (blocker discovered)
- Multiple viable paths with different trade-offs
- Scope would change (expand or contract)
- Risk level increases beyond original assessment
- Decisions affect future phases
- Implementation would diverge from spec intent

**Proceed Autonomously (log in Deviations, don't block):**
- Minor technical choices within spec boundaries
- Implementation details that don't affect behavior
- Choosing between equivalent approaches
- Obvious error corrections in the plan
- Well-established patterns in the codebase

**Threshold Guidance:** When in doubt, err toward engaging the user. The cost of a brief pause is lower than implementing the wrong thing.

### User Engagement During Implementation Work

If implementation work reports an issue:

1. **Issue surfaced** - Describe what was found
2. **Evaluate impact** - Is this a blocker or solvable within scope?
3. **If blocker or scope question**: Use AskUserQuestion before proceeding
4. **If solvable within spec**: Proceed and log decision if it deviates from plan

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

## Orchestrator Responsibilities

As the orchestrator, you must:

1. **Track progress** - Update task list markdown after each completion
2. **Follow completion protocol:**
   - Mark each finished **sub-task** `[x]`
   - Mark the **parent task** `[x]` once **all** its subtasks are `[x]`
3. **Manage git** - Handle branching, staging, and commits
4. **Run validations** - Execute lint, build, and test commands
5. **Maintain context** - Keep "Relevant Files" section accurate
6. **Gate progress** - Pause for user approval unless NOSUBCONF is specified

---

## ➡️ Next Command

When all tasks are complete, run:
```
/dev:4:validate [path-to-tasks]
```
