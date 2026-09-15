---
name: planning-workflow
description: "Structure executable plans with scope, acceptance criteria, verification, and resumable phases."
---

Read [the Codex runtime contract](../adn-mode/references/codex-runtime.md) once per task.

# Planning workflow

Create only the requested plan artifact. Research and planning do not authorize implementation, installations, publication, Git operations, or a delivery ledger. Use the existing plan or repository convention for format and path; choose routine names without asking. Ask only when missing information changes scope, behavior, authority, or a required artifact contract.

Validate relevant paths, commands, current behavior, and dependencies. Preserve acceptance criteria and non-goals. Protect behavior affected by the proposed change; report unrelated discoveries separately. An executable plan must not hide unresolved product decisions in later phases.

Read the relevant references:

- Creating or materially updating an execution plan: [plan structure](references/plan-structure.md).
- Assessing readiness or preparing an execution handoff: [readiness](references/readiness.md).
- Explicit tests-first work: [TDD and BDD](references/tests-first.md). Ordinary planning does not require TDD.

Use product-principles when product or operator behavior changes, and integration-integrity for exact contracts or distributed behavior. Do not load unrelated domain skills. Use doct-document-ops only when Doct publication or interaction is requested; a local plan stays local.

Keep post-merge deployment and observation as non-blocking handoff obligations, never pre-PR gates. Continue through the requested planning outcome and required reviews. Complete only with actual evidence; otherwise name the specific unresolved decision or missing evidence.
