# Architecture

herdr-ntfysh is a short-lived CLI that herdr spawns per event. It reads the
event and configuration, decides whether to notify, publishes to ntfy, and
exits. There is no daemon and no persistent connection.

## Invocation model

herdr runs the binary in three situations, all through the same `main`:

| Trigger | herdr config | Mode |
|---|---|---|
| Agent status change | `[[events]] on = "pane.agent_status_changed"` | event |
| Manual test | `[[actions]] id = "test"` → `--test` | user-facing |
| Config inspection | `[[actions]] id = "doctor"` → `--doctor` | user-facing |

Because the binary is re-spawned on every status change, startup cost matters.
A compiled Go binary with no runtime and no `node_modules` starts in
low-single-digit milliseconds, which is why Go was chosen over the Node
approach of the prior art.

## Failure policy

The single most important design rule: **the event path never fails loudly.**
A misconfigured `.env`, an unreachable ntfy server, or a malformed event is
logged to stderr (which herdr captures) and the process exits `0`. If this
plugin crashed or exited non-zero on every event, it could disrupt herdr's
event pipeline — a notifier is not worth that.

The `--test` and `--doctor` actions are the exception: they are invoked
deliberately by a human who wants a pass/fail signal, so they exit non-zero on
error.

## Packages

```
main.go                 orchestration + the fail-safe exit-code policy
internal/config         resolve + validate settings (env > .env file)
internal/event          parse HERDR_PLUGIN_EVENT_JSON, with HERDR_* fallbacks
internal/decide         map a status transition -> notify decision + kind
internal/render         event + kind + config -> ntfy.Message (title/body/tags)
internal/ntfy           dependency-free HTTP client (auth + custom TLS)
internal/dedup          per-pane last-seen + debounce state, persisted as JSON
```

Dependency direction is acyclic: `decide`, `render`, `ntfy` and `dedup`
depend on `config`; `main` depends on everything. Nothing depends on `main`.

## Status model

herdr rolls each pane up to `idle | working | blocked | done | unknown` and
delivers transitions via `pane.agent_status_changed`. The observed payload is:

```json
{"event":"pane_agent_status_changed",
 "data":{"pane_id":"w5:p2","workspace_id":"w5","agent_status":"idle","agent":"claude"}}
```

Two things make the "done" signal non-trivial, both handled in `internal/decide`:

- herdr **usually** emits `done` directly when a turn finishes, but **some**
  completions arrive only as a `working → idle` transition. Both are mapped to
  the `done` kind, so completion is caught either way.
- Detecting the `working → idle` case requires the previous status, which is
  why `internal/dedup` persists the last-seen status per pane across the
  short-lived invocations.

The event's `agent_status` is the raw status; the notification *kind* ("done",
"blocked", "working", "idle") is what `decide` produces and what `render` uses
for wording, tags and priority — they are deliberately separate.

## Configuration resolution

Two layers, highest priority first:

1. Process environment (`HERDR_NTFY_*`) — herdr passes the invoking
   environment through, useful for overrides and testing.
2. A `.env` file, looked up in order: `HERDR_NTFY_ENV_FILE`, then
   `HERDR_PLUGIN_CONFIG_DIR/.env` (the durable per-plugin location herdr
   assigns), then `./.env`.

Validation only runs when the plugin is enabled, so a disabled plugin never
errors on a missing server/topic. Secrets are redacted in every output path.

## Event payload

The `pane.agent_status_changed` payload is read defensively. herdr versions
differ, so every field is optional; missing location fields fall back to the
`HERDR_WORKSPACE_ID` / `HERDR_TAB_ID` / `HERDR_PANE_ID` runtime variables.
The fields consumed are:

```
data.agent_status              idle | working | blocked | done | unknown
data.agent / data.display_agent friendly agent name (display_agent preferred)
data.workspace_id / data.tab_id location breadcrumb (workspace/tab also read)
data.pane_id                   stable key for state + debounce bookkeeping
data.custom_status             free-form status text, if present
data.state_labels.task         detail preferred for done/working, if present
data.state_labels.error        detail preferred for blocked, if present
```

The core payload carries `agent_status`, `agent`, `pane_id` and
`workspace_id`; the richer fields (`display_agent`, `custom_status`,
`state_labels`) are read opportunistically and simply absent on lean events.

## ntfy protocol choices

- Notifications use ntfy's HTTP header protocol (`X-Title`, `X-Priority`,
  `X-Tags`, …) over a plain `POST`, so there are no client libraries to
  maintain.
- **Emoji are ntfy tag shortcodes** (`white_check_mark`, `rotating_light`),
  not raw Unicode. HTTP header values must stay ISO-8859-1/ASCII clean, so
  the title uses an ASCII separator and lets ntfy render the emoji from tags.
  Free-form Unicode only ever appears in the request body.
- Auth precedence: an access token (Bearer) beats basic credentials.
- TLS: a custom CA bundle is preferred; `InsecureSkipVerify` is an explicit,
  documented last resort.

## Debounce

herdr can re-emit an event, and an agent can flap between states, so a single
logical "done" could otherwise become a burst of pushes. `internal/dedup`
persists a small JSON map per pane under `HERDR_PLUGIN_STATE_DIR` holding both
the last-seen status (for `working → idle` detection) and the last-notified
kind + timestamp. A notification of the same kind for the same pane within the
configured window is suppressed. It writes via a temp-file rename so a crash
can't leave truncated state. When no state dir is available (e.g. a standalone
`--test`), state is in-memory only for that run.
