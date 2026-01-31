---
description: Post-implementation verification against a plan bundle (spec.md + tasks.md)
argument-hint: "<slug | thoughts/plans/<slug>/ | path/to/tasks.md>"
---

# Validate Implementation (Plan Bundle)

Verify that a plan bundle task list was correctly executed.

Target: $ARGUMENTS

## Process

### 1. Locate Bundle and Read Inputs

If no argument provided, search `thoughts/plans/` for the most recently modified `tasks.md`.

Resolve to `spec_path` and `tasks_path`:

- Slug: `thoughts/plans/<slug>/spec.md` and `thoughts/plans/<slug>/tasks.md`
- Directory: `<dir>/spec.md` and `<dir>/tasks.md`
- `tasks.md` path: read YAML frontmatter `spec:`

Read `spec_path` and `tasks_path` completely.

### 2. Gather Evidence

Use git to understand what changed:

```bash
git log --oneline -20
git diff --stat HEAD~10
```

Run project-specific tests/build/lint if available. Treat them as supporting evidence, not correctness.

### 3. Validate Results

- Check tasks are marked `[x]` only when completed.
- Validate outcomes against acceptance criteria and manual verification steps.
- If tests fail, reconcile vs acceptance criteria + observed behavior. Do not propose product-code changes purely to satisfy a suspect test.

### 4. Write Validation Report

Write: `thoughts/validation/YYYY-MM-DD-validation.md`

Include:

- Bundle paths (`spec_path`, `tasks_path`)
- Overall status (PASS/FAIL/PARTIAL)
- Phase-by-phase findings
- Manual verification still required
