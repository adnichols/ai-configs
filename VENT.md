# VENT

Feedback log. Repeated/systemic workflow friction that should become future automation, docs, or workflow fixes.

## 26-07-17 17:17 — codex-app-server-proxy-framing

Targeted stale-goal cleanup hit the same timeout twice because `codex app-server proxy`, even with the explicit control socket, did not expose the documented app-server JSONL request/response protocol to stdin. The repeated workaround was launching a standalone `codex app-server`, resuming each thread, then calling `thread/goal/set` and `thread/goal/clear`. A documented control-socket framing/auth contract or a first-class `codex thread goal complete/clear <id>` CLI command would prevent this retry sequence.
