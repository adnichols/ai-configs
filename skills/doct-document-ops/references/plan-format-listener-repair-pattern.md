# Plan format/listener repair pattern

Use this reference when a reviewer-facing plan was accidentally created as a plain Doct text document, or when a plan URL was shared without a listener.

## Durable lesson

For reviewer-facing implementation plans, the successful path is:

1. Write semantic HTML source with stable section IDs.
2. Register it with `doct-agent plans register`, not `doct-agent documents create` or `documents replace-body`.
3. Verify the artifact with `doct-agent plans show --id <document-id> --json`.
   - Evidence to look for: `documentId`, `workspaceId`, `documentVersionId`, render/html version IDs, and nonzero `anchorTargets`.
   - `documents get` can prove a document exists, but it does not prove it is the commentable plan-review surface.
4. Check queue once with `doct-agent plans queue list --workspace-id <workspace-id> --document-id <document-id> --json`.
5. Process any startup claims, then start or verify a document-specific listener before final response. `plans watch` is source sync and does not satisfy this step.
6. If a wrong text-doc URL was already shared, delete or clearly supersede it so there is one canonical URL.

## Final response checklist

When handing the plan back, include:

- canonical Doct URL,
- document ID,
- workspace ID,
- proof `plans show` succeeded, such as anchor target count or render id,
- current queue item count,
- listener job/process/session id, last verified status, and the host wake mechanism (Codex active terminal/automation, Pi repeating process watch, or another verified equivalent).

Do not say or imply comments will be handled automatically unless you have verified both a live process for that exact document ID and a host path that re-activates or remains attached to the processing agent. On Codex, a surviving exec session without an active poll or native wake path is `LISTENER_WAKE_UNAVAILABLE`, not complete supervision.
