# Deterministic GM publish-state fidelity (2026-06-28)

## Context

A manual recovery run of the deterministic Good Morning cron produced and published the 2026-06-28 briefing correctly, but a later validation smoke test used the same report date with `GM_DRY_RUN=1`. Because the deterministic runner writes `runs/YYYY-MM-DD/manifest.json` and `publish.json` for every run, the same-day dry run overwrote the publish metadata with `dry_run: true` and null `review_url` / `plan_id`, even though the real plan-review registration and Todoist task were valid.

## Durable lessons

- After a real `--publish`, do not run same-date `--dry-run` as a validation step unless you intentionally want to overwrite the run checkpoint.
- Prefer validating the wrapper with a non-publishing test date, `--skip-live` smoke test, unit tests, or direct artifact/plan-review/Todoist/registry checks.
- If same-date dry-run validation already overwrote publish metadata, restore `runs/YYYY-MM-DD/manifest.json` and `publish.json` from the verified plan-review URL, plan id, Todoist task id, and registry entry.
- Cron fidelity matters: the wrapper should pass `GM_JOB_ID=039f96dcecfc` and `GM_JOB_NAME="Daily Good Morning HTML Plan + Todoist Review"` into the deterministic runner so `active-plans.json` shows the real owning cron job, not `manual`.

## Verification checklist

- HTML artifact exists at `adn_vault/DailyGM/YYYY-MM-DD-gm.html`.
- Plan-review URL returns 200.
- `plan-review agent next <plan_id> --no-wait --json --url http://mbp.braid-python.ts.net:4317` returns `status: empty` or the queue is drained.
- Todoist contains `Review good morning report: <exact URL>` due at 8:00 AM local time.
- `/Users/anichols/.hermes/state/gm-plan-maintainer/active-plans.json` has the exact plan id and review URL with `status: active`.
- `runs/YYYY-MM-DD/manifest.json` and `publish.json` preserve the real publish metadata after verification.
