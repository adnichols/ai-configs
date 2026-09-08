---
name: delivery-run
description: "Route an authorized Codex implementation lifecycle or inspect an existing external delivery ledger without changing its owner."
---

Read [the Codex runtime contract](../adn-mode/references/codex-runtime.md) before executing this skill.

# Delivery from Codex

Use native `run-plan` for an authorized implementation-through-PR task. It owns implementation, verification, bounded review, publication, and the final readiness snapshot in this driving session.

The repository's delivery CLI currently supports only OMP and Pi. This Codex skill does not implement another ledger runtime. For a request to inspect an existing delivery run, read its ledger and status without changing runtime ownership. Report its owner, stage, evidence, and blockers. Do not emit fake implementation-profile, planner, or completion evidence.

If the user explicitly requests launching or administering an OMP/Pi delivery run, that is an external-runtime operation. Read the named product's current CLI instructions and honor the exact requested runtime and repository. Do not infer this authorization from an ordinary Codex implementation request. If native Codex delivery-ledger support itself is requested, explain the unsupported feature and treat adding it as a separate implementation scope.
