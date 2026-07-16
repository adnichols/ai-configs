Scope: `_pi/extensions/codex-review/runtime.ts`, `skills/codex-review-partner/scripts/run-review.sh`, and directly related runtime/production tests only.

1. Numeric-string `codexSignal` preserves truthful inner-timeout/signal classifications:
   - Launcher (`run-review.sh:262`, `271-274`) emits `SIGNAL_NUMBER=$((CODEX_EXIT-128))` as a bash string, JSON-encoded via `signal or None` (`run-review.sh:95`) so `codexSignal` is a numeric string like `"9"`/`"15"`.
   - `validLauncherProtocol` (`runtime.ts:191-196`) parses numeric strings via `/^\d+$/.test` → `Number()`, then requires `codexExitCode === 128 + signalNumber!` for INNER_TIMEOUT and CODEX_REVIEW_CODEX_SIGNAL. Right-associativity of the ternary chain is correct (numeric branch first, string branch second, undefined default). SIGKILL→137/9 and SIGTERM→143/15 map cleanly. `test_run_review_contract.sh:167` (`codexSignal in (9,'9')`) exercises the numeric-string path. Invariant intact.

2. Canonical outer exit mappings and OUTPUT_COMMIT failure classification enforced:
   - `validLauncherProtocol` rule table (`runtime.ts:181-188`) fixes outer codes: INNER_TIMEOUT=[124], ARTIFACT_MISSING=[20], ARTIFACT_INVALID=[21], OUTPUT_COMMIT_FAILED=[23,129,130,143]; CODEX_SIGNAL/EXIT_NONZERO/LAUNCH_FAILED bound to `outerCode === protocol.codexExitCode`; outer signal is rejected unconditionally (`runtime.ts:177`).
   - Launcher exits match: 124 (`run-review.sh:264`), 20 (`:281`), 21 (`:310`), 23 (`:343`); `abort_publication` writes the OUTPUT_COMMIT_FAILED status then exits 129/130/143 for HUP/INT/TERM around the protected `mv` (`run-review.sh:314-345`) and stays trapped only across the commit window. Invariant intact.

3. Failed identity-safe cleanup is explicit and retains evidence:
   - `finishOnce` gates `safeUnlink(job.reservationFile)`/`safeUnlink(job.processIdentityFile)` on `cleanupSucceeded` (`runtime.ts:334`); `launcherStatus` is never unlinked on the finish path; forced=`CODEX_REVIEW_CLEANUP_FAILED` when `terminateVerified` fails (`runtime.ts:312-313`).
   - `cancelOnce` gates the same unlinks on `cleanupSucceeded` (`runtime.ts:415`).
   - Directly covered by `runtime.test.mjs:23` ("mismatched private process identity …") which asserts `existsSync(j.processIdentityFile)` after CLEANUP_FAILED. Invariant intact on the live finish/cancel paths.

4. Pending/delivering exactly-once evidence cannot be pruned:
   - `prune()` (`runtime.ts:423`) restricts the candidate set to `TERMINAL` jobs with `deliveryState === "delivered" || "ineligible"`, then trims by cutoff and `maxCompletedJobs`. Emergency file survives via the same key derivation. Directly covered by `restart-reconciliation.test.mjs:28`. Invariant intact.

5. Concurrently active job owned by another live Pi manager is not reconciled or killed:
   - `reconcile` (`runtime.ts:250`) skips any starting/running persisted job whose `persistedOwnerIsActive` returns true.
   - `persistedOwnerIsActive` (`runtime.ts:236-246`) rejects on boot-id drift, requires owner PID `startTime` match, and (owner-less legacy) requires the launcher PID `startTime` to match plus the manager PPID > 1 and non-zombie — preventing hijack of a launcher parented to another live manager. Reservation-mismatch protection is confirmed by `restart-reconciliation.test.mjs:22`. `terminateVerified` is only reached after ownership check, so no cross-manager kill path exists. Invariant intact.

No concrete P1/P2 regressions found in the five in-scope fixes.

VERDICT: PASS_SCOPED

---
CLAUDE_REVIEW_LAUNCHER_METADATA
socket=claude-review-claude-review-b861ebadba64-4173533-761d039d50b4
session=review
window=claude-review
model=claude-opus-4-7
effort=xhigh
transcript=/home/anichols/.herdr/worktrees/ai-configs/codex-review-plugin/thoughts/validation/pre-pr-reviews/2026-07-16-claude-convergence.md.transcript.txt
claude_session_id=7982ee4a-d95d-4d05-8fba-9e4ae1b8a201
session_record=/home/anichols/.claude/projects/-home-anichols--herdr-worktrees-ai-configs-codex-review-plugin/7982ee4a-d95d-4d05-8fba-9e4ae1b8a201.jsonl
readiness_regex=❯
clear_boundary=persisted Claude session JSONL after visible completion sentinel
history_limit=50000
capture_depth=50000
