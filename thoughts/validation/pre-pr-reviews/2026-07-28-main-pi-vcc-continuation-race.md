# Pre-PR Autoreview: pi-vcc post-compaction continuation race

- **Date:** 2026-07-28
- **Scope:** Standalone bug fix; no execution plan was supplied.
- **Base / target:** `main` / `origin/main` (`88b533e`; no committed branch delta). All candidate changes are unstaged or untracked in the live worktree.
- **Base freshness:** Local `main` tracks `origin/main`; no rebase was needed or performed. Final verification applies to the current dirty worktree.
- **Reviewer surface:** Pi active-harness `reviewer` subagent (`openai-codex/gpt-5.6-terra`, medium reasoning), read-only.

## Scope baseline

### Intended behavior

Pi 0.82.1 can mark the session idle before its underlying `Agent.activeRun` is cleared during semantic compaction. An active `compact_context` continuation must therefore not call `sendMessage` from the compaction lifecycle callback. It must submit after `agent_settled`, retain a bounded fallback for a fully idle manual compaction, and never submit through an old `ExtensionContext` after session replacement.

### Supported paths

- Active `compact_context` semantic-boundary continuation.
- Existing command-origin and interrupted-turn continuation paths.
- Session shutdown/replacement while an active semantic continuation is deferred.
- Source and installed pi-vcc deterministic continuation-soak paths.

### Explicit non-goals

- Changing the continuation wire protocol or `sendMessage` options.
- Changing Pi core's session/Agent lifecycle implementation.
- Adding a new public configuration option or retry policy.
- Claiming a provider-backed Luna E2E when the local provider does not return a model response.

### Integration integrity

The exact continuation contract remains owned by `_pi/packages/pi-vcc/src/core/coordinator.ts`; the producer is `session_compact` in `_pi/packages/pi-vcc/src/hooks/before-compact.ts`; the consumer is Pi 0.82.1 `AgentSession.sendCustomMessage()` plus durable coordinator lifecycle entries. The fix preserves the existing `pi-vcc-continuation` metadata and `triggerTurn: true, deliverAs: "steer"` delivery. The source/installed package hook SHA-1 reconciled to `33a3a7dc9a4f0a96992ace057ed106ccc3db20f6`.

## Candidate files

- `_pi/packages/pi-vcc/src/hooks/before-compact.ts`
- `_pi/packages/pi-vcc/tests/before-compact.test.ts`
- `scripts/pi-vcc-continuation-soak.ts`
- `scripts/pi-vcc-real-host-integration.ts`
- `scripts/fixtures/pi-vcc-actual-compact-context-trigger.ts` (untracked)

## Review-cycle ledger

| Cycle | Reviewer result | Triage / disposition |
| --- | --- | --- |
| Infrastructure attempt (not counted) | `fd97e960-4e7e-488` inspected an isolated clean `/tmp/pi-agent-*` worktree with `STATUS_SHORT: EMPTY`. `REVIEW_INFRASTRUCTURE_FAILURE`; discarded. | Relaunched against the live dirty worktree. |
| 1 | `4311d316-a357-4d7`, live worktree, found P1 in `before-compact.ts`: a 100ms fallback retained a stale compaction-time context after `session_shutdown`. | Fixed in scope by clearing queued timers on `session_shutdown`; added regression coverage. |
| 2 (targeted rereview) | Same live-worktree reviewer verified the shutdown cleanup and returned `CLEAN`. | No unresolved in-scope P1/P2 findings. |

### Triage

| Finding | Reviewer | Severity | Scope | Decision | Evidence |
| --- | --- | --- | --- | --- | --- |
| Deferred fallback could submit through an invalid old session after shutdown/replacement. | `4311d316-a357-4d7` | P1 | `REGRESSION_FROM_THIS_DIFF` | Fixed | Queue now clears every timer on `session_shutdown`; targeted test keeps the fallback window open past 100ms and observes no delivery. |

## Verification after the last fix

| Command / check | Result |
| --- | --- |
| `bun test _pi/packages/pi-vcc/tests/before-compact.test.ts` | PASS — 31 tests, 0 failures. |
| `bash scripts/run-pi-vcc-continuation-soak.sh --candidate installed --compactions 20 --fault-matrix all --artifacts-dir /tmp/pi-vcc-installed-soak-final` | PASS — audit passed. |
| `bash scripts/run-pi-vcc-continuation-soak.sh --candidate installed --compactions 100 --fault-matrix all --artifacts-dir /tmp/pi-vcc-installed-long-soak-final` | PASS — 102 terminal coordinator transactions; audit passed. |
| `git diff --check` | PASS. |
| Transactional live package refresh (`./install.sh --pi-vcc` via a temporary local Pi CLI wrapper) | PASS; installed package matches source hook hash. |

## Verification limitations and dispositions

- The full real-host integration script did not reach the new case because its pre-existing first `AgentSession.reload()` case hung in this environment. The new real-host fixture is present but that full harness result is not claimed as passing.
- A source-soak run after the installer could not resolve the source package's peer dependency `@earendil-works/pi-coding-agent`. The installed candidate, which is the actual live package, completed both the 20- and 100-compaction soak runs successfully.
- Two direct Luna CLI validation attempts did not emit a session entry, model response, tool call, or test output. They were stopped after 5m42s and 1m53s. This is an external-provider validation limitation, not a clean Luna-backed E2E result.

## Final gate

**Reviewer verdict: PASS equivalent.** The active-harness reviewer has no unresolved in-scope P1/P2 findings after the targeted rereview. The reviewer did not execute behavioral tests by policy; the coordinator-owned verification listed above is separate evidence. There are no remaining non-blocking review findings and no external approval is required for this local gate.

**Next step:** This was an independent autoreview, not `run-plan`; no PR action was requested.
