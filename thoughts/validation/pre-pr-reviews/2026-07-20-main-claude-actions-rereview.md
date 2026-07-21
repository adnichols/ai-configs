## Scope checked
- `_hermes/default/scripts/pi_analytics_action.py` (full read, restricted worker)
- `_hermes/default/scripts/gm_plan_comment_listener.py` (full read + `git diff origin/main`)
- `scripts/tests/test_gm_pi_analytics_action.py` + `scripts/tests/fixtures/pi-analytics-actions/*`
- Executed locally: exact cited 51-test combined subset (`test_pi_session_analytics`, `test_pi_analytics_ccore_publish`, `test_pi_analytics_deploy`, `test_hermes_config_sync_component`, `test_gm_pi_analytics_action`) — **51/51 PASS**, reproducing the claimed evidence exactly.

## Targeted fix verification

**1. Minimal 0600 transient projected claim file + cleanup — verified fixed.**
`_analytics_claim_projection()` (`gm_plan_comment_listener.py:214-256`) strips the claim down to only the identity/validator fields the restricted worker needs (drops `privatePrompt`, `textQuote`, and any other passthrough fields). `_write_claim_file()` (`:197-211`) creates it via `os.open(..., O_EXCL, 0o600)` then atomically renames into place. `pi_analytics_action.main()` (`pi_analytics_action.py:537-546`) unlinks the claim file in a `finally` immediately after reading it into memory — before `process_claim` even runs, not merely "eventually." `start_analytics_worker` also unlinks on a `Popen` launch failure (`gm_plan_comment_listener.py:283-286`). Confirmed by `test_restricted_worker_uses_minimal_private_claim_file_and_fixed_python_argv` (mode `0o600`, sentinels absent, `textQuote`/`privatePrompt` absent) and `test_claim_file_is_removed_after_worker_reads_it`.

**2. Persisted per-delivery closure progress — verified fixed.**
`finish_claim()` (`pi_analytics_action.py:408-436`) now loops `reply → ack → resolve`, skipping any step already `True` in `record["closure"]`, and calls `_mark_closure_step()` (`:387-405`) — same `flock`-guarded, atomic-write path as `record_decision` — immediately after each individual Doct call succeeds. `test_partial_doct_close_retry_skips_completed_reply` proves: first attempt (ack fails) → `["reply","ack","release"]`, ledger shows `reply` closed; retry → `["ack","resolve"]` only, no duplicate reply; final closure `{"reply": true, "ack": true, "resolve": true}`. Only the ack-failure case has an explicit test (not a symmetric resolve-failure case), but the loop is step-uniform with no special-casing, so the resolve-failure path is exercised by the same mechanism — not a functional gap, just a minor test-coverage gap (P3, non-blocking).

**3. Ordinary analytics-card comments stay discussion-only, never enter a worker — verified fixed.**
`dispatch_claim()` (`gm_plan_comment_listener.py:306-315`) now checks `submit_action(claim) != "agent"` *first* and calls `release_claim(...)` only (no reply/ack/resolve), returning before `is_analytics_anchor` is ever consulted. This closes the prior finding (comment-only claims on a card were previously auto-resolved by the restricted worker). Confirmed by `test_ordinary_conversation_is_noop_and_nonanalytics_agent_keeps_generic_path` and the "comment" subtests in `test_agent_routed_analytics_prefix_is_restricted_and_comments_are_noop`, which assert `start_analytics_worker`/`start_worker` are never called and only `release_claim` fires.

**4. Agent-routed malformed analytics anchors remain restricted — verified, no regression.**
`is_analytics_anchor` is still a bare `pi-analytics-card-` prefix match, checked only after the `submit_action == "agent"` gate, so any agent-routed claim with that prefix (well-formed or malformed) still routes to `start_analytics_worker`, never `start_worker`. Confirmed by `test_agent_routed_analytics_prefix_is_restricted_and_comments_are_noop` for both `CARD_ID` and `pi-analytics-card-malformed`.

**5. No regression in auth/workspace/ledger/generic-worker isolation.**
`validate_claim` (identity, author, hash/version, registry parity) and `record_decision` (idempotency/dedup) are unchanged in logic — only `closure: {}` was added to new records. `test_wrong_author_malformed_stale_and_identity_mismatches_are_rejected` and `test_duplicate_and_crash_retry_record_one_decision_without_extending_window` still pass. Command-authority allowlist (`reply/ack/resolve/release` + `documents get` only, no shell) reconfirmed by `test_restricted_commands_cannot_reach_external_mutation_systems`. Generic-worker path (`start_worker`) reachable only for non-card, agent-routed claims — reconfirmed by `test_ordinary_conversation_is_noop_and_nonanalytics_agent_keeps_generic_path`.

## Remaining P1/P2 blockers
None found. Both prior P2-blocking findings (Codex: partial-close duplicate reply, claim-file privacy persistence) and the prior P2-non-blocking finding (Claude: ordinary comments auto-resolved) are fixed and covered by passing tests. One P3 note only: the closure-retry mechanism has an explicit test for ack-failure but not resolve-failure (logic is symmetric, not flagged as a blocker).

## Final verdict
Restricted-path authorization, TOCTOU, generic-worker isolation, ledger idempotency, closure-progress persistence, and claim-file privacy handling are all sound and match their test coverage (51/51 reproduced locally, matching cited evidence exactly).

VERDICT: CLEAN_FOR_PR
