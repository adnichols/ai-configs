---
name: claude-review-partner
description: Use Codex itself as a second-pass reviewer, plan reviewer, or pairing partner during coding work. Trigger when implementing, refactoring, debugging, writing tests, reviewing a plan/spec, or when you want an independent Codex CLI pass before finalizing technical work.
allowed-tools: "Bash(Codex:*), Read, Write"
argument-hint: "[implementation-review|plan-review|pair] <input-file> [repo-path]"
---

# Codex Review Partner

Use Codex as an explicit second pass before you finalize technical work.

## Core rule

For coding work, plan work, refactors, debugging, and test changes, run a Codex review pass before your final answer.

Use one of three modes:
- `implementation-review` for code changes, bug fixes, refactors, and tests
- `plan-review` for plans, specs, and implementation approaches
- `pair` for open-ended debugging, exploration, and design discussion

## Timeout rule

When launching `Codex` from another tool runner, never use a short 120s timeout for review work.

Minimum:
- use at least 300 seconds for a blocking review run
- if the review may take longer, launch it asynchronously and wait for completion
- prefer waiting for the review to finish over truncating a live review

## Recommended workflow

1. Create a concise input file with the exact context Codex needs.
2. Run `scripts/run-review.sh --help` once if you need the interface.
3. Invoke the wrapper in the matching mode.
4. Review the output critically. Codex is a reviewer, not an oracle.
5. Verify important claims against the repo, tests, and runtime evidence.

## Wrapper usage

```bash
~/.agents/skills/claude-review-partner/scripts/run-review.sh \
  --mode implementation-review \
  --input /tmp/review-input.md \
  --cwd /path/to/repo
```

Optional output capture:

```bash
~/.agents/skills/claude-review-partner/scripts/run-review.sh \
  --mode plan-review \
  --input /tmp/plan.md \
  --cwd /path/to/repo \
  --output /tmp/codex-plan-review.md
```

## Direct CLI pattern

Use this only when the wrapper is unnecessary:

```bash
codex exec \
  -m gpt-5.6-sol \
  -c 'model_reasoning_effort="high"' \
  -s read-only \
  -C /path/to/repo \
  - < /tmp/review-input.md
```

## Input guidance

Keep the input file concrete and bounded:
- what changed or what is proposed
- which files or diffs matter
- what kind of review you want
- any repo-specific constraints or acceptance criteria

For templates, see `references/prompt-templates.md`.

## Non-recursion rule

If the wrapper or prompt says that review-partner invocation is already active, do not start another nested Codex review.

## Final-answer rule

When a Codex review was used, summarize the result in your final output:
- what was reviewed
- key findings or that no material issues were found
- what you changed because of the review, if anything
