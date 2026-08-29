---
name: completeness
description: Run plan-completeness review through the active harness's completeness reviewer. Use when the operator asks for a completeness check or completeness review, after autoreview on run-plan, or before opening a PR or claiming merge readiness that needs a request-bound completeness artifact.
---

# Completeness

Driver skill for the active harness's independent plan-completeness reviewer.
Do not review the change yourself. Do not invent envelope fields.

`run-plan` must run this gate after autoreview and before PR creation, unless the operator explicitly instructs opening the PR regardless of review status. Do not open a PR on `OPEN_PR_READY` alone. An explicit override opens the PR immediately; disclose the missing or non-COMPLETE completeness state and do not claim merge readiness.

## Stakes-scaled fast path

For small, reversible, low-stakes work, run one completeness review pass. On `INCOMPLETE`, fix the in-plan findings and request exactly one rereview. If `COMPLETE` is not reached after the rereview, stop with a convergence blocker or an explicit operator waiver; do not loop beyond three total passes. Record `fast-path: true` and the reason.

## Delivery run

When `.delivery/ledger.json` exists and `runtime` is `omp`:

```bash
delivery stage COMPLETENESS_REVIEW
delivery completion-review --prepare --reviewer-identity omp-completeness-grok-4.5-high
```

Send the emitted JSON packet unchanged to `@completeness`. The reviewer
writes only `packet.artifact`. The first seven LF-terminated ASCII lines
must be exactly `packet.requiredEnvelope` (`VERDICT` may be `COMPLETE` or
`INCOMPLETE`). Then run `packet.acceptCommand`.

On `INCOMPLETE`, fix in-plan findings and prepare a fresh request. Do not
reuse a stale, replayed, or incomplete artifact.

Do not arm delivery just to run this skill. Delivery ledgers support only
the `omp` and `pi` runtimes; a Devin session always uses the standalone form
below.

## Standalone (no ledger)

Write a packet JSON with `artifact`, `requiredEnvelope` (same seven-line
shape), and `requiredIncompleteVerdict`. Put the packet path in the reviewer
prompt. Do not call `delivery completion-review`.

Launch the reviewer with the active harness's native subagent mechanism:

- **OMP:** `task agent=completeness` on `xai/grok-4.5:high`.
- **Devin:** `run_subagent` with the `completeness` profile
  (`~/.config/devin/agents/completeness.md`); it pins its own model. Run it
  in the foreground, or in the background and join via `read_subagent` with
  `block: true`.

Include `TARGET_CHECKOUT`, the plan or operator acceptance criteria, and the
packet path. The reviewer is read-only except the named artifact.
