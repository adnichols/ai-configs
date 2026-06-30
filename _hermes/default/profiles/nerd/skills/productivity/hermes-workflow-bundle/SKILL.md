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

- `search_files` may miss hidden-directory layouts or be less useful than a direct `find` when quickly inventorying `~/.hermes`; if discovery looks empty, verify with terminal-based filesystem inspection instead of assuming files are absent.
- Read back the generated memory pack: host-specific shell details often need one more sanitization pass to become portable.
- Read back the SPEC after generation too: indentation artifacts from templated multiline strings can slip through and should be corrected before finishing.
- A manifest with SHA-256 hashes is useful for peer Hermes instances to detect drift and verify sync state.
- When the build script emits Python helper scripts from nested string literals, use raw triple-quoted strings or carefully escaped `\\n`; otherwise generated files can contain accidental physical newlines inside quoted strings or preserve indentation, causing `IndentationError`/`SyntaxError`. Always `python -m py_compile` generated scripts after rebuilding.
- For a bundle that will live in a git repo on multiple machines, make the build script default its output root to `Path(__file__).resolve().parents[1]` and derive the source Hermes home from `HERMES_HOME`, `~/.hermes/profiles/<profile>`, then `~/.hermes` rather than hardcoding one host path.
- For git-backed bundles, include explicit push/export and pull/import instructions in the bundled README/SPEC or a bundled support skill. A portable archive alone is not enough when the desired operating model is ongoing bidirectional sync.

## Sync guidance

When a shared bundle already exists, treat that location as the canonical sync target. Regenerate the bundle after material Hermes-side workflow changes so peer Hermes instances can localize the update.
