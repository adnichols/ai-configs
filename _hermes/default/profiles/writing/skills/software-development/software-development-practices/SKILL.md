---
name: software-development-practices
description: "Proven software engineering practices: TDD, systematic debugging, spike experiments, plan-driven development, direct implementation, and code review."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [tdd, debugging, spike, planning, code-review, direct-development, workflow]
    related_skills: [github, kanban-operations]
---

# Software Development Practices

This umbrella covers structured development workflows: planning, experimenting, testing, debugging, direct implementation, and reviewing.

## Test-Driven Development (TDD)

Enforce the RED-GREEN-REFACTOR cycle before writing production code.

### Workflow
1. **RED:** Write a failing test that describes the desired behavior
2. **GREEN:** Write the minimum production code to make the test pass
3. **REFACTOR:** Clean up duplication, improve names, optimize while keeping tests green

### Implementation Steps
1. Create a test file with a single failing test
2. Run the test suite (`pytest`, `jest`, `cargo test`, etc.) — confirm it fails
3. Write minimal production code to make it pass
4. Run tests again — confirm green
5. Refactor and repeat

### Golden Rules
- Never write production code without a failing test first
- Keep tests fast (≤5s per test, ≤1min total suite)
- One conceptual assertion per test
- Use descriptive test names that explain the behavior

## Systematic Debugging

Four-phase root-cause debugging: understand before fixing.

### Phase 1: Reproduce
- Find the minimal trigger (exact command, input, state)
- Verify it fails on demand
- Record environment (OS, versions, config)

### Phase 2: Isolate
- Binary-search the code path
- Use print/logging, breakpoints, or profiling
- Eliminate variables one at a time

### Phase 3: Hypothesize
- Formulate 2–3 competing theories
- Design one experiment to falsify each theory
- Run the cheapest experiment first

### Phase 4: Fix and Verify
- Apply the smallest fix that addresses the root cause
- Confirm the reproduction no longer fails
- Run the full test suite
- Add a regression test

## Spike Experiments

Throwaway experiments to validate an idea before committing to full build.

### When to Spike
- New technology or API unfamiliar to the team
- Unclear performance characteristics
- Unknown integration complexity
- Architectural decision with irreversible consequences

### Rules
- Time-box: 2–4 hours max
- Output: a README + working proof-of-concept
- Must answer a specific yes/no question
- Code is disposable — do not merge spike code
- Decision record: keep the README, delete the code

## Plan-Driven Development

Write markdown implementation plans before coding.

### Plan Contents
- Goal (1 sentence)
- Background (why now, trade-offs considered)
- Tasks (bite-sized, numbered, with estimated effort)
- Open questions (what needs clarification before starting)
- Risks and mitigations
- Definition of done

### Output
- Write to `.hermes/plans/YYYY-MM-DD-{slug}.md`
- Do not execute the plan — only write it
- The plan becomes the acceptance criteria for later execution

## Pre-Commit Code Review

Security scan + quality gates before every commit.

### Checklist
- [ ] No secrets in diff (`git diff | grep -i 'api.?key\|token\|secret'`)
- [ ] No debug breakpoints or `console.log` / `print` statements
- [ ] No `TODO` or `FIXME` without a ticket reference
- [ ] Tests pass
- [ ] Lint passes (`eslint`, `flake8`, `clippy`, etc.)
- [ ] Type check passes (`mypy`, `tsc`, etc.)

### Automated Gate Script
```bash
#!/bin/bash
set -euo pipefail
git diff --cached | grep -iE 'api.?key|token|secret|password' && exit 1
grep -rE 'TODO|FIXME' --include='*.py' . && exit 1
pytest -q
```

## Direct Development

Execute plans in the driving session with one implementation context and explicit verification.

### Pattern
1. **Plan stage:** Write or read the scoped plan and identify the next complete slice.
2. **Implement stage:** Use direct repository tools to write tests, change code, and manage files.
3. **Verify stage:** Run the relevant tests, lint, typecheck, or build commands directly.
4. **Review stage:** Inspect the resulting diff and use an independent read-only review only when the workflow requires it.

### Constraints
- Do not delegate implementation, test writing, fixes, or repository management to subagents.
- Keep the evidence trail in the driving session so hypotheses and edits remain connected.
- Verify file writes and test results directly before reporting completion.
