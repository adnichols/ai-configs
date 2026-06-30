---
name: aoe-development-sessions
description: "Use when Aaron asks Hermes to manage repo-based development sessions through Agent of Empires (`aoe`) instead of launching pi, Codex, or other coding agents directly in tmux. Covers creating sessions/worktrees, sending prompts, capturing state, using ACP structured sessions, and safely supervising or cleaning up work."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [aoe, agent-of-empires, coding-agents, development-sessions, tmux, worktrees, acp]
    related_skills: [pi-coding-workflow, codex, opencode, claude-code]
---

# AoE Development Sessions

## Overview

Use Agent of Empires (`aoe`) as the control plane for development sessions instead of launching pi, Codex, Claude Code, OpenCode, or Hermes directly in ad-hoc tmux panes.

AoE is a terminal session manager backed by tmux. It tracks session records, project paths, tools, profiles, worktrees, status, pane capture, prompts, ACP structured-view workers, and cleanup. For Aaron's development work, prefer `aoe` as the durable interface whenever the request is to start, resume, inspect, message, supervise, or clean up a coding-agent session.

This skill does **not** replace the repo's development workflow expectations. If a repo has a staged plan/review/execute/validate/PR workflow, keep that workflow; use AoE for session lifecycle and interaction rather than raw tmux.

Aaron's current preferred evolution for new Hermes-driven development work is: HTML planning through `plan-review`, AoE as the session/worktree/control plane, Pi running under AoE where appropriate, explicit plan-stage and implementation-stage PM review gates, and an open-PR feedback/check watcher. Raw tmux should be treated as an observation or emergency-diagnostics layer, not the primary management surface, unless repo-local instructions or Aaron explicitly require tmux-first control.

## When to Use

Use this skill when Aaron asks you to:

- start a development session using `aoe`
- manage coding-agent sessions without directly launching pi/Codex in tmux
- create an AoE-managed worktree session for a branch
- list or inspect active coding sessions
- send follow-up instructions to an existing agent session
- capture recent session output without attaching interactively
- use AoE ACP structured-view sessions
- stop, archive, snooze, remove, or clean up an AoE-managed session
- resume or coordinate multiple repo sessions through Agent of Empires

Do **not** use this skill for:

- one-off shell commands that do not need a long-running agent session
- generic Git/GitHub operations after the agent has completed work
- destructive cleanup without first identifying the exact session and worktree
- bypassing repo-specific workflow gates such as plan review, validation, smoke tests, PM review, code review, or PR follow-up

## Core Principle

Treat AoE as the session registry and transport layer:

1. Discover the target repo and current AoE profile.
2. Create or identify an AoE session.
3. Send grounded prompts through AoE.
4. Inspect state with AoE list/show/status/capture/history.
5. Let the repo workflow define what the agent should do.
6. Verify filesystem/git/test outcomes from Hermes before reporting success.

Avoid freehand tmux pane management for sessions that AoE can own. Use raw tmux only for emergency diagnosis when AoE output is insufficient.

## Prerequisites

Check these before launching substantial work:

```bash
command -v aoe
aoe --version
aoe agents
```

Known-good local shape observed on Aaron's macOS machine:

- `aoe` installed at `/opt/homebrew/bin/aoe`
- `aoe 1.11.0`
- installed tools include `claude`, `opencode`, `codex`, `gemini`, `cursor`, `copilot`, `pi`, `droid`, and `hermes`

Do not assume those versions forever; verify live state when it matters.

## Profiles

AoE supports separate profiles:

```bash
aoe list --json
aoe list --all --json
aoe status --json
aoe status --verbose
```

Many existing sessions may be under profile `main`. If a user names a session that does not appear in the default profile, retry with:

```bash
aoe --profile main list --json
aoe --profile main session show <id-or-title> --json
```

Use `AGENT_OF_EMPIRES_PROFILE=<profile>` or `--profile <profile>` when necessary. Do not silently create duplicate sessions in the wrong profile if an existing matching session is likely under another profile.

## Creating Sessions

### Basic session in an existing repo

```bash
aoe add /path/to/repo --title "short-task-name" --tool pi --launch
```

Useful options:

| Option | Purpose |
|---|---|
| `--title <TITLE>` | Human-readable session name. Prefer concise task/issue names. |
| `--group <GROUP>` | Group sessions by repo or project. |
| `--tool <TOOL>` | Built-in/configured agent, e.g. `pi`, `codex`, `claude`, `opencode`, `hermes`. |
| `--cmd <COMMAND>` | Raw command to run when a named tool is not enough. |
| `--launch` | Start immediately after creating the session. |
| `--extra-args <ARGS>` | Append args after the agent binary. |
| `--yolo` | Skip permission prompts; only use when explicitly appropriate. |
| `--trust-hooks` | Trust repo hooks/project-local MCP servers; use deliberately. |
| `--structured-view` | Use ACP structured view instead of raw terminal/tmux view. |
| `--agent <AGENT>` | Select ACP agent for structured view, e.g. `aoe-agent`, `claude-code`. |
| `--model <MODEL>` | Override the model for `aoe-agent`. |
| `--scratch` | Use a fresh scratch directory; removed when session is deleted unless kept. |

### Worktree session for parallel development

For repo work where a new branch is desired, prefer AoE-managed worktrees:

```bash
aoe add /path/to/repo \
  --title "issue-or-task-slug" \
  --group "repo-name" \
  --tool pi \
  --worktree issue-or-task-slug \
  --new-branch \
  --base-branch develop \
  --launch
```

Guidance:

- Create the branch/worktree before planning when following Aaron's staged workflow.
- Use the repo's actual target branch (`develop`, `main`, release branch, or stacked branch) as `--base-branch`.
- Use `--repo <extra-repo>` or `--project <registered-project>` for multi-repo workspaces.
- Use `--no-submodules` only when submodules are irrelevant or too expensive.

Inspect worktree state with:

```bash
aoe worktree list
aoe worktree info <session-id-or-title>
```

## Listing and Identifying Sessions

Use JSON when scripting or when you need exact IDs:

```bash
aoe list --json
aoe status --json
aoe status --verbose
aoe session show <id-or-title> --json
```

Prefer the stable session `id` over a title when sending prompts or performing lifecycle actions, especially if titles are ambiguous.

If you are inside an AoE tmux session, auto-detect it:

```bash
aoe session current --json
aoe session current --quiet
```

## Starting, Stopping, Attaching, and Capturing

Lifecycle:

```bash
aoe session start <id-or-title>
aoe session stop <id-or-title>
aoe session restart <id-or-title>
aoe session attach <id-or-title>
aoe session show <id-or-title> --json
```

Capture recent pane output without attaching:

```bash
aoe session capture <id-or-title> --lines 80 --strip-ansi
aoe session capture <id-or-title> --lines 120 --strip-ansi --json
```

Use capture before sending follow-up prompts. It prevents stale steering and gives evidence of whether the agent is idle, blocked, asking for approval, actively working, or already finished.

When summarizing several idle sessions for Aaron's `/gm` or planning triage, combine AoE capture with filesystem evidence. `aoe session capture` may be empty for stopped/old panes even when the session record is still idle; in that case inspect the session path for active plan/discovery artifacts and run git status/log to identify what was left untracked, modified, registered, or waiting for review. Summaries should say where each session left off, not just list paths.

## Sending Prompts to Terminal-View Sessions

For regular terminal/tmux-backed sessions:

```bash
aoe send <id-or-title> "Continue from the current state. First summarize what you believe remains, then execute the next safe step."
```

Behavior note:

- `aoe send` revives dead/stopped sessions by default.
- Use `--no-revive` when scripts should fail loudly rather than restart a crashed/stopped session:

```bash
aoe send --no-revive <id-or-title> "status check"
```

Prompting rules:

- Always include enough repo/task context for the agent to act correctly.
- Tell the agent whether it may edit files, run tests, commit, push, or open PRs.
- If following a staged workflow, specify the current stage and what not to redo.
- Ask for concrete artifacts: plan path, test command output, PR URL, screenshots, etc.

## ACP Structured-View Sessions

AoE can run ACP structured sessions with native prompt/history/tail/approval commands.

Create an ACP session:

```bash
aoe add /path/to/repo \
  --title "task-slug" \
  --tool hermes \
  --structured-view \
  --agent aoe-agent \
  --model gpt-5 \
  --launch
```

Inspect ACP setup:

```bash
aoe acp doctor
aoe acp agents
aoe acp ps
```

Send a prompt:

```bash
aoe acp prompt <session-id> "message text"
```

For long prompts, read from stdin:

```bash
printf '%s\n' "$(cat /path/to/prompt.md)" | aoe acp prompt <session-id> -
```

Read persisted transcript or live stream:

```bash
aoe acp history <session-id>
aoe acp history <session-id> --json
aoe acp status <session-id> --json
aoe acp tail <session-id> --since 0
```

Resolve approvals:

```bash
aoe acp approve <session-id> <nonce>
aoe acp approve <session-id> <nonce> --always
aoe acp approve <session-id> <nonce> --deny
```

Cancel or restart when wedged:

```bash
aoe acp cancel <session-id>
aoe acp restart <session-id>
aoe acp stop <session-id>
aoe acp kill <session-id>
```

Use ACP history/tail instead of pane scraping for structured sessions when available.

## Staged Development Workflow Through AoE

When the repo/task requires Aaron's full development loop, keep the stages but route interaction through AoE:

1. Inspect repo guidance (`AGENTS.md`, testing docs, plan conventions, product intent docs).
2. Create an AoE worktree session on the intended branch.
3. Send a **plan-only** prompt; explicitly prohibit code changes.
4. Verify the plan file exists on disk from Hermes.
5. Run plan review/integration prompts through AoE.
6. Commit the reviewed plan from Hermes or by explicitly delegating and verifying.
7. Send implementation prompt (`/dev:run` or repo-specific equivalent) through AoE.
8. Capture output periodically; nudge only from live evidence.
9. Run/verify full validation and smoke tests before PR.
10. Run PM/product-intent review and full code review before PR.
11. Open PR only after verifying clean git state, passing validation, addressed review issues, and required screenshots/videos for UI/flow changes.
12. After PR creation, check jobs/review feedback/mergeability at least once.

Important: AoE owning the session does **not** mean the agent owns final truth. Hermes must still verify artifacts with filesystem, git, tests, and GitHub output before reporting completion.

## Safe Supervision Loop

A robust loop for an existing session:

```bash
aoe session show <id> --json
aoe session capture <id> --lines 120 --strip-ansi
git -C <session-path> status --short
git -C <session-path> diff --stat
```

Then decide:

- If the agent is actively working: wait; do not spam prompts.
- If it is asking for a decision: answer narrowly with the decision and constraints.
- If it is idle before completion: send a continuation prompt grounded in the latest capture and repo state.
- If it claims completion: verify files, git diff, tests, and required artifacts before accepting.
- If it is wedged: capture logs/status, then consider restart/cancel/stop based on session type.

## Cleanup and Archival

Prefer non-destructive lifecycle actions first:

```bash
aoe session snooze <id> 2h
aoe session archive <id>
aoe session archive <id> --no-kill
aoe session unarchive <id>
aoe session stop <id>
```

Remove a session record only after confirming no needed work is left:

```bash
aoe remove <id>
```

For AoE-managed worktrees:

```bash
aoe remove <id> --delete-worktree
```

Only delete the branch when explicitly intended:

```bash
aoe remove <id> --delete-worktree --delete-branch
```

Avoid `--force` unless the user explicitly confirms it or you have inspected and preserved the work. Aaron prefers safe deletion practices; never use broad destructive cleanup as a shortcut.

Clean orphaned worktrees:

```bash
aoe worktree cleanup
```

## Common Recipes

### Create a pi session in an AoE worktree

```bash
aoe add /Users/anichols/code/heddle \
  --title "nod-123-short-name" \
  --group "heddle" \
  --tool pi \
  --worktree nod-123-short-name \
  --new-branch \
  --base-branch develop \
  --launch
```

Then:

```bash
aoe send nod-123-short-name "Read repo guidance and create the canonical plan only. Do not change code."
aoe session capture nod-123-short-name --lines 100 --strip-ansi
```

### Resume an existing session by title

```bash
aoe list --json
aoe session show "session title" --json
aoe session capture "session title" --lines 120 --strip-ansi
aoe send "session title" "Continue from the current state. Do not redo completed stages; first state what remains."
```

### Use JSON to pick exact sessions

```bash
aoe list --json | jq -r '.[] | [.id, .title, .tool, .path, .profile] | @tsv'
```

### Check whether any session needs attention

```bash
aoe status --json
aoe status --verbose
```

### Debug AoE itself

```bash
aoe logs
aoe log-level --get
aoe log-level debug
```

## Common Pitfalls

1. **Creating duplicate sessions in the wrong profile.** Check `aoe list --all --json` or known profile `main` before creating a new session that may already exist.

2. **Treating AoE capture as proof of completion.** Capture is evidence, not verification. Verify on disk and with git/test commands.

3. **Prompting without checking current state.** Always capture/show status first; stale prompts cause duplicated stages and conflicting work.

4. **Bypassing repo workflow gates.** AoE manages sessions; it does not waive plan review, validation, PM review, code review, PR requirements, or post-PR follow-up.

5. **Overusing `--yolo`, `--trust-hooks`, `--force`, or branch deletion.** These are high-authority choices. Use deliberately and explain when necessary.

6. **Confusing terminal-view and ACP sessions.** Use `aoe send`/`aoe session capture` for terminal-view sessions; use `aoe acp prompt/history/tail/approve` for ACP structured sessions.

7. **Reviving a session accidentally.** `aoe send` revives by default. Use `--no-revive` if restart would be unsafe or misleading.

8. **Using raw tmux as the primary controller.** If AoE owns the session, prefer AoE lifecycle/capture/send commands. Use raw tmux only as a fallback diagnosis layer.

## Verification Checklist

- [ ] `aoe` is installed and `aoe agents` shows the requested tool installed.
- [ ] Correct AoE profile selected; existing sessions checked before creating a new one.
- [ ] Session ID/title/path/tool verified with `aoe session show --json`.
- [ ] For repo work, path/worktree/branch/base branch are correct.
- [ ] Latest session output captured before sending steering.
- [ ] Prompts include current stage, authority boundaries, and what not to redo.
- [ ] Claimed plan/code/test/PR artifacts verified outside the agent session.
- [ ] Cleanup uses AoE lifecycle commands and avoids destructive branch/worktree deletion unless explicitly intended.
