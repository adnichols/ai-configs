# doct-agent command reference

Full reference for the `doct-agent` CLI. This is the **only** supported way to operate doct from an agent — no `doct-cli`, no raw REST, no hand-written Yjs/Hocuspocus scripts. `doct-agent` wraps REST (discovery, reads, creation, metadata) and the Yjs/Hocuspocus collaborative path (text-body edits, comments) behind verified commands.

For the canonical, always-current version of this spec, run `doct-agent onboard` (add `--json` for structured output). When the CLI and this file disagree, trust the CLI.

## Top-level commands

```
doct-agent auth         # login / status / token import / logout
doct-agent context      # agent identity, base URL, websocket URL, instructions
doct-agent onboard      # canonical onboarding + runtime spec
doct-agent workspaces   # list workspaces
doct-agent documents    # list / get / create / replace-body / publish-plan / update-metadata / rename / move / delete
doct-agent collab       # edit / anchored / comments (realtime Yjs surfaces)
doct-agent triage       # read-only DB + log operational triage
```

Almost every command accepts `--json`.

## Install and storage

- Install/update via Homebrew only, from the doct repo root:
  ```bash
  brew tap local/doct "$(pwd)"
  brew install --build-from-source local/doct/doct-agent
  # refresh an existing install:
  brew reinstall --build-from-source local/doct/doct-agent
  ```
- Do not copy Cargo build artifacts into `~/.local/bin` or other ad hoc paths, and do not use alternate CLI binaries, wrapper scripts, or token-store fallbacks.
- Config lives under the platform user config directory. The token is held in a restrictive-permission plaintext PAT file fallback. `DOCT_AGENT_PAT` overrides the stored token for one-off automation and is the only supported token environment override.

## Auth

```bash
doct-agent auth status [--json]
doct-agent auth login --base-url https://doct.nodaste.com [--enrollment-code <code>] [--websocket-url <wss-url>]
doct-agent auth import-pat --base-url <url> --token <doct_pat_v1_...> [--websocket-url <wss-url>]
doct-agent auth logout
```

- Owner must generate and approve a **selected-agent enrollment code** before `auth login`.
- The websocket URL is discovered and stored automatically; `--websocket-url` is an override only.
- Environments: production `https://doct.nodaste.com`, develop `https://doct.develop.nodaste.com`.

## Context

```bash
doct-agent context [--json]
```

Returns the agent identity (`agent.id`, `displayName`, `ownerUserId`), the deployment (`baseUrl`, `websocketUrl`), and any system/agent instructions. Use it to confirm you are pointed at the right deployment before mutating anything.

## Workspaces

```bash
doct-agent workspaces list [--json]
```

Each workspace has `id`, `handle`, `slug`, `name`, and `isPersonal`. The personal workspace has `isPersonal: true` (used as the default for `publish-plan`).

## Documents

### List

```bash
doct-agent documents list --workspace-id <id> [--json]
```

### Get / read

```bash
# by id
doct-agent documents get --id <document-id> --text        # markdown body
doct-agent documents get --id <document-id> --json         # metadata + content

# by workspace + path
doct-agent documents get --workspace-id <id> --path '<doc/path>' --text
```

`--text` returns markdown. Note: markdown is **not** the authoritative selection surface for anchored edits/comments — see "Anchored selection surface" below.

### Create

```bash
doct-agent documents create \
  --workspace-id <id> \
  --title '<title>' \
  --path '<doc/path>' \
  --kind text \
  [--content '# Visible document'] \
  [--status draft] \
  [--parent-id <parent-document-id>] \
  [--display-order <n>] \
  [--json]
```

- Published by default. Use `--status draft` only for the explicit hidden-draft path.
- Provide `--content` at creation time to bootstrap a body (also gives anchorable text for later anchored edits).
- `--parent-id` nests the new document under an existing one.

### Replace full body

```bash
doct-agent documents replace-body --id <document-id> (--file prepared.md | --text '<markdown>' | --stdin) [--json]
```

Replaces the entire text-document body through the supported Hocuspocus/Yjs-safe server path and returns verified readback metadata. This is the right tool for a full rewrite.

### Metadata, rename, move, delete

```bash
doct-agent documents update-metadata --id <id> [--title '<t>'] [--status <published|draft|...>] [--json]
doct-agent documents rename --id <id> --workspace-id <wsid> --title '<new title>' [--json]
doct-agent documents move --id <id> --workspace-id <wsid> [--new-parent-id <id>] [--new-display-order <n>] [--json]
doct-agent documents delete (--id <id> | --path '<path>') [--workspace-id <wsid>] [--json]
```

### Publish a coding plan

```bash
doct-agent documents publish-plan --file /path/to/plan.md [--title '<title>'] [--parent-title 'Coding Plans'] [--workspace personal|<id-or-slug>] [--json]
```

Defaults to the personal workspace and a `Coding Plans` parent document (created if missing), as a new text child. Title defaults to the first H1 in the file. This is the default destination whenever the user asks to send/publish/save a coding plan to doct.

## Collab (realtime text surfaces)

### Append

```bash
doct-agent collab edit --document-id <id> --append-markdown '\n\nAppended by agent' [--websocket-url <wss>] [--json]
```

Append-only text edit over websocket/Hocuspocus. Also the way to add anchorable text to an empty document.

### Anchored surgical edits

```bash
doct-agent collab anchored replace        --document-id <id> --selected-text 'target text' --text 'replacement text'
doct-agent collab anchored insert-before  --document-id <id> --selected-text 'target text' --text 'prefix text'
doct-agent collab anchored insert-after   --document-id <id> --selected-text 'target text' --text 'suffix text'
doct-agent collab anchored delete         --document-id <id> --selected-text 'target text'
```

Optional `--prefix-text` / `--suffix-text` disambiguate a repeated quote. These persist through collaborative Yjs mutations under the hood.

### Comments

```bash
doct-agent collab comments add       --document-id <id> --selected-text 'target text' --body 'initial thread body' [--prefix-text '...'] [--suffix-text '...'] [--preferred-from '...']
doct-agent collab comments list      --document-id <id> [--json]
doct-agent collab comments reply     --document-id <id> ...
doct-agent collab comments resolve   --document-id <id> ...
doct-agent collab comments unresolve --document-id <id> ...
doct-agent collab comments mentions  --workspace-id <id> [--json]
```

`comments list` works for text documents — this is the supported way to inspect existing text-doc comments (no browser/DB workaround needed).

### Anchored selection surface

Build `--selected-text`, `--prefix-text`, and `--suffix-text` from the document's **normalized collaborative plain-text view** (visible prose), not from markdown syntax. `documents get --text` returns markdown only. In practice: select on the words a reader sees, not on `**`, `#`, list markers, or link syntax. Bootstrap empty/near-empty docs with creation-time `--content` or `collab edit --append-markdown` until anchorable text exists.

Websocket auth uses the raw PAT string, never a `Bearer ` prefix (handled internally by `doct-agent`).

## Triage (read-only operations surface)

```bash
doct-agent triage run <db|doct|doct-hocuspocus> <preview|production|develop> [--log-limit n] [--log-since ...] [--log-until ...] [--json|--human]
doct-agent triage logs <doct|doct-hocuspocus> <preview|production|develop> [--limit n] [--since ...] [--until ...] [--json|--human]
doct-agent triage db-query --sql '<sql>' <preview|production|develop> [--json|--human]
doct-agent triage db-tables <env>
doct-agent triage db-describe <env> ...
doct-agent triage db-check-text-missing-yjs <env>
doct-agent triage db-top-yjs-updates <env>
doct-agent triage db-recent-yjs-updates <env>
```

Use triage to inspect DB state and Railway logs when something is failing. It is read-only — never the path for mutations.

## High-value command quicklist

```bash
doct-agent auth status
doct-agent context
doct-agent workspaces list
doct-agent documents list --workspace-id <id> --json
doct-agent documents get --id <document-id> --text
doct-agent documents create --workspace-id <id> --title 'Title' --path 'notes/title' --kind text --content '# Visible document'
doct-agent documents replace-body --id <document-id> --file prepared.md --json
doct-agent documents publish-plan --file thoughts/plans/example.md --title 'Example Plan' --json
doct-agent collab edit --document-id <id> --append-markdown '\n\nAppended by agent'
doct-agent collab anchored replace --document-id <id> --selected-text 'target text' --text 'replacement text'
doct-agent collab comments add --document-id <id> --selected-text 'target text' --body 'initial thread body'
doct-agent collab comments mentions --workspace-id <id>
doct-agent triage logs doct production --limit 50 --json
```
