# Herdr CLI map

This map was verified against `herdr 0.8.2-preview.2026-08-19-b5c4a0176e91` (protocol 20). The installed binary remains authoritative because preview releases can change syntax.

Refresh discovery with:

```bash
herdr --version
herdr --help
herdr --skill
herdr <group>
herdr <group> <command> --help
```

`herdr --skill` prints upstream's inside-pane skill (`Requires HERDR_ENV=1`). This repo's skill overrides that gate when the socket is reachable.

Do not run bare `herdr`; it launches or attaches the TUI. Do not omit arguments from nested mutating commands merely to discover syntax.

## Top-level lifecycle and discovery

| Command | Purpose |
|---|---|
| `herdr` | Launch or attach to the persistent TUI session. |
| `herdr --session <name> ...` | Target or create a named persistent session; place before the command group. |
| `herdr --remote <ssh-target> [--session <name>]` | Attach through SSH to a remote Herdr server. |
| `herdr --remote-keybindings <local\|server>` | Keybindings for `--remote` app attach (default: `local`). |
| `herdr --no-session` | Run monolithically without server/client persistence. |
| `herdr --skill` | Print the upstream agent skill and exit. |
| `herdr status [server\|client]` | Show client/server versions, protocol compatibility, socket, channel, and restart state. |
| `herdr update [--handoff]` | Download and install the latest version; optional live handoff. |
| `herdr channel show` | Print the configured update channel. |
| `herdr channel set <stable\|preview>` | Select the update channel. |
| `herdr completion <shell>` | Generate completions for bash, elvish, fish, PowerShell, or zsh. |
| `herdr --default-config` | Print the default configuration. |
| `herdr server` | Run a headless server. |
| `herdr server reload-config` | Reload the running server's `config.toml`. |
| `herdr server stop` | Stop the running server and its pane processes. Destructive. |
| `herdr server agent-manifests [--json]` | Show active agent detection manifests. |
| `herdr server update-agent-manifests` | Fetch and reload agent detection manifests. |
| `herdr server reload-agent-manifests` | Reload local agent detection manifest overrides. |

Configuration defaults to `~/.config/herdr/config.toml`; `HERDR_CONFIG_PATH` overrides it. Logs default to `~/.config/herdr/herdr.log` plus client/server logs.

## API and configuration

```text
herdr api snapshot
herdr api schema [--json | --output PATH]
herdr config check
herdr config reset-keys
```

- `api snapshot` prints live session state.
- `api schema` prints or writes the bundled JSON schema, including event/request/response shapes.
- `config check` validates configuration and prints diagnostics.
- `config reset-keys` backs up config and removes custom keybindings; it mutates configuration.

## Agent commands

Targets accept a unique agent name or a pane ID that currently hosts an agent. Names must match `[a-z][a-z0-9_-]{0,31}`.

```text
herdr agent list
herdr agent get <target>
herdr agent read <target> [--source visible|recent|recent-unwrapped|detection] [--lines N] [--format text|ansi] [--ansi]
herdr agent send-keys <target> <key> [key ...]
herdr agent prompt <target> <text> [--wait] [--until STATUS]... [--timeout MS]
herdr agent rename <target> <name>|--clear
herdr agent focus <target>
herdr agent wait <target> [--until STATUS]... [--timeout MS]
herdr agent attach <target> [--takeover]
herdr agent start <name> --kind KIND --pane ID [--timeout MS] [-- <agent-args...>]
herdr agent explain [<target>] [--json|--format text|json] [--verbose]
herdr agent explain --file PATH --agent LABEL [--json|--format text|json] [--verbose]
```

States: `idle`, `working`, `blocked`, `done`, `unknown`.

Important semantics:

- `agent start` launches a supported interactive agent in an existing pane at a shell prompt and waits for detection/readiness. Default timeout is 30 seconds; maximum is 300 seconds.
- Blocked startup returns `agent_not_ready` immediately; the name stays available for `agent read` and `agent send-keys`.
- `agent prompt` rejects an already-blocked agent with `agent_blocked` before sending input.
- `agent prompt --wait` waits for a state observed after submission. Default settled matches are `idle`, `done`, or `blocked`; do not repeat those defaults with `--until`.
- Starting from a non-working state, prompt wait requires a state change within 5 seconds or reports `agent_prompt_stalled`. A shorter explicit timeout reports `timeout`.
- If the target is already working, prompt wait may match that active turn's completion; it does not track conversational turn IDs.
- `agent wait` also defaults to `idle`, `done`, or `blocked`. Without `--timeout`, it waits indefinitely.
- `agent attach --takeover` takes terminal control; use only with explicit intent.
- `agent explain` diagnoses integration and screen-detection state.

Verified agent kinds:

```text
pi claude codex gemini cursor devin agy cline omp mastracode opencode
copilot kimi kiro droid amp grok hermes kilo qodercli qwen maki
```

## Pane commands

```text
herdr pane list [--workspace <workspace_id>]
herdr pane current [--pane ID|--current]
herdr pane get <pane_id>
herdr pane layout [--pane ID|--current]
herdr pane process-info [--pane ID|--current]
herdr pane neighbor --direction left|right|up|down [--pane ID|--current]
herdr pane edges [--pane ID|--current]
herdr pane focus --direction left|right|up|down [--pane ID|--current]
herdr pane resize --direction left|right|up|down [--amount FLOAT] [--pane ID|--current]
herdr pane zoom [<pane_id>|--pane ID|--current] [--toggle|--on|--off]
herdr pane rename <pane_id> <label>|--clear
herdr pane read <pane_id> [--source visible|recent|recent-unwrapped] [--lines N] [--format text|ansi] [--ansi]
herdr pane input [<pane_id>|--pane ID|--current] --right-click herdr|pane
herdr pane split [<pane_id>|--pane ID|--current] --direction right|down [--ratio FLOAT] [--cwd PATH] [--env KEY=VALUE] [--right-click herdr|pane] [--focus|--no-focus]
herdr pane swap --direction left|right|up|down [--pane ID|--current]
herdr pane swap --source-pane ID --target-pane ID
herdr pane move <pane_id> --tab <tab_id> --split right|down [--target-pane ID] [--ratio FLOAT] [--focus|--no-focus]
herdr pane move <pane_id> --new-tab [--workspace ID] [--label TEXT] [--focus|--no-focus]
herdr pane move <pane_id> --new-workspace [--label TEXT] [--tab-label TEXT] [--focus|--no-focus]
herdr pane close <pane_id>
herdr pane send-text <pane_id> <text>
herdr pane send-keys <pane_id> <key> [key ...]
herdr pane wait-output <pane_id> (--match TEXT | --regex PATTERN) [--source visible|recent|recent-unwrapped] [--lines N] [--timeout MS] [--raw]
herdr pane run <pane_id> <command>
```

After `pane move`, continue with `.result.move_result.pane.pane_id`. `--lines` cannot recover rows that left a terminal alternate screen.

Integration/reporting commands, normally called by hooks or plugins:

```text
herdr pane report-agent <pane_id> --source ID --agent LABEL --state idle|working|blocked|unknown [--message TEXT] [--seq N] [--agent-session-id ID] [--agent-session-path PATH]
herdr pane report-agent-session <pane_id> --source ID --agent LABEL [--seq N] [--agent-session-id ID] [--agent-session-path PATH]
herdr pane release-agent <pane_id> --source ID --agent LABEL [--seq N]
herdr pane report-metadata <pane_id> --source ID [--agent LABEL] [--applies-to-source ID] [--title TEXT|--clear-title] [--display-agent TEXT|--clear-display-agent] [--state-label STATUS=TEXT] [--clear-state-labels] [--token NAME=VALUE] [--clear-token NAME] [--seq N] [--ttl-ms N]
```

`pane wait-output` searches the current snapshot immediately and then polls. `--regex` accepts Rust regular expressions. Without a timeout, it waits indefinitely.

Ai-configs installs `herdr-operator-attention` as a workflow-facing wrapper around the reporting commands:

```text
herdr-operator-attention set --pane <id> --message <text> [--kind approval|blocker|password|generic] [--no-notify]
herdr-operator-attention clear --pane <id>
herdr-operator-attention status --pane <id>
```

Pane defaults to `HERDR_PANE_ID`. The fixed report identity is source `workflow:operator-attention`, agent `operator-wait`. The helper also maintains a SHA-256-named JSON marker so the authoritative Pi integration can report blocked without surrendering `herdr:pi` ownership. `set` notifies with request sound only for a new or changed message unless `--no-notify`; `clear` never notifies.

## Direct terminal commands

The terminal group remains active even though it may not appear in abbreviated top-level help.

```text
herdr terminal attach <terminal_id> [--takeover]
herdr terminal session control <target> [--takeover] [--cols N] [--rows N]
herdr terminal session observe <target> [--cols N] [--rows N]
herdr terminal title set <title>
herdr terminal title clear
```

- `terminal attach` opens a direct terminal stream by terminal ID.
- `terminal session control` controls a target stream; `observe` is read-only interaction.
- `terminal title` manages the outer terminal title, not a pane label.
- Detach from direct attach with `Ctrl-b q`; send a literal `Ctrl-b` with `Ctrl-b Ctrl-b`.
- Use `--takeover` only with explicit intent.

## Workspace, tab, and worktree commands

```text
herdr workspace list
herdr workspace create [--cwd PATH] [--label TEXT] [--env KEY=VALUE] [--focus|--no-focus]
herdr workspace get <workspace_id>
herdr workspace focus <workspace_id>
herdr workspace rename <workspace_id> <label>
herdr workspace report-metadata <workspace_id> --source ID [--token NAME=VALUE] [--clear-token NAME] [--seq N] [--ttl-ms N]
herdr workspace close <workspace_id>
```

```text
herdr tab list [--workspace <workspace_id>]
herdr tab create [--workspace <workspace_id>] [--cwd PATH] [--label TEXT] [--env KEY=VALUE] [--focus|--no-focus]
herdr tab get <tab_id>
herdr tab focus <tab_id>
herdr tab rename <tab_id> <label>
herdr tab close <tab_id>
```

```text
herdr worktree list [--workspace ID | --cwd PATH]
herdr worktree create [--workspace ID | --cwd PATH] [--branch NAME] [--base REF] [--path PATH] [--label TEXT] [--focus|--no-focus]
herdr worktree open [--workspace ID | --cwd PATH] (--path PATH | --branch NAME) [--label TEXT] [--focus|--no-focus]
herdr worktree remove --workspace ID [--force]
```

Create commands can execute with defaults. Use group help rather than probing them without arguments. Most control commands return JSON; do not add undocumented `--json` flags to discover that.

## Sessions

```text
herdr session list [--json]
herdr session attach <name>
herdr session stop <name> [--json]
herdr session delete <name> [--json]
```

Use `default` as the session name to stop the default session. Stop/delete are destructive and can terminate pane processes.

## Notifications

```text
herdr notification show <title> [--body TEXT] [--position top-left|top-right|bottom-left|bottom-right] [--sound none|done|request]
```

This is an external user-visible action; invoke only when requested or when an authorized workflow explicitly calls for notification.

## Integrations

```text
herdr integration status [--outdated-only]
herdr integration install <kind>
herdr integration uninstall <kind>
```

Install/uninstall kinds in this release:

```text
pi omp claude codex copilot devin droid kimi opencode kilo hermes
qodercli qwen cursor mastracode antigravity-cli grok
```

Integration install/uninstall writes hooks or plugins into the target agent's configuration. `status` is non-mutating.

## Plugins

The plugin group is available even though it may not appear in the abbreviated top-level help.

```text
herdr plugin install <owner>/<repo>[/subdir...] [--ref REF] [--yes]
herdr plugin uninstall <plugin_id|owner/repo[/subdir...]>
herdr plugin link <path> [--disabled]
herdr plugin unlink <plugin_id>
herdr plugin enable <plugin_id>
herdr plugin disable <plugin_id>
herdr plugin list [--plugin ID] [--json]
herdr plugin config-dir <plugin_id>
herdr plugin action list
herdr plugin action invoke ...
herdr plugin log list [--plugin ID] [--limit N]
herdr plugin pane open ...
herdr plugin pane focus ...
herdr plugin pane close ...
```

Use nested `--help` before plugin action invocation or plugin-pane mutation because their arguments are plugin/action specific.

## Legacy-to-current mapping

Older skills and scripts may use forms that changed in the current CLI.

| Legacy form | Current form |
|---|---|
| `herdr wait agent-status <pane> --status ...` | `herdr agent wait <target> --until ...` |
| `herdr wait output <pane> --match ...` | `herdr pane wait-output <pane> --match ...` |
| Generic agent control through `herdr terminal ...` | Prefer `herdr agent ...` for supported agents and `herdr pane ...` for pane/process control. Keep `herdr terminal attach/session/title` for direct terminal streams and outer-title management. |
| `pane run <pane> "codex"`, wait for prompt, then `pane run` task | `herdr agent start <name> --kind codex --pane <pane>`, then `herdr agent prompt <name> <task>`. |
| Numeric/compacting IDs such as `1`, `1:1`, `1-1` | Opaque stable public handles such as `w1`, `w1:t1`, `w1:p1`. Parse responses. |
| Gate all use on `HERDR_ENV=1` | Use the reachable socket from inside or outside; environment variables only identify managed caller context. |
| Repeat `--until idle --until done --until blocked` on every `--wait` | Omit `--until` unless the wait is for a specific non-default state. |
