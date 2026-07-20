Scope: backup_path() (scripts/hermes_config_sync.py:421-428) and its component-install callers, plus the regression test test_component_backups_stay_under_explicit_nondefault_home
  (scripts/tests/test_hermes_config_sync_component.py:184-201).

  Resolved-home threading
  - main() resolves --hermes-home once (Path(args.hermes_home).expanduser().resolve(), line ~825) before dispatch.
  - Both component call sites pass it through: install_component_jobs → backup_path(dst, hermes_home) (line 740) and install_component → backup_path(destination, hermes_home) (line 762). backup_path computes home =
  (hermes_home or DEFAULT_HERMES_HOME).expanduser().resolve(), so file and cron-job backups both root under the actual resolved CLI home, not the module-level DEFAULT_HERMES_HOME.

  Regression test
  - test_component_backups_stay_under_explicit_nondefault_home deliberately does not patch DEFAULT_HERMES_HOME (unlike an earlier test in the same file that does), so it exercises the real fallback path. It installs to
  root/explicit-home, then asserts both the file backup (scripts/pi_analytics_collector.py) and the cron backup (cron/jobs.json) land under explicit-home/backups/ai-configs-install-fixture-stamp/..., and explicitly
  asserts the backup dir is absent under DEFAULT_HERMES_HOME. This is a correct, targeted regression guard against the exact class of bug (silently reverting to the default home) that would otherwise be easy to
  reintroduce.

  Path containment
  - load_component() rejects any component-manifest file entry that is absolute or contains .. in its parts (line 673-674) before any path is used, so destination = hermes_home / rel in install_component can't escape the
  resolved home.
  - backup_path() additionally resolves both home and dst and uses relative_to() inside a try/except ValueError, falling back to the bare filename rather than propagating an out-of-tree relative path — safe either way.

  Default (non-component) behavior unchanged
  - Diffed against HEAD: backup_path(dst) call sites in install_file, install_dir, install_config, install_cron_jobs (lines 400, 413, 444, 528) are byte-identical in call shape to before this change (still single-arg).
  The pre-existing behavior of those call sites (using DEFAULT_HERMES_HOME for backup rooting regardless of --hermes-home) predates this diff (confirmed via git show HEAD:...) and is out of scope for "one new blocker
  only" — it is not a regression introduced here, and the new component path deliberately fixes/avoids it rather than inheriting it.

  Test/verify run
  - python3 -m unittest discover -s scripts/tests: 100 tests, all OK (superset including unrelated pi-vcc suites).
  - Targeted PR-relevant files (test_hermes_config_sync_component, test_gm_pi_analytics_action, test_pi_analytics_ccore_publish, test_pi_analytics_deploy, test_pi_session_analytics): 49 passing, 0 failures (count differs
  slightly from the reported 52, likely due to suite selection/tooling — no failures or errors either way).
  - python3 scripts/hermes_config_sync.py verify: VERIFY OK: 1701 files, no obvious secret patterns.

  Minor non-blocking observation: there's no dedicated unit test asserting load_component rejects a component manifest whose files entries contain .. or an absolute path — the guard exists and is correct by inspection,
  but is untested in isolation. Not a P1/P2 and outside the stated single-blocker scope; worth a follow-up test, not a PR blocker.

  No P1/P2 blocker found in the inspected area.

  VERDICT: CLEAN_FOR_PR

---
CLAUDE_REVIEW_LAUNCHER_METADATA
socket=claude-review-claude-review-9b60bc691494-1959272-44b7e802299e
session=review
window=claude-review
model=claude-sonnet-5
effort=xhigh
transcript=/home/anichols/code/ai-configs/thoughts/validation/pre-pr-reviews/2026-07-20-main-claude-core-final.md.transcript.txt
claude_session_id=afe8ea92-dcb7-4ac7-8546-5de1b5df8287
session_record=/home/anichols/.claude/projects/-home-anichols-code-ai-configs/afe8ea92-dcb7-4ac7-8546-5de1b5df8287.jsonl
readiness_regex=❯
clear_boundary=baseline-relative marker/sentinel occurrence diff after submit
history_limit=50000
capture_depth=50000
