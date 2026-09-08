---
name: pre-pr-implementation-review
description: Indefinite compatibility alias for autoreview. Use when an existing prompt, operator, or automation invokes the former pre-PR review skill name; preserve all arguments and OPEN_PR_READY handoff semantics by immediately following the canonical autoreview policy.
---

Read [the Codex runtime contract](../adn-mode/references/codex-runtime.md) before executing this skill.

# Compatibility route

Use the parallel `autoreview` skill for the current candidate. Preserve existing review evidence and its bounded cycle budget. Do not create a second review transport or reset the budget through this alias.
