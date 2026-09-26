---
name: ai-configs-planning
description: Apply ai-configs plan, review, and execution conventions when working on a plan in this repository.
---

# ai-configs planning

Use the shared planning-workflow skill for methodology. Local plans remain local unless the user requests Doct publication. Active browser-reviewed plans are semantic HTML at `thoughts/plans/<slug>.html`, with no Markdown companion. Use doct-document-ops for registration, title consistency, comment listeners, and lifecycle state.

### Execution

- In this repo, operate directly on `main`; do not create feature branches or worktrees unless the user explicitly asks for them.
- This is an intentional repo-specific exception to the usual branch-first guidance used in many other repos. Do not "correct" this back to a branch workflow unless the user explicitly asks to change the protocol.
- Run the repository’s primary test command(s) before committing any change that touches behavior, plus any additional checks (lint, build, etc.) defined in the project’s AGENTS.md or TESTING.md.
- For BDD/TDD phase plans, review the implemented slice for concrete in-scope failures: unmet acceptance criteria, incomplete wiring, regressions, credible current-path security/data-loss/correctness risks, or misleading verification. You are not required to expand the change for speculative future scale, ideal architecture, unrelated pre-existing defects, optional polish, or unsupported hypothetical paths; capture those as findings.
- Default to one implementation review plus one targeted rereview after fixes. A third review is allowed only when the prior fix introduced or exposed a new concrete blocker. After three total rounds, require exactly one bounded, read-only, advisory external consultation through the harness's configured consultation surface before reporting review non-convergence; in Pi this is the repository-owned `oracle` subagent. This applies to a fixed candidate branch/diff with or without a PR. Only when that consultation authorizes it, allow one scope-bound `REVIEW_ESCAPE` adversarial reviewer-pair pass plus the existing single pass-after-fixes allowance. Do not consult repeatedly or review until clean.
- Complete the promised PR-reviewable slice before claiming success: no required stubs, TODO behavior, dead-end surfaces, missing producer/consumer wiring, fake success, or tests that avoid the real implementation. If the promised outcome cannot be completed safely, resize it before implementation to a smaller independently useful complete slice.
- Deployment, promotion, merge-dependent smoke checks, production observation, and rollback-window closure are post-merge delivery/operations work. They must never block PR creation or be used as pre-PR phase/progress/acceptance/verification gates; preserve them as explicit non-blocking handoff obligations with truthful evidence status.
- Validate planned verification commands against real repo/package/target names before execution; correct obvious drift in the plan immediately instead of carrying stale commands forward.
- When a phase spans multiple required surfaces (HTTP/CLI/MCP/UI/etc.), make parity expectations explicit and treat missing registry/dispatcher/wrapper wiring as implementation work, not optional cleanup.
- When locked schemas, payloads, response shapes, or evidence sources change, update stale fixtures/tests in the touched scope during the same run rather than leaving contract drift for a later phase.
- When working from task lists or simplification plans:
  - After completing a listed sub-task or step, immediately change its checkbox from `[ ]` to `[x]` in the same file.
  - Verify that the change is reflected in the file (do not batch updates at the end).
  - Keep any “Relevant Files” or similar sections accurate as files are created or modified.
  - Exception: delivery-managed HTML implementation plans keep phase progress in the delivery/coverage ledger during implementation, then synchronize truthful source-plan and Doct checkboxes once immediately before PR. This preserves the reviewed-plan hash; material plan changes still require a fresh readiness cycle.
- Prefer repository-specific guidance for tools, security, and performance; this central file is only a baseline.


For Linear-backed PRs, start the title with the issue key and include the issue title. Use ltui for Linear operations. `run-plan` owns an authorized implementation-through-PR lifecycle; an execution-only request ends at local verification without publication. Legacy OMP/Pi delivery is not a Codex prerequisite.
