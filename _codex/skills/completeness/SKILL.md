---
name: completeness
description: Run skill://completeness as an on-request plan walk through the active harness's completeness reviewer. Use only when the operator asks for a completeness check or plan walk. Do not run this automatically after autoreview, before a PR, or as merge-readiness.
---

Read [the Codex runtime contract](../adn-mode/references/codex-runtime.md) before executing this skill.

# Walk a plan for completeness

Run only when the user asks for a completeness or plan-coverage walk. It is not an automatic merge or PR gate. Identify the canonical plan, acceptance criteria, changed artifacts, and current verification evidence.

Request a bounded read-only native planner to map each required outcome to implementation and evidence. Name the allowed artifacts, output path if authorized, authority, and stopping condition. Have it return COMPLETE or INCOMPLETE with criterion-level gaps. The driver checks claims and performs any authorized fixes and verification.

Inspect real wiring across required interfaces, registry entries, producer/consumer paths, errors, and contract fixtures. Do not count stubs, unreachable paths, or tests bypassing the implementation as completion. Keep post-merge operations as non-blocking obligations. Preserve scope and identify optional work separately.

Report covered outcomes, missing outcomes, evidence limitations, and the next in-scope action. Do not arm an external delivery ledger, launch another client, or manufacture a completion envelope for a runtime Codex does not own.
