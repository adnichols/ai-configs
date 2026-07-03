# AI Configs

Shared configuration repo for:

- Claude Code
- Codex
- Gemini CLI
- Oh My Pi (`_omp`)
- Pi (`_pi`)
- OpenCode

It packages prompt/command surfaces, agent definitions, shared skills, helper scripts, and install tooling in one place.

## Repository layout

```text
ai-configs/
├── _claude/      # Claude source config
├── _codex/       # Codex source config
├── _gemini/      # Gemini source config
├── _omp/         # OMP source config
├── _opencode/    # OpenCode source config
├── _pi/          # Pi source config
├── scripts/      # Shared helper scripts fanned out by install.sh
├── skills/       # Repo-owned shared skills + install matrix for package-backed skills
├── tools/        # Optional local tool shims/cache; distributable CLIs live in standalone repos
├── docs/         # Fetched/reference docs kept in repo
├── thoughts/     # Working plans, handoffs, research, validation
└── install.sh    # Main installer / updater
```

Convention:
- `_<tool>/` directories are the committed source-of-truth trees.
- `.<tool>/` directories are treated as local runtime/install artifacts and are gitignored.
- Shared helper scripts live once in `scripts/` and are copied to installed runtime locations by `install.sh`.

## Install

Project install:

```bash
git clone <repository-url> ~/ai-configs
cd ~/ai-configs
pip3 install -r requirements.txt

cd /path/to/your/project
bash ~/ai-configs/install.sh --all
```

Single-surface installs:

```bash
bash ~/ai-configs/install.sh --claude
bash ~/ai-configs/install.sh --codex
bash ~/ai-configs/install.sh --gemini
bash ~/ai-configs/install.sh --omp
bash ~/ai-configs/install.sh --pi
bash ~/ai-configs/install.sh --opencode
bash ~/ai-configs/install.sh --skills
bash ~/ai-configs/install.sh --tools
```

Update skills installed through skills.sh before running the normal installer sync:

```bash
bash ~/ai-configs/install.sh --skills --update
bash ~/ai-configs/install.sh --all --update
```

Global install:

```bash
bash ~/ai-configs/install.sh --all ~
```

## What the installer does

- installs Claude config into `.claude/`
- installs Gemini config into `.gemini/`
- does not create project `.codex/`; Codex uses global `~/.codex/config.toml`
- mirrors Codex prompts into `~/.codex/prompts`
- keeps Codex prompt availability aligned with Pi, using Pi-delegating wrappers for Pi-only multi-model/subagent commands
- refreshes Codex-discoverable shared skills in `~/.agents/skills`
- mirrors shared helper scripts into the runtime locations that need them
- installs OMP to `~/.omp/agent/`
- copies repo-managed OMP extensions into `~/.omp/agent/extensions/`
- installs Pi to `~/.pi/agent/`
- copies repo-managed Pi extensions into `~/.pi/agent/extensions/` (these do not appear in `pi list`)
- installs OpenCode resources to `~/.config/opencode/`
- syncs shared skills into `~/.agents/skills` from `skills/install-matrix.json`
- with `--update`, first runs `npx skills update -g -y` for globally installed skills tracked by skills.sh, then runs the normal ai-configs sync
- installs the shared repo-root `APPEND_SYSTEM.md` to Pi as `~/.pi/agent/APPEND_SYSTEM.md` and to OMP as `~/.omp/agent/SYSTEM.md`
- preserves local settings files where appropriate

To update an existing install from this repo, run the same `install.sh` command again. To also refresh skills installed through skills.sh, add `--update`.

## Key directories

### `_claude/`
Claude-specific agents, commands, and default settings.

### `_codex/`
Codex prompt files plus config templates. Global Codex prompt discovery is handled by the installer.

### `_gemini/`
Gemini TOML command definitions plus the `GEMINI.template.md` persona template.

### `_omp/`
OMP commands, agents, repo-managed extensions, and OMP-local docs. The repo-managed planning entrypoint is the `/aplan` extension/alias, which is installed under `~/.omp/agent/extensions/`, enters built-in `/plan` mode while queueing repo-managed planning guidance for the next planning turn, preserves native `/plan`, auto-runs `/review:change-integrate` after standard plan review leaves inline comments, supports `/dev:pm-review` as a corrective PM reshaping pass, and hands reviewed plans off through prepared `/cmd:execute-plan ... --target ...` execution choices. This tree also now ships a vendored `pi-vcc` extension for OMP under `_omp/extensions/pi-vcc`, installed to `~/.omp/agent/extensions/pi-vcc`, which provides algorithmic compaction, the `/pi-vcc` manual compaction command, and the `vcc_recall` tool.

### `_pi/`
Pi prompts, subagents, repo-managed extensions copied into `~/.pi/agent/extensions/`, and Pi package baseline documentation for the separate `pi list`-visible package set. Notable reviewed-plan commands include `/dev:plan`, `/dev:pm-review`, `/review:plan`, `/cmd:execute-plan`, and `/run-plan`.

### `_opencode/`
OpenCode commands, agents, prompts, repo-local-only skills, onboarding docs, and helper scripts.

### `scripts/`
Canonical shared helper scripts used across multiple runtimes.

Current shared scripts include:
- `docs-fetch.py`
- `docs-fetch-batch.py`
- `markdown-converter.py`
- review helpers

### `skills/`
Repo-owned shared skill tree plus `skills/install-matrix.json`, which inventories default and optional package-backed shared skills fetched via `npx skills` during install.

### ltui
The token-efficient Linear CLI for AI agents is no longer vendored in this repository. Install and develop it from the standalone repo.

```bash
brew tap Nodaste-Lab/ltui https://github.com/Nodaste-Lab/ltui.git
brew install Nodaste-Lab/ltui/ltui
```

Source: <https://github.com/Nodaste-Lab/ltui>

`ai-configs install.sh --tools` clones/builds `ltui` from the standalone repo into `${XDG_CACHE_HOME:-~/.cache}/ai-configs/tools/ltui` and links `~/.local/bin/ltui` to that checkout. Override the source for testing or pinning with `LTUI_REPO_URL` and `LTUI_REF`.

### Plan Reviewer
The HTML plan-review daemon and `plan-review` CLI are no longer vendored in this repository. Install and develop them from the standalone repo.

If this machine previously installed the old `local/ai-configs/plan-reviewer` formula, remove that local tap install first so Homebrew does not keep launching the stale cellar service:

```bash
brew services stop plan-reviewer || true
brew uninstall local/ai-configs/plan-reviewer || brew uninstall plan-reviewer || true
brew untap local/ai-configs || true
```

Then install from the standalone tap:

```bash
brew tap Nodaste-Lab/plan-reviewer https://github.com/Nodaste-Lab/plan-reviewer.git
brew install Nodaste-Lab/plan-reviewer/plan-reviewer
brew services start plan-reviewer
```

Source: <https://github.com/Nodaste-Lab/plan-reviewer>

`ai-configs` still owns workflow guidance such as `skills/html-plan-reviewer`, but any daemon, CLI, service, or formula changes belong in `Nodaste-Lab/plan-reviewer`.

## Skills and tools

Shared skills install to:

```text
~/.agents/skills/
```

Consumer-specific compatibility links are created where needed, but `~/.agents/skills` is the canonical shared runtime location. Codex discovers user skills directly from this location. Repo-owned payloads come from `skills/`; package-backed payloads are fetched per `skills/install-matrix.json`.

`skills/install-matrix.json` also records optional profiles (`creative-content`, `macos`, `rust`, and `ops-browser`). Skills with `defaultInstall: false` stay available as managed inventory but are backed out of the default `~/.agents/skills` discovery surface so Pi and Codex do not load rarely used profiles into every session.

`--update` updates globally installed skills tracked by skills.sh before ai-configs re-syncs its managed skill set:

```bash
bash ./install.sh --skills --update
```

`ltui` lives in the standalone `Nodaste-Lab/ltui` repository and can be installed with:

```bash
bash ./install.sh --tools
```

For testing or pinning a branch:

```bash
LTUI_REPO_URL=/path/to/ltui LTUI_REF=linear-rate-limit-reduction bash ./install.sh --tools
```

## Working docs

The repo keeps long-lived and working documentation separate:

- `spec/` — permanent architecture and ADR-style material
- `thoughts/` — plans, research, handoffs, validation, retro notes
- `docs/` — fetched framework/library docs

## Notes

- This repo intentionally no longer tracks accumulated local runtime trees like `.claude/`, `.gemini/`, `.codex/`, `.opencode/`, `.agent/`, or `.agents/`.
- If older notes or scripts reference pre-cleanup paths such as `claude/...`, `codex/...`, `gemini/...`, or `opencode/...`, use the underscored source paths instead.
- Installed runtime paths remain the normal dot-directories used by each tool.

For a host-level verification of both Pi installation surfaces, run:

```bash
bash ./scripts/verify-pi-install.sh
```

## More specific docs

- `_pi/README.md`
- `_opencode/OPENCODE_ONBOARDING.md`
- `_opencode/QUICKSTART.md`
- `AGENTS.md`
- `CLAUDE.md`
