---
name: computer-use
description: Use cua-driver for native desktop GUI interaction only when requested or when no purpose-built CLI, API, or connector can perform the operation. Check those interfaces before inspecting the UI.
---

Identify the requested result before opening an app. Check its purpose-built CLI, API, connector, or skill first, even when the result appears in the UI. Do not inspect the UI merely to decide whether a purpose-built interface exists. If the user specifies a CLI, stay with it and report any unavailable action. Use CUA only when the user requests GUI interaction or no semantic interface can perform the result. Then read the installed cua-driver skill and use its actual tool contract.

For browser tasks, honor the user's browser and the active session's preferred browser controller. Use Playwright for requested web test automation. Do not load several browser-control skills for the same operation or switch an existing session without a task-specific reason.
