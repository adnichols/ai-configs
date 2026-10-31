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
python3 ~/.agents/skills/worktree-cleanup/scripts/worktree_cleanup.py --workspace <workspace-id> --path <worktree>   # the record at the worktree path is the fallback when the id matches nothing; the path must be the recorded worktree root
python3 ~/.agents/skills/worktree-cleanup/scripts/worktree_cleanup.py --show-record <worktree-or-workspace-id>      # prints the cleanup record; changes nothing
```

Stdout is one JSON report. Stderr is progress. Re-running is always safe: each step probes the real system (claim file, Cloudflare, `paseo workspace ls`, `git ls-remote`) and reports `already_done` when there is nothing left. The workspace step archives a Paseo workspace only when `paseo workspace ls` lists the recorded id with a `cwd` equal to the worktree path. A listed id with another `cwd` is left alone.

## Order

1. **preflight.** Refuses, with exit 2 and nothing changed, on uncommitted changes (untracked files included, ignored files not), a branch whose head is not contained in the head of a merged PR from this repository (GitHub compare reports `ahead_by` 0; a stack landing adds a merge-main commit after the worker's head, and that still passes) or is also the head of an open PR, any other PR named in the lab claim that is not merged, a running agent in the worktree, a detached HEAD, the default branch, a locked worktree, or the main checkout. It also records what only the worktree knows (claim id and lab, never the credential; demo identities) in `~/.local/state/worktree-cleanup/` so a re-run can finish after the worktree is gone.
2. **lab.** Runs the repo's own `lab -- release` from the worktree, then confirms the claim is gone from the manager. A failed release stops everything and keeps the claim file. A release the manager reports as accounting only (`deprovisioning: false`) succeeds and is listed in `remaining` for the operator; agents do not run `lab deprovision`.
3. **demos.** Deletes each worker and `<run>-feedback` D1 database listed in `artifacts/verified-build/*/demos.json`, in the Nodaste Labs account only. It exports the D1 database first. An entry written by another worktree or branch, with a mismatched name, or a `*.demos.keramos.tech` URL in a run note with no manifest entry is recorded as an unresolved demo and reported in `remaining`, never guessed at. Every run re-checks each unresolved demo against the Labs account (the Worker and R2 bucket lists over the REST API with wrangler's own token, because wrangler cannot list Workers and stops `r2 bucket list` at 20 buckets, following every cursor and reading the default and EU jurisdictions; `wrangler d1 list`). The API call never follows a redirect and accepts only an https endpoint. A demo is cleared from the record when no worker, D1 database or R2 bucket is named `<run>` or starts `<run>-` (so `<run>-builder-lab017` counts) or equals a worker or D1 name its manifest entry declared. A malformed run name (not a string, or not `[a-z0-9][a-z0-9-]*`) is never cleared, and an account listing that fails, is malformed or is cut short fails the step with the record unchanged. A record written before the manifest's declared names were kept is matched by run name alone, plus the names its manifest still declares when that file exists. `--demo-removed <run>` (repeatable) is the strict form for a demo removed by hand: it refuses, before anything changes, while the account still holds a matching name (`REFUSE-DEMO-PRESENT`) or when the record holds no such unresolved demo (`REFUSE-NO-SUCH-DEMO`), and otherwise the run clears it. A plain re-run clears the same demo without the flag.
4. **workspace.** Archives the Paseo workspace, or runs `git worktree remove` (never `--force` unless abandoning) when none owns the path. Inside the target worktree it defers this step instead, because archiving ends the calling session.
5. **remote_branch.** Deletes `origin/<branch>` with a lease on the remote tip. It deletes only when that tip is the recorded head or the head of a merged PR that contains it, and keeps the branch and reports it when the remote tip is anything else, an open PR is based on or still comes from it, or the PR never merged (`--abandon`), since the branch is then the only copy of that work. The local branch is never deleted.

## Exit codes

| Code | Meaning | What to do |
| --- | --- | --- |
| 0 | Complete. | Nothing. |
| 2 | Refused; nothing changed. | Read `error`. Fix the cause and run it again. Do not ask the operator to release the lab. |
| 3 | A step failed; later steps did not run. | Read `error`, fix, run the same command again. |
| 4 | Done with what this process may do; `remaining` lists work for others. | Run each `remaining[].command` whose `owner` is you. Report the rest. |

`remaining` is built by the run that does the work, so record it from that report: a rerun sees nothing left to do and exits 0. `resume` in the report is the exact command that finishes the job. A worker that runs the script from inside its own worktree gets exit 4 with the archive deferred to the `orchestrator`. The orchestrator runs `resume` (or `--workspace <id>`) from outside. An orchestrator may also run the whole script itself for a child worktree.

## Refusal codes

A refusal (exit 2) puts a stable code in the report's `code` field (`null` otherwise) and prints `<code>: <error>` on stderr. Match the code, never the `error` text.

| Code | Cause |
| --- | --- |
| `REFUSE-GONE-NO-RECORD` | The worktree is gone and no cleanup record names it. |
| `REFUSE-UNKNOWN-WORKSPACE` | `--workspace` names an id paseo does not list and no record holds, and `--path` is absent or has no record at that worktree path. |
| `REFUSE-TARGET-CONFLICT` | `--workspace` resolves to a different worktree than `--path`, or the id fell back to the record at `--path` while another workspace now uses that path or the live worktree is not the recorded one. A worktree is recorded with a random token kept in its git admin directory, so a worktree removed and recreated at the same path (even on the same branch) is refused; run with `--path` alone to clean it deliberately. |
| `REFUSE-NOT-WORKTREE`, `REFUSE-MAIN-CHECKOUT`, `REFUSE-LOCKED` | The path is not a linked git worktree, is the main checkout, or is locked. |
| `REFUSE-NO-REPO` | The GitHub repository cannot be resolved. |
| `REFUSE-PASEO-UNAVAILABLE` | `--workspace` was given, or the worktree is under the Paseo home, and `paseo workspace ls` fails. A failed listing is never read as the workspace being gone. |
| `REFUSE-CLAIM-MALFORMED` | `.ccore/lab-claim.json` cannot be parsed. |
| `REFUSE-PREFLIGHT` | Dirty, unmerged, open-PR, running-agent or lab-claim checks failed; `error` lists them. |
| `REFUSE-PRESERVE-FAILED` | `--abandon` could not save the unpushed commits. |
| `REFUSE-NO-RECORD` | `--show-record` found no record. |
| `REFUSE-DEMO-PRESENT` | `--demo-removed <run>` named a demo for which the Labs account still holds a worker, D1 database or R2 bucket; `error` names each. |
| `REFUSE-NO-SUCH-DEMO` | `--demo-removed <run>` named a run the cleanup record does not hold as an unresolved demo. |
| `REFUSE-AMBIGUOUS-RECORD` | More than one cleanup record holds the workspace id (an id reused for another worktree). Name the record by `--path`. |

## Reading a record

`--show-record <path|workspace-id>` prints the cleanup record as one JSON object (`path`, `repo`, `branch`, `head`, `workspace_id`, `pr`, `claims`, `demos`, `merged_heads`, and the rest) and exits 0, or exits 2 with a report whose `code` is `REFUSE-NO-RECORD`. It takes no other option. Callers read `workspace_id` from it instead of locating the state directory themselves.

## Authority

Running the script releases the lab claim. Run it as soon as the work using the lab is done: every PR using the lab has merged, or the work is abandoned or concluded without a merge. No operator agreement is needed and no agent asks for it. Keep the lab while a PR using it is open or a prototype review is pending; the script refuses an open PR on its own. `--abandon <reason>` marks work concluded without a merge (`NOT_REPRODUCED`, `EXPECTED_BEHAVIOR`, duplicate, won't fix, superseded, or abandoned). It overrides the dirty, unpushed, and unmerged checks and nothing else, so never use it to get past an open PR or a pending prototype review. It saves a patch, untracked files, and a bundle of unpushed commits under the state directory first and lists them in `preserved`. If the claim file is lost, release your own orphaned claim through the lab-manager's agent release path (see the ccore2 lab-manager skill), not through the operator.

**Stale claim file.** When `lab release` fails with `claim_credential_invalid`, the script runs `lab inspect <lab>`. If the manager answers cleanly and the claim id in `.ccore/lab-claim.json` is not the lab's live holder (another claim holds the lab, the lab has no claim, or that claim is already released), the file is a leftover of a claim the manager already ended. The script moves it, content intact, to `~/.local/state/stale-lab-claims/<worktree-name>-<claim-id>.json` (never deletes it), marks the claim released in the cleanup record, reports the `lab` step as `done` with the note `stale claim file moved aside` (claim id and current holder id), and continues with demos, workspace, and branch. A re-run finds no claim file and reports `already_done`. If the file's claim id is the live holder, or `lab inspect` fails or is unreadable, nothing changes: the step fails as for any other release failure and the claim file stays. A live claim is never treated as released.

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
