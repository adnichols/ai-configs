---
name: doct-document-ops
description: "Read or manage Doct documents, comments, and published HTML plans using doct-agent."
---

Read [the Codex runtime contract](../adn-mode/references/codex-runtime.md) once per task.

# Doct operations

Use doct-agent for Doct URLs, documents, comments, and published plans. Resolve the exact target and requested operation before writing. A read request does not authorize publication, edits, or starting a listener.

Read [connection and target guidance](references/connection.md), then only the operation needed:

- Read or edit an ordinary document or its metadata: [document commands](references/documents.md).
- Create, publish, retitle, or update a reviewer-facing HTML plan: [plan publication](references/plans.md).
- Start, resume, or supervise a plan listener, or process plan feedback: [listener and feedback](references/listener.md).

Plan publication includes listener setup unless explicitly registration-only: read the listener guide before browser-review handoff. Update a plan's source before claiming the registered version is current. Keep matching document title, HTML title, and h1. Plans are HTML-only; Markdown/text publication applies only to an explicit text-document request.

Use [doct-agent commands](references/doct-agent-commands.md) for a specific command's details. Existing repair references are for matching failures, not routine prerequisites.

For planning-only work, a published execution-ready plan with no pending feedback completes the task. Drain acknowledged work, then release only this task's listener/monitor ownership using its documented stop procedure. Preserve durable server state and other owners. Return the review URL and readiness evidence; do not wait for unrequested implementation.
