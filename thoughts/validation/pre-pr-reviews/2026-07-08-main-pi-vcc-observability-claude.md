redaction guarantee the pi-vcc package provides is silently bypassed by extension log calls, and future edits will drift.
  - Impact: Redaction inconsistency (fields like authorization, token, etc. present in extension payloads are not scrubbed) and duplicated code that will rot. Also compaction options carry a preserve string of arbitrary
  user text that only the pi-vcc side would sanitize.
  - Recommended fix: Have the extension import from a shared vendored module, or duplicate the exact safeJson behavior into the extension. Add a short comment noting both must stay in sync.
  - Blocks pre-PR gate: YES (fix duplication or explicitly justify the divergence).

  Finding 3 — Set<string> fields log as {}, dropping the highest-signal data

  - Severity: P3
  - Scope: REGRESSION_FROM_THIS_DIFF
  - File: _pi/extensions/percentage-compaction.ts:521-527 (also 301-307, 383-389)
  - Evidence: compaction_failed logs interruptedTurn: options.interruptedTurn, whose pendingToolCallIds is a Set<string>. JSON.stringify(new Set(...)) returns {} and safeJson in core/log.ts also treats a Set as an object
  with no enumerable properties. The pending tool-call ids — the single most useful data for triaging why a compaction continuation stalls — silently vanish from the log line. Same happens for pending.pendingToolCallIds
  in no-cut and compaction continuation delivery-failure events.
  - Impact: Precisely the failure family we are trying to observe (mid-tool-batch continuation stalls) loses the ids we would use to correlate with the transcript.
  - Recommended fix: Convert Sets to arrays before logging (e.g. pendingToolCallIds: [...set]) at each callsite, or teach safeJson in core/log.ts to expand Set/Map.
  - Blocks pre-PR gate: NO, but strongly recommended before shipping since it degrades the diff's stated goal.

  Finding 4 — 60s continuation retry window has no cancellation on user recovery

  - Severity: P3
  - Scope: QUESTION / REGRESSION_FROM_THIS_DIFF
  - File: _pi/packages/pi-vcc/src/hooks/before-compact.ts:20, 293-341
  - Evidence: CONTINUE_AFTER_COMPACTION_MAX_WAIT_MS increased from 5000 to 60000 with a 100 ms retry interval (up to ~600 attempts). continueTimer is only cleared on successful sendMessage, expiry, or if a new
  session_compact arrives (which just returns via continuation_already_pending). There is no cancellation on agent_start, agent_end, or user-initiated turn. If the user manually types "continue" during the window and
  sendMessage transiently starts working, a duplicate continuation may still land on top of the manual recovery.
  - Impact: Possible duplicate steer message and a longer window in which stale state can be replayed. Probably rare because most transient sendMessage errors clear in <1s, but the risk surface grew 12x.
  - Recommended fix: Cancel continueTimer on agent_start (or on the first message_end after the compaction) so any user-initiated recovery wins. Alternatively, gate the retry on pi.isIdle?.() before each attempt. If
  retained, note the rationale for 60s in the code.
  - Blocks pre-PR gate: NO — clarify intent or add cancellation.

  Finding 5 — Redaction is name-only; error stacks and free-form preserve bypass it

  - Severity: P3
  - Scope: OUT_OF_SCOPE_FOLLOW_UP
  - File: _pi/packages/pi-vcc/src/core/log.ts:24, 7-16
  - Evidence: safeJson only redacts by key name (/token|secret|key|authorization|password/i). Error stacks emitted via serializeError and free-form user text like compactionIntent.preserve (up to 500 chars) or
  pending.lastError are logged verbatim. The regex is also broad enough to false-positive on unrelated names (e.g. keyword, tokenCount, key in domain terms).
  - Impact: Redaction reads as defense-in-depth but does not protect against secrets appearing inside error messages/stacks or free-form user prompts. Not a leak we can point to today, but the shape invites one.
  - Recommended fix: Either drop the redaction and document that this log path is user-local diagnostic (accurate today), or add value-side scrubbing for common secret shapes (Bearer tokens, sk-... keys) and bound stack
  length. Consider tightening the name pattern to reduce collateral redaction (\btoken\b, \bapi[_-]?key\b, etc.).
  - Blocks pre-PR gate: NO.

  4. Remaining checks

  None — coverage complete for the assigned surfaces.

  5. Final verdict

  VERDICT: FINDINGS_TO_RESOLVE

---
CLAUDE_REVIEW_LAUNCHER_METADATA
socket=claude-review-claude-pre-pr-pi-vcc-observability-2765215-f0667a12f50f
session=review
window=claude-review
model=claude-opus-4-7
effort=xhigh
transcript=/home/anichols/code/ai-configs/thoughts/validation/pre-pr-reviews/2026-07-08-main-pi-vcc-observability-claude.md.transcript.txt
readiness_regex=❯
clear_boundary=prompt-cleared marker/sentinel extraction after submit
history_limit=50000
capture_depth=50000
