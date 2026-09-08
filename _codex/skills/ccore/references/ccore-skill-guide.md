# C-Core Skill Guide

## Overview

C-Core is a local-first knowledge graph system with two parts:

- `ccore-node`: HTTP API server and local data store.
- `ccore` CLI: operator and agent interface for common workflows.

The CLI defaults to `http://127.0.0.1:8787` and can target another node with `--url`.

Product direction: C-Core is agent-first. The `ccore` CLI is currently the
primary local agent interface. `ccore mcp` is the stdio MCP server over the
existing `ccore-node` and CLI/runtime substrate that we are growing into as the
long-term agent surface. The local HTTP API remains the underlying substrate.

## Concepts

- **Space**: top-level namespace for documents and graph state.
- **Document**: an item in a space with versions and metadata.
- **Version**: immutable content snapshot for a document update.
- **Ingest run**: a tracked import job (for example, Obsidian ingest).
- **Connector**: integration endpoint that imports external content into a space.
- **Links**: graph edges between documents (backlinks and outlinks).
- **Search**: relevance query scoped to one space.

## Workflows

### Create a space

1. Check node health: `ccore health`
2. Create a space: `ccore space create <slug> <display_name>`
3. List spaces: `ccore space list`

### Ingest an Obsidian vault

1. Start ingest: `ccore ingest obsidian <space> <vault_path>`
2. Track status: `ccore ingest status <ingest_run_id>`

### Ingest Slack fixture events

1. Start ingest: `ccore ingest slack-fixture <space> <fixture_path> [--workspace-id <id>]`
2. Track status: `ccore ingest status <ingest_run_id>`

### Browse and search

1. List docs: `ccore doc list <space>`
2. Show doc: `ccore doc show <document_id>`
3. Search (legacy document-only compatibility path): `ccore search <space> <query>`
4. Ranked authority/freshness query: `ccore query <space> <query> [--kinds documents,decision_records,canonical_packages]`

Compatibility notes:

- `ccore search` stays on legacy `GET /v1/spaces/{space_id}/search` for document-only compatibility.
- `ccore query` calls `POST /v1/spaces/{space_id}/query` and returns authority/freshness explanations for ranked results.

### Inspect artifacts

1. List artifacts: `ccore artifact list <space>`
2. Show artifact metadata: `ccore artifact show <artifact_id>`
3. Read artifact bytes/text: `ccore artifact cat <artifact_id>`
4. Inspect artifact references: `ccore artifact references <artifact_id>`

### Explore graph links

1. Backlinks: `ccore links backlinks <space> <document>`
2. Outlinks: `ccore links outlinks <space> <document>`

### Decision memory and canonical packages

1. Promote a decision record: `ccore decision create <space> --kind <kind> --input-refs '<json>' --output '<json>' --approvals '<json>'`
2. Discover decisions: `ccore decision list <space> [--kind <kind>] [--query <text>]`
3. Inspect one decision: `ccore decision show <decision_record_id>`
4. Promote a canonical package: `ccore package promote <space> --label <label> --contents '<json>' --approvals '<json>'`
5. Discover packages: `ccore package list <space> [--label <label>] [--query <text>]`
6. Inspect/consume a package: `ccore package show <package_id>` then `ccore package consume <package_id> [--action <action>] [--metadata '<json>']`

### Sync and sharing

1. Check sync status: `ccore space sync-status <space>`
2. Push local changes: `ccore space sync-push <space>`
3. Pull remote changes: `ccore space sync-pull <space>`
4. Create an invite code: `ccore space invite <space> --code`
5. Import an invite code: `ccore space invite-import <ccore_inv_code>`

## Identity and Caveats

- Obsidian ingest can write stable document IDs into frontmatter (`ccore_id` by default).
- `write_frontmatter_id=true` is the default and keeps note identity stable across rename/move.
- If `write_frontmatter_id=false`, identity falls back to path-derived deterministic IDs and rename stability is not guaranteed.
- `vault_id` should stay stable per vault; changing it can create identity drift.
- File renames are expected and should not break identity when IDs are present.
- Malformed YAML frontmatter may reduce ingest fidelity; fix frontmatter and rerun ingest.
- Many commands accept space and document references by human-readable values, but UUIDs are always accepted.

## Troubleshooting

- Node reachability: run `ccore health` and verify `--url`.
- Port mismatch: default node URL is `http://127.0.0.1:8787`.
- Missing data: check node startup data-dir configuration and retry.
- Ambiguous refs: pass UUIDs when names or titles collide.
- Ingest failures: inspect `ccore ingest status <ingest_run_id>` for details.

## Shell completions

Generate scripts with `ccore completions <shell>`.

- bash: `source <(ccore completions bash)`
- zsh: `source <(ccore completions zsh)`
- fish: `ccore completions fish > ~/.config/fish/completions/ccore.fish`
- powershell: `ccore completions powershell | Out-String | Invoke-Expression`
- elvish: `eval (ccore completions elvish)`

## Complete CLI reference

Generated from the live clap command model in this binary.

### `ccore`

```text
C-Core CLI for local knowledge graph operations.

Use this tool to manage spaces/documents, run ingest pipelines, inspect links, search, and run ranked authority/freshness queries.

Agent workflow: run `ccore skill` first to get the curated guide and complete command reference. Use `ccore skill --output <path>` to save and reuse the guide.

Usage: ccore [OPTIONS] <COMMAND>

Commands:
  skill            Print the C-Core skill guide with workflows and full CLI reference
  completions      Generate shell completion scripts for the selected shell
  mcp              Start the local MCP server over stdio
  config           Show effective CLI/runtime configuration
  hub              Cloudflare Sync Hub tooling (secrets/bootstrap helpers)
  init             Initialize account session and personal space sync
  health           Check node health endpoint
  identity         Read node identity defaults and configured actor selectors
  sync             Inspect automatic sync state across spaces
  space            Manage spaces
  doc              Manage documents in a space
  object           Manage typed managed objects on canonical documents
  project          Manage project registry objects
  project-context  Manage project context objects
  clarification    Manage transcript clarification objects
  signal           Manage runtime-critical signals on canonical documents
  ingest           Run and inspect ingest pipelines
  artifact         Inspect and retrieve binary artifacts
  links            Explore graph links between documents
  workstream       Manage resumable workstreams
  session          Manage resumable work sessions
  transcript       Read and append session transcript history
  activity         Inspect low-churn activity history
  search           Legacy compatibility path: search documents within a space
  query            Ranked authority/freshness query across supported object kinds in a space
  decision         Manage immutable decision records
  package          Manage canonical context packages
  help             Print this message or the help of the given subcommand(s)

Options:
      --config <CONFIG>
          Path to the C-Core config file

      --url <URL>
          C-Core node base URL. Overrides configured/default URL

  -h, --help
          Print help (see a summary with '-h')

  -V, --version
          Print version

Agent tip: start with `ccore skill` (or `ccore skill --output <path>`) before invoking other commands.
```

### `ccore skill`

```text
Print the C-Core skill guide with workflows and full CLI reference

Usage: skill [OPTIONS]

Options:
      --output <OUTPUT>
          Write skill markdown to a file instead of stdout

  -h, --help
          Print help
```

### `ccore completions`

```text
Generate shell completion scripts for the selected shell

Usage: completions [OPTIONS] <SHELL>

Arguments:
  <SHELL>
          Target shell for completion generation

          [possible values: bash, zsh, fish, powershell, elvish]

Options:
      --output <OUTPUT>
          Write completion script to a file instead of stdout

  -h, --help
          Print help
```

### `ccore mcp`

```text
Start the local MCP server over stdio

Usage: mcp [OPTIONS]

Options:
      --transport <TRANSPORT>
          Transport selection (first release: stdio only)

          [default: stdio]

  -h, --help
          Print help
```

### `ccore config`

```text
Show effective CLI/runtime configuration

Usage: config <COMMAND>

Commands:
  show
  help  Print this message or the help of the given subcommand(s)

Options:
  -h, --help
          Print help
```

### `ccore config show`

```text
Usage: show

Options:
  -h, --help
          Print help
```

### `ccore config help`

```text
Print this message or the help of the given subcommand(s)

Usage: help [COMMAND]...

Arguments:
  [COMMAND]...
          Print help for the subcommand(s)
```

### `ccore hub`

```text
Cloudflare Sync Hub tooling (secrets/bootstrap helpers)

Usage: hub <COMMAND>

Commands:
  login    Store bootstrap auth for automatic hub provisioning
  status   Show bootstrap auth status (never prints secrets)
  logout   Remove locally stored bootstrap auth
  config   Manage hub tool configuration (stored in the user config dir)
  secrets  Ensure required Cloudflare hub secrets exist
  help     Print this message or the help of the given subcommand(s)

Options:
  -h, --help
          Print help
```

### `ccore hub login`

```text
Store bootstrap auth for automatic hub provisioning

Usage: login [OPTIONS]

Options:
      --hub-url <HUB_URL>
          Hub base URL

      --account-token <ACCOUNT_TOKEN>
          Hub bootstrap account token

      --passphrase <PASSPHRASE>
          Passphrase used to encrypt local bootstrap auth. Defaults to `CCORE_PASSPHRASE`, with `CCORE_HUB_PASSPHRASE` as an override

      --hub-config <HUB_CONFIG>
          Override hub tool config path

  -h, --help
          Print help
```

### `ccore hub status`

```text
Show bootstrap auth status (never prints secrets)

Usage: status [OPTIONS]

Options:
      --hub-config <HUB_CONFIG>
          Override hub tool config path

  -h, --help
          Print help
```

### `ccore hub logout`

```text
Remove locally stored bootstrap auth

Usage: logout [OPTIONS]

Options:
      --hub-config <HUB_CONFIG>
          Override hub tool config path

  -h, --help
          Print help
```

### `ccore hub config`

```text
Manage hub tool configuration (stored in the user config dir)

Usage: config <COMMAND>

Commands:
  path  Print the hub tool config path
  show  Show effective hub tool config (redacted)
  init  Initialize or update hub tool config
  help  Print this message or the help of the given subcommand(s)

Options:
  -h, --help
          Print help
```

### `ccore hub config path`

```text
Print the hub tool config path

Usage: path

Options:
  -h, --help
          Print help
```

### `ccore hub config show`

```text
Show effective hub tool config (redacted)

Usage: show [OPTIONS]

Options:
      --hub-config <HUB_CONFIG>
          Override hub tool config path

  -h, --help
          Print help
```

### `ccore hub config init`

```text
Initialize or update hub tool config

Usage: init [OPTIONS] --project-dir <PROJECT_DIR>

Options:
      --project-dir <PROJECT_DIR>
          Hub project directory containing wrangler.toml

      --default-env <DEFAULT_ENV>
          Default Wrangler environment (dev|staging|prod)

          [possible values: dev, staging, prod]

      --hub-config <HUB_CONFIG>
          Override hub tool config path

  -h, --help
          Print help
```

### `ccore hub config help`

```text
Print this message or the help of the given subcommand(s)

Usage: help [COMMAND]...

Arguments:
  [COMMAND]...
          Print help for the subcommand(s)
```

### `ccore hub secrets`

```text
Ensure required Cloudflare hub secrets exist

Usage: secrets <COMMAND>

Commands:
  ensure  Create TOKEN_HASH_SECRET and INTERNAL_API_KEY if missing
  help    Print this message or the help of the given subcommand(s)

Options:
  -h, --help
          Print help
```

### `ccore hub secrets ensure`

```text
Create TOKEN_HASH_SECRET and INTERNAL_API_KEY if missing

Usage: ensure [OPTIONS]

Options:
      --env <ENV>
          Wrangler environment (dev|staging|prod)

          [possible values: dev, staging, prod]

      --project-dir <PROJECT_DIR>
          Hub project directory containing wrangler.toml

      --hub-config <HUB_CONFIG>
          Override hub tool config path

  -h, --help
          Print help
```

### `ccore hub secrets help`

```text
Print this message or the help of the given subcommand(s)

Usage: help [COMMAND]...

Arguments:
  [COMMAND]...
          Print help for the subcommand(s)
```

### `ccore hub help`

```text
Print this message or the help of the given subcommand(s)

Usage: help [COMMAND]...

Arguments:
  [COMMAND]...
          Print help for the subcommand(s)
```

### `ccore init`

```text
Initialize account session and personal space sync

Usage: init [OPTIONS]

Options:
      --hub-url <HUB_URL>
          Hub base URL

      --account-handle <ACCOUNT_HANDLE>
          Account handle (e.g. alice)

      --space-key <SPACE_KEY>
          Optional local space key override

      --display-name <DISPLAY_NAME>
          Personal space display name sent to control-plane ensure

      --remote <REMOTE>
          Sync remote name for local wiring (default: primary)

  -h, --help
          Print help
```

### `ccore health`

```text
Check node health endpoint

Usage: health

Options:
  -h, --help
          Print help
```

### `ccore identity`

```text
Read node identity defaults and configured actor selectors

Usage: identity [OPTIONS]

Options:
      --json
          Emit raw JSON instead of human-readable output

  -h, --help
          Print help
```

### `ccore sync`

```text
Inspect automatic sync state across spaces

Usage: sync <COMMAND>

Commands:
  status  Show node-wide sync status across configured spaces
  help    Print this message or the help of the given subcommand(s)

Options:
  -h, --help
          Print help
```

### `ccore sync status`

```text
Show node-wide sync status across configured spaces

Usage: status [OPTIONS]

Options:
      --json
          Emit raw JSON instead of human-readable output

  -h, --help
          Print help
```

### `ccore sync help`

```text
Print this message or the help of the given subcommand(s)

Usage: help [COMMAND]...

Arguments:
  [COMMAND]...
          Print help for the subcommand(s)
```

### `ccore space`

```text
Manage spaces

Usage: space <COMMAND>

Commands:
  list
  create
  sync-status         Show sync cursor/head/lag against a configured remote hub
  sync-enable         Enable background auto-sync for this space
  sync-disable        Disable background auto-sync for this space
  sync-push           Diagnostic: push local outbox events to a configured remote hub now
  sync-pull           Diagnostic: pull remote hub feed entries into local sync cursor state now
  sync-configure-hub  Configure per-space sync hub credentials for push/pull/invites
  invite              Create an invite bundle for sharing this space with another node
  invite-import       Import an invite code or bundle from another machine
  trust-import        Import a reciprocal trust receipt from the receiver to complete bidirectional trust
  help                Print this message or the help of the given subcommand(s)

Options:
  -h, --help
          Print help
```

### `ccore space list`

```text
Usage: list

Options:
  -h, --help
          Print help
```

### `ccore space create`

```text
Usage: create <SLUG> <DISPLAY_NAME>

Arguments:
  <SLUG>


  <DISPLAY_NAME>


Options:
  -h, --help
          Print help
```

### `ccore space sync-status`

```text
Show sync cursor/head/lag against a configured remote hub

Usage: sync-status [OPTIONS] <SPACE>

Arguments:
  <SPACE>
          Space id, slug, or display name

Options:
      --remote <REMOTE>
          Sync remote name (default: primary)

      --json
          Emit raw JSON instead of human-readable output

  -h, --help
          Print help
```

### `ccore space sync-enable`

```text
Enable background auto-sync for this space

Usage: sync-enable <SPACE>

Arguments:
  <SPACE>
          Space id, slug, or display name

Options:
  -h, --help
          Print help
```

### `ccore space sync-disable`

```text
Disable background auto-sync for this space

Usage: sync-disable <SPACE>

Arguments:
  <SPACE>
          Space id, slug, or display name

Options:
  -h, --help
          Print help
```

### `ccore space sync-push`

```text
Diagnostic: push local outbox events to a configured remote hub now

Usage: sync-push [OPTIONS] <SPACE>

Arguments:
  <SPACE>
          Space id, slug, or display name

Options:
      --remote <REMOTE>
          Sync remote name (default: primary)

  -h, --help
          Print help
```

### `ccore space sync-pull`

```text
Diagnostic: pull remote hub feed entries into local sync cursor state now

Usage: sync-pull [OPTIONS] <SPACE>

Arguments:
  <SPACE>
          Space id, slug, or display name

Options:
      --remote <REMOTE>
          Sync remote name (default: primary)

  -h, --help
          Print help
```

### `ccore space sync-configure-hub`

```text
Configure per-space sync hub credentials for push/pull/invites

Usage: sync-configure-hub [OPTIONS] --hub-url <HUB_URL> --hub-read-token <HUB_READ_TOKEN> --hub-write-token <HUB_WRITE_TOKEN> --space-key <SPACE_KEY> <SPACE>

Arguments:
  <SPACE>
          Space id, slug, or display name

Options:
      --hub-url <HUB_URL>
          Hub base URL

      --hub-read-token <HUB_READ_TOKEN>
          Hub read token

      --hub-write-token <HUB_WRITE_TOKEN>
          Hub write token

      --space-key <SPACE_KEY>
          Local space key material

      --remote <REMOTE>
          Sync remote name (default: primary)

  -h, --help
          Print help
```

### `ccore space invite`

```text
Create an invite bundle for sharing this space with another node

Usage: invite [OPTIONS] <SPACE>

Arguments:
  <SPACE>
          Space id, slug, or display name

Options:
      --role <ROLE>
          Invite role (default: member)

          [default: member]

      --scope <SCOPE>
          Invite scope (default: read_write)

          [default: read_write]

      --label <LABEL>
          Optional invite label

      --remote <REMOTE>
          Sync remote name (default: primary)

      --hub-url <HUB_URL>
          Hub base URL used for automatic setup when sync config is missing

      --account-token <ACCOUNT_TOKEN>
          Hub bootstrap account token used for automatic setup when sync config is missing

      --passphrase <PASSPHRASE>
          Passphrase used to unlock locally stored hub bootstrap auth. Defaults to `CCORE_PASSPHRASE`, with `CCORE_HUB_PASSPHRASE` as an override

      --space-key <SPACE_KEY>
          Space key override used for automatic setup when sync config is missing

      --code
          Print only the cloud invite code

      --format <FORMAT>
          Output format (default: json)

          [default: json]
          [possible values: json, code, bundle]

      --bundle-only
          Print only the invite bundle string

  -h, --help
          Print help
```

### `ccore space invite-import`

```text
Import an invite code or bundle from another machine

Usage: invite-import [OPTIONS] [BUNDLE]

Arguments:
  [BUNDLE]
          Invite code or bundle string. If omitted, reads from --file, stdin, or prompt

Options:
      --file <FILE>
          Read invite code or bundle from a file

  -h, --help
          Print help
```

### `ccore space trust-import`

```text
Import a reciprocal trust receipt from the receiver to complete bidirectional trust

Usage: trust-import [OPTIONS] [RECEIPT]

Arguments:
  [RECEIPT]
          Trust receipt string. If omitted, reads from --file, stdin, or prompt

Options:
      --file <FILE>
          Read trust receipt from a file

  -h, --help
          Print help
```

### `ccore space help`

```text
Print this message or the help of the given subcommand(s)

Usage: help [COMMAND]...

Arguments:
  [COMMAND]...
          Print help for the subcommand(s)
```

### `ccore doc`

```text
Manage documents in a space

Usage: doc <COMMAND>

Commands:
  list
  new
  show
  help  Print this message or the help of the given subcommand(s)

Options:
  -h, --help
          Print help
```

### `ccore doc list`

```text
Usage: list [OPTIONS] <SPACE>

Arguments:
  <SPACE>


Options:
      --limit <LIMIT>
          [default: 50]

      --cursor <CURSOR>
          [default: 0]

      --kind <KIND>


  -h, --help
          Print help
```

### `ccore doc new`

```text
Usage: new [OPTIONS] <SPACE> <TITLE> <CONTENT>

Arguments:
  <SPACE>


  <TITLE>


  <CONTENT>


Options:
      --kind <KIND>
          [default: note]

      --content-type <CONTENT_TYPE>
          [default: text/markdown]

  -h, --help
          Print help
```

### `ccore doc show`

```text
Usage: show [OPTIONS] <DOCUMENT>

Arguments:
  <DOCUMENT>


Options:
      --space <SPACE>


      --include-content


  -h, --help
          Print help
```

### `ccore doc help`

```text
Print this message or the help of the given subcommand(s)

Usage: help [COMMAND]...

Arguments:
  [COMMAND]...
          Print help for the subcommand(s)
```

### `ccore object`

```text
Manage typed managed objects on canonical documents

Usage: object <COMMAND>

Commands:
  create
  list
  get
  trace
  update
  delete
  restore
  help     Print this message or the help of the given subcommand(s)

Options:
  -h, --help
          Print help
```

### `ccore object create`

```text
Usage: create [OPTIONS] --title <TITLE> --content <CONTENT> <SPACE> <KIND>

Arguments:
  <SPACE>


  <KIND>


Options:
      --title <TITLE>


      --content <CONTENT>


      --json


  -h, --help
          Print help
```

### `ccore object list`

```text
Usage: list [OPTIONS] <SPACE> <KIND>

Arguments:
  <SPACE>


  <KIND>


Options:
      --limit <LIMIT>
          [default: 50]

      --cursor <CURSOR>
          [default: 0]

      --status <STATUS>


      --priority <PRIORITY>


      --assignee-actor-id <ASSIGNEE_ACTOR_ID>


      --project-registry-id <PROJECT_REGISTRY_ID>


      --due-before <DUE_BEFORE>


      --due-after <DUE_AFTER>


      --search <SEARCH>


      --include-archived


      --include-deleted


      --json


  -h, --help
          Print help
```

### `ccore object get`

```text
Usage: get [OPTIONS] <OBJECT_ID>

Arguments:
  <OBJECT_ID>


Options:
      --json


  -h, --help
          Print help
```

### `ccore object trace`

```text
Usage: trace [OPTIONS] <OBJECT_ID>

Arguments:
  <OBJECT_ID>


Options:
      --json


  -h, --help
          Print help
```

### `ccore object update`

```text
Usage: update [OPTIONS] <OBJECT_ID>

Arguments:
  <OBJECT_ID>


Options:
      --title <TITLE>


      --content <CONTENT>


      --json


  -h, --help
          Print help
```

### `ccore object delete`

```text
Usage: delete [OPTIONS] <OBJECT_ID>

Arguments:
  <OBJECT_ID>


Options:
      --json


  -h, --help
          Print help
```

### `ccore object restore`

```text
Usage: restore [OPTIONS] <OBJECT_ID>

Arguments:
  <OBJECT_ID>


Options:
      --json


  -h, --help
          Print help
```

### `ccore object help`

```text
Print this message or the help of the given subcommand(s)

Usage: help [COMMAND]...

Arguments:
  [COMMAND]...
          Print help for the subcommand(s)
```

### `ccore project`

```text
Manage project registry objects

Usage: project <COMMAND>

Commands:
  create
  list
  get
  update
  delete
  restore
  help     Print this message or the help of the given subcommand(s)

Options:
  -h, --help
          Print help
```

### `ccore project create`

```text
Usage: create [OPTIONS] --title <TITLE> --content <CONTENT> <SPACE>

Arguments:
  <SPACE>


Options:
      --title <TITLE>


      --content <CONTENT>


      --json


  -h, --help
          Print help
```

### `ccore project list`

```text
Usage: list [OPTIONS] <SPACE>

Arguments:
  <SPACE>


Options:
      --limit <LIMIT>
          [default: 50]

      --cursor <CURSOR>
          [default: 0]

      --status <STATUS>


      --priority <PRIORITY>


      --assignee-actor-id <ASSIGNEE_ACTOR_ID>


      --project-registry-id <PROJECT_REGISTRY_ID>


      --due-before <DUE_BEFORE>


      --due-after <DUE_AFTER>


      --search <SEARCH>


      --include-archived


      --include-deleted


      --json


  -h, --help
          Print help
```

### `ccore project get`

```text
Usage: get [OPTIONS] <PROJECT_ID>

Arguments:
  <PROJECT_ID>


Options:
      --json


  -h, --help
          Print help
```

### `ccore project update`

```text
Usage: update [OPTIONS] <PROJECT_ID>

Arguments:
  <PROJECT_ID>


Options:
      --title <TITLE>


      --content <CONTENT>


      --json


  -h, --help
          Print help
```

### `ccore project delete`

```text
Usage: delete [OPTIONS] <PROJECT_ID>

Arguments:
  <PROJECT_ID>


Options:
      --json


  -h, --help
          Print help
```

### `ccore project restore`

```text
Usage: restore [OPTIONS] <PROJECT_ID>

Arguments:
  <PROJECT_ID>


Options:
      --json


  -h, --help
          Print help
```

### `ccore project help`

```text
Print this message or the help of the given subcommand(s)

Usage: help [COMMAND]...

Arguments:
  [COMMAND]...
          Print help for the subcommand(s)
```

### `ccore project-context`

```text
Manage project context objects

Usage: project-context <COMMAND>

Commands:
  create
  list
  get
  update
  delete
  restore
  help     Print this message or the help of the given subcommand(s)

Options:
  -h, --help
          Print help
```

### `ccore project-context create`

```text
Usage: create [OPTIONS] --title <TITLE> --content <CONTENT> <SPACE>

Arguments:
  <SPACE>


Options:
      --title <TITLE>


      --content <CONTENT>


      --json


  -h, --help
          Print help
```

### `ccore project-context list`

```text
Usage: list [OPTIONS] <SPACE>

Arguments:
  <SPACE>


Options:
      --limit <LIMIT>
          [default: 50]

      --cursor <CURSOR>
          [default: 0]

      --status <STATUS>


      --priority <PRIORITY>


      --assignee-actor-id <ASSIGNEE_ACTOR_ID>


      --project-registry-id <PROJECT_REGISTRY_ID>


      --due-before <DUE_BEFORE>


      --due-after <DUE_AFTER>


      --search <SEARCH>


      --include-archived


      --include-deleted


      --json


  -h, --help
          Print help
```

### `ccore project-context get`

```text
Usage: get [OPTIONS] <PROJECT_CONTEXT_ID>

Arguments:
  <PROJECT_CONTEXT_ID>


Options:
      --json


  -h, --help
          Print help
```

### `ccore project-context update`

```text
Usage: update [OPTIONS] <PROJECT_CONTEXT_ID>

Arguments:
  <PROJECT_CONTEXT_ID>


Options:
      --title <TITLE>


      --content <CONTENT>


      --json


  -h, --help
          Print help
```

### `ccore project-context delete`

```text
Usage: delete [OPTIONS] <PROJECT_CONTEXT_ID>

Arguments:
  <PROJECT_CONTEXT_ID>


Options:
      --json


  -h, --help
          Print help
```

### `ccore project-context restore`

```text
Usage: restore [OPTIONS] <PROJECT_CONTEXT_ID>

Arguments:
  <PROJECT_CONTEXT_ID>


Options:
      --json


  -h, --help
          Print help
```

### `ccore project-context help`

```text
Print this message or the help of the given subcommand(s)

Usage: help [COMMAND]...

Arguments:
  [COMMAND]...
          Print help for the subcommand(s)
```

### `ccore clarification`

```text
Manage transcript clarification objects

Usage: clarification <COMMAND>

Commands:
  create
  list
  get
  update
  delete
  restore
  help     Print this message or the help of the given subcommand(s)

Options:
  -h, --help
          Print help
```

### `ccore clarification create`

```text
Usage: create [OPTIONS] --title <TITLE> --content <CONTENT> <SPACE>

Arguments:
  <SPACE>


Options:
      --title <TITLE>


      --content <CONTENT>


      --json


  -h, --help
          Print help
```

### `ccore clarification list`

```text
Usage: list [OPTIONS] <SPACE>

Arguments:
  <SPACE>


Options:
      --limit <LIMIT>
          [default: 50]

      --cursor <CURSOR>
          [default: 0]

      --status <STATUS>


      --priority <PRIORITY>


      --assignee-actor-id <ASSIGNEE_ACTOR_ID>


      --project-registry-id <PROJECT_REGISTRY_ID>


      --due-before <DUE_BEFORE>


      --due-after <DUE_AFTER>


      --search <SEARCH>


      --include-archived


      --include-deleted


      --json


  -h, --help
          Print help
```

### `ccore clarification get`

```text
Usage: get [OPTIONS] <CLARIFICATION_ID>

Arguments:
  <CLARIFICATION_ID>


Options:
      --json


  -h, --help
          Print help
```

### `ccore clarification update`

```text
Usage: update [OPTIONS] <CLARIFICATION_ID>

Arguments:
  <CLARIFICATION_ID>


Options:
      --title <TITLE>


      --content <CONTENT>


      --json


  -h, --help
          Print help
```

### `ccore clarification delete`

```text
Usage: delete [OPTIONS] <CLARIFICATION_ID>

Arguments:
  <CLARIFICATION_ID>


Options:
      --json


  -h, --help
          Print help
```

### `ccore clarification restore`

```text
Usage: restore [OPTIONS] <CLARIFICATION_ID>

Arguments:
  <CLARIFICATION_ID>


Options:
      --json


  -h, --help
          Print help
```

### `ccore clarification help`

```text
Print this message or the help of the given subcommand(s)

Usage: help [COMMAND]...

Arguments:
  [COMMAND]...
          Print help for the subcommand(s)
```

### `ccore signal`

```text
Manage runtime-critical signals on canonical documents

Usage: signal <COMMAND>

Commands:
  create
  list
  get
  update
  delete
  restore
  acknowledge
  start
  block
  request-info
  resolve
  cancel
  append-response
  help             Print this message or the help of the given subcommand(s)

Options:
  -h, --help
          Print help
```

### `ccore signal create`

```text
Usage: create [OPTIONS] --title <TITLE> --content <CONTENT> <SPACE>

Arguments:
  <SPACE>


Options:
      --title <TITLE>


      --content <CONTENT>


      --json


  -h, --help
          Print help
```

### `ccore signal list`

```text
Usage: list [OPTIONS] <SPACE>

Arguments:
  <SPACE>


Options:
      --limit <LIMIT>
          [default: 50]

      --cursor <CURSOR>
          [default: 0]

      --status <STATUS>


      --priority <PRIORITY>


      --assignee-actor-id <ASSIGNEE_ACTOR_ID>


      --requester-actor-id <REQUESTER_ACTOR_ID>


      --project-registry-id <PROJECT_REGISTRY_ID>


      --due-before <DUE_BEFORE>


      --due-after <DUE_AFTER>


      --stale-before <STALE_BEFORE>


      --overdue-before <OVERDUE_BEFORE>


      --inbox-actor-id <INBOX_ACTOR_ID>


      --outbox-actor-id <OUTBOX_ACTOR_ID>


      --search <SEARCH>


      --include-archived


      --include-deleted


      --json


  -h, --help
          Print help
```

### `ccore signal get`

```text
Usage: get [OPTIONS] <SIGNAL_ID>

Arguments:
  <SIGNAL_ID>


Options:
      --json


  -h, --help
          Print help
```

### `ccore signal update`

```text
Usage: update [OPTIONS] <SIGNAL_ID>

Arguments:
  <SIGNAL_ID>


Options:
      --title <TITLE>


      --content <CONTENT>


      --json


  -h, --help
          Print help
```

### `ccore signal delete`

```text
Usage: delete [OPTIONS] <SIGNAL_ID>

Arguments:
  <SIGNAL_ID>


Options:
      --json


  -h, --help
          Print help
```

### `ccore signal restore`

```text
Usage: restore [OPTIONS] <SIGNAL_ID>

Arguments:
  <SIGNAL_ID>


Options:
      --json


  -h, --help
          Print help
```

### `ccore signal acknowledge`

```text
Usage: acknowledge [OPTIONS] --expected-current-version-id <EXPECTED_CURRENT_VERSION_ID> <SIGNAL_ID>

Arguments:
  <SIGNAL_ID>


Options:
      --expected-current-version-id <EXPECTED_CURRENT_VERSION_ID>


      --json


  -h, --help
          Print help
```

### `ccore signal start`

```text
Usage: start [OPTIONS] --expected-current-version-id <EXPECTED_CURRENT_VERSION_ID> <SIGNAL_ID>

Arguments:
  <SIGNAL_ID>


Options:
      --expected-current-version-id <EXPECTED_CURRENT_VERSION_ID>


      --json


  -h, --help
          Print help
```

### `ccore signal block`

```text
Usage: block [OPTIONS] --expected-current-version-id <EXPECTED_CURRENT_VERSION_ID> <SIGNAL_ID>

Arguments:
  <SIGNAL_ID>


Options:
      --expected-current-version-id <EXPECTED_CURRENT_VERSION_ID>


      --json


  -h, --help
          Print help
```

### `ccore signal request-info`

```text
Usage: request-info [OPTIONS] --expected-current-version-id <EXPECTED_CURRENT_VERSION_ID> <SIGNAL_ID>

Arguments:
  <SIGNAL_ID>


Options:
      --expected-current-version-id <EXPECTED_CURRENT_VERSION_ID>


      --json


  -h, --help
          Print help
```

### `ccore signal resolve`

```text
Usage: resolve [OPTIONS] --expected-current-version-id <EXPECTED_CURRENT_VERSION_ID> <SIGNAL_ID>

Arguments:
  <SIGNAL_ID>


Options:
      --expected-current-version-id <EXPECTED_CURRENT_VERSION_ID>


      --json


  -h, --help
          Print help
```

### `ccore signal cancel`

```text
Usage: cancel [OPTIONS] --expected-current-version-id <EXPECTED_CURRENT_VERSION_ID> <SIGNAL_ID>

Arguments:
  <SIGNAL_ID>


Options:
      --expected-current-version-id <EXPECTED_CURRENT_VERSION_ID>


      --json


  -h, --help
          Print help
```

### `ccore signal append-response`

```text
Usage: append-response [OPTIONS] --expected-current-version-id <EXPECTED_CURRENT_VERSION_ID> --response <RESPONSE> <SIGNAL_ID>

Arguments:
  <SIGNAL_ID>


Options:
      --expected-current-version-id <EXPECTED_CURRENT_VERSION_ID>


      --response <RESPONSE>


      --json


  -h, --help
          Print help
```

### `ccore signal help`

```text
Print this message or the help of the given subcommand(s)

Usage: help [COMMAND]...

Arguments:
  [COMMAND]...
          Print help for the subcommand(s)
```

### `ccore ingest`

```text
Run and inspect ingest pipelines

Usage: ingest <COMMAND>

Commands:
  obsidian
  slack-fixture
  status
  help           Print this message or the help of the given subcommand(s)

Options:
  -h, --help
          Print help
```

### `ccore ingest obsidian`

```text
Usage: obsidian [OPTIONS] <SPACE> <VAULT_PATH>

Arguments:
  <SPACE>


  <VAULT_PATH>


Options:
      --vault-id <VAULT_ID>


      --write-frontmatter-id <WRITE_FRONTMATTER_ID>
          [possible values: true, false]

      --frontmatter-key <FRONTMATTER_KEY>


      --attachments-mode <ATTACHMENTS_MODE>
          [possible values: off, referenced_only, include_dirs, all_files]

      --attachment-dir <ATTACHMENT_DIRS>


      --attachment-include-glob <ATTACHMENT_INCLUDE_GLOBS>


      --attachment-exclude-glob <ATTACHMENT_EXCLUDE_GLOBS>


      --attachment-max-file-bytes <ATTACHMENT_MAX_FILE_BYTES>


      --attachment-mime-deny <ATTACHMENT_MIME_DENYLIST>


      --attachment-max-run-bytes <ATTACHMENT_MAX_RUN_BYTES>


  -h, --help
          Print help
```

### `ccore ingest slack-fixture`

```text
Usage: slack-fixture [OPTIONS] <SPACE> <FIXTURE_PATH>

Arguments:
  <SPACE>


  <FIXTURE_PATH>


Options:
      --workspace-id <WORKSPACE_ID>


  -h, --help
          Print help
```

### `ccore ingest status`

```text
Usage: status <INGEST_RUN_ID>

Arguments:
  <INGEST_RUN_ID>


Options:
  -h, --help
          Print help
```

### `ccore ingest help`

```text
Print this message or the help of the given subcommand(s)

Usage: help [COMMAND]...

Arguments:
  [COMMAND]...
          Print help for the subcommand(s)
```

### `ccore artifact`

```text
Inspect and retrieve binary artifacts

Usage: artifact <COMMAND>

Commands:
  list
  show
  cat
  references
  help        Print this message or the help of the given subcommand(s)

Options:
  -h, --help
          Print help
```

### `ccore artifact list`

```text
Usage: list [OPTIONS] <SPACE>

Arguments:
  <SPACE>


Options:
      --limit <LIMIT>
          [default: 50]

      --cursor <CURSOR>
          [default: 0]

      --kind <KIND>


  -h, --help
          Print help
```

### `ccore artifact show`

```text
Usage: show <ARTIFACT>

Arguments:
  <ARTIFACT>


Options:
  -h, --help
          Print help
```

### `ccore artifact cat`

```text
Usage: cat [OPTIONS] <ARTIFACT>

Arguments:
  <ARTIFACT>


Options:
      --output <OUTPUT>


  -h, --help
          Print help
```

### `ccore artifact references`

```text
Usage: references <ARTIFACT>

Arguments:
  <ARTIFACT>


Options:
  -h, --help
          Print help
```

### `ccore artifact help`

```text
Print this message or the help of the given subcommand(s)

Usage: help [COMMAND]...

Arguments:
  [COMMAND]...
          Print help for the subcommand(s)
```

### `ccore links`

```text
Explore graph links between documents

Usage: links <COMMAND>

Commands:
  backlinks
  outlinks
  help       Print this message or the help of the given subcommand(s)

Options:
  -h, --help
          Print help
```

### `ccore links backlinks`

```text
Usage: backlinks <SPACE> <DOCUMENT>

Arguments:
  <SPACE>


  <DOCUMENT>


Options:
  -h, --help
          Print help
```

### `ccore links outlinks`

```text
Usage: outlinks <SPACE> <DOCUMENT>

Arguments:
  <SPACE>


  <DOCUMENT>


Options:
  -h, --help
          Print help
```

### `ccore links help`

```text
Print this message or the help of the given subcommand(s)

Usage: help [COMMAND]...

Arguments:
  [COMMAND]...
          Print help for the subcommand(s)
```

### `ccore workstream`

```text
Manage resumable workstreams

Usage: workstream <COMMAND>

Commands:
  create
  list
  show
  update
  archive
  restore
  search
  help     Print this message or the help of the given subcommand(s)

Options:
  -h, --help
          Print help
```

### `ccore workstream create`

```text
Usage: create [OPTIONS] <SPACE> <TITLE>

Arguments:
  <SPACE>
          Space id, slug, or display name

  <TITLE>
          Workstream title

Options:
      --summary <SUMMARY>
          Optional workstream summary

      --status <STATUS>
          Optional workstream status

      --created-by-actor-id <CREATED_BY_ACTOR_ID>
          Optional creator actor id

      --json
          Emit raw JSON instead of human-readable output

  -h, --help
          Print help
```

### `ccore workstream list`

```text
Usage: list [OPTIONS] <SPACE>

Arguments:
  <SPACE>
          Space id, slug, or display name

Options:
      --limit <LIMIT>
          Maximum number of results

          [default: 50]

      --cursor <CURSOR>
          Offset cursor

          [default: 0]

      --status <STATUS>
          Optional status filter

      --archived <ARCHIVED>
          Optional archived filter (true|false)

          [possible values: true, false]

      --json
          Emit raw JSON instead of human-readable output

  -h, --help
          Print help
```

### `ccore workstream show`

```text
Usage: show [OPTIONS] <WORKSTREAM_ID>

Arguments:
  <WORKSTREAM_ID>
          Workstream id

Options:
      --json
          Emit raw JSON instead of human-readable output

  -h, --help
          Print help
```

### `ccore workstream update`

```text
Usage: update [OPTIONS] <WORKSTREAM_ID>

Arguments:
  <WORKSTREAM_ID>
          Workstream id

Options:
      --title <TITLE>
          Updated workstream title

      --summary <SUMMARY>
          Updated workstream summary

      --status <STATUS>
          Updated workstream status

      --json
          Emit raw JSON instead of human-readable output

  -h, --help
          Print help
```

### `ccore workstream archive`

```text
Usage: archive [OPTIONS] <WORKSTREAM_ID>

Arguments:
  <WORKSTREAM_ID>
          Workstream id

Options:
      --json
          Emit raw JSON instead of human-readable output

  -h, --help
          Print help
```

### `ccore workstream restore`

```text
Usage: restore [OPTIONS] <WORKSTREAM_ID>

Arguments:
  <WORKSTREAM_ID>
          Workstream id

Options:
      --json
          Emit raw JSON instead of human-readable output

  -h, --help
          Print help
```

### `ccore workstream search`

```text
Usage: search [OPTIONS] <SPACE> <QUERY>

Arguments:
  <SPACE>
          Space id, slug, or display name

  <QUERY>
          Search query text

Options:
      --limit <LIMIT>
          Maximum number of results

          [default: 20]

      --include-related-sessions
          Include related recent sessions for each match

      --json
          Emit raw JSON instead of human-readable output

  -h, --help
          Print help
```

### `ccore workstream help`

```text
Print this message or the help of the given subcommand(s)

Usage: help [COMMAND]...

Arguments:
  [COMMAND]...
          Print help for the subcommand(s)
```

### `ccore session`

```text
Manage resumable work sessions

Usage: session <COMMAND>

Commands:
  create
  list
  show
  update
  archive
  restore
  resume
  help     Print this message or the help of the given subcommand(s)

Options:
  -h, --help
          Print help
```

### `ccore session create`

```text
Usage: create [OPTIONS] <SPACE> <WORKSTREAM_ID> <TITLE>

Arguments:
  <SPACE>
          Space id, slug, or display name

  <WORKSTREAM_ID>
          Parent workstream id

  <TITLE>
          Session title

Options:
      --status <STATUS>
          Optional status

      --resume-summary <RESUME_SUMMARY>
          Optional resume summary

      --parent-session-id <PARENT_SESSION_ID>
          Optional parent session id

      --focus-refs <FOCUS_REFS>
          Optional JSON payload for focus refs

      --created-by-actor-id <CREATED_BY_ACTOR_ID>
          Optional creator actor id

      --json
          Emit raw JSON instead of human-readable output

  -h, --help
          Print help
```

### `ccore session list`

```text
Usage: list [OPTIONS] <SPACE>

Arguments:
  <SPACE>
          Space id, slug, or display name

Options:
      --workstream-id <WORKSTREAM_ID>
          Optional workstream id filter

      --limit <LIMIT>
          Maximum number of results

          [default: 50]

      --cursor <CURSOR>
          Offset cursor

          [default: 0]

      --status <STATUS>
          Optional status filter

      --archived <ARCHIVED>
          Optional archived filter (true|false)

          [possible values: true, false]

      --json
          Emit raw JSON instead of human-readable output

  -h, --help
          Print help
```

### `ccore session show`

```text
Usage: show [OPTIONS] <SESSION_ID>

Arguments:
  <SESSION_ID>
          Session id

Options:
      --json
          Emit raw JSON instead of human-readable output

  -h, --help
          Print help
```

### `ccore session update`

```text
Usage: update [OPTIONS] <SESSION_ID>

Arguments:
  <SESSION_ID>
          Session id

Options:
      --title <TITLE>
          Updated title

      --status <STATUS>
          Updated status

      --resume-summary <RESUME_SUMMARY>
          Updated resume summary

      --focus-refs <FOCUS_REFS>
          Updated focus refs JSON payload

      --json
          Emit raw JSON instead of human-readable output

  -h, --help
          Print help
```

### `ccore session archive`

```text
Usage: archive [OPTIONS] <SESSION_ID>

Arguments:
  <SESSION_ID>
          Session id

Options:
      --json
          Emit raw JSON instead of human-readable output

  -h, --help
          Print help
```

### `ccore session restore`

```text
Usage: restore [OPTIONS] <SESSION_ID>

Arguments:
  <SESSION_ID>
          Session id

Options:
      --json
          Emit raw JSON instead of human-readable output

  -h, --help
          Print help
```

### `ccore session resume`

```text
Usage: resume [OPTIONS] <SESSION_ID>

Arguments:
  <SESSION_ID>
          Session id

Options:
      --created-by-actor-id <CREATED_BY_ACTOR_ID>
          Optional actor id for resume attribution

      --json
          Emit raw JSON instead of human-readable output

  -h, --help
          Print help
```

### `ccore session help`

```text
Print this message or the help of the given subcommand(s)

Usage: help [COMMAND]...

Arguments:
  [COMMAND]...
          Print help for the subcommand(s)
```

### `ccore transcript`

```text
Read and append session transcript history

Usage: transcript <COMMAND>

Commands:
  show
  append
  help    Print this message or the help of the given subcommand(s)

Options:
  -h, --help
          Print help
```

### `ccore transcript show`

```text
Usage: show [OPTIONS] <SESSION_ID>

Arguments:
  <SESSION_ID>
          Session id

Options:
      --limit <LIMIT>
          Maximum number of messages

          [default: 50]

      --cursor <CURSOR>
          Offset cursor

          [default: 0]

      --json
          Emit raw JSON instead of human-readable output

  -h, --help
          Print help
```

### `ccore transcript append`

```text
Usage: append [OPTIONS] --role <ROLE> --parts-json <PARTS_JSON> <SESSION_ID>

Arguments:
  <SESSION_ID>
          Session id

Options:
      --role <ROLE>
          Message role

      --parts-json <PARTS_JSON>
          Session part array JSON payload

      --message-id <MESSAGE_ID>
          Optional message id override

      --actor-id <ACTOR_ID>
          Optional actor id

      --parent-message-id <PARENT_MESSAGE_ID>
          Optional parent message id

      --metadata <METADATA>
          Optional metadata JSON payload

      --json
          Emit raw JSON instead of human-readable output

  -h, --help
          Print help
```

### `ccore transcript help`

```text
Print this message or the help of the given subcommand(s)

Usage: help [COMMAND]...

Arguments:
  [COMMAND]...
          Print help for the subcommand(s)
```

### `ccore activity`

```text
Inspect low-churn activity history

Usage: activity <COMMAND>

Commands:
  list
  help  Print this message or the help of the given subcommand(s)

Options:
  -h, --help
          Print help
```

### `ccore activity list`

```text
Usage: list [OPTIONS] <SPACE>

Arguments:
  <SPACE>
          Space id, slug, or display name

Options:
      --kind <KIND>
          Activity kind filter. Repeat or provide comma-delimited values

      --workstream <WORKSTREAM>
          Optional workstream id filter

      --session <SESSION>
          Optional session id filter

      --subject <SUBJECT>
          Optional subject filter as type or type:id

      --since <SINCE>
          Optional lower time bound (RFC3339)

      --until <UNTIL>
          Optional upper time bound (RFC3339)

      --limit <LIMIT>
          Maximum number of events

          [default: 100]

      --json
          Emit raw JSON instead of human-readable output

  -h, --help
          Print help
```

### `ccore activity help`

```text
Print this message or the help of the given subcommand(s)

Usage: help [COMMAND]...

Arguments:
  [COMMAND]...
          Print help for the subcommand(s)
```

### `ccore search`

```text
Legacy compatibility path: search documents within a space

Usage: search [OPTIONS] <SPACE> <QUERY>

Arguments:
  <SPACE>
          Space id, slug, or display name

  <QUERY>
          Query text

Options:
      --limit <LIMIT>
          Maximum number of results

          [default: 20]

  -h, --help
          Print help
```

### `ccore query`

```text
Ranked authority/freshness query across supported object kinds in a space

Usage: query [OPTIONS] <SPACE> <QUERY>

Arguments:
  <SPACE>
          Space id, slug, or display name

  <QUERY>
          Query text

Options:
      --limit <LIMIT>
          Maximum number of results

          [default: 20]

      --kinds <KINDS>
          Optional comma-separated ranked kinds override

          [possible values: documents, decision_records, canonical_packages]

      --json
          Emit raw JSON instead of human-readable ranked output

  -h, --help
          Print help
```

### `ccore decision`

```text
Manage immutable decision records

Usage: decision <COMMAND>

Commands:
  create
  list
  show
  trace
  help    Print this message or the help of the given subcommand(s)

Options:
  -h, --help
          Print help
```

### `ccore decision create`

```text
Usage: create [OPTIONS] --kind <KIND> --input-refs <INPUT_REFS> --output <OUTPUT> --approvals <APPROVALS> <SPACE>

Arguments:
  <SPACE>
          Space id, slug, or display name

Options:
      --kind <KIND>
          Decision kind

      --input-refs <INPUT_REFS>
          JSON payload for immutable input refs

      --output <OUTPUT>
          JSON payload for decision output/rationale

      --approvals <APPROVALS>
          JSON payload for approvals

      --created-by-actor-id <CREATED_BY_ACTOR_ID>
          Optional creator actor id

  -h, --help
          Print help
```

### `ccore decision list`

```text
Usage: list [OPTIONS] <SPACE>

Arguments:
  <SPACE>
          Space id, slug, or display name

Options:
      --limit <LIMIT>
          Maximum number of results

          [default: 50]

      --cursor <CURSOR>
          Offset cursor

          [default: 0]

      --kind <KIND>
          Filter by decision kind

      --query <QUERY>
          Search text over kind and JSON payloads

  -h, --help
          Print help
```

### `ccore decision show`

```text
Usage: show <DECISION_RECORD_ID>

Arguments:
  <DECISION_RECORD_ID>
          Decision record id

Options:
  -h, --help
          Print help
```

### `ccore decision trace`

```text
Usage: trace <DECISION_RECORD_ID>

Arguments:
  <DECISION_RECORD_ID>
          Decision record id

Options:
  -h, --help
          Print help
```

### `ccore decision help`

```text
Print this message or the help of the given subcommand(s)

Usage: help [COMMAND]...

Arguments:
  [COMMAND]...
          Print help for the subcommand(s)
```

### `ccore package`

```text
Manage canonical context packages

Usage: package <COMMAND>

Commands:
  promote
  list
  show
  trace
  consume
  help     Print this message or the help of the given subcommand(s)

Options:
  -h, --help
          Print help
```

### `ccore package promote`

```text
Usage: promote [OPTIONS] --label <LABEL> --contents <CONTENTS> --approvals <APPROVALS> <SPACE>

Arguments:
  <SPACE>
          Space id, slug, or display name

Options:
      --label <LABEL>
          Package label

      --contents <CONTENTS>
          JSON payload for frozen contents

      --approvals <APPROVALS>
          JSON payload for approvals

      --created-by-actor-id <CREATED_BY_ACTOR_ID>
          Optional creator actor id

  -h, --help
          Print help
```

### `ccore package list`

```text
Usage: list [OPTIONS] <SPACE>

Arguments:
  <SPACE>
          Space id, slug, or display name

Options:
      --limit <LIMIT>
          Maximum number of results

          [default: 50]

      --cursor <CURSOR>
          Offset cursor

          [default: 0]

      --label <LABEL>
          Filter by package label (substring match)

      --query <QUERY>
          Search text over label and frozen contents

  -h, --help
          Print help
```

### `ccore package show`

```text
Usage: show <PACKAGE_ID>

Arguments:
  <PACKAGE_ID>
          Canonical package id

Options:
  -h, --help
          Print help
```

### `ccore package trace`

```text
Usage: trace <PACKAGE_ID>

Arguments:
  <PACKAGE_ID>
          Canonical package id

Options:
  -h, --help
          Print help
```

### `ccore package consume`

```text
Usage: consume [OPTIONS] <PACKAGE_ID>

Arguments:
  <PACKAGE_ID>
          Canonical package id

Options:
      --action <ACTION>
          Optional audited action (default: canonical_package.consume)

      --actor-id <ACTOR_ID>
          Optional actor id for audit attribution

      --metadata <METADATA>
          Optional JSON metadata payload

  -h, --help
          Print help
```

### `ccore package help`

```text
Print this message or the help of the given subcommand(s)

Usage: help [COMMAND]...

Arguments:
  [COMMAND]...
          Print help for the subcommand(s)
```

### `ccore help`

```text
Print this message or the help of the given subcommand(s)

Usage: help [COMMAND]...

Arguments:
  [COMMAND]...
          Print help for the subcommand(s)
```
