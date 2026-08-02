# Herdr operator-blocked attention — implementation PM review

Plan: `thoughts/plans/herdr-operator-blocked-attention.html`
Review type: implementation outcome (local equivalent of `/dev:pm-review`, which is not exposed as a tool in this runtime)

## Verdict

VERDICT: PASS

The implementation delivers the plan's operator outcome without expanding scope:

- Password waits on Heddle's stable work pane set password/operator attention before the interactive pane run and clear in `finally` for success, failure return, timeout return, and throw.
- Delivery derives attention from the resulting ledger. Pending execution approval sets approval attention; a valid approval clears it even if agent launch later fails; revoke restores it; explicit blockers take precedence; blocker clear derives the next approval state.
- Pi-owned panes retain `herdr:pi` lifecycle authority and honor a complete matching marker above working/idle. Invalid, incomplete, mismatched, unreadable, and missing markers fail open.
- Shell-only panes receive the fixed-source best-effort `pane report-agent` call. The helper never impersonates or releases `herdr:pi`.
- Helper marker I/O remains authoritative and honest; Herdr CLI/socket failure remains best-effort for workflow continuity.
- Install and operator docs cover both installed paths, the marker directory, fixed identity, and preference for Pi UI wrappers when available.

## Acceptance / BDD evidence

| Plan outcome | Evidence |
|---|---|
| Shared set/clear/status helper | `tests/test_herdr_operator_attention.py` |
| Pi-owned idle/working marker latch and priority | `tests/test_herdr_agent_state.mjs` |
| Shell reporting fixed identity and notification idempotence | fake-Herdr argv assertions in helper tests |
| Delivery approval/blocker/plan mutation reconciliation | `test_operator_attention_reconciles_delivery_state` in delivery CLI suite |
| Heddle password gate set-before-run and clear-all-outcomes | `tests/test_heddle_release_operator_attention.mjs` |
| Install destinations executable | `tests/test_herdr_operator_attention_install.sh` |
| Existing Pi and delivery behavior preserved | full existing extension lifecycle and 32-case delivery suites |

## Scope / non-goals

No Herdr binary/core behavior changed. No password-screen scraping, automatic ledger `BLOCKED` transition for approval/password waits, completeness-review attention, or free-text publish prompt expansion was added.

## Plan correction found during implementation

The documented `delivery blocker "..." --mark-blocked` form was not parsed correctly because the positional used `argparse.REMAINDER`; the option became blocker text. Changing that positional to `nargs="*"` is a plan prerequisite for the named acceptance path and is covered by the transition test.

## Residual evidence boundary

The plan's live multi-pane smoke remains optional and was not used as a PR gate. The production CLI boundary and Pi socket behavior are covered through fakes/local socket tests; actual Herdr tab aggregation remains the existing Herdr product behavior and was not modified.
