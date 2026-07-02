# Coding plan archive audit pattern

Use this reference when Aaron asks to clean up Doct Coding Plans by identifying completed work, PR-backed work, or merged work and moving those plans to Done/Archived.

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
   - Board `plan.prMetadata` if present.
   - `documents get --id <plan-id> --json` frontmatter/body for `linear`, `planId`, branch names, status notes, checked tasks, validation log, PR URL.
   - GitHub PR search/list by Linear issue key, branch, title slug, or explicit PR URL. Evidence can be open PR or merged PR when Aaron says those both count as done for Kanban cleanup.
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

Do **not** archive when:

- The plan is only `executionReady=true` with no PR/completion evidence.
- The plan is a browser-review draft or `executionReady=false` and no matching PR exists.
- Title similarity is the only evidence; title collisions and duplicate documents happen.

## Pitfalls observed

- Doct board column, plan lifecycle, and document folder placement drift independently; update and verify all three.
- Archived folders may be text/folder-like documents with generated paths such as `coding-plans/archived-<id>.md`; the id is what matters for moves.
- Board cards may include plans outside `coding-plans/`; filter carefully when Aaron asks for personal Coding Plans only.
- Duplicate/hidden documents can represent the same plan. Tie duplicates to the same Linear key/plan id/branch before archiving.
- `gh search prs --state all` is invalid; either omit `--state` for broad search or query open/closed separately. `gh search prs` JSON fields differ from `gh pr list`; for merged state, `gh pr list --state all --json mergedAt,...` works on a known repo, while `gh search prs` exposes `state` as values like `merged` but may not expose `mergedAt`.
