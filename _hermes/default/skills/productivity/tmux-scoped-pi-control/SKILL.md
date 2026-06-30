---
name: tmux-scoped-pi-control
description: "Use this whenever you need to stop, restart, clean up, or verify a pi workflow on Aaron's shared machine. This skill exists to prevent collateral damage: never broad-kill pi by name, never kill a whole session/window unless the exact workflow in scope matches, and always use the tmux-scoped kill helper for destructive actions. Trigger on any request involving stopping pi, cleaning up tmux workflows, killing panes, restarting a run, or 'close out' / 'shut down' workflow language."
---

# Tmux Scoped Pi Control

Use this skill before any destructive workflow action involving `pi` on Aaron's machine.

## Hard rule

Never use broad process targeting for `pi`:
- no `pkill -f pi`
- no `killall pi`
- no `pkill`/`kill` by guessed cwd or fuzzy grep alone
- no `tmux kill-session`, `kill-window`, or `kill-pane` unless the exact session/window/pane was already resolved as the workflow in scope

On a shared box, destructive actions must be pane-scoped and metadata-verified.

## Required control surface

Use the scoped helper:

```bash
python3 ~/.hermes/scripts/tmux_scoped_kill_pi.py \
  --pane <pane_id> \
  --expected-session <session_name> \
  --expected-window <window_name> \
  --expected-cwd <repo_or_worktree_path>
```

That command is dry-run by default. It does nothing except print JSON describing the exact `pi` pid it would target.

Only after confirming the JSON matches the intended workflow may you execute:

```bash
python3 ~/.hermes/scripts/tmux_scoped_kill_pi.py \
  --pane <pane_id> \
  --expected-session <session_name> \
  --expected-window <window_name> \
  --expected-cwd <repo_or_worktree_path> \
  --execute
```

## Required sequence

1. Resolve the exact tmux pane id.
2. Read the pane metadata: session, window, cwd, current command.
3. Match all three scope anchors before any destructive action:
   - session
   - window
   - cwd/worktree
4. Run the helper in dry-run mode first.
5. Inspect the JSON and confirm it found exactly one `pi` process in that pane.
6. Run with `--execute` only after the dry-run target is correct.
7. Verify the specific pane/process stopped; do not infer success from unrelated process listings.

## Refusal conditions

Stop and do nothing destructive if any of these are true:
- the pane id is unknown
- session/window/cwd do not all match
- the helper finds zero `pi` processes in the target pane
- the helper finds more than one `pi` process in the target pane
- the request is ambiguous about which workflow is in scope

## Session/window cleanup

After the scoped `pi` process is stopped, only then consider closing the exact pane/window/session tied to that workflow. Do not close shared containers first.

## Output expectation

When reporting a stop/cleanup action, include:
- pane id
- session name
- window name
- cwd/worktree
- exact pid targeted by the helper
- whether the helper ran in dry-run or execute mode
