## Scope checked
- `_hermes/default/scripts/gm_plan_comment_listener.py` (diff vs origin/main + full read)
- `_hermes/default/scripts/pi_analytics_action.py` (new, full read)
- `scripts/tests/test_gm_pi_analytics_action.py` + `scripts/tests/fixtures/pi-analytics-actions/{config,valid-agent-claim,ordinary-conversation-claim,non-analytics-agent-claim}.json`
- `_hermes/default/manifest.json` (grep for analytics/listener paths), `_hermes/default/components/pi-analytics-collector.json`, `_hermes/default/cron/jobs.json` diff (both job entries)
- Remote GM snapshots at `/tmp/hermes-daily-pi-analytics-mbp-review/`: `orchestrator.py`, `pi_analytics_phase.py`, `publish.py`, `render.py` (targeted sections), `test_gm_pi_analytics_publish.py`, plus `range.diff` for change shape
- Executed locally: full `scripts/tests` discovery (95 tests, OK) and the exact cited 47-test combined subset (`test_pi_session_analytics`, `test_pi_analytics_ccore_publish`, `test_pi_analytics_deploy`, `test_hermes_config_sync_component`, `test_gm_pi_analytics_action`) — 47/47 OK, matching the claimed evidence exactly.
- Not executed: the remote 20-test `test_gm_pi_analytics_publish.py` suite itself — the shared snapshot directory contains only 5 of the `gm` package's files, not sibling modules (`calendar_phase`, `coding_sessions_phase`, `review_phase`, etc.) it imports transitively via `orchestrator`. Verified by static/code-path cross-reference instead (see below).

## Coverage table
| Area | Result |
|---|---|
| Auth/identity (routed Agent action, Aaron user ID, card/selector match) | Verified in code + tests; fails closed on missing config, wrong author, wrong selector |
| TOCTOU (registry read vs. live document version) | Verified: `require_current_document_version` re-checks live Doct version after registry-based validation, before any mutation |
| Generic-worker escape | Verified: `is_analytics_anchor` forces any `pi-analytics-card-*`-anchored claim (even malformed) through the restricted worker, never `start_worker`; confirmed by test and by grep (no `hermes`/`shell=True` in either file) |
| Command authority | Verified: restricted worker only ever shells out to `doct-agent plans {reply,ack,resolve,release}` and `doct-agent documents get`; test asserts no `hermes/linear/todoist/benchmark/git/config` substrings reach argv |
| Ledger idempotency/persistence | Verified: `flock`-guarded read-modify-write, atomic tempfile+fsync+`os.replace`+dir-fsync; duplicate/crash-retry test proves one recorded decision, first-writer-wins |
| Producer/consumer parity | Verified: `publish.py`'s `upsert_registry` field names/types (`document_version` int, `html_sha256`, `pi_analytics_cards[{card_id,signal_key,evidence_snapshot_id}]`, `routine`, `status`) exactly match what `pi_analytics_action._active_registry_entry`/`validate_claim` reads |
| Display-state semantics (D4) | Mostly verified against fixtures/tests; one deviation found (below) |
| Privacy leakage | Verified: sentinel tests pass across ledger, replies, HTML, registry; ledger records only hashes/action labels, never body/textQuote content |
| Nonfatal behavior | Verified: analyzer/collector reader wraps broad `Exception` to warning payload; corrupt ledger state is caught and reported as a warning, not a crash |
| Host ownership (mbp-only publisher, dever component-only) | Verified: `jobs.json` diff adds only `a91c0d7e4b22` (collector, `no_agent: true`, local delivery); `039f96dcecfc` (GM publisher) untouched; component manifest lists only `scripts/pi_analytics_collector.py`; full manifest includes `pi_analytics_action.py`, confirming it ships only in the mbp full bundle |
| Verification truthfulness | Confirmed: cited "47 PASS" is exact and reproducible; remote "20 PASS" not independently re-run (see caveat) |

## Findings

**1. [P2, non-blocking] Ordinary (non-Agent-routed) comments anchored on a Pi Analytics card get auto-resolved by the restricted worker instead of being left as discussion-only, contradicting the literal AC-6 text.**
- Scope: display-state/behavior semantics (`_hermes/default/scripts/gm_plan_comment_listener.py`, `_hermes/default/scripts/pi_analytics_action.py`)
- Trigger: Aaron replies in ordinary conversation (Doct `submitAction: "comment"`) directly on/near a `pi-analytics-card-<signal>` anchor, without using the routed Agent action.
- Path: `dispatch_claim()` (`gm_plan_comment_listener.py:248-257`) checks `is_analytics_anchor(claim)` *before* checking `submit_action(claim)`, so any claim anchored on an analytics card — regardless of submit type — is routed to `start_analytics_worker`, never to the plain "ordinary conversation, release only" branch. Inside `pi_analytics_action.validate_claim` (`pi_analytics_action.py:164-166`), the non-`agent` submit action is correctly rejected (no analytics state changes — confirmed safe), but `reject_claim` then replies "Pi analytics action rejected: ... require the routed Agent action" and **acks + resolves the Doct thread** (`pi_analytics_action.py:405-435`).
- Impact: a plain discussion comment on a card gets automatically closed with a boilerplate rejection instead of remaining open, discussion-only, as D2/D4 state ("Ordinary conversation comments remain discussion-only") and AC-6 states verbatim ("Ordinary comments do nothing"). No analytics state, ledger, or external system is affected — this is a UX/spec-fidelity deviation, not a security or data-integrity defect.
- Evidence: code paths above; test `test_gm_pi_analytics_action.py::test_wrong_author_malformed_stale_and_identity_mismatches_are_rejected`, "wrong submit action" subtest, explicitly asserts `plan_actions(calls) == ["reply","ack","resolve"]` for this exact scenario — i.e., this is deliberate, tested behavior, not an oversight.
- Diff relationship: introduced by this slice's `dispatch_claim`/`is_analytics_anchor` ordering; pre-existing `start_worker` path already handled ordinary comments correctly for non-card anchors.
- Smallest fix: in `dispatch_claim`, check `submit_action(claim) == "agent"` first; only escalate to the restricted analytics worker when the claim is both card-anchored *and* agent-routed. For a card-anchored claim with `submitAction != "agent"`, release it the same way as any other ordinary comment (no reply/ack/resolve) rather than routing to the restricted worker at all. (This preserves the existing malformed-anchor defense for `submitAction == "agent"` cases, which is the actual bypass vector the design cares about.)
- Blocking: No — recommend explicit confirmation with product intent (AC-6 wording is unambiguous, but prior review rounds marked this plan execution-ready, so this may have been a conscious trade-off favoring closing the loop over leaving stray threads open).

No other P1/P2 issues surfaced after reviewing auth/TOCTOU, generic-worker isolation, ledger idempotency, producer/consumer field parity, host-ownership isolation, and privacy-sentinel handling — all matched their tests and held up under manual trace.

## Remaining checks if needed
- Follow-up slice: execute `test_gm_pi_analytics_publish.py` against the actual `adn_vault/_agents` package on mbp (not just the 5-file snapshot) to directly confirm the claimed "20 PASS" rather than relying on static cross-reference of `publish.py`/`pi_analytics_phase.py`/`render.py`/`orchestrator.py` against the test file's assertions.

## Final verdict
Restricted-path authorization, TOCTOU handling, generic-worker isolation, ledger idempotency, host-ownership isolation, and privacy handling are all sound and match their test coverage, which is real (47/47 reproduced locally). One non-blocking behavioral deviation from AC-6's literal wording was found (ordinary comments on analytics cards get auto-resolved rather than left untouched) — worth a product confirmation but not a merge blocker given no analytics-state, security, or privacy impact.

VERDICT: CLEAN_FOR_PR

---
CLAUDE_REVIEW_LAUNCHER_METADATA
socket=claude-review-claude-review-e99e0efd70cf-1820088-2654925ce3b7
session=review
window=claude-review
model=claude-sonnet-5
effort=xhigh
transcript=/home/anichols/code/ai-configs/thoughts/validation/pre-pr-reviews/2026-07-20-main-claude-actions.md.transcript.txt
claude_session_id=e88ee09b-aa21-4df1-a26e-57096f37bba4
session_record=/home/anichols/.claude/projects/-home-anichols-code-ai-configs/e88ee09b-aa21-4df1-a26e-57096f37bba4.jsonl
readiness_regex=❯
clear_boundary=persisted Claude session JSONL after visible completion sentinel
history_limit=50000
capture_depth=50000
