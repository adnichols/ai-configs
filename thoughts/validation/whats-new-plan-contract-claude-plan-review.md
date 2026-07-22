# Claude Code Plan Readiness Review — Compatibility Risk Slice

- Reviewer: Claude Code `claude-sonnet-5`, xhigh, read-only Herdr tab `w67:t4`
- Nonce: `129ce03795f9f0d840c46f1a18f3ce3b`
- Plan: `thoughts/plans/whats-new-plan-contract.html`
- High-risk question: fail-closed current-plan enforcement without historical invalidation, bypass weakening, cross-client divergence, or semantic mismatch.
- Fingerprint: unchanged during review; see `/tmp/whats-new-review-fingerprint-before.txt` and `/tmp/whats-new-review-fingerprint-after-initial.txt`

## Scope checked

Canonical ai-configs semantics, Doct shared config-driven enforcement, Heddle presence/order/duplicate behavior, date-gated compatibility, actionable errors/tests, cross-repository parity, and no-loss delivery constraints.

## Findings

1. `OPTIONAL_CLARITY`: Heddle's new `whats-new` compatibility boundary must use a separate effective-date threshold rather than extending the existing `PLAN_CONTRACT_EFFECTIVE_DATE`/`requiresCurrentPlanContract` pair.
2. `OPTIONAL_CLARITY`: inserting `whats-new` after `summary` shifts `decision-attention` beyond the validator's current `ordinal > 4` near-top rule; P3 should explicitly require a compatible threshold/order adjustment rather than weakening the check.
3. `DISAGREE_REPO_EVIDENCE`: the reviewer reported the named Doct/Heddle stale worktrees absent. Coordinator-side direct filesystem evidence already confirmed both exact paths exist and contain the stale diffs; no plan correction is needed for this item.

No readiness blocker or product question was found. The two clarity items will be integrated to eliminate implementation ambiguity.

VERDICT: PLAN_EXECUTION_READY
