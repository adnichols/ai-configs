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
   - GitHub PR search/list by Linear issue key, branch, title slug, or explicit PR URL.
5. Mutate only confident plans:
   ```bash
   doct-agent plans board set --base-url https://doct.nodaste.com --workspace-id <ws> --document-id <id> --column done --json
   doct-agent plans lifecycle --base-url https://doct.nodaste.com --workspace-id <ws> --document-id <id> --state archived --json
   doct-agent documents move --base-url https://doct.nodaste.com --workspace-id <ws> --id <id> --new-parent-id <archived-folder-id> --json
   ```
6. Verify with another board/doc readback. Report active Coding Plans left behind and why they were not archived.

## Evidence heuristics

Archive when one or more of these are present and there is no contradictory signal:

- Board PR metadata says PR is open or merged.
- GitHub PR list/search shows a matching Linear key/branch/title and state is `OPEN` or `MERGED`.
- Plan body says all progress tasks are checked and final validation/PR handoff happened.
- The card is already `done` and physically under Archived, but lifecycle is still `active`; normalize lifecycle to `archived`.

Do not archive when the plan is only `executionReady=true` with no PR/completion evidence, is a browser-review draft, has `executionReady=false`, or title similarity is the only evidence.
