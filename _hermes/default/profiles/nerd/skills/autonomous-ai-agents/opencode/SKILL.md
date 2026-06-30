---
name: opencode
description: "Delegate coding to OpenCode CLI (features, PR review)."
version: 1.2.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [Coding-Agent, OpenCode, Autonomous, Refactoring, Code-Review]
    related_skills: [claude-code, codex, hermes-agent, hermes-opencode-linear-build, opencode-http-coding-workflow]
---

# OpenCode CLI

Use [OpenCode](https://opencode.ai) as an autonomous coding worker orchestrated by Hermes terminal/process tools. OpenCode is a provider-agnostic, open-source AI coding agent with a TUI and CLI.

## When to Use

- User explicitly asks to use OpenCode
- You want an external coding agent to implement/refactor/review code
- You need long-running coding sessions with progress checks
- You want parallel task execution in isolated workdirs/worktrees

## Prerequisites

- OpenCode installed: `npm i -g opencode-ai@latest` or `brew install anomalyco/tap/opencode`
- Auth configured: `opencode auth login` or set provider env vars (OPENROUTER_API_KEY, etc.)
- Verify: `opencode auth list` should show at least one provider
- Git repository for code tasks (recommended)
- `pty=true` for interactive TUI sessions

## Binary Resolution (Important)

Shell environments may resolve different OpenCode binaries. If behavior differs between your terminal and Hermes, check:

```
terminal(command="which -a opencode")
terminal(command="opencode --version")
```

If needed, pin an explicit binary path:

```
terminal(command="$HOME/.opencode/bin/opencode run '...'", workdir="~/project", pty=true)
```

## One-Shot Tasks

Use `opencode run` for bounded, non-interactive tasks:

```
terminal(command="opencode run 'Add retry logic to API calls and update tests'", workdir="~/project")
```

## HTTP API / Server Control

When the user has `opencode server` running (commonly `http://localhost:63333`), Hermes can operate OpenCode sessions directly with `curl` via terminal. Prefer read/list/status endpoints first, and only create/send prompts when the user has asked to run a coding session.

For Aaron's Linear-backed OpenCode issue workflow, do not use generic manual workdir/worktree patterns from this skill. Load `hermes-opencode-linear-build` and launch OpenCode's `/cmd:linear-build-workspace <ISSUE_KEY> <BASE_REF>` command. OpenCode owns workspace creation and build orchestration; Hermes only monitors liveness and terminal status.

Readiness checks:

```
terminal(command="curl -sS http://localhost:63333/global/health")
terminal(command="curl -sS http://localhost:63333/session")
```

Useful endpoints observed in OpenCode 1.14.x:

| Endpoint | Use |
|---|---|
| `GET /global/health` | health/version, e.g. `{\"healthy\":true,\"version\":\"1.14.x\"}` |
| `GET /session` | list sessions; supports query params such as `directory`, `workspace`, `limit`, `search`, `archived` |
| `POST /session` | create a session; JSON body may include `title`, `agent`, `model`, `permission`, `workspaceID`, `parentID`; in OpenCode 1.14.x `permission` is an array of objects like `{\"permission\":\"bash\",\"action\":\"allow\",\"pattern\":\"*\"}`, not a map |
| `GET /session/{sessionID}` | session metadata |
| `GET /session/{sessionID}/message` | list messages for a session; supports `limit` and `before` |
| `POST /session/{sessionID}/message` | send a prompt; JSON body can include `parts`, `agent`, `model`, `variant`, `tools`, `system`, `noReply` |
| `POST /session/{sessionID}/prompt_async` | fire-and-monitor prompt launch; OpenCode 1.14 may return `204 No Content` on success, so do not retry via `/message` after a 204 |
| `GET /event` | workspace-scoped SSE event stream |
| `GET /global/event` | global SSE event stream |
| `POST /session/{sessionID}/permissions/{permissionID}` | answer permission prompts |
| `GET /config/providers` | provider/model availability; output may include secrets, so never paste raw output back to the user |

Example create + prompt shape (use an explicit repo directory/workspace query when appropriate):

```
terminal(command="curl -sS -X POST 'http://localhost:63333/session?directory=/absolute/repo/path-url-encoded' -H 'Content-Type: application/json' -d '{\"title\":\"Hermes task\",\"agent\":\"build\"}'")
terminal(command="curl -sS -X POST 'http://localhost:63333/session/$SESSION_ID/prompt_async?directory=/absolute/repo/path-url-encoded' -H 'Content-Type: application/json' -d '{\"parts\":[{\"type\":\"text\",\"text\":\"Inspect the repo and summarize test commands. Do not edit files.\"}],\"agent\":\"build\"}'")
```

Observed OpenCode 1.14.40 quirk: `POST /session` may reject richer bodies like `{"permission":{"edit":"allow",...}}` with HTTP 400 even though simple `{title, agent}` succeeds. Start with the minimal body, then send the work prompt via `/prompt_async`. A successful `/prompt_async` can return an empty response body; treat HTTP 2xx as the success signal and poll `/session/status`.

Pitfalls:
- `/doc` may expose a partial OpenAPI document; the frontend bundle can reveal additional session/message endpoints.
- `/config` and `/config/providers` may include credential-bearing or sensitive provider metadata; summarize only non-secret facts.
- Creating sessions and posting prompts are side effects and may spend model tokens. Do not do that for a smoke test unless the user explicitly asks.
- For coding workflows, pass/choose the correct repo `directory`/`workspace` so OpenCode does not operate from `$HOME`.


Attach context files with `-f`:

```
terminal(command="opencode run 'Review this config for security issues' -f config.yaml -f .env.example", workdir="~/project")
```

Show model thinking with `--thinking`:

```
terminal(command="opencode run 'Debug why tests fail in CI' --thinking", workdir="~/project")
```

Force a specific model:

```
terminal(command="opencode run 'Refactor auth module' --model openrouter/anthropic/claude-sonnet-4", workdir="~/project")
```

## Interactive Sessions (Background)

For iterative work requiring multiple exchanges, start the TUI in background:

```
terminal(command="opencode", workdir="~/project", background=true, pty=true)
# Returns session_id

# Send a prompt
process(action="submit", session_id="<id>", data="Implement OAuth refresh flow and add tests")

# Monitor progress
process(action="poll", session_id="<id>")
process(action="log", session_id="<id>")

# Send follow-up input
process(action="submit", session_id="<id>", data="Now add error handling for token expiry")

# Exit cleanly — Ctrl+C
process(action="write", session_id="<id>", data="\x03")
# Or just kill the process
process(action="kill", session_id="<id>")
```

**Important:** Do NOT use `/exit` — it is not a valid OpenCode command and will open an agent selector dialog instead. Use Ctrl+C (`\x03`) or `process(action="kill")` to exit.

### TUI Keybindings

| Key | Action |
|-----|--------|
| `Enter` | Submit message (press twice if needed) |
| `Tab` | Switch between agents (build/plan) |
| `Ctrl+P` | Open command palette |
| `Ctrl+X L` | Switch session |
| `Ctrl+X M` | Switch model |
| `Ctrl+X N` | New session |
| `Ctrl+X E` | Open editor |
| `Ctrl+C` | Exit OpenCode |

### Resuming Sessions

After exiting, OpenCode prints a session ID. Resume with:

```
terminal(command="opencode -c", workdir="~/project", background=true, pty=true)  # Continue last session
terminal(command="opencode -s ses_abc123", workdir="~/project", background=true, pty=true)  # Specific session
```

## Common Flags

| Flag | Use |
|------|-----|
| `run 'prompt'` | One-shot execution and exit |
| `--continue` / `-c` | Continue the last OpenCode session |
| `--session <id>` / `-s` | Continue a specific session |
| `--agent <name>` | Choose OpenCode agent (build or plan) |
| `--model provider/model` | Force specific model |
| `--format json` | Machine-readable output/events |
| `--file <path>` / `-f` | Attach file(s) to the message |
| `--thinking` | Show model thinking blocks |
| `--variant <level>` | Reasoning effort (high, max, minimal) |
| `--title <name>` | Name the session |
| `--attach <url>` | Connect to a running opencode server |

## Procedure

1. Verify tool readiness:
   - `terminal(command="opencode --version")`
   - `terminal(command="opencode auth list")`
2. For bounded tasks, use `opencode run '...'` (no pty needed).
3. For iterative tasks, start `opencode` with `background=true, pty=true`.
4. Monitor long tasks with `process(action="poll"|"log")`.
5. If OpenCode asks for input, respond via `process(action="submit", ...)`.
6. Exit with `process(action="write", data="\x03")` or `process(action="kill")`.
7. Summarize file changes, test results, and next steps back to user.

## PR Review Workflow

OpenCode has a built-in PR command:

```
terminal(command="opencode pr 42", workdir="~/project", pty=true)
```

Or review in a temporary clone for isolation:

```
terminal(command="REVIEW=$(mktemp -d) && git clone https://github.com/user/repo.git $REVIEW && cd $REVIEW && opencode run 'Review this PR vs main. Report bugs, security risks, test gaps, and style issues.' -f $(git diff origin/main --name-only | head -20 | tr '\n' ' ')", pty=true)
```

## Parallel Work Pattern

Use separate workdirs/worktrees to avoid collisions:

```
terminal(command="opencode run 'Fix issue #101 and commit'", workdir="/tmp/issue-101", background=true, pty=true)
terminal(command="opencode run 'Add parser regression tests and commit'", workdir="/tmp/issue-102", background=true, pty=true)
process(action="list")
```

## Session & Cost Management

List past sessions:

```
terminal(command="opencode session list")
```

Check token usage and costs:

```
terminal(command="opencode stats")
terminal(command="opencode stats --days 7 --models anthropic/claude-sonnet-4")
```

## Pitfalls

- Interactive `opencode` (TUI) sessions require `pty=true`. The `opencode run` command does NOT need pty.
- `/exit` is NOT a valid command — it opens an agent selector. Use Ctrl+C to exit the TUI.
- PATH mismatch can select the wrong OpenCode binary/model config.
- If OpenCode appears stuck, inspect logs before killing:
  - `process(action="log", session_id="<id>")`
- Avoid sharing one working directory across parallel OpenCode sessions.
- Enter may need to be pressed twice to submit in the TUI (once to finalize text, once to send).

## Verification

Smoke test:

```
terminal(command="opencode run 'Respond with exactly: OPENCODE_SMOKE_OK'")
```

Success criteria:
- Output includes `OPENCODE_SMOKE_OK`
- Command exits without provider/model errors
- For code tasks: expected files changed and tests pass

## Rules

1. Prefer `opencode run` for one-shot automation — it's simpler and doesn't need pty.
2. Use interactive background mode only when iteration is needed.
3. Always scope OpenCode sessions to a single repo/workdir.
4. For long tasks, provide progress updates from `process` logs.
5. Report concrete outcomes (files changed, tests, remaining risks).
6. Exit interactive sessions with Ctrl+C or kill, never `/exit`.
