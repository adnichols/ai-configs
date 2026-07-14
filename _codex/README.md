# Codex Configuration

This directory is the repository source for Codex prompts and reference snippets.

## Contents

- `prompts/` — Codex prompt files
- `config.toml` — reference-only Codex config template
- `mcp-servers.toml` — reference-only MCP server snippets for Codex
- `../scripts/` — shared helper scripts installed into `~/.codex/scripts`

## Install

```bash
bash /path/to/ai-configs/install.sh --codex
bash /path/to/ai-configs/install.sh --codex ~
```

Re-run `install.sh` to refresh an existing installation.

## Notes

- Repo source lives under `_codex/`; installed runtime files live under `~/.codex/` for global Codex resources.
- Shared helper scripts are maintained once in the repo-level `scripts/` directory and copied into `~/.codex/scripts` by the installer.
- Prompt files are mirrored to `~/.codex/prompts` because Codex discovers global prompts there.
- Codex prompt availability tracks Pi prompt availability; Pi-only multi-model/subagent commands are installed as Codex wrappers that delegate to `pi -p --approve` from the same worktree.
- The installer does not create project `.codex/` directories.
- The installer does not install or mutate `config.toml`; keep account, model, and MCP settings in your global `~/.codex/config.toml`.
- Existing legacy generated project `.codex` files from this repo are removed during install so they cannot override global settings.

## Canonical reviewed-plan workflow

Codex mirrors the core reviewed-plan flow used in Pi:

```text
/dev:plan <plan>
/dev:pm-review <plan> plan        # optional reshaping pass
/review:plan <plan>
/review:change-integrate <plan>
/cmd:execute-plan <plan>
```

Canonical continuation after a reviewed plan is ready:

- `/run-plan <plan>` for full lifecycle execution through PR creation and monitoring
- `/dev:run <plan>` for direct execution-only handoff

Plan review and execution use the maintained `reviewed-html-plan` and `run-plan` workflows directly. Optional-profile skills in `skills/install-matrix.json` are not installed into the default Codex discovery surface.
