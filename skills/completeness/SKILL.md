---
name: completeness
description: Run OMP plan-completeness review through @completeness. Use when the operator asks for a completeness check or completeness review, when skill://completeness is requested, after autoreview on an OMP Lite delivery run, or before claiming PR/merge readiness that needs a request-bound completeness artifact.
---

# Completeness

Driver skill for the OMP `@completeness` agent (`xai/grok-4.5:high`).
Do not review the change yourself. Do not invent envelope fields.

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

Do not arm delivery just to run this skill.

## Standalone (no ledger)

Write a packet JSON with `artifact`, `requiredEnvelope` (same seven-line
shape), and `requiredIncompleteVerdict`. Put the packet path in the
`@completeness` prompt. Do not call `delivery completion-review`.

## Launch

```text
task agent=completeness
```

Keep the agent on `xai/grok-4.5:high`. Include `TARGET_CHECKOUT`, the
plan or operator acceptance criteria, and the packet path. The reviewer
is read-only except the named artifact.
