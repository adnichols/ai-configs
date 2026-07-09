# Durable Doct plan comment dispatcher pattern

Use this reference when a Doct HTML/Markdoc plan listener exists but comments remain pending or the listener is not taking action.

## Failure mode

A listener can appear healthy while doing no useful work in two common ways:

- A script-only cron polls `doct-agent plans queue list`, prints notifications, stores thread IDs in `seen_item_keys`, and exits without claiming/editing/replying/resolving.
- A durable `doct-agent plans listen --jsonl` process claims work and prints `plan_comment_dispatch`, but the harness was not configured to activate the supervising agent from that output.

Both are incomplete supervision. In Pi, start the durable listener with `alertOnFailure: true`, `alertOnKill: true`, and a repeating stdout `logWatches` match for `"type":"plan_comment_dispatch"`. Without `repeat: true`, only the first claim wakes Pi; without the alerts, a crash or external termination can leave the plan silently unwatched. Doct queue state is authoritative; local seen-key state and process health are diagnostic only.

## Correct pattern

A quiet-by-default listener should be a script-only cron gate plus a real action path:

1. Poll exactly one `<workspace-id>/<document-id>` with `doct-agent plans queue list`.
2. If no pending items exist, print nothing.
3. If pending items exist, acquire a state/lock file so scheduled ticks do not overlap.
4. Either process directly or launch a bounded worker with `doct-document-ops` loaded. For a Pi durable listener, configure `alertOnFailure: true`, `alertOnKill: true`, and `logWatches: [{"pattern":"\\\"type\\\":\\\"plan_comment_dispatch\\\"","stream":"stdout","repeat":true}]` at process start so each claim, listener failure, or external termination creates an agent turn.
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
- For Pi, the process registration includes failure/kill alerts and a repeating `plan_comment_dispatch` stdout watch; merely observing a running PID does not satisfy listener readiness.
