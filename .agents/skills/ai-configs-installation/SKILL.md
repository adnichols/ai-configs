---
name: ai-configs-installation
description: Maintain ai-configs installers, skill provenance, retirement, and source-to-install synchronization.
---

# ai-configs installation

Repository-managed configuration uses Git as its source of truth. Shared skills are inventoried in `skills/install-matrix.json`; repo-owned payloads live in `skills/`, with pinned ADN sources in `_adn/`. Codex adaptations are independently maintained in `_codex/skills`, selected through `_codex/skill-overrides.json`. Do not rewrite shared descriptions or PSTack principles for a Codex-only change.

Before changing an install, identify its source, consumer, managed marker or manifest, and local modifications. Preserve unrelated configuration, system-owned plugin caches, and unmanaged skills. Back up retired managed files. A missing optional-profile skill is not installation drift. Validate a disposable install and a repeated install before refreshing the live destination.

Codex prompts use `_codex/install-prompts.py` with hashes in `ai-configs-prompts.json`. Legacy hashes are migration evidence, not permission to delete edited files. Codex skills use `_codex/install-skills.py`; disabled shared paths affect Codex only. Start a fresh Codex session to inspect the new catalog.

Use `bash install.sh --retire-skills <name>...` only for names in the deprecated list. This uses managed markers and recoverable backups. Do not remove same-name custom content by inference.

Remote installs use Git only: commit and push, install locally, then run `git pull --ff-only` in each remote ai-configs checkout before installing. Do not transport managed source with tar, rsync, scp, or ad hoc copies.

## Hermes Configuration Source of Truth

- Managed Hermes configuration lives in `_hermes/default` and is synchronized by `scripts/hermes_config_sync.py`.
- For any change to live Hermes configuration (`~/.hermes` skills, config, hooks, plugins, scripts, cron jobs, memories, or profile-local equivalents), also run `python3 scripts/hermes_config_sync.py export` from this repo, then `python3 scripts/hermes_config_sync.py verify`.
- Prefer source-first edits in `_hermes/default`; preview install with `python3 scripts/hermes_config_sync.py install --dry-run`, then apply with `python3 scripts/hermes_config_sync.py install --apply` when live Hermes should be updated.
- After synchronization and verification, commit and push the `ai-configs` changes so the repo copy stays authoritative. Do not commit secrets or runtime state; the sync tool excludes those surfaces.



For Pi discovery and installation see `_pi/README.md`. For local Pi development, add `"skills": ["skills"]` to its settings. For each runtime, use its own installer and README; do not install or launch other runtimes merely to satisfy a Codex workflow.
