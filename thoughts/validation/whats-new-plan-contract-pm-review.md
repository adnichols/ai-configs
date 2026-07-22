# PM Product-Intent Readiness Review — Early “What’s new” Contract

- Plan: `thoughts/plans/whats-new-plan-contract.html`
- Doct: `https://doct.nodaste.com/d/workspace_759bfae3-44f1-4ce5-9bff-9077d9933a21/docs/6fd4cbb2-7dcd-4459-b58f-b142a6852968`
- Review date: 2026-07-22
- Reviewer: coordinating Pi PM-equivalent review using `product-principles`

## Product outcome

The plan defines a coherent golden path: non-trivial reviewer-facing plans announce the concrete audience-visible product change early by default; repository templates and authoring guidance prevent omission; review packets catch weak/restated content; Doct and Heddle validators enforce repository-specific presence/order; historical compatibility and existing escape hatches remain intact.

## Readiness checks

| Check | Result | Evidence |
|---|---|---|
| Standalone product-owner context | Pass | Near-top context explains the problem, why now, key conclusion, and all five impact dimensions. |
| Concrete “What’s new” outcome | Pass | Headline, promise, before/after, reviewer-visible result, and preserved guarantees are explicit. |
| Golden path and defaults | Pass | Templates/prompts make compliance the default; no new flags or manual setup are required. |
| Fail-closed and compatibility boundaries | Pass | Current plans fail review/validation; Doct preserves reason-bearing bypass; Heddle preserves date-gated historical handling. |
| Scope discipline | Pass | Non-goals exclude retired agents, Herdr transport changes, generalized migration infrastructure, unrelated template cleanup, and runtime changes. |
| Acceptance and behavioral coverage | Pass | AC1–AC11 and BDD1–BDD10 cover authoring, review semantics, structural validation, legacy behavior, sync, and safe cleanup. |
| Executable phases | Pass | P1–P4 each include end state, tests first, expected files, work, decision dependencies, and concrete verification. |
| Current repository evidence | Pass after refresh | Readiness review refreshed ai-configs to `88434a96`, Doct to `3a85b75a`, and Heddle to `d0f33d1f`; expected files remain present. |
| UI impact | Pass | Correctly classified as text-only; current/target reviewer experience is explicitly described. |
| Product decisions | Pass | No unresolved product-shaping decision remains. |

## PM corrections made

1. Refreshed the three repository authority SHAs to current remote tips.
2. Recorded that intervening ai-configs/Heddle changes do not alter the planned architecture or target files.
3. Added Heddle’s required committed-head `npm run pre-pr:check -- --base develop` handoff gate to P4.

## Verdict

The plan represents the smallest complete cross-repository slice that delivers the stated planning-product behavior without reviving stale architecture or widening into migration/template cleanup.

PM_VERDICT: EXECUTION_READY
