Targeted re-review of Claude rereview Finding 2 (pi-vcc before-compact tests polluting the real central ~/.pi/logs/pi-vcc.jsonl):

  Scope of check
  - Verified the isolation mechanism in _pi/packages/pi-vcc/tests/before-compact.test.ts.
  - Confirmed the log module honors the env override on every write.
  - Did not perform a broader audit outside this finding.

  Fix analysis
  - _pi/packages/pi-vcc/tests/before-compact.test.ts:26-33: module-scope beforeAll captures the previous process.env.PI_VCC_LOG_PATH, creates a per-suite temp dir via mkdtemp(join(tmpdir(), "pi-vcc-log-test-")), and
  points PI_VCC_LOG_PATH at <temp>/pi-vcc.jsonl before any test runs. Because Bun evaluates the test file top-to-bottom and beforeAll runs before the first it, every subsequent test that transitively invokes
  logPiVccEvent will hit the temp file, not the real central path.
  - _pi/packages/pi-vcc/tests/before-compact.test.ts:35-39: afterAll restores the prior env value (or deletes it when originally undefined) and recursively removes the temp dir. State leakage into other test files is
  prevented.
  - _pi/packages/pi-vcc/tests/before-compact.test.ts:395-426: the specific "logs session compactions" test now reads process.env.PI_VCC_LOG_PATH, throws a clear error if the override was not applied, snapshots the file
  text before triggering session_compact, then asserts on the appended tail only. This is diff-based, so it also tolerates other tests in the suite writing to the same temp file.
  - _pi/packages/pi-vcc/src/core/log.ts:7: getPiVccLogPath reads process.env.PI_VCC_LOG_PATH on every call (no module-load caching), so the beforeAll override is honored for all logPiVccEvent code paths hit during the
  suite.

  Independent reasoning about the reported manual verification
  - Pre/post wc -l on ~/.pi/logs/pi-vcc.jsonl staying at 180 across a full run of this test file (24 pass) is consistent with the code above: no logger call can escape the env override because getPiVccLogPath re-reads
  process.env every time.

  Risk of new P1/P2 from the fix itself
  - beforeAll uses mkdtemp (unique per run, no collisions with parallel runs).
  - afterAll correctly handles the undefined-vs-set restore branch, so it will not accidentally leave PI_VCC_LOG_PATH="undefined" behind.
  - The suite-level override does not weaken the assertions of the "logs session compactions" test; it still verifies that an entry with event === "session_compact" and the matching compactionEntryId is appended.
  - No new global state, no filesystem writes outside mkdtemp, no reliance on Date.now() or randomness beyond mkdtemp.

  Prior blocking Finding 2 status
  - The env-based redirect covers all hot paths inside this test file, not just the one test that previously used mock.module. The prior failure mode (24 real central-log entries appended) is eliminated by construction
  and matches the reported 180→180 measurement.

  Conclusion
  - Prior blocking Finding 2 is resolved.
  - No unresolved in-scope P1/P2 remains from this fix.

  VERDICT: CLEAN_FOR_PR

---
CLAUDE_REVIEW_LAUNCHER_METADATA
socket=claude-review-claude-pre-pr-pi-vcc-finding2-rereview-3033541-182170b671a1
session=review
window=claude-review
model=claude-opus-4-7
effort=xhigh
transcript=/home/anichols/code/ai-configs/thoughts/validation/pre-pr-reviews/2026-07-08-main-pi-vcc-observability-claude-finding2-rereview.md.transcript.txt
readiness_regex=❯
clear_boundary=baseline-relative marker/sentinel occurrence diff after submit
history_limit=50000
capture_depth=50000
