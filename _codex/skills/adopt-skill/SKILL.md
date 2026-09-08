---
name: adopt-skill
description: Explicitly adopt a post-pin upstream skill after review. Never silently refresh the pin.
---

## Codex execution

Read [the Codex runtime contract](../adn-mode/references/codex-runtime.md) before executing this skill. It owns tool dispatch, models, delegation, history access, and authorization for this Codex-only copy. Instructions below about other clients describe their workflows, not permission to launch those clients. Preserve the task-specific evidence and output requirements using native Codex tools.



Adoption is explicit. Diff the pinned source against the candidate, record the new pin only after review, and refuse a silent refresh. Fail closed if the license or required source is missing.

Available-update, no-mutation:
1. Detect a newer upstream SHA than the ai-configs repository `_adn/PROVENANCE.md`.
2. Show the diff. Do not write the pin, LICENSE, or skill tree.
3. Apply the new pin only after an explicit operator adopt command.
4. If the operator declines, leave the live tree unchanged.
