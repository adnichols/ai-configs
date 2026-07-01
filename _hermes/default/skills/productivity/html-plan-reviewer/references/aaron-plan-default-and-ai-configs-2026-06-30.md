# Aaron plan default + ai-configs sync correction — 2026-06-30

## Trigger
Aaron corrected a plan workflow failure where an agent created a plain Doct text document instead of a browser-reviewable HTML/Markdoc plan, did not start a comment listener, then patched only the runtime Hermes skills before syncing them to `ai-configs`.

## Durable lesson
For Aaron-facing implementation/development plans, “create/post/make/publish a plan” means:

1. Create a browser-reviewable HTML or Markdoc source.
2. Register it with `doct-agent plans register` against `https://doct.nodaste.com`.
3. Inspect the plan queue once.
4. Start or verify a document-specific queue-backed comment listener/maintainer.
5. Return the canonical Doct plan URL and listener status.

A plain `doct-agent documents create` / `documents replace-body` text document is the wrong artifact for this class of task because it is not the expected commentable plan-review surface.

## Skill-library persistence requirement
When the fix involves editing Hermes skills under `~/.hermes/skills`, do not stop there. Aaron’s Hermes config source of truth is `~/code/ai-configs/_hermes/default`.

Required sequence after runtime skill edits:

```bash
cd ~/code/ai-configs
python3 scripts/hermes_config_sync.py export
python3 scripts/hermes_config_sync.py verify
git status --short
git add _hermes/default/...
git commit -m "fix: <summary>"
git push origin main
```

If SSH push fails but `gh auth status` shows a valid HTTPS-capable account, retry with an explicit HTTPS remote:

```bash
git push https://github.com/adnichols/ai-configs.git main
```

Avoid committing pure cron tick/runtime noise if export updates only timestamps/counters in cron jobs; restore those files and regenerate the manifest before committing.

## Skills patched in the correction
- `writing-plans`
- `planning-workflow`
- `plan`
- `dev-plan`
- `html-plan-reviewer`
- `reviewed-html-plan`
- `doct-document-ops`
- `doct-agent-cli`

## Verification pattern used
- Validate skill frontmatter parses and description lengths are within limits.
- Search for stale contradictory language such as “no default plan file format,” “ask one targeted question,” or Markdown/text-doc plan defaults.
- Run `hermes_config_sync.py verify` after export.
- Commit and push `ai-configs` before reporting the skill-library correction complete.
