---
name: debugging-and-tracing
description: "Debug applications with language-specific tools: Python (pdb, debugpy), Node.js (--inspect + CDP), and browser DevTools."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [debugging, pdb, debugpy, node, chrome-devtools, tracing]
    related_skills: [systematic-debugging]
---

# Debugging and Tracing

Language-specific debugging recipes. Pair with `systematic-debugging` for the root-cause methodology; this skill is the tool-level mechanics.

## Python: pdb REPL

```python
import pdb; pdb.set_trace()   # Break here
# (Pdb) n  → next line
# (Pdb) s  → step into
# (Pdb) c  → continue
# (Pdb) p variable
# (Pdb) l  → list source
# (Pdb) b 42  → breakpoint at line 42
# (Pdb) q  → quit
```

### Post-Mortem (after exception)
```python
import traceback, sys
traceback.print_exception(*sys.exc_info())
```

## Python: debugpy Remote (DAP)

Attach VS Code / another DAP client to a running Python process.

### Setup
1. Install: `pip install debugpy`
2. Launch script with debugpy server:
```python
import debugpy
debugpy.listen(("0.0.0.0", 5678))
print("Waiting for debugger on port 5678")
debugpy.wait_for_client()  # Blocks here until attached
```
3. VS Code `launch.json`:
```json
{
  "name": "Attach to Remote",
  "type": "python",
  "request": "attach",
  "connect": { "host": "localhost", "port": 5678 }
}
```

### Headless Attach (no VS Code)
```bash
python -m debugpy --listen 5678 --wait-for-client script.py
```

## Node.js: --inspect + Chrome DevTools Protocol

### Local Debug
```bash
node --inspect-brk script.js   # Break on first line
# Open chrome://inspect → click "inspect"
```

### Remote / Docker
```bash
node --inspect=0.0.0.0:9229 script.js
# Port-forward 9229, then chrome://inspect
```

### CDP via CLI (no browser)
```bash
npm install -g ndb
ndb node script.js
```

### Break on Exception
```bash
node --inspect --inspect-brk script.js
# In DevTools, enable "Pause on caught exceptions"
```

### Programmatic Break
```javascript
debugger;  // Breaks here when inspector attached
```

## Node.js: Tracing Async Operations

```bash
node --trace-event-categories node.async_hooks script.js
# Generates trace file; open in chrome://tracing
```

## Common Pitfalls
- `debugpy` blocks forever if client never connects — add a timeout or gate behind env var
- `--inspect-brk` in production exposes the debugger — never bind to `0.0.0.0` in prod
- `pdb.set_trace()` hangs in async/event-loop contexts — use `asyncio` debugger or `breakpoint()` with PYTHONBREAKPOINT
- Chrome DevTools disconnects on process restart — use `--inspect` (not `--inspect-brk`) for persistent attach
