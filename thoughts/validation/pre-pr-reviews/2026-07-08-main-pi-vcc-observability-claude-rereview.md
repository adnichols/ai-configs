Status: RESOLVED (per reviewer convention).
  - File is present at _pi/packages/pi-vcc/src/core/log.ts in the worktree, exports PI_VCC_LOG_PATH, getPiVccLogPath, safePiVccLogJson, logPiVccEvent, and logPiVccError. Treating worktree presence as sufficient per the
  reviewer's instruction; commit staging must include it.

  Finding 2 — Codex P2: test polluted the real central log

  Status: NOT FULLY RESOLVED — new blocking regression of the same class.

  Evidence:
  - The single new test "logs session compactions for central observability" is now hermetic: it creates a temp dir via mkdtemp, sets PI_VCC_LOG_PATH, restores the previous env value in finally, and calls rm(tempDir, {
  recursive: true, force: true }). log.ts reads PI_VCC_LOG_PATH per call via getPiVccLogPath, so the override works.
  - However, the PR's observability additions in _pi/packages/pi-vcc/src/hooks/before-compact.ts insert logPiVccEvent(...) calls on hot paths that ~20 pre-existing tests in the same file exercise: no_safe_cut
  (session_before_compact, ~9 tests), session_compact / continuation_scheduled / continuation_delivered / continuation_already_pending (session_compact, ~7 tests), and retained_non_message_entries_after_cut. None of
  those pre-existing tests set PI_VCC_LOG_PATH, so they all write to join(homedir(), ".pi", "logs", "pi-vcc.jsonl") — the same real central log the original P2 called out.
  - Empirically confirmed by running bun test _pi/packages/pi-vcc/tests/before-compact.test.ts once against the current worktree: ~/.pi/logs/pi-vcc.jsonl grew from 156 lines to 180 lines (24 new entries with events
  no_safe_cut, session_compact, continuation_scheduled, continuation_delivered, and cwd of the pi-vcc package). The single-test fix therefore does not prevent central-log pollution; the observability code in this PR
  causes the rest of the suite to keep polluting.

  Severity: P2. Scope: correctness / test hygiene. Blocks: yes.
  File/line: _pi/packages/pi-vcc/tests/before-compact.test.ts:1-609 (whole file); root cause is any pre-existing test that runs session_before_compact or session_compact handlers.
  Recommended fix: redirect PI_VCC_LOG_PATH for the entire test file — e.g., top-of-file (before importing the hook) create a temp dir, set process.env.PI_VCC_LOG_PATH in a beforeAll (or module scope) and restore + rm in
  afterAll. That preserves the observability writes for the one test that asserts on them while hermetically isolating all others.

  Finding 3 — Claude blocking: percentage-compaction.ts duplicated raw JSON logging

  Status: RESOLVED.
  - _pi/extensions/percentage-compaction.ts:83-136 introduces an inline SECRET_KEY_PATTERN, SECRET_VALUE_PATTERN, scrubLogText, serializeLogError, and safePiVccLogJson with an explicit "keep in sync with
  _pi/packages/pi-vcc/src/core/log.ts" comment — identical scrubbing behavior to the package sanitizer (key redaction, Bearer/sk- value redaction, 4000-char truncation with tail marker, Error/Set/Map handling).
  - All central log writes go through logPiVccEvent at line 123, which spreads safePiVccLogJson(data) into the JSON payload. logPiVccError (line 138) attaches raw err, which the sanitizer's Error branch normalizes via
  serializeLogError.
  - Set → array conversion is present at every relevant callsite: no_cut_continuation details (pendingToolCallIds: [...pending.pendingToolCallIds] at 331, 353), compaction continuation details (414, 437), and
  interruptedTurn.pendingToolCallIds at 576–578 in the compaction_failed payload. The sanitizer would also flatten these automatically, so the explicit spreads are defensive-in-depth.

  Bonus fix — cancel pending continuation timer on agent_start

  Status: RESOLVED.
  - _pi/packages/pi-vcc/src/hooks/before-compact.ts:263-274 adds cancelPendingContinuation("agent_started") invoked from the agent_start handler; it clears the timer only if one is armed, sets continueTimer = undefined,
  and emits logPiVccEvent("continuation_cancelled", { reason }). This eliminates the double-recovery risk after manual/user resumption. The added log call also inherits the central-log pollution risk under Finding 2 but
  does not introduce any additional blocking behavior.

  Other in-scope concerns

  - logPiVccError in percentage-compaction.ts (line 138) passes the raw err under error. safePiVccLogJson in that same file handles Error instances explicitly, so redaction and truncation still apply. Behavior parity
  with the package log.ts is fine.
  - No new secret-leak, data-loss, or logic-regression paths detected in the four listed files beyond the pollution issue.

  Verdict

  VERDICT: FINDINGS_TO_RESOLVE

  Blocking item to address before PR: extend Finding 2's hermetic override so _pi/packages/pi-vcc/tests/before-compact.test.ts (and any other pi-vcc tests that exercise session_before_compact/session_compact) redirect
  PI_VCC_LOG_PATH for the full run, not just the single new observability test. The other two prior blocking findings and the bonus retry-cancel are resolved with no new blocking P1/P2 introduced.

---
CLAUDE_REVIEW_LAUNCHER_METADATA
socket=claude-review-claude-pre-pr-pi-vcc-rereview-2937211-752d7ba7bef3
session=review
window=claude-review
model=claude-opus-4-7
effort=xhigh
transcript=/home/anichols/code/ai-configs/thoughts/validation/pre-pr-reviews/2026-07-08-main-pi-vcc-observability-claude-rereview.md.transcript.txt
readiness_regex=❯
clear_boundary=prompt-cleared marker/sentinel extraction after submit
history_limit=50000
capture_depth=50000
