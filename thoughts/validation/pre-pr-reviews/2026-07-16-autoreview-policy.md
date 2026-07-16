# Autoreview Behavioral Policy — Pre-PR Review

- Plan: `thoughts/plans/autoreview-behavioral-review-policy.html`
- Branch: `autoreview-policy`
- Base: `origin/main`
- Base freshness at review: `HEAD == origin/main` before the scoped commit; fetch/rebase remains required immediately before push.
- Review surface: Codex and Claude Code (required because the in-scope Hermes synchronization fix touches scheduler persistence and file locking).

## Scope baseline

Implement the reviewed plan's canonical `autoreview` skill, indefinite compatibility alias, maintained caller/documentation migration, installation synchronization, and verification. Preserve existing review severities, scope labels, reviewer transports, bounded convergence, durable artifacts, and `OPEN_PR_READY`. Do not add reviewer engines or broaden the public/runtime contract.

The initial implementation changed the canonical and alias skills, maintained Codex/Pi/Hermes callers, install metadata, documentation, tests, and managed Hermes source. During required synchronization, the initial Codex review found that the existing Hermes installer copied cron definitions wholesale and reset runtime-owned scheduler state. The accepted in-scope prerequisite was a narrow merge-under-lock fix plus regression coverage and restoration of affected live state.

## Review cycles and triage

| Cycle | Reviewer | Verdict | Triage |
|---|---|---|---|
| Initial | Codex | `FIX_IN_SCOPE_FINDINGS` | P2 `REGRESSION_FROM_THIS_DIFF`: managed cron apply reset runtime counters, timestamps, claims, and scheduler state. Accepted and fixed at the existing Hermes installer ownership boundary. |
| Targeted rereview | Codex | `CLEAN_FOR_PR` | No unresolved P1/P2 or required P3 findings. |
| Targeted rereview | Claude Code | `CLEAN_FOR_PR` | Required high-risk persistence/locking review found no P1/P2 defects; five advisory observations were explicitly non-blocking. |

Initial Codex artifact: `thoughts/validation/pre-pr-reviews/2026-07-16-autoreview-policy-codex.md`

Targeted artifacts:

- `thoughts/validation/pre-pr-reviews/2026-07-16-autoreview-policy-codex-rereview.md`
- `thoughts/validation/pre-pr-reviews/2026-07-16-autoreview-policy-claude-rereview.md`

## Fix and verification

The Hermes installer now validates cron files, merges source-owned job definitions with live runtime-owned fields, preserves `repeat.completed` and top-level `updated_at`, removes jobs absent from source, writes atomically, and performs backup/merge/replace under each cron directory's `.jobs.lock`. The same helper covers top-level and profile cron files. A regression test exercises divergent source/live state and would fail under the prior whole-file copy.

Affected live scheduler counters and claims were restored from the pre-apply backups. A subsequent live apply preserved them while installing the canonical prompt.

Final verification after the last fix:

```text
bash test_install_shared_skills.sh                                      PASS (25/25)
node --test _pi/extensions/claude-review/tests/source-policy.test.mjs   PASS (5/5)
python3 -m unittest scripts/test_hermes_config_sync.py                  PASS
python3 -m py_compile scripts/hermes_config_sync.py scripts/test_hermes_config_sync.py  PASS
python3 scripts/hermes_config_sync.py verify                            PASS (1686 files)
git diff --check                                                        PASS
```

## PM review

Implementation-stage PM review is clean. The canonical command is now obvious, compatibility is automatic, maintained callers agree, the behavioral policy adds only the seven reviewed constraints, and review-triggered remediation stayed within the existing Hermes installer boundary. No promised slice is stubbed or deferred, and no product decision remains.

## Final gate

- Codex verdict: `CLEAN_FOR_PR`
- Claude Code verdict: `CLEAN_FOR_PR`
- Unresolved blocking in-scope P1/P2 findings: none
- Blocking P3 findings: none
- Non-blocking follow-ups: none required; Claude Code advisory notes describe optional future hardening only.
- Result: `OPEN_PR_READY`

No Codex PR thumbs-up or external approval is required after this clean local review-agent consensus. The `run-plan` caller must complete base freshness, commit, push, PR creation, current PR feedback inspection, and local merge-readiness confirmation.
