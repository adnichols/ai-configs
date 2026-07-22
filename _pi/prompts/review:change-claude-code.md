---
description: Run a visible read-only Claude Code review in an adjacent Herdr tab
argument-hint: "<plan path, diff/range, or review scope>"
---

Run a read-only Claude Code review using the `herdr-reviewers` and `claude-code-review` skills.

Requirements:

1. Identify the current Pi pane's Herdr workspace and exact worktree. Parse returned IDs; do not guess.
2. Create a no-focus adjacent tab labelled for this review.
3. Start Claude interactively with `claude-sonnet-5`, `xhigh` effort, `dontAsk` permission mode, and only `Read,Grep,Glob`; do not expose Bash or write-capable tools.
4. Build a bounded prompt for `$ARGUMENTS` that prohibits edits, state-changing shell commands, tests, builds, linters, typechecks, benchmarks, and verification commands.
5. Generate a cryptographically random nonce immediately before submission and include exact `BEGIN_REVIEW_RESULT <nonce>` and `END_REVIEW_RESULT <nonce>` markers plus the workflow's required verdict vocabulary.
6. Inspect the reviewer before prompting, submit through `herdr agent prompt --wait`, then read both visible and recent-unwrapped output.
7. Validate the matching boundaries, exact verdict, non-empty review, and unchanged worktree fingerprint. The coordinating Pi agent writes the artifact; Claude does not.
8. On startup modal, auth/usage/permission block, timeout, prompt stall, unknown state, missing boundaries, invalid verdict, or stale fingerprint, inspect with `herdr agent get`, `herdr agent read`, and `herdr agent explain --verbose`. Keep the tab open for operator inspection.

Do not use `claude_review`, the old private-tmux Python launcher, `interactive_shell`, Claude print mode, or a Pi subagent. The legacy Pi review extension is disabled.
