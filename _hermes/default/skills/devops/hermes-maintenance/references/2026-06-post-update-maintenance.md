# 2026-06 post-update Hermes maintenance notes

Session context: Aaron asked to run routine maintenance after a Hermes update on macOS. The protected `hermes-agent` skill was loaded for authoritative command references, then live checks were run.

## Useful command sequence from the run

```bash
date
hermes --version
hermes config path
hermes status --all
hermes config check
hermes doctor
hermes config migrate
hermes doctor --fix
hermes skills check
hermes skills update
hermes plugins list
hermes mcp list
hermes cron list --all
hermes webhook list
hermes sessions stats
hermes gateway restart
hermes gateway status
hermes gateway start   # only when status reports stale service definition
hermes gateway status
```

## Observed results worth remembering

- `hermes config check` reported config version `26 → 29`; `hermes config migrate` updated it successfully.
- `hermes doctor --fix` cleared a large SQLite WAL warning; afterward doctor no longer reported the WAL issue.
- `hermes skills update` successfully updated `honcho`. `baoyu-article-illustrator` reported successful install, but `hermes skills check` still reported `update_available`; treat this as a possible skill hub/check metadata inconsistency and report it rather than loop forever.
- Doctor reported WhatsApp bridge dependency issues. Running `npm audit fix` in `scripts/whatsapp-bridge` reduced findings from `1 critical, 4 moderate` to `1 critical, 0 moderate`.
- The remaining WhatsApp bridge issue was `@whiskeysockets/baileys` advisory `GHSA-qvv5-jq5g-4cgg`, with `No fix available`. Report this honestly; the safe recommendation is not to run the optional WhatsApp bridge if unused/exposed until upstream publishes a patched Baileys.
- After `hermes gateway restart`, `hermes gateway status` reported the launchd service definition was stale relative to the current Hermes install.
- Running `hermes gateway start` refreshed the launchd definition. It printed `Bootstrap failed: 5: Input/output error`, then reported the service definition updated and service started. A follow-up `hermes gateway status` showed the service definition matched and the gateway remained loaded. Treat this as a verify-after-warning case.

## Reporting pattern that worked

Keep the summary short and operational:

- Completed checks/fixes
- Changed files
- Remaining issues
- Any approval-blocked side effects
- One next action

Avoid treating missing optional provider API keys as failures unless the task is specifically to enable those tool capabilities.
