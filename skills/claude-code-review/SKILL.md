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

## Transport validity and outcome tolerance

A settled Claude TUI is not by itself a valid review. Require:

- matching nonce boundaries and current-turn provenance under `herdr-reviewers`;
- non-empty review content;
- an allowed workflow verdict as the final non-empty substantive line inside the boundaries;
- an unchanged worktree fingerprint since launch;
- no visible provider, authentication, permission, truncation, or tool-only failure.

Separate provenance failures from workflow-profile mechanics. Unknown provenance, malformed boundaries, unknown presentation prefixes, invalid final-verdict syntax, stale fingerprints, provider/auth/permission failures, empty or tool-only output, contradictory verdict/body content, and incomplete coverage are `REVIEW_INFRASTRUCTURE_FAILURE` or the workflow's incomplete verdict. Only the whitespace and known provider-prefix normalization explicitly defined by `herdr-reviewers` is permitted before mechanical acceptance. After that acceptance, a generic helper's inability to aggregate the workflow-specific verdict is a protocol warning, not a failed Claude review. Preserve the raw accepted result, classify it by substance under the declared workflow profile, avoid a redundant rerun, and record the warning in the durable artifact. Keep genuinely failed tabs open and inspect them through Herdr rather than switching transports.
