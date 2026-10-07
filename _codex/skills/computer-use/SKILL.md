---
name: computer-use
description: Use cua-driver for native desktop GUI interaction only when requested or when no purpose-built CLI, API, or connector can perform the operation. Check those interfaces before inspecting the UI.
---

Identify the requested result before opening an app. Check its purpose-built CLI, API, connector, or skill first, even when the result appears in the UI. Do not inspect the UI merely to decide whether a purpose-built interface exists. If the user specifies a CLI, stay with it and report any unavailable action. Use CUA only when the user requests GUI interaction or no semantic interface can perform the result. Then read the installed cua-driver skill and use its actual tool contract.

For browser tasks, honor the user's browser and the active session's preferred browser controller. Use Playwright for requested web test automation. Do not load several browser-control skills for the same operation or switch an existing session without a task-specific reason.

## Browser work

- Do not use Paseo's built-in browser (the `browser_*` tools) for browser work.
- On Linux, `browser_prepare` with `strategy: existing_profile` brings the target window to the foreground and injects global input (XTest) to open the remote-debugging setup page. It does this on a reconnect that then fails, and its schema has no background-only option. Never use it in a background-only or unattended workflow.
- Prefer an isolated driver-owned profile (`isolated_new` or `isolated_named`) or the native background action ladder.
- Use existing-profile attachment only when the user has explicitly authorized foreground takeover.
- Never retry a failed `browser_prepare` on the user's desktop.
- `route: global_input` on a native click is a transport label, not proof of foreground. Take a fresh state and screenshot to verify the effect. An unverifiable effect is not success.
- Typed browser grants can disappear about 5 minutes after preparation (cause unconfirmed, possibly session idle cleanup). Re-check the binding before each typed action. Do not recover by rerunning `browser_prepare`.
