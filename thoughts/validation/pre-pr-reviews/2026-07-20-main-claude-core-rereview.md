Scope checked

  _hermes/default/scripts/pi_analytics_collector.py, scripts/tests/test_pi_analytics_ccore_publish.py, scripts/tests/test_pi_analytics_deploy.py, scripts/hermes_config_sync.py (component-merge surface only),
  scripts/tests/test_hermes_config_sync_component.py, _hermes/default/manifest.json. Read-only: no files edited.

  Verification of the three named fixes

  1. Cursor pagination — complete. list_title_matches (pi_analytics_collector.py:334-351) now loops ccore doc list --cursor <n> until next_cursor is null, accumulating title matches across all pages, with a seen_cursors
  guard that raises PublishFailure on a repeating cursor instead of looping forever. reconcile_existing consumes the full accumulated match list, so a same-title document beyond the first 500 is now found before
  publish_report would create a duplicate. Directly tested: test_existing_report_on_later_page_is_reused_without_create (test_pi_analytics_ccore_publish.py:83-100) mocks a two-page response (next_cursor: 500 then null)
  with the match on page 2, and asserts exactly 3 calls, --cursor 0 then --cursor 500, then a doc show (reuse, no create). Passes.

  2. Invalid-config stale-status replacement — complete. _run_collection_locked (pi_analytics_collector.py:446-462) now wraps load_config in try/except; on CollectorError it atomically writes a publish_failed status
  (with started_at/finished_at stamped and an explanatory message) before returning, rather than exiting silently. This still runs inside collector_lock, so serialization is preserved. Directly tested:
  test_invalid_config_replaces_stale_success_status (test_pi_analytics_deploy.py:143-162) seeds a real succeeded status file, corrupts the config, calls the real (unmocked) run_collection, and asserts the status flips to
  publish_failed with a fresh started_at. Passes.

  3. Obsolete source-field convergence — complete, consistent with documented runtime preservation. merge_component_job (hermes_config_sync.py:696-720) now builds replacement fresh from dict(incoming_job) (mirroring the
  pre-existing merge_cron_jobs pattern) and only re-injects fields in COMPONENT_CRON_RUNTIME_FIELDS when present on current — a field dropped from source no longer survives. That runtime-field set is the single source of
  truth used symmetrically by verify_component's _job_source_fields (hermes_config_sync.py:766-771) for drift comparison, so merge and verify agree on what's "runtime" vs. "source-owned." Directly tested:
  test_component_install_is_additive_and_preserves_unrelated_jobs_and_runtime (test_hermes_config_sync_component.py:134-181) seeds a destination job with obsolete_source_field (absent from the current source source_job()
  fixture) plus real runtime state (enabled=False, state=paused, last_status=ok, repeat.completed=41), installs, and asserts the obsolete field is gone while all runtime fields and unrelated jobs/top-level runtime keys
  survive. Passes.

  No-regression checks

  - Scoped suite (test_pi_analytics_ccore_publish, test_pi_analytics_deploy, test_hermes_config_sync_component): 25/25 pass.
  - Full local suite (python3 -m unittest discover scripts/tests): 99/99 pass, no failures/errors.
  - hermes_config_sync.py verify --bundle _hermes/default --hermes-home _hermes/default: VERIFY OK: 1701 files.
  - verify_component for pi-analytics-collector: COMPONENT VERIFY OK: 1 file(s), 1 cron job(s).
  - Recomputed manifest.json from bundle source matches the checked-in file exactly (1701/1701 files, identical path/sha256 set) — no manifest drift.
  - merge_cron_jobs (full-install path) and install_all/verify dispatch are structurally unchanged apart from the additive --component/refresh-manifest branches in main(); the default (no --component) install/verify
  behavior is untouched, matching the disposition that full-bundle install remains intentionally mbp-scoped.

  Dispositioned items (not re-raised)

  - Full _hermes/default install deploying the collector unconditionally: per disposition, intended (mbp-only bundle includes mbp's collector); dever uses --component. Confirmed the code still supports both paths as
  described.
  - Hardcoded created_at on first component install: confirmed present (_hermes/default/cron/jobs.json:334) and non-blocking per disposition; also confirmed it self-corrects after first install since created_at is in
  COMPONENT_CRON_RUNTIME_FIELDS and gets preserved from current on every subsequent merge.

  Remaining checks

  None — all three named fix areas were read at the diff level and exercised via the existing targeted tests plus a live re-run of the full suite and both verify commands.

  Findings

  None. No P1/P2 blockers found in the reviewed files.

  VERDICT: CLEAN_FOR_PR
