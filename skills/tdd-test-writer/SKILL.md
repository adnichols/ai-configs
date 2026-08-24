---
name: tdd-test-writer
description: Guide direct RED-phase test authoring by the driving agent. Use for test-first development, RED/GREEN/REFACTOR work, behavior-gating tests, and regression tests that must fail before implementation.
---

# Direct TDD Test Authoring

Use this skill to define and verify the RED phase without delegating test changes. The driving agent writes and runs the RED tests directly, then hands a strict implementation contract to the next implementation step. This skill does not authorize production-code changes during RED.

## Required rules

1. Do not modify production code during RED.
2. Do not delegate test authoring, test execution, or RED-phase fixes to a subagent or another persona.
3. Write behavior-focused tests that fail for the expected behavioral reason, not because of syntax, setup, or an unavailable fixture.
4. Run the narrowest deterministic command that exercises the new or updated tests and record the expected failure.
5. Do not weaken, delete, or bypass the RED test to make a later implementation pass. A changed requirement needs a new explicit acceptance decision and updated test contract.
6. Reuse the repository's existing runner, naming, fixture, and helper conventions unless the accepted scope requires a change.
7. For workflow fixtures that depend on service/account transport, explicitly initialize Hub availability/default state, selected profile or account root, and transport success/failure. Clear inherited environment/home configuration first. Missing axes are fixture setup failures, not product failures.

## RED workflow

### 1. Establish the behavior contract

Translate the request into observable acceptance criteria. Identify the happy path, relevant failure or guardrail path, and ambiguity or boundary case where a misleading partial implementation could pass. For a bug fix, capture the reported failure mode as a regression test.

Read the current implementation, existing tests, and repository instructions before writing the test. If a requirement is genuinely ambiguous, stop for the smallest needed product decision rather than encoding an invented behavior.

### 2. Choose the test shape

Keep the test as close as practical to the observable entry point. Unit tests remain appropriate for local behavior; use a stronger shape only when the trigger requires it.

- **Integration-integrity trigger:** When exact-contract or distributed-production work applies, load `integration-integrity`. Test the actual cross-boundary or production-dispatch path represented by its inventory, and reuse the shared contract artifact where available.
- **Documented CLI trigger:** When a documented command form is part of the request, execute that representative form through the actual parser. Help-text or documentation-string assertions alone do not prove parser acceptance.
- **External deterministic boundary:** When an external service sits between components, prove the actual request/response or serialized boundary with the supported deterministic fake, capture, or fixture. Do not require an impossible in-process round trip.

If none of these triggers applies, keep the RED test lightweight and local. Do not fabricate integration coverage merely because this skill was loaded.
For concrete good/bad behavior-test examples, read `references/tests.md`. When a boundary may need a fake, read `references/mocking.md`; prefer a real test dependency and mock only genuine system boundaries.


### 3. Author and verify RED

Write or update only the test files and necessary test fixtures. For relevant workflow tests, declare the fixture axes `hubState`, `profileRoot`, and `transportResult` (using repo-local equivalent names) before execution and reject omission or conflicting inherited state with a setup diagnostic. Run the narrowest command that executes the changed behavior. Confirm the failure is caused by the missing or incorrect production behavior. If the failure is a test problem, repair the test and rerun it while production code remains untouched.

Record the test files, command, expected failure summary, and any assumptions in the working notes or plan-owned evidence surface. The plan or execution layer owns coverage-ledger and remediation-task management; this skill supplies the RED contract and evidence.

### 4. Hand off without weakening

The implementation handoff must name the immutable RED test files, the exact command, the expected failing behavior, the allowed production surfaces, and the acceptance condition for GREEN. The driving agent keeps ownership of any later implementation, verification, and test updates.

## Required RED handoff format

```markdown
TDD RED PHASE COMPLETE

## Test files
- <path>

## Verification
- Command: <exact command>
- Result: FAIL (expected)
- Behavioral reason: <missing or incorrect behavior>

## Implementation contract
1. Preserve these RED tests unless the accepted requirement changes: <paths>
2. Implement only the smallest in-scope production change: <surfaces>
3. GREEN gate: <exact command> passes without weakening the tests.
4. Required boundary or dispatch proof, if triggered: <evidence>

## Assumptions
- <only if needed>
```

## Quality bar

- RED evidence is deterministic and tied to an observable accepted behavior.
- The test can reject a helper-only or disconnected-fixture implementation when a boundary or distributed-behavior trigger applies.
- The test and its command are authored and run by the driving agent.
- The handoff makes it clear what must change for GREEN and what evidence remains owned by the plan or execution workflow.
