---
name: session-cleanup
description: Tear down a finished work session. Inventory owned PRs, schedules, and agents, run the worktree-cleanup script for each worktree (lab claim, demos, Paseo workspace, remote branch), then delete leftover schedules and standalone agents. Use when a PR has merged and the worktree is done, when the user says "cleanup", "clean up", "tear down", "release the lab", "archive this session", or asks to remove worktrees, agents, or demos.keramos.tech prototypes left over from completed work. Also use proactively when finishing work that claimed a lab, published a demo, or spawned child workspaces.
user-invocable: true
---

# Session cleanup

Worktree, lab, demo, workspace, and branch teardown is `worktree-cleanup`'s
script, which runs the steps in the one safe order and refuses when that would
lose state. Do not release a lab, delete a demo, remove a worktree, archive a
workspace, or delete a branch by hand. This skill covers what the script does
not: deciding what the session owns, and the schedules and agents outside any
workspace.

## Step 0 — Inventory

Enumerate what this session owns before running anything:

- PRs: include unresolved PRs owned by this session and its children, even
  when their original branch or worktree is gone. Use existing task notes,
  handoffs, and GitHub state as well as the current branch. Highlight each
  remaining PR's URL, status, next step, and owner before archival; usually
  retain the session or leave an explicit handoff while that work remains.
  Cleanup alone does not authorize merging or closing those PRs.
- Worktrees: this one, plus each child workspace (`paseo workspace ls --json`,
  matched by path and by what this session created) and unmanaged child
  worktrees (`git worktree list`).
- Standalone agents (`paseo ls --json`) and schedules or heartbeats this
  session created (`paseo schedule ls`, `list_schedules`). A surviving
  schedule keeps spawning agents after the session is gone.

## Step 1 — Run the script per worktree

For each worktree whose PR has merged, or that the operator told you to
abandon, run `worktree-cleanup` (`skill://worktree-cleanup`):

```sh
python3 ~/.agents/skills/worktree-cleanup/scripts/worktree_cleanup.py --workspace <child-workspace-id>
```

Use `--path <dir>` for an unmanaged worktree. The script releases the lab
claim, removes the demos, archives the workspace, and deletes the remote
branch. Releasing a lab needs the lab-manager release conditions: merge plus
the operator's agreement that the work is complete, or an explicit instruction
to abandon. A generic cleanup request for a PR still under review does not
meet them, and the script refuses it. Report that PR and its preserved lab
claim instead. Pass `--abandon <reason>` only on an explicit operator
instruction to discard the work.

Act on the exit code as `worktree-cleanup` documents it. Exit 4 from inside
this session's own worktree means the archive is deferred: finish Step 2,
report the printed `resume` command as the final action, and let the operator
or orchestrator run it. Run it yourself only when the user asked you to clean
up including yourself, and only as the last action, after the report.

## Step 2 — Leftovers the script does not cover

- Archive standalone child agents that no archived workspace owned
  (`archive_agent` / `paseo archive <id>`). Archiving interrupts a running
  agent. Note any that were mid-task.
- Delete the schedules and heartbeats this session created.

## Report

End with a short accounting taken from each script report: unresolved owned
PRs and their next steps and owners, labs released (or preserved and why), demos
removed, worktrees and branches removed, anything in `remaining`, schedules and
agents removed, anything dirty or unreachable that was left in place, and the
`resume` command or workspace ID awaiting archival.
