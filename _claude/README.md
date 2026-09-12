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
- The installer removes any previously installed managed `.claude/agents/` subagents; the repository no longer ships a Claude reviewer.
- Slash commands must keep discovery, planning, implementation, testing, review, and documentation in the driving Claude session.
- `CLAUDE.md` is repo documentation, not an installed runtime file.
