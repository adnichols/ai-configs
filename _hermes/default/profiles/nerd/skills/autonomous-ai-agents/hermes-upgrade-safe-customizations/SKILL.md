---
name: hermes-upgrade-safe-customizations
description: Build Hermes custom features in upgrade-safe user space instead of patching core Hermes files.
version: 1.0.0
author: Hermes Agent
license: MIT
---

# Hermes upgrade-safe customizations

Use this whenever a user wants Hermes behavior changed but does **not** want the change to be lost on Hermes upgrade.

## Core rule
Do **not** modify Hermes core repo files for user-specific features unless the user explicitly wants an upstream code change.

Prefer extension points under `~/.hermes/`:
- `~/.hermes/hooks/` for gateway/runtime patching at startup
- `~/.hermes/plugins/` for reusable plugin modules with `plugin.yaml`
- `~/.hermes/skills/` for prompt-level workflows
- config in `~/.hermes/config.yaml`

## Decision framework
1. **Prompt behavior only?**
   - Use a skill.
2. **Tooling or reusable Python integration?**
   - Use a plugin in `~/.hermes/plugins/`.
3. **Gateway event interception / startup monkey-patch / message routing?**
   - Use a hook in `~/.hermes/hooks/`.
4. **Broad product improvement intended to survive as upstream code?**
   - Only then consider changing Hermes core.

## Hook pattern for upgrade-safe gateway extensions
Use hooks when you need to alter gateway behavior without editing `gateway/run.py`.

### Layout
```text
~/.hermes/hooks/<hook-name>/
  HOOK.yaml
  handler.py
  README.md
```

### Minimal `HOOK.yaml`
```yaml
name: my-hook
description: My upgrade-safe Hermes gateway extension
events:
  - gateway:startup
```

### Handler pattern
- Load at `gateway:startup`
- Import `gateway.run`
- Save original method(s)
- Monkey-patch `GatewayRunner` methods
- Keep patch idempotent with a module-global `_PATCHED` flag

Skeleton:
```python
_PATCHED = False
_ORIGINAL_HANDLE_MESSAGE = None

async def _patched_handle_message(self, event):
    # custom intercept here
    return await _ORIGINAL_HANDLE_MESSAGE(self, event)


def _apply_patch():
    global _PATCHED, _ORIGINAL_HANDLE_MESSAGE
    if _PATCHED:
        return
    import gateway.run as gateway_run
    _ORIGINAL_HANDLE_MESSAGE = gateway_run.GatewayRunner._handle_message
    gateway_run.GatewayRunner._handle_message = _patched_handle_message
    _PATCHED = True


async def handle(event_type, context):
    if event_type == "gateway:startup":
        _apply_patch()
```

## Pi passthrough example pattern
For thread-local interactive Pi bridging:
- patch `GatewayRunner._handle_message`
- intercept `/pi ...` commands before normal agent handling
- maintain module-global bridge state keyed by gateway session key
- spawn Pi with `tools.process_registry.process_registry.spawn(..., use_pty=True)`
- relay output by polling process output in an asyncio task
- intercept `/STOP` and send `"\x1b"` via `write_stdin`
- forward all other thread messages with `submit_stdin`

## Verification checklist
1. Confirm no core Hermes files were modified.
   ```bash
   git diff -- gateway/run.py gateway/platforms/base.py hermes_cli/commands.py
   ```
2. Syntax-check the external hook/plugin.
   ```bash
   python -m py_compile ~/.hermes/hooks/<hook-name>/handler.py
   ```
3. Restart gateway so the hook loads.
4. Run a focused behavioral test against the external extension.
5. Add a `README.md` in the hook/plugin directory describing behavior and location.

## Pitfalls
- Hooks load on gateway startup, so changes usually require a gateway restart.
- Keep monkey-patches idempotent; gateway startup paths may run more than once in tests/restarts.
- Store long-lived custom state in the external module, not Hermes core objects.
- If importing a hook manually in tests, insert the module into `sys.modules` before execution when needed.
- Prompt-level skills cannot disable Hermes interpretation of incoming messages; transport-layer passthrough needs a hook/plugin.

## Preferred response to user requests
If the user asks for a custom Hermes feature and cares about persistence across upgrades, state the plan explicitly:
- implement externally under `~/.hermes/...`
- avoid modifying Hermes core
- document restart/activation requirements
