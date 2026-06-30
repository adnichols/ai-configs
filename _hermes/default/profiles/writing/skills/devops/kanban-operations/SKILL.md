---
name: kanban-operations
description: "Operate the Hermes Kanban board: orchestrate multi-agent work, manage worker lifecycles, and run Codex lanes."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [kanban, multi-agent, orchestration, worker, codex, collaboration]
    related_skills: [hermes-agent]
---

# Kanban Operations

The Hermes Kanban system is a durable SQLite board for multi-profile collaboration. This skill covers three roles:

1. **Orchestrator** — decompose goals and route work through the board
2. **Worker** — execute assigned tasks and write clean handoffs
3. **Codex Lane** — optionally delegate implementation to Codex CLI while Hermes keeps ownership

## Orchestrator — Decomposition Playbook

> The core worker lifecycle is auto-injected into every kanban worker's system prompt as `KANBAN_GUIDANCE`. This section is the deeper playbook when you're specifically playing the orchestrator role.

### Step 0: Discover Profiles
Before fanning out, discover which profiles exist:
```bash
hermes profile list
```
The dispatcher silently fails to spawn unknown assignees — cards sit in `ready` forever.

### When to Use the Board
Create Kanban tasks when any of these are true:
- Multiple specialists needed
- Work should survive a crash/restart
- Human-in-the-loop expected
- Multiple subtasks can run in parallel
- Review/iteration expected
- Audit trail matters

### Anti-Temptation Rules
- **Do not execute the work yourself.** Create a Kanban task and assign it.
- **Split multi-lane requests before creating cards.** One card per independent workstream.
- **Link only true data dependencies** with `parents=[...]` in `kanban_create`.
- **Never invent profile names** — ask the user which profile to use.

### Decomposition Pattern
```python
t1 = kanban_create(title="research: ...", assignee="<profile-A>", body="...")
t2 = kanban_create(title="research: ...", assignee="<profile-A>", body="...")
t3 = kanban_create(title="synthesize", assignee="<profile-B>", body="...", parents=[t1, t2])
```

### Goal-Mode Cards
For open-ended tasks, pass `goal_mode=True`:
```python
kanban_create(
    title="Translate full docs site to French",
    assignee="<translator-profile>",
    goal_mode=True,
    goal_max_turns=15,
)
```
An auxiliary judge re-evaluates after each turn against the card's acceptance criteria.

## Worker — Pitfalls and Examples

### Workspace Handling
| Kind | Behavior |
|---|---|
| `scratch` | Fresh tmp dir; read/write freely |
| `dir:<path>` | Shared persistent directory |
| `worktree` | Git worktree; run `git worktree add` if `.git` missing |

### Good Handoff Shapes
**Coding task:**
```python
kanban_complete(
    summary="shipped rate limiter — token bucket, 14 tests pass",
    metadata={"changed_files": [...], "tests_passed": 14},
)
```

**Review-required task:**
```python
kanban_comment(body=json.dumps({"changed_files": [...], "tests_passed": 14}))
kanban_block(reason="review-required: rate limiter shipped, needs eyes on key choice")
```

### Do NOT
- Call `delegate_task` as a substitute for `kanban_create`
- Call `clarify` — you're headless; use `kanban_comment` + `kanban_block`
- Modify files outside `$HERMES_KANBAN_WORKSPACE` unless instructed
- Complete a task you didn't finish — block it instead

### Retry Diagnostics
Check `kanban_show` runs for prior outcomes:
- `timed_out` → chunk the work
- `crashed` → reduce memory footprint
- `spawn_failed` → profile config issue; ask human via `kanban_block`

## Codex Lane

Use Codex CLI as an isolated implementation lane while Hermes keeps ownership.

### When to Use
- Coding/refactor/test task with clear acceptance criteria
- Bounded diff evaluable in one run
- Repo can be isolated in a git worktree
- Hermes can run tests after Codex exits

### Ownership Rules
1. Hermes owns the Kanban lifecycle — Codex must never call `kanban_complete`
2. Hermes owns final acceptance — treat Codex diffs as untrusted patches
3. Hermes owns test execution — repeat verification with canonical wrappers
4. Hermes owns safety and cleanup

### Worktree Pattern
```bash
SAFE_TASK="$(printf '%s' "$HERMES_KANBAN_TASK" | tr -cd '[:alnum:]_-')"
BRANCH="codex/${SAFE_TASK}/$(date -u +%Y%m%d%H%M%S)"
WORKTREE="/tmp/${SAFE_TASK}-codex-lane"
git worktree add -b "$BRANCH" "$WORKTREE" "$BASE"
```

### Monitoring
```python
result = terminal(command="codex exec --full-auto '$(cat /tmp/codex_prompt.md)'",
                  workdir=WORKTREE, background=True, pty=True, notify_on_complete=True)
process(action="poll", session_id=result["session_id"])
```

### Reconciliation Checklist
- [ ] `git status --short` shows only expected files
- [ ] `git diff` reviewed by Hermes
- [ ] No secrets or unrelated artifacts
- [ ] Hermes ran canonical tests independently
- [ ] `metadata.codex_lane` follows schema
