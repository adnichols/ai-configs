# Plan format/listener repair pattern

Use this reference when an Aaron-facing plan was accidentally created as a plain Doct text document, or when a plan URL was shared without a listener.

## Durable lesson

For Aaron-facing implementation plans, the successful path is:

1. Write semantic HTML or Markdoc source with stable section IDs.
2. Register it with `doct-agent plans register`, not `doct-agent documents create` or `documents replace-body`.
3. Verify the artifact with `doct-agent plans show --id <document-id> --json`.
   - Evidence to look for: `documentId`, `workspaceId`, `documentVersionId`, render/html version IDs, and nonzero `anchorTargets`.
   - `documents get` can prove a document exists, but it does not prove it is the commentable plan-review surface.
4. Check queue once with `doct-agent plans queue list --workspace-id <workspace-id> --document-id <document-id> --json`.
5. Start or verify a document-specific listener/watcher before final response.
6. If a wrong text-doc URL was already shared, delete or clearly supersede it so Aaron has one canonical URL.

## Hermes listener pattern

For a quiet-by-default Hermes listener, prefer a script-only cron job:

- schedule: `every 1m` or another user-specified review cadence,
- `no_agent=true`,
- `deliver=origin` when the current Discord thread should receive comment notifications,
- stdout empty when no actionable comments exist,
- stdout non-empty only for new actionable queue items or listener failures,
- persist seen queue item/thread IDs under `~/.hermes/state/` to avoid repeat spam.

The script should poll exactly one `<workspace-id>/<document-id>` pair unless intentionally responsible for a whole workspace. It should include the canonical Doct plan URL in any notification.

## Final response checklist

When handing the plan back, include:

- canonical Doct URL,
- document ID,
- workspace ID,
- proof `plans show` succeeded, such as anchor target count or render id,
- current queue item count,
- listener job/process id and last verified status.

Do not say or imply a listener is running unless you have verified a process/cron/job for that exact document ID.
