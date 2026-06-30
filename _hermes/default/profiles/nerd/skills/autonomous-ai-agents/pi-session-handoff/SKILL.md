---
name: pi-session-handoff
description: Recover and continue a Pi coding-agent session for a specific repo, then produce a concise handoff summary for another surface like Discord.
---

# Pi session handoff

Use this when a user says they started a Pi session in a code repo and wants to continue it from Hermes or relay its current state into chat.

## When to use
- User references a Pi session in a repo (not a Context Core `ccore session` object).
- You need to recover the latest session file for a repo path.
- You need a concise continuation summary without reading a huge JSONL file directly.

## Core distinction
Do **not** confuse:
- `ccore session ...` = Context Core resumable work sessions
- `pi` session files under `~/.pi/agent/sessions/...` = coding-agent conversation history

If the user says "in the ccore code repo" or similar, they usually mean the Pi coding session associated with the repo path.

## Recovery workflow
1. Confirm the repo path.
   - Typical example: `~/code/ccore`
2. Find the Pi session directory slug for that repo.
   - Pi stores sessions under `~/.pi/agent/sessions/` with repo paths encoded like:
     - `~/code/ccore` -> `~/.pi/agent/sessions/--Users-<user>-code-ccore--/`
3. List candidate session files and sort by modification time to find the newest session.
   ```bash
   python3 - <<'PY'
   from pathlib import Path
   root=Path.home()/'.pi/agent/sessions/--Users-anichols-code-ccore--'
   files=[p for p in root.rglob('*.jsonl') if p.is_file()]
   files=sorted(files,key=lambda p:p.stat().st_mtime, reverse=True)
   for p in files[:10]:
       print(f"{p.stat().st_mtime:.0f}\t{p}")
   PY
   ```
4. If needed, inspect only the tail of the JSONL with paginated file reads. Avoid loading the whole file if it is large.
5. Prefer asking Pi itself for a handoff summary instead of manually parsing large transcript blobs:
   ```bash
   cd ~/code/ccore && pi --session "$HOME/.pi/agent/sessions/--Users-anichols-code-ccore--/<session>.jsonl" -p "Summarize the current session state for handoff into a Discord thread. Include: goal, what was inspected, files changed, exact plan file written, and the recommended next concrete implementation steps. Keep it under 250 words."
   ```
6. Report back with:
   - exact session path
   - current goal
   - files inspected/changed
   - next recommended implementation steps

## Useful diagnostics
Check Pi CLI usage if needed:
```bash
pi --help
```

Check default session directory:
```bash
printenv PI_CODING_AGENT_DIR || echo "$HOME/.pi/agent"
```

Find repo-related sessions quickly:
```bash
find "$HOME/.pi/agent" -type f \( -name "*.jsonl" -o -name "*.json" \) 2>/dev/null | grep -i ccore
```

## Live bridge pattern for chat-thread relay
If the user wants Hermes to act as a live relay between chat and a running Pi TUI session:

1. Start Pi in the repo with the recovered session file in a background PTY process.
   ```bash
   pi --session "$HOME/.pi/agent/sessions/--Users-<user>-code-<repo>--/<session>.jsonl"
   ```
2. Use Hermes `process` tooling as the bridge.
3. Prefer `process.write` followed by a raw carriage return (`"\r"`) to send user input into Pi.
   - In practice, `process.submit` may not reliably trigger Pi TUI command handling for slash commands.
   - `process.write` + `"\r"` worked reliably for forwarding commands like:
     - `/review:plan thoughts/plans/...md`
4. Poll/wait/log the process to relay Pi output back into chat.
5. Tell the user this is a bridged relay, not a native Discord↔Pi socket integration, so some interactive/TUI-heavy flows may still be quirky.

### Bridge startup cautions
- Avoid `watch_patterns` with generic words like `ready`, `error`, or `tool`.
  - Pi output often contains these words in normal status text.
  - Generic watch patterns can create false positive system notifications in chat that look like errors.
- If you add a bridge note message to Pi, do it once and keep it short.

## Pitfalls
- Do not assume the latest `ccore session list` result is related; that is a different system.
- Do not read huge Pi JSONL files in full unless necessary; use paginated reads or let Pi summarize its own session.
- Repo slug names are path-encoded; verify the actual session directory before hardcoding.
- For live relays, do not assume `process.submit` is equivalent to a real Enter key in Pi's TUI; verify with a simple command or fall back to `process.write` + `"\r"`.
- Do not use broad bridge watch patterns that can spam the user with benign matcher alerts.

## Output pattern
A good response includes:
- "I found the Pi session for `<repo>`"
- exact session file path
- one-paragraph summary of goal and status
- short bullet list of next implementation steps
- if bridging live, the active Hermes process id and a brief note about how messages will be forwarded
