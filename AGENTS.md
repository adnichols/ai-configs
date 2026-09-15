# ai-configs

## Working rules

- Work directly on `main`. Create branches or worktrees only when explicitly requested.
- Preserve unrelated staged, unstaged, and untracked work. Never reset the checkout to simplify a task.
- Follow the requested outcome and existing repository conventions for routine choices. Continue through affected verification and fixes caused by the change. Ask when missing information changes product behavior, scope, authority, or an irreversible action. Report completion with evidence or identify the specific blocker.
- The driving agent implements, tests, fixes, and manages Git. Independent reviewers stay within their read-only task packet. Use native tools for the active runtime; do not route filesystem work through another agent client.
- Required code review uses the active runtime's configured reviewer. Completeness and supervision are opt-in. Read the local planning skill for review budgets and plan execution.
- External actions require authorization for the exact repository and action. In particular, implementing a dependency fix or owning a fork does not authorize upstream PR creation, updates, comments, or reviews. Keep third-party changes local/downstream until that interaction is authorized.
- For index mutations use `git-with-index-lock`, bootstrapped with `scripts/ensure-git-with-index-lock`. Never delete a live index lock or bypass a failed bootstrap.
- Reuse existing code, standard libraries, and maintained dependencies. Use dependency-selection when choosing a dependency. Approval follows consequential scope, dependency, or architecture decisions, not code line count. Do not implement custom cryptography, JSON parsers, async runtimes, or HTTP stacks.

## Verification

Before committing behavior changes, run `cd _adn && bun test` and `cd _adn && bun tests/routing-eval.ts`, plus affected installer or runtime checks. There is no separate ADN lint, typecheck, or build gate. Run required checks once; rerun affected checks after relevant changes or failures. Expand checks when concrete evidence warrants it. Do not describe unrun or failing checks as passing.

## Conditional guidance

Read only the local skill needed by the task:

- Installer, skill provenance, retirement, or source/install synchronization: [.agents/skills/ai-configs-installation/SKILL.md](.agents/skills/ai-configs-installation/SKILL.md).
- Agent definitions, model selection, runtime prompts, or execution boundaries: [.agents/skills/ai-configs-runtime-config/SKILL.md](.agents/skills/ai-configs-runtime-config/SKILL.md).
- Plans, readiness reviews, or phased execution: [.agents/skills/ai-configs-planning/SKILL.md](.agents/skills/ai-configs-planning/SKILL.md).

The shared install inventory is `skills/install-matrix.json`; Codex adaptations are maintained in `_codex/skills` and `_codex/skill-overrides.json`. PSTack principle skills are intentionally retained. Never shorten shared descriptions merely to optimize Codex.
