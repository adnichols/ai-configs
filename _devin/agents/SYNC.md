# Sync rule for ADN subagent profiles

These agent profiles are the source of truth for the ADN custom subagent
profiles (`completeness`, `oracle`, `planner`, `reviewer`) used across
Nodaste tooling.

When you edit any file in this directory, treat the change as a cross-repo
update that must also land in the `devin-skills` plugin:

1. Copy the changed `.md` files to `devin-skills/agents/` (sibling repo at
   `../devin-skills/agents/` or the path the user names). Keep the filenames
   and frontmatter identical.
2. If the profile's behavior, invariants, or frontmatter contract changed,
   bump `devin-skills/.devin-plugin/plugin.json` version. Use a patch bump
   for wording or clarifications, a minor bump for behavioral changes, and a
   major bump for breaking contract changes.
3. If `devin-skills` is installed locally, run `devin plugins update
   devin-skills` so the installed plugin reflects the new files.
4. Commit and push both repositories in the same logical step. The
   `devin-skills` commit should reference the `ai-configs` commit or the
   specific files that changed.

Do not leave `ai-configs` updated while `devin-skills` is stale. The plugin
ships a derived copy so it works offline as a Devin plugin; the derivation
must stay current.
