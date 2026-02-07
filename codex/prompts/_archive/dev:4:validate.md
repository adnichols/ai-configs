---
description: Post-implementation verification against a single plan file (spec + phases + progress). Usage: <slug | thoughts/plans/<slug>.md | path/to/plan.md>
---

# Validate Implementation (Single Plan File)

Verify that a single plan file was correctly executed. This is independent verification after implementation.

Target: $ARGUMENTS

## Process

### 1. Locate Plan and Read Inputs

If no argument provided, search `thoughts/plans/` for the most recently modified `*.md` plan file.

Resolve to:

- `plan_path`

Resolution rules:

- If argument is a slug: `thoughts/plans/<slug>.md`
- If argument is a `*.md` file path: use it as-is

Legacy support (read-only; do not modify legacy files):

- If `thoughts/plans/<slug>.md` does not exist but `thoughts/plans/<slug>/spec.md` exists, treat this as a legacy bundle and validate against `spec.md` as intent and `tasks.md` as progress.

Read `plan_path` completely. Extract:

- Goal / non-goals
- Acceptance criteria
- Phases and their `### Verify` sections
- `## Progress` completion state
- `## Decisions / Deviations Log` entries

### 2. Gather Implementation Evidence

Run verification commands:

```bash
# Git history for changes
git log --oneline -20

# Scope / change shape
git diff --stat HEAD~10
```

Run project-specific validation commands when available (tests/build/lint). Treat them as supporting evidence.

### 3. Verify Outcomes

For each phase in `## Progress`:

1. Check completion status
   - Is it marked `[x]`?
2. Verify deliverables
   - If it implies code/config, does it exist and match intent?
3. Validate against acceptance criteria
   - Prefer behavioral evidence and manual verification steps when defined.
   - Use tests/build/lint as supporting evidence.
4. Assess scope
   - Did the implementation materially diverge from the plan intent?
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
author: [opencode]
git_commit: [Commit hash]
type: validation
status: [pass|fail|partial]
plan_file: [plan_path]
---

# Validation Report

## Source Plan
- Plan: `[plan_path]`

## Validation Summary

| Item | Status | Notes |
|------|--------|-------|
| Phase 1 | [pass/fail/partial] | ... |
| Phase 2 | [pass/fail/partial] | ... |

Overall Status: [PASS / FAIL / PARTIAL]

## Detailed Findings

### Phase N

Verification:
- [ ] Progress marked complete
- [ ] Acceptance criteria met (behavioral evidence)
- [ ] Phase verify steps executed / reproducible
- [ ] Automated checks (optional / supporting)

Evidence:
- [Cite file changes or logs]

## Deviations & Issues

### Unexpected Changes
- [Changes not in plan]

### Missing Items
- [Phases marked complete but missing evidence]

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
