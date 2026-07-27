# Dirty-snapshot fix verification

## Fix
Skills/prompts ban Pi `isolation: "worktree"` for required read-only reviewers and require live-worktree provenance. Isolated clean-HEAD results while dirty changes are in scope are `REVIEW_INFRASTRUCTURE_FAILURE`.

## Post-fix live path (no isolation): 5/5 PASS
All five reviewer launches saw `MARKER_STATE=DIRTY_FIXED_NEW` / `BUG_LINE=fixed-in-working-tree-only` in the live worktree, with non-empty `STATUS_SHORT` including the unstaged marker path.

## Control (isolation still used): still broken
One isolated launch still saw `COMMITTED_OLD` with empty status in `<tmpdir>/pi-agent-*` and correctly returned `REVIEW_INFRASTRUCTURE_FAILURE` under the new reviewer contract.

## Artifacts
- `thoughts/validation/dirty-snapshot-fix-verify.json`
- pre-fix baseline: `thoughts/validation/dirty-snapshot-mechanical.json`, `thoughts/validation/dirty-snapshot-agent-path.json`
