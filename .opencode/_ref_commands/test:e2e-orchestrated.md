---
description: Run E2E tests with automated debugging and fixing via subagents
argument-hint: "[test filter or grep pattern]"
---

You are the E2E Test Orchestrator. You coordinate a three-agent pipeline to run tests, debug failures, implement fixes, and verify results.

## Input

Test filter or pattern: $ARGUMENTS

## Phase 0: Prerequisites Check

Execute these checks in sequence:

```bash
# Verify not on main branch
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" = "main" ]; then
  echo "ERROR: Cannot run orchestrated tests on main branch"
  exit 1
fi

# Validate test environment
echo "=== Verifying E2E test environment ==="
pnpm test:env:e2e

# Create artifact directory
TIMESTAMP=$(date -u +"%Y-%m-%d_%H-%M-%S")
ARTIFACT_DIR="thoughts/e2e-runs/$TIMESTAMP"
mkdir -p "$ARTIFACT_DIR"
echo "Artifacts: $ARTIFACT_DIR"
```

## Phase 1: Run Tests (Playwright Runner subagent)

Spawn the Playwright Runner subagent with the test filter:

```
Task(
  subagent_type="playwright-runner",
  description="Run E2E tests with real-time failure detection",
  prompt="TEST_FILTER=\"$ARGUMENTS\" - Execute tests and stream all failures as JSON events. Cap at 3 failures maximum."
)
```

**Capture the JSON event stream** from the agent. Parse each line and:
- Write raw events to: `$ARTIFACT_DIR/failures.jsonl`
- Extract failure count and completion status

## Phase 2: Analyze Failures

Read `$ARTIFACT_DIR/failures.jsonl` and extract unique failures:

```python
failures = []
for line in jsonl:
    event = parse_json(line)
    if event.event == "test-failed":
        failures.append({
            "test_file": event.test_file,
            "line": event.line,
            "test_name": event.test_name,
            "error_message": event.error_message,
            "stack_trace": event.stack_trace,
            "project": event.project
        })
```

**Cap at 3 failures** - if more than 3 failures were detected, only process the first 3.

## Phase 3: Parallel Debugging + Fixing (Developer subagents)

For each failure (up to 3), spawn a Developer subagent in parallel:

```python
for idx, failure in enumerate(failures[:3]):
  Task(
    subagent_type="developer",
    description=f"Debug & fix E2E failure #{idx+1}: {failure.test_file}:{failure.line}",
    prompt=f"""You are debugging and fixing an E2E test failure.

**Failure #{idx+1}:**
- Test: {failure.test_file}:{failure.line}
- Name: {failure.test_name}
- Error: {failure.error_message}
- Project: {failure.project}

**Phase 1: Debug (5 minutes)**
1. Read the failing test file: {failure.test_file}
2. Analyze the code paths from the stack trace
3. Use serena_find_symbol + serena_find_referencing_symbols to trace the issue
4. Identify the root cause of the failure

**Phase 2: Fix (10 minutes)**
1. Implement a minimal fix at the root cause location
2. If the test is flaky, improve test reliability (selectors, waits)
3. Do NOT run the full test suite

**Return:**
1. Root cause analysis (2-3 sentences)
2. Files modified with line numbers
3. Fix summary (what was changed)
4. Suggested verification command
"""
  )
```

## Phase 4: Aggregate Fixes

After all Developer agents complete:

1. **Collect fix summaries** from each agent
2. **Identify affected components** from modified files
3. **Extract verification commands** from each response

## Phase 5: Verify & Re-run (Quality Reviewer subagent)

Spawn the Quality Reviewer to verify fixes:

```python
Task(
  subagent_type="quality-reviewer",
  description="Verify E2E test fixes",
  prompt=f"""You are verifying E2E test fixes from automated debugging.

**Fixes Implemented:**
{failed_fix_summaries}

**Verification Steps:**

**Step 1: Review Fix Changes**
- Read each modified file
- Ensure fixes are minimal and targeted
- Flag any potential side effects

**Step 2: Run Focused Tests**
Execute ONLY the previously failing tests. Use grep to target them:

```bash
pnpm test:e2e --grep="{failure_1_name}|{failure_2_name}|{failure_3_name}"
```

**Step 3: Regression Check**
For each component that was modified:
- Identify related test files
- Run a focused subset of related tests

**Return:**
1. Fix review (approved/needs revision)
2. Focused re-run results (passed/failed counts)
3. Any regressions detected
4. Final verdict: PASS or FAIL
"""
)
```

## Phase 6: Generate Final Report

Create `$ARTIFACT_DIR/Report.md`:

```markdown
# E2E Test Orchestration Report

## Initial Run
- **Date:** {TIMESTAMP}
- **Filter:** {ARGUMENTS or 'full suite'}
- **Duration:** {from completion event}
- **Results:** {passed} passed, {failed} failed, {skipped} skipped

## Failures Processed (max 3)

{failed_fixes_list}

## Verification Results
- **Re-run status:** {all passed / some failed}
- **Quality Review:** {PASS / FAIL}
- **Regressions:** {none / list them}

## Artifacts
- `failures.jsonl` - Raw failure events
- `Developer fix summaries` - Inline above

## Summary
{outcome_summary}
```

## Phase 7: User Notification

Present the final report to the user with:
1. High-level pass/fail status
2. List of failures processed and fixed
3. Files created in `$ARTIFACT_DIR/`
4. If cap was reached: "Fixed first 3 failures. Re-run to process remaining."
5. If failures remain unfixed: "These failures need manual investigation"

## Output Format

Present results in markdown with:
- Status emoji (✅/❌)
- Summary statistics
- Link to artifacts directory
- Suggested next action

## Example Output

```
=== E2E Test Orchestration Complete ===

📊 Initial Run: 45 passed, 3 failed, 1 skipped
🔧 Fixed: 3/3 failures
✅ Verification: All fixes verified
⏱️  Total Time: 8 minutes

Failures Fixed:
1. sidebar-collapsed-visibility:23 - selector update
2. document-tree-operations:67 - wait condition added  
3. chat-mentions:45 - async handler fixed

Artifacts: thoughts/e2e-runs/2026-01-10_20-45-00/
```

## Important Notes

- Work on feature branches only (not main)
- Cap failures at 3 per orchestration cycle
- Use parallel Developer agents for efficiency
- Always run focused re-tests for verification
- Preserve all artifacts in thoughts/e2e-runs/