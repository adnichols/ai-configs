---
name: herdr
description: "Control and troubleshoot Herdr, the terminal workspace manager for coding agents. Use whenever the user explicitly mentions Herdr or asks to inspect, start, prompt, wait for, read, attach to, rename, or coordinate Herdr agents, panes, tabs, workspaces, worktrees, sessions, integrations, plugins, or runtime state. The CLI works from inside or outside a managed pane when its socket is reachable; HERDR_ENV is context, not a prerequisite. Do not use merely because parallel work might be useful."
---

# Herdr

Herdr is a terminal workspace manager and runtime for coding agents. It organizes terminals into workspaces, tabs, and panes, detects supported agents, and exposes the running session through the `herdr` CLI.

Prefer the agent-native commands. Use `herdr agent ...` for supported coding agents and `herdr pane ...` for generic terminals, processes, layout, and raw output.

The installed binary is the syntax authority. Read [references/cli.md](references/cli.md) when the task needs broad command discovery, lifecycle/configuration commands, or a complete command-group map. `herdr --skill` dumps upstream's inside-pane skill; keep this repo override, which allows a reachable socket from outside a managed pane.

When the request transfers live work to another agent, load `skill://herdr-agent-handoff` before creating or opening any destination session, worktree, workspace, tab, or pane. The handoff skill owns the default new-session-plus-new-worktree topology, same-host and remote routing, runtime and model fidelity, context transfer, callback availability, and ownership change. This skill remains the CLI and resource-control authority.

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

Suffixes may contain letters or multiple characters. Parse IDs from JSON responses; never derive them from display order or examples. Closed handles are not reused. After `pane move`, continue with `.result.move_result.pane.pane_id` or the live agent name; `.result.move_result.previous_pane_id` is not a general target. Re-read mutation responses and refresh state before later actions.

Creation responses expose the next IDs: `workspace create` returns `.result.workspace`, `.result.tab`, and `.result.root_pane`. `tab create` returns `.result.tab` and `.result.root_pane`. `pane split` returns `.result.pane`.

## Prefer the agent control surface

`herdr agent` targets a unique agent name or a pane ID currently hosting an agent. It does not accept terminal IDs or bare kind labels. Names must match `[a-z][a-z0-9_-]{0,31}` and be unique among live agents. A name follows the current pane occupant and is cleared when that agent exits, is released, or is replaced.

Discover agents and inspect one:

```bash
herdr agent list
herdr agent get <agent-name-or-pane-id>
herdr agent read <target> --source recent-unwrapped --lines 120
```

Agent states are `idle`, `working`, `blocked`, `done`, and `unknown`:

- `idle`: ready for input, and the tab has been seen in the focused Herdr UI.
- `done`: the same underlying idle state after unseen background work finishes.
- `blocked`: Herdr recognized an approval or question UI.
- `working`: actively processing.
- `unknown`: an agent is present but Herdr cannot classify it confidently; it does not prove completion.

Focusing the tab, or targeting the pane/agent with a focus command, marks it seen. CLI reads do not. Treat `idle` and `done` as settled. Do not require only one of them unless the task depends on attention state.

### Signal workflow-owned operator waits

Use the installed `herdr-operator-attention` helper when an authorized workflow needs human action outside Pi's own blocking UI, such as a password prompt on a shell pane or an execution-stage approval pause:

```bash
herdr-operator-attention set --pane <pane-id> --kind password --message "Enter password to continue"
# run the interactive wait; always clear in finally/trap
herdr-operator-attention clear --pane <pane-id>
herdr-operator-attention status --pane <pane-id>
```

The helper writes a per-pane marker under `${HERDR_OPERATOR_WAIT_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/herdr-operator-wait}` for Pi's authoritative reporter and best-effort calls `pane report-agent` for shell-only panes. It uses fixed source `workflow:operator-attention` and agent `operator-wait`. Herdr CLI/socket failures do not fail the helper after marker I/O succeeds; marker write/delete failures remain non-zero. Prefer Pi's normal `ctx.ui` input/confirm methods when the interaction already lives inside Pi because the integration reports those blocks automatically.

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

Split wide panes right and narrow/tall panes down. Avoid repeated same-direction splits that create unusable columns or rows. Keep user focus in place and preserve the intended working directory:

```bash
herdr pane split --current --direction right --cwd "$PWD" --no-focus
# or, outside managed context:
herdr pane split <pane-id> --direction right --cwd <path> --no-focus
```

Read `result.pane.pane_id` from the JSON response. The pane must be at its interactive shell prompt, with the shell in the foreground. Then use the readiness-aware launcher rather than typing the executable:

```bash
herdr agent start reviewer --kind codex --pane <new-pane-id> --timeout 30000
```

Supported kinds are listed by `herdr agent` and `herdr agent start --help`. Pass agent-specific argv only after `--` and only when the user requests them.

`agent start` returns only after Herdr detects the expected agent in that same pane and considers it ready. If the agent is blocked during startup, the command returns `agent_not_ready` immediately but keeps the name available for `agent read` and `agent send-keys`. Wait until idle before prompting.

### Prompt and wait

Submit the task with the agent-native prompt command:

```bash
herdr agent prompt reviewer \
  "Review the current diff and report only actionable findings." \
  --wait --timeout 120000
```

`agent prompt` honors live bracketed-paste mode and sends text plus encoded Enter. If the agent is already blocked, submission is rejected with `agent_blocked` before any input is sent. Inspect the blocked UI and ask the user before answering it.

`--wait` matches the first settled `idle`, `done`, or `blocked` state. Do not repeat those defaults with `--until`. Use `--until` only for a state-specific wait. Always pass a timeout for automated coordination.

A prompt sent from a non-working state must produce an observed lifecycle change within five seconds or Herdr returns `agent_prompt_stalled`. This wait tracks lifecycle state, not a conversational turn. If the target is already `working`, completion of the active turn may satisfy it. Avoid sending new work to a working agent unless that behavior is intentional.

Wait without submitting:

```bash
herdr agent wait <target> --timeout 120000
```

Use `--until blocked` (or another single state) only when that is the workflow.

After a wait, inspect state and read the transcript:

```bash
herdr agent get <target>
herdr agent read <target> --source recent-unwrapped --lines 120
```

If a wait fails or returns `blocked`, inspect `agent get` and `agent read` before sending more input. Use logical keys for interactive agent UI:

```bash
herdr agent send-keys <target> esc
herdr agent send-keys <target> ctrl+c
```

Herdr validates all keys before writing any bytes.

If increasing `--lines` does not reveal more of a completed response, the pane is probably on the terminal alternate screen; those rows do not enter Herdr host scrollback. As a fallback, ask the agent to write its complete response as Markdown in a temp directory and reply with only the file path, then read the file. Do not request file output in the initial prompt.

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

`pane run` atomically sends command text and Enter. `pane wait-output` searches the selected snapshot immediately, including existing output, and then polls. Literal matching uses `--match`; Rust regex matching uses `--regex`.

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
herdr worktree create --cwd /path/to/repo --branch feature/name --no-focus
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
- CLI server errors are JSON on stderr with exit status 1. CLI syntax errors exit with status 2.
