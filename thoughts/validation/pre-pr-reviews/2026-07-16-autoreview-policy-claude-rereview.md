# Bounded fix review — hermes_config_sync cron install

Scope: only the fix for the prior scheduler-state data-loss regression. No architecture/export-redesign commentary.

## Contract trace (each requirement mapped to code)

| Requirement | Location | Result |
|---|---|---|
| Preserve runtime fields (enabled/state/pause/next/last/status/errors/fire_claim/run_claim) | `merge_cron_jobs` loop over `CRON_RUNTIME_FIELDS` (scripts/hermes_config_sync.py:462-464) | OK — all 11 fields listed |
| Preserve `repeat.completed`, take `repeat.times` from source | `merge_cron_jobs` (scripts/hermes_config_sync.py:466-471) | OK — starts from incoming repeat, overlays only `completed` |
| Update incoming def fields (prompt/schedule/model/provider/snapshots/toolsets/workdir/deliver) | Incoming is the base (`job = dict(incoming_job)`), runtime overlay is narrow (scripts/hermes_config_sync.py:459-460) | OK |
| Preserve top-level `updated_at` | scripts/hermes_config_sync.py:475-476 | OK |
| New incoming jobs unchanged | Iteration includes new incoming jobs, only overlays when existing match found | OK |
| Drop live jobs absent from source | `merge_jobs` iterates only `incoming["jobs"]` — orphans not carried forward (scripts/hermes_config_sync.py:458) | OK (matches contract) |
| Top-level and profile cron use same helper | `install_all` calls `install_cron_jobs` for both (scripts/hermes_config_sync.py:546, 567) | OK |
| Backup + merge + atomic replace under `<cron-dir>/.jobs.lock` | `install_cron_jobs` opens `.jobs.lock`, LOCK_EX, then backup → load-existing → merge → `atomic_write_json` all inside `with` (scripts/hermes_config_sync.py:508-522) | OK |
| Atomic write | `tempfile.mkstemp` sibling, `fsync` file + parent dir, `os.replace` (scripts/hermes_config_sync.py:480-498) | OK |

## Findings

No P1/P2 defects for this fix. Notes below are advisory only; the review requested strictly current-path P1/P2 risks and none rise to that bar.

### Non-blocking observations

**N1. `created_at` is not in `CRON_RUNTIME_FIELDS` (scripts/hermes_config_sync.py:129-132).**
Trigger: install after Hermes wrote a `created_at` value not present in source. Path: incoming becomes the base; if source lacks `created_at`, live loses it; if source has one, live is overwritten by source's value. Impact: negligible — `created_at` is immutable per-job; export copies the same value back, so source and live agree in normal use. Only exposure is manual editing of the source. Not a P1/P2. Diff relationship: pre-existing field-set choice, not caused by this fix.

**N2. Backup destination stamp differs between top-level and profile install calls (scripts/hermes_config_sync.py:412 via `now_stamp()` when `HERMES_AI_CONFIGS_INSTALL_STAMP` is unset).**
Trigger: single `install --apply` writing top-level and profile jobs.json each generates its own `ai-configs-install-<stamp>` directory. Impact: rollback needs two paths, not one. Diff relationship: `HERMES_AI_CONFIGS_INSTALL_STAMP` support already exists — install just doesn't set it. Not blocking; the final "Backups written:" section prints every path.

**N3. `.jobs.lock` sentinel file is created (`a+`) and never removed (scripts/hermes_config_sync.py:509).**
Residual empty file per cron dir. Harmless; lock is held via fd, not path. Not blocking.

**N4. Merge preserves only `repeat.completed`; other runtime keys inside `repeat` would be lost (scripts/hermes_config_sync.py:466-471).**
Current live jobs.json only shows `times` and `completed` inside `repeat`, so no observed data loss. If Hermes ever adds another mutable field there, it would silently be dropped. Not a current-path defect.

**N5. Test wiring runs unit tests via `python3 -m unittest scripts/test_hermes_config_sync.py` (test_install_shared_skills.sh:1369).**
Assumes CWD is repo root. Since the suite is invoked from repo root (25/25 passing per user evidence), this works. Minor coupling but not a defect.

### Explicitly verified negatives

- No orphan-preservation ambiguity: contract asks orphans to be removed, and `merge_cron_jobs` does so by iterating only `incoming["jobs"]`.
- No TOCTOU on `dst.exists()`/`dst.stat()`: both run inside the exclusive `flock`; scheduler is expected to honor the same lock (verified by user's pre/post live-apply counter assertion).
- No temp-file leak on the happy path: `os.replace` renames the temp; `finally` `unlink` becomes a no-op on the (now non-existent) temp path. On mid-flight failure the temp is cleaned up.
- No mode drift: `stat.S_IMODE(dst.stat().st_mode)` captured under lock, applied via `os.chmod` before `os.replace`.
- Dry-run path never opens the lock or writes (scripts/hermes_config_sync.py:503-504). No side effects.
- No secret exposure: cron path never uses the redaction/merge_skip_redacted code path; it is a plain JSON round-trip.

### Test adequacy vs prior failure

The regression was "installation reset jobs.json to source, wiping fire_claim/run_claim/next_run_at/last_*, `repeat.completed`, and `updated_at`." The new unit test in scripts/test_hermes_config_sync.py:16-168 asserts each of those survives at both top-level and per-profile scope, that source-side definition fields do overwrite live, that new jobs are unchanged, that orphans are removed, that `.jobs.lock` is created, and that install_cron_jobs is called for each cron path. This is a direct, adequate regression guard for the prior failure mode.

## Verdict

CLEAN_FOR_PR

---
CLAUDE_REVIEW_LAUNCHER_METADATA
socket=claude-review-claude-review-384676caef08-62091-6daeca02e53f
session=review
window=claude-review
model=claude-opus-4-7
effort=xhigh
transcript=/Users/anichols/.codex/worktrees/cbb7/ai-configs/thoughts/validation/pre-pr-reviews/2026-07-16-autoreview-policy-claude-rereview.md.transcript.txt
claude_session_id=546dc709-d3fc-43ef-bd47-4373690d32b6
session_record=/Users/anichols/.claude/projects/-Users-anichols--codex-worktrees-cbb7-ai-configs/546dc709-d3fc-43ef-bd47-4373690d32b6.jsonl
readiness_regex=❯
clear_boundary=persisted Claude session JSONL after visible completion sentinel
history_limit=50000
capture_depth=50000
