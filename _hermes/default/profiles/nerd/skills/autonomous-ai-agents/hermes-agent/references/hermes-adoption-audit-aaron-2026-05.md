# Aaron Hermes adoption audit pattern — May 2026

Use this as a compact example/reference when Aaron asks to review recent Hermes changes against his local setup.

## Scope pattern
- Load `hermes-agent` first for any Hermes configuration/setup/troubleshooting task.
- Use the current date to define the release window; for this session the review window was `2026-04-18` through `2026-05-02`.
- Identify:
  - Hermes home, usually `/Users/anichols/.hermes` on Aaron's Mac.
  - Source checkout, usually `/Users/anichols/.hermes/hermes-agent`.
  - Active/default profile plus profile-specific homes under `~/.hermes/profiles/<name>`.
  - LaunchAgents/gateway status when gateway behavior matters.
- Always redact `.env`, auth, webhook URLs, API keys, OAuth tokens, cookies, private keys, and connection strings.

## Useful live probes
Prefer small targeted probes over broad/long git aggregations.

```bash
hermes update --check
hermes --version
hermes status --all
hermes doctor
hermes config check
hermes profile list
hermes profile show writing
hermes tools list
hermes plugins list
hermes mcp list
hermes cron list --all
hermes webhook list
hermes sessions stats
launchctl list | grep -i hermes || true
/bin/ls ~/Library/LaunchAgents | grep -i hermes || true
git -C ~/.hermes/hermes-agent status --short --branch
git -C ~/.hermes/hermes-agent log --since='2 weeks ago' --oneline --max-count=100
```

Avoid rerunning a command that previously timed out and returned an explicit `BLOCKED: Command timed out. Do NOT retry this command.` message; switch to smaller `--max-count`, narrower path filters, release notes, docs, or manifests.

## What to inspect for adoption gaps
- Config drift: compare `hermes config check` for default and key profiles, especially `_config_version` migrations.
- Profiles: model/provider, gateway running state, `.env`/`SOUL.md` presence, alias path.
- LaunchAgents: default/profile gateway health and stale/failed services.
- Cron/webhooks: jobs, delivery type, toolset restrictions, `workdir`, `context_from`, attached skills, script-backed jobs, webhook `deliver-only` opportunities.
- Plugins/hooks: enabled user plugins, dormant local hook directories, bundled plugin manifests under `hermes-agent/plugins`.
- Skills: local/user-created skills, pinned/curator-sensitive skills, `.usage.json` if relevant.
- State size: `hermes sessions stats`, WAL size, `cron/output`, logs/cache/checkpoints.
- Source overrides: local git diff in `~/.hermes/hermes-agent`; direct source edits should be avoided or migrated to plugins/hooks/skills/config per upgrade-safe customization guidance.

## Capabilities to map in recommendations
For Hermes v0.12-era audits, explicitly check these because they often replace ad-hoc local automation:
- Config migration and `hermes doctor --fix`.
- Curator dry-runs, pinning critical local skills before real runs.
- `disk-cleanup` plugin versus custom temp/log cleanup scripts.
- Persistent `/goal` for long-running objectives.
- Kanban board for durable multi-agent task tracking; evaluate as an orchestration layer above Pi/tmux, not an immediate replacement.
- Cron enhancements: `workdir`, `script`, `context_from`, enabled toolsets, attached skills.
- Webhook `--deliver-only` for low-cost event notifications.
- Fallback providers via `hermes fallback`.
- Observability via Langfuse, only after privacy/telemetry review.
- Built-in plugins such as Google Meet, Spotify, image generation, Teams/IRC/Yuanbao only when they match an actual workflow.
- Browser CDP availability and requirements when web QA/dashboard automation is needed.

## Reporting style for Aaron
- Start with direct current-state findings and adoption priorities, not a long narrative.
- Separate: current state, new capabilities, local custom functionality, recommended adoption sequence.
- Call out caveats when exact command output was unavailable or compacted.
- Do not include secret values; state that secret-bearing files were inspected/redacted if relevant.
