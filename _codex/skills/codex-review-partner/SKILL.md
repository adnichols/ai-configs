---
name: codex-review-partner
description: "Request bounded independent native Codex review of a design, candidate, or technical claim."
---

Read [the Codex runtime contract](../adn-mode/references/codex-runtime.md) before executing this skill.

# Native review partner

Use a fresh native read-only reviewer for a requested second opinion, following the Codex runtime contract. Give raw scope, candidate files, comparison range, required behavior, verification evidence, and the specific question. The driver synthesizes the result and owns fixes.

For pre-PR review use `autoreview`; for a necessity claim use `adversarial-fix-review`; for one unresolved decision use `oracle-consultation`. A requested external CLI review remains explicit opt-in. Do not silently start another client or label an independent same-family review cross-family.
