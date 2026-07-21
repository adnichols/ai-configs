P2 — Privacy boundary — blocking

- Scope: restricted analytics claim-file projection.
- Trigger: a claim carries sensitive data in `status` fields.
- Path: `_analytics_claim_projection()` copies root, nested, and item-claim `status` values, although the validator never reads them.
- Impact: restricted claim files can retain unnecessary untrusted data, violating the required validator-only projection.
- Diff: introduced with the new projection.
- Evidence: [gm_plan_comment_listener.py](../../../_hermes/default/scripts/gm_plan_comment_listener.py#L233) and [gm_plan_comment_listener.py](../../../_hermes/default/scripts/gm_plan_comment_listener.py#L246); validator only reads registry `status`, not claim `status`.
- Fix: remove unused `status` fields (and other unused projection fields such as `anchorType`/comment `id`) and assert an exact projected schema plus sentinel exclusion in tests.
- Blocking: yes.

VERDICT: FINDINGS_TO_RESOLVE