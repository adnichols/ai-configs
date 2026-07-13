---
name: herdr
description: "Control Herdr, a terminal multiplexer for coding agents. Use when the user explicitly mentions Herdr or asks to inspect or control Herdr panes, tabs, workspaces, terminals, commands, or communication with another agent. The CLI may be used from inside or outside a Herdr-managed pane when it can reach the running Herdr session; HERDR_ENV is context, not a prerequisite. Do not use merely because a task could benefit from a background terminal, delegation, or parallel work."
---

# Herdr

Herdr is a terminal multiplexer and runtime for coding agents. It organizes terminals into workspaces, tabs, and panes, detects agent identity and status, and exposes the running session through the `herdr` CLI.

The `herdr` binary talks to the running session over its local control channel. It can do this from a Herdr-managed pane or from an ordinary terminal. Do not gate Herdr use on `HERDR_ENV=1`, and do not stop merely because that variable is absent.

Treat `HERDR_ENV` only as caller-context information:

- When `HERDR_ENV=1` and the `HERDR_WORKSPACE_ID`, `HERDR_TAB_ID`, and `HERDR_PANE_ID` variables are present, current-pane shortcuts are available.
- When those variables are absent, operate from outside the managed session: discover live state with non-mutating list/get commands and use explicit returned IDs.
- If the CLI reports that no Herdr server, socket, or session is reachable, report that actual error. Do not infer failure from environment variables alone.

Do not set or fake `HERDR_ENV=1` globally. That value claims the shell has a real managed-pane context and is only useful together with the IDs Herdr injects.

## Learn the current CLI

The installed binary is the authority for command syntax. Begin with:

```bash
herdr --help
```

Then print the relevant command group by running it without a subcommand:

```bash
herdr pane
herdr workspace
herdr worktree
herdr tab
herdr wait
herdr terminal
herdr notification
herdr integration
herdr session
```

Do not run bare `herdr` for discovery; it launches or attaches the TUI. Do not probe a mutating nested command by omitting arguments; some commands, including `herdr workspace create`, are valid with defaults and will execute. Use the command-group output above instead.

Most control commands print JSON. Read identifiers and state from those responses instead of predicting either one.

## IDs and current context

Public IDs are short stable handles:

- workspace: `w1`
- tab: `w1:t1`
- pane: `w1:p1`
- terminal: `term_...`

The encoded suffix can contain letters and can grow beyond one character. Treat every ID as an opaque string.

Closed tab and pane IDs are not reused and do not retarget later resources. A pane moved into another workspace receives a new public pane ID. Re-read create, split, move, list, or get responses after mutations; never construct an ID from a workspace or display number.

Herdr injects stable caller context into managed panes:

```bash
printf '%s\n' "$HERDR_WORKSPACE_ID" "$HERDR_TAB_ID" "$HERDR_PANE_ID"
```

When that context is present, prefer `--current` when a pane command should target the calling pane. Omitting a target can use the UI-focused pane, which may belong to the user or another client.

From outside a managed pane, do not use `--current` or empty `HERDR_*_ID` variables. Discover the focused workspace and live pane IDs, then pass an explicit target:

```bash
herdr workspace list
herdr tab list --workspace <workspace-id>
herdr pane list --workspace <workspace-id>
herdr pane get <pane-id>
```

Read the focused workspace, active tab, and pane IDs from command responses rather than assuming the external shell has a current pane.

## Control agents through panes

An agent runs inside a pane. Use the pane ID as the control target for agents, shells, servers, tests, and logs. This keeps spawning, input, reads, waits, and cleanup on one stable control surface.

Use workspace and tab commands for organization. Use worktree commands only when you intentionally want Herdr to create, open, or remove a Git checkout.

Pane records expose `agent`, `agent_status`, and native session metadata when available. Agent status is `idle`, `working`, `blocked`, `done`, or `unknown`.

`idle` and `done` are the same underlying semantic state with different attention state:

- `idle`: the agent is waiting and its result is considered seen.
- `done`: the agent finished and its result has not been seen.

An agent that first opens at its prompt reports `idle`, including in a background pane. After a working or blocked agent completes, it reports `done` when its tab or workspace is in the background. It reports `idle` when it completes in the active tab while the foreground client is focused. If the foreground client is explicitly unfocused, completion can become `done` even in the active tab.

Focusing a pane, switching to its tab, or regaining outer terminal focus marks the visible tab as seen, so `done` becomes `idle`. Switching away does not turn an existing `idle` status into `done`; `done` is created by a later completion while the pane is unseen. With no foreground client, a new completion in the globally active tab is treated as seen while completions in background tabs still become `done`.

## Start agents interactively

Default to a sibling pane in the relevant tab and current working directory. Do not create a workspace, tab, worktree, or different cwd unless the user explicitly requests that topology or location.

Inside a managed pane, the relevant pane is the caller. Outside Herdr, identify the UI-focused workspace and active tab from list responses, then select the intended pane explicitly. If discovery does not distinguish a safe target, ask the user which pane to use before mutating state; do not reject the task merely because the caller is external.

Honor a direction requested by the user. Otherwise inspect the target pane's current rectangle:

```bash
herdr pane layout --pane <target-pane-id>
```

Split a wide pane to the right and a narrow or tall pane down. Avoid repeated same-direction splits that would create unusably narrow columns or short rows. Keep the user's focus in the existing pane:

```bash
herdr pane split <target-pane-id> --direction right --no-focus
```

When running inside Herdr, `<target-pane-id>` may be replaced with `--current`. Replace `right` with `down` when the layout calls for it.

Read `result.pane.pane_id` from the JSON response. Give the pane a useful label, then start the requested agent by running only its normal executable so its interactive TUI opens:

```bash
herdr pane rename <returned-pane-id> "reviewer"
herdr pane run <returned-pane-id> "codex"
```

Use the executable that belongs to the requested agent:

- Codex: `codex`
- Claude Code: `claude`
- pi: `pi`
- OpenCode: `opencode`
- OMP: `omp`

Do not pass the task as an argv prompt by default. Do not add non-interactive flags. Only change the normal interactive launch when the user explicitly asks for a different launch mode or command.

Inspect the pane after launch. If `agent_status` is not yet `idle`, wait for the idle transition. Once it is idle, submit the task with `pane run`:

```bash
herdr pane get <returned-pane-id>
herdr wait agent-status <returned-pane-id> --status idle --timeout 30000
herdr pane run <returned-pane-id> "Review the current diff and report only actionable findings."
```

Status waits match the current status immediately or wait for a future matching transition.

`pane run` sends the text and Enter together. Use it for initial prompts and follow-ups instead of coordinating `send-text` and `send-keys` separately.

For normal background work, wait for the agent to start working. If the pane remains in a background tab or workspace, wait for `done` before reading its transcript:

```bash
herdr wait agent-status <returned-pane-id> --status working --timeout 30000
herdr wait agent-status <returned-pane-id> --status done --timeout 120000
herdr pane read <returned-pane-id> --source recent-unwrapped --lines 120
```

If the user is watching that tab, completion reports `idle` instead, so wait for `idle`. Always treat either `idle` or `done` as completed when inspecting `pane get`; the difference is whether the result has been seen.

If a wait times out, inspect `herdr pane get <returned-pane-id>` and `pane read` before deciding what to do. A `blocked` agent needs input; an `unknown` pane may not yet contain a detected or integrated agent.

Submit follow-ups the same way:

```bash
herdr pane run <returned-pane-id> "Now check the failing test."
```

## Run an ordinary command in another pane

Split the selected pane using the same geometry rule without moving the user's focus:

```bash
herdr pane split <target-pane-id> --direction right --no-focus
```

Use `--current` instead of an explicit ID only when the caller has real Herdr pane context.

Read the new `pane_id` from the JSON response, then run and inspect the command:

```bash
herdr pane run <returned-pane-id> "just test"
herdr wait output <returned-pane-id> --match "test result" --timeout 120000
herdr pane read <returned-pane-id> --source recent-unwrapped --lines 120
```

Inspect existing output before waiting for future output. A wait timeout exits with status `1`.

Use the read source that matches the task:

- `visible`: the current rendered viewport
- `recent`: recent scrollback as rendered, including soft wraps
- `recent-unwrapped`: recent scrollback with soft wraps joined; prefer it for logs and transcripts
- `detection`: the bottom-buffer snapshot used by agent detection

Use `--format ansi` when colors and terminal styling are evidence. Otherwise use text.

If the user explicitly asks for another tab, workspace, or worktree, discover that command group and use returned IDs. Do not infer a larger topology from a request to start an agent or command.

## Safety and coordination rules

- Use `--no-focus` for background work unless the user asked to switch context.
- Use `--current` only with real managed-pane context; otherwise discover and pass an explicit ID. Do not rely blindly on another client's focused pane.
- Parse IDs from JSON responses. Do not derive them from sidebar order or examples.
- Inspect before waiting. Read current output first, then wait for the next state or output you expect.
- Do not close workspaces, tabs, panes, or sessions you did not create unless the user explicitly asked.
- Never run `herdr server stop` from an active session unless the user explicitly intends to stop the server and its pane processes.
- Never kill the main Herdr process. Use named test sessions for experiments that need an isolated server.
