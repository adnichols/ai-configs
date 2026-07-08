**Coverage**

| Scope item | Implementation evidence | Test evidence | Status |
|---|---|---|---|
| Prior P2 same-percent failure retry | `_pi/extensions/percentage-compaction.ts:482-486` ratchets owned non-no-cut `onError` before continuation | `scripts/percentage-compaction.test.ts:577-598` | Covered |
| Stale callbacks | Attempt ownership checks at `:435-487` | `scripts/percentage-compaction.test.ts:378-409` | Covered |
| Scheduled pi-vcc vs core overlap | Scheduler/owner at `:493-509`, core cancellation at `:771-778` | `scripts/percentage-compaction.test.ts:348-376`, `:411-431` | Covered |
| Pending continuation blocks replacement compaction | `turn_end` blocks at `:655-658`; `session_before_compact` blocks at `:762-768` | `scripts/percentage-compaction.test.ts:433-465` | Covered |
| No-cut retry suppression | No-cut ratchet at `:464-480`; suppression at `:699-705`, `:823-833` | `scripts/percentage-compaction.test.ts:467-574`, `:600-697` | Covered |
| Direct scheduled failure/cancel same-percent suppression | Failure ratchet at `:482-486`; stale suppression at `:694-698` | `scripts/percentage-compaction.test.ts:323-335`, `:577-598` | Covered |

**Findings**

No in-scope findings. The latest fix resolves the prior P2 without reopening the reviewed stale-callback, overlap, pending-continuation, no-cut, or same-percent retry races.

VERDICT: PASS_SCOPED
