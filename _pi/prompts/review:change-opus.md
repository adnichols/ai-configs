---
description: Compatibility alias for the repository-owned reviewer-subagent change review
argument-hint: '<plan-path | plan-slug>'
---

Do not launch Opus, Claude Code, or a Herdr reviewer tab. Run the active Pi `reviewer` subagent (`openai-codex/gpt-5.6-terra`, medium reasoning) with a bounded read-only packet for `$ARGUMENTS`, then record its verdict and findings.
