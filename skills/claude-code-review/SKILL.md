---
name: claude-code-review
description: Run read-only Claude Code plan/code reviews through the canonical private-tmux interactive launcher. In Pi, use the deterministic background claude_review tool; non-Pi consumers call the launcher directly.
---

# Claude Code Review

Use this skill when a required Claude Code review must run reliably and produce a saved review artifact.

The canonical Python launcher owns all Claude Code process mechanics: private tmux, authentication checks, interactive TUI startup, model/effort selection, prompt delivery, answer extraction, timeout classification, transcript preservation, and successful teardown. Do not duplicate or override those mechanics in callers.

## Pi: required background tool

In Pi, required Claude Code reviews must use the `claude_review` tool. The tool always runs invisibly in the background, returns immediately, applies no output-silence timeout, and notifies Pi when the saved artifact is ready.

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

Do not poll after starting a normal job. Consume the automatic completion notification, then read `output`. Use `action: "status"`, `"list"`, or `"cancel"` only for explicit diagnosis or cancellation.

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
- starts exactly one interactive Claude TUI with the launcher-internal command pinned to Opus 4.7 on Extra High (`claude --model claude-opus-4-7 --effort xhigh`),
- pastes the prompt through tmux,
- extracts only the answer region after the post-submit boundary,
- writes normalized review text at the beginning of `--output`,
- tears down successful smoke/review tmux servers,
- preserves transcript and inspect metadata on failure.

Do not choose or document alternate required-review transports or models. Required Claude Code reviews must use the launcher's Opus 4.7 Extra High pin. In particular, do not use `claude -p` [FORBIDDEN-EXAMPLE], `claude --print` [FORBIDDEN-EXAMPLE], prompt piping, input redirection, direct `interactive_shell` Claude launches, direct `process` Claude launches, raw tmux Claude snippets outside the launcher, lower-effort/model substitutions, or model-provider substitutes for a required Claude Code gate.

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
- name the expected verdict format,
- ask for findings with file/path evidence,
- exclude unrelated cleanup and broad audits.

## Result contract

A process exit by itself is not a review verdict.

- Success requires a valid launcher artifact beginning with normalized review text and containing launcher metadata.
- Smoke success requires `CLAUDE_REVIEW_SMOKE_READY`, `socket=`, and `session=`.
- Empty output, missing metadata, tool-only output, provider errors, and timeouts are review infrastructure failures.
- A classified launcher failure is not a clean review and must not trigger an alternate transport.

## Failure handling

Launcher failures are agent-legible and may include:

- missing `tmux`, the configured login shell, `claude`, or launcher installation,
- TUI reports not logged in,
- TUI readiness timeout,
- prompt-boundary uncertainty,
- session/rate limit,
- review timeout.

Read the output artifact and sibling transcript/log paths. If an inspect command is present, use it to inspect the preserved private tmux server. Ask for the exact user action named by the failure, such as `/login`, unlocking the keychain, or waiting for a usage reset. Never switch transports as a fallback.

## Installed locations

Canonical source:

- `skills/claude-code-review/scripts/claude_interactive_review.py`

Expected installed copies:

- shared launcher: `$HOME/.agents/skills/claude-code-review/scripts/claude_interactive_review.py`
- OpenCode compatibility: `$HOME/.config/opencode/skills/claude-code-review/scripts/claude_interactive_review.py`

The Pi `claude_review` tool always resolves the shared installed launcher. OpenCode may resolve its explicit override, the shared installed launcher, the repo checkout launcher, or the compatibility copy according to its existing resolver contract.
