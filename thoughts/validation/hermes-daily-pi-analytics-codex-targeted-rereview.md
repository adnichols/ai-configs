- `READINESS_BLOCKER` — P2’s source/install synchronization is sequenced incompatibly with the current sync tool. Its first component dry-run must validate against `_hermes/default/manifest.json`, but P2 adds a script and changes `cron/jobs.json` without requiring the full manifest to be regenerated before that dry-run. The current installer verifies the manifest before installing. Further, its generic “install apply → export” instruction is unsafe after a dever component install: a full export from dever can replace the full default bundle with that host’s partial gateway state. Define the pre-dry-run manifest update and a component-safe post-install verification/export path. Evidence: plan P2 and verification [lines 60–68, 78](../plans/hermes-daily-pi-analytics-morning-review.html#L60); current pre-install verification [hermes_config_sync.py](../../scripts/hermes_config_sync.py#L620).

Completed checks:

- Prior finding 1 resolved: component-only merge, negative dry-run assertions, and mbp singleton ownership are explicit and tested.
- Prior finding 2 resolved: v1 makes no C-Core deletion or retention-success claim.
- Prior finding 3 resolved: ingress is routed-Agent-only, intercepted before generic dispatch, with fixed-argv restricted handling and negative tests.
- Prior finding 4 resolved: identity, idempotency, seven-day behavior, and dismissal reset semantics are deterministic.
- Prior finding 5 resolved: exact JSON paths and token/category mapping prevent transcript scraping and error-message output.
- Recovery/readback and `Private` space evidence are consistent with the requested fixes.

VERDICT: PLAN_NEEDS_REVISION