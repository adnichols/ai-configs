## Scope checked
`scripts/pi_session_analytics.py`, `docs/pi-session-analytics-report-schema-v1.md`, `scripts/tests/test_pi_session_analytics.py` + fixtures + `thoughts/retro/pi-session-analytics-sanitized-baseline-v1.json`, `_hermes/default/scripts/pi_analytics_collector.py`, `scripts/tests/test_pi_analytics_ccore_publish.py`, `scripts/tests/test_pi_analytics_deploy.py`, `scripts/hermes_config_sync.py`, `scripts/tests/test_hermes_config_sync_component.py`, `_hermes/default/components/pi-analytics-collector.json`, `_hermes/default/cron/jobs.json`, `_hermes/default/manifest.json`. All changes are uncommitted/untracked local work on top of `origin/main` (HEAD == origin/main). `pi_analytics_action.py`, `gm_plan_comment_listener.py`, and their tests were intentionally excluded (slice 2/actions).

## Coverage table

| Area | Checked | Method |
|---|---|---|
| Privacy-safe explicit-root aggregation | Yes | Read analyzer, traced allowlist fields, verified error-path never leaks paths (OSError.strerror always populated) |
| Completed-day determinism | Yes | Read `reporting_window`/`completed_day`, ran unit tests incl. DST cases |
| Host-local serialization/locking | Yes | Read `fcntl.flock` usage, ran the concurrency unit test |
| Immutable canonical C-Core reports | Yes | Read `publish_report`/`reconcile_existing`, ran ccore-publish tests |
| Truthful statuses | Partial | Found fabricated `created_at`; `next_run_at:null` anomaly noted but not independently verifiable (Hermes scheduler internals are outside this repo) |
| Component merge/verify/export parity | Yes | Read + reproduced `merge_component_job` vs `merge_cron_jobs`; ran component test suite |
| Additive collector-only install | Yes | Reproduced full `install --apply` against a scratch home |
| Test suite | Yes | `python3 -m unittest` on all 4 in-scope test modules — 35/35 pass |
| Bundle verify | Yes | `hermes_config_sync.py verify` — 1701 files OK |

## Findings

**1. [P1] [deploy/cron-scope] Ordinary full `install --apply` silently deploys the pi-analytics-collector job and script to every host, bypassing the new component-scoped mechanism.**
- Trigger/path: any operator (or the tool's own generated `README.md` instructions) running the pre-existing, default `python scripts/hermes_config_sync.py install --apply` (no `--component` flag).
- Impact: `_hermes/default/cron/jobs.json` now contains job `a91c0d7e4b22` unconditionally, and `scripts/` is one of `TOP_LEVEL_DIRS` (`hermes_config_sync.py:64`), so `install_all`/`install_dir`/`install_cron_jobs` (`hermes_config_sync.py:536,407,512`) copy `pi_analytics_collector.py` and merge the cron job into **any** host's `cron/jobs.json`, activated (`enabled:true`, `state:"scheduled"`) with no opt-in. This directly contradicts the stated goal "additive collector-only install preserving unrelated state," and defeats the purpose of building the new `--component` mechanism (whose own tests only assert the *component* path is additive/scoped — they never assert the *full* path is not).
- Diff relationship: caused by the combination of two new-in-diff facts — the job entry added straight into the shared `cron/jobs.json` (`_hermes/default/cron/jobs.json:319-357`) and the collector script placed under `scripts/`, which the pre-existing full-sync path already walks unmodified.
- Evidence: reproduced live — `install --apply --hermes-home /tmp/scratch --bundle _hermes/default` (no `--component`) deployed `pi_analytics_collector.py`, `pi_analytics_action.py`, and job id `a91c0d7e4b22` (`enabled:true`) into the scratch home. No existing or new test asserts the opposite.
- Consequence if uncorrected: hosts never intended to run this collector get a daily 5am cron entry; it fails at runtime only if `~/.hermes/config/pi-analytics-collector.json` is absent (clean `CollectorError`, no crash, no privacy leak), but the job is left permanently "scheduled" and failing daily on hosts an operator never opted in.
- Smallest fix: exclude component-owned cron job ids/files (as declared in `components/*.json`) from the plain `install_cron_jobs`/`install_dir` full-sync paths, so only `--component pi-analytics-collector install` can activate them — or explicitly document/confirm this is intended and adjust the plan's stated goal.
- Blocking: **Yes** — directly contradicts the change's own stated goal and is unverified by any test.

**2. [P2] [config-sync/merge-parity] `merge_component_job` can never converge if a source cron-job field is later removed — unlike the full-install merge path.**
- Trigger/path: a future edit to the checked-in job definition (`a91c0d7e4b22` in `_hermes/default/cron/jobs.json`) that drops a field, followed by re-running `install --component pi-analytics-collector install --apply` on a host that already has the job installed.
- Impact: `merge_component_job` (`hermes_config_sync.py:696-720`) builds `replacement = {**current, **incoming_job}`, so any field present on the host's copy but absent from the new source is never deleted — it survives indefinitely across repeated installs. The equivalent full-bundle path, `merge_cron_jobs` (`hermes_config_sync.py:464-488`), instead rebuilds each job from `incoming_job` and only re-injects the small preserved-runtime-field set, correctly dropping obsolete fields.
- Diff relationship: `merge_component_job` is new code in this diff; `merge_cron_jobs` is pre-existing and unchanged.
- Evidence: reproduced directly — feeding `merge_component_job({"jobs":[{"id":"job1","skill":"obsolete"}]}, {"id":"job1","name":"new"})` retains `"skill":"obsolete"` after one merge and again after a second merge (never converges), while the equivalent `merge_cron_jobs` call correctly drops it.
- Consequence: once triggered, `verify_component` (`hermes_config_sync.py:774-805`) would report permanent "component cron job drift" with no install-driven remediation, undermining the "truthful statuses"/verify-parity goal for future component updates.
- Smallest fix: in `merge_component_job`, start `replacement` from `dict(incoming_job)` (like `merge_cron_jobs`) and only re-inject `COMPONENT_CRON_RUNTIME_FIELDS` present on `current`, instead of starting from `current`.
- Blocking: No — not triggered by this diff (only an addition, no field removal yet), but it's new code shipping with an unaddressed correctness gap and no test covers field-removal drift.

**3. [P3] [deploy/status-truthfulness] Every host's first-time component install stamps a fabricated, non-representative `created_at`.**
- Trigger/path: first-time `install --component pi-analytics-collector install --apply` on any host, at any future date.
- Impact: the source job in `_hermes/default/cron/jobs.json:347` hardcodes `"created_at": "2026-07-20T05:00:00-06:00"` (the authoring date). `install_component_jobs`/`merge_component_job` only preserve `current`'s `created_at` when a job already exists (`hermes_config_sync.py:707-709`); for a fresh install there is no `current`, so every host that installs this component — whether tomorrow or a year from now — gets the identical, backdated `created_at` verbatim, misrepresenting when the job was actually created on that host.
- Diff relationship: new behavior introduced by the component job's source definition plus `merge_component_job`'s first-install branch.
- Evidence: confirmed by code inspection of the install-time branch (`hermes_config_sync.py:717-718`, `jobs.append(replacement)` with no timestamp substitution) and the literal value in the diff.
- Smallest fix: omit `created_at` from the source job (or set it `null`) and have `install_component_jobs` stamp the real install-time UTC timestamp when no `current` entry exists, mirroring how `started_at`/`finished_at` are stamped live in the collector itself.
- Blocking: No — cosmetic/audit-metadata only, does not affect scheduling or privacy behavior.

## Remaining checks (if pursued further)
- Confirm with Hermes runtime/scheduler documentation (outside this repo) whether a freshly-added job with `next_run_at: null` (the new job, `_hermes/default/cron/jobs.json:348`) is safely backfilled by the scheduler, since it's the only `state:"scheduled"` job in the file with `next_run_at: null` — every other existing job has a concrete value.

## Final verdict
One P1 finding (full-install/component-scope contradiction) is concretely reproduced, untested, and directly undermines the change's own stated non-goal boundary ("additive collector-only install preserving unrelated state"). This should be resolved or explicitly re-scoped before merge.

VERDICT: FINDINGS_TO_RESOLVE

---
CLAUDE_REVIEW_LAUNCHER_METADATA
socket=claude-review-claude-review-2f9823c011e4-1820094-77dc99540c71
session=review
window=claude-review
model=claude-sonnet-5
effort=xhigh
transcript=/home/anichols/code/ai-configs/thoughts/validation/pre-pr-reviews/2026-07-20-main-claude-core.md.transcript.txt
claude_session_id=eeacc870-d93d-42f2-9c26-e39bbd397098
session_record=/home/anichols/.claude/projects/-home-anichols-code-ai-configs/eeacc870-d93d-42f2-9c26-e39bbd397098.jsonl
readiness_regex=❯
clear_boundary=persisted Claude session JSONL after visible completion sentinel
history_limit=50000
capture_depth=50000
