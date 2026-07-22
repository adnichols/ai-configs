---
name: claude-code-review
description: Run required read-only Claude Code plan and implementation reviews as visible interactive agents in adjacent Herdr tabs. The legacy Pi claude_review extension and private-tmux launcher route are disabled.
---

# Claude Code Review

Use `herdr-reviewers` as the transport and lifecycle authority for every required Claude Code review.

## Pi route

- Create a no-focus adjacent tab in the parent Pi session's Herdr workspace, using the exact current worktree cwd.
- Start Claude through `herdr agent start` with the full model ID `claude-sonnet-5`, `xhigh` effort, `dontAsk` permission mode, and only the built-in `Read,Grep,Glob` tools. Do not expose Bash or write-capable tools. Do not use the `sonnet` alias, Opus, Fable, or a fallback model.
- Submit the bounded review packet through `herdr agent prompt`.
- Wait for `idle`, `done`, or `blocked`, then inspect the visible and recent-unwrapped transcript.
- The coordinating Pi agent extracts the nonce-delimited result and writes the durable review artifact.
- Preserve failed or blocked tabs for operator inspection.

Do not use the disabled `claude_review` tool, the old Python/private-tmux launcher, direct Claude print mode, `interactive_shell`, or a Pi subagent to satisfy the required reviewer leg.

## Review packet

The prompt must be read-only and scope-bounded. It must:

- prohibit edits and state-changing shell commands;
- prohibit tests, builds, linters, typechecks, benchmarks, and verification commands;
- name the plan or diff/range and relevant files/surfaces;
- include caller-supplied verification evidence;
- specify the workflow's severity, scope, output, and verdict contract;
- include cryptographically random unique `BEGIN_REVIEW_RESULT <nonce>` and `END_REVIEW_RESULT <nonce>` markers generated immediately before submission.

Follow `herdr-reviewers` for startup checks, worktree fingerprinting, prompt correlation, artifact capture, failure diagnosis, reuse, and cleanup.

## Transport validity

A settled Claude TUI is not by itself a valid review. Require:

- matching nonce boundaries;
- non-empty review content;
- the exact allowed workflow verdict as the final non-empty line inside the boundaries;
- an unchanged worktree fingerprint since launch;
- no visible provider, authentication, permission, truncation, or tool-only failure.

Anything else is `REVIEW_INFRASTRUCTURE_FAILURE`. Keep the tab open and inspect it through Herdr rather than switching transports.
