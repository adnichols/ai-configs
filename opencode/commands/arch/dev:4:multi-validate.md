---
description: Post-implementation verification using multi-agent review (plan file)
argument-hint: '<slug | thoughts/plans/<slug>.md | path/to/plan.md>'
---

# Multi-Agent Validation (Single Plan File)

Verify that a plan file was correctly executed using parallel review from multiple reviewers.

Target: $ARGUMENTS

## Process

### 1) Locate and Read Plan

Resolve `plan_path`:

- If argument is a slug: `thoughts/plans/<slug>.md`
- If argument is a `*.md` file path: use it

If no argument provided, pick the most recently modified `thoughts/plans/*.md`.

Read `plan_path` completely. Extract:

- Goal / non-goals
- Acceptance criteria
- Phases and their `### Verify` sections
- `## Progress` completion state
- `## Decisions / Deviations Log`

### 2) Gather Implementation Evidence

Run verification commands and capture output:

```bash
# Git metadata
git rev-parse HEAD
git log --oneline -20

# Git changes for scope verification
git diff --stat HEAD~10
```

Also run project-specific tests/build/lint when available; treat as supporting evidence.

### 3) Launch Parallel Reviewers

Launch reviewers in parallel using multiple Task calls.

Each reviewer prompt MUST include:

- Plan file path (`plan_path`)
- Git commit hash
- Evidence block

Reviewer instructions:

- Read the plan.
- Validate the implementation against acceptance criteria and phase verify steps.
- Flag:
  - INCORRECT
  - SCOPE DRIFT
  - GAP
  - RISK
  - WRONG REFERENCE
  - CRITICAL

Comments format:

```markdown
[REVIEW:<Reviewer>] <CATEGORY> - <Phase or section>: <finding> [/REVIEW]
```

### 4) Synthesize Findings

After reviewers return:

- Identify consensus issues (2+ reviewers agree)
- Identify single-reviewer concerns
- Determine overall status: PASS / FAIL / PARTIAL

### 5) Write Validation Report

Create: `thoughts/validation/YYYY-MM-DD-validation.md` with:

- `plan_file: [plan_path]`
- Overall status
- Phase-by-phase findings
- Manual verification still required
- Recommendations / next steps
