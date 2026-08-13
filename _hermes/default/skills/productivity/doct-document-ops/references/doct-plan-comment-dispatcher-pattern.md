# Durable Doct plan comment dispatcher pattern

Use this reference when a Doct HTML plan listener exists but comments remain pending or the listener is not taking action.

## Failure mode

A script-only cron listener can appear healthy while doing no useful work if it:

- polls `doct-agent plans queue list`,
- prints a notification for new queue items,
- stores thread IDs in `seen_item_keys`, and
- exits without calling `doct-agent plans agent next`, editing/updating the plan, replying, acking, and resolving.

A second unsafe variant is starting `doct-agent plans listen --jsonl` as a generic Hermes background process without a real supervisor/dispatcher consuming each JSONL claim event. That command can remain alive and claim work while no agent worker is launched, leaving threads leased until expiry. A live PID is not evidence that an agent is connected.

That is notification/event-consumption-only behavior, not a complete comment listener. Doct queue state is authoritative; local seen-key state is diagnostic only.

## Startup gate

Do not report a listener as ready unless one of these complete paths is observable:

- a bounded `doct-agent plans agent next --wait --timeout <n> --json` child owned by a dispatcher that launches a Hermes worker for every returned claim; or
- `plans listen --jsonl` under a real supervisor whose dispatcher/worker handoff is proven by process state and a routed smoke test.

For Aaron's macOS plans that must stay monitored until archival, prefer the document-scoped LaunchAgent dispatcher pattern. Verify the supervisor PID, its current `agent next --wait` child, source-path handoff, and empty queue. Never substitute a raw `plans listen --jsonl` process launched from `terminal(background=true)`.

## Correct pattern

A quiet-by-default listener should be a script-only cron gate plus a real action path:

1. Poll exactly one `<workspace-id>/<document-id>` with `doct-agent plans queue list`.
2. If no pending items exist, print nothing.
3. If pending items exist, acquire a state/lock file so scheduled ticks do not overlap.
4. Either process directly or launch a bounded worker with `doct-document-ops` loaded.
5. The worker must claim one item at a time with `doct-agent plans agent next` and capture `threadId` plus `claim.id`.
6. Read current plan state with `doct-agent plans show` before editing.
7. Apply the smallest plan source change that addresses the comment; update through `doct-agent plans update`.
8. Add a visible reply, then `ack`, then `resolve`. If the item cannot be handled safely, `release` it with a reason before the lease expires.
9. Recheck the queue and continue until the exact document has no pending items.

## Verification checklist

- The listener script compiles or passes its local syntax check.
- Manual script run with an empty queue exits `0` and prints no stdout/stderr.
- `doct-agent plans queue list ... --json` returns `{"items":[]}` after processing.
- `doct-agent plans show ... --json` verifies expected plan changes and nonzero anchors.
- The scheduled job or background process succeeds once after the update.
