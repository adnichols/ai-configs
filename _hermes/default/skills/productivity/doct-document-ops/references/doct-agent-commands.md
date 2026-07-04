# doct-agent command reference

Full reference for the `doct-agent` CLI. This is the **only** supported way to operate doct from an agent — no `doct-cli`, no raw REST, no hand-written Yjs/Hocuspocus scripts, no local wrapper scripts. `doct-agent` wraps REST (discovery, reads, creation, plan registration, metadata) and Yjs/Hocuspocus collaborative surfaces (text edits, comments) behind supported commands.

For the canonical, always-current version of this spec, run `doct-agent onboard` (add `--json` when supported for structured output). When the CLI and this file disagree, trust the CLI.

## Top-level commands

```text
doct-agent auth         # login / status / default endpoint / token renewal / token import / logout
doct-agent context      # agent identity, base URL, websocket URL, instructions
doct-agent onboard      # canonical onboarding + runtime spec
doct-agent workspaces   # list workspaces
doct-agent documents    # list / get / create / replace-body / update-metadata / rename / move / delete / legacy publish-plan
doct-agent plans        # register / update / watch / listen / show / comments / queue / agent / ack / resolve / reply / release / lifecycle / board / metadata
doct-agent collab       # text edit / anchored text edits / text-document comments
doct-agent triage       # read-only DB + log operational triage
```

Almost every command accepts `--json`. Most authenticated commands accept `--base-url <BASE_URL>`.

## Install and storage

- Install/update via Homebrew only, from the doct repo root:
  ```bash
  brew tap local/doct "$(pwd)"
  brew install --build-from-source local/doct/doct-agent
  # refresh an existing install:
  brew reinstall --build-from-source local/doct/doct-agent
  ```
- Do not copy Cargo build artifacts into `~/.local/bin` or other ad hoc paths, and do not use alternate CLI binaries, wrapper scripts, or token-store fallbacks.
- Config lives under the platform user config directory in a v2 registry keyed by canonical endpoint origin.
- Endpoint tokens are stored in separate hash-derived plaintext PAT files with restrictive permissions.
- `DOCT_AGENT_PAT` is only for one-off automation with an explicit `--base-url`; it never falls back across stored endpoints or rewrites endpoint token files.

## Auth

```bash
doct-agent auth status --all --json
doct-agent auth login --base-url https://doct.nodaste.com [--enrollment-code <code>] [--websocket-url <wss-url>]
doct-agent auth renew --base-url https://doct.nodaste.com --json
doct-agent auth default --base-url https://doct.nodaste.com
doct-agent auth import-pat --base-url <url> --token <doct_pat_v1_...> [--websocket-url <wss-url>]
doct-agent auth logout --base-url <url>
```

- Owner must generate and approve a **selected-agent enrollment code** before `auth login`.
- The websocket URL is discovered and stored automatically; `--websocket-url` is an override only.
- Environments: production `https://doct.nodaste.com`, develop `https://doct.develop.nodaste.com`.
- Production is the preferred endpoint for registering HTML plans unless the user explicitly selects another endpoint.

## Context

```bash
doct-agent context --base-url https://doct.nodaste.com --json
```

Returns the agent identity, deployment (`baseUrl`, `websocketUrl`), token lifecycle metadata, and any system/agent instructions. Use it to confirm you are pointed at the right deployment before mutating anything.

## Workspaces

```bash
doct-agent workspaces list --base-url https://doct.nodaste.com --json
```

Each workspace has `id`, `handle`, `slug`, `name`, and often `isPersonal`. Use the personal workspace by default for personal coding plans unless repo guidance or the user specifies a shared workspace.

## Documents

### List

```bash
doct-agent documents list --workspace-id <id> --json
```

### Get / read

```bash
# by id
doct-agent documents get --id <document-id> --text        # markdown body for text docs
doct-agent documents get --id <document-id> --json        # metadata + content

# by workspace + path
doct-agent documents get --workspace-id <id> --path '<doc/path>' --text
```

`--text` returns markdown. Markdown is **not** the authoritative selection surface for anchored edits/comments — see "Anchored selection surface" below.

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
- Provide `--content` at creation time to bootstrap a body and anchorable text.
- `--parent-id` nests the new document under an existing one.

### Replace full body

```bash
doct-agent documents replace-body --id <document-id> (--file prepared.md | --text '<markdown>' | --stdin) --json
```

Replaces the entire text-document body through the supported Hocuspocus/Yjs-safe server path and returns verified readback metadata.

### Metadata, rename, move, delete

```bash
doct-agent documents update-metadata --id <id> [--title '<t>'] [--status <published|draft|...>] --json
doct-agent documents rename --id <id> --workspace-id <wsid> --title '<new title>' --json
doct-agent documents move --id <id> --workspace-id <wsid> [--new-parent-id <id>] [--new-display-order <n>] --json
doct-agent documents delete (--id <id> | --path '<path>') [--workspace-id <wsid>] --json
```

### Legacy publish-plan

```bash
doct-agent documents publish-plan --file /path/to/plan.md [--title '<title>'] [--parent-title 'Coding Plans'] [--workspace personal|<id-or-slug>] --json
```

Current onboarding says `documents publish-plan` fails closed with replacement guidance for plan-review publishing. Prefer `doct-agent plans register` for HTML/Markdoc coding plans. Current registration responses may identify handcrafted HTML as a legacy/import source and recommend Markdoc templates for newly-authored reviewed plans; follow repo-local plan-format authority, but preserve and follow the returned `sourceGuidance`.

## Plans: register, update, and review HTML plans

### Register an HTML plan

```bash
doct-agent plans register \
  --base-url https://doct.nodaste.com \
  --file thoughts/plans/example.html \
  --source-format html \
  --allow-untemplated \
  [--title 'Example Plan'] \
  [--workspace <workspace-id-or-slug> | --workspace-id <workspace-id>] \
  [--path '<path>'] \
  [--parent-id <document-id>] \
  [--plan-config <file>] \
  [--reason '<summary>'] \
  --json
```

Use this for repo-authorized handcrafted HTML plans. Omit `--allow-untemplated` only when using a Doct plan template/config that validates without it. Preserve any returned `sourceGuidance`; the service may recommend Markdoc/templates for new reviewed plans even while accepting intentional HTML registrations.

### Register a Markdoc plan

```bash
doct-agent plans register \
  --base-url https://doct.nodaste.com \
  --file thoughts/plans/example.markdoc \
  --source-format markdoc \
  [--title 'Example Plan'] \
  --json
```

### Update a registered plan

```bash
doct-agent plans update \
  --base-url https://doct.nodaste.com \
  --id <document-id> \
  --workspace-id <workspace-id> \
  --file thoughts/plans/example.html \
  --source-format html \
  [--expected-version <version>] \
  [--force] \
  [--plan-config <file>] \
  [--allow-untemplated] \
  [--reason '<summary>'] \
  --json
```

Prefer optimistic updates with `--expected-version` from the last `register`, `update`, or `show` response. Use `--force` only after confirming you are not overwriting someone else's changes.

### Watch/sync local source

```bash
doct-agent plans watch \
  --base-url https://doct.nodaste.com \
  --id <document-id> \
  --workspace-id <workspace-id> \
  --file thoughts/plans/example.html \
  [--expected-version <version>] \
  [--interval-seconds 2] \
  --json
```

Run long-lived watch commands with the harness background-process tool. `plans watch` syncs source changes; it is not the queue-backed comment listener.

### Start the Codex-observable plan comment listener

Every reviewer-facing registration returns `listenerInstructions`. Follow that object before browser-review handoff: set lifecycle active, leave the plan in its registration/default board column (normally `backlog`), drain pending claims, then start an observable one-claim listener. Do not move a plan to `in_progress` during registration or browser-review setup; execution workflows such as `run-plan` do that when implementation starts.

```bash
# Drain pending work until status is empty
doct-agent plans agent next \
  --base-url https://doct.nodaste.com \
  --workspace-id <workspace-id> \
  --document-id <document-id> \
  --no-wait \
  --json

# Codex observable one-claim listener
doct-agent plans agent next \
  --base-url https://doct.nodaste.com \
  --workspace-id <workspace-id> \
  --document-id <document-id> \
  --wait \
  --timeout 300 \
  --json

# Create a routed smoke-test comment when verifying wake behavior
doct-agent plans comments add \
  --base-url https://doct.nodaste.com \
  --document-id <document-id> \
  --workspace-id <workspace-id> \
  --node-id <stable-html-id> \
  --submit-action agent \
  --body 'Smoke test routed plan-review comment.' \
  --json
```

In Codex, run the one-claim listener with the `exec_command` tool and a matching `yield_time_ms` window. It is quiet while waiting. When a routed browser action or `--submit-action agent` comment arrives, it returns one JSON claim payload and wakes the active session with the returned reply/ack/resolve/release commands. Process that claim, then start the next one-claim listener.

Ordinary conversation comments are not routed work: they return `queueState: "none"` and do not wake the listener. Use them only for visible discussion, not for listener wake tests.

`doct-agent plans listen --jsonl` is retained for advanced compatibility supervisors that can dispatch JSONL events to workers. The Codex path is the one-claim `plans agent next --wait --json` command because it is directly observable by the active session.

### Show plan state

```bash
doct-agent plans show --base-url https://doct.nodaste.com --id <document-id> --json
```

### Add a plan comment/action

```bash
doct-agent plans comments add \
  --base-url https://doct.nodaste.com \
  --document-id <document-id> \
  --workspace-id <workspace-id> \
  --node-id <stable-html-id> \
  [--selector '#stable-html-id'] \
  --body '<comment body>' \
  [--submit-action conversation|execution-ready|build] \
  --json
```

The exact `--submit-action` values can evolve; check `--help` or returned UI metadata if an action is rejected.

### Queue and agent claims

```bash
doct-agent plans queue list \
  --base-url https://doct.nodaste.com \
  --workspace-id <workspace-id> \
  [--document-id <document-id>] \
  [--all] \
  [--view <view>] \
  [--queue-state <state>] \
  [--claim-status <status>] \
  [--thread-state <state>] \
  --json

doct-agent plans agent next \
  --base-url https://doct.nodaste.com \
  --workspace-id <workspace-id> \
  [--document-id <document-id>] \
  [--target-agent-id <agent-id>] \
  [--target-scope <scope>] \
  [--wait | --no-wait] \
  [--all] \
  --json
```

Use `--no-wait` for startup drain and manual recovery. Use `--wait` only for one-shot listener flows or when the registration response explicitly returns it as the preferred command. Process one claimed item at a time. Preserve `thread-id`, `claim-id`, `document-id`, and `workspace-id` for ack/resolve/release.

### Reply, ack, resolve, release

```bash
doct-agent plans reply \
  --base-url https://doct.nodaste.com \
  --document-id <document-id> \
  --workspace-id <workspace-id> \
  --thread-id <thread-id> \
  --body '<visible reply>' \
  --json

doct-agent plans ack \
  --base-url https://doct.nodaste.com \
  --workspace-id <workspace-id> \
  --thread-id <thread-id> \
  --claim-id <claim-id> \
  --summary '<what changed or why no change was needed>' \
  --json

doct-agent plans resolve \
  --base-url https://doct.nodaste.com \
  --workspace-id <workspace-id> \
  --thread-id <thread-id> \
  --claim-id <claim-id> \
  --summary '<resolution summary>' \
  --json

doct-agent plans release \
  --base-url https://doct.nodaste.com \
  --workspace-id <workspace-id> \
  --thread-id <thread-id> \
  --claim-id <claim-id> \
  --reason '<why this agent cannot finish it now>' \
  --json
```

### Lifecycle, board, and readiness metadata

```bash
doct-agent plans lifecycle \
  --base-url https://doct.nodaste.com \
  --document-id <document-id> \
  --workspace-id <workspace-id> \
  --state active \
  --json

doct-agent plans board list \
  --base-url https://doct.nodaste.com \
  --workspace-id <workspace-id> \
  --json

doct-agent plans metadata \
  --base-url https://doct.nodaste.com \
  --document-id <document-id> \
  --workspace-id <workspace-id> \
  --execution-ready true \
  --json
```

Only set board columns when the user explicitly asks for a board move or an execution workflow requires it. Registration should keep the service default board assignment, normally `backlog`. Set readiness metadata only after the plan has passed the required independent readiness gates.

## Collab (realtime text surfaces)

### Append

```bash
doct-agent collab edit --document-id <id> --append-markdown '\n\nAppended by agent' --json
```

Append-only text edit over websocket/Hocuspocus.

### Anchored surgical text edits

```bash
doct-agent collab anchored replace        --document-id <id> --selected-text 'target text' --text 'replacement text'
doct-agent collab anchored insert-before  --document-id <id> --selected-text 'target text' --text 'prefix text'
doct-agent collab anchored insert-after   --document-id <id> --selected-text 'target text' --text 'suffix text'
doct-agent collab anchored delete         --document-id <id> --selected-text 'target text'
```

Optional `--prefix-text` / `--suffix-text` disambiguate repeated quotes.

### Text-document comments

```bash
doct-agent collab comments add       --document-id <id> --selected-text 'target text' --body 'initial thread body' [--prefix-text '...'] [--suffix-text '...'] [--preferred-from '...']
doct-agent collab comments list      --document-id <id> --json
doct-agent collab comments reply     --document-id <id> ...
doct-agent collab comments resolve   --document-id <id> ...
doct-agent collab comments unresolve --document-id <id> ...
doct-agent collab comments mentions  --workspace-id <id> --json
```

`comments list` works for text documents; plan comments use `doct-agent plans ...` commands instead.

### Anchored selection surface

Build `--selected-text`, `--prefix-text`, and `--suffix-text` from the document's **normalized collaborative plain-text view** (visible prose), not markdown syntax. `documents get --text` returns markdown only. Select on the words a reader sees, not on `**`, `#`, list markers, or link syntax.

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
doct-agent auth status --all --json
doct-agent auth renew --base-url https://doct.nodaste.com --json
doct-agent auth default --base-url https://doct.nodaste.com
doct-agent context --base-url https://doct.nodaste.com --json
doct-agent workspaces list --base-url https://doct.nodaste.com --json
doct-agent plans register --base-url https://doct.nodaste.com --file thoughts/plans/example.html --source-format html --allow-untemplated --json
doct-agent plans lifecycle --base-url https://doct.nodaste.com --workspace-id <workspace-id> --document-id <document-id> --state active --json
doct-agent plans agent next --base-url https://doct.nodaste.com --workspace-id <workspace-id> --document-id <document-id> --no-wait --json
doct-agent plans agent next --base-url https://doct.nodaste.com --workspace-id <workspace-id> --document-id <document-id> --wait --timeout 300 --json
doct-agent plans update --base-url https://doct.nodaste.com --id <document-id> --workspace-id <workspace-id> --file thoughts/plans/example.html --source-format html --expected-version <version> --json
doct-agent plans queue list --base-url https://doct.nodaste.com --workspace-id <workspace-id> --document-id <document-id> --json
doct-agent documents list --workspace-id <id> --json
doct-agent documents get --id <document-id> --text
doct-agent documents create --workspace-id <id> --title 'Title' --path 'notes/title' --kind text --content '# Visible document'
doct-agent documents replace-body --id <document-id> --file prepared.md --json
doct-agent collab edit --document-id <id> --append-markdown '\n\nAppended by agent'
doct-agent collab anchored replace --document-id <id> --selected-text 'target text' --text 'replacement text'
doct-agent collab comments add --document-id <id> --selected-text 'target text' --body 'initial thread body'
doct-agent triage logs doct production --limit 50 --json
```
