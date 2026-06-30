---
name: herdr
description: "Use when running inside herdr (HERDR_ENV=1) to inspect and coordinate agent sessions, panes, tabs, workspaces, and waits through the herdr CLI. Do not use from outside herdr."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [herdr, agents, panes, terminal, coordination]
    related_skills: [pi-coding-workflow, pi-tmux-event-bridge, subagent-driven-development]
---

# herdr

## Overview

herdr is a terminal-native agent multiplexer. It provides workspaces, tabs, and panes, where each pane is a real terminal running a shell, agent, server, test job, or log stream. The `herdr` CLI talks to the running herdr instance over a local Unix socket.

Use this skill to coordinate agent sessions from inside herdr: discover panes, read neighboring agents, split panes, run commands, wait for output, and wait for agent status changes.

## Environment Check

`HERDR_ENV=1` means this shell is itself running inside a herdr-managed pane, but it is **not required** for managing herdr sessions. You may still use the `herdr` CLI from outside a herdr pane as long as the CLI can reach the running herdr instance over its local Unix socket.

Check it for context, not as a hard gate:

```bash
printf '%s\n' "$HERDR_ENV"
```

If herdr commands fail because no socket/session is available, report that directly and do not invent pane state.

## Core Concepts

- **Workspace**: project context containing one or more tabs. IDs look like `1`, `2`.
- **Tab**: subcontext inside a workspace. IDs look like `1:1`, `1:2`.
- **Pane**: terminal split inside a tab. IDs look like `1-1`, `1-2`.
- **Agent status**: detected by herdr as `idle`, `working`, `blocked`, `done`, or `unknown`.
- **Important**: IDs can compact when panes/tabs/workspaces close. Never treat IDs as durable. Re-read current IDs before acting.

## Discovery

List panes and identify the focused pane:

```bash
herdr pane list
```

List workspaces:

```bash
herdr workspace list
```

List tabs in a workspace:

```bash
herdr tab list --workspace 1
```

## Reading Panes

Read another pane's current output:

```bash
herdr pane read 1-1 --source recent --lines 80
```

Sources:

- `visible`: current viewport
- `recent`: recent scrollback as rendered
- `recent-unwrapped`: recent terminal text with soft wraps joined; useful for matching or exact transcript review

For TUI feedback loops:

```bash
herdr pane read 1-1 --source recent --lines 80 --ansi
```

## Splitting Panes and Running Commands

Split the current/known pane to the right without stealing focus, parse the new pane ID, then run a command:

```bash
NEW_PANE=$(herdr pane split 1-2 --direction right --no-focus | python3 -c 'import sys,json; print(json.load(sys.stdin)["result"]["pane"]["pane_id"])')
herdr pane run "$NEW_PANE" "npm run dev"
```

Split downward:

```bash
NEW_PANE=$(herdr pane split 1-2 --direction down --no-focus | python3 -c 'import sys,json; print(json.load(sys.stdin)["result"]["pane"]["pane_id"])')
```

Close a pane:

```bash
herdr pane close 1-3
```

## Waiting

Wait for output:

```bash
herdr wait output 1-3 --match "ready on port 3000" --timeout 30000
```

Regex wait:

```bash
herdr wait output 1-3 --match "server.*ready" --regex --timeout 30000
```

Wait for another agent's status:

```bash
herdr wait agent-status 1-1 --status done --timeout 120000
```

Timeout exits with code `1`. After a successful wait, read the pane before summarizing.

## Sending Text and Keys

Send text without Enter:

```bash
herdr pane send-text 1-1 "hello"
```

Send keys:

```bash
herdr pane send-keys 1-1 Enter
```

Run a command/message (text + Enter):

```bash
herdr pane run 1-1 "echo hello"
```

## Tabs and Workspaces

Create a tab:

```bash
herdr tab create --workspace 1 --label "logs"
```

Focus, rename, close:

```bash
herdr tab focus 1:2
herdr tab rename 1:2 "logs"
herdr tab close 1:2
```

Create a workspace:

```bash
herdr workspace create --cwd /path/to/project --label "api server"
```

Create without focusing:

```bash
herdr workspace create --cwd /path/to/project --no-focus
```

Focus, rename, close:

```bash
herdr workspace focus 2
herdr workspace rename 1 "api server"
herdr workspace close 2
```

## Agent Session Workflow

1. Gate on `HERDR_ENV=1`.
2. Run `herdr pane list` and identify your focused pane plus target agent panes.
3. Read target panes with `pane read --source recent --lines 80`.
4. If waiting for a running agent, use `wait agent-status ... --status done`, then read output.
5. If launching support work, split with `--no-focus`, parse the new pane ID from JSON, run the command, wait for expected output, then read the result.
6. Re-list panes before any later action; do not reuse stale IDs blindly.

## Recipes

### Run a server and wait until ready

```bash
NEW_PANE=$(herdr pane split 1-2 --direction right --no-focus | python3 -c 'import sys,json; print(json.load(sys.stdin)["result"]["pane"]["pane_id"])')
herdr pane run "$NEW_PANE" "npm run dev"
herdr wait output "$NEW_PANE" --match "ready" --timeout 30000
herdr pane read "$NEW_PANE" --source recent --lines 40
```

### Run tests in a separate pane

```bash
NEW_PANE=$(herdr pane split 1-2 --direction down --no-focus | python3 -c 'import sys,json; print(json.load(sys.stdin)["result"]["pane"]["pane_id"])')
herdr pane run "$NEW_PANE" "cargo test"
herdr wait output "$NEW_PANE" --match "test result" --timeout 60000
herdr pane read "$NEW_PANE" --source recent --lines 60
```

### Coordinate with another agent

```bash
herdr pane list
herdr wait agent-status 1-1 --status done --timeout 120000
herdr pane read 1-1 --source recent --lines 100
```

### Spawn a new agent pane

```bash
NEW_PANE=$(herdr pane split 1-2 --direction right --no-focus | python3 -c 'import sys,json; print(json.load(sys.stdin)["result"]["pane"]["pane_id"])')
herdr pane run "$NEW_PANE" "claude"
herdr wait output "$NEW_PANE" --match ">" --timeout 15000
herdr pane run "$NEW_PANE" "review the test coverage in src/api/"
```

## Output Formats

- `workspace list/create`, `tab list/create/get`, `pane list/get/split`, `wait output`, and `wait agent-status` print JSON on success.
- `pane read` prints text, not JSON.
- `pane send-text`, `pane send-keys`, and `pane run` print nothing on success.
- `pane split` returns the new pane ID at `result.pane.pane_id`.
- `workspace create` returns `result.workspace`, `result.tab`, and `result.root_pane`.
- `tab create` returns `result.tab` and `result.root_pane`.

## Common Pitfalls

1. **Using herdr outside herdr.** Always check `HERDR_ENV=1` first.
2. **Acting on stale IDs.** IDs can compact. Re-list before actions.
3. **Forgetting `--no-focus`.** Use it when creating support panes so you do not steal focus.
4. **Summarizing after a wait without reading.** Wait only proves a condition happened; read the pane to see the result.
5. **Assuming `pane read --source recent` and waits see the same wrapping.** Wait matching uses unwrapped recent text; use `recent-unwrapped` when exact matching context matters.

## Verification Checklist

- [ ] Confirmed `HERDR_ENV=1` before controlling herdr.
- [ ] Re-read current pane/tab/workspace IDs before acting.
- [ ] Used `--no-focus` for non-interrupting splits/tabs/workspaces.
- [ ] Parsed new pane IDs from JSON instead of guessing.
- [ ] Waited for explicit output/status when coordinating asynchronous work.
- [ ] Read pane output after waits before reporting results.
