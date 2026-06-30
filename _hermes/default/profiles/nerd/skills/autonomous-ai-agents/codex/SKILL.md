---
name: codex
description: "Delegate coding to OpenAI Codex CLI (features, PRs)."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [Coding-Agent, Codex, OpenAI, Code-Review, Refactoring]
    related_skills: [claude-code, hermes-agent, hermes-opencode-linear-build, opencode-http-coding-workflow]
---

# Codex CLI

Delegate coding tasks to [Codex](https://github.com/openai/codex) via the Hermes terminal. Codex is OpenAI's autonomous coding agent CLI.

## When to use

- Building features
- Refactoring
- PR reviews
- Batch issue fixing
- For Aaron's current Linear-backed OpenCode repo workflow under `~/code/`, load `hermes-opencode-linear-build`: OpenCode's `/cmd:linear-build-workspace` command owns review orchestration. Do not have Hermes run Codex review gates directly unless Aaron explicitly asks for a legacy/manual review. Codex CLI v0.128.0 no longer accepts the older `-a/--ask-for-approval` flag; use `-s read-only` for read-only reviews and rely on the default non-interactive `approval: never` behavior shown by `codex exec`.

Requires the codex CLI and a git repository.

## Prerequisites

- Codex installed: `npm install -g @openai/codex`
- OpenAI API key configured
- On Aaron's macOS/Hermes setup, if Codex returns `401 Unauthorized` / missing authentication from a plain invocation, retry through the user's interactive login shell: `HOME=/Users/anichols zsh -lic 'cd <repo> && codex exec ...'`. This can expose the configured auth environment that non-login Hermes shells miss.
- **Must run inside a git repository** — Codex refuses to run outside one
- Use `pty=true` in terminal calls for interactive sessions. `codex exec` is non-interactive, but on Aaron's setup a PTY/login shell may still be useful when auth environment is not visible.

## One-Shot Tasks

```
terminal(command="codex exec 'Add dark mode toggle to settings'", workdir="~/project", pty=true)
```

For scratch work (Codex needs a git repo):
```
terminal(command="cd $(mktemp -d) && git init && codex exec 'Build a snake game in Python'", pty=true)
```

## Background Mode (Long Tasks)

```
# Start in background. Use workspace-write for autonomous repo-local work; current Codex exec defaults to non-interactive approval: never.
terminal(command="codex exec -s workspace-write 'Refactor the auth module'", workdir="~/project", background=true, notify_on_complete=true)
# Returns session_id

# Monitor progress
process(action="poll", session_id="<id>")
process(action="log", session_id="<id>")

# Send input if Codex asks a question
process(action="submit", session_id="<id>", data="yes")

# Kill if needed
process(action="kill", session_id="<id>")
```

## Key Flags (verified with codex-cli 0.128.0)

| Flag | Effect |
|------|--------|
| `exec "prompt"` | One-shot/non-interactive execution, exits when done |
| `-C, --cd <DIR>` | Set Codex's working root |
| `-s, --sandbox read-only|workspace-write|danger-full-access` | Select sandbox policy |
| `--dangerously-bypass-approvals-and-sandbox` | No sandbox/no approvals; avoid unless the environment is externally sandboxed |
| `--output-last-message <FILE>` / `-o <FILE>` | Write the final agent message to a file; useful for review artifacts |

## PR Reviews

Clone to a temp directory for safe review:

```
terminal(command="REVIEW=$(mktemp -d) && git clone https://github.com/user/repo.git $REVIEW && cd $REVIEW && gh pr checkout 42 && codex review --base origin/main", pty=true)
```

## Parallel Issue Fixing with Worktrees

```
# Create worktrees
terminal(command="git worktree add -b fix/issue-78 /tmp/issue-78 main", workdir="~/project")
terminal(command="git worktree add -b fix/issue-99 /tmp/issue-99 main", workdir="~/project")

# Launch Codex in each
terminal(command="codex exec -s workspace-write 'Fix issue #78: <description>. Commit when done.'", workdir="/tmp/issue-78", background=true, notify_on_complete=true)
terminal(command="codex exec -s workspace-write 'Fix issue #99: <description>. Commit when done.'", workdir="/tmp/issue-99", background=true, notify_on_complete=true)

# Monitor
process(action="list")

# After completion, push and create PRs
terminal(command="cd /tmp/issue-78 && git push -u origin fix/issue-78")
terminal(command="gh pr create --repo user/repo --head fix/issue-78 --title 'fix: ...' --body '...'")

# Cleanup
terminal(command="git worktree remove /tmp/issue-78", workdir="~/project")
```

## Batch PR Reviews

```
# Fetch all PR refs
terminal(command="git fetch origin '+refs/pull/*/head:refs/remotes/origin/pr/*'", workdir="~/project")

# Review multiple PRs in parallel
terminal(command="codex exec 'Review PR #86. git diff origin/main...origin/pr/86'", workdir="~/project", background=true, pty=true)
terminal(command="codex exec 'Review PR #87. git diff origin/main...origin/pr/87'", workdir="~/project", background=true, pty=true)

# Post results
terminal(command="gh pr comment 86 --body '<review>'", workdir="~/project")
```

## Rules

1. **Use `exec` for one-shots** — `codex exec "prompt"` runs non-interactively and exits cleanly
2. **Git repo required by default** — Codex won't run outside a git directory unless `--skip-git-repo-check` is supplied. Use `mktemp -d && git init` for scratch repo work
3. **Prefer repo-local autonomy** — for supervised implementation use `-s workspace-write`; avoid danger-full-access unless explicitly needed
4. **Background for long tasks** — use `background=true`, `notify_on_complete=true`, and monitor with `process`
5. **PTY is mainly for the interactive TUI** — use `pty=true` for interactive `codex` sessions; `codex exec` is non-interactive and usually does not need PTY
6. **Don't interfere** — monitor with `poll`/`log`, be patient with long-running tasks
7. **Parallel is fine** — run multiple Codex processes at once for batch work
