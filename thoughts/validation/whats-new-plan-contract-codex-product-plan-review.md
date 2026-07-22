# Codex Plan Readiness Review — Product and Scope Slice

- Reviewer: Codex `gpt-5.6-terra`, high reasoning, read-only Herdr tab `w67:t2`
- Nonce: `aec238ed52b4f66f2e5b0d4101a3907f`
- Plan: `thoughts/plans/whats-new-plan-contract.html`
- Fingerprint: unchanged during review; see `/tmp/whats-new-review-fingerprint-before.txt` and `/tmp/whats-new-review-fingerprint-after-initial.txt`

## Scope checked

Product framing, golden path, scope/non-goals, locked decisions, acceptance criteria, BDDs, phases, legacy compatibility, UI impact, and fresh/stale-worktree handling across ai-configs, Doct, and Heddle.

## Finding

`READINESS_BLOCKER`: the plan requires fresh replacement worktrees but did not establish the user authorization that makes this an explicit exception to ai-configs' normal direct-on-main rule. The plan's phrase “prior isolation authorization” was not supported in its Authority section. The reviewer requested an explicit authority statement and corresponding resume/P1 wording.

All other assigned product/scope checks were complete and aligned.

VERDICT: PLAN_NEEDS_REVISION
