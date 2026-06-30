---
name: doct-document-ops
description: Interact with doct through the doct-agent CLI. Use when asked to open a doct URL, list doct workspaces or documents, view/create/edit doct documents, update metadata, rename/move/delete, add or inspect comments, register/update/monitor HTML or Markdoc coding plans in Doct, or run read-only doct DB/log triage. Prefer `doct-agent plans register` on `https://doct.nodaste.com` for HTML plan registration.
---

# Doct document operations

Use this skill when the user wants work done **inside doct itself** or wants a coding/HTML plan registered in Doct for review.

## Golden rule: doct-agent only

Every doct operation goes through the `doct-agent` CLI on PATH. Do **not** use `doct-cli`, raw `curl`/REST calls, hand-written Hocuspocus/Yjs scripts, local wrapper scripts, or token-store fallbacks. `doct-agent` wraps REST for discovery, reads, creation, plan registration, metadata, and Yjs/Hocuspocus-safe edits/comments — with verified readback where supported. If a task seems to need raw REST or a custom Yjs script, you are on the wrong path: find the matching `doct-agent` subcommand or run `doct-agent onboard`.

- **Install/update via Homebrew only.** From the doct repo root: `brew tap local/doct "$(pwd)"` then `brew install --build-from-source local/doct/doct-agent`. Refresh with `brew reinstall --build-from-source local/doct/doct-agent`.
- Most discovery and mutation commands accept `--json`.
- `references/doct-agent-commands.md` is the local command reference. `doct-agent onboard` prints the canonical, always-current spec from the installed CLI — consult it if anything here looks stale.

## Auth and endpoint

Production Doct is the default target for plan registration:

```bash
https://doct.nodaste.com
```

Check first:

```bash
doct-agent auth status --all --json
doct-agent context --base-url https://doct.nodaste.com --json
```

If production is authenticated but not default, either pass `--base-url https://doct.nodaste.com` on every command or set it:

```bash
doct-agent auth default --base-url https://doct.nodaste.com
```

If not authenticated:

1. Ask the doct owner to generate and approve a selected-agent enrollment code.
2. `doct-agent auth login --base-url https://doct.nodaste.com` (develop: `https://doct.develop.nodaste.com`).
3. Paste the enrollment code when prompted, or pass `--enrollment-code <code>`.
4. Fallback: `doct-agent auth import-pat --base-url <url> --token <doct_pat_v1_...>`.

The CLI discovers and stores the collaboration websocket URL after auth; pass `--websocket-url` only to override. For one-off automation, `DOCT_AGENT_PAT` overrides the stored token only when paired with an explicit `--base-url`.

## Resolve the target first

Accept any of: a full doct URL, document id, workspace + path/title, or registered plan URL/id.

- Doct document URLs look like `https://doct.nodaste.com/d/<workspace-handle>/docs/<document-id>` — parse `<document-id>` from `/docs/<uuid>`, then use `doct-agent documents get --id <id>` or `doct-agent plans show --id <id>` for plan artifacts.
- Discover with `doct-agent workspaces list --base-url https://doct.nodaste.com --json`, then `doct-agent documents list --workspace-id <id> --json`.
- If still ambiguous, ask for exactly one missing locator: document URL, document/plan id, or workspace + path.

## Command map by task

| Task | Command |
|------|---------|
| Check auth / identity | `doct-agent auth status --all --json` · `doct-agent context --base-url https://doct.nodaste.com --json` |
| Set default endpoint | `doct-agent auth default --base-url https://doct.nodaste.com` |
| List workspaces | `doct-agent workspaces list --base-url https://doct.nodaste.com --json` |
| List documents | `doct-agent documents list --workspace-id <id> --json` |
| Read a text document | `doct-agent documents get --id <id> --text` (markdown) or `--json` (metadata); or `--workspace-id <id> --path '<path>'` |
| Create a text document | `doct-agent documents create --workspace-id <id> --title <t> --path <p> --kind text --content '# ...'` (published by default; add `--status draft` for a hidden draft; `--parent-id` to nest) |
| Replace full text body | `doct-agent documents replace-body --id <id> --file prepared.md` (or `--text` / `--stdin`) |
| Append to text body | `doct-agent collab edit --document-id <id> --append-markdown '...'` |
| Surgical text edit | `doct-agent collab anchored <replace\|insert-before\|insert-after\|delete> --document-id <id> --selected-text '...' [--text '...']` |
| Add a text-doc comment thread | `doct-agent collab comments add --document-id <id> --selected-text '...' --body '...'` |
| List / reply / resolve text-doc comments | `doct-agent collab comments <list\|reply\|resolve\|unresolve> --document-id <id>` |
| Register an HTML plan | `doct-agent plans register --base-url https://doct.nodaste.com --file thoughts/plans/<plan>.html --source-format html --allow-untemplated --json` |
| Register a Markdoc plan | `doct-agent plans register --base-url https://doct.nodaste.com --file thoughts/plans/<plan>.markdoc --source-format markdoc --json` |
| Update a registered plan | `doct-agent plans update --id <document-id> --workspace-id <workspace-id> --file thoughts/plans/<plan>.html --source-format html --expected-version <version> --json` |
| Show a registered plan | `doct-agent plans show --id <document-id> --json` |
| Watch/sync a plan file | `doct-agent plans watch --id <document-id> --workspace-id <workspace-id> --file thoughts/plans/<plan>.html --json` |
| Inspect plan queue | `doct-agent plans queue list --workspace-id <workspace-id> --document-id <document-id> --json` |
| Claim next plan item | `doct-agent plans agent next --workspace-id <workspace-id> --document-id <document-id> --json` |
| Reply / ack / resolve plan item | `doct-agent plans <reply\|ack\|resolve> ... --thread-id <thread-id> --claim-id <claim-id> --json` |
| Plan lifecycle / board | `doct-agent plans lifecycle --document-id <id> --workspace-id <id> --state active --json`; `doct-agent plans board list|set ...` |
| Title / status | `doct-agent documents update-metadata --id <id> --title <t> --status <s>` |
| Rename | `doct-agent documents rename --id <id> --workspace-id <id> --title <t>` |
| Move / reorder | `doct-agent documents move --id <id> --workspace-id <id> --new-parent-id <id>` |
| Delete | `doct-agent documents delete --id <id> --workspace-id <id>` |
| Read-only ops triage | `doct-agent triage <run\|logs\|db-query\|db-tables\|db-describe\|...>` |

### Text edit notes

- `replace-body` is the safe path for a full text-document rewrite.
- For anchored edits and comments, build `--selected-text` from the document's **visible prose**, not markdown syntax. Add prefix/suffix context when a quote is ambiguous.
- Bootstrap empty or near-empty documents with creation-time `--content` or `collab edit --append-markdown` until there is anchorable text to target.

## Special default: coding and HTML plans

If the user asks to **send, publish, copy, save, register, or review a coding plan in doct**, prefer Doct plan registration over text-document publishing.

For HTML plans:

```bash
doct-agent plans register \
  --base-url https://doct.nodaste.com \
  --file thoughts/plans/<plan>.html \
  --source-format html \
  --allow-untemplated \
  --json
```

For Markdoc plans:

```bash
doct-agent plans register \
  --base-url https://doct.nodaste.com \
  --file thoughts/plans/<plan>.markdoc \
  --source-format markdoc \
  --json
```

Use `documents publish-plan` only as a legacy fallback when the CLI explicitly directs you there for old Markdown/text-plan flows. Current `doct-agent onboard` says `documents publish-plan` fails closed with replacement guidance for plan-review publishing.

Return the created/updated Doct URL, document/plan id, workspace id, and current version when available.

## Decision rules

- One tool: `doct-agent`. Reads and discovery are safe to run freely.
- Production plan registration defaults to `https://doct.nodaste.com`; develop is opt-in.
- Confirm before create / replace-body / delete / move on documents you did not create, and before publishing into shared workspaces.
- `doct-agent triage` is read-only operational triage (DB checks and Railway logs) — use it to inspect state, not to mutate.
- For visual verification inside doct, use browser automation after approval.

## References

- `references/doct-agent-commands.md` — full per-command reference, flags, and worked examples.
- `doct-agent onboard` — the canonical, always-current spec from the installed CLI.
