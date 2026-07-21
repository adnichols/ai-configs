1. Resolved: rejected claims are mutation-free unless their document maps to exactly one active `good_morning` registry entry and its workspace matches. [`reject_claim`](../../_hermes/default/scripts/pi_analytics_action.py#L405) rechecks both before any Doct command; the local test asserts no plan actions for wrong document/workspace.

2. **IN_PLAN**: the reader is not fully fail-closed for every configured value not exactly `Private`. An explicit empty or non-string `ccore_space` is silently replaced with the `Private` default, then invokes C-Core (reader snapshot, `pi_analytics_phase.py:158`). The new test covers `"Other"` but not these values. Treat any present invalid/non-`Private` setting as incomplete without invoking C-Core.

The restricted-action and nonfatal incomplete-data paths otherwise remain intact.

VERDICT: FIX_IN_SCOPE_FINDINGS