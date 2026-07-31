---
name: herdr
description: "Control and troubleshoot Herdr, the terminal workspace manager for coding agents. Use whenever the user explicitly mentions Herdr or asks to inspect, start, prompt, wait for, read, attach to, rename, or coordinate Herdr agents, panes, tabs, workspaces, worktrees, sessions, integrations, plugins, or runtime state. The CLI works from inside or outside a managed pane when its socket is reachable; HERDR_ENV is context, not a prerequisite. Do not use merely because parallel work might be useful."
---

# Herdr

Herdr is a terminal workspace manager and runtime for coding agents. It organizes terminals into workspaces, tabs, and panes, detects supported agents, and exposes the running session through the `herdr` CLI.

Prefer the agent-native commands introduced in current Herdr releases. Use `herdr agent ...` for supported coding agents and `herdr pane ...` for generic terminals, processes, layout, and raw output.

The installed binary is the syntax authority. Read [references/cli.md](references/cli.md) when the task needs broad command discovery, lifecycle/configuration commands, or a complete command-group map.

## Establish current context

Start with non-mutating discovery:

```bash
herdr --version
herdr status
herdr agent list
herdr workspace list
```

The binary can reach the running session from a Herdr-managed pane or an ordinary terminal. Do not gate use on `HERDR_ENV=1`.

Treat the environment only as caller context:

- With `HERDR_ENV=1` and real `HERDR_WORKSPACE_ID`, `HERDR_TAB_ID`, and `HERDR_PANE_ID` values, current-pane shortcuts are safe.
- Without those values, discover state and pass explicit returned IDs.
- If the CLI reports no reachable server, socket, or compatible session, report that error instead of inferring failure from environment variables.

Do not set or fake `HERDR_ENV` or `HERDR_*_ID` values.

For a named persistent session, place the selector before the command group:

```bash
herdr --session <name> status
herdr --session <name> agent list
```

## Treat IDs as opaque

Public handles resemble:

- workspace: `w1`
- tab: `w1:t1`
- pane: `w1:p1`
- terminal: `term_...`

Suffixes may contain letters or multiple characters. Parse IDs from JSON responses; never derive them from display order or examples. Closed handles are not reused, and moving a pane across workspaces can assign a new pane ID. Re-read mutation responses and refresh state before later actions.

## Prefer the agent control surface

`herdr agent` targets a unique agent name or a pane ID currently hosting an agent. It provides readiness-aware start, prompting, settled-state waits, transcript reads, focus, attach, rename, and detection diagnostics.

Discover agents and inspect one:

```bash
herdr agent list
herdr agent get <agent-name-or-pane-id>
herdr agent read <target> --source recent-unwrapped --lines 120
```

Agent states are `idle`, `working`, `blocked`, `done`, and `unknown`:

- `idle`: waiting, and the result is considered seen.
- `done`: waiting after unseen completion.
- `blocked`: needs input or intervention.
- `working`: actively processing.
- `unknown`: no reliable supported-agent state is available.

Treat `idle` and `done` as settled. Focus and visibility can turn `done` into `idle`, so do not require only one of them unless the task specifically depends on attention state.

### Start a supported agent

Default to a sibling pane in the relevant tab and cwd. Do not create a workspace, tab, or worktree unless the user requests that topology.

Inside a managed pane, inspect the caller's geometry:

```bash
herdr pane layout --current
```

Outside a managed pane, identify the intended pane explicitly:

```bash
herdr workspace list
herdr tab list --workspace <workspace-id>
herdr pane list --workspace <workspace-id>
herdr pane layout --pane <pane-id>
```

Split wide panes right and narrow/tall panes down. Keep user focus in place for background work:

```bash
herdr pane split --current --direction right --no-focus
# or, outside managed context:
herdr pane split <pane-id> --direction right --no-focus
```

Read `result.pane.pane_id` from the JSON response. Then use the readiness-aware launcher rather than manually typing the executable:

```bash
herdr agent start reviewer --kind codex --pane <new-pane-id> --timeout 30000
```

Supported kinds are listed by `herdr agent` and `herdr agent start --help`. The current release includes Pi, Claude, Codex, Gemini, Cursor, Devin, OpenCode, Copilot, Hermes, and other integrated agents.

`agent start` requires an existing pane at an interactive shell prompt. Success means the expected agent was detected in that same terminal and is ready for input. Pass agent-specific argv only after `--` and only when the user requests them.

### Prompt and wait

Submit the task with the agent-native prompt command:

```bash
herdr agent prompt reviewer \
  "Review the current diff and report only actionable findings." \
  --wait --until idle --until done --until blocked --timeout 120000
```

Without explicit `--until`, `--wait` matches `idle`, `done`, or `blocked`. Always use a reasonable timeout for automated coordination.

Before prompting an existing target, inspect it. If it is already `working`, a prompt wait can match completion of the active turn rather than a newly submitted turn. Avoid sending new work to a working agent unless that behavior is intentional.

Wait without submitting:

```bash
herdr agent wait <target> --until idle --until done --until blocked --timeout 120000
```

After a wait, inspect state and read the transcript:

```bash
herdr agent get <target>
herdr agent read <target> --source recent-unwrapped --lines 120
```

If a wait times out, read the transcript before deciding whether the agent is still working, blocked, misdetected, or awaiting input.

### Follow up, diagnose, and attach

Follow-ups use the same prompt command:

```bash
herdr agent prompt <target> "Now investigate the failing test." \
  --wait --timeout 120000
```

Use detection diagnostics when status or identity is wrong:

```bash
herdr agent explain <target>
herdr agent explain <target> --verbose
```

Rename an agent you created to make it uniquely addressable, or rename another agent only when the user explicitly requests it:

```bash
herdr agent rename <target> reviewer
```

Names are accepted as control targets, so changing an existing agent's name can break name-based coordination.

Attach directly only when interactive control is requested:

```bash
herdr agent attach <target>
```

Use `--takeover` only when the user explicitly wants to take over that terminal.

## Control generic panes and commands

Use pane commands for shells, servers, tests, logs, unsupported agents, raw terminal input, and layout operations.

Run a command and wait for output:

```bash
herdr pane run <pane-id> "just test"
herdr pane wait-output <pane-id> --match "test result" --timeout 120000
herdr pane read <pane-id> --source recent-unwrapped --lines 120
```

`pane wait-output` searches the selected snapshot immediately, including existing output, and then polls. Literal matching uses `--match`; Rust regex matching uses `--regex`.

Choose the read source intentionally:

- `visible`: current rendered viewport.
- `recent`: recent rendered scrollback, including soft wraps.
- `recent-unwrapped`: recent scrollback with soft wraps joined; prefer for logs and transcripts.
- `detection`: agent-only bottom-buffer snapshot, available through `herdr agent read`.

Use `--format ansi` or `--ansi` only when colors or terminal styling are evidence.

For raw interaction:

```bash
herdr pane send-text <pane-id> "text without Enter"
herdr pane send-keys <pane-id> Enter
herdr pane run <pane-id> "text plus Enter"
```

Prefer `agent prompt` over raw pane input when the pane hosts a supported agent.

## Organize only when requested

Use workspace and tab commands for organization, and worktree commands only when Herdr should intentionally create, open, or remove a Git checkout. Default background mutations to `--no-focus`.

Examples:

```bash
herdr tab create --workspace <workspace-id> --label logs --no-focus
herdr workspace create --cwd /path/to/project --label api --no-focus
herdr worktree create --cwd /path/to/repo --branch feature/name --no-focus --json
```

After creating or opening a delivery worktree, best-effort bootstrap the delivery navigator so a newly spawned agent can continue without prior chat context:

```bash
# Linear optional at start
delivery --cwd <worktree-path> bootstrap --slug <feature-slug> --goal "<operator ask>"
# or with issue:
delivery --cwd <worktree-path> bootstrap --issue NOD-123 --goal "..."
```

Then prompt the worktree agent with `/delivery:bootstrap` or: read `.delivery/AGENT_BRIEF.md`, run `delivery show && delivery check -v`, continue from the recommended next step. If `delivery` is unavailable, skip without failing the Herdr operation.

Parse every returned workspace, tab, pane, and worktree handle. Do not predict them.

## Safety rules

- Do not run bare `herdr`; it launches or attaches the TUI.
- Use `herdr --help`, bare command groups, and nested `--help` for discovery. Do not probe a mutating command by omitting arguments; some create commands execute with defaults.
- Use `--current` only with real managed-pane context. Otherwise pass explicit IDs.
- Use `--no-focus` for background panes, tabs, workspaces, and worktrees unless focus was requested.
- Inspect before waiting, and read output after waits.
- Do not close, move, rename, stop, delete, or take over resources you did not create unless the user explicitly asks.
- Never run `herdr server stop`, `herdr session stop`, or `herdr session delete` without explicit intent to stop that scope and its processes.
- Treat plugin install/uninstall/enable/disable/action invocation and integration install/uninstall as state-changing operations.
- Use named test sessions for experiments that need isolation; do not kill the main Herdr process.
