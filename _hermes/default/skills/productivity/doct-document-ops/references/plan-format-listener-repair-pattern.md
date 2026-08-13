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
5. Start or verify a document-specific listener/watcher before final response.
6. If a wrong text-doc URL was already shared, delete or clearly supersede it so there is one canonical URL.

## Final response checklist

When handing the plan back, include:

- canonical Doct URL,
- document ID,
- workspace ID,
- proof `plans show` succeeded, such as anchor target count or render id,
- current queue item count,
- listener job/process id and last verified status.

Do not say or imply a listener is running unless you have verified a process, cron job, or harness background command for that exact document ID.
