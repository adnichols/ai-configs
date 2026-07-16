# Durable Doct plan comment dispatcher pattern

Use this reference when a Doct HTML/Markdoc plan listener exists but comments remain pending or the listener is not taking action.

## Failure mode

A listener can appear healthy while doing no useful work in three common ways:

- A script-only cron polls `doct-agent plans queue list`, prints notifications, stores thread IDs in `seen_item_keys`, and exits without claiming/editing/replying/resolving.
- A durable `doct-agent plans listen --jsonl` process claims work and prints `plan_comment_dispatch`, but the harness was not configured to activate the supervising agent from that output.
- A startup drain calls `plans agent next --no-wait` in a shell loop and discards non-empty JSON, leaving claims leased but unprocessed until redelivery.

All are incomplete supervision. `plans listen` and `plans agent next` both claim/dequeue work; their JSON must reach an agent that completes or releases the claim. Doct queue state is authoritative; local seen-key state and process health are diagnostic only.

## Correct pattern

A quiet-by-default worker should use the native listener plus a real action path:

1. Scope work to exactly one `<workspace-id>/<document-id>`.
2. At startup, call `doct-agent plans agent next ... --no-wait --json` once. If it returns a claim, process it fully before calling again; stop on the empty envelope.
3. Start the exact registration-provided `doct-agent plans listen ... --jsonl` command.
4. Connect every `plan_comment_dispatch` to the current agent or a wake-capable worker. Treat the dispatch as already claimed; do not re-claim it.
5. Read current plan state with `doct-agent plans show` before editing.
6. Apply the smallest plan source change that addresses the comment; update through `doct-agent plans update`.
7. Add a visible reply when useful, then `ack`, then `resolve`. If the item cannot be handled safely, `release` it with a reason before the lease expires.
8. Keep the listener alive for future routed work and verify the exact document queue after each processing burst.

## Host-specific supervision

- **Codex desktop/app:** run the listener in a persistent exec/terminal session, keep its session id, and keep the plan-review task active. Poll with `write_stdin` or the equivalent, process dispatches immediately, and periodically inspect `plans board list` for the exact document. If the listener exits while the plan is active and still pre-execution, restart it automatically. Do not return final until the document enters `in_progress`, its lifecycle ends, or the user cancels, unless a verified native automation/thread-wake path owns the same watchdog responsibility.
- **Pi:** configure `alertOnFailure: true`, `alertOnKill: true`, and repeating `logWatches` for `"type":"plan_comment_dispatch"`. Without `repeat: true`, only the first claim wakes Pi.
- **Other wake-capable harnesses:** use their repeating stdout-event wake primitive and listener exit/failure alerts.
- **Terminal-only agents:** detached processes are diagnostic only unless an explicitly authorized scheduler launches a real agent worker.

If no durable wake primitive exists, a quiet scheduled fallback may inspect `plans queue list` and launch a bounded worker, but queue polling alone is never sufficient. The worker must claim and complete one item at a time, prevent overlapping ticks, and continue until the exact document is empty.

## Ownership handoff

The pre-execution listener owner stops only after observing the exact document in `in_progress` (or a repo-configured equivalent), a non-active lifecycle/deleted target, or explicit cancellation. On the execution transition, complete or release the current claim, drain once, stop the pre-execution listener, and record that the execution workflow now owns subsequent Doct coordination. On resume, inspect board, lifecycle, queue, and listener state before deciding whether to restart.

## Verification checklist

- The listener script compiles or passes its local syntax check.
- Manual script run with an empty queue exits `0` and prints no stdout/stderr.
- `doct-agent plans queue list ... --json` returns `{"items":[]}` after processing.
- `doct-agent plans show ... --json` verifies expected plan changes and nonzero anchors.
- The background process is alive and its stdout is connected to a real agent wake/active polling path.
- For Codex, either the task remains attached and polling until the ownership handoff, or a verified native automation/thread-wake path owns the watchdog; otherwise the result says `LISTENER_WAKE_UNAVAILABLE`.
- For Pi, the process registration includes failure/kill alerts and a repeating `plan_comment_dispatch` stdout watch; merely observing a running PID does not satisfy listener readiness.
