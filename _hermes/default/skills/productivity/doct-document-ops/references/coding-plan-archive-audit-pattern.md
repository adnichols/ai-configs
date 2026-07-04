# Coding plan archive audit pattern

Use this reference when asked to clean up Doct Coding Plans by identifying completed work, PR-backed work, or merged work and moving those plans to Done/Archived.

## Source-of-truth sequence

1. Confirm production auth/context:
   ```bash
   doct-agent auth status --all --json
   doct-agent context --base-url https://doct.nodaste.com --json
   ```
2. Find the personal workspace and read both board and documents:
   ```bash
   doct-agent workspaces list --base-url https://doct.nodaste.com --json
   doct-agent plans board list --base-url https://doct.nodaste.com --workspace-id <personal-ws> --json
   doct-agent documents list --base-url https://doct.nodaste.com --workspace-id <personal-ws> --json
   ```
3. Resolve folder ids from document readback:
   - `Coding Plans` folder id from title/path/kind.
   - `Archived` child id from `parentId=<coding-plans-id>` and title `Archived`.
   - Use the actual archived document id in `documents move --new-parent-id`; do not synthesize a path.
4. Gather completion evidence:
   - board `plan.prMetadata` if present,
   - `documents get --id <plan-id> --json` frontmatter/body for Linear keys, plan ids, branch names, status notes, checked tasks, validation log, or PR URL,
   - GitHub PR search/list by Linear issue key, branch, title slug, or explicit PR URL,
   - recent merged PR scans when metadata is sparse. Good `gh` syntax is:
     ```bash
     gh search prs --owner Nodaste-Lab --merged --merged-at '>=YYYY-MM-DD' \
       --json url,number,title,state,closedAt,repository --limit 100
     ```
     `gh search prs --state merged` is invalid; merged is a separate `--merged` flag.
   - For active plans with no explicit PR URL, search by exact Linear key first, then distinctive title words. Treat title-only matches as supporting evidence only when the title clearly describes the same shipped change and there is no contradictory plan state.
5. Mutate only confident plans:
   ```bash
   doct-agent plans board set --base-url https://doct.nodaste.com --workspace-id <ws> --document-id <id> --column done --json
   doct-agent plans lifecycle --base-url https://doct.nodaste.com --workspace-id <ws> --document-id <id> --state archived --json
   doct-agent documents move --base-url https://doct.nodaste.com --workspace-id <ws> --id <id> --new-parent-id <archived-folder-id> --json
   ```
   Normalize state anomalies even without new PR evidence: if a plan is already under the `Archived` folder with lifecycle `archived` but the board column is still `in_progress`/`backlog`, set the board column to `done`; if a plan is already `done` but still active in the `Coding Plans` folder, archive/move it only when completion evidence is otherwise strong.
6. Verify with another board/doc readback, not just mutation command stdout. Some `doct-agent plans board set` / `plans lifecycle` JSON shapes may not echo `documentId` or `columnKey`; the source of truth is a fresh `plans board list` plus `documents list` readback showing `columnKey: done`, `plan.lifecycleState: archived`, and `parentId=<archived-folder-id>` / archived path. Report active Coding Plans left behind and why they were not archived.

## Evidence heuristics

Archive when one or more of these are present and there is no contradictory signal:

- Board PR metadata says PR is open or merged.
- GitHub PR list/search shows a matching Linear key/branch/title and state is `OPEN` or `MERGED`.
- Plan body says all progress tasks are checked and final validation/PR handoff happened.
- The card is already `done` and physically under Archived, but lifecycle is still `active`; normalize lifecycle to `archived`.

Do not archive when the plan is only `executionReady=true` with no PR/completion evidence, is a browser-review draft, has `executionReady=false`, or title similarity is the only evidence.
