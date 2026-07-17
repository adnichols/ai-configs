---
name: codex-review-partner
description: Use Codex as a second-pass reviewer, adversarial PR-feedback follow-up reviewer, plan reviewer, or pairing partner during technical work. Trigger when implementing, refactoring, debugging, writing tests, reviewing a plan/spec, when PR feedback shows prior review missed issues, or when you want an independent Codex CLI pass before finalizing technical work.
---

# Codex Review Partner

Use Codex as an explicit second pass before you finalize technical work.

When the caller is already Codex, prefer a Codex subagent/native review task when available.

In Pi, required Codex review legs must use the managed `codex_review` tool.

Other runtimes may use the wrapper when no managed or native review facility exists.

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
2. In Codex, launch a Codex subagent/native review task when available; otherwise run `scripts/run-review.sh --help` once if you need the subprocess interface.
3. In Pi, invoke `codex_review` with the workflow-specific verdict profile.
   In other runtimes, invoke the wrapper in the matching mode when a subprocess fallback is needed.
4. Review the output critically. Codex is a reviewer, not an oracle.
5. Verify important claims against the repo, tests, and runtime evidence.

## Pi managed usage

```text
codex_review({
  action: "start",
  reviewType: "implementation-review",
  verdictProfile: "generic-implementation",
  promptFile: "/tmp/review-input.md",
  output: "/tmp/codex-review.md",
  cwd: "/path/to/repo"
})
```

## Non-Pi / fallback wrapper usage

```bash
~/.agents/skills/codex-review-partner/scripts/run-review.sh \
  --mode implementation-review \
  --verdict-profile generic-implementation \
  --input /tmp/review-input.md \
  --cwd /path/to/repo
```

Optional output capture:

```bash
~/.agents/skills/codex-review-partner/scripts/run-review.sh \
  --mode plan-review \
  --verdict-profile generic-plan \
  --input /tmp/plan.md \
  --cwd /path/to/repo \
  --output /tmp/codex-plan-review.md
```

Review modes require an explicit compatible `--verdict-profile`; legacy profile-less calls fail before launch with migration syntax. `generic-implementation` accepts `FINDINGS_TO_RESOLVE`, `CLEAN_FOR_PR`, `BLOCKED_BY_QUESTION`, and `REVIEW_INCOMPLETE_RERUN_NEEDED`. `generic-plan` accepts `PLAN_EXECUTION_READY`, `PLAN_NEEDS_REVISION`, `BLOCKED_BY_QUESTION`, and `REVIEW_INCOMPLETE_RERUN_NEEDED`. The exact final non-empty line must be `VERDICT: <TOKEN>`. Pair mode remains profile-less and non-gating.

The wrapper resolves `${SHELL:-/bin/zsh}`, invokes `codex exec --json --output-last-message` through a supported login shell, and keeps progress JSONL separate from the final artifact. Its process-group watchdog is elapsed-time based, never output-silence based.

## Supported hosts and process safety

The managed launcher supports Linux and macOS with the system Python standard library. It does not require an external `setsid` executable or a Homebrew PATH change. `process_identity.py` uses Linux `/proc` only inside the Linux adapter and Darwin `libproc` plus kernel boot time inside the macOS adapter. `review_supervisor.py` creates the private session with `os.setsid()`, monitors both the launcher and Pi owner identities, and verifies SID-wide TERM-to-KILL cleanup before reporting success.

Unsupported platforms, unavailable Darwin `libproc`, malformed identity output, PID/start/boot/session mismatch, and cleanup uncertainty fail closed. Inspect the launcher stderr, status file, and process-identity sidecar named by the `codex_review` completion. Do not rerun a required review while `CODEX_REVIEW_CLEANUP_FAILED` evidence remains unresolved, and do not work around capability failures with `ps` parsing, direct `codex exec`, or a model/subagent fallback.

Installed-stack diagnostics:

```bash
python3 ~/.agents/skills/codex-review-partner/scripts/process_identity.py preflight
python3 ~/.agents/skills/codex-review-partner/scripts/review_supervisor.py --preflight
```

## Direct CLI pattern

Use this only when the wrapper is unnecessary and login-shell normalization is not required:

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

For `adversarial-implementation-review`, include the PR feedback that escaped earlier review, the direct fix, and your hypothesis about the failure family — but pass the direct fix and failure-family hypothesis as claims to verify or refute, not as established facts, and ask Codex to re-derive the invariant from the code/schema rather than trusting them. Ask Codex to search the full current PR diff for sibling issues, partial fixes, missing tests, and nearby plan-bound failures, including the inverse direction of any serialization/reference boundary the fix touches. This is not a license for broad unrelated audits; it is a more skeptical pass over the PR's assumptions after a missed defect signal.

For templates, see `references/prompt-templates.md`.

## Non-recursion rule

If the wrapper or prompt says that review-partner invocation is already active, do not start another nested Codex review.

## Final-answer rule

When a Codex review was used, summarize the result in your final output:
- what was reviewed
- key findings or that no material issues were found
- what you changed because of the review, if anything
