# Exclusions and localization contract

This export captures source-like Hermes configuration: config conventions, skills, hooks, plugins, scripts, memories, cron job definitions, and profile-local equivalents.

Excluded by design:

- `.env`, `auth.json`, OAuth/PAT/API tokens, credential pools, and private keys
- `sessions/`, `state.db*`, `kanban.db*`, checkpoints, state snapshots, process state
- logs, caches, audio/image artifacts, paste dumps, cron output, temp directories
- Hermes source checkout / venv / node_modules under `~/.hermes/hermes-agent`
- host locks and pid files

Install preserves machine-local secrets by recursively merging config and skipping any redacted leaves. If a future change needs to remove a config key, do that explicitly in Hermes or extend the installer with a deletion manifest.
