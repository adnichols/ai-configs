# Dirty-snapshot fix verification

## Fix
Skills/prompts ban Pi `isolation: "worktree"` for required read-only reviewers and require live-worktree provenance. Isolated clean-HEAD results while dirty changes are in scope are `REVIEW_INFRASTRUCTURE_FAILURE`.

## Recorded historical observations
The historical counts below are redacted coordinator records. The temporary marker fixture and raw subagent transcripts were not retained, so these counts are not independently auditable from the committed artifacts alone.

- Recorded post-fix live path: five no-isolation reviewer launches reported `DIRTY_FIXED_NEW` / `fixed-in-working-tree-only` and a non-empty `STATUS_SHORT` including the unstaged marker path.
- Recorded isolation control: one isolated launch reported `COMMITTED_OLD` with empty status in `<tmpdir>/pi-agent-*` and returned `REVIEW_INFRASTRUCTURE_FAILURE` under the new reviewer contract.

## Artifacts
- `thoughts/validation/dirty-snapshot-fix-verify.json`
- recorded pre-fix observations: `thoughts/validation/dirty-snapshot-mechanical.json`, `thoughts/validation/dirty-snapshot-agent-path.json`
