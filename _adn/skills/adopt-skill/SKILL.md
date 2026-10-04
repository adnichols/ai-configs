---
name: adopt-skill
description: Explicitly adopt a post-pin upstream skill after review. Never silently refresh the pin.
---

ADN_RUNTIME_MARKER:adopt-skill:e43c7ee26e0038c6c1fa8380dd34ce86ff94cb2a

Adoption is explicit. Diff the pinned source against the candidate, record the new pin only after review, and refuse a silent refresh. Fail closed if the license or required source is missing.

Available-update, no-mutation:
1. Detect a newer upstream SHA than `PROVENANCE.md`.
2. Show the diff. Do not write the pin, LICENSE, or skill tree.
3. Apply the new pin only after an explicit operator adopt command.
4. If the operator declines, leave the live tree unchanged.
