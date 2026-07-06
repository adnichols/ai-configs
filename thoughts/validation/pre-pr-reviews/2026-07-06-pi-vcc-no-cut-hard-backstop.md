# Pre-PR Implementation Review — pi-vcc-no-cut-hard-backstop

Date: 2026-07-06
Branch: `pi-vcc-no-cut-hard-backstop`
Plan: `thoughts/plans/pi-vcc-no-cut-hard-backstop-recovery.html`
Comparison: current branch working tree against repository base; includes committed, staged, and unstaged changes at review time.

## Changed files

- `_pi/README.md`
- `_pi/extensions/percentage-compaction.ts`
- `_pi/packages/pi-vcc/README.md`
- `_pi/packages/pi-vcc/src/hooks/before-compact.ts`
- `_pi/packages/pi-vcc/src/types.ts`
- `_pi/packages/pi-vcc/tests/before-compact.test.ts`
- `scripts/percentage-compaction.test.ts`
- `thoughts/plans/pi-vcc-no-cut-hard-backstop-recovery.html`

## Scope summary

Implements Pi VCC no-cut hard-backstop recovery so active agent sessions continue when high reported context cannot produce a safe compaction cut. Scope is limited to repo-owned percentage compaction extension, vendored pi-vcc hook/types/tests/docs, and the execution plan. Pi core/provider accounting and UI/footer percentage fixes remain out of scope.

## Verification after final fixes

| Command | Result |
|---|---|
| `bun test scripts/percentage-compaction.test.ts` | PASS — 38 pass |
| `cd _pi/packages/pi-vcc && bun test` | PASS — 156 pass |
| `git diff --check` | PASS |
| `bash scripts/check-pi-vcc-upstream.sh --summary` | Expected exit 2 due pre-existing stale upstream metadata: reviewed `0.3.18`/`45e93e8`, latest `0.4.0`/`b9e0bab`; documented in plan decision log |

## Review cycles

| Cycle | GPT verdict | GLM verdict | Notes |
|---|---|---|---|
| Scoped implementation review | `PASS_WITH_DOCUMENTED_OUT_OF_SCOPE_FOLLOW_UPS` | `PASS_WITH_DOCUMENTED_OUT_OF_SCOPE_FOLLOW_UPS` | GLM prior findings resolved; GPT noted core-gate/README follow-ups, GLM noted optional pre-delivery timeout hardening. Core-gate and README items were fixed; optional timeout remains deferred. |
| Pre-PR initial gate | `FINDINGS_TO_RESOLVE` | `CLEAN_FOR_PR` | GPT found P2 core high-usage fallback halt path and P3 exact unchanged user re-arm gap. GLM noted non-blocking retry timer cleanup. |
| Pre-PR follow-up | `FINDINGS_TO_RESOLVE` | `CLEAN_FOR_PR` | GPT found exact unchanged user re-arm still blocked by `session_before_compact` stale check. GLM noted conditional non-blocking user counter issue from injected continuation messages. |
| Final narrow gate | `CLEAN_FOR_PR` | `CLEAN_FOR_PR` | Both prior findings resolved with tests. |

## Triage table

| Finding | Reviewer | Severity | Scope | Decision | Evidence |
|---|---|---|---|---|---|
| `noCutRetryState` not cleared on successful non-extension/core compaction | GLM scoped review | P2 | IN_PLAN | Fixed | `session_compact` now clears `noCutRetryState`; regression `successful core compaction clears no-cut retry suppression`. |
| Stale `pendingNoCutContinuation` could outlive a new compaction | GLM scoped review | P3 | IN_PLAN | Fixed | `triggerCompaction` and `session_compact` clear pending no-cut continuation; regression `new compaction attempt clears stale pending no-cut continuation`. |
| Unused `noCutClassification` details field | GLM scoped review | P3 | IN_PLAN | Fixed | Removed unused field from details typing; classification bridge remains `getLastNoCutClassification()`. |
| Core `session_before_compact` same-floored suppression gap | GPT scoped review | P3 | OUT_OF_SCOPE_FOLLOW_UP then fixed | Fixed | Core gate now suppresses same-floored no-cut and cancels non-extension hard-backstop fallback; regression coverage added. |
| README threshold wording stale | GPT scoped review | P3 | OUT_OF_SCOPE_FOLLOW_UP then fixed | Fixed | `_pi/README.md` now distinguishes nudge thresholds from `HARD_AUTO_COMPACTION_PERCENT`. |
| Core high-usage compaction could fall through to unhandled core no-cut halt | GPT pre-PR initial gate | P2 | IN_PLAN | Fixed | `session_before_compact` cancels non-extension core hard-backstop attempts and leaves extension-managed `turn_end` compaction as recovery path; regression `core auto-compaction is canceled above hard threshold unless extension-managed`. |
| Core gate ignored new-user re-arm when usage exactly unchanged | GPT pre-PR initial/follow-up | P3 | IN_PLAN | Fixed | `session_before_compact` allows extension-managed `compactionInFlight` attempts before stale cancellation; regression covers exact `96.2%` user re-arm. |
| Retry catch replaced pending timer without clearing | GLM pre-PR initial gate | P3 | REGRESSION_FROM_THIS_DIFF | Fixed | Catch path clears `pending.timer` before scheduling retry. |
| Injected no-cut continuation might self-increment `userMessageCount` | GLM pre-PR follow-up | P3 | REGRESSION_FROM_THIS_DIFF | Fixed | `message_end` ignores role=user messages with string `customType`; regression confirms no retry re-arm from `pi-vcc-no-cut-continuation`. |

## Remaining non-blocking follow-up

- Optional hardening: add pre-delivery timeout diagnostics for no-cut continuations that never become safe to send because pending tool results never arrive and no completed assistant boundary occurs. This is outside the plan acceptance criteria; current behavior safely defers until safe and clears stale continuations when a later compaction starts or succeeds.

## Final gate result

- GPT verdict: `CLEAN_FOR_PR`
- GLM verdict: `CLEAN_FOR_PR`
- Final verification rerun after last fix: PASS for targeted extension tests, pi-vcc package tests, and diff whitespace check.
- Next step: `OPEN_PR_READY`
