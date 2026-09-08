# Pause safely

Read the parent skill and [Codex runtime contract](../references/codex-runtime.md).

On an explicit pause, stop starting new units. Preserve in-progress files and evidence. Record the current goal, constraints, decisions, worktree state, verification, background processes, and next action in the requested handoff or a scoped local artifact. Stop only task-owned processes when appropriate; do not kill unrelated services. Do not commit or publish solely to manufacture a clean handoff. Return a usable resumption pointer.
