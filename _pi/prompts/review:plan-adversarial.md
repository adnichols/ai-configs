---
description: Run a bounded adversarial plan review with the repository-owned reviewer subagent
argument-hint: '<plan-path | plan-slug>'
---

Resolve the plan path, then launch the repository-owned read-only `reviewer` Pi subagent (`openai-codex/gpt-5.6-terra`, medium reasoning) with the plan, source input, relevant repo guidance, known non-goals, and an exact readiness verdict contract.

Do not launch Codex or Claude Code sessions, use Herdr, or delegate to an external reviewer. The subagent must not edit files or run tests, builds, linters, typechecks, benchmarks, or verification commands. The driving agent may record the findings and make in-scope plan edits, then run one bounded rereview if needed.

Return the reviewer verdict, cited material findings, and any review-infrastructure failure. Stop when the bounded review contract is complete.
