# Pre-PR Implementation Review: Herdr Pi State Reconciliation

Date: 2026-06-25
Branch: `herdr-pi-state-reconciliation`
Plan: `thoughts/plans/herdr-pi-state-reconciliation.html`
Base/range: `origin/main...HEAD` plus uncommitted/untracked working tree changes

## Changed files

- `_pi/extensions/herdr-agent-state.ts` — adds subagent-aware state, full reconciliation, heartbeat republish, session-boundary cleanup, and session-generation guards.
- `thoughts/plans/herdr-pi-state-reconciliation.html` — execution-ready plan and progress/deviation updates.

## Review cycles

| Cycle | GPT verdict | GLM verdict | Outcome |
|---|---|---|---|
| Scoped implementation review | `FIX_IN_SCOPE_FINDINGS` | `PASS_WITH_DOCUMENTED_OUT_OF_SCOPE_FOLLOW_UPS` | Fixed GPT `IN_PLAN` shutdown-state leak. |
| Scoped implementation rereview | `PASS_SCOPED` | `PASS_SCOPED` | No remaining scoped findings. |
| Pre-PR gate | `FINDINGS_TO_RESOLVE` | `CLEAN_FOR_PR` | Fixed GPT P2 session-generation/shutdown-release race. |
| Pre-PR gate rerun | `CLEAN_FOR_PR` | `FINDINGS_TO_RESOLVE` | Fixed GLM P3 retry-timer generation race. |
| Pre-PR final rerun | `CLEAN_FOR_PR` | `CLEAN_FOR_PR` | Gate passed; `OPEN_PR_READY`. |

## Triage table

| Finding | Reviewer | Severity | Scope | Decision | Evidence |
|---|---|---|---|---|---|
| `session_shutdown` did not reset parent/retry/blocked/last-state fields, allowing stale working/blocked into the next session. | GPT scoped review | P2-equivalent | `IN_PLAN` | Fixed. Added `clearSessionState()` and call it on shutdown. | AC7 requires shutdown cleanup before pane release and next-session safety. |
| `session_start` did not reset stale state; async shutdown could release after a newer session started. | GPT pre-PR | P2 | `IN_PLAN` | Fixed. Added `stateReportGeneration`; reset state on `session_start`; generation-guard queued reports and shutdown release. | Session-boundary cleanup is required by the plan. |
| `retryTimer` could promote an old retry hold to blocked after a newer session started. | GLM pre-PR rerun | P3 | `IN_PLAN` | Fixed. Captured `retryGeneration` and bailed before mutating state when generation changed. | Plan requires session-scoped timers/state. |
| `test_install.sh` aborts under `set -e` arithmetic increments. | GLM scoped review | N/A | `OUT_OF_SCOPE_FOLLOW_UP` | Not fixed. Pre-existing harness issue unrelated to touched files; targeted extension verification covers this change. | `./test_install.sh` fails after first PASS before exercising this extension. Tracking: separate test harness cleanup. |
| Dormant `herdr:blocked` handler is not generation-tagged. | GLM final pre-PR | P3 theoretical | `OUT_OF_SCOPE_FOLLOW_UP` / non-blocking | Not fixed. No emitter exists in repo, installed Pi extensions, or herdr repo, so no reachable input today. | Tracking: future change that introduces a `herdr:blocked` emitter should include session identity/generation in the event contract. |

## Fixes applied

- Added subagent lifecycle tracking from `subagents:created`, `subagents:started`, `subagents:completed`, and `subagents:failed`.
- Added manager-backed `hasRunning()` lookup as the authoritative running/queued subagent signal when available.
- Updated desired-state priority to preserve blocked/retry precedence and keep Herdr working while blocking subagents exist.
- Replaced stale-working-only reconciliation with full desired-state reconciliation.
- Added heartbeat republish via `HERDR_PI_HEARTBEAT_MS`.
- Added session-boundary cleanup for parent/retry/blocked state, subagent fallback IDs, timers, queued reports, and release ordering.
- Added `stateReportGeneration` guards for queued reports, retry timer promotion, and shutdown release.
- Updated and installed the repo-managed Pi extension copy.

## Verification

Commands run after the final fix:

```bash
npx --yes tsc --noEmit --module NodeNext --moduleResolution NodeNext --target ES2022 --skipLibCheck _pi/extensions/herdr-agent-state.ts
npx --yes tsx /tmp/test-herdr-agent-state.mts
npx --yes tsx /tmp/test-herdr-retry-generation.mts
./install.sh --pi >/tmp/herdr-pi-install.log && diff -u _pi/extensions/herdr-agent-state.ts ~/.pi/agent/extensions/herdr-agent-state.ts
```

Results:

- TypeScript syntax check: pass.
- Runtime Herdr/Pi socket harness: pass.
- Retry generation probe: pass.
- Pi install parity: pass.

Known verification caveat:

- `./test_install.sh` currently fails before this extension is exercised due a pre-existing `set -e` arithmetic increment issue in the test harness. This branch did not modify that script.

## Final gate result

- GPT verdict: `CLEAN_FOR_PR`
- GLM verdict: `CLEAN_FOR_PR`
- Remaining in-scope P1/P2/P3 findings: none.
- Non-blocking out-of-scope follow-ups: pre-existing `test_install.sh` harness bug; future `herdr:blocked` emitter should carry session identity/generation.
- Next step: `OPEN_PR_READY`.
