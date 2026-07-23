# VENT

Feedback log. Repeated/systemic workflow friction that should become future automation, docs, or workflow fixes.

## 26-07-17 17:17 — codex-app-server-proxy-framing

Targeted stale-goal cleanup hit the same timeout twice because `codex app-server proxy`, even with the explicit control socket, did not expose the documented app-server JSONL request/response protocol to stdin. The repeated workaround was launching a standalone `codex app-server`, resuming each thread, then calling `thread/goal/set` and `thread/goal/clear`. A documented control-socket framing/auth contract or a first-class `codex thread goal complete/clear <id>` CLI command would prevent this retry sequence.
## 26-07-22 21:53 — git-index-lock-contention

Repeated git add/commit attempts in the shared ai-configs checkout failed because another concurrent Git process intermittently held .git/index.lock, with no stable owner visible by the time diagnostics ran. Workaround: copied the staged index to an isolated temporary GIT_INDEX_FILE and committed successfully, preserving five unrelated unstaged files. A per-worktree commit/index lock or clearer concurrent-session coordination would prevent the repeated retries and protect shared working trees.
