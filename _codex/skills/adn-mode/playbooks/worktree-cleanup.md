# Worktree cleanup

Read the parent skill and [Codex runtime contract](../references/codex-runtime.md).

Inspect disk usage and Git worktree status before proposing cleanup. Identify ownership, dirty or untracked changes, branches, and merge state. Preserve any work not proven disposable. Separate safe temporary artifacts from repositories, simulators, or worktrees that require a specific decision. Delete only the exact authorized targets and verify reclaimed state. Do not use a blanket prune or reset as evidence that user work is safe.
