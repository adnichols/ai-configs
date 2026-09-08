---
name: ccore
description: C-Core local-first knowledge graph CLI guide. Use when working with the `ccore` command or `ccore-node` to inspect spaces, documents, ingest runs, graph links, artifacts, resumable work/session state, sync/sharing, or ranked query flows, and when you need the current `ccore` command reference.
---

## Codex execution

Read [the Codex runtime contract](../adn-mode/references/codex-runtime.md) before executing this skill. It owns tool dispatch, models, delegation, history access, and authorization for this Codex-only copy. Instructions below about other clients describe their workflows, not permission to launch those clients. Preserve the task-specific evidence and output requirements using native Codex tools.


# C-Core CLI

## Overview

Use this skill to operate a local or remote C-Core node through the `ccore` CLI.
The full generated guide from the installed binary lives in `references/ccore-skill-guide.md`; read that file when you need exact flags or a subcommand that is not covered here.

## Quick Start

1. Confirm the target node: `ccore health`
2. If the command should hit a non-default node, add `--url <base_url>`
3. Resolve the working space early: `ccore space list`
4. Use UUIDs when names or titles are ambiguous
5. Prefer the smallest command that answers the question, then fall back to `references/ccore-skill-guide.md` for exact syntax

## Core Concepts

- `space`: top-level namespace for documents and graph state
- `document`: content item in a space with immutable versions
- `ingest run`: tracked import job such as Obsidian or Slack fixture ingest
- `links`: graph edges between documents
- `decision` / `package`: durable memory objects for reusable decisions and canonical context

## Common Workflows

### Space and document inspection

- List spaces: `ccore space list`
- List docs in a space: `ccore doc list <space>`
- Show one doc: `ccore doc show <document> --include-content`

### Search and ranking

- Use `ccore search <space> <query>` for the legacy document-only compatibility path
- Use `ccore query <space> <query>` for authority/freshness-ranked results across supported kinds
- If the user cares about why results ranked the way they did, prefer `query`

### Ingest

- Obsidian: `ccore ingest obsidian <space> <vault_path>` then `ccore ingest status <ingest_run_id>`
- Slack fixture: `ccore ingest slack-fixture <space> <fixture_path>` then `ccore ingest status <ingest_run_id>`
- Keep `vault_id` stable per vault and avoid disabling frontmatter IDs unless the user accepts rename instability

### Graph and artifacts

- Backlinks: `ccore links backlinks <space> <document>`
- Outlinks: `ccore links outlinks <space> <document>`
- Artifacts: `ccore artifact list <space>`, `ccore artifact show <artifact_id>`, `ccore artifact cat <artifact_id>`

### Durable memory

- Decisions: `ccore decision create|list|show`
- Canonical packages: `ccore package promote|list|show|consume`
- Use these when the user wants reusable, inspectable memory rather than ad hoc notes

### Sync and sharing

- Check space sync state with `ccore space sync-status <space>`
- Use `sync-push` and `sync-pull` for diagnostic/manual sync
- Use `space invite` and `space invite-import` for sharing flows
- Treat `hub` and sync credential commands as sensitive operations; do not invent tokens or passphrases

## Working Style

- Default node URL is `http://127.0.0.1:8787`
- Many commands accept human-readable refs, but UUIDs are safer when collisions exist
- For failures, start with `ccore health`, then confirm `--url`, then inspect the specific run/object by ID
- For exhaustive CLI details, read `references/ccore-skill-guide.md` and jump with grep patterns like `^### \`ccore space` or `^### \`ccore ingest`

## Maintenance

- Refresh the generated reference after upgrading `ccore` by running `scripts/refresh_reference.sh`
- That script overwrites `references/ccore-skill-guide.md` with fresh output from `ccore skill`
- If new top-level commands appear, update this `SKILL.md` task map so the concise guidance stays aligned with the binary

## Resources

- `references/ccore-skill-guide.md`: raw generated guide and full clap-derived command reference from the installed binary
- `scripts/refresh_reference.sh`: refresh helper for keeping the reference current
