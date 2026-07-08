# Pre-PR implementation review: pi-vcc observability

Date: 2026-07-08

## Scope and base

- Selected review surface: Codex/Claude Code.
- Repo: `/home/anichols/code/ai-configs`.
- Branch: `main`.
- Base/range: `origin/main` plus current working-tree changes.
- Plan path: none. Standalone user request: investigate the NOD-1250 pi-vcc compaction continuation failure and add central observability for similar failures.
- Base freshness context: independent pre-PR gate; no run-plan caller, no caller-reported base-freshness status, and no known rebase-triggered rerun requirement.

## Changed files summary

- `_pi/packages/pi-vcc/src/core/log.ts` — new central JSONL logger/sanitizer for `~/.pi/logs/pi-vcc.jsonl`, with `PI_VCC_LOG_PATH` override for hermetic tests.
- `_pi/packages/pi-vcc/src/hooks/before-compact.ts` — logs session compaction / continuation lifecycle events, extends continuation retry window, cancels stale continuation timers on `agent_start`, records retained non-message entries.
- `_pi/packages/pi-vcc/src/commands/pi-vcc.ts` — logs manual compaction completion/failure.
- `_pi/packages/pi-vcc/src/details.ts` — records retained non-message entry metadata.
- `_pi/extensions/percentage-compaction.ts` — logs percentage-compaction failures and continuation-delivery failures to the same central log with sanitizer parity.
- `_pi/packages/pi-vcc/tests/before-compact.test.ts` — adds observability coverage and redirects all before-compact test logging to a temporary JSONL file.
- `_pi/packages/pi-vcc/README.md` — documents the central log.

## Review cycles and verdicts

| Cycle | Reviewer | Artifact | Verdict | Notes |
|---|---|---|---|---|
| Initial | Codex | `thoughts/validation/pre-pr-reviews/2026-07-08-main-pi-vcc-observability-codex.md` | `FINDINGS_TO_RESOLVE` | P2: new `core/log.ts` must be included; P2: test used `/home/anichols/.pi/logs/pi-vcc.jsonl` directly and polluted the real log. |
| Initial | Claude Code Opus 4.7 xhigh | `thoughts/validation/pre-pr-reviews/2026-07-08-main-pi-vcc-observability-claude.md` | `FINDINGS_TO_RESOLVE` | Blocking sanitizer drift in percentage extension; P3 Set serialization, stale retry cancellation, and redaction limitations. |
| Targeted rereview | Codex | `thoughts/validation/pre-pr-reviews/2026-07-08-main-pi-vcc-observability-codex-rereview.md` | `CLEAN_FOR_PR` | Prior Codex blockers resolved; no unresolved in-scope P1/P2. |
| Targeted rereview | Claude Code Opus 4.7 xhigh | `thoughts/validation/pre-pr-reviews/2026-07-08-main-pi-vcc-observability-claude-rereview.md` | `FINDINGS_TO_RESOLVE` | Sanitizer and Set fixes resolved; found remaining P2 test-suite pollution because other tests still wrote to the real central log. |
| Finding 2 rereview | Claude Code Opus 4.7 xhigh | `thoughts/validation/pre-pr-reviews/2026-07-08-main-pi-vcc-observability-claude-finding2-rereview.md` | `CLEAN_FOR_PR` | Suite-level `PI_VCC_LOG_PATH` override resolved central-log pollution; no unresolved in-scope P1/P2. |
| Finding 2 rereview | Codex | `thoughts/validation/pre-pr-reviews/2026-07-08-main-pi-vcc-observability-codex-finding2-rereview.md` | `CLEAN_FOR_PR` | Confirmed all before-compact logging hot paths write to temp log; no unresolved in-scope P1/P2. |

## Triage table

| Finding | Reviewer | Severity | Scope | Decision | Evidence |
|---|---|---|---|---|---|
| `core/log.ts` was untracked while imported by tracked files | Codex | P2 | PLAN_PREREQUISITE | Fixed / must include in final commit | File is present in worktree and live pi-vcc mirror was synced after final fixes. |
| New observability test used `/home/anichols/.pi/logs/pi-vcc.jsonl` directly | Codex | P2 | REGRESSION_FROM_THIS_DIFF | Fixed | `before-compact.test.ts` now uses suite-level temp `PI_VCC_LOG_PATH`; targeted tests show central log stayed `180 -> 180`. |
| Percentage extension duplicated raw unsanitized logging | Claude | P2 | REGRESSION_FROM_THIS_DIFF | Fixed | Extension now has sanitizer parity with `core/log.ts`, redacts keys/values, truncates long strings, handles Error/Set/Map, and comments that it must stay in sync. |
| Set fields logged as `{}` | Claude | P3 | REGRESSION_FROM_THIS_DIFF | Fixed as small safe cleanup | `pendingToolCallIds` now serialize as arrays in log/detail payloads; sanitizer also handles Set. |
| 60s retry window lacked cancellation on user recovery | Claude | P3 | QUESTION / REGRESSION_FROM_THIS_DIFF | Fixed as small safe cleanup | `cancelPendingContinuation("agent_started")` clears stale retry timer and logs `continuation_cancelled`. |
| Name-only redaction limitations | Claude | P3 | OUT_OF_SCOPE_FOLLOW_UP | Partially fixed in scope; no remaining blocker | Added value-side Bearer/sk-style scrubbing and long string/stack truncation. Remaining local diagnostic-log privacy hardening, if desired, is follow-up. |

## Fixes applied during review

- Added `PI_VCC_LOG_PATH` override support in `_pi/packages/pi-vcc/src/core/log.ts`.
- Made `before-compact.test.ts` redirect all suite log writes to a temp JSONL file and restore the environment in `afterAll`.
- Confirmed the real central log did not grow during the before-compact suite: `central_log_lines_before=180 after=180`.
- Added log sanitizer support for secret-looking keys, Bearer/sk-looking values, long string/stack truncation, `Error`, `Set`, and `Map`.
- Mirrored sanitizer behavior in `_pi/extensions/percentage-compaction.ts` with a sync comment because the standalone extension cannot safely import the vendored package helper in every install context.
- Converted pending tool-call ID Sets to arrays in the relevant log/detail payloads.
- Cancelled pending pi-vcc continuation retry timers when a new `agent_start` begins.
- Synced the final pi-vcc package into the live Pi mirror at `~/.pi/agent/local-packages/ai-configs/pi-vcc`.

## Verification after fixes

- `bun --print "await import('./_pi/extensions/percentage-compaction.ts'); 'percentage-ok'"` — pass.
- `bun test _pi/packages/pi-vcc/tests/before-compact.test.ts` — 24 pass.
- `bun test _pi/packages/pi-vcc/tests/before-compact.test.ts` with central-log line check — 24 pass; `central_log_lines_before=180 after=180`.
- `bun test _pi/packages/pi-vcc/tests --timeout 20000` — 157 pass.
- `bun --print "await import('./_pi/extensions/percentage-compaction.ts'); await import('./_pi/packages/pi-vcc/src/core/log.ts'); 'imports-ok'"` — pass.

## Remaining follow-ups

- No unresolved in-scope P1/P2 findings remain.
- Optional non-blocking follow-up: further harden local diagnostic log privacy if desired beyond current key/value scrubbing and truncation.

## Final gate result

- Codex verdict: `CLEAN_FOR_PR` by targeted final rereview; no unresolved in-scope P1/P2.
- Claude Code verdict: `CLEAN_FOR_PR` by targeted final rereview; no unresolved in-scope P1/P2.
- Final gate result: `CLEAN_FOR_PR`.
- Since this was invoked independently rather than from `run-plan`, no `OPEN_PR_READY` handoff is required; the implementation is ready for normal final commit/PR steps. No Codex PR thumbs-up is required beyond the clean local review artifacts.
