---
name: worktree-cleanup
description: Tear down a finished worktree with one idempotent script that releases its lab claim, removes its published demos, archives its Paseo workspace, and deletes its remote branch, in that order. Use after every PR merge, when abandoning work, and whenever someone says cleanup, clean up, tear down, release the lab, archive the workspace, or remove the worktree. Run it instead of any hand-typed gh --delete-branch, git worktree remove, archive_workspace, or lab release.
user-invocable: true
---

# Worktree cleanup

`scripts/worktree_cleanup.py` is the only supported way to tear down a worktree. Merging never deletes anything. `gh pr merge --delete-branch` also removes the local branch's checked-out worktree, and the lab claim file inside it, before the lab can be released. Never pass `--delete-branch`, and never run `git worktree remove`, `git branch -d`, `paseo workspace archive`, `archive_workspace`, or `lab release` by hand for cleanup. The script runs them in the one safe order and refuses when that would lose state.

```sh
python3 ~/.agents/skills/worktree-cleanup/scripts/worktree_cleanup.py            # from inside the worktree
python3 ~/.agents/skills/worktree-cleanup/scripts/worktree_cleanup.py --workspace <workspace-id>   # from anywhere
python3 ~/.agents/skills/worktree-cleanup/scripts/worktree_cleanup.py --path <worktree>
```

Stdout is one JSON report. Stderr is progress. Re-running is always safe: each step probes the real system (claim file, Cloudflare, `paseo workspace ls`, `git ls-remote`) and reports `already_done` when there is nothing left.

## Order

1. **preflight.** Refuses, with exit 2 and nothing changed, on uncommitted changes (untracked files included, ignored files not), a branch whose head is not the head of a merged PR, any other PR named in the lab claim that is not merged, a running agent in the worktree, a detached HEAD, the default branch, a locked worktree, or the main checkout. It also records what only the worktree knows (claim id and lab, never the credential; demo identities) in `~/.local/state/worktree-cleanup/` so a re-run can finish after the worktree is gone.
2. **lab.** Runs the repo's own `lab -- release` from the worktree, then confirms the claim is gone from the manager. A failed release stops everything and keeps the claim file. A release the manager reports as accounting only (`deprovisioning: false`) succeeds and is listed in `remaining` for the operator; agents do not run `lab deprovision`.
3. **demos.** Deletes each worker and `<run>-feedback` D1 database listed in `artifacts/verified-build/*/demos.json`, in the Nodaste Labs account only. It exports the D1 database first. An entry written by another worktree or branch, with a mismatched name, or a `*.demos.keramos.tech` URL in a run note with no manifest entry is reported in `remaining`, never guessed at.
4. **workspace.** Archives the Paseo workspace, or runs `git worktree remove` (never `--force` unless abandoning) when none owns the path. Inside the target worktree it defers this step instead, because archiving ends the calling session.
5. **remote_branch.** Deletes `origin/<branch>` with a lease on the recorded head. It keeps the branch and reports it when the remote tip moved, or an open PR is based on or still comes from it. The local branch is never deleted.

## Exit codes

| Code | Meaning | What to do |
| --- | --- | --- |
| 0 | Complete. | Nothing. |
| 2 | Refused; nothing changed. | Read `error`. Fix the cause or ask the operator. |
| 3 | A step failed; later steps did not run. | Read `error`, fix, run the same command again. |
| 4 | Done with what this process may do; `remaining` lists work for others. | Run each `remaining[].command` whose `owner` is you. Report the rest. |

`remaining` is built by the run that does the work, so record it from that report: a rerun sees nothing left to do and exits 0. `resume` in the report is the exact command that finishes the job. A worker that runs the script from inside its own worktree gets exit 4 with the archive deferred to the `orchestrator`. The orchestrator runs `resume` (or `--workspace <id>`) from outside. An orchestrator may also run the whole script itself for a child worktree.

## Authority

Running the script releases the lab claim, so run it only when the lab-manager release conditions hold: every PR using the lab has merged and the operator agreed the work is complete, or the operator told you to abandon it. A request to clean up a worktree whose PR is still under review is not that agreement, and the script refuses it anyway. `--abandon <reason>` overrides the dirty, unpushed, and unmerged checks and nothing else. Use it only on an explicit operator instruction to discard the work. It saves a patch, untracked files, and a bundle of unpushed commits under the state directory first and lists them in `preserved`.

## Demo manifest

`verified-build` writes `artifacts/verified-build/<run-id>/demos.json` when it publishes a prototype, so cleanup does not depend on reading prose:

```json
{"demos": [{"run": "<run-name>", "worker": "<run-name>", "d1": "<run-name>-feedback",
            "account": "e6d3e575b97001f8ad1a7e98e497afa5",
            "url": "https://<run-name>.demos.keramos.tech",
            "worktree": "<absolute worktree path>", "branch": "<branch>"}]}
```

Set `d1` to `null` for a static-only demo.

## Outside the script

Pull-request inventory, schedules and heartbeats a session created, and standalone child agents are not covered. See `session-cleanup`.
