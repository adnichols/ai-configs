# Run-plan implementation review — Codex downstream slice (cycle 1)

- Review ID: `whats-new-downstream-codex-r1`
- Nonce: `abd364c24b96eeb31c63c0ee64e3c556`
- Model: `gpt-5.6-terra`, high reasoning, read-only
- Comparisons: Doct `origin/develop...aa82be21`; Heddle `origin/develop...75bdc5a1`
- Fingerprints: unchanged before/after review
- Verdict: `FIX_IN_SCOPE_FINDINGS`

## Finding

**P1 / IN_PLAN** — Four tracked Heddle plans dated/updated at the `2026-07-22` cutover are current-contract artifacts, lack `data-section="whats-new"`, and now correctly fail closed. The plan’s backfill-before-continuation policy requires adding exactly one section immediately after summary to:

- `thoughts/plans/nod-1392-auth-account-space-error-contracts.html`
- `thoughts/plans/nod-1410-v0250-migration-0046-collision-repair.html`
- `thoughts/plans/nod-1412-bounded-process-test-lifecycle.html`
- `thoughts/plans/heddle-test-suite-performance-and-review-efficiency.html`

The targeted fix must also audit sibling same-cutover plans and rerun the all-plan validator.
