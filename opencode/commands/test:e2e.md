---
description: Run Playwright e2e tests using dedicated test runner subagent
argument-hint: "[test pattern, grep filter, or empty for full suite]"
---

# Run Playwright E2E Tests

Execute Playwright tests and provide detailed results.

## Input

Test pattern or grep filter: $ARGUMENTS

The user may provide test pattern, grep filter, or empty for full suite.

## Process

### Step 1: Run Tests

Execute Playwright tests using the bash tool:

```bash
npx playwright test $ARGUMENTS
```

If that fails, try the project's test script:

```bash
npm test $ARGUMENTS
```

Use a timeout of 300000ms (5 minutes) to allow full test suite completion.

### Step 2: Capture and Analyze Results

Review the output for:

1. **Overall status** - Did tests pass or fail?
2. **Failure details** - What specifically failed and why?
3. **Patterns** - Are failures related (same component, same error type)?
4. **Actionable info** - File:line locations for investigation

### Step 3: Present to User

Summarize the test results for the user, including:
- High-level pass/fail status
- Key failures with context
- Suggested next steps (if failures exist)

## Examples

```bash
# Run full e2e suite
/test:e2e

# Run specific test file
/test:e2e document-tree-operations.test.ts

# Run tests matching pattern
/test:e2e --grep "sidebar"

# Run quick smoke tests
/test:e2e tests/e2e/promptbench-mentions.test.ts tests/e2e/promptbench-export.test.ts
```
