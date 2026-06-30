---
name: pi-rpc-discord-bridge
description: Build or repair the Hermes user plugin that relays to pi sessions from Discord/Hermes. For Aaron's workflow, direct headless starts are disabled; use tmux for initial launch and reserve RPC for explicit bridge/maintenance work.
---

# Pi RPC Discord Bridge

Use when Aaron wants bridge/relay behavior inside Hermes/Discord. Do not use this skill to perform the initial pi launch for normal coding work — initial launch must happen in tmux so the run is visible.

## Current implementation

- Plugin path: `~/.hermes/plugins/pi_rpc_discord/`
- Files:
  - `plugin.yaml`
  - `__init__.py`
  - `client.py`
- Registered tool: `pi_rpc_session`
- Toolset: `pi_rpc`
- Hook: `pre_llm_call`

## Why RPC over SDK

Choose **pi RPC mode** for Hermes Python integration:
- Hermes is Python; pi SDK is TypeScript-first.
- RPC already exposes `prompt`, `steer`, `follow_up`, `abort`, `get_state`, `get_last_assistant_text`, and session metadata over JSONL.
- It avoids tmux/CLI scraping while keeping pi isolated in its own process.
- It is simpler to ship as a Hermes plugin than embedding a Node runtime bridge around `AgentSession`.

Use the SDK only if you are willing to build a dedicated Node sidecar/service and want deep in-process control over resource loaders, custom tools, or session-runtime replacement.

## Implementation notes

### Plugin behavior

- Historical implementation started `pi --mode rpc` via `subprocess.Popen()`.
- Aaron's current workflow requirement is stricter: initial launch must happen in tmux, and direct headless RPC starts should be treated as bridge-maintenance behavior only.
- Uses binary stdout reading with manual `\n` JSONL framing.
- Tracks request/response IDs with per-request queues.
- Polls `get_state` until `isStreaming == false`, `pendingMessageCount == 0`, and not compacting.
- Retrieves final answer via `get_last_assistant_text`.
- Binds the current Hermes chat/thread context using `gateway.session_context.get_session_env()`.
- Injects pre-LLM guidance so Hermes prefers relaying thread messages to the bound pi session.

### Tool actions

`pi_rpc_session` still exposes:
- `start` (intentionally returns an error in Aaron's environment to prevent hidden headless launches)
- `send`
- `status`
- `abort`
- `stop`
- `list`
- `bind`
- `unbind`

### Repo resolution

- Accept explicit path if it exists.
- Otherwise try `~/code/<repo>`.
- Otherwise resolve the input as a path.

## Validation

Run from the Hermes repo with venv active:

```bash
source venv/bin/activate
python - <<'PY'
from hermes_cli.plugins import discover_plugins
from tools.registry import registry

discover_plugins()
print(registry.dispatch('pi_rpc_session', {
    'action': 'start',
    'repo': '/home/anichols/.hermes/hermes-agent',
    'display_name': 'rpc-test'
}))
PY
```

Expected: the tool returns an error explaining that direct RPC starts are disabled and that pi must be launched in tmux first.

## Common follow-up improvements

If Aaron wants more direct UX later, the next step is **gateway-native slash commands or streaming updates**, not a different transport:
- `/pi-start`
- `/pi-send`
- `/pi-stop`
- live partial pi stream into Discord while the RPC session runs

That requires Hermes gateway/core changes; the current plugin intentionally avoids them.
