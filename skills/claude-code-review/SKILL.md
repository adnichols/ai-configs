---
name: claude-code-review
description: Run read-only Claude Code plan/code reviews through the canonical private-tmux interactive launcher. In Pi, use the visibly-running deterministic claude_review subprocess tool; non-Pi consumers call the launcher directly.
---

# Claude Code Review

Use this skill when a required Claude Code review must run reliably and produce a saved review artifact.

The canonical Python launcher owns all Claude Code process mechanics: private tmux, authentication checks, interactive TUI startup, model/effort selection, prompt delivery, terminal-boundary extraction, persisted Claude-session JSONL recovery when long alternate-screen output scrolls beyond the viewport, timeout classification, transcript preservation, signal cleanup, and successful teardown. Do not duplicate or override those mechanics in callers.

## Pi: required visible subprocess tool

In Pi, required Claude Code reviews must use the `claude_review` tool. Before starting it, tell the user that the Claude reviewer subprocess is starting and that you will wait for it. The tool remains visibly active with its job ID and supervisor PID until the reviewer exits, applies no output-silence timeout, and then returns the terminal result directly so the agent can read and triage the artifact in the same turn. The accepted job is still owned by a detached supervisor and persists independently if the visible tool call is interrupted, the session is replaced, or Pi exits. In that detached case the originating session receives the completion notification when available; after reload, session replacement, or Pi exit, recover the job with `list` or `status`.

Write the bounded read-only prompt to a file, then call:

```text
claude_review({
  action: "start",
  cwd: "/path/to/repo",
  promptFile: "/tmp/claude-review-prompt.md",
  output: "/tmp/claude-review-output.md"
})
```

For same-process readiness validation:

```text
claude_review({
  action: "smoke",
  cwd: "/path/to/repo",
  output: "/tmp/claude-review-smoke.txt"
})
```

Do not poll after starting a normal job: the visible tool call remains active and returns when the reviewer exits. Then read `output`. If that tool call was interrupted, consume its automatic completion notification when it arrives. Use `action: "status"` or `"list"` to recover persisted work after reload/restart or for explicit diagnosis; use `"cancel"` only for genuine user-requested cancellation.

Pi must not invoke the launcher through `bash`, `process`, `interactive_shell`, prompt piping, raw tmux, or direct Claude CLI commands. The Pi extension blocks known direct review routes and points callers back to `claude_review`.

## Non-Pi consumers

Codex, OpenCode, and other runtimes without the Pi tool call the canonical launcher directly:

```bash
python3 "$HOME/.agents/skills/claude-code-review/scripts/claude_interactive_review.py" \
  --cwd /path/to/repo \
  --prompt-file /tmp/claude-review-prompt.md \
  --output /tmp/claude-review-output.md \
  --review-name claude-review \
  --timeout-seconds 3600
```

The launcher owns all Claude Code process mechanics. For required reviews, pass `--timeout-seconds 3600` unless the user explicitly asks for a longer limit; do not rely on implicit defaults or short outer tool timeouts.

- creates a fresh private tmux server from the real caller process,
- removes an inherited `CLAUDE_CONFIG_DIR` override and resolves `claude` through the configured non-interactive POSIX-style login shell (`sh`, `bash`, `zsh`, `ksh`, or `dash`), so stale harness profiles cannot shadow the current user login; unsupported shells fail clearly,
- starts exactly one interactive Claude TUI with the launcher-internal command pinned to Sonnet 5 on Extra High (`claude --model claude-sonnet-5 --effort xhigh`),
- pastes the prompt through tmux,
- extracts only the answer region after the post-submit boundary,
- assigns a known Claude session id and, when the completion sentinel is visible but the marker/review scrolled out of the 60-row alternate-screen viewport, recovers the complete assistant answer from Claude's persisted session JSONL,
- writes normalized review text at the beginning of `--output` and records the Claude session id/session-record path in launcher metadata,
- tears down successful smoke/review tmux servers and kills the exact private tmux server on cancellation signals,
- preserves transcript and inspect metadata on failure.

Do not choose or document alternate required-review transports or models. Required Claude Code reviews must use the launcher's Sonnet 5 Extra High pin. In particular, do not use `claude -p` [FORBIDDEN-EXAMPLE], `claude --print` [FORBIDDEN-EXAMPLE], prompt piping, input redirection, direct `interactive_shell` Claude launches, direct `process` Claude launches, raw tmux Claude snippets outside the launcher, lower-effort/model substitutions, or model-provider substitutes for a required Claude Code gate.

## Same-process smoke outside Pi

Before relying on a non-Pi caller context, smoke-test the launcher from that same context:

```bash
python3 "$HOME/.agents/skills/claude-code-review/scripts/claude_interactive_review.py" \
  --smoke \
  --cwd /path/to/repo \
  --review-name claude-review-smoke \
  --output /tmp/claude-review-smoke.txt
```

Required reviews must not use direct Claude print mode, prompt piping, input redirection, direct `interactive_shell` Claude launches, direct `process` Claude launches, raw tmux snippets outside the launcher, lower-effort/model substitutions, or model-provider substitutes.

## Prompt rules

Keep prompts read-only and scope-bounded:

- explicitly say **read-only** and **do not edit files**,
- name the plan path or diff/range under review,
- name any workflow-specific verdict format (this is separate from launcher transport validity),
- ask for findings with file/path evidence,
- exclude unrelated cleanup and broad audits.

## Result contract

A process exit by itself is not a review verdict. Transport validity and workflow verdict interpretation are separate contracts.

- Review transport success requires successful launcher completion, a non-empty normalized review answer, `CLAUDE_REVIEW_LAUNCHER_METADATA` with launcher metadata such as `socket=` and `session=`, and no classified launcher/provider failure.
- A literal `VERDICT:` line is not a universal transport requirement. Calling workflows may still require one of their own verdict tokens and must interpret or reject the otherwise valid review artifact at that layer.
- Smoke success requires `CLAUDE_REVIEW_SMOKE_READY`, `socket=`, and `session=`.
- Empty output, missing metadata, prompt-template/tool-only output, provider errors, malformed smoke artifacts, and timeouts are review infrastructure failures.
- A classified launcher failure is not a clean review and must not trigger an alternate transport.
- Pi persists `running`, `succeeded`, `failed`, `timed_out`, `cancelled`, and `interrupted` states. Routine session shutdown does not cancel accepted jobs; `cancelled` is reserved for explicit cancellation, while `interrupted` identifies a genuinely lost supervisor that required orphan cleanup.

## Failure handling

Launcher failures are agent-legible and may include:

- missing `tmux`, the configured login shell, `claude`, or launcher installation,
- TUI reports not logged in,
- TUI readiness timeout,
- prompt-boundary uncertainty,
- session/rate limit,
- review timeout.

Read the output artifact and sibling transcript/log paths. Launcher metadata may also include `claude_session_id=` and `session_record=` for the persisted Claude answer source. If an inspect command is present, use it to inspect the preserved private tmux server. Ask for the exact user action named by the failure, such as `/login`, unlocking the keychain, or waiting for a usage reset. Never switch transports as a fallback.

## Installed locations

Canonical source:

- `skills/claude-code-review/scripts/claude_interactive_review.py`

Expected installed copies:

- shared launcher: `$HOME/.agents/skills/claude-code-review/scripts/claude_interactive_review.py`
- OpenCode compatibility: `$HOME/.config/opencode/skills/claude-code-review/scripts/claude_interactive_review.py`

The Pi `claude_review` tool always resolves the shared installed launcher. OpenCode may resolve its explicit override, the shared installed launcher, the repo checkout launcher, or the compatibility copy according to its existing resolver contract.
