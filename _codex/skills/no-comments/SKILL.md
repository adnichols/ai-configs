---
name: no-comments
description: "Review comments for misleading or redundant explanations while preserving real constraints. Use for a scoped comment cleanup."
---

Read [the Codex runtime contract](../adn-mode/references/codex-runtime.md) before executing this skill.

# Review comments

Review the caller's files or current candidate diff for misleading, redundant, stale, or unnecessary comments. Preserve non-obvious constraints, legal text, public API documentation, compatibility rationale, and explanations the code cannot express.

For a substantial sweep, request a bounded read-only reviewer. Give exact paths and ask for proposed removals or corrections with evidence. There is no special Comment Sicko native agent. The driver checks findings and performs edits.

Read surrounding code before removing a warning or suppression. An unclear constraint is not evidence that it is safe to delete. If a constraint belongs in types, tests, or validation, implement that only within the authorized scope; keep an accurate comment when the encoding is deferred. Do not widen a comment cleanup into an architectural rewrite.

Report meaningful corrections, kept constraints, any required verification, and unresolved uncertainty. Do not make a comment sweep a mandatory gate for every unrelated review.
