---
name: pi-interactive-relay
description: Create an interactive relay between Discord/Gateway and pi coding agent for real-time bidirectional chat. User messages go to pi, pi responses stream back.
command: pi-chat
---

# Pi Interactive Relay

Turn a messaging thread into a real-time extension of pi. Whatever you type gets forwarded to pi, whatever pi outputs streams back.

## Usage

```
/skill:pi-interactive-relay [--repo REPO_NAME] [--model MODEL]
```

Or activated by user request like:
> "I want this thread to be an extension of pi"
> "Relay my messages to pi"
> "Connect this chat to pi"

## Setup Process

### 1. Determine Repository & Model

**Repository:**
- Default: `~/code/ccore` (user's main project)
- Override: `--repo <REPO_NAME>`
- Check: `~/code/<REPO_NAME>/` must exist

**Model:**
- Default: Use pi's default or `gpt-5.4` if specified
- Override: `--model <MODEL>`

### 2. Launch Pi as Background Process

```python
terminal(
    command=f"cd ~/code/{REPO} && pi --model {MODEL} --thinking-level high",
    background=True,
    check_interval=30
)
```

**Store session_id** for subsequent interaction.

### 3. Explain the Interaction Model

```
✅ Pi is now running in background at ~/code/{REPO}
✅ Session: {session_id}

Just type your messages here - they'll be forwarded to pi.
Pi's responses will stream back automatically.

Type "stop" or "exit" to end the session.
```

## Interaction Loop

### User → Pi

When user sends a message:
```python
if message.lower() in ["stop", "exit", "quit", "end"]:
    process(action="kill", session_id=session_id)
    return "Session ended"

process(action="write", session_id=session_id, data=message)
```

### Pi → User

Responses come automatically via `check_interval`. No manual polling needed - Hermes reports background process updates.

**Important:** When `background=true` and `check_interval` is set, Hermes will automatically push pi's output to the chat as it arrives.

## Known Issues & Pitfalls

### 1. Output Not Visible

**Symptom:** Pi is running but no output appears.

**Likely causes:**
- **Line buffering:** Pi may be line-buffered, waiting for newline
- **TTY requirement:** Some pi commands need a TTY for interactive mode
- **Process waiting:** Pi may be waiting for confirmation/acknowledgment

**Workarounds:**
- Try launching pi with `pi --no-repl` or similar non-interactive flag
- Use `unbuffer` or `stdbuf -oL` to force line buffering:
  ```bash
  stdbuf -oL pi --model gpt-5.4 --thinking-level high
  ```

### 2. Wrong Configuration

If user specifies wrong provider/model:
```
process(action="kill", session_id=old_session_id)
# Restart with corrected settings
```

### 3. Command Format

Pi commands like `/review:plan` may need:
- Full path: `/review:plan thoughts/plans/file.md`
- Newline after: Ensure `data` includes `\n`

## Alternative: Synchronous Mode

If background relay doesn't work well:
```
terminal(
    command=f"cd ~/code/{REPO} && pi --model {MODEL} --thinking-level high --prompt '{user_message}'",
    background=False,
    timeout=300
)
```

This runs pi to completion and returns output - simpler but not interactive.

## Example Session

```
User: I want this thread to be an extension of pi for ccore

Hermes: ✅ Pi is now running in background at ~/code/ccore
        Session: proc_a1dd2371d9a7
        Just type your messages here!

User: /review:plan thoughts/plans/fix-auth.md

[pi output streams...]

User: implement the changes

[pi output streams...]

User: stop

Hermes: Session ended. Pi process killed.
```

## Comparison to Other Skills

| Skill | Use Case |
|-------|----------|
| `launch-pi` | One-shot delegation - pi takes over terminal |
| `pi-coding-workflow` | Linear/Sentry issue workflow with PR creation |
| `pi-interactive-relay` | **Bidirectional chat** - Discord↔Pi real-time |

## Files

- Main script: `scripts/relay.sh` (optional wrapper for stdbuf/unbuffer)
