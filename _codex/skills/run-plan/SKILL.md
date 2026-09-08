---
name: run-plan
description: Execute an existing implementation plan persistently through code changes, bounded scoped quality reviews, active-harness pre-PR review, verification, commit, push, PR creation, and local merge-readiness consensus without expanding beyond the plan's stated scope.
---

Read [the Codex runtime contract](../adn-mode/references/codex-runtime.md) before executing this skill.

# Execute a plan in Codex

Use this skill when the user requests execution of an existing plan through verification and PR creation. Read the plan and repository instructions first. Preserve locked scope, acceptance criteria, exclusions, and required evidence. `adn-mode` supplies engineering discipline; this skill owns lifecycle and review budget.

Do not create or convert an OMP/Pi delivery ledger. An existing ledger is evidence of another runtime's ownership; inspect it and avoid concurrent implementation. Continue the requested Codex work only when ownership is clear. Use task notes or the client's task list. Create a Codex goal only when explicitly requested.

1. Inspect the current checkout, dirty files, plan progress, and authoritative issue or Doct state. Validate commands against actual packages and targets. Keep unrelated work untouched and follow the repository's branch policy.
2. Implement each unfinished in-scope phase directly. Make every required producer, consumer, registry, dispatcher, and interface work together. Keep planned verification consistent with changed contracts and fixtures. Do not leave required stubs or fake success. Update progress when each unit is complete. Preserve any explicitly locked reviewed-plan hash procedure.
3. Run the phase's meaningful verification. Correct obvious command drift. Keep deployment, promotion, production observation, and rollback windows as explicit post-merge obligations, not pre-PR blockers.
4. Compare the finished behavior with the plan as a product-outcome review. Run `autoreview` for independent material review, counting earlier equivalent review of the unchanged candidate once. Completeness is a separate on-request plan walk. The driver runs tests and fixes findings.
5. After authorized in-scope fixes, rerun affected checks and use at most one targeted rereview. A third round requires a new concrete blocker introduced or exposed by the fix. Before declaring non-convergence, consult `oracle-consultation` once for the fixed artifact and follow the repository's escape policy. Never review indefinitely or expand scope to please a reviewer.
6. Check base freshness. Integrate safely within repository policy, preserving user work. Use `safe-git-index` for index changes and `cmd-create-pr` to commit/publish only the scoped candidate to its authorized repository. Follow an explicit instruction to publish despite incomplete review or verification, but disclose the actual evidence and do not call it clean.
7. Inspect the published PR's current checks, mergeability, and actionable feedback. Fix authorized in-scope findings and reverify changed behavior. Take a fresh final snapshot. Do not wait for absent bot comments, a hosted thumbs-up, or human approval once local review and applicable required checks establish the requested readiness. Do not merge unless requested.

Keep a compact evidence record with the plan, comparison range, candidate identity, commands/results, review rounds and dispositions, PR URL, base state, and unresolved obligations. Finish only when the requested slice and local readiness are established, or report a concrete blocker with completed work preserved. If a required check is still running, use a bounded wait and retain ownership of the task.
