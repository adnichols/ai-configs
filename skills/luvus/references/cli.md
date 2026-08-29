# Luvus CLI map

This map was verified against `luvus 0.13.2`. The installed binary remains authoritative because releases can change syntax.

Refresh discovery with:

```bash
luvus --version
luvus help
luvus help all
luvus help <topic>
luvus skill show
```

`luvus skill show` prints upstream's bundled skill. This repo's skill is the override used for agentic control from inside or outside a managed pane.

Do not run bare `luvus`. It launches or attaches the TUI. Do not omit arguments from nested mutating commands merely to discover syntax.

## Top-level lifecycle and discovery

| Command | Purpose |
|---|---|
| `luvus` | Launch or attach the TUI. Do not run this from an agent. |
| `luvus --session <name> ...` | Target a named server session. Place before the command group. |
| `luvus --remote <host> [ssh args]` | Attach through SSH. |
| `luvus help [all\|<topic>]` | Compact, complete, or focused help. |
| `luvus doctor` | Check optional tools such as git and gh. |
| `luvus update` | Check for and install a newer release. |
| `luvus ping` | Check whether the selected server responds. |
| `luvus attach <id>` | Open the TUI focused on one pane. |
| `luvus events` | Stream live status changes as NDJSON. |
| `luvus search <text...>` | Search pane scrollback. |
| `luvus search --fuzzy <query...>` | Rank navigation, files, and retained output. |

The default socket is `$HOME/.luvus/luvus.sock`. Named sessions keep runtime files under `$HOME/.luvus/sessions/<name>/`. `LUVUS_HOME` selects an isolated root. Debug builds use `$HOME/.luvus-dev/`. Do not mix those roots.

## Agent commands

Targets accept a live name, a pane id, or a unique agent kind. Names must match `[a-z][a-z0-9_-]{0,31}`.

```text
luvus agent list
luvus agent get <target>
luvus agent read <target> [--lines N] [--source visible|recent]
luvus agent explain <target>
luvus agent start <name> --kind <k> [--pane <id> | --anchor <id>] [--down] [--timeout <s>] [-- <args>]
luvus agent fork <target> [--name <alias>] [--no-focus]
luvus agent name <name> [--pane <id>]
luvus agent name --clear
luvus agent prompt <target> <text> [--wait] [--until STATE] [--timeout <s>]
luvus agent send <target> <text> [--wait] [--until STATE] [--timeout <s>]
luvus agent keys <target> <key>...
luvus agent sessions
luvus agent resume <id>
```

`agent send` is a compatibility alias for `agent prompt`. States: `idle`, `working`, `blocked`, `done`.

Important semantics:

- `agent start` splits beside `--anchor` or reuses `--pane`, then waits until the agent is ready. Never combine `--anchor` and `--pane`.
- Inside a managed pane, omit `--anchor` and `--pane` to spawn beside `LUVUS_PANE_ID`.
- `--wait` on `agent prompt` is optional. Default is handoff. Default wait timeout is 300s. Exit 2 on timeout still submitted the prompt.
- Luvus permits one waiting prompt per pane.
- Native forks currently support Claude, Grok, Codex, Pi, and OMP.
- `agent name` is the same live address as `pane name`. It also retitles the pane strip.

Kinds documented in 0.13.2 include `claude`, `copilot`, `codex`, `opencode`, `kimi`, `grok`, `pi`, `omp`, `muse`, `fx`, `cursor`, `gemini`, `qwen`, `kiro`, `aider`, `amp`, and `droid`. Confirm with `luvus help agent` on the installed binary.

## Pane commands

```text
luvus pane list
luvus pane split [<id>] [--down] [--no-focus]
luvus pane focus <id>
luvus pane move [<id>] (--tab <n> | --new-tab)
luvus pane run [<id>] <cmd...>
luvus pane send [<id>] <text>
luvus pane read [<id>]
luvus pane status [<id>]
luvus pane processes [<id>]
luvus pane name <name> [--pane <id>]
luvus pane name --clear
luvus pane close [<id>]
```

`pane list` is scoped to the current tab. `pane status` works across workspaces. Prefer `agent prompt` over `pane send` when the pane hosts a supported agent.

## Waits

```text
luvus wait output <id> --match <text> [--timeout <s>]
luvus wait agent-status <id> --status done|blocked|working|idle [--timeout <s>]
```

Exit `0` when the condition is met, `2` on timeout. Use `wait agent-status` for a requested lifecycle transition after work is sent, not for startup identity.

## Workspace, tab, and worktree commands

Workspace indexes are 0-based. Tab numbers are 1-based.

```text
luvus workspace list
luvus workspace new
luvus workspace open <path>
luvus workspace focus <i>
luvus workspace rename <i> <name>
luvus workspace pin <i>
luvus workspace unpin <i>
luvus workspace close [<i>]
```

```text
luvus tab list
luvus tab new
luvus tab focus <n>
luvus tab move <from> <to>
luvus tab move left|right
luvus tab swap <first> <second>
luvus tab rename <name> [--tab N]
luvus tab close [<n>]
```

```text
luvus worktree list
luvus worktree create <branch>
luvus worktree open <path>
luvus worktree remove <path>
```

Closing the final project replaces it with a neutral home workspace. That is not proof the server is offline. `worktree remove` keeps the branch.

## Sessions and server

```text
luvus session list [--json]
luvus session attach <name>
luvus session stop <name> [--json]
luvus session delete <name> [--json]
luvus server status
luvus server start
luvus server stop
luvus server restart
luvus server update-manifest
```

`session attach` launches or attaches the TUI. Never run it merely to test whether a session exists. Stop, restart, and delete are destructive and can terminate pane processes. Never delete `default`.

## Orchestration

```text
luvus task add "<title>" [--paths <glob>...] [--dep <id>...] [--gate <cmd>]
luvus task list
luvus task get <id>
luvus task claim <id>
luvus task next [--start] [--agent <cmd>]
luvus task start <id> [--branch <b>] [--agent <cmd>]
luvus task heartbeat <id> --context <0..1>
luvus task update <id> [--status <s>] [--output <o>] [--note <n>]
luvus task done <id>
luvus task merge <id>
luvus task release <id>
luvus task delete <id>
luvus lease acquire <glob>... --task <id>
luvus lease list
luvus lease release <id>
```

`task start` creates an isolated worktree on `luvus/<id>` and a pane. `task merge` integrates into `luvus/integration` in a dedicated worktree. Context above 0.85 blocks `done`.

## Files, Git, DIFF, and Mission Control

```text
luvus files tree
luvus files open <path> [--target pane|tab|preview]
luvus files reveal <path>
luvus files refresh
luvus git status
luvus git branches
luvus git log [--limit N]
luvus git open [<workspace>]
luvus mission open [<workspace>]
luvus diff list [--layer staged|worktree|untracked|conflict]
luvus diff get <path> [--layer <layer>] [--include-patch]
luvus diff note add --file <path> (--old-line N|--new-line N) --body <text>
luvus diff note list
luvus diff note send --to <agent> [<id>...] [--all-open]
```

Inspect the exact DIFF layer before adding, resolving, removing, or sending notes. Removing a note and sending feedback require explicit authorization.

## Skill, integration, and UHP

```text
luvus skill enable
luvus skill status
luvus skill disable
luvus skill show
luvus integration install <claude|copilot|codex|opencode|kimi|grok|omp>
luvus integration uninstall <claude|copilot|codex|opencode|kimi|grok|omp>
luvus uhp capabilities
luvus uhp schema
luvus uhp snapshot
luvus uhp events
luvus uhp proxy
```

`skill enable` installs prompt guidance. `integration install` writes optional session-resume hooks. Enabling one never enables the other. Use UHP only for explicit harness or protocol work. Never print, persist, or log UHP delegated-token secrets.

## Modules, themes, bar, and UI

These mutate the live interface. Inspect first. Install, uninstall, and consequential setting changes need clear authorization.

```text
luvus module list
luvus module info <id>
luvus module install <owner>/<repo>[/sub] [--ref REF] [--yes]
luvus module run <id> <action>
luvus theme list [--json]
luvus theme install <source> [--yes]
luvus theme use <id>
luvus bar list
luvus ui dock list
luvus ui notification push --text <text> [--level info|success|warning|error]
```

## JSON responses

Most commands return JSON with `.result` or `.error`. Parse pane, workspace, tab, name, and status from those fields. Live `agent list` rows include `pane`, `agent`, `name`, `status`, `cwd`, `workspace`, and `workspace_name`.
