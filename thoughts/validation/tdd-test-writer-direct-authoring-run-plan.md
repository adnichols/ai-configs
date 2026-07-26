# Run-plan coverage ledger — Portable Integration Integrity and Direct TDD Authorship

- **Plan:** `thoughts/plans/tdd-test-writer-direct-authoring.html`
- **Doct:** `https://doct.nodaste.com/d/workspace_759bfae3-44f1-4ce5-9bff-9077d9933a21/docs/1db5efc7-a1ac-40e6-baaf-ff9286f7f344`
- **Target branch:** `main`
- **Execution branch:** `main` (repo policy requires normal ai-configs work directly on `main`)
- **Doct state at start:** lifecycle `active`; board `in_progress`; `executionReady: true`; queue empty.

## Scope contract

Implement the four PR-reviewable plan phases only:

1. Add a triggered integration-integrity invariant to Pi doctrine and the portable repository-bootstrap rule/template.
2. Make planning, execution, and review packets materialize or validate the invariant at their appropriate layer without making `run-plan` the sole enforcement path.
3. Replace the external delegated TDD skill with a repository-owned, directly authored universal skill and prove installer distribution.
4. Reconcile the named top-level and active `profiles/nerd` Hermes consumers, refresh the source manifest, and verify the managed source bundle.

No application product/API/persistence/deployment behavior, new reviewer persona, test-writing subagent, bespoke installer path, or live Hermes install is in scope. Existing external repositories are covered only when they adopt the updated bootstrap/root-`AGENTS.md` guidance.

## Integration integrity record

| Trigger | Source of truth | Producers | Consumers | Required proof | Status |
|---|---|---|---|---|---|
| Exact workflow guidance contracts | `APPEND_SYSTEM.md`; shared skill source; bootstrap template; managed Hermes mirrors | Pi installer, shared-skill installer, repository bootstrap, Hermes source bundle | Pi, newly bootstrapped repos, Claude/Codex/Pi skills, Hermes top-level/profile skills | Source assertions, temp-home install parity, Doct source sync, Hermes manifest verification | reconciled |
| Distributed workflow behavior | Source-search inventory across base doctrine, planning, run-plan, reviewer packets, TDD, installer, and Hermes profile consumers | Direct-execution, plan authoring, review, RED test design, source bundle paths | Agents entering each workflow | Per-surface reconciliation plus bounded code review | reconciled |

## Verification ledger

| Gate | Attempt | Result | Notes |
|---|---:|---|---|
| Doct plan registration/readiness | 1 | pass | Registered, active, execution-ready, board moved to `in_progress`; queue empty before edits. |
| Plan HTML correction/source sync | 1 | pass | Corrected malformed closing markup discovered during execution startup and pushed to Doct. |
| Focused source/install/Hermes checks | 1 | pass | `bash -n`, matrix JSON parse, focused integration/TDD/Hermes checks, and `git diff --check` passed before final suite. |
| Full installer suite | 4 | pass | Final `bash test_install_shared_skills.sh` run passed 30/30; earlier attempts exposed and fixed only new TDD test-contract assertions. |
| Live shared-skill distribution | 1 | pass | `./install.sh --skills` installed the source-owned `tdd-test-writer`; `cmp` matched `~/.agents/skills/tdd-test-writer/SKILL.md` to the source. |
| Hermes source bundle | 2 | pass | Manifest refreshed after mirror changes; `python3 scripts/hermes_config_sync.py verify` reported 1700 files and no obvious secret patterns. No live Hermes apply/export was run. |

## Review-cycle ledger

| Cycle | Scope | Triggering diff | Result | Remaining budget |
|---|---|---|---|---|
| 0 | Plan readiness only (pre-implementation) | execution-ready plan | passed after two plan-specific fixes | 2 implementation-review cycles available by default |
| 1 | Whole changed guidance surface | implementation candidate | finding: run-plan reviewer gate could lack integration evidence | remediated in shared/Hermes packets and focused test |
| 2 | Reviewer-packet remediation | shared/Hermes packet and test | finding: test omitted coverage declaration and reconciliation state | remediated in focused test |
| 3 | Test-coverage remediation | exact added assertions | pass (`VERDICT: PASS`) | review complete; `Not examined: unrelated files, broader remediation, or runtime execution` |

## Deviations / discoveries

- The plan source had one unclosed `div` in Decision Attention. It was corrected before phase implementation and synchronized to Doct. This is a plan-artifact validity fix, not scope expansion.
- The first full suite revealed two narrow test-contract omissions in the newly added TDD installer assertion (the literal `cross-boundary` requirement and its Claude link setup). Both were fixed before the final passing run. The second implementation review then found missing coverage of two packet fields; the focused test was extended and the permitted targeted rereview passed. These were in-scope verification corrections, not product behavior changes.
