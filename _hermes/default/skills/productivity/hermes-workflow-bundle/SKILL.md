---
name: hermes-workflow-bundle
description: Export a portable Hermes workflow bundle into a shared location with a SPEC, build script, sanitized config fragment, critical memories, selected skills, optional plugin source, and a manifest. Use this whenever the user wants Hermes-side workflow configuration packaged for reuse by other Hermes instances, especially when credentials and host-specific settings must be excluded and peers need enough guidance to localize the workflow.
---

# Hermes workflow bundle

Use this skill when a user wants Hermes-side configuration packaged for sharing across instances without leaking secrets.

The goal is to package the **Hermes layer only**: skills, durable memory, selected config conventions, optional plugin code, and documentation explaining what is included vs intentionally excluded.

## When to use

Use this skill when the user asks to:
- bundle Hermes workflow configuration for another instance
- export skills + memory + config conventions into a shared folder
- create a portable package with a SPEC and build code
- sync a shared workflow bundle after Hermes-side changes

Do **not** use this skill to distribute credentials, auth state, or machine-specific runtime configuration.

## Output contract

Create a bundle root containing at least:

- `build/build_bundle.py` — reproducible export script
- `bundle/README.md` — quick explanation and usage
- `bundle/SPEC.md` — scope, exclusions, localization contract
- `bundle/config/<name>.config.yaml` — sanitized config fragment
- `bundle/memory/<name>.md` — portable memory pack
- `bundle/skills/...` — selected exported skills
- `bundle/manifest.json` — inventory with hashes

If workflow behavior depends on a Hermes plugin, also include:
- `bundle/plugins/<plugin-name>/...`

## Process

### 1. Discover the local Hermes assets

Inspect the active Hermes home first, usually:
- `~/.hermes/config.yaml`
- `~/.hermes/memories/MEMORY.md`
- `~/.hermes/memories/USER.md`
- `~/.hermes/skills/...`
- `~/.hermes/plugins/...`

Also inspect the requested shared destination so the package lands somewhere other agents already use.

### 2. Separate portable workflow knowledge from secrets

Include only settings and artifacts that help another Hermes instance reproduce behavior.

Good candidates:
- turn budgets and timeout conventions
- compression thresholds
- approval mode
- memory enablement and size limits
- delegation default toolsets
- workflow skills
- plugin source that implements the workflow
- durable memory entries describing the workflow

Exclude:
- `.env`
- API keys, OAuth state, auth.json, tokens
- custom provider secrets and host-only base URLs
- messaging channel IDs and routing state
- personal caches, sessions, cron output, request dumps
- any external dependency repo that is distributed separately

### 3. Sanitize memory for portability

When turning memory into a portable bundle note:
- keep the workflow logic
- remove personal/host-specific phrasing where possible
- convert machine-specific fixes into generalized guidance when that preserves the intent
- preserve explicit boundaries around externally managed dependencies

Example: prefer "launch through a login shell; do not read env files directly" over a host-specific shell-file story unless the exact file layout is essential.

### 4. Select the minimal config fragment

Do **not** copy the whole config file.

Instead, create a sanitized fragment containing only the keys needed to reproduce workflow behavior. Build this from a clear allowlist in the export script so future rebuilds stay safe.

### 5. Export the exact skills and plugin code that matter

Copy only the skills that are critical or strongly supportive for the workflow. Preserve directory structure so another Hermes instance can re-import them cleanly.

If a local plugin is part of the workflow, export its source alongside the bundle and mention why it is needed in the SPEC.

### 6. Write the SPEC

The SPEC should clearly cover:
- goal of the bundle
- included artifacts
- exclusions
- localization contract
- sync policy

Explicitly state which external systems are **not** bundled and how they are expected to arrive.

### 7. Make the bundle reproducible

Write a build script that:
- reads from the local Hermes home
- rewrites the export directory from scratch
- copies selected skills/plugins
- writes sanitized config + memory files
- generates a manifest with file hashes

This script is the main deliverable, not just the exported files.

### 8. Verify the export

After generating the bundle:
- read back the SPEC and sanitized memory
- inspect the config fragment for secrets
- inspect the manifest
- list exported files
- confirm the expected skills/plugins are present

### 9. Save a durable reminder if appropriate

If the user wants this shared location to stay current, save memory noting the canonical bundle path and the expectation to resync it when Hermes-side workflow changes materially.

## Recommended structure

```text
<bundle-root>/
├── build/
│   └── build_bundle.py
└── bundle/
    ├── README.md
    ├── SPEC.md
    ├── manifest.json
    ├── config/
    ├── memory/
    ├── plugins/
    └── skills/
```

## Practical lessons from prior use

## Practical lessons from prior use

- `search_files` may miss hidden-directory layouts or be less useful than a direct `find` when quickly inventorying `~/.hermes`; if discovery looks empty, verify with terminal-based filesystem inspection instead of assuming files are absent.
- Read back the generated memory pack: host-specific shell details often need one more sanitization pass to become portable.
- Read back the SPEC after generation too: indentation artifacts from templated multiline strings can slip through and should be corrected before finishing.
- A manifest with SHA-256 hashes is useful for peer Hermes instances to detect drift and verify sync state.
- When updating an existing shared bundle, first locate the canonical bundle root and run its own verify tool. Pass the directory that contains `bundle/`, not the `bundle/` directory itself.
- For workflow packaging questions, answer from Hermes mechanics first: skill as behavioral entry point, `scripts/` for executable workflow code, `templates/` for reusable artifact/prompt/render templates, `references/` for session-specific details, sanitized config fragments, managed memory blocks, manifest hashes, and verify/import/export tooling.
- Do not introduce an unasked renderer/app-layer ownership frame (for example Markdoc owning a layer) when the user only asked how to package code/templates. If a tradeoff or assumption is relevant, label it explicitly as the assistant's assumption before using it.
- Export tools that rewrite `bundle/` from scratch should preserve a temp backup of the previous export until the new export succeeds; otherwise a missing local skill can delete checked-in bundle content before failing.
- Do not include `manifest.json` in its own file-hash list unless the verifier intentionally handles self-referential hashes; otherwise verification can never be stable after writing the manifest.

Reference: `references/aaron-hermes-pi-workflow-bundle-discovery-2026-06-27.md` captures Aaron's canonical shared Hermes/Pi bundle path and the Good Morning skill addition pattern.

Reference: `references/good-morning-workflow-packaging-2026-06-29.md` captures the Hermes-first packaging pattern for Good Morning code/templates/tests and the important premise-discipline correction: do not introduce renderer/app-layer ownership framing unless the user asked for that tradeoff.

Reference: `references/ai-configs-hermes-managed-sync-2026-06-30.md` captures the source-first `~/code/ai-configs/_hermes/default` pattern: export managed Hermes config into a repo copy, sanitize config and copied text files, verify manifest hashes/no obvious token patterns, and install back into `~/.hermes` with redacted config leaves skipped.

## Source-first repo sync pattern

When Aaron asks to keep Hermes config in `~/code/ai-configs` or to edit there first and install into Hermes:

1. Treat `~/code/ai-configs/_hermes/default` as the managed source copy and `scripts/hermes_config_sync.py` as the reproducible export/install surface.
2. Include source-like Hermes assets: sanitized `config.yaml`, skills, hooks, plugins, scripts, `cron/jobs.json`, memories, and profile-local equivalents.
3. Exclude secrets and runtime state: `.env`, `auth.json`, OAuth/PAT/API tokens, sessions, logs, caches, SQLite state, checkpoints/state snapshots, pid/lock/process files, cron output, and the Hermes source checkout/venv.
4. Before reporting success, run the export script's `verify` and a dry-run install. Verify should check manifest hashes and scan for obvious secret/token patterns.
5. Prefer future changes in the repo copy first, followed by `python3 scripts/hermes_config_sync.py install --dry-run` and then `--apply` when the user wants to update live Hermes.
6. After every Hermes configuration change, synchronize the repo copy with `python3 scripts/hermes_config_sync.py export`, verify, then commit and push the `~/code/ai-configs` changes so the source copy does not drift from live Hermes.

## Sync guidance

When a shared bundle already exists, treat that location as the canonical sync target. Regenerate the bundle after material Hermes-side workflow changes so peer Hermes instances can localize the update.
