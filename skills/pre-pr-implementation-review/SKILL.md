---
name: pre-pr-implementation-review
description: Indefinite compatibility alias for autoreview. Use when an existing prompt, operator, or automation invokes the former pre-PR review skill name; preserve all arguments and OPEN_PR_READY handoff semantics by immediately following the canonical autoreview policy.
---

# Pre-PR Implementation Review Compatibility Alias

This skill is an indefinite compatibility alias. Immediately run the canonical `autoreview` workflow with exactly the same arguments supplied to this invocation:

```text
/skill:autoreview <same arguments, unchanged>
```

The accepted argument shapes remain unchanged: no arguments, a plan path, a base branch or comparison range, or a plan path plus `--base <branch-or-range>`.

Do not recurse into `pre-pr-implementation-review`, and do not redefine or duplicate reviewer routing, severities, scope labels, convergence limits, artifacts, verification rules, or fix policy here. The canonical `autoreview` skill owns the full Codex and applicable Claude Code workflow for Codex and Pi.

Preserve the canonical result exactly. In particular, when called from `run-plan`, a passing gate remains `OPEN_PR_READY` and hands control back to the caller for completeness review, final verification, base freshness, commit, push, PR creation, and local merge-readiness checking.
