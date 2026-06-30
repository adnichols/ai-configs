# GM cron timeout recovery — 2026-06-27

## Symptom

The Daily Good Morning cron job (`039f96dcecfc`) produced the canonical HTML artifact but failed before delivery/finalization with an inactivity timeout:

```text
TimeoutError: Cron job 'Daily Good Morning HTML Plan + Todoist Review' idle for 604s (limit 600s) — last activity: tool completed: terminal (...)
```

The artifact already existed at:

```text
/Users/anichols/Obsidian/adn_vault/DailyGM/YYYY-MM-DD-gm.html
```

but the cron run had not delivered the Discord message, registered/recorded the active plan for the maintainer, or created the Todoist review task.

## Recovery pattern

When a GM cron run times out after the HTML artifact exists, do not rerun the full collection pipeline first. Recover the already-generated artifact:

1. Register the artifact from `/Users/anichols/Obsidian`:
   ```bash
   plan-review register adn_vault/DailyGM/YYYY-MM-DD-gm.html \
     --repo auto --branch auto --commit auto \
     --execution-ready false --json
   ```
2. Use the returned `planId` and `reviewUrl` exactly. If `reviewUrl` is relative, prepend `http://mbp.braid-python.ts.net:4317` without normalizing the path.
3. Drain comments once:
   ```bash
   plan-review agent next <planId> \
     --url http://mbp.braid-python.ts.net:4317 \
     --no-wait --json
   ```
   Repeat only until it reports `status: empty`.
4. Upsert `/Users/anichols/.hermes/state/gm-plan-maintainer/active-plans.json` with the exact plan id, exact full review URL, artifact path, date, and `status: active` so the durable maintainer cron owns the plan.
5. Create and verify the Todoist review task:
   ```bash
   td task add "Review good morning report: <exact plan URL>" \
     --due "YYYY-MM-DDT08:00:00" --priority p2
   td today --json
   ```
6. Report the exact URL, queue-drain status, registry update, and Todoist task ID.

## Prevention note

The Hermes cron runner uses an inactivity watchdog (default observed limit: 600s). Long GM runs can legitimately take longer around finalization/review. If this recurs, prefer reducing long idle gaps in the GM pipeline or increasing the cron inactivity timeout for this environment; do not make the daily cron spawn passive `plan-review agent next --wait` listeners.