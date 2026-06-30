# Hermes managed config export

This directory is the ai-configs source copy of managed Hermes configuration.

## Workflow

- Export current local Hermes config: `python scripts/hermes_config_sync.py export`
- Verify the repo copy: `python scripts/hermes_config_sync.py verify`
- Preview install back into Hermes: `python scripts/hermes_config_sync.py install --dry-run`
- Install managed files into Hermes: `python scripts/hermes_config_sync.py install --apply`

For future changes, prefer editing this repo copy first, then run the install command.
After any Hermes configuration change, run export + verify, then commit and push ai-configs before considering the work complete.

## Exclusions

Secrets and runtime state are intentionally not stored here: `.env`, `auth.json`, OAuth tokens, sessions, logs, caches, SQLite state, checkpoints, process state, and generated output.
Secret-like config leaves are written as `[REDACTED: managed outside ai-configs]`; the installer skips those leaves so local secrets remain in `~/.hermes`.
