---
description: Compatibility pointer for the canonical Claude Code change-review workflow
argument-hint: '<existing-plan-path | plan slug | legacy: <spec> <tasks> | legacy: <directory containing spec.md and tasks.md>'
---

# Compatibility Pointer

This provider-named command is retained only for compatibility. It does not route through a provider-specific Pi subagent.

Run the canonical Claude Code review workflow with the caller-supplied argument unchanged:

```text
/review:change-claude-code $ARGUMENTS
```

The canonical workflow owns the review artifact, Claude lens, inline `[REVIEW:CLAUDE] ... [/REVIEW]` output contract, read-only authority, subprocess lifecycle, completion handling, and stop behavior. Do not translate the artifact, substitute a Pi reviewer, integrate comments, or perform any additional work in this compatibility prompt.
