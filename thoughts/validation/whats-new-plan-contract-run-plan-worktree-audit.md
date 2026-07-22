# Run-plan stale-worktree no-loss audit

**Decision:** retain all three stale worktrees. Their uncommitted state is not safe to delete; retention satisfies the plan’s explicit blocker/handoff path and does not block the fresh delivery branches.

## ai-configs

`/home/anichols/.herdr/worktrees/ai-configs/worktree-plan-whats-new-guidance`

- 45 status entries: 37 modified tracked files and 8 untracked plan/review artifacts.
- The stale diff includes retired `_pi/agents/plan-*` and `_pi/agents/reviewer-plan-*` surfaces intentionally excluded from the fresh implementation, plus stale review prompts absent from the delivered diff.
- Because those files are not represented in the fresh branch and may be user-owned reference state, removal is blocked.

## Doct

`/home/anichols/.herdr/worktrees/doct/worktree-plan-whats-new-guidance`

- 7 modified tracked files.
- The file set overlaps the delivered adapter, but the stale worktree remains an uncommitted independent patch based on an older tip. It was not destructively normalized or deleted.

## Heddle

`/home/anichols/.herdr/worktrees/heddle/worktree-plan-whats-new-guidance`

- 11 modified tracked files and 1 untracked changelog fragment.
- The stale patch uses a different changelog artifact and predates the fresh current-plan backfills and independent-cutover corrections. It was not destructively normalized or deleted.

## Preserved delivery

- ai-configs: branch `whats-new-plan-contract`, PR https://github.com/adnichols/ai-configs/pull/47
- Doct: branch `whats-new-plan-contract`, PR https://github.com/Nodaste-Lab/doct/pull/275
- Heddle: branch `whats-new-plan-contract`, PR https://github.com/Nodaste-Lab/heddle/pull/491

A future cleanup owner may compare or archive the stale patches, but this run performs no worktree removal because the no-loss condition is not proven.
