# Bulk Skill Migration Checklist

Use when a session updates several installed Hermes skills or migrates a workflow across skills.

## Procedure

1. **Identify source and runtime trees.** Distinguish authoritative source skills from installed runtime skills, e.g. a repo/config checkout versus `~/.hermes/skills`. Do not assume they are the same tree.
2. **Create a rollback handle first.** If the runtime skill tree is not a git worktree, copy the targeted skill directories into a timestamped backup under `~/.hermes/tmp/skill-backups/` before writing.
3. **Patch active instructions, not just descriptions.** Search for old commands and service URLs in SKILL.md bodies, not only frontmatter. Replace default-path instructions; leave historical/deprecation mentions only when they explicitly say not to use the old flow.
4. **Validate frontmatter after every bulk edit.** Parse every touched `SKILL.md` as YAML and enforce at least `name` and `description`. Quote descriptions containing colons or other YAML-sensitive punctuation.
5. **Verify command guidance against the CLI.** For migrated command flows, check the relevant `--help` output for flags used in examples before finalizing the skill text.
6. **Run two searches before reporting done.** One search for legacy/default-path commands and URLs; one search for the new canonical commands/terms. Classify remaining legacy hits as either intentional history/deprecation or still-active instructions.
7. **Check skill discovery.** Use `skills_list` for the affected categories to confirm new/updated skills are visible and descriptions reflect the migration.

## Completion bar

A bulk skill migration is not complete until: rollback exists, frontmatter validates, command examples are internally consistent, old default-path instructions are gone, new commands are discoverable in the relevant skills, and any remaining legacy references are explicitly labeled as legacy/history/fallback.