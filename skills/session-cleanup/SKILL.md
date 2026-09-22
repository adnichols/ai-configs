---
name: session-cleanup
description: Tear down a finished work session in the correct order — release claimed labs, remove published clickable-prototype demos, remove child worktrees and agents, then archive the Paseo session. Use when a PR has merged and the worktree is done, when the user says "cleanup", "clean up", "tear down", "release the lab", "archive this session", or asks to remove worktrees, agents, or demos.keramos.tech prototypes left over from completed work. Also use proactively when finishing work that claimed a lab, published a demo, or spawned child workspaces.
user-invocable: true
---

# Session cleanup

Tear down a finished session's resources in a fixed order. The order is not
arbitrary — each step depends on state the previous step leaves intact:

1. **Release lab claims and demos first.** The lab release command reads the
   bearer credential from `.ccore/lab-claim.json` inside the worktree, and a
   published clickable prototype's run name, account, and URL live in `run.md`
   or the prototype note in the worktree's evidence area. Once the worktree is
   gone, the claim can no longer be released from here and the demo's identity
   is lost — the lab stays accounted to a dead checkout and the demo keeps
   serving a stale prototype.
2. **Remove child worktrees and agents second.** Children must go before the
   session record that owns them; archiving a workspace is also what removes a
   Paseo-managed worktree.
3. **Archive the session last.** Archiving interrupts the agent and its
   terminals. Anything left undone at this point stays undone, so this is
   always the final action — and an agent cannot remove the worktree it is
   running in, so self-archival is a handoff unless explicitly requested.

## Step 0 — Inventory

Before deleting anything, enumerate what this session actually owns:

- Lab claims: `.ccore/lab-claim.json` in this worktree and in each child
  worktree (`git worktree list` for unmanaged children).
- Published demos: `run.md` and prototype notes under the worktree's evidence
  area (for example `artifacts/verified-build/<run-id>/`) record each
  clickable prototype's unique run name, Nodaste Labs account, and
  `demos.keramos.tech` URL.
- Paseo state: `paseo workspace ls --json` and `paseo ls --json` (or the
  `list_workspaces` / `list_agents` tools). Identify the current workspace by
  matching its path to the working directory, and child workspaces/agents this
  session created.
- Schedules and heartbeats this session created (`paseo schedule ls`,
  `list_schedules`). A surviving schedule keeps spawning agents after the
  session is gone — delete them as part of teardown.
- Dirty state: `git status` in each worktree. Uncommitted work is the user's;
  never remove a dirty worktree without surfacing it first.

## Step 1 — Release lab claims and demos

Follow the `lab-manager` skill's release conditions and release command
verbatim: release only after all PRs using the lab have merged and the
operator has explicitly agreed the work is complete, or after an explicit
instruction to abandon the work. A generic cleanup request that arrives while
a lab is still awaiting review does not authorize release — preserve the
claim, record its identity, and report it instead of releasing.

Run the release from the worktree that holds the claim, before that worktree
is removed. The manager removes `.ccore/lab-claim.json` only after confirming
the release. If the manager is unreachable, report the unreleased claim and
continue with worktree cleanup — do not claim the release succeeded, and do
not delete the claim file by hand.

### Published clickable prototypes

A cleanup request is the operator-requested removal that `verified-build`
requires before deleting a published demo — but only for demos this session
published. `verified-build` is Codex-only and documents publishing, not
removal, so the teardown steps live here.

For each demo recorded in `run.md` or the prototype note:

- Delete the worker with `npx wrangler delete --name <worker-name>` in the
  Nodaste Labs account (`e6d3e575b97001f8ad1a7e98e497afa5`). Removing the
  worker removes its `<run-name>.demos.keramos.tech` custom domain with it.
- Verify the demo URL no longer serves the prototype (curl it).
- Never touch another run's demo or the parent domain.

Demos can outlive the worktree — if `run.md` is already gone, inventory
candidates with `wrangler` in that account filtered to
`*.demos.keramos.tech`, then confirm each candidate against the session's
PRs and handoffs before deleting. `wrangler list` and `deployments list` do
not show custom domains, so when CLI listing is insufficient use the
Cloudflare dashboard or API for that account. Never bulk-delete by prefix.

## Step 2 — Remove child worktrees and agents

For each child this session created:

- **Paseo-managed workspaces:** archive them with `archive_workspace` or
  `paseo workspace archive <workspace-id>`. Archiving a workspace also
  archives the agents and terminals it owns, and removes the owned worktree
  once its last active workspace reference is archived — do not also run
  `git worktree remove` on the same path or separately archive its agents.
- **Standalone child agents** (not owned by an archived workspace): archive
  them (`archive_agent` / `paseo archive <id>`). Archiving interrupts a
  still-running agent; that is the intended behavior once cleanup has been
  requested, but note any agent that was mid-task in the final report.
- **Unmanaged git worktrees:** verify `git status` is clean, then
  `git worktree remove <path>`. If it is dirty, stop on that worktree and
  report what is uncommitted — cleanup must not silently destroy work.
- Delete any schedules or heartbeats the session created.

## Step 3 — Archive the session

Distinguish who is being cleaned up:

- **Orchestrator cleaning a child session:** archive the child's workspace
  (`archive_workspace` / `paseo workspace archive <workspace-id>`). This is a
  normal operation and completes the teardown.
- **Agent cleaning up after itself:** an agent cannot remove the worktree it
  is running in, and archiving its own workspace terminates the session
  mid-report. By default, finish every other step, then report the workspace
  ID and state that the session is ready to archive — the operator or
  orchestrator performs the final archive. Only when the user explicitly asks
  the agent to archive its own session ("archive this session", "clean up
  including yourself") should it call `archive_workspace` on its own
  workspace — as the literal final action, after the report is written.

## Report

End with a short accounting: labs released (or preserved and why), demos
removed, worktrees and agents removed, schedules deleted, anything dirty or
unreachable that was left in place, and the workspace ID awaiting archival if
self-archival was not requested.

## Outside Paseo

The same order applies without Paseo: release labs first, then clean
`git worktree remove` for child worktrees, then let the operator close the
session. Skip the Paseo-specific steps when no daemon is reachable.
