---
name: ccore-cli-operations
description: Use the ccore CLI as the primary operator surface for Context Core spaces, signals, workstreams, decisions, packages, and ingest workflows.
---

# C-Core CLI operations

Use this when work is moving from Obsidian-note conventions toward canonical Context Core objects and the `ccore` CLI.

## Core rule

Start with:

```bash
ccore skill
```

or save the live guide for reference:

```bash
ccore skill --output /tmp/ccore-skill.md
```

Treat `ccore` as the primary local operator/agent surface. Prefer it over inventing ad hoc file conventions when the work should live in Context Core.

## First diagnostics

Before doing anything substantive:

```bash
ccore health
ccore identity --json
ccore status
```

If the task is space-specific, also run:

```bash
ccore space list
ccore space sync-status <space> --json
```

## Signals

Signals are canonical managed objects, not markdown notes.

See `references/bulk-signal-resolution-verification.md` for a concrete verification pattern when bulk-closing handled signals and re-resolving stale-version leftovers.

### Create a signal

```bash
ccore signal create <space> \
  --title "<title>" \
  --content '{"status":"new","body":"<details>","priority":"high"}'
```

### List signals

```bash
ccore signal list <space>
```

### Read / update lifecycle

```bash
ccore signal get <signal-id>
ccore signal acknowledge <signal-id> --expected-current-version-id <version>
ccore signal start <signal-id> --expected-current-version-id <version>
ccore signal block <signal-id> --expected-current-version-id <version>
ccore signal request-info <signal-id> --expected-current-version-id <version>
ccore signal resolve <signal-id> --expected-current-version-id <version>
ccore signal append-response <signal-id> --expected-current-version-id <version> --response "<text>"
```

When bulk-closing signals, do not trust a single successful resolve batch as final. Immediately run a fresh `ccore signal list <space> --json` and filter for nonterminal statuses. If a signal reappears as nonterminal with a different `current_version_id` (for example from stale list/sync state), run `ccore signal get <signal-id> --json` and resolve it again with that fresh version, then verify the active set is empty.

Important inspection note:
- `ccore signal get <signal-id>` returns signal metadata, but not necessarily the full body content.
- To inspect the canonical JSON payload/body for a signal, use the backing document surface:

```bash
ccore doc show <signal-id> --space <space> --include-content
```

That returns `current_version_content`, which is typically a **JSON-encoded string** for signal docs, not an already-decoded object. Parse it before accessing fields. After parsing, it includes fields such as:
- `requester_actor_id`
- `assignee_actor_id`
- `body`
- `status`
- `priority`
- `last_response_at`
- `response_count`

Practical shell pattern:

```bash
ccore doc show <signal-id> --space <space> --include-content \
  | jq -r '.current_version_content | fromjson'
```

## Workstreams / sessions / decisions / packages

### Workstreams

```bash
ccore workstream list <space>
ccore workstream show <workstream-id>
```

### Decisions

```bash
ccore decision list <space>
ccore decision show <decision-id>
ccore decision trace <decision-id>
```

### Canonical packages

```bash
ccore package list <space>
ccore package show <package-id>
```

## Search vs query

Use legacy document-only search only when you specifically want documents:

```bash
ccore search <space> <query>
```

Prefer ranked query when decisions/packages/documents may all matter:

```bash
ccore query <space> <query> --kinds documents,decision_records,canonical_packages
```

## Ingest

### Obsidian ingest

```bash
ccore ingest obsidian <space> <vault_path>
ccore ingest status <ingest_run_id>
```

Important identity note:
- `ccore_id` frontmatter is the stable identity mechanism.
- `write_frontmatter_id=true` is default.
- If you need no source-file mutation, use the no-rewrite ingest configuration path instead of assuming note-native signal storage.

## Practical operating guidance

- Prefer diagnostics before repair.
- Do not paste passphrases, hub tokens, invite codes, or bundles into logs.
- For unclear sync/account/device state, stop at `health`, `identity`, `status`, and `space sync-status` before using repair commands.
- Treat `ccore space rejoin`, authority remediation, and sync repair as explicit operator actions.

## Recovery pattern: remote shared space is discovered but not locally attached

A reusable failure mode on receiver machines is:
- `ccore init` succeeds enough to discover the remote shared space
- the local space still does **not** appear in `ccore space list`
- `ccore space sync-status <space> --json` says the local space is missing and suggests `ccore space invite-import <code-or-bundle>`
- the error / signal context mentions missing **same-account bootstrap attach material** or an incomplete shared-space ensure response

Treat this as an **attach/bootstrap contract gap**, not as proof that more receiver-side local cleanup is needed.

### Safe next-step sequence
1. On the receiver / affected machine, capture:
   ```bash
   ccore health
   ccore status
   ccore space sync-status <space> --json
   ```
2. On a machine where the shared space is already healthy/attached, verify the space exists:
   ```bash
   ccore status
   ccore space list
   ```
3. Generate fresh invite material from the healthy owner/member machine:
   ```bash
   ccore space invite <space>
   ```
4. Use the receiver-side import path explicitly:
   ```bash
   ccore space invite-import <fresh-code-or-bundle>
   ```
5. Then re-check on the receiver:
   ```bash
   ccore status
   ccore space sync-status <space> --json
   ```

### Decision rule
- If the receiver can now discover the remote space but cannot attach it locally because the ensure/bootstrap payload is incomplete, prefer **fresh explicit invite/import** as the next operator action.
- Do **not** jump straight to destructive local repair (`forget-sync`, deleting local state, etc.) unless diagnostics show a real stale-linkage conflict.
- If a local space already exists but is misbound, then escalate to `ccore space rejoin <space> --invite-code ...` rather than treating it like a first import.

## When this matters most for Aaron

Use this skill especially when:
- moving studio signal workflows from Obsidian into Context Core
- evaluating C-Core readiness for shared team use
- working with HUD as the primary UX over C-Core
- inspecting canonical signals, project context, decisions, and packages

## Aaron-specific signal rule

For Aaron going forward:
- if Aaron asks to **send/create a signal**, default to creating the canonical signal in `ccore`, not as a vault markdown signal
- still check the Obsidian vault signal folders during review / `/gm` / migration periods, because some active work may still live there
- when reporting signal state, treat vault signals as a secondary compatibility surface unless Aaron explicitly asks for vault-native handling
- if a task needs both surfaces during transition, say so explicitly rather than silently using only the vault

## Current caveats

- The shipped signal model is canonical JSON-backed managed objects, not the older markdown-note signal protocol.
- Some repo docs and future docs may describe removed or planned surfaces; trust `ccore skill`, current CLI help, and implementation-authoritative specs first.
- For trust-sensitive rollout decisions, review known C-Core issues around auth, sync correctness, and onboarding before assuming team-safe behavior.
- DoltDB/Dolt is not a drop-in replacement for C-Core's embedded SQLite local store: Dolt is normally used through `dolt sql-server` via MySQL-compatible clients or through the `dolt` CLI, not as an in-process SQLite-style library. For C-Core/Heddle architecture research, prefer framing Dolt as an optional versioned projection/review/audit layer over selected canonical C-Core state unless Aaron explicitly asks for a full storage re-platforming analysis.

## Troubleshooting lessons

### Partial auth failure: `doc new` works but `status` / signals / workstreams 401

A recurring C-Core diagnostic shape is:
- `ccore health` succeeds or the node is reachable
- `ccore identity --json` shows `actors: []` and `default_actor_id: null`
- `ccore hub status` shows bootstrap auth not configured
- `ccore status`, `ccore signal create`, `ccore workstream create`, or direct managed-object/version endpoints return `401 Unauthorized` / `{"error":"unauthenticated"}`
- but some plain local commands such as `ccore doc new Personal ...` still succeed

Interpretation:
- treat this as a missing/expired/no-longer-accepted local account/session/bootstrap context, not as proof the node is dead
- plain document paths may be able to use a reachable local node/local space path without resolving the authenticated actor/hub/session context required by aggregate status, signal, workstream, or managed-object flows
- missing actor/default actor state is sufficient to explain authenticated path failures; stale/wrong-account space linkage may still exist as a second-layer issue, but repair account/session first

Safe repair order on the affected machine:
1. Capture read-only diagnostics first:
   ```bash
   ccore version
   ccore health
   ccore config show
   ccore hub status
   ccore identity --json
   ccore space list
   ```
2. Restore bootstrap/session before attempting space repairs:
   ```bash
   ccore hub login --hub-url <hub-url> --account-token <token>
   ccore init --hub-url <hub-url> --account-handle <handle>
   ```
   If hub bootstrap auth is already configured and valid, `ccore init --hub-url <hub-url> --account-handle <handle>` may be enough.
3. Re-check:
   ```bash
   ccore hub status
   ccore identity --json
   ccore status --json
   ccore doc list Personal
   ```
4. Only after session repair succeeds, diagnose or repair stale shared-space linkage (`sync-status`, invite/import, rejoin, etc.). Do not start with `forget-sync`, `rejoin`, `delete-local`, or direct DB edits while the machine is still unauthenticated.

Document cleanup caveat:
- Confirm current CLI capabilities with `ccore skill`; at the time this lesson was learned, `ccore doc` exposed `list/new/show` but not document update/delete, while typed managed objects exposed `ccore object update` / `ccore object delete`.
- For plain duplicate docs, prefer a supported soft-deprecation/canonical-replacement path unless a supported doc update/delete command/API exists. Avoid direct node mutation endpoints unless the CLI/API explicitly supports the mutation and the session is verified authenticated.

### If sync shows `lag > 0` with no explicit error
A useful live diagnostic pattern is:

```bash
ccore status
ccore space sync-status <space> --json
ccore space authority status <space> --json
```

If you see something like:
- `head_seq > last_seq`
- `lag: 1` (or another small positive number)
- `pending_local_changes: 0`
- `last_error: null`
- `wake_connected: true`

then do **not** assume the missing event is unreadable or blocked by authority state. First test whether it is immediately importable:

```bash
ccore space sync-pull <space>
ccore space sync-status <space> --json
```

Interpretation:
- if manual `sync-pull` imports the missing event and clears the lag, the problem is more likely a background sync/runtime wedge or stale telemetry than an unreadable remote event
- if manual `sync-pull` fails, inspect the exact failure before concluding auth/linkage is the cause

This matters because a space can look superficially healthy (`auto_sync_effective: true`, `wake_connected: true`) while still missing remote events.

### Authority-mode sanity check for fresh shared spaces
If a newly provisioned same-account shared space shows:

```bash
ccore space authority status <space> --json
```

with:
- `authority_mode: legacy_compatible`
- `can_cutover: true`
- remediation guidance telling the operator to run `ccore space authority cutover ...`

that is evidence the space is still being born in legacy-compatible mode instead of landing directly as `account_rooted`.

For operator triage, verify with:

```bash
ccore space authority cutover <space>
ccore space authority status <space> --json
```

If cutover is required on a freshly provisioned same-account shared space, treat that as a product bug / regression, not as the intended steady state.

### Issue-tracker note for the ccore repo
Before trying to file a GitHub issue, check whether repo issues are actually enabled:

```bash
gh issue list --repo Nodaste-Lab/ccore --state open --limit 20
```

If GitHub returns that issues are disabled, use the repo-local tracker under:

- `thoughts/issues/*.md`
- `thoughts/issues/README.md`

and update the indexed issue note there instead of claiming the issue was filed on GitHub.

## Sync-status interpretation lesson

A useful diagnostic pattern when a space looks healthy remotely but still shows `syncing` locally:

```bash
ccore status
ccore space sync-status <space> --json
ccore sync status --json
```

If you see a shape like:
- `head_seq: 1`
- `last_seq: 0`
- `lag: 1`
- `pending_local_changes: 0`
- `last_error: null`
- `auto_sync_effective: true`
- `global_sync_enabled: true`
- `wake_connected: true`
- `last_pull_at: null`

then the safe interpretation is:
- the local machine is exactly **one remote event behind**
- sync is **not disabled**
- there is **no recorded local write conflict**
- there is **no explicit sync error captured in status**
- the local node likely has **not yet completed a pull/apply cycle** for that space, or the sync telemetry is stale/incomplete

Important constraint:
- this output alone does **not** identify the exact root cause of why the pull has not completed
- do **not** overstate it as a confirmed sync bug, auth failure, or conflict without checking runtime logs / deeper diagnostics

Use this interpretation especially when:
- `ccore signal list <space>` is empty
- the actual coordination update lives in Obsidian / Nodaste Agents signal notes rather than canonical C-Core signal objects
- the user asks why sync is not complete and wants an evidence-based answer from current machine state
