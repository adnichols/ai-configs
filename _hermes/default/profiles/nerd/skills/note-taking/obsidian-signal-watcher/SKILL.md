---
name: obsidian-signal-watcher
description: Set up a quiet-by-default Obsidian vault watcher that scans on an interval, scores likely signals, persists state, and only notifies when meaningful changes appear.
---

# Obsidian Signal Watcher

Use this when a user wants ongoing signal detection from one or more Obsidian vaults, especially for product/project updates, without noisy heartbeat messages.

## When to use
- The user wants periodic checks of Obsidian vaults for new signals
- Notifications should happen only when something meaningful changed
- The monitoring should prioritize certain projects, folders, or keywords
- A lightweight local watcher is acceptable

## Important terminology check
Before implementing, clarify what the user means by **"signal"**.

Two common meanings can coexist:
1. **Formal signal protocol** — structured agent-to-agent message notes in the Studio vault (for example under `studio/Nodaste Agents/Signals/...`)
2. **Generic signals** — incoming information, updates, decisions, context changes, or clarity from many sources across the vault

Do not assume these are the same. A good setup may need to:
- prioritize formal protocol inboxes separately, and/or
- run broader heuristic scanning for general product/project signals

## Default approach
1. **Clarify the delivery constraint first**
   - Confirm whether the environment can actually post to the desired destination (e.g. Discord threads).
   - If thread creation or channel management is not available, say so clearly and proceed with the closest workable setup.

2. **Create a local watcher script under `~/.hermes/scripts/`**
   - Use a Python script like `~/.hermes/scripts/obsidian_signal_watch.py`
   - Persist last-scan state in `~/.hermes/state/obsidian_signal_watch_state.json`
   - Append detected-signal history to `~/.hermes/state/obsidian_signal_watch_log.md`

3. **Watch only the intended vaults**
   - Typical roots:
     - `~/Documents/Obsidian/adn_vault`
     - `~/Documents/Obsidian/studio`
   - Skip noisy directories such as:
     - `.git`, `.obsidian`, `.tmp`, `node_modules`, `__pycache__`, `.ruff_cache`
     - binary-heavy or attachment directories like `attachments`, `assets`, `Browsers`

4. **Score signal candidates instead of notifying on every file change**
   - Scan recently modified `*.md` files since the last run
   - Boost score for high-signal paths like:
     - `projects`
     - `Action Tracking`
     - `Nodaste Agents`
     - `Meeting Transcripts`
     - `reference`
   - Boost score for priority terms like:
     - `c-core`, `ccore`, `context core`
     - `hud`
     - `doct`, `doc t`, `dock t`
     - `heddle`
     - `design partner`, `decision log`, `action tracking`, `nodaste agents`
   - Quiet-by-default threshold used successfully:
     - notify if top item score `>= 6`, or
     - notify if at least 3 of the top 5 items score `>= 3`

5. **Make the first run silent**
   - On first run, initialize `last_scan` and exit without printing anything
   - This avoids spamming from pre-existing vault contents

6. **Emit a compact signal report**
   - Print a line starting with `SIGNAL:` so a background watcher can detect it
   - Include top changed files, timestamps, reasons, and a short excerpt from each file
   - Keep the summary short enough to paste into chat cleanly

7. **Run as a background process for real-time watch-pattern notifications**
   - Start an infinite loop that runs the script, prints output only when non-empty, then sleeps
   - For a 30-minute cadence: `sleep 1800`
   - Use terminal background execution with `watch_patterns=["SIGNAL:"]`
   - Poll once after launch to confirm the process is running and quiet

## Example behavior
- No meaningful change -> no output, no notification
- New high-signal C-Core / HUD / DocT note or Action Tracking update -> watcher emits `SIGNAL:` report

## Recommended implementation details
- Limit candidate analysis to a manageable recent set (e.g. 12 files)
- Use a small timestamp skew (e.g. 5 seconds) to avoid race conditions around write times
- Extract the first meaningful content line, skipping frontmatter and blank lines
- Sort by `(score, modified_time)` descending

## Verification checklist
- Run the script once manually: it should initialize state and stay silent
- Run it a second time with no vault changes: still silent
- Start the background loop and confirm the process stays running
- Verify that signal output begins with `SIGNAL:` so watch-pattern notifications trigger

## Limitations to communicate clearly
- Hermes may be able to notify about a signal but not create Discord threads automatically
- A background watcher is less durable than a platform-native scheduler if the runtime restarts
- Without extra dedupe logic, repeated edits to the same hot file can retrigger notifications

## Platform-specific scheduler note
- If the environment already has Hermes' built-in cron scheduler available and the goal is **protocol-native inbox processing** rather than instant chat notifications, a Hermes cron job every 5 minutes is a valid watcher mechanism.
- On macOS, if the user wants **realtime** processing and specifically wants the automation to belong to the agent stack rather than the Obsidian plugin surface, use a **Hermes-owned script under `~/.hermes/scripts/` plus a user LaunchAgent** watching the inbox directory.
- In that pattern, `launchd` provides the directory-change trigger and the Hermes-owned watcher script scans for `SIG-*.md` with `status: new`, uses a lock to prevent overlap, and invokes Hermes on the exact signal note.
- Keep delivery local-only / note-native by default so the signal note remains the source of truth and chat does not get heartbeat noise.
- If using `launchd`, store the automation files outside the vault (for example under `~/.hermes/` and `~/Library/LaunchAgents/`) so watcher logic stays agent-owned.

## macOS realtime pattern (agent-owned)
1. Create a Hermes-owned watcher script under `~/.hermes/scripts/`.
2. Have it watch only the intended inbox path and only process `SIG-*.md` with `status: new`.
3. Use a lock file under `~/.hermes/watchers/<name>/` to prevent overlapping runs when multiple filesystem events fire.
4. Install a user LaunchAgent plist under `~/Library/LaunchAgents/` with `WatchPaths` pointing at the inbox directory.
5. Log stdout/stderr to `~/Library/Logs/` and watcher activity under `~/.hermes/watchers/<name>/watcher.log`.
6. Keep a cron/backstop watcher if missed events or downtime would matter.

## Important implementation lesson
- Do **not** assume the user wants watcher logic implemented as an Obsidian plugin just because Obsidian can observe vault events.
- If the user frames it as agent automation, keep the code in the Hermes-owned runtime surface (`~/.hermes`) and use Obsidian only as the data source/vault, not the execution host.
- When editing signal notes from Hermes, be careful with `read_file` re-reads in the same conversation: it can return a sentinel like `File unchanged since last read...` instead of the full file body. Never write that sentinel back into the note. For post-write verification, either trust the explicit content you just wrote or verify with a direct filesystem read (for example via `terminal`/Python) rather than feeding the cached `read_file` text back into another write.

## macOS realtime pattern for vaults under ~/Documents
When the user wants **realtime** signal processing on macOS and the vault lives under `~/Documents`, the safest reusable pattern is:
1. **Use Obsidian app-context events as the realtime trigger**
   - Prefer a local Obsidian plugin or Shell Commands event hook that listens for vault `create` / `modify` / `rename` events.
   - Filter immediately to the exact inbox path, e.g. `Nodaste Agents/Signals/inbox/aaron/SIG-*.md`.
2. **Invoke a local wrapper script outside the vault**
   - Put the processor under `~/.hermes/scripts/`.
   - The wrapper should validate the target path, ignore non-`SIG-*.md` files, parse frontmatter, and exit unless `status: new`.
3. **Use a lock file to prevent event storms / overlapping runs**
   - Obsidian file events may fire more than once as notes are written and then updated.
   - A lock file plus a short debounce window prevents duplicate Hermes runs.
4. **Keep Hermes focused on one exact signal file**
   - Pass the absolute signal path into the wrapper.
   - In the prompt, make the default contract explicit.
   - For Aaron's current setup, the default contract is **notify-only**: summarize the new signal to Aaron and leave the note untouched.
   - Do **not** acknowledge, resolve, or otherwise change signal state unless Aaron has explicitly pre-approved that signal type for autonomous handling and Hermes is highly confident the requested action was actually completed.
   - If uncertain what action to take, notify Aaron of the signal and leave it unacknowledged.
   - Do not invent new autonomous handling rules inside the watcher.
5. **Keep a polling fallback**
   - Retain a Hermes cron watcher or similar catch-up loop in case Obsidian is closed or an event is missed.

### Why this pattern is preferred
- Vault-local app context already has the file permissions that background macOS jobs often lack.
- It gives near-immediate processing without making `launchd` the primary reader of protected `~/Documents` content.
- The fallback poller preserves backlog recovery.

### What to avoid as the primary mechanism
- Do **not** default to direct `launchd` watching of a vault under `~/Documents` when a safer app-context trigger is available.
- Existing workspace docs explicitly warn that background `launchd` jobs against `~/Documents` can fail with `Operation not permitted`.

### Important troubleshooting lesson: `status: new` filter can hide real arrivals
If a realtime watcher is implemented to process only inbox notes with `status: new`, it can appear to "miss" a signal even when `launchd` / filesystem watching is working correctly.

A concrete failure mode:
- another agent creates a recipient inbox `SIG-*.md` file already marked `status: done`
- the watched inbox path receives the file event
- the realtime watcher sees the file but skips it because its logic only handles `status: new`
- a polling / cron watcher later reports the file, making it look like realtime failed

Implications:
- this is often a **protocol / watcher-contract mismatch**, not a broken watcher
- verify both the watched path **and** the status filter before debugging `launchd`
- for notify-only inbox monitoring, consider notifying on **first-seen inbox files** even if status is already `done`, or enforce a protocol rule that recipient inbox copies always start as `status: new`
- when diagnosing, check watcher logs for explicit skip messages like `status is 'done', not 'new'`

### Important troubleshooting lesson: inbound-only watchers miss requester-facing follow-ups
A watcher aimed only at one user's inbox (for example `Signals/inbox/aaron`) is **not** a general "tell me about any important signal development" monitor.

A concrete failure mode:
- Aaron sends Ana a signal asking her to join a shared `ccore` space
- Ana updates **her inbox copy** / Aaron's **outbox mirror** with a blocker such as `status: needs_info_from_requester`
- Aaron's realtime watcher never fires, because it only watches `Signals/inbox/aaron`
- this can look like the watcher missed an important update, when in reality the update happened outside the watched path and outside the `status: new` contract

Implications:
- distinguish **new inbound work** from **follow-up / blocked / needs-info responses on sent work**
- if the user expects "tell me when something I sent now needs my attention," add a second watcher surface such as:
  - `Signals/outbox/<user>` for statuses like `needs_info_from_requester`, `blocked`, or new response text
  - and/or specific teammate inboxes for signals originally sent by the user
- when diagnosing a miss, check three things before blaming `launchd`:
  1. was the file under the watched path?
  2. did its status satisfy the watcher's filter?
  3. was the important change a **new file arrival** or a **follow-up edit to an existing signal**?

## Architecture pitfall: CLI wake-up is not the same as a channel message
When the user wants a vault signal to be handled **like an incoming Discord/Telegram message**, do **not** treat a file watcher that shells out to:

```bash
hermes chat -q "..."
```

as equivalent to a real inbound conversation.

Why this matters:
- A standalone `hermes chat` run creates a fresh CLI/tool session, not a gateway-origin `MessageEvent`
- `--source tool` is only a session/source tag, **not** a real Discord/Telegram/webhook conversation source
- The agent may choose ad-hoc notification mechanisms (for example local `osascript` notifications on macOS) instead of routing through the messaging gateway
- This can produce false "Notified Aaron" summaries even though no Discord/Telegram message was actually delivered

### Prefer these mechanisms when the user wants channel-like behavior
1. **Best fit: gateway platform adapters**
   - Real Discord / Telegram / Slack / Signal inbound messages already become `MessageEvent`s inside the Hermes gateway
   - Use this when the signal can be posted into a real chat/channel/thread
2. **Best bridge for file-based signals: webhook adapter**
   - Have the file watcher POST a structured payload to a Hermes webhook route
   - The webhook adapter turns that POST into a real `MessageEvent`
   - This is much closer to "wake Hermes up as a conversation" than invoking `hermes chat`
3. **Dedicated profile + channel-bound bot**
   - If the user wants a specialized agent living in one Discord/Telegram channel, use a separate Hermes profile and gateway instance

### What to avoid
- Do **not** present a LaunchAgent/file-watcher + `hermes chat` subprocess as if it were a true watched messaging channel
- Do **not** rely on local desktop notifications (`osascript`, Notification Center, etc.) when the user expects a Discord/Telegram-style incoming conversation or message delivery
- Do **not** claim notification success unless the run actually used a messaging delivery path or the gateway/webhook conversation itself delivered the response

## Protocol-native inbox processor pattern
When the watcher job is explicitly asked to **process formal Nodaste signals in place** rather than merely notify, use this contract:

1. Read the local protocol/operating-model docs and the agent identity file first.
2. Scan only the specified inbox for `SIG-*.md`.
3. Parse frontmatter and keep only `status: new` items.
4. Sort by `priority`, then `due_at`, then `created_at`, then filename.
5. Update the **inbox note itself**:
   - keep `## Response` current with short timestamped lines
   - update `last_updated_at`
   - set `status: done` when the signal has been received/acknowledged and no concrete requester action is required, even if the response includes feedback or recommendations for future packaging/process changes
   - set `status: needs_info_from_requester` only when the current signal cannot be completed without a specific answer or artifact from the requester, and put concrete questions under `## Clarifying Questions`
   - do **not** use `needs_info_from_requester` merely because you found a related issue, missing optional artifact, or have feedback; if the user's intent is “we see it, we're done,” close as `done` and put feedback in `## Response`
   - use `status: in_progress` only when work is genuinely still underway
6. If `linked_signal_path` exists, mirror the same status / response / frontmatter changes into that linked note immediately.
7. Keep the chat output quiet and terse:
   - if no new signals: `No new Aaron signals.`
   - otherwise return a compact processed-id/status summary line

### Important lesson: local task instructions can override generic watcher defaults
A generic watcher skill may recommend notify-only handling, but some vault setups use the watcher as a **protocol-native note processor**. In those runs, follow the task-local contract and update the signal note as the source of truth.

## Webhook bridge pattern for real incoming-conversation handling
When the user wants a vault signal to be handled **like a real inbound Discord/Telegram conversation**, do **not** wake Hermes by spawning a standalone CLI run such as `hermes chat -q ...` from the file watcher.

That pattern is the wrong abstraction because it creates an isolated CLI session with a source tag, not a gateway-origin `MessageEvent`. In practice it can drift into the wrong delivery mechanism (for example local `osascript` notifications, ad-hoc cron jobs, or other side channels) instead of behaving like a normal inbound chat conversation.

### Preferred pattern
Use a **local file watcher → Hermes webhook adapter → gateway MessageEvent** bridge:

1. Keep the filesystem watcher lightweight.
2. On each newly detected `SIG-*.md` with `status: new`, POST a JSON payload to a local Hermes webhook route.
3. Let the webhook adapter create the `MessageEvent` and route the final response using its normal `deliver` target (for example `discord` with `chat_id` + `thread_id`).
4. In the webhook route prompt, explicitly say that the webhook conversation's **final response is automatically delivered by Hermes** and that the agent must **not** use `cronjob`, `send_message`, `osascript`, or other side-channel notification mechanisms unless the signal explicitly requests an additional separate destination.

### Concrete local pattern that worked
- Watcher script under `~/.hermes/scripts/aaron_signal_watch_launchd.py`
- LaunchAgent plist under `~/Library/LaunchAgents/com.anichols.aaron-signal-watcher.plist`
- Webhook endpoint: `http://127.0.0.1:8644/webhooks/aaron-signal`
- Use HMAC signing on the POST body (for Hermes webhook auth)
- Include payload fields such as:
  - `event_type`
  - `signal_path`
  - `signal_id`
  - `signal_type`
  - `priority`
  - `status`
  - `summary`
  - `from_agent`
  - `to_agent`
  - `created_at`
- Use a stable delivery id like `signal_id:mtime_ns` for webhook idempotency
- Persist a small seen-state map (for example `dispatched_signals.json`) so the watcher only posts once per currently-new signal path

### Aaron-specific delivery note
For Aaron's current setup, if a signal explicitly requests notifying Aaron on Discord and no other destination is specified, use Hermes home Discord delivery (`discord`) as the default out-of-band target instead of blocking on destination ambiguity.

### Discord delivery lesson: fixed thread vs new thread per signal
If the user wants **each detected signal to appear as a new Discord thread under a channel**, do **not** configure the webhook route with a fixed `thread_id` in `deliver_extra`.

A fixed-thread configuration like:

```yaml
deliver: discord
deliver_extra:
  chat_id: "1492535022811480126"
  thread_id: "1492880396646486186"
```

will route every webhook response into that one existing thread.

Instead, configure the route to target the parent channel and request thread creation:

```yaml
deliver: discord
deliver_extra:
  chat_id: "1492535022811480126"
  create_thread: true
  thread_name: "{signal_id}"
  thread_reason: "New Aaron inbound Nodaste signal"
```

Implementation note:
- the webhook delivery path must forward Discord-specific metadata such as:
  - `create_thread`
  - `thread_name`
  - `thread_reason`
  - optional `auto_archive_duration`
- the Discord adapter must honor `create_thread=true` by creating a fresh thread under `chat_id` and posting the first response chunk there
- if the gateway only supports `thread_id`, the result will be "always post into one existing thread," which is the wrong behavior for per-signal thread fan-out

Verification:
- confirm the fixed `thread_id` is removed from the route
- send a test webhook and verify a **new thread appears under the parent channel**
- check that the created thread name matches the rendered `thread_name` template (for example the `signal_id`)

### Why this is better
- Hermes receives the signal through the same gateway pipeline used for real platform messages
- The run gets a real `platform=webhook` session and `MessageEvent`
- Delivery is handled by the configured route target instead of an improvised local notification
- This cleanly separates:
  - filesystem detection
  - inbound conversation creation
  - outgoing chat delivery

### Important delivery limitation: fixed `thread_id` means reuse, not per-signal thread creation
For Discord webhook-route delivery, the current cross-platform webhook path does **not** create a new Discord thread for each incoming signal.

What actually happens today:
- the webhook route stores `deliver` plus `deliver_extra`
- if `deliver_extra.thread_id` is set, Hermes sends the final response directly to that existing Discord thread
- if no `thread_id` is set, Hermes sends to the parent channel `chat_id`
- the webhook delivery path does **not** auto-create a fresh Discord thread per delivery

Implication:
- a route configured like:
  - `deliver: discord`
  - `deliver_extra.chat_id: <forum-or-channel-id>`
  - `deliver_extra.thread_id: <existing-thread-id>`
  will send **every** signal into that one existing thread

So if the user expects:
- each new signal detected should start a new thread under a parent Discord channel/forum

then that requires a code-path change or a dedicated thread-creation bridge step, not merely a prompt tweak.

### Verification lesson for Discord delivery debugging
When signals are appearing in the wrong Discord place, inspect the webhook route config first:
- `platforms.webhook.extra.routes.<route>.deliver`
- `platforms.webhook.extra.routes.<route>.deliver_extra.chat_id`
- `platforms.webhook.extra.routes.<route>.deliver_extra.thread_id`

If `thread_id` is present, Hermes will reuse that thread. Do not assume it is creating a new one per signal.
### Verification checklist for the webhook bridge
- Confirm `platforms.webhook.enabled: true` in `~/.hermes/config.yaml`
- Confirm the route exists under `platforms.webhook.extra.routes`
- Confirm the gateway is running and webhook is connected
- Send one manual POST and verify logs show:
  - `[webhook] POST event=... route=...`
  - `gateway.run: inbound message: platform=webhook ...`
  - `response ready: platform=webhook ...`
- Only after that trust the launchd/file-watcher trigger path

## Background process monitoring fit: use it for generic scanners, not the formal signal bus
Hermes background process monitoring (`terminal(background=true, watch_patterns=[...])`) is a good fit for **generic vault-change scanners** that emit sentinel lines such as `SIGNAL:`.

### Good fit
- a quiet Obsidian-wide heuristic scanner running in a loop
- ad hoc "watch this until something interesting happens" monitoring
- development/debugging of watcher scripts where the agent should wake up on matching output

Example pattern:
- watcher script prints `SIGNAL: ...` only when it detects something meaningful
- start it as a Hermes background process
- set `watch_patterns=["SIGNAL:"]`
- optionally add `notify_on_complete=true` for finite test runs

### Not the right replacement for the formal Aaron signal watcher
Do **not** treat Hermes background-process watch patterns as a drop-in replacement for the production Aaron signal watcher architecture.

Keep these roles separate:
- **formal signal bus / team inbox processing** -> Hermes cron and/or OS/file-trigger + webhook bridge
- **generic vault scanning / heuristic alerts** -> Hermes background process + `watch_patterns`

Why:
- `watch_patterns` is session-scoped agent tooling for reacting to process output
- cron / launchd / webhook patterns are better for durable always-on automation, realtime file triggers, protocol-native handling, and chat delivery semantics
- re-architecting the production signal bus around a long-lived Hermes background process would increase session coupling and notification-noise risk without improving the core delivery model

## Good follow-up improvements
- Add deduping by file path + recent hash
- Add per-project scoring weights
- Add structured signal briefs: `what changed / why it matters / suggested next action`
- If a durable scheduler is needed, port the script into a cronjob run — but note that cron is less suitable for immediate watch-pattern notifications unless note updates are the primary output
- For note-native realtime triggers, prefer file watcher -> Hermes webhook route -> gateway `MessageEvent` over file watcher -> `hermes chat`
