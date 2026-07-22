---
name: codex-review-partner
description: Use Codex as an independent reviewer or pairing partner. In Pi, required review legs run as visible interactive Codex sessions in adjacent Herdr tabs through the herdr-reviewers skill.
---

# Codex Review Partner

Use Codex as an explicit independent review pass. For required Pi plan and implementation gates, `herdr-reviewers` is the transport and lifecycle authority.

## Pi required-review route

- Create a no-focus adjacent tab in the parent Pi session's Herdr workspace, using the exact current worktree cwd.
- Start Codex through `herdr agent start` with the required model/reasoning pair, `-s read-only`, and `-a never`.
- Required-review pin: `gpt-5.6-terra`, reasoning `high`. A different pair requires an explicit operator instruction for that review and must be recorded.
- Submit the bounded review packet through `herdr agent prompt`.
- Wait for `idle`, `done`, or `blocked`, then inspect the visible and recent-unwrapped transcript.
- The coordinating Pi agent extracts the nonce-delimited result and writes the durable review artifact.
- Preserve failed or blocked tabs for operator inspection.

Do not use the disabled `codex_review` tool, Pi GPT subagents, `interactive_shell`, `codex exec`, `codex review`, or the old `run-review.sh` transport to satisfy a required Pi reviewer leg.

## Modes

Use the existing workflow verdict contract for:

- `implementation-review`;
- `adversarial-implementation-review`;
- `plan-review`;
- `pair` for non-gating exploration.

Review prompts must be concrete and bounded: identify the changed behavior or proposal, files/diff/range, verification evidence, failure families, scope rules, and exact verdict vocabulary. Required reviews must prohibit edits and prohibit execution of tests, builds, linters, typechecks, benchmarks, and verification commands.

Each required prompt must include unique `BEGIN_REVIEW_RESULT <nonce>` and `END_REVIEW_RESULT <nonce>` markers. A settled TUI is not a valid result without matching boundaries, non-empty content, the exact allowed verdict as the final non-empty line inside the boundaries, and an unchanged worktree fingerprint.

## Startup caveat

Codex can display update, hook-trust, MCP, authentication, or other first-run UI after Herdr reports interactive readiness. Read the visible screen before the first prompt. Dismiss only non-blocking informational UI; never auto-trust hooks or grant permissions. Re-prompt only after the reviewer is genuinely idle.

Follow `herdr-reviewers` for topology discovery, model/reasoning arguments, worktree fingerprinting, prompt correlation, artifact capture, diagnosis, reuse, and cleanup.

## Non-recursion

If the review packet says that a Codex review is already active, do not start another nested Codex review.
