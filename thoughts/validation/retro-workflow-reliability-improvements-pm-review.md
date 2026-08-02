# PM Review — Retro Workflow Reliability Improvements

- **Mode:** Implementation-stage product review
- **Plan:** `thoughts/plans/retro-workflow-reliability-improvements.html`
- **Reviewed:** 2026-08-02
- **Reviewer:** coordinating PM/product-intent pass
- **Verdict:** READY

## Intended operator outcome

The implementation delivers the requested workflow outcome through existing commands rather than parallel machinery. Review transport is probed before model use; expensive verification receives partition, failure-inventory, scratch-ownership, and final-candidate rules; Pi review-stack install/rollback/verification share one manifest and structured receipts; delivery writes use revision-checked locking with a narrow implementation-launch lease; transcript acceptance now explains exact mismatch states; and planning evidence is conditional rather than an eight-heading duplicate questionnaire.

## Acceptance and stage-fit review

- **P1:** The checked-in patch plus no-model transport probe resolves effective planner/reviewer isolation, model, reasoning, and checkout handling. Run-plan, test, and PR guidance now names bounded partitions, merge-base proof, owned scratch, and committed-candidate checks.
- **P2:** `scripts/pi-review-stack-managed-surfaces.json` is consumed by bounded/full install reconciliation, the transaction wrapper, verifier, and tests. Local, transactional, and remote commands emit the locked private JSON receipt. Foreign symlink leaves and ancestors fail before managed mutation, while an already-correct managed link remains reinstallable.
- **P3:** Every named delivery writer reaches the locked revision-aware JSON writer. `--force` uses an explicit locked replace, unrelated evidence can proceed during a launch lease, and callbacks reload and revalidate launch identity. Completeness parsing covers exact, wrapped, duplicate, malformed, non-complete, missing-ID, and likely-truncated states.
- **P4:** Canonical workflow changes are reflected in the named Pi, Codex, Claude, and Hermes surfaces. The exact six-search after-inventory contains all enumerated paths and writer families. Shared installer fixtures now explicitly stage the review transport rather than depending on inherited host state.
- **P5:** Documentation and changelog describe the manifest, probe, and receipt contracts without PR placeholders. Focused production-parser, rollback, remote, delivery, and review-orchestration suites are green. The repository-wide Python suite has one inherited real-host pi-vcc reload failure, reproduced before this change and unrelated to the touched workflow contracts.

## Product-principles review

The normal entry points remain the golden path. Safe defaults reject stale revisions, foreign symlink boundaries, ambiguous reviewer provenance, unowned scratch deletion, and malformed completeness responses. Errors identify the failing path, revision, request, host, or retry action. Advisory delivery checks remain advisory, and operator-approved exceptions remain operator-owned.

## Review disposition

Three bounded implementation-review rounds found and drove fixes for full-mode preflight ordering, force-replace semantics, launch-lease scope, callback behavior, and symlink boundary coverage. The final reviewer concern asked a successful full-install preflight to make every later non-transactional full-install failure roll back all earlier full-install mutations. That is not AC5 or AC6: AC5 requires one manifest and caller-owned sibling preservation; exact rollback is provided by `scripts/install-pi-transactionally.sh`. The full route now proves the required narrower contract: manifest validation and a real staged transport probe happen before manifest-owned mutation, and a preflight failure leaves managed destinations untouched. Converting the entire legacy full installer into a transaction would be a new installer architecture explicitly outside this plan.

## Final status

**READY** — the implementation matches the reviewed product outcome. No unresolved in-scope product decision or blocking implementation-review finding remains. Local/remote post-merge install execution and Heddle schema-v2 template reconciliation remain truthful non-blocking follow-ups.
