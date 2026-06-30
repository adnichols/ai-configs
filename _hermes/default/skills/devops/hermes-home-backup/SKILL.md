---
name: hermes-home-backup
description: Create a lean, cron-safe backup of Hermes home that preserves config, memory, sessions, skills, scripts, and profiles while excluding reinstallable code, venvs, caches, and other bulky reproducible artifacts.
tags: [hermes, backup, cron, config, state, restore]
triggers:
  - User wants to back up Hermes config/state without backing up the whole checkout
  - User asks how to preserve Hermes memory, sessions, skills, or profiles across reinstalls
  - Need a cron-safe Hermes home backup with failure notifications
---

# Hermes Home Backup

## Goal
Create a **lean backup** of `HERMES_HOME` that captures the hard-to-reproduce state and excludes Hermes source/dependency bulk such as `hermes-agent/`, virtualenvs, `node_modules`, caches, and logs.

## Default backup scope
Include these when the goal is **config + memory preservation**:

### Files
- `.env`
- `config.yaml`
- `auth.json`
- `SOUL.md`
- `channel_directory.json`
- `discord_threads.json`
- `gateway_state.json`
- `processes.json`
- `state.db`
- `state.db-wal`

### Directories
- `cron/` **but exclude `cron/output/`**
- `hooks/`
- `memories/`
- `pairing/`
- `profiles/`
- `scripts/`  ← back up the backup script too
- `sessions/`
- `skills/`
- `state/`
- `watchers/`

## Exclude by default
These are usually reproducible or not required for restore:
- `hermes-agent/` (repo checkout, venv, node_modules, .git)
- `bin/`
- `cache/`
- `sandboxes/`
- `audio_cache/`
- `image_cache/`
- `logs/`
- `.hermes_history`
- `.update_check`
- `.skills_prompt_snapshot.json`
- `state.db-shm` (SQLite transient file)
- `whatsapp/` unless the user specifically wants platform working state
- `cron/output/` (cron delivery logs; useful for audit, not usually needed for restore)

## Implementation pattern
Use a standalone Python script under:
- `~/.hermes/scripts/hermes_state_backup.py`

Design requirements:
1. Non-interactive and cron-safe
2. Writes a timestamped `.tar.gz` archive **atomically** via temp file + rename
3. Destination must be **outside** Hermes home
4. Optional retention pruning (`--keep N`)
5. Exit nonzero on failure
6. On failure, notify using credentials already stored in `.env`
7. Include a `backup-manifest.json` in the archive documenting what was included/excluded

## Notification strategy
For simple cron-safe failure alerts, prefer direct API calls using tokens already present in `.env`:
1. Discord home channel (`DISCORD_BOT_TOKEN` + `DISCORD_HOME_CHANNEL`)
2. Telegram home channel (`TELEGRAM_BOT_TOKEN` + `TELEGRAM_HOME_CHANNEL`)

Default mode should be `--notify auto`.

Reason: this avoids depending on the live Hermes gateway or a nested agent run just to send failure alerts.

## Verification checklist
After writing or updating the script:
1. `python -m py_compile ~/.hermes/scripts/hermes_state_backup.py`
2. Run a dry run:
   ```bash
   ~/.hermes/scripts/hermes_state_backup.py --dry-run
   ```
3. Run a real backup to a temp dir:
   ```bash
   tmpdir=$(mktemp -d /tmp/hermes-backup-test.XXXXXX)
   ~/.hermes/scripts/hermes_state_backup.py --destination "$tmpdir" --keep 2 --notify none
   ```
4. Inspect archive contents and confirm excluded paths are absent:
   ```bash
   tar -tzf "$tmpdir"/*.tar.gz | head -50
   tar -tzf "$tmpdir"/*.tar.gz | grep '^cron/output'
   ```
   The `grep` should return nothing.

## Current observed result
On Aaron's machine at the time this skill was created:
- full `~/.hermes` was about **925 MB**
- lean backup archive was about **45.8 MB**
- most of the wasted bulk in full backup came from `~/.hermes/hermes-agent/venv`, `node_modules`, and `.git`

## Cron example
```cron
15 2 * * * /Users/anichols/.hermes/scripts/hermes_state_backup.py --destination /Users/anichols/Backups/hermes-state >> /Users/anichols/.hermes/logs/hermes-backup.log 2>&1
```

## Pitfalls
- Do **not** write backups inside `HERMES_HOME`; that risks recursive/self-inclusion and state churn.
- Do **not** include `state.db-shm`; it is transient and often unnecessary.
- If `cron/` is included, explicitly exclude `cron/output/` unless the user wants audit history.
- Nested profiles under `profiles/` can contain their own `home/`, `Library/`, caches, cron output, logs, package stores, and repo checkouts. Apply exclusions by path component at any depth, not just top-level archive prefixes.
- If the user wants platform-specific runtime state, revisit exclusions like `whatsapp/`.
- Avoid backing up `hermes-agent/` when the goal is restoration-after-reinstall rather than full local dev environment cloning.
