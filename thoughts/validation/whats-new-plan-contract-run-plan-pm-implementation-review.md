# Run-plan implementation-stage PM review

**Plan:** `thoughts/plans/whats-new-plan-contract.html`

**Issue:** NOD-1415

**Verdict:** `PASS_SCOPED — ready for delivery steps`

## Product-intent audit

- **AC1–AC4 / BDD1–BDD4, BDD9:** ai-configs now defines one canonical early standalone section contract and delegates active Pi, Codex, Claude, bootstrap, product-review, and managed Hermes surfaces to it. The readiness packet explicitly blocks missing, late, vague, or duplicative content. Retired Pi plan/reviewer agents and generic Herdr transport were not restored or changed.
- **AC5–AC6 / BDD5–BDD6:** Doct’s default Markdoc template and configured section order now place `whats-new` after `status` and before `goal`; existing config-driven CLI/API validation covers missing/order failures while legacy HTML and reason-bearing bypass behavior remain intact. No versioned-template subsystem was added.
- **AC7–AC8 / BDD7–BDD8:** Heddle generation emits `summary → whats-new`; current-contract validation rejects missing, duplicate, and misplaced sections; the new independent effective-date boundary preserves historical warning/backfill behavior. Current plans at the boundary were backfilled rather than left invalid.
- **AC9:** focused happy-path, missing, duplicate/order, weak/restatement, generation, route parity, install/sync, and historical-compatibility tests pass. The ai-configs aggregate shell suite still reports eight failures that reproduce against current `origin/main`; focused contract and Hermes verification pass.
- **AC10:** bounded Codex and applicable Claude reviews reached clean scoped consensus after one targeted fix/rereview cycle. The coverage ledger records reviewer surface coverage and dispositions.
- **AC11 / BDD10:** implementation is in three fresh branches/worktrees rebased onto current remote tips. Old worktrees have not been deleted; cleanup remains gated on the final no-loss audit and may be explicitly retained if unrelated state prevents safe removal.

## Scope and user-flow check

The delivered behavior matches the approved product promise: plan readers encounter a concise audience-visible before/after explanation before implementation detail; authoring guidance prevents omission; review catches semantic weakness; Doct and Heddle enforce their repository-specific structural contracts without changing trivial-work or legacy escape hatches.

No new settings, public API, migration subsystem, retired agent architecture, or generic reviewer transport was introduced.

## Process note

The implementation-review legs were completed before this PM artifact was materialized. This is a sequencing deviation from the preferred run-plan order, not a product or verification gap; no implementation code changed after reviewer consensus. The only later edit was the decisions-log entry requested by review.
