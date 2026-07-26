---
name: codex-review-partner
description: Legacy compatibility guidance for Codex pairing. Do not use it as a normal plan or implementation review gate.
---

# Codex Review Partner

Codex is not a required plan or implementation reviewer in the standard workflow. Use the current harness's read-only `reviewer` subagent instead:

- Pi and OpenCode use GPT-5.6 Terra at medium reasoning.
- Claude Code uses Sonnet 5 at high effort.

Do not start a Codex review process, delegate a review to Herdr, or substitute Codex when the configured reviewer is unavailable. Report `REVIEW_INFRASTRUCTURE_FAILURE` or request a waiver under the governing workflow.

An operator may explicitly request a separate Codex pairing or advisory pass. Treat that pass as non-gating unless the operator explicitly changes the review contract, and keep it read-only and bounded to the supplied artifact or diff.
