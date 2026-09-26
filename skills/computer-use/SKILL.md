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
