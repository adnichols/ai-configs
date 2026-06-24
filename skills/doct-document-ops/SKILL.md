---
name: doct-document-ops
description: Interact with doct documents through the doct-agent CLI. Use when asked to open a doct URL, list doct workspaces or documents, view a doct document, create or edit a doct document body, update document metadata, rename/move/delete a document, add or inspect comments, publish a coding plan to the personal "Coding Plans" document, or run read-only doct DB/log triage.
---

# Doct document operations

Use this skill when the user wants work done **inside doct itself** rather than only in local markdown files.

## Golden rule: doct-agent only

Every doct operation goes through the `doct-agent` CLI on PATH. Do **not** use `doct-cli`, raw `curl`/REST calls, hand-written Hocuspocus/Yjs scripts, or any wrapper/bash helper. `doct-agent` already wraps REST for discovery, reads, creation, and metadata, and the Yjs/Hocuspocus path for text-body edits and comments — with verified readback. If a task seems to need raw REST or a Yjs script, you are on the wrong path: find the matching `doct-agent` subcommand or run `doct-agent onboard`.

- **Install/update via Homebrew only.** From the doct repo root: `brew tap local/doct "$(pwd)"` then `brew install --build-from-source local/doct/doct-agent`. Refresh an existing install with `brew reinstall --build-from-source local/doct/doct-agent`. Never copy Cargo build artifacts into ad hoc paths or use alternate binaries, wrapper scripts, or token-store fallbacks.
- Most discovery and mutation commands accept `--json` for machine-readable output.
- `references/doct-agent-commands.md` is the full command reference. `doct-agent onboard` prints the canonical, always-current spec straight from the installed CLI — consult it if anything here looks stale.

## Auth

Check first:

```bash
doct-agent auth status
```

If not authenticated:

1. Ask the doct owner to generate and approve a selected-agent enrollment code.
2. `doct-agent auth login --base-url https://doct.nodaste.com` (develop: `https://doct.develop.nodaste.com`).
3. Paste the enrollment code when prompted, or pass `--enrollment-code <code>`.
4. Fallback: `doct-agent auth import-pat --base-url <url> --token <doct_pat_v1_...>`.

The CLI discovers and stores the collaboration websocket URL after auth; pass `--websocket-url` only to override. For one-off automation, `DOCT_AGENT_PAT` overrides the stored token — it is the only supported token environment override. Confirm identity and deployment any time with `doct-agent context`.

## Resolve the target first

Accept any of: a full doct URL, a document id, or a workspace + path/title.

- doct URLs look like `https://doct.nodaste.com/d/<workspace-handle>/docs/<document-id>` — parse `<document-id>` from `/docs/<uuid>`, then `doct-agent documents get --id <id>`.
- Discover with `doct-agent workspaces list`, then `doct-agent documents list --workspace-id <id>`.
- If still ambiguous, ask for exactly one missing locator: document URL, document id, or workspace + path.

## Command map by task

| Task | Command |
|------|---------|
| Check auth / identity | `doct-agent auth status` · `doct-agent context` |
| List workspaces | `doct-agent workspaces list --json` |
| List documents | `doct-agent documents list --workspace-id <id> --json` |
| Read a document | `doct-agent documents get --id <id> --text` (markdown) or `--json` (metadata); or `--workspace-id <id> --path '<path>'` |
| Create a document | `doct-agent documents create --workspace-id <id> --title <t> --path <p> --kind text --content '# ...'` (published by default; add `--status draft` for a hidden draft; `--parent-id` to nest) |
| Replace full body | `doct-agent documents replace-body --id <id> --file prepared.md` (or `--text` / `--stdin`) |
| Append to body | `doct-agent collab edit --document-id <id> --append-markdown '...'` |
| Surgical body edit | `doct-agent collab anchored <replace\|insert-before\|insert-after\|delete> --document-id <id> --selected-text '...' [--text '...']` |
| Add a comment thread | `doct-agent collab comments add --document-id <id> --selected-text '...' --body '...'` |
| List / reply / resolve comments | `doct-agent collab comments <list\|reply\|resolve\|unresolve> --document-id <id>` |
| Mentions for me | `doct-agent collab comments mentions --workspace-id <id>` |
| Title / status | `doct-agent documents update-metadata --id <id> --title <t> --status <s>` |
| Rename | `doct-agent documents rename --id <id> --workspace-id <id> --title <t>` |
| Move / reorder | `doct-agent documents move --id <id> --workspace-id <id> --new-parent-id <id>` |
| Delete | `doct-agent documents delete --id <id> --workspace-id <id>` |
| Read-only ops triage | `doct-agent triage <run\|logs\|db-query\|db-tables\|db-describe\|...>` |

### Text edit notes

- `replace-body` is the safe path for a full rewrite — it routes through the Hocuspocus/Yjs-safe server path and returns verified readback metadata. Prefer it over append-then-cleanup when you are rewriting a whole document.
- For anchored edits and comments, build `--selected-text` (and optional `--prefix-text` / `--suffix-text`) from the document's **visible prose**, not markdown syntax. `documents get --text` returns markdown, which is not the authoritative selection surface — keep selections to plain visible text and add prefix/suffix context when a quote is ambiguous.
- Bootstrap empty or near-empty documents with creation-time `--content` or `collab edit --append-markdown` until there is anchorable text to target.

## Special default: coding plans

If the user asks to **send, publish, copy, or save a coding plan to doct**, default to:

```bash
doct-agent documents publish-plan --file /path/to/plan.md --json
```

Defaults: personal workspace, parent document **Coding Plans** (created if missing), a new text child document, and a title taken from the first H1 (override with `--title`). Override the destination with `--parent-title` / `--workspace` only when the user asks. Return the created doct URL and document id.

## Decision rules

- One tool: `doct-agent`. Reads and discovery are safe to run freely.
- Confirm before create / replace-body / delete / move on documents you did not create, and before publishing into shared workspaces.
- `doct-agent triage` is read-only operational triage (DB checks and Railway logs) — use it to inspect state, not to mutate.
- For visual verification inside doct, use browser automation after approval.

## References

- `references/doct-agent-commands.md` — full per-command reference, flags, and worked examples.
- `doct-agent onboard` — the canonical, always-current spec from the installed CLI.
