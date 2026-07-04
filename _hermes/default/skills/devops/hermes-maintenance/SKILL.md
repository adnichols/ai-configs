---
name: hermes-maintenance
description: "Routine Hermes Agent maintenance after updates: health checks, config migration, doctor fixes, skill updates, gateway/service refresh, and safe follow-up triage."
version: 1.0.0
author: Hermes Agent
tags: [hermes, maintenance, update, doctor, gateway, skills]
---

# Hermes Maintenance

Use this skill when Aaron asks for routine maintenance after updating Hermes Agent, or when an update may have changed config schema, launchd/service definitions, skills, plugins, or dependency state.

This is an operations skill for an installed Hermes environment. For authoritative CLI semantics and full reference, load the protected `hermes-agent` skill and/or consult the official docs first; use this skill for the practical maintenance sequence and pitfalls learned from local runs.

## Default sequence

1. Establish current state.
   - `date`
   - `hermes --version`
   - `hermes config path`
   - `hermes status --all`
   - `hermes config check`
   - `hermes doctor`

2. Migrate config when `config check` or `doctor` reports an outdated config version.
   - Run `hermes config migrate`.
   - Re-run `hermes config check` and verify the config version is current.
   - Treat missing optional API keys as informational unless Aaron asked to enable those capabilities.

3. Run safe automated fixes.
   - Run `hermes doctor --fix` when doctor recommends it.
   - Common safe fix: checkpointing a large SQLite WAL file.
   - Re-run `hermes doctor` afterward and compare remaining issues.

4. Check update-adjacent surfaces.
   - `hermes skills check`
   - `hermes plugins list` (or compact/plain if available)
   - `hermes mcp list`
   - `hermes cron list --all`
   - `hermes webhook list`
   - `hermes sessions stats`

5. Update installed hub skills if updates are reported.
   - `hermes skills update`
   - Re-run `hermes skills check`.
   - Pitfall: an update may report successful install while `skills check` still says `update_available`; report it as a possible hub/check metadata inconsistency rather than retrying indefinitely.

6. Triage dependency audits that doctor explicitly reports.
   - For Node workspaces called out by doctor, run the suggested `npm audit fix` in that exact workspace.
   - Re-run `npm audit` and `hermes doctor`.
   - If the remaining vulnerability has `No fix available`, report that clearly and do not invent a remediation. Recommend disabling/not running the affected optional bridge if it is unused or exposed.

7. Restart/refresh gateway only after config/service changes.
   - `hermes gateway restart` applies the new config to the default gateway.
   - This can kill/restart running agents and may require user approval.
   - After restart, run `hermes gateway status`.
   - If status says the launchd service definition is stale relative to the current Hermes install, run `hermes gateway start` to refresh the service definition, then check status again.
   - On macOS launchd, `hermes gateway start` may print `Bootstrap failed: 5: Input/output error` but still update the service definition and leave the service loaded. Verify by re-running `hermes gateway status`; trust the final status over the intermediate warning.

8. Final verification and report.
   - Summarize what changed, what was verified, and what remains.
   - Include changed file paths when known.
   - Separate actionable remaining issues from optional missing credentials.
   - Do not over-explain; Aaron prefers concise operational summaries.

## Safety boundaries

- Do not inspect or print secret values from `.env` or auth files.
- Do not edit other Hermes profiles unless Aaron explicitly asks.
- Read-only checks against other profiles are acceptable only when clearly framed as read-only; profile-specific config migrations/restarts are separate side effects.
- Do not treat optional unconfigured providers as maintenance failures.
- Do not use destructive cleanup unless Aaron explicitly authorizes scope.

## Reporting template

```
Maintenance complete.

Done:
- <version/status checks>
- <config migration / doctor --fix results>
- <skills/plugins/cron/webhook/MCP checks>
- <gateway restart/status if performed>

Changed:
- <path>: <reason>

Remaining:
1. <real issue needing decision>
2. <optional capability/config gap>

Next recommended action:
- <one concise action, if any>
```

## Compaction-specific triage

If Hermes context compaction hangs, times out, creates a blank-looking continuation session, or delays Discord/Telegram responses, check the compression auxiliary route before treating it as a generic session DB issue:

- Inspect `auxiliary.compression` and `compression` in `~/.hermes/config.yaml`.
- Search `~/.hermes/logs/agent.log` for `Auxiliary compression`, `Request timed out`, `Failed to generate context summary`, and `context compression done`.
- Prefer `openai-codex / gpt-5.4-mini` for compression over `custom / gpt-5.5` through a localhost proxy.
- See `references/2026-07-compaction-model-routing.md` for the full observed pattern and fix commands.

## References

- `references/2026-06-post-update-maintenance.md` — session-specific transcript notes from a post-v0.16.0 local maintenance run, including config v26→v29, WAL checkpointing, WhatsApp bridge audit behavior, and launchd stale-service refresh behavior.
- `references/2026-07-compaction-model-routing.md` — compaction timeout/blank-continuation diagnosis and preferred auxiliary compression routing.
