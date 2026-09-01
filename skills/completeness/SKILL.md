---
name: completeness
description: Run skill://completeness as an on-request plan walk through the active harness's completeness reviewer. Use only when the operator asks for a completeness check or plan walk. Do not run this automatically after autoreview, before a PR, or as merge-readiness.
---

# Completeness

Driver skill for the active harness's independent plan-completeness reviewer.
Do not review the change yourself. Do not invent envelope fields. When the
operator asks for completeness, run it. Do not refuse. Do not ask them to
arm delivery or recite a trigger phrase.

This is not a run-plan or delivery gate. Autoreview `OPEN_PR_READY` is
permission to continue to verification and PR. Do not block PR creation or
merge readiness on a missing completeness artifact. When the operator asks
for a plan walk, run this skill and follow its packet contract.

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

If no ledger exists and this is after implementation, a request for
completeness, PM review, or pre-PR is late-attach authorization. Run
`delivery arm --from existing-implementation` silently and use the packet
path above. Do not ask them to recite a phrase. Otherwise run standalone.
Delivery ledgers support only the `omp` and `pi` runtimes. A Devin session
always uses the standalone form below.

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
