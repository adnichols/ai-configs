# GM deterministic runtime comparison — 2026-06-29

## When to use

Use this reference when Aaron asks whether the deterministic `/gm` runner is faster or more reliable than the previous LLM-agent cron flow, or when tuning runtime budgets for the Good Morning workflow.

## Evidence sources used

- Hermes cron scheduler logs for job `039f96dcecfc` (`Daily Good Morning HTML Plan + Todoist Review`).
- Cron output files under `~/.hermes/cron/output/039f96dcecfc/`.
- Deterministic run manifests under `adn_vault/DailyGM/runs/YYYY-MM-DD/manifest.json`.
- The 2026-06-29 reliability investigation session, which verified the script-only cron path after raising `cron.script_timeout_seconds`.

## Old LLM-agent cron runtime

Successful pre-deterministic runs:

| Date | Status | Runtime |
|---|---:|---:|
| 2026-06-22 | ok | 420.2s / 7m00s |
| 2026-06-23 | ok | 634.0s / 10m34s |
| 2026-06-24 | ok | 489.3s / 8m09s |
| 2026-06-25 | ok | 405.7s / 6m46s |
| 2026-06-26 | ok | 903.6s / 15m04s |

Summary for successful old runs:
- Average: ~570.6s / 9m31s
- Median: ~489.3s / 8m09s
- Range: ~405.7s–903.6s / 6m46s–15m04s

Failed old runs after context growth / LLM stall issues:
- 2026-06-27: failed after ~1274.0s / 21m14s with cron inactivity timeout.
- 2026-06-28 morning: failed after ~1171.1s / 19m31s with cron inactivity timeout.

## Deterministic runner runtime

Manifest phase sums:

| Date | Status | Phase sum | Notes |
|---|---:|---:|---|
| 2026-06-28 | ok | ~43.6s | Published successfully after deterministic conversion. |
| 2026-06-29 | ok | ~56.8s | Published successfully after script-timeout fix. |

Observed wrapper / cron end-to-end checks:
- Local exact wrapper run on 2026-06-29: ~71s.
- Real Hermes cron triggers on 2026-06-29: ~74–98s observed around completion/delivery.

Current long poles from manifests:
- `plan_review_audit`: ~26–36s.
- `coding_sessions`: ~9–14s.
- `recent_inputs`: usually small, but ~4.5s on 2026-06-29.
- Most other phases are sub-3s.

## Comparison

Against the old successful-run average (~570.6s), the deterministic path is roughly:
- ~8.0x faster using the ~71s local-wrapper observation.
- ~5.8x faster using the ~98s conservative real-cron observation.

Against the old successful-run median (~489.3s), the deterministic path is roughly:
- ~6.9x faster at ~71s.
- ~5.0x faster at ~98s.

Operationally, the bigger win is reliability: the old flow depended on long LLM turns and context/compression behavior; the deterministic no-agent flow checkpoints phases and returns bounded script output.

## Pitfalls

- Do not compare cron output file modification times to run times; cron output files are written after completion and may not encode duration. Use scheduler log start/completion lines and deterministic manifest phase seconds.
- The 2026-06-29 06:02 deterministic failure was not a deterministic-runner speed failure. It was the outer Hermes script-only scheduler timeout still set to 120s. The fix was `cron.script_timeout_seconds: 900`.
- Avoid same-day `--dry-run` validation after a real publish because it can overwrite same-day manifest/publish metadata. Use unit tests, non-publishing test dates, or direct artifact/URL/Todoist/registry checks instead.
