---
name: deslop
description: Remove unnecessary code and generated clutter from the current diff before commit.
---

ADN_RUNTIME_MARKER:deslop:ecc249f1e306fc64ddf83c7bed16cacf7c2239db

# Deslop

Use the caller's named files or candidate diff, including staged and unstaged changes. Read the surrounding code and callers before editing. Preserve unrelated work.

Remove redundant comments, unused imports and variables, dead branches, duplicated logic, and abstractions added without a current caller. Reuse existing helpers and platform features. Keep validation at trust boundaries, error handling, accessibility, and explanations of non-obvious constraints. Do not replace working code merely to match a style preference.

The driving agent makes the smallest justified edits with native tools. Run affected checks after behavior changes. Report what changed and any unresolved concern; a clean diff is a valid result. This is a managed ADN skill and requires no OMP plugin.
