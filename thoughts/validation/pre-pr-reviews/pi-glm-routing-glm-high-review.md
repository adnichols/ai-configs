# Pi GLM-5.2 Routing GLM High Review

Plan: `thoughts/plans/pi-glm-5-2-routing-cost-plan.html`
PR: https://github.com/adnichols/ai-configs/pull/33
Date: 2026-07-09
Reviewer: `glm5.2-high`

## Risk classification

The user corrected the earlier low-risk classification: this change is not low risk because it affects future coding workflows, model routing, review-routing expectations, and E2E delegation behavior. GLM high review is therefore applicable and was run as an additional scoped review leg.

## Review focus

1. Whether prompt/agent/install changes could accidentally change defaults, model availability, routing, or future coding behavior in unsafe or expensive ways.
2. Whether required high-risk review gates are preserved rather than weakened or substituted.
3. Whether GLM roles are bounded to orchestration/UI design and not accidentally made broad implementation defaults.
4. Whether Playwright/E2E prompt changes improve future coding workflows without deadlocks, under-delegation, or misleading instructions.
5. Whether installer/verifier changes are robust against existing settings shapes and stale model entries.

## Substantive checks

- Defaults/model availability/routing safety: clean. `install.sh` and `scripts/verify-pi-install.sh` preserve `openai-codex/gpt-5.5` defaults and add `opencode/glm-5.2` to `enabledModels` additively/idempotently.
- High-risk review gates: clean. The run-plan skill and review agents were not modified, and new GLM briefs explicitly say they do not replace required review gates.
- GLM role bounding: clean. `orchestrator-glm` and `ui-design-glm` are subagents on `opencode/glm-5.2`; `developer-mid` and `developer-high` remain pinned to `openai-codex/gpt-5.5`.
- Playwright/E2E coherence: one minor prompt-label issue found; the split supervision/fix model and failure packets are otherwise coherent.
- Installer/verifier robustness: clean. Non-list `enabledModels` fails explicitly, non-string entries pass through, stale Spark entries are removed, and the GLM append is conditional.

## Findings

| ID | Severity | Classification | Finding | Resolution |
| --- | --- | --- | --- | --- |
| F1 | P3 | IN_PLAN | The pre-PR gate artifact incorrectly recorded this as a low-risk GLM skip. | Updated `pi-glm-routing-prepr-gate.md` to reflect the corrected risk classification and this GLM high review result. |
| F2 | P3 | IN_PLAN | Playwright prompt H1 labels still said `Live Fix Mode B` despite the new split supervision/fix mode. | Updated both Playwright prompt H1 labels to `Split Supervision/Fix Mode`. |

No P1/P2 issues found.

## Verdict

VERDICT: PASS_SCOPED after applying the two P3 in-scope documentation/prompt-label fixes.
