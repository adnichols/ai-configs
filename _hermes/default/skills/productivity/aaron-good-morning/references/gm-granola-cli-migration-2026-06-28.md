# GM Granola CLI migration — 2026-06-28

## Context

Aaron replaced the previous Granola transcript CLI workflow with the public API CLI `granola-cli`. Future `/gm` runs should not use the old `granola auth login` / `granola meeting ...` commands.

## Current CLI shape observed

```bash
granola-cli --skip-updates auth status --json
granola-cli --skip-updates status --check-api --json
granola-cli --skip-updates folders list --all --json
granola-cli --skip-updates notes list --all --json
granola-cli --skip-updates notes get <note-id> --include transcript --json
granola-cli --skip-updates notes summary <note-id> --format markdown
granola-cli --skip-updates notes transcript <note-id> --format markdown
granola-cli --skip-updates sync [folder] --out <dir> --skip-existing --refresh-changed
```

`notes list --all --json` returns an object with `notes`, `hasMore`, and `cursor`. Individual notes include `id`, `title`, `created_at`, `updated_at`, and owner metadata. `notes get --include transcript --json` adds `web_url`, `calendar_event`, `attendees`, `folder_membership`, transcript array, `summary_text`, and `summary_markdown`.

## Repo changes made

- Rebuilt `.agents/scripts/granola_sync_recent.py` to use `granola-cli` and keep stdout compact.
- Updated `.agents/skills/granola/SKILL.md` and `.agents/commands/gm.md` to remove the old auth/session refresh model.
- Updated `.agents/scripts/gm/recent_inputs_phase.py` and `render.py` so Recent Inputs can carry both local Obsidian paths and Granola `web_url` source links.
- Updated `_pi/prompts/gm.md` and the shared Hermes/Pi bundle copy of `aaron-good-morning` so Pi/Hermes agree on the migration.

## Verification performed

```bash
python3 .agents/scripts/granola_sync_recent.py --days 7 --limit 10 --json
PYTHONDONTWRITEBYTECODE=1 python3 .agents/tests/test_gm_deterministic.py -v
```

Observed sync summary after migration: `ok: true`, `notes: 3`, `synced: 0`, `already: 3`, `failed: 0`. Full deterministic GM test suite passed: 30 tests OK.

## Durable rules

- Use `granola-cli --skip-updates ...` in automation.
- If auth is missing, the setup fix is `granola-cli auth <token>`; do not revive `granola auth login`.
- New transcript frontmatter should include both compatibility `granola_meeting_id` and new `granola_id`, plus `granola_web_url`, `created_at`, `updated_at`, `source: granola_public_api`, and `cli: granola-cli`.
- Continue resolving local transcripts across both `adn_vault/Granola/` and the historical nested `adn_vault/adn_vault/Granola/` until the vault is fully cleaned up.
