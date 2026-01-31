---
description: Post-implementation verification against a plan bundle (spec.md + tasks.md)
argument-hint: "<slug | thoughts/plans/<slug>/ | path/to/tasks.md>"
---

# Validate Implementation (Plan Bundle)

Verify that a plan bundle task list was correctly executed. This is independent verification after implementation.

Target: $ARGUMENTS

## Process

### 1. Locate Bundle and Read Inputs

If no argument provided, search `thoughts/plans/` for the most recently modified `tasks.md`.

Resolve to:

- `spec_path` (must be `spec.md`)
- `tasks_path` (must be `tasks.md`)

Resolution rules:

- If argument is a slug: `thoughts/plans/<slug>/spec.md` and `thoughts/plans/<slug>/tasks.md`
- If argument is a directory: `<dir>/spec.md` and `<dir>/tasks.md`
- If argument is a `tasks.md` path: read YAML frontmatter and use `spec:` to locate `spec.md`

Read `tasks_path` completely. Extract:

- All tasks and subtasks (items starting with `- [ ]` or `- [x]`)
- `## Deviations Log` entries

Read `spec_path` completely. Extract:

- Goal / non-goals
- Acceptance criteria
- Verification strategy (manual checks + expected behavior)

### 2. Gather Implementation Evidence

Run verification commands:

```bash
# Git history for changes
git log --oneline -20

# Scope / change shape
git diff --stat HEAD~10
```

Run project-specific validation commands when available (tests/build/lint). Treat them as supporting evidence.

### 3. Verify Tasks

For each top-level task and phase:

1. Check completion status
   - Is it marked `[x]`?
   - Are all required subtasks `[x]`?

2. Verify deliverables
   - If it implies code/config, does it exist and match intent?

3. Validate against acceptance criteria
   - Prefer behavioral evidence and manual verification steps when defined.
   - Use tests/build/lint as supporting evidence.

4. Assess scope
   - Did the implementation materially diverge from the bundle intent?
   - Are there unrequested changes that should be documented?

#### Tests Policy (Validation Perspective)

- Do not treat "tests passing" as the definition of working code.
- If tests fail, reconcile the failure against acceptance criteria + observed behavior:
  - If code is correct and the test is wrong/outdated, recommend fixing the test.
  - If the test reveals a real bug, recommend fixing product code.
  - Do not recommend changing product code merely to make tests pass.

### 4. Generate Validation Report

Create document at: `thoughts/validation/YYYY-MM-DD-validation.md`

```markdown
---
date: [ISO timestamp]
author: [claude]
git_commit: [Commit hash]
type: validation
status: [pass|fail|partial]
bundle: [thoughts/plans/<slug>/]
spec_file: [spec_path]
task_file: [tasks_path]
---

# Validation Report

## Source Bundle
- Spec: `[spec_path]`
- Tasks: `[tasks_path]`

## Validation Summary

| Item | Status | Notes |
|------|--------|-------|
| Phase 1 | [pass/fail/partial] | ... |
| Phase 2 | [pass/fail/partial] | ... |

**Overall Status**: [PASS / FAIL / PARTIAL]

## Detailed Findings

### Phase N

**Verification:**
- [ ] Tasks marked complete
- [ ] Acceptance criteria met (behavioral evidence)
- [ ] Automated checks (optional / supporting)

**Evidence:**
- [Cite file changes or logs]

## Deviations & Issues

### Unexpected Changes
- [Changes not in tasks/spec]

### Missing Items
- [Tasks marked complete but missing evidence]

## Manual Verification Required
- [ ] [Item 1]

## Recommendations
[Next steps]
```

### 5. User Engagement

When validation reveals issues that require user input, use `question` before finalizing the report.

Always engage the user when:

- Validation status is FAIL or PARTIAL
- Evidence is ambiguous or missing
- There are multiple viable interpretations of acceptance criteria
- Scope drift is detected and needs classification
