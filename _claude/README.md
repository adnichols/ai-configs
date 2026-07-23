# Claude Code Configuration

This directory is the repository source for Claude Code commands and settings.

## Contents

- `commands/` — Claude slash commands executed by the driving session
- `settings.local.json` — default Claude project settings template
- `../scripts/` — shared helper scripts installed into `.claude/scripts`

## Install

```bash
bash /path/to/ai-configs/install.sh --claude
bash /path/to/ai-configs/install.sh --claude ~
```

Re-run `install.sh` to refresh an existing installation. The installer preserves an existing project `settings.local.json`.

## Notes

- Repo source lives under `_claude/`; installed runtime files live under `.claude/` in target projects.
- Claude has no repository-owned subagents. The installer removes any legacy `.claude/agents/` directory.
- Slash commands must keep discovery, planning, implementation, testing, and documentation in the driving Claude session. Independent required reviews use visible read-only Herdr sessions rather than Claude subagents.
- Shared helper scripts are maintained once in the repo-level `scripts/` directory and copied into `.claude/scripts` by the installer.
- `CLAUDE.md` is repo documentation, not an installed runtime file.
