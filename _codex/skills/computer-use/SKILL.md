---
name: computer-use
description: Compatibility alias for cua-driver when operating native desktop applications.
---

For native application interaction, read the installed cua-driver skill and use its actual tool contract. Prefer a purpose-built connector or CLI when it covers the requested operation.

For browser tasks, honor the user's browser and the active session's preferred browser controller. Use Playwright for requested web test automation. Do not load several browser-control skills for the same operation or switch an existing session without a task-specific reason.
