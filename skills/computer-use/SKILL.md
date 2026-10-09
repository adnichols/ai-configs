---
name: computer-use
description: >-
  Drive a native GUI via cua-driver when the user requests GUI interaction or
  no purpose-built CLI, API, or connector can perform the requested operation.
  Check those interfaces before inspecting the UI, even if the operation is
  represented by a button or tab. Use for clicks, typing, scrolling, dragging,
  accessibility actions, browser windows, and webviews when GUI control is needed.
---

# Computer Use

Identify the requested result before opening an app. Check its purpose-built
CLI, API, connector, or skill first, even when the result appears in the UI.
Do not inspect the UI merely to decide whether a purpose-built interface
exists. If the user specifies a CLI, stay with it and report any unavailable
action. Use CUA only when the user requests GUI interaction or no semantic
interface can perform the result.

This skill is a routing name. Immediately load and follow the `cua-driver`
skill with the same task, app, and arguments. Do not use Orca's computer-use CLI.

Default transport is the `cua-driver` CLI:

```text
cua-driver <tool-name> '<JSON-args>'
```

If the cua-driver skill pack is missing, run `cua-driver skills install` and
then follow the `cua-driver` skill. If the binary is missing, report that and
stop. Do not fall through to `orca`, `orca-dev`, or `orca-ide`.

## Browser work

- Do not use Paseo's built-in browser (the `browser_*` tools) for browser work.
- On Linux, `browser_prepare` with `strategy: existing_profile` brings the target window to the foreground and injects global input (XTest) to open the remote-debugging setup page. It does this on a reconnect that then fails, and its schema has no background-only option. Never use it in a background-only or unattended workflow.
- Prefer an isolated driver-owned profile (`isolated_new` or `isolated_named`) or the native background action ladder.
- Use existing-profile attachment only when the user has explicitly authorized foreground takeover.
- Never retry a failed `browser_prepare` on the user's desktop.
- `route: global_input` on a native click is a transport label, not proof of foreground. Take a fresh state and screenshot to verify the effect. An unverifiable effect is not success.
- Typed browser grants can disappear about 5 minutes after preparation (cause unconfirmed, possibly session idle cleanup). Re-check the binding before each typed action. Do not recover by rerunning `browser_prepare`.
