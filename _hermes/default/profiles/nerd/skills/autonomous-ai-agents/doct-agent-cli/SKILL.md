---
name: doct-agent-cli
description: Use the `doct-agent` CLI command for doct agent auth, workspace discovery, document operations, collaborative editing, and comments.
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [doct, cli, docs, collaboration]
prerequisites:
  commands: [doct-agent]
---

# doct-agent CLI

Use this skill when a request involves **the `doct-agent` command**.

`doct-agent` is a CLI for agent-focused doct operations. Prefer it over hand-rolled curl/python when the task is about doct agent auth or agent-driven doct document work.

## Verify first

```bash
doct-agent --help
doct-agent auth status --json
```

## Quick reference

| Action | Command |
|---|---|
| Check auth | `doct-agent auth status --json` |
| Login with enrollment code | `doct-agent auth login --base-url <url> --enrollment-code <code> --json` |
| Show agent context | `doct-agent context --json` |
| List workspaces | `doct-agent workspaces list --json` |
| List docs | `doct-agent documents list --workspace-id <id> --json` |
| Get doc content | `doct-agent documents get --id <id> --text` |
| Create doc | `doct-agent documents create --workspace-id <id> --title <t> --path <p> --kind text --content '<md>' --json` |
| Append markdown | `doct-agent collab edit --document-id <id> --append-markdown '<md>' --json` |
| Add comment | `doct-agent collab comments add --document-id <id> --selected-text '<text>' --body '<comment>' --json` |
| Reply to comment | `doct-agent collab comments reply --document-id <id> --thread-id <tid> --body '<reply>' --json` |
| Resolve thread | `doct-agent collab comments resolve --document-id <id> --thread-id <tid> --json` |

## Default workflow

1. Check `doct-agent auth status --json`.
2. If needed, authenticate with `doct-agent auth login ... --json`.
3. Discover the workspace/document with `workspaces list` and `documents list`.
4. Use `documents` subcommands for create/read/metadata operations.
5. Use `collab` subcommands for collaborative edits and comments.
6. Return the resulting doct URL or document id when you create or move something.

## Runtime rules

- Prefer `--json` whenever available.
- REST-style document operations go through `doct-agent documents ...`.
- Existing text edits go through `doct-agent collab edit`.
- Anchored comments go through `doct-agent collab comments ...`.
- Websocket auth uses the raw PAT string, not a `Bearer ` prefix.

## Known quirks

- `collab edit` is append-only. There is no replace-content command.
- `collab comments list` may hang; write operations are more reliable than listing.
- `documents list --json` currently returns a bare JSON array of documents, not an object like `{ "documents": [...] }`. Parse the top level accordingly.
- If you need to pass markdown containing backticks, parentheses, or other shell-sensitive characters to `collab edit --append-markdown`, prefer calling `doct-agent` via Python `subprocess.run([...])` or another argv-safe path instead of inline shell quoting. A naive quoted shell string can silently lose content via command substitution.
- If production collab fails with `no websocket URL configured`, first update the CLI and re-run `doct-agent auth status --json`.
- On Aaron's machine, the config can still show the wrong default websocket (`wss://doct.nodaste.com`) even though collab edits succeed against `wss://p.doct.nodaste.com`.
- Check and fix persistent config in `~/Library/Application Support/dev.doct.doct-agent-cli/config.json` so `websocket_url` is `wss://p.doct.nodaste.com`.
- Current builds otherwise auto-default production collab traffic to `wss://p.doct.nodaste.com` when using `https://doct.nodaste.com`.
- When iterating on a doct doc for Aaron, preserve the existing permalink by editing in place; if true in-place editing is unavailable, say so explicitly rather than recreating the doc.

## Editing existing docs

Current CLI support visible from `doct-agent collab edit --help` is append-only:
- `doct-agent collab edit --document-id <id> --append-markdown ...`

That means Hermes should **not** delete and recreate an existing doct document just to revise it. Doing so loses continuity, breaks links, and is the wrong default for collaborative drafting.

If the user asks to iterate on an existing doct doc:
1. Keep the same document id.
2. Prefer an in-place edit path if the available doct surface supports it.
3. If the CLI available to Hermes only supports append, either append a clearly marked revision section or stop and tell the user the exact limitation instead of recreating the document.
4. Only recreate a document if the user explicitly asks for replacement and accepts the history/link break.

## Guardrails

- Do not hand-roll enrollment if `doct-agent auth login` can do it.
- Do not assume auth failed before checking `doct-agent auth status --json`.
- Do not promise exact user/workspace ids without reading them from the CLI.
- Never delete/recreate an existing doct doc for routine revisions unless the user explicitly wants that tradeoff.
- Prefer a short Discord summary with detailed doct/Obsidian docs when the output is long.
