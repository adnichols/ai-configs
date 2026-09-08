# Codex Configuration

This directory is the repository source for Codex prompts and reference snippets.

## Contents

- `prompts/` — Codex prompt files
- `skills/` — parallel Codex skill payloads, including ADN's supporting resources
- `skill-overrides.json` — source provenance and optional-profile selection
- `install-skills.py` — isolated skill installation and Codex-only shared-skill exclusions
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
- The installer preserves account, model, MCP, and unrelated configuration. It maintains a marked `skills.config` block in the Codex config to disable shared counterparts of the parallel skills. It backs up the config before changing it.
- Existing legacy generated project `.codex` files from this repo are removed during install so they cannot override global settings.

## Parallel skill installation

Install just the skills with `python3 _codex/install-skills.py` from this repository. Python 3.11 or newer is required. The default destination is `$CODEX_HOME/skills`, or `~/.codex/skills`. No files under `~/.agents`, OMP, Pi, or Cursor are changed. Optional-profile copies are installed only when their shared counterparts already exist.

Codex does not reliably select one skill merely because two folders have the same skill name. The installer therefore disables both the shared path and its resolved symlink target in Codex's configuration and enables the parallel copy. Other clients retain the shared originals. Restart Codex after installation to refresh configuration; an already-running task may retain its initial skill catalog.

The installer refuses unmanaged same-name collisions in the Codex destination. It records installed files and hashes in `ai-configs-skills.json`. Re-running refreshes managed copies and replaces only its own config block. User role overrides live separately in `$CODEX_HOME/adn-models.json` and survive installation. Use `audit-adn` for installed integrity checks.

The parallel copies are independently maintained. `skill-overrides.json` identifies each original source; installation does not regenerate or silently refresh the copies. ADN-derived content retains its upstream license at `skills/adn-mode/LICENSE.pstack` and the pin recorded in `_adn/PROVENANCE.md`. Codex model choices and tool mappings live in `skills/adn-mode/references/`.

Core orchestration uses native Codex agents for bounded read-only work and keeps implementation in the driver. The external delivery CLI remains OMP/Pi-only; its parallel skill provides honest native routing and read-only status rather than inventing a Codex ledger runtime. Product-specific guides retain commands for administering those products only when that is the user's actual task.

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
