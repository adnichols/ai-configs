---
name: claude-code-review
description: Legacy compatibility guidance for external Claude Code reviews. Do not use it as a normal plan or implementation review gate.
---

# Claude Code Review

A separate Claude Code process is not a required plan or implementation reviewer. Use the active harness's native read-only `reviewer` subagent:

- In Claude Code, use the repository-owned `reviewer` subagent pinned to `claude-sonnet-5` at high effort.
- In Pi and OpenCode, use the repository-owned `reviewer` subagent pinned to GPT-5.6 Terra at medium reasoning.

Do not launch Claude Code in Herdr, private tmux, print mode, or any other external transport to meet the standard review gate. The coordinating agent owns the bounded review packet, verification, fixes, and artifact capture. If its configured reviewer cannot run, return `REVIEW_INFRASTRUCTURE_FAILURE` unless the user explicitly waives the gate.

A user may explicitly request a separate Claude Code advisory review. That is a non-gating, read-only exception and does not replace the standard reviewer-subagent result unless the user explicitly changes the review contract.
