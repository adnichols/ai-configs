## 1 Scope checked

Reviewed all assigned analyzer, collector, C-Core publication, component-sync, cron/manifest, schema, and test surfaces. Static review only; no files changed or nested review launched.

## 2 Coverage table

| Area | Result |
|---|---|
| Aggregate-only analyzer and schema | Checked allowlist, canonical output, window/DST behavior, symlink containment, fixtures/baseline |
| C-Core create/reconcile | P2 finding: bounded list can miss an existing title |
| Host serialization | `flock` serializes collector runs per status directory |
| Status truthfulness | P2 finding: configuration failures leave stale success status |
| Component deployment/parity | Checked manifest allowlist, source validation, additive job merge, unrelated-job preservation |
| Tests | Existing tests cover nominal reconcile/status cases but miss both findings below |

## 3 Findings

1. **P2 — IN_PLAN — Gate-blocking: yes.** C-Core reconciliation only examines the first 500 documents, so it can create a duplicate report instead of detecting/reusing the immutable same-title report.

   - Trigger / reachable path: `Private` contains more than 500 documents and the existing `pi-analytics/v1/<host>/<date>` document is not returned by `ccore doc list Private --limit 500`.
   - Impact: `reconcile_existing()` returns no match and `publish_report()` creates another document with the same title, violating the “exactly one report per host/day” and conflict/reuse contract.
   - Diff relationship: introduced by the new collector publication path.
   - Evidence: [pi_analytics_collector.py](/home/anichols/code/ai-configs/_hermes/default/scripts/pi_analytics_collector.py:321) hard-caps the list to 500; [reconcile_existing](/home/anichols/code/ai-configs/_hermes/default/scripts/pi_analytics_collector.py:348) treats that partial result as exhaustive. The supported CLI exposes pagination via `--cursor`; [tests](/home/anichols/code/ai-configs/scripts/tests/test_pi_analytics_ccore_publish.py:56) only model a single-page list.
   - Smallest fix: paginate `ccore doc list` through all cursors (within the existing deadline) and collect all exact-title matches before deciding absent/unique/conflicting; add a second-page existing-title test.

2. **P2 — IN_PLAN — Gate-blocking: yes.** A malformed or unreadable collector configuration exits as `publish_failed` without updating `last-run.json`, leaving `--status --json` to report an earlier success.

   - Trigger / reachable path: after any successful collection, make `~/.hermes/config/pi-analytics-collector.json` invalid, missing, or unreadable; the next scheduled run calls `load_config()` before it creates `base_status`.
   - Impact: the documented recovery command reports stale `state: succeeded` rather than the failed run, undermining the required truthful status behavior.
   - Diff relationship: introduced by the new collector status implementation.
   - Evidence: [collector](/home/anichols/code/ai-configs/_hermes/default/scripts/pi_analytics_collector.py:421) loads config before any status write; the only top-level handling at [main](/home/anichols/code/ai-configs/_hermes/default/scripts/pi_analytics_collector.py:496) prints an error and returns. Existing tests cover failures only after a mocked successful config load at [test_pi_analytics_deploy.py](/home/anichols/code/ai-configs/scripts/tests/test_pi_analytics_deploy.py:143).
   - Smallest fix: catch config-load failures inside the collection lifecycle and atomically record `publish_failed` (using safely derivable date/nullable host fields if necessary), then add a test beginning with an old success status and asserting it is replaced.

## 4 Remaining checks if incomplete

None; assigned static review is complete.

## 5 Final verdict

Two in-plan correctness/status defects need resolution before PR.

VERDICT: FINDINGS_TO_RESOLVE