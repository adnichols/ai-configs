# Deterministic Background Claude Review Extension Design

## Status

Approved direction; awaiting written-spec review before implementation planning.

## Problem

Required Claude Code reviews currently have a deterministic inner transport but a variable outer launch path.

The canonical launcher at `skills/claude-code-review/scripts/claude_interactive_review.py` owns the important Claude mechanics:

- a private tmux server inherited from the real Pi caller environment,
- interactive Claude Code rather than print mode,
- fixed model and effort,
- authentication and TUI-readiness checks,
- prompt paste, answer-boundary detection, and normalized artifact extraction,
- classified failures, transcript preservation, and successful teardown.

The remaining reliability gap is how Pi starts that launcher. A review can be run through blocking `bash`, a managed process, or `pi-interactive-shell` with foreground, dispatch-overlay, or headless-dispatch presentation. Those choices remain under agent control. `pi-interactive-shell` also defaults headless dispatch to an output-quietness kill heuristic, which is unsafe for a Claude review that may be healthy but silent while reasoning.

## Goal

Provide one purpose-built Pi tool named `claude_review` that always starts the canonical launcher invisibly in the background, immediately returns control to Pi, and notifies Pi exactly once when the review succeeds or fails.

The tool must remove agent control over transport, presentation mode, model, effort, quiet-time termination, launcher location, and timeout policy.

## Non-goals

- Replace the canonical Python launcher or reimplement its tmux/TUI protocol in TypeScript.
- Change Claude authentication, subscription, account limits, or credential storage.
- Make `pi-interactive-shell` less capable for unrelated interactive-agent delegation.
- Build a general-purpose background process manager.
- Guarantee that a review survives Pi process termination, `/reload`, session replacement, or machine restart. Active reviews are session-scoped in the first implementation and fail visibly during shutdown rather than becoming untracked orphan processes.
- Block all possible non-review Claude CLI usage. Enforcement is limited to known required-review routes and the canonical launcher.

## Architecture

Add a repo-owned Pi extension under `_pi/extensions/claude-review/`. `install.sh --pi` already copies repo-owned extension files and directories into `~/.pi/agent/extensions`, so no separate package installation is required.

The extension registers a custom `claude_review` tool. It does not depend on `pi-interactive-shell` or `pi-processes`.

```text
review workflow
  -> writes a bounded review prompt file
  -> calls claude_review with semantic file inputs
  -> extension validates inputs and creates a job
  -> extension spawns the canonical Python launcher headlessly
  -> tool returns the job id immediately
  -> canonical launcher drives interactive Claude in private tmux
  -> canonical launcher writes the review/failure artifact and exits
  -> extension validates completion and sends one Pi notification
  -> coordinating agent reads and triages the artifact
```

The outer child process uses ordinary redirected stdio, not a PTY. This is safe because the Python launcher creates and drives Claude's interactive TUI inside its own private tmux server.

## Tool contract

The public schema exposes semantic operations, not launch mechanics.

### Start a review

```text
claude_review({
  action: "start",
  promptFile: "/absolute/or/repo-relative/review-prompt.md",
  output: "/absolute/or/repo-relative/review-output.md",
  cwd: "/repo"
})
```

`cwd` defaults to the current Pi working directory. Leading `@` path markers are normalized consistently with Pi file tools.

The agent cannot provide:

- a shell command,
- foreground/background mode,
- overlay settings,
- model or effort,
- launcher path,
- inner or outer timeout,
- quiet threshold,
- arbitrary Claude arguments,
- alternate transport or fallback behavior.

### Smoke test

```text
claude_review({
  action: "smoke",
  output: "/tmp/claude-review-smoke.txt",
  cwd: "/repo"
})
```

Smoke uses the canonical launcher's `--smoke` mode and the same background controller.

### Job inspection and cancellation

```text
claude_review({ action: "list" })
claude_review({ action: "status", jobId: "claude-review-..." })
claude_review({ action: "cancel", jobId: "claude-review-..." })
```

Inspection returns bounded output and stable paths to the full stdout/stderr logs. Cancellation terminates the launcher process, records a cancelled result, and reports any preserved canonical-launcher inspect/transcript metadata. It does not silently classify cancellation as a review verdict.

## Fixed launch policy

For review jobs the extension always invokes:

```text
python3 $HOME/.agents/skills/claude-code-review/scripts/claude_interactive_review.py
  --cwd <resolved cwd>
  --prompt-file <resolved prompt path>
  --output <resolved output path>
  --review-name <extension-generated collision-safe name>
  --timeout-seconds 3600
```

For smoke jobs it invokes the same launcher with `--smoke` and a 120-second launcher timeout.

The extension starts the command with `node:child_process.spawn` using an argument array rather than a shell string. This avoids quoting ambiguity and prevents agent-controlled shell expansion.

Outer watchdogs cover the launcher's complete valid lifecycle—not only its answer timeout—including login-shell discovery, auth preflight, TUI readiness, prompt-boundary setup, teardown, and margin:

- review: 4,200 seconds,
- smoke: 300 seconds.

There is no output-quietness timeout. Silence is not treated as failure.

The launcher remains the single source of truth for Claude model, effort, readiness regex, prompt protocol, and tmux behavior. Prompts and skills must not repeat model/version claims that can drift from launcher constants.

## Job lifecycle

Each job has:

- a collision-safe job id,
- action, resolved cwd, prompt path when applicable, and output path,
- start and completion timestamps,
- child PID while running,
- stdout and stderr log paths,
- a durable terminal-state JSON path,
- status: `running`, `succeeded`, `failed`, `timed_out`, or `cancelled`,
- exit code and completion classification.

The extension atomically reserves the canonicalized output identity before any awaited stale-output cleanup, rejects a second active job targeting that identity, and releases only the owning reservation. Different output paths may run concurrently.

The initial `start` or `smoke` call returns immediately after the child has spawned successfully. A spawn failure is returned synchronously as a tool error.

On child exit the extension validates the result:

- Exit zero requires the output artifact to exist and contain the expected launcher success marker/metadata for that action; review artifacts must also contain a final `VERDICT:` line.
- Nonzero exit requires a classified launcher failure artifact. Missing output is reported as review infrastructure failure with stdout/stderr log paths.
- A zero exit with a missing or malformed artifact is infrastructure failure, never a clean review.
- Completion notification is emitted exactly once with `pi.sendMessage(..., { triggerTurn: true })`.

Notifications contain only a bounded summary. Full review content remains in the output artifact so large reviews do not flood the Pi context. Active jobs plus a bounded terminal-history ring remain in memory; every terminal result is persisted to its JSON state file before old history is evicted.

## Shutdown behavior

Active jobs are session-scoped in the first implementation.

On `session_shutdown`, the extension suppresses normal completion-triggered LLM turns, terminates active launcher children, waits a short bounded grace period, force-kills remaining child process groups, cleans job-owned private tmux sockets, and writes cancellation status to durable job metadata. It does not leave an untracked Claude or launcher process running or start work in a session being destroyed.

Because the canonical launcher intentionally preserves failed tmux state for inspection, shutdown and cancellation messages must surface any output artifact, transcript, or tmux inspect command that the launcher produced before termination.

Cross-session durability can be added later only if real usage demonstrates a need. It would require a separate supervisor and persisted completion delivery, which is deliberately excluded from this scoped reliability fix.

## Enforcement and migration

All Pi required-review prompts and shared review skills must instruct agents to call `claude_review` rather than constructing launcher commands.

The extension adds a `tool_call` policy guard for Pi calls that attempt to invoke the canonical launcher through `bash`, `process`, or `interactive_shell`. Those calls are blocked with:

```text
Direct Claude review launcher invocation is disabled. Use claude_review.
```

The guard also blocks direct review-intent Claude launches through `bash`, `process`, or `interactive_shell`. It does not block unrelated Claude delegation or benign source inspection/diff/parity commands that merely reference the launcher path.

The existing source scanner at `skills/claude-code-review/scripts/check_no_direct_claude_review_launches.py` is updated so `claude_review` is the only accepted Pi required-review entrypoint. Canonical launcher internals and approved tests remain exempt.

Known migration targets include:

- `skills/claude-code-review/SKILL.md`,
- `_pi/prompts/review:change-claude-code.md`,
- `_pi/prompts/review:plan-adversarial.md`,
- shared workflows that currently show direct Python launcher commands,
- `_pi/README.md`,
- install verification and guardrail tests.

Codex and non-Pi consumers may continue to invoke the canonical Python launcher directly where Pi tools are unavailable. The `claude_review` restriction applies to Pi required-review execution paths.

## Error handling

Failures are explicit and do not trigger alternate transports.

The extension distinguishes:

- invalid or missing input paths,
- output path already owned by an active job,
- canonical launcher missing,
- Python spawn failure,
- launcher-classified auth/readiness/rate-limit/boundary/timeout failures,
- outer watchdog timeout,
- cancellation or Pi shutdown,
- zero exit without a valid artifact,
- nonzero exit without a classified artifact.

Every failure reports the output path and stdout/stderr log paths. When available, it also reports the canonical launcher's transcript and tmux inspect command.

No error path falls back to direct Claude, print mode, another model provider, `pi-interactive-shell`, or a foreground execution.

## Testing strategy

### Extension unit tests

Use a fake launcher executable or injected test-only launcher resolver to verify:

- the tool returns immediately after spawn,
- no `ctx.ui.custom`, overlay, or terminal UI API is called,
- the exact argument array and fixed timeouts are used,
- no shell is involved,
- model, effort, transport, timeout, and presentation cannot be supplied by tool input,
- silence longer than the previous interactive-shell quiet threshold does not kill a job,
- success notification occurs exactly once,
- failure notification occurs exactly once,
- zero exit without a valid artifact fails,
- nonzero exit with a classified artifact preserves the classification,
- duplicate active output paths are rejected,
- distinct jobs can run concurrently,
- status/list output is bounded,
- cancellation and session shutdown reap child processes,
- direct canonical-launcher calls through other Pi tools are blocked.

### Launcher regression tests

Retain and run the existing canonical-launcher fake-TUI suite covering auth, TUI readiness, prompt echo, marker/sentinel boundaries, ANSI handling, session limits, teardown, and real smoke opt-ins.

### Stress tests

Run repeated fake jobs with randomized combinations of:

- immediate and delayed success,
- long silent intervals,
- partial stdout/stderr,
- classified failures,
- missing artifacts,
- timeout and cancellation races,
- concurrent completion ordering.

The stress test must assert no duplicate completion notification, no active-job registry leak, and no surviving fake child process.

### Installed-surface tests

After `./install.sh --pi`:

- confirm the extension exists under `~/.pi/agent/extensions/claude-review/`,
- confirm `claude_review` is registered in a real Pi process,
- run installed smoke mode,
- run source and installed guardrail scans,
- confirm migrated prompts contain no direct Pi launcher command,
- confirm `pi-interactive-shell` is not involved in the Claude review path.

### Real Claude validation

Run several same-process smoke tests followed by a bounded number of tiny real reviews. Record rate-limit or account-limit failures as real infrastructure evidence rather than retrying through another transport.

## Success criteria

The change is complete when:

1. Pi required Claude reviews call only `claude_review`.
2. Starting a review never opens an overlay or blocks the active Pi turn.
3. The agent cannot select foreground/background, model, effort, transport, launcher path, or timeout policy.
4. Long output silence does not terminate a healthy review.
5. Completion wakes Pi exactly once and points to a validated artifact.
6. Failure never becomes a clean verdict and never triggers an alternate transport.
7. Cancellation and session shutdown leave no untracked launcher child.
8. Source, installed, stress, launcher regression, and bounded real-Claude tests pass or report a truthful external Claude limit blocker.
