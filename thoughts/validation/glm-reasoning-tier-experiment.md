# GLM Reasoning-Tier Experiment

Date: 2026-07-05
Plan: `/Users/anichols/thoughts/plans/glm-cost-optimization-plan.html`
Scope: Compare `glm5.2-high` and `glm5.2-xhigh` on the same compact review packet before changing workflow defaults.

## Fixed Review Packet

- Target files: `_pi/agents/explore.md`, `_pi/agents/glm5.2-high.md`, `_pi/agents/glm5.2-xhigh.md`, `skills/pre-pr-implementation-review/SKILL.md`, `skills/run-plan/SKILL.md`, `skills/reviewed-html-plan/SKILL.md`, `skills/plan-reviewer-execution-ready/SKILL.md`, `AGENTS.md`.
- Risk checked: whether the GLM cost optimization preserves high-risk review coverage while reducing unnecessary GLM xhigh usage.
- Outcome limit: `CLEAN_FOR_EXPERIMENT`, `FINDINGS_TO_RESOLVE`, or `REVIEW_INCOMPLETE`.

## Measurements

| Profile | Reasoning | Result | Reported quality | Input tokens | Output tokens | Cache-read tokens | Total tokens | Wall time | Estimated cost |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `glm5.2-high` | high | `FINDINGS_TO_RESOLVE` | Found no high-risk coverage blocker. Identified one completion-contract issue: skipped-GLM pre-PR runs still required a GLM clean verdict in the final summary. Fixed in `skills/pre-pr-implementation-review/SKILL.md`. | 221,308 | 6,187 | 509,952 | 737,447 | 274.7s | $1.55 |
| `glm5.2-xhigh` | xhigh | `CLEAN_FOR_PR` | Found no blocking safety issue. Confirmed high-risk coverage, low-risk skips, alias migration safety, and Pi profile usability. | 1,159,901 | 18,023 | 1,078,784 | 2,256,708 | 734.0s | $6.88 |

Both reviewers received the same packet. The high-reasoning reviewer found one actionable workflow-contract gap; xhigh did not identify additional P1/P2 blockers for this bounded guidance/configuration change. The xhigh run used about 3.06x total tokens, 2.12x cache-read tokens, 2.67x wall time, and 4.45x estimated cost for no additional blocking findings.

## Finding-Quality Comparison

- Both profiles agreed the scope is safe as a bounded configuration/guidance change.
- Both profiles agreed high-risk coverage remains protected by explicit high-risk triggers, `glm5.2-xhigh` for exceptional-risk review, and `quality-reviewer-glm` as the compatibility alias.
- Both profiles identified the same xhigh-required classes by substance: final pre-PR high-risk review, security boundary changes, irreversible data-loss risk, difficult concurrency/locking correctness, migrations, and release-blocking ambiguity.
- High reasoning was sufficient for this plan's normal high-risk review packet because it found the only actionable completion-contract gap and xhigh found no additional blocker.

## Decision Rubric

Use `glm5.2-high` for normal high-risk bounded reviews after this experiment, when the packet has named files, a specific P1/P2 risk question, relevant diff excerpts, and verification evidence.

Use `glm5.2-xhigh` for:

1. Final pre-PR review gates for high-risk scopes.
2. Security boundary or auth/authz changes.
3. Irreversible data-loss or destructive-write risk.
4. Difficult concurrency, locking, race, or deadlock correctness.
5. Schema/data migrations and persistence-layer changes with rollback risk.
6. Release-blocking ambiguity, deploy/rollback risk, or CI gate semantics.
7. Any case where `glm5.2-high` returns `REVIEW_INCOMPLETE`, asks for xhigh escalation, or identifies a material P1/P2 ambiguity.

## Routing Decision

Proceed with installing the split profiles and keep `quality-reviewer-glm` as the compatibility alias. Workflow guidance may route normal high-risk bounded review to `glm5.2-high`, while retaining `glm5.2-xhigh` for the final/exceptional-risk classes above.
