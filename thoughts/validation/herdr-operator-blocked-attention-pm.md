# PM plan review — herdr-operator-blocked-attention

Mode: plan (pre-execution readiness)
Date: 2026-08-02
Plan: thoughts/plans/herdr-operator-blocked-attention.html

## Verdict

**Ready after PM integration** — plan reshaped during this pass; no product decision blocked.

## Intended outcome

Operators notice when a workflow needs them (password, stage approval, explicit blocker) via Herdr `blocked` attention, without requiring the coding agent to self-report blocked.

## Changes made to the plan

1. Clarified delivery `EXECUTION_READY` is the between-stage approval pause even when the agent only asks in chat and settles idle; latch outranks working so the tab stays attention-grabbing.
2. Excluded completeness-review and other agent-owned waits from operator-attention set sites (AC-9).
3. Heddle release: keep gate as the shell password minimum; document that host Pi UI prompts already use existing blocked wrappers; leave free-text publish asks non-minimum (prefer Pi UI).
4. Status pill moved to execution-readiness review in progress.

## Product principles check

| Principle | Assessment |
|---|---|
| Golden path | Password gate + EXECUTION_READY + blocker cover the named pain without requiring operators to run a separate status command |
| Safe defaults | Best-effort Herdr; skip env; no ledger stage flip for normal waits |
| Honest status | blocked = human needed now; not quality advisory gaps |
| Early-stage scope | Dual-path helper is the smallest complete mechanism; no Herdr binary change, no screen scraping |

## Residual non-blocking notes

- Publish-agent free-text operator questions may still look idle unless agents use Pi UI; documented as prefer-UI, not expanded into scraping.
- Live multi-pane smoke remains manual verification after implementation.

## Stage fit

Appropriate for ai-configs operator tooling; single PR slice P1–P4 is independently useful.
