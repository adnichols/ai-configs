# Run-plan implementation review — Claude Doct slice (cycle 1 incomplete)

- Review ID: `whats-new-downstream-claude-r1`
- Nonce: `230c76fb5da46880f61aa1544efd1952`
- Model: `claude-sonnet-5`, xhigh, Read/Grep/Glob only
- Comparison inspected: Doct `origin/develop...aa82be21`
- Fingerprint: unchanged before/after review
- Verdict: `REVIEW_INCOMPLETE_RERUN_NEEDED`

## Doct disposition

- Template/config/register/update parity and reason-bearing bypass behavior were read and found structurally correct.
- The reported P1 about all existing Markdoc plans requiring immediate bulk backfill is **OUT_OF_SCOPE_FOLLOW_UP / intentional compatibility behavior**, not a regression: the locked plan explicitly says existing Markdoc remains readable, and a later validated update must add the section or use the existing audited bypass; it explicitly rejects a versioned migration subsystem and bulk historical rewrite.
- The Rust direct-contract test observation is non-blocking because the plan requires Rust additions only if the config-driven consumer is not already covered; direct inspection confirmed the shared algorithm.
- The inert `allowLegacyHtml` question is pre-existing and not introduced by this diff.

## Remaining allowed follow-up slice

Claude could not read the Heddle worktree from a Doct-scoped session. Run one Heddle-only Claude slice in the Heddle worktree after the same-cutover backfill fix. That slice is the single allowed incomplete-review follow-up.
