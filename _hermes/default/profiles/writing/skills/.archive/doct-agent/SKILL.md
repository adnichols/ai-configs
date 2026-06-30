---
name: doct-agent
description: Agent-focused CLI for the doct document collaboration platform. Read, create, edit, and comment on doct documents from the terminal.
version: 1.0.0
---

# doct-agent

Agent-focused CLI for the **doct** document collaboration platform. Use this skill to read, create, edit, and comment on doct documents from the terminal.

## Prerequisites

- `doct-agent` installed (typically via Homebrew: `/opt/homebrew/bin/doct-agent`)
- Authenticated session (`doct-agent auth status` should show logged-in state)

## Authentication

```bash
# Interactive browser login
doct-agent auth login

# Or import an existing personal access token
doct-agent auth import-pat

# Check current auth state
doct-agent auth status

# Log out
doct-agent auth logout
```

## Context & Onboarding

```bash
# Show current workspace/user context
doct-agent context

# Same, as JSON
doct-agent context --json

# Onboarding info
doct-agent onboard
doct-agent onboard --json
```

## Workspaces

```bash
# List accessible workspaces
doct-agent workspaces list
```

## Documents

### List documents
```bash
doct-agent documents list --workspace-id <WORKSPACE_ID> [--json]
```

### Get a document
```bash
# By ID
doct-agent documents get --id <ID> [--text] [--json]

# By workspace + path
doct-agent documents get --workspace-id <WORKSPACE_ID> --path <PATH> [--text] [--json]
```
Use `--text` to extract plain text content.

### Create a document
```bash
doct-agent documents create \
  --workspace-id <WORKSPACE_ID> \
  --title "My Document" \
  --path "/folder/name" \
  --kind <KIND> \
  [--content "Initial markdown"] \
  [--status published] \
  [--parent-id <PARENT_ID>] \
  [--display-order <N>] \
  [--json]
```

### Update metadata
```bash
doct-agent documents update-metadata \
  --id <ID> \
  [--title "New Title"] \
  [--status draft|published] \
  [--json]
```

### Rename, move, delete
```bash
# Rename
doct-agent documents rename --id <ID> --workspace-id <WORKSPACE_ID> --title "New Title" [--json]

# Move (reparent or reorder)
doct-agent documents move --id <ID> --workspace-id <WORKSPACE_ID> \
  [--new-parent-id <PARENT_ID>] \
  [--new-display-order <N>] \
  [--json]

# Delete by ID, workspace+path, or just ID
doct-agent documents delete --id <ID> [--json]
```

## Collaboration

### Append content
```bash
doct-agent collab edit \
  --document-id <DOCUMENT_ID> \
  --append-markdown "## New Section\n\nContent here." \
  [--websocket-url <URL>] \
  [--json]
```

### Anchored edits (precise text surgery)
All anchored commands accept optional `--prefix-text` and `--suffix-text` to disambiguate the target.

```bash
# Replace selected text
doct-agent collab anchored replace \
  --document-id <DOCUMENT_ID> \
  --selected-text "old phrase" \
  --text "new phrase" \
  [--prefix-text "..."] \
  [--suffix-text "..."] \
  [--json]

# Insert before selected text
doct-agent collab anchored insert-before \
  --document-id <DOCUMENT_ID> \
  --selected-text "anchor phrase" \
  --text "inserted text" \
  [--prefix-text "..."] \
  [--suffix-text "..."] \
  [--json]

# Insert after selected text
doct-agent collab anchored insert-after \
  --document-id <DOCUMENT_ID> \
  --selected-text "anchor phrase" \
  --text "inserted text" \
  [--prefix-text "..."] \
  [--suffix-text "..."] \
  [--json]

# Delete selected text
doct-agent collab anchored delete \
  --document-id <DOCUMENT_ID> \
  --selected-text "text to remove" \
  [--prefix-text "..."] \
  [--suffix-text "..."] \
  [--json]
```

### Comments
```bash
# List comments on a document
doct-agent collab comments list --document-id <DOCUMENT_ID> [--json]

# Add a comment on selected text
doct-agent collab comments add \
  --document-id <DOCUMENT_ID> \
  --selected-text "the quoted passage" \
  --body "Feedback goes here." \
  [--preferred-from <USER_ID>] \
  [--prefix-text "..."] \
  [--suffix-text "..."] \
  [--json]

# Reply to a comment
doct-agent collab comments reply \
  --document-id <DOCUMENT_ID> \
  --selected-text "..." \
  --body "Reply text." \
  [--preferred-from <USER_ID>] \
  [--prefix-text "..."] \
  [--suffix-text "..."] \
  [--json]

# Resolve / unresolve
doct-agent collab comments resolve --document-id <DOCUMENT_ID> --selected-text "..." [--json]
doct-agent collab comments unresolve --document-id <DOCUMENT_ID> --selected-text "..." [--json]

# List mentions
doct-agent collab comments mentions --document-id <DOCUMENT_ID> [--json]
```

## Pitfalls

- **Unauthenticated**: Most commands fail with `no local authentication found; run doct-agent auth login or doct-agent auth import-pat`. Always check auth first.
- **macOS config location mismatch**: On macOS, doct-agent stores auth under `~/Library/Application Support/dev.doct.doct-agent/` (config.json + pat file). If the CLI cannot find auth despite a prior login, check that directory. There may also be an older `~/.config/doct-cli/config.json` from a legacy CLI — do not confuse the two. If `auth status` fails, try `auth import-pat` with `--base-url`, `--websocket-url`, and the raw token string from the `pat` file.
- **Ambiguous anchors**: If `--selected-text` appears multiple times in a document, the command may fail or target the wrong occurrence. Use `--prefix-text` and `--suffix-text` to narrow the match.
- **Workspace required**: `documents list`, `create`, `rename`, and `move` require `--workspace-id`.
- **IDs vs paths**: Some commands accept `--id`, others accept `--workspace-id` + `--path`, and some accept either. Prefer `--id` when you have it; use `--path` when resolving from human-readable location.
- **JSON output**: Append `--json` to any command when parsing output programmatically.

## Typical Workflows

### Review a document and leave comments
1. `doct-agent documents get --id <ID> --text` → read content.
2. `doct-agent collab comments add --document-id <ID> --selected-text "..." --body "..."` → leave feedback.

### Auth recovery (macOS)
If `auth status` fails after prior login, see `references/auth-troubleshooting.md` for config paths and re-import steps.

### Quick edit
1. `doct-agent documents get --id <ID> --text` → inspect.
2. `doct-agent collab anchored replace --document-id <ID> --selected-text "..." --text "..."` → precise fix.

### Create and publish
1. `doct-agent workspaces list` → pick workspace.
2. `doct-agent documents create --workspace-id <WID> --title "..." --path "/..." --kind <KIND> --content "..."`.
