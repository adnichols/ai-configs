# AI Configs

Shared configuration repo for:

- Claude Code
- Codex
- Pi (`_pi`)
- Oh My Pi (`_omp`)

It packages prompt/command surfaces, agent definitions, shared skills, helper scripts, and install tooling in one place.

## Repository layout

```text
ai-configs/
├── _claude/      # Claude source config
├── _codex/       # Codex source config
├── _pi/          # Pi source config
├── _omp/         # Oh My Pi source config and custom agents
├── amp/          # Canonical Amp settings + custom plugin modes installer
├── herdr/        # Canonical cross-host Herdr configuration and installer
├── hammerspoon/  # Terminal-scoped macOS image-paste configuration
├── kitty/        # Managed Kitty/Herdr remote-workflow configuration
├── wezterm/      # Managed WezTerm/Herdr remote-workflow configuration
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
bash ~/ai-configs/install.sh --pi
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
- does not create project `.codex/`; Codex uses global `~/.codex/config.toml`
- mirrors Codex prompts into `~/.codex/prompts`
- keeps Codex prompt availability aligned with Pi, using Pi-delegating wrappers for Pi-only multi-model/subagent commands
- refreshes Codex-discoverable shared skills in `~/.agents/skills`
- mirrors shared helper scripts into the runtime locations that need them
- installs Pi to `~/.pi/agent/`
- copies repo-managed Pi extensions into `~/.pi/agent/extensions/` (these do not appear in `pi list`) and registers the managed npm Pi package set, including `@juicesharp/rpiv-todo`
- with `--tools` or `--all`, installs Oh My Pi configuration, cross-repository guidance, custom agents, non-credential extensions, the canonical Herdr and Amp configuration, terminal-scoped Hammerspoon image-paste workflow, and managed Kitty screenshot/Herdr workflow locally; remote OMP deployment is a separate Git pull/install workflow
- removes positively identified managed deprecated shared-skill entries (including `omp-review-partner`), while preserving ambiguous Gemini, OMP, OpenCode, and Pi plan-mode runtime files for explicit manual cleanup
- syncs shared skills into `~/.agents/skills` from `skills/install-matrix.json`
- with `--update`, first runs `npx skills update -g -y` for globally installed skills tracked by skills.sh, then runs the normal ai-configs sync
- renders the tracked repo-root `APPEND_SYSTEM.md` to `~/.pi/agent/APPEND_SYSTEM.md`, replacing `{{AI_CONFIGS_VERSION}}` with `YYYY-MM-DD+<git-sha>` and adding `-dirty` only when the doctrine differs from that commit; non-Git or untracked doctrine installs fail rather than recording ambiguous provenance
- keeps Pi request-type-first: questions, explanations, diagnosis, review, planning discussion, and status are read-only unless the user separately authorizes a change
- preserves local settings files where appropriate

To update an existing install from this repo, run the same `install.sh` command again. To also refresh skills installed through skills.sh, add `--update`.

For the bounded Pi review stack, `install.sh --pi-review-stack` derives every managed path from `scripts/pi-review-stack-managed-surfaces.json`, runs the deterministic no-model planner/reviewer transport probe, and preserves caller-owned siblings. Use `--summary-json <path>` for an atomic mode-0600 install-summary-v1 receipt. `scripts/install-pi-transactionally.sh --summary-json <path>` adds exact rollback status, while `scripts/install-kitty-remote-hosts.sh --summary-json <path>` records ordered, deduplicated hosts, explicit remote staging cwd, transport status, and strict versus advisory failure.

## Key directories

### `_claude/`
Claude commands, default settings, and the read-only `reviewer` subagent. The installer installs `_claude/agents/reviewer.md`, which uses `claude-sonnet-5` at high effort for bounded plan and code review only.

### `_codex/`
Codex prompt files plus config templates. Global Codex prompt discovery is handled by the installer.

### `_pi/`
Pi prompts, subagents, repo-managed extensions copied into `~/.pi/agent/extensions/`, and Pi package baseline documentation for the separate `pi list`-visible package set. Notable reviewed-plan commands include `/dev:plan`, `/dev:pm-review`, `/review:plan`, `/cmd:execute-plan`, and `/run-plan`.

### `_omp/`
Canonical Oh My Pi host configuration, custom agents, provider extensions,
Herdr/Orca runtime integrations, and delivery routing. The managed DeepInfra
extension registers the `deepinfra` provider, dynamically discovers its model
catalog, and provides the API-key login flow. The Herdr and Orca extensions
contain no credentials; they read host-local integration endpoints and tokens
from the process environment.
`config.yml` is installed to `~/.omp/agent/config.yml` with mode `0600`;
`AGENTS.md`, custom agents, and extensions are installed alongside it. The OMP-discoverable
DeepInfra requests use `DEEPINFRA_API_KEY` when present; otherwise authenticate
the provider through OMP's provider login flow.
`delivery-run` skill is installed to
`~/.agents/skills/delivery-run/SKILL.md`, and the `delivery` CLI is exposed
through `~/.local/bin/delivery`. It preserves the first differing managed file as
`<name>.before-ai-configs`.

OMP delivery uses the persisted `omp-lite` profile: normal-mode planning,
same-session Terra-high implementation/scoped/PM review, bounded OMP
planner/reviewer agents, Grok-high request-bound completeness acceptance,
verification, and PR handoff. It never launches Pi or enables OMP native plan
mode. Start from OMP with
`delivery spawn --runtime omp -- "<goal>"`, or bootstrap the current worktree
with `delivery bootstrap --runtime omp --slug <slug> --goal "<goal>"`.

Run `bash _omp/install.sh` for an OMP-only local install. Remote OMP
installation always uses the existing `ai-configs` Git checkout as transport:
commit and push the repository change, install locally, then pull and install
from the checkout on each remote host. The remote helper refuses dirty
checkouts and non-fast-forward pulls:

```bash
bash scripts/install-omp-remote-hosts.sh
```

The helper defaults to `dever` and `mbp14`; override with `OMP_REMOTE_HOSTS`.
Use `OMP_REMOTE_BRANCH` and `OMP_REMOTE_REPO_PATH` when the checkout differs
from the local branch or the default `$HOME/code/ai-configs` path. It never
copies source trees with tar, rsync, or scp, and never transfers `auth.json`,
databases, sessions, blobs, or other credential/runtime state. Unmanaged
active OMP command, system, model, agent, and extension entries on a
destination are moved to a timestamped
`~/.omp/agent.before-ai-configs/` backup before reconciliation.

### `amp/`
Canonical Amp CLI settings and custom plugin modes from `plugins/subscription-models.ts`: `ADN Low` (Luna max), `ADN High` (Terra high), `adn_oracle` tool/mode (Sol high), and `adn_alt` tool/mode (Grok 4.6 high). Amp's built-in `low`/`medium`/`high`/`ultra` keys cannot be overwritten; these ADN modes sit beside them. `install.sh --tools` and `install.sh --all` install them to `~/.config/amp/`, preserve first-differing backups as `*.before-ai-configs`, and on macOS stream the bundle to `mbp`, `dever`, and `mbp14` (override with `AMP_REMOTE_HOSTS`). Model-provider subscriptions stay host-local credentials.

Run `bash amp/install.sh` for an Amp-only local install.

### `herdr/`
Canonical host-independent Herdr configuration plus its installer. `install.sh --tools` and `install.sh --all` install it to `~/.config/herdr/config.toml`, preserving the first differing local file as `config.toml.before-ai-configs`. The same configuration validates on the current Herdr versions on `mbp`, `dever`, `mbp14`, and `mba`; it intentionally standardizes theme and UI preferences across hosts.

Run `bash herdr/install.sh` for a Herdr-only local install. From macOS, the normal tools workflow also streams it to the configured Kitty remote hosts. Override those targets when needed, for example:

```bash
KITTY_REMOTE_HOSTS="mbp14 mba" bash ./install.sh --tools
```

### `wezterm/`

Canonical WezTerm remote-development configuration. `install.sh --tools` and `--all` install a narrowly composed Lua module into `~/.config/wezterm/` and add its loader to a compatible user-owned `~/.wezterm.lua`; the installer refuses to guess when that root config does not have exactly one `return config`. It renders each Herdr tab with a solid host-colored background — **mbp** purple, **dever** blue, and **mbp14** green — while preserving live working / blocked / done counts from the existing `herdr-kitty-status` terminal-title contract. It also enables the Kitty keyboard protocol so Pi and OMP receive a distinct `Shift+Enter` over SSH, and adds the `herdr-mbp`, `herdr-dever`, and `herdr-mbp14` shell functions, launch-menu entries, `Cmd+Shift+1/2/3` host shortcuts, and `Cmd+Shift+V` image upload/path insertion for the focused supported remote pane. The WezTerm workflow is local-only; it does not alter Kitty or stream WezTerm files to remote hosts.

Run `bash wezterm/install.sh` for a WezTerm-only local install.

### `hammerspoon/`
Terminal-scoped macOS clipboard-image workflow. Its installer copies `scripts/remote-image-paste` to `~/.local/bin/`, adds an isolated managed block to `~/.hammerspoon/init.lua`, and installs Hammerspoon plus `pngpaste` through Homebrew when either is missing. With a supported terminal focused, `Cmd+Shift+V` uploads the clipboard image over SSH to both `dever` and `mbp`, then pastes `/tmp/ai-image-paste-anichols/latest.png` into the focused prompt. The event tap passes the chord through unchanged in non-terminal applications, and rechecks the active app before its asynchronous upload completion can paste text.

### `kitty/`
Canonical Kitty remote-development configuration, shell reminder, SSH kitten settings, and its local installer. On macOS, `--tools` and `--all` also deploy this tracked bundle and the canonical Herdr config to the `mbp` and `dever` SSH aliases. Remote hosts that are offline produce a warning and are retried the next time the installer runs; set `KITTY_WORKFLOW_STRICT_REMOTE=1` to make an unreachable host fail the install.

The workflow installs `clipssh` and its Kitty helper into `~/.local/bin`, installs `pngpaste` through Homebrew when needed, installs the commit-pinned `herdr-kitty-status` integration, and sets Herdr toast delivery to `terminal`. On a Kitty client without Herdr, it still installs the status renderer so titles from remote Herdr hosts retain their aliases, colors, and compact counters. It deliberately does not run `herdr integration install pi`, which would overwrite the Pi extension managed by this repository. Set `KITTY_WORKFLOW_SKIP_REMOTE=1` to perform only the current-host install, or override the targets with `KITTY_REMOTE_HOSTS="host1 host2"`.

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

`ai-configs` still owns workflow guidance such as `skills/doct-document-ops`, but any daemon, CLI, service, or formula changes belong in `Nodaste-Lab/plan-reviewer`.

## Skills and tools

Shared skills install to:

```text
~/.agents/skills/
```

Claude compatibility links are created where needed, but `~/.agents/skills` is the canonical shared runtime location. Codex discovers user skills directly from this location. Repo-owned payloads come from `skills/`; package-backed payloads are fetched per `skills/install-matrix.json`.

`skills/install-matrix.json` also records optional profiles (`creative-content`, `macos`, `rust`, and `ops-browser`). Skills with `defaultInstall: false` stay available as managed inventory but are backed out of the default `~/.agents/skills` discovery surface so Pi and Codex do not load rarely used profiles into every session.

`--update` updates globally installed skills tracked by skills.sh before ai-configs re-syncs its managed skill set:

```bash
bash ./install.sh --skills --update
```

`--tools` installs or updates the canonical Herdr, Amp, and WezTerm configuration, terminal-scoped Hammerspoon image-paste workflow, managed Kitty remote workflow, `ltui` from the standalone `Nodaste-Lab/ltui` repository, and the managed Herdr plugin set:

- `persiyanov/herdr-reviewr`

```bash
bash ./install.sh --tools
```

The Herdr plugin installer intentionally reruns `herdr plugin install <source> --yes`, which resolves the current upstream revision and replaces an older managed checkout while preserving the plugin's configuration directory. If Herdr is not installed, the plugin step is skipped with a warning.

For testing or pinning an `ltui` branch:

```bash
LTUI_REPO_URL=/path/to/ltui LTUI_REF=linear-rate-limit-reduction bash ./install.sh --tools
```

## Working docs

The repo keeps long-lived and working documentation separate:

- `spec/` — permanent architecture and ADR-style material
- `thoughts/` — plans, research, handoffs, validation, retro notes
- `docs/` — fetched framework/library docs

## Notes

- This repo intentionally no longer tracks accumulated local runtime trees like `.claude/`, `.codex/`, `.pi/`, `.agent/`, or `.agents/`.
- The retired `_gemini/` and `_opencode/` source trees are no longer installed or maintained here.
- Installed runtime paths remain the normal dot-directories used by each maintained tool.

For a host-level verification of both Pi installation surfaces, run:

```bash
bash ./scripts/verify-pi-install.sh
```

## More specific docs

- `_pi/README.md`
- `AGENTS.md`
- `CLAUDE.md`
