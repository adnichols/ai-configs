## 1 Scope checked

Read-only review completed for the assigned listener/action/tests plus all supplied Good Morning snapshots. I did not rerun tests; I used the stated 47 local / 20 remote passing results.

## 2 Coverage table

| Surface | Result |
|---|---|
| Restricted routing / generic-worker escape | Pass: analytics-prefixed anchors take fixed Python worker; non-analytics Agent work retains generic path. |
| Author, workspace, card, hash, registry validation | Pass: fail-closed checks are present and fixture coverage is broad. |
| Command execution authority | Pass: only `doct-agent documents get` and plan reply/ack/resolve/release commands are reachable; no shell or Hermes path. |
| D4 display / capped cards / Private C-Core / nonfatal reads | Pass in supplied remote snapshots. |
| Ledger retry / Doct closure idempotency | Finding 1. |
| Claim-file privacy persistence | Finding 2. |

## 3 Findings

1. **P2 — IN_PLAN — Gate-blocking: yes.** Partial Doct-close failure duplicates the visible reply on retry.

   - Trigger: `plans reply` succeeds, then `plans ack` or `plans resolve` fails.
   - Reachable path: [`process_claim`](../../../_hermes/default/scripts/pi_analytics_action.py#L452) records the ledger first; [`finish_claim`](../../../_hermes/default/scripts/pi_analytics_action.py#L386) posts a reply before ack/resolve; failure releases the claim, and redelivery enters `finish_claim` again.
   - Impact: the display decision is idempotent, but the exact claimed action produces duplicate “Recorded Pi analytics disposition” comments. This contradicts the intended duplicate/crash-retry handling.
   - Diff relationship: introduced by the new restricted action worker.
   - Evidence: the retry test only models failure of the initial reply; it does not model reply-success/ack-failure or reply-success/resolve-failure ([test](../../../scripts/tests/test_gm_pi_analytics_action.py#L215)).
   - Smallest fix: persist closure progress for the delivery (or use a Doct-supported idempotency key), then retry only unfinished close steps. Add both partial-close retry cases.

2. **P2 — IN_PLAN — Gate-blocking: yes.** The restricted path persists the full, untrusted claim payload in a long-lived, normally world-readable state file.

   - Trigger: a routed analytics claim includes private or sensitive fields outside the worker’s required identity fields.
   - Reachable path: [`start_analytics_worker`](../../../_hermes/default/scripts/gm_plan_comment_listener.py#L206) serializes the complete payload through [`_write_claim_file`](../../../_hermes/default/scripts/gm_plan_comment_listener.py#L197); `write_text` creates the final JSON using the process umask, and neither the claim nor its parent directory is restricted or cleaned up.
   - Impact: claim context can persist under `~/.hermes/state/.../runs` after completion, outside the ledger/privacy assertions. This is a privacy leak path for a feature explicitly constrained to aggregate-only information.
   - Diff relationship: newly introduced for restricted analytics dispatch (and the helper now also changes the generic path).
   - Evidence: the privacy test proves only ledger and outgoing Doct argv content, not the listener-created claim JSON ([test](../../../scripts/tests/test_gm_pi_analytics_action.py#L251)). The fixture’s injected `privatePrompt` would be written verbatim by the listener.
   - Smallest fix: write only a minimal required claim projection with mode `0600`, remove it after the worker reads it/completes, and add a listener-level sentinel test covering the persisted file and permissions.

## 4 Remaining checks if incomplete

None.

## 5 Final verdict

The authorization boundary, registry parity checks, D4 behavior, capped cards, Private-space enforcement, and fixed-argv restriction are sound in the reviewed surfaces. Resolve the two retry/privacy gaps before PR.

VERDICT: FINDINGS_TO_RESOLVE