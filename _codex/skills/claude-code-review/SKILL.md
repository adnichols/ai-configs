---
name: claude-code-review
description: "Route an explicitly requested external Claude review; use native review for ordinary Codex work."
---

Read [the Codex runtime contract](../adn-mode/references/codex-runtime.md) before executing this skill.

# External Claude review compatibility

Use native `autoreview` for ordinary Codex review. If the user explicitly requested Claude as an external reviewer, use the installed `claude-review-partner` skill and validate that client's availability before invoking it. Keep the review bounded and read-only. Missing external capability is an explicit limitation, not permission to report a native review as Claude's verdict.
