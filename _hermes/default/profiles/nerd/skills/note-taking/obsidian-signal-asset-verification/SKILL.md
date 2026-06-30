---
name: obsidian-signal-asset-verification
description: Verify whether assets referenced by a Nodaste/Obsidian signal have actually landed locally, including canonical files, archived/deprecated files, package artifacts, and stale code references.
---

# Obsidian signal asset verification

Use this when Aaron asks to inspect a signal and confirm whether referenced branding, logo, package, or other assets are now available locally.

## Workflow
1. Locate the relevant signal first.
   - Search formal signal folders under the vault, especially `studio/Nodaste Agents/Signals/inbox/aaron/` and the sender's outbox.
   - Prefer the Aaron inbox copy for Aaron-facing status, but cross-check nearby follow-up signals if the issue may have evolved.
   - Search by sender, project, and asset terms, e.g. `Katie`, `Heddle`, `branding`, `logo`, `.skill`.

2. Read the signal and extract concrete assertions.
   - Expected asset paths and filenames.
   - Claimed package/artifact sizes.
   - Deprecated or archived filenames.
   - Acceptance criteria and any previous blocker/status in `## Response` or `## Clarifying Questions`.

3. Verify the local filesystem, not just the note text.
   - Check the exact project path named by the signal.
   - Search more broadly under the vault and likely repo roots when a package/artifact is missing.
   - For binary/vector assets, validate basic integrity when possible. For SVGs, parse as XML and report `valid_xml`, size, and viewBox.
   - For package artifacts such as `.skill`, verify existence and size against the signal's claim.

4. Distinguish asset availability from package availability.
   - It is common for the referenced asset set to have landed while the installable package artifact is still missing.
   - Report these separately: `canonical assets present` vs `packaged skill/artifact missing`.

5. Check deprecated references when the signal includes migration guidance.
   - Search the vault/project docs for old filenames to confirm they are only mentioned in archive/change-log contexts.
   - Search relevant code roots such as `/Users/anichols/code` for stale references before claiming application surfaces are clean.
   - Do not edit code or signal statuses unless Aaron explicitly asks.

6. Summarize tersely with evidence.
   - Name the signal file inspected.
   - List present canonical files and missing artifacts.
   - Include whether old assets are archived and whether stale code references were found.
   - Avoid claiming install success if only raw assets are present.

## Heddle example
For Katie's Heddle logo canonical-set signal, the reusable checks were:
- expected canonical SVGs under `studio/projects/Heddle Branding/brand-package/assets/`
- archived old SVGs under `assets/_archive/`
- missing package artifact at `studio/projects/Heddle Branding/heddle-brand.skill`
- SVG integrity checked with Python XML parsing
- stale old filename references searched in both the Studio vault and `/Users/anichols/code`

## Pitfalls
- Signal `status` may remain `needs_info_from_requester` because an earlier package artifact is missing, even if the raw assets have landed.
- Do not treat an Obsidian wikilink or signal claim as evidence that a file exists locally.
- Search results may include old filenames in the signal itself, archive notes, or changelogs; classify those separately from active code references.
