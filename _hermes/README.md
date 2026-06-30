# Hermes configuration in ai-configs

This tree captures the managed, source-like parts of Aaron's Hermes home so changes can be reviewed and kept in `~/code/ai-configs` instead of living only under `~/.hermes`.

## Current bundle

- `default/` — export of `/Users/anichols/.hermes` for the active default Hermes profile plus profile-local managed config under `profiles/`.

## Normal workflow

From the repo root:

```bash
# Pull the current managed Hermes config into this repo
python3 scripts/hermes_config_sync.py export

# Check manifest hashes and scan for obvious token patterns
python3 scripts/hermes_config_sync.py verify

# Preview what would be installed into ~/.hermes
python3 scripts/hermes_config_sync.py install --dry-run

# Install managed files from this repo into ~/.hermes
python3 scripts/hermes_config_sync.py install --apply
```

Prefer editing this repo copy first, then installing into Hermes. `install --apply` backs up overwritten target files/directories under `~/.hermes/backups/ai-configs-install-<timestamp>/`.

After any Hermes configuration change, run `python3 scripts/hermes_config_sync.py export`, run `python3 scripts/hermes_config_sync.py verify`, then commit and push the `ai-configs` changes before considering the Hermes configuration work complete.

## What is included

- Sanitized `config.yaml` fragments
- Skills
- Hooks
- Plugins
- Scripts
- Cron job definitions (`cron/jobs.json`, not cron output)
- Hermes memory markdown files
- Selected small source/config files such as `SOUL.md` and `shell-hooks-allowlist.json`
- The same managed surfaces for nested Hermes profiles where present

## What is excluded

Secrets and runtime/generated state stay out of git: `.env`, `auth.json`, OAuth/PAT/API tokens, sessions, logs, caches, SQLite state, checkpoints, process state, lock/pid files, generated cron output, and the Hermes source checkout/venv.

Secret-like config leaves are replaced with `[REDACTED: managed outside ai-configs]`; the installer skips those leaves so local secrets remain in `~/.hermes`.
