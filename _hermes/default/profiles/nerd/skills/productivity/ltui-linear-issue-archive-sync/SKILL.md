---
name: ltui-linear-issue-archive-sync
description: Sync a local markdown issue archive into Linear via ltui, then rewrite local files as deprecated mirrors pointing to the Linear issues.
version: 1.0.0
author: Hermes Agent
license: MIT
prerequisites:
  commands: [ltui, python3]
metadata:
  hermes:
    tags: [Linear, ltui, markdown, migration, issue-tracking]
---

# ltui Linear issue-archive sync

Use this when a repo has a directory of local markdown issue docs that must become Linear issues, while preserving the local docs as deprecated archival mirrors.

## When to use

- A repo has many `*.md` issue files in a local folder
- Each file should map to one Linear issue
- The Linear issue should become the source of truth
- The local file should be rewritten with a Linear link and deprecation metadata

## Important tool findings

- `ltui` may work through its configured auth profile even when `LINEAR_API_KEY` is not present in the shell environment. Check `ltui auth list` before assuming Linear access is unavailable.
- In Hermes profile/sandbox contexts, `$HOME` may point at a profile home with no `ltui` auth. For Aaron's local machine, retry with the real home before declaring Linear unavailable:
  - `HOME=/Users/anichols ltui auth list`
  - `HOME=/Users/anichols ltui --format json projects list`
- `ltui` global flags must go **before** the subcommand:
  - good: `ltui --format json --limit 250 issues list --project <project-id>`
  - bad: `ltui issues list --project <project-id> --format json`
- `ltui projects list` does **not** accept `--format` after the subcommand; use the global form.
- `ltui issues create` returns a full JSON object with `identifier`, `url`, `project`, etc. This is enough to update local files immediately.
- `ltui` supports issue create/update/comment/link, plus dependency helpers:
  - `ltui issues relate <child> --parent <parent>` for parent/child structure
  - `ltui issues block <child> --blocked-by <parent>` for execution-order blocking
- `ltui` may not support deletion. For accidental test issues, prefer canceling and renaming them.
- Network calls to Linear can intermittently timeout (`ETIMEDOUT` / `EHOSTUNREACH`) even when auth is valid. For bulk updates, use a script with retries/backoff.
- For large migrations or bulk rewrites, use a script rather than one tool call per issue.

## Recommended workflow

1. **Inspect the archive directory**
   - Enumerate `*.md` files.
   - Exclude non-issue files like `README.md`.
   - Sample a few issue files to confirm frontmatter shape and title extraction rules.

2. **Confirm Linear access and discover target project**
   - Run `ltui auth list`
   - Run `ltui projects list` or `ltui --format json projects list`
   - Identify the target project ID/key and team key

3. **Check for existing Linear representation**
   - List current issues in the target project:
     ```bash
     ltui --format json --limit 250 issues list --project <project-id>
     ```
   - Build a title -> issue map before creating anything
   - Paginate if needed using the global `--cursor`

4. **Create missing Linear issues**
   - Extract the markdown H1 as the Linear title
   - Preserve key frontmatter fields in the description, e.g.:
     - source file
     - created
     - priority
     - review_area
     - category
     - original local status
   - Pass descriptions via a temp file using `--description @/tmp/file.md`
   - Map local priorities if useful (e.g. critical→1, high→2, medium→3, low→4)

5. **Rewrite local files as deprecated mirrors**
   Update frontmatter with fields like:
   ```yaml
   status: deprecated
   original_status: open
   deprecated: true
   deprecated_in_favor_of: linear
   source_of_truth: linear
   linear_issue: NOD-123
   linear_url: https://linear.app/...
   ```

   Add a top-of-file callout like:
   ```md
   > [!IMPORTANT]
   > Deprecated local mirror. Canonical tracking now lives in Linear: [NOD-123](https://linear.app/...).
   > Keep this file only for archival context; update the Linear issue instead.
   ```

6. **Sync structural relationships if the archive has a hierarchy**
   - If the archive contains an index/tree (for example a README section like `Related concern tree`), treat that as the source of truth for dependency structure.
   - For each parent -> child pair, apply both:
     ```bash
     ltui issues relate <child> --parent <parent>
     ltui issues block <child> --blocked-by <parent>
     ```
   - Use parent/child to preserve conceptual grouping.
   - Use `blocked-by` when the parent must be fixed first and is expected to resolve or subsume the child issue.

7. **Normalize severity ranking in Linear**
   - Linear only has 4 priority buckets, so if the local archive has more nuance than that, define an explicit mapping before bulk updates.
   - A good pattern when the archive has a curated shortlist is:
     - top curated issues -> `1` (Urgent)
     - remaining local `critical` -> `2` (High)
     - local `high` -> `3` (Medium)
     - local `medium` / `low` -> `4` (Low)
   - For a curated top list, parse it from the archive index rather than inferring it later.
   - Bulk-apply priorities with a retrying script, since `ltui` calls may intermittently time out.

8. **Verify all files and Linear issue shape**
   - Confirm every local issue file contains the new Linear metadata
   - Confirm every file is marked `status: deprecated`
   - Sample created issues with `ltui --format json issues view <id>`
   - For relationship migrations, confirm representative children were updated after `relate`/`block`
   - For priority migrations, sample one issue from each bucket to confirm the mapping landed

## Suggested automation pattern

For 20+ issues, write a short Python script that:

- enumerates files
- parses frontmatter + H1 title
- fetches existing project issues once (with pagination)
- creates only missing issues
- rewrites each local file
- optionally parses an archive index / README tree into parent-child dependency pairs
- optionally bulk-applies `relate` + `block` relationships in Linear
- optionally bulk-normalizes priorities from local severity + curated top lists
- retries `ltui` commands with backoff on transient network errors
- verifies required markers are present
- prints a concise migration summary

This is faster and more reliable than manual per-issue CLI calls.

## Example commands

List projects:
```bash
ltui projects list
```

List project issues as JSON:
```bash
ltui --format json --limit 250 issues list --project <project-id>
```

List issues opened since a date:
```bash
ltui --format json --limit 250 issues list --project <project-id> --created-since 2026-05-04T00:00:00-06:00
```

Important: `issues list` output may omit `createdAt` and canonical URLs; it can show only `updatedAt`. For an accurate "opened this week" report, collect identifiers from `issues list`, then call `ltui --format json issues view <issue-id>` for each issue to retrieve `createdAt`, `url`, labels, assignee, and project.

Create an issue:
```bash
ltui --format json issues create \
  --team <team-key> \
  --project <project-id> \
  --title "Issue title" \
  --description @/tmp/issue.md \
  --priority 2
```

Update an issue if needed:
```bash
ltui --format json issues update <issue-id-or-key> --state Canceled --title "[test] accidental issue"
```

## Pitfalls

- Do not rely only on `LINEAR_API_KEY`; `ltui` profile auth can still be valid.
- Put `--format` / `--limit` before the subcommand.
- Avoid creating test issues unless necessary; if you do, cancel and clearly rename them.
- If the local archive contains non-issue files (indexes, notes, open-question docs), decide explicitly whether they should become Linear issues before bulk creation.
- Verify title uniqueness assumptions before using title-based deduplication.

## Good final report

Report:
- how many local files were processed
- how many Linear issues were created vs reused
- what deprecation markers were added locally
- any accidental test artifacts or cleanup items remaining
