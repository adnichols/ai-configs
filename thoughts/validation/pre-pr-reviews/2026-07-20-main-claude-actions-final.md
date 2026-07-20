## Scope checked
- `_hermes/default/scripts/gm_plan_comment_listener.py:214-256` (`_analytics_claim_projection`), full read
- `_hermes/default/scripts/pi_analytics_action.py` (`validate_claim`, `claim_parts`, `_last_comment`, `_submit_actions`), full read, to trace every field the restricted validator/closure path actually consumes
- `scripts/tests/test_gm_pi_analytics_action.py::test_restricted_worker_uses_minimal_private_claim_file_and_fixed_python_argv` (the exact-schema test) and `scripts/tests/fixtures/pi-analytics-actions/valid-agent-claim.json`
- Executed locally: exact cited 52-test combined subset (`test_pi_session_analytics`, `test_pi_analytics_ccore_publish`, `test_pi_analytics_deploy`, `test_hermes_config_sync_component`, `test_gm_pi_analytics_action`) — **52/52 PASS**, reproducing the claimed evidence exactly.

## New blocker verification (Codex P2 — privacy boundary, restricted claim-file projection)

**Fixed.** `_analytics_claim_projection()` now builds every nested object via an explicit `selected(value, names)` allowlist — no `"status"` key is copied anywhere in the function (root, `claim.claim`, `item`, `item.claim`, or `thread`), and `anchorType` / comment `id` / `createdBy` / `routingMetadata.agentRoute` / `routingMetadata.mentions` / the top-level `listenerInstructions` block are all likewise dropped (confirmed by direct read of lines 214-256; grepped the file for `"status"` — the only remaining hits are in unrelated registry/lifecycle code at lines 69, 78-79, 102, 500, none inside the projection function).

Cross-checked the allowlisted fields against every field `validate_claim`/`claim_parts`/`_last_comment`/`_submit_actions` actually read (`pi_analytics_action.py`): submitAction (thread + item), anchor `nodeId`/`selector`, last-comment `authorType`/`authorUserId`/`body`, `documentId`/`workspaceId`/`threadId`/`claimId` at every location the identity-consistency check inspects (root, `claim.claim`, `item`, `item.claim`, `thread`), `item.documentVersion`, `item.generatedHtmlHash`/`sourceHash`, `item.signalKey`/`evidenceSnapshotId`, and `source.generatedHtmlHash`/`sourceHash`. Every one of these is present in the projection's allowlist and nothing else is — the projection is exactly the validator/closure-consumed set, not a superset or subset.

The exact-schema test (`test_restricted_worker_uses_minimal_private_claim_file_and_fixed_python_argv`, lines 377-430) asserts this precisely: `set(value)`, `set(value["claim"])`, `set(value["item"])`, `set(value["item"]["claim"])`, `set(value["thread"])`, `set(value["thread"]["anchor"])`, `set(value["thread"]["comments"][-1])`, and `set(value["source"])` are each pinned to an exact key set, plus `assertNotIn` for `"status"`, `"textQuote"`, `"privatePrompt"`, and the injected `SENTINELS` string in the raw serialized output. The fixture used (`valid-agent-claim.json`) genuinely contains all the fields the fix needed to strip — root `status`, `item.claim.status`, `thread.anchor.anchorType`, `thread.comments[0].id`/`createdBy`, `routingMetadata.agentRoute`/`mentions`, and `listenerInstructions` — so the test is not vacuously passing; it exercises real exclusion, not absence-by-omission.

## Mode / cleanup — unchanged, still intact
`_write_claim_file()` (lines 197-211) is untouched: `os.open(..., O_EXCL, 0o600)` then atomic rename; `test_restricted_worker_uses_minimal_private_claim_file_and_fixed_python_argv` confirms `st_mode & 0o777 == 0o600`. `pi_analytics_action.main()` still unlinks the claim file in a `finally` immediately after reading it (lines 540-546), confirmed by `test_claim_file_is_removed_after_worker_reads_it`. `start_analytics_worker`'s `Popen`-failure cleanup path (unlink on exception) is unchanged.

## Valid processing still works
No test feeds the *projected* claim JSON back through `validate_claim`/`process_claim` end-to-end (the schema test mocks `subprocess.Popen`, so `pi_analytics_action.py` never actually runs against the written file). This is closed by direct code trace rather than an executed integration test: since the projection's allowlist is a strict superset of everything the validator/closure code reads (enumerated above), and `process_claim`-based tests already prove that logic succeeds when extra unread fields are present, the same logic necessarily succeeds when those extra fields are simply absent. P3, non-blocking — a nice-to-have would be one test that runs the real projected file through `process_claim`, but the current coverage plus this trace closes the gap functionally.

## Remaining P1/P2 blockers
None. The single new blocker (unnecessary `status`/anchor/comment metadata persisting in the restricted claim file) is fixed and covered by an exact-schema test with a fixture that genuinely exercises the exclusion. No regression found in auth, TOCTOU, generic-worker isolation, ledger idempotency, closure-progress persistence, or command-authority allowlisting — all unchanged from the prior clean rereview.

## Final verdict
The restricted analytics claim projection now persists exactly the validator/closure-consumed field set — no `status`, `anchorType`, comment `id`/`createdBy`, `routingMetadata.agentRoute`/`mentions`, or arbitrary passthrough fields survive — verified both by exact-schema test assertions against a fixture that actually contains those fields, and by an independent manual trace of every field the restricted worker reads. Mode (`0600`) and cleanup (unlink-after-read, unlink-on-launch-failure) remain intact. 52/52 tests reproduced locally, matching cited evidence exactly.

VERDICT: CLEAN_FOR_PR

---
CLAUDE_REVIEW_LAUNCHER_METADATA
socket=claude-review-claude-review-0e232a985bcb-1959273-ece99f0118d7
session=review
window=claude-review
model=claude-sonnet-5
effort=xhigh
transcript=/home/anichols/code/ai-configs/thoughts/validation/pre-pr-reviews/2026-07-20-main-claude-actions-final.md.transcript.txt
claude_session_id=6fa9d75d-0549-47c5-9bbf-d5f5500212ab
session_record=/home/anichols/.claude/projects/-home-anichols-code-ai-configs/6fa9d75d-0549-47c5-9bbf-d5f5500212ab.jsonl
readiness_regex=❯
clear_boundary=persisted Claude session JSONL after visible completion sentinel
history_limit=50000
capture_depth=50000
