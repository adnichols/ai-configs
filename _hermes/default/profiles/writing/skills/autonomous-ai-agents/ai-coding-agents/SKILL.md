---
name: ai-coding-agents
description: "Delegate coding tasks to autonomous AI CLI tools (Claude Code, OpenAI Codex, OpenCode) with proper setup, scoping, and safety."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [claude-code, codex, opencode, ai-coding, delegation, multi-agent]
    related_skills: [kanban-operations]
---

# AI Coding Agents

Hermes can delegate complex coding tasks to three autonomous CLI tools. All three follow the same high-level pattern: **describe the goal → delegate → review the diff → run tests**. Differences are in CLI quirks, output modes, and model support.

## Claude Code

```bash
claude --help           # Full flag list
claude "refactor utils.py to use pathlib"
claude --output-format stream "review PR 42"
```

### Setup
- Install: `brew install claude-code`
- No explicit auth required if ANTHROPIC_API_KEY or default credentials exist

### Modes
- **Prompt mode:** `claude "do X"` — one-shot
- **Interactive mode:** `claude` — REPL
- **Script mode:** `claude -p "do X"` — non-interactive

### Post-Delegation Verification
Claude Code operates directly on the filesystem. After it exits:
1. `git diff` — check what actually changed
2. `git status` — verify no unintended files were touched
3. Run tests — Claude's claim of passing tests may be stale

## OpenAI Codex

```bash
codex --help
codex "review PR 42"           # One-shot
codex "implement feature X"    # Implementation
codex --output-format diff     # Structured review output
```

### Setup
- Install: `npm install -g @openai/codex`
- Auth: `codex auth` (API key via OPENAI_API_KEY env var)

### Output Formats
- `stream` — real-time (default)
- `diff` — structured patch
- `json` — machine-readable

### Non-Interactive / CI
```bash
codex "review PR 42" --output-format json --no-interaction
```

## OpenCode

```bash
opencode --help
opencode "refactor utils.py to use pathlib"
opencode --output-format diff "review PR 42"
```

### Setup
- Install: `npm install -g opencode`
- Auth: `opencode auth` (supports API keys from multiple providers)

### Multi-Provider Support
OpenCode can route to different providers via config:
```yaml
# ~/.config/opencode/opencode.yaml
default:
  provider: openai
  model: gpt-4.1
```

### Non-Interactive
```bash
opencode "do X" --no-interaction
```

## Common Post-Delegation Checklist

| Step | Command |
|---|---|
| Inspect diff | `git diff --stat && git diff` |
| Verify tests | `pytest` / `cargo test` / `npm test` (Hermes runs, not the agent) |
| Check for secrets | `git diff | grep -E 'api.?key\|token\|secret'` |
| Review new files | `git status --short` |
| Commit or revert | `git add -p` / `git checkout -- <file>` |

## When to Delegate vs. Do Inline

**Delegate when:**
- Task is self-contained (one file/module)
- Acceptance criteria are clear
- Test suite is comprehensive
- Hermes will review the diff afterward

**Do inline when:**
- Task spans architecture decisions
- User expects conversational iteration
- Safety critical (no unreviewed code changes)
- Agent lacks project context

## Worktree Isolation

For maximum safety, always run AI coding agents in a disposable git worktree:
```bash
WORKTREE="/tmp/codex-$(date +%s)"
git worktree add -b codex-lane "$WORKTREE"
cd "$WORKTREE"
codex "implement feature X"
# Review diff, cherry-pick, or discard
git worktree remove "$WORKTREE"
```
