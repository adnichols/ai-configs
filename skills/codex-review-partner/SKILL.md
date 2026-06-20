---
name: codex-review-partner
description: Use Codex as a second-pass reviewer, adversarial PR-feedback follow-up reviewer, plan reviewer, or pairing partner during technical work. Trigger when implementing, refactoring, debugging, writing tests, reviewing a plan/spec, when PR feedback shows prior review missed issues, or when you want an independent Codex CLI pass before finalizing technical work.
argument-hint: "[implementation-review|adversarial-implementation-review|plan-review|pair] <input-file> [repo-path]"
---

# Codex Review Partner

Use Codex as an explicit second pass before you finalize technical work.

## Core rule

For coding work, plan work, refactors, debugging, and test changes, run a Codex review pass before your final answer.

Use one of four modes:
- `implementation-review` for code changes, bug fixes, refactors, and tests
- `adversarial-implementation-review` when PR feedback proves a prior review missed issues and the next pass must search harder for related failures
- `plan-review` for plans, specs, and implementation approaches
- `pair` for open-ended debugging, exploration, and design discussion

## Timeout rule

When launching `codex` from another tool runner, never use a short 120s timeout for review work.

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
~/.agents/skills/codex-review-partner/scripts/run-review.sh \
  --mode implementation-review \
  --input /tmp/review-input.md \
  --cwd /path/to/repo
```

Optional output capture:

```bash
~/.agents/skills/codex-review-partner/scripts/run-review.sh \
  --mode plan-review \
  --input /tmp/plan.md \
  --cwd /path/to/repo \
  --output /tmp/codex-plan-review.md
```

## Direct CLI pattern

Use this only when the wrapper is unnecessary:

```bash
codex exec \
  -m gpt-5.5 \
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

For `adversarial-implementation-review`, include the PR feedback that escaped earlier review, the direct fix, and your hypothesis about the failure family — but pass the direct fix and failure-family hypothesis as claims to verify or refute, not as established facts, and ask Codex to re-derive the invariant from the code/schema rather than trusting them. Ask Codex to search the full current PR diff for sibling issues, partial fixes, missing tests, and nearby plan-bound failures, including the inverse direction of any serialization/reference boundary the fix touches. This is not a license for broad unrelated audits; it is a more skeptical pass over the PR's assumptions after a missed defect signal.

For templates, see `references/prompt-templates.md`.

## Non-recursion rule

If the wrapper or prompt says that review-partner invocation is already active, do not start another nested Codex review.

## Final-answer rule

When a Codex review was used, summarize the result in your final output:
- what was reviewed
- key findings or that no material issues were found
- what you changed because of the review, if anything
