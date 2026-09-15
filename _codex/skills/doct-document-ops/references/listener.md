## Start and supervise the comment worker automatically

Codex planning-only completion takes precedence over ongoing monitoring instructions below: once the published plan is execution-ready with no pending feedback, drain acknowledged work and release only this task's listener/monitor ownership using its documented stop procedure. Preserve durable server state and other owners. Return the URL and readiness evidence without waiting for unrequested implementation.

A registered reviewer-facing plan is not ready for browser-review handoff until existing routed work has been processed and the durable comment listener is both running and observable by the supervising agent. Do this automatically after registration or a monitoring handoff; do not wait for the user to separately ask you to start the listener. The exceptions are an explicit registration-only request or a host that cannot provide a safe wake path, which must be reported precisely.

Treat the returned `listenerInstructions.listenerCommand` as the live command contract. The CLI listener claims/dequeues routed items and emits one JSONL `plan_comment_dispatch` per claim; it does not edit the plan or acknowledge/resolve the claim for you.

After registration:

1. Run `doct-agent plans lifecycle --state active` before draining/listening when lifecycle is not already active.
2. Leave the plan in its registration/default board column, normally `backlog`, unless the user explicitly requested a board move. Registration and browser-review handoff do not mean implementation is underway.
3. Drain existing routed work with `doct-agent plans agent next ... --no-wait --json`. If the response contains a claim, process that claim immediately, then call `agent next --no-wait` again. Stop only on the CLI's empty envelope. Never use a blind shell loop that discards claimed JSON; a claim that is dequeued but not handled remains leased and can be hidden until redelivery.
4. Start the exact returned `listenerInstructions.listenerCommand` (`doct-agent plans listen ... --jsonl`) using the host-specific supervision path below. This durable listener uses bounded request timeouts and retries transient 408/429/5xx responses.
5. Verify both halves before browser handoff: the process is alive, and every emitted `plan_comment_dispatch` can re-activate or remain connected to the agent that will handle it. A running PID alone is insufficient.
6. When the listener emits a dispatch, treat that event as the already-claimed work item. Process exactly that claim, then reply/ack/resolve/release with the returned identifiers and commands. Do not call `agent next` to re-claim the same event. Keep the listener running for later work.
7. A routed work item is created by the browser's agent action or by `doct-agent plans comments add --submit-action agent ...`. A generic routed item commonly has `submitAction: "agent"` with `agentRoute.targetScope: "plan-review"` and no requested skill; it is plan feedback, not an execution-ready request. Doct's **Request execution-ready review** action currently adds `agentRoute.requestedSkill: "plan-reviewer-execution-ready"`; an explicit `submitAction: "execution-ready"` is equivalent when returned by the service. Ordinary conversation comments use `submitAction: "conversation"`, return `queueState: "none"`, and intentionally do not wake the listener.
8. If a claim cannot be completed before its lease expires, release it with a reason. Do not let a listener silently accumulate claimed-but-unhandled work.

### Host supervision matrix

- **Codex desktop/app:** Start the listener with a persistent `exec_command`/terminal session and capture its session id. Keep the plan-review task active; wait for output with `write_stdin` (or the equivalent terminal poll), process each dispatch immediately, and periodically inspect `doct-agent plans board list` for this document's assignment. Do not return a final handoff while Codex owns pre-execution monitoring. If a native recurring automation or thread-wake tool is available and the requested monitoring scope authorizes it, that may carry the same watchdog responsibility without holding the interactive turn open. A background exec process alone does **not** prove that Codex will start a new turn after the current task returns.
- **Pi:** Start the listener through `process` with `alertOnFailure: true`, `alertOnKill: true`, and `logWatches: [{"pattern":"\\\"type\\\":\\\"plan_comment_dispatch\\\"","stream":"stdout","repeat":true}]`. The repeating watch wakes Pi for every dispatch; the failure/kill alerts create recovery turns.
- **Other wake-capable harnesses:** Use their durable background-process primitive plus a repeating stdout match for `"type":"plan_comment_dispatch"`, and alerts for listener exit/failure.
- **Claude Code:** This IS a wake-capable harness — supervise, do not opt out. Start the listener with Bash `run_in_background: true` (writing JSONL to a log file), then arm a **persistent `Monitor`** whose command tails that log filtered to `"type":"plan_comment_dispatch"` **plus** error/exit signatures (`error|Error|unauthorized|exit`). Each matching stdout line wakes a fresh turn with the already-claimed dispatch; `run_in_background` independently re-invokes you if the listener process exits, so a crash surfaces instead of going silent. That pair is durable supervision. Do **not** report `LISTENER_WAKE_UNAVAILABLE` from a Claude Code session that has `Monitor` and background Bash available — claiming you cannot supervise here is a false limitation.
- **Terminal-only agents (no background-process or per-output wake primitive):** A detached PID or `nohup` is not autonomous supervision. Keep the interactive task attached and polling, install an explicitly authorized scheduler/worker, or report `LISTENER_WAKE_UNAVAILABLE`.

### Pre-execution ownership and stop condition

The agent that publishes or opens the plan for browser review owns the pre-execution listener until one of these observable conditions occurs:

1. An execution workflow moves the exact document to the visible `in_progress` board column, or repo/service configuration explicitly identifies an equivalent execution-start column.
2. The plan lifecycle is no longer `active`, the document is deleted/archived, or the listener exits because target validation is no longer valid.
3. The user explicitly cancels monitoring or requested registration-only work.

For Codex, treat this as an ongoing-task terminal condition:

1. Keep the listener exec session attached and poll it for dispatches.
2. Periodically run `doct-agent plans board list --workspace-id <workspace-id> --json` and locate the exact document card; do not infer execution from a local progress checkbox.
3. If the listener exits before an ownership boundary, inspect lifecycle/auth/board state and restart the exact registration-provided command automatically when the plan is still active and pre-execution.
4. When `in_progress` is observed, finish or release any current claim, drain the exact document queue once, interrupt the pre-execution listener cleanly, and report that listener ownership passed to the execution workflow.
5. When a Codex task is resumed after interruption, inspect board state, lifecycle, queue, and listener health first; restart monitoring automatically if the plan is still active and not yet `in_progress`.

If the listener command itself cannot start or fails lifecycle/auth/scope validation, report `LISTENER_START_BLOCKED`. If the user requires the Codex task to return before execution begins and no native automation/thread-wake path exists, report `LISTENER_WAKE_UNAVAILABLE` rather than pretending a detached listener is sufficient. Queue inspection and manual claims are recovery paths, not evidence of durable supervision.

Durable listener example:

```bash
doct-agent plans listen \
  --base-url https://doct.nodaste.com \
  --workspace-id <workspace-id> \
  --document-id <document-id> \
  --jsonl
```

Use the exact `listenerInstructions.listenerCommand` returned by registration when it differs from this example.

`plans agent next --wait --json` is a one-shot diagnostic/recovery path only. It depends on the HTTP request staying open until the server-side wait deadline and is more vulnerable to platform/proxy timeouts than `plans listen --jsonl`. `plans watch` is only source sync/debug visibility and does not replace the comment listener.

## Monitor and process plan comments/actions

Use Doct plan listener and queue commands, not the legacy `plan-review agent next` flow.

The normal path is automatic startup drain followed by the durable listener immediately after registration. Use queue inspection and one-shot claims for startup drain, recovery, or manual processing; do not wait for a second user prompt before performing the startup drain.

Inspect pending work:

```bash
doct-agent plans queue list \
  --base-url https://doct.nodaste.com \
  --workspace-id <workspace-id> \
  --document-id <document-id> \
  --json
```

Claim the next applicable item for this agent during drain/recovery:

```bash
doct-agent plans agent next \
  --base-url https://doct.nodaste.com \
  --workspace-id <workspace-id> \
  --document-id <document-id> \
  --no-wait \
  --json
```

For cross-document adapter workers, use `--all` only when that worker is intentionally responsible for all active plan comments/actions in the workspace.

A listener-delivered or manually claimed item should provide a thread id, claim id, reviewer context, action metadata, selected node/selector context, and returned ack/resolve/release commands. A listener event is already claimed; a manual drain response is the claim. Process one claim at a time:

1. Read the full local plan file and, if needed, `doct-agent plans show --id <document-id> --json`.
2. Use the selected node ID, selector, heading path, quoted text, and reviewer body.
3. Classify the item as `READINESS_BLOCKER`, `PRODUCT_QUESTION`, `OPTIONAL_CLARITY`, `OUT_OF_SCOPE_FOLLOW_UP`, `DISAGREE_REPO_EVIDENCE`, `EXECUTION_READY_REQUEST`, or `BUILD_REQUEST`.

   Treat an item as `EXECUTION_READY_REQUEST` only when its routing metadata has `agentRoute.requestedSkill: "plan-reviewer-execution-ready"` or an explicit `submitAction: "execution-ready"`. A generic `submitAction: "agent"` claim without that requested skill is feedback only: apply or disposition it, then keep the plan in browser review. Never start PM or active-harness readiness review merely because the first feedback comment arrived or the listener is quiet.
4. Make the smallest plan change that addresses in-scope feedback without widening scope.
5. Update Doct with `doct-agent plans update` after edits.
6. Add a visible reply when useful:
   ```bash
   doct-agent plans reply \
     --base-url https://doct.nodaste.com \
     --document-id <document-id> \
     --workspace-id <workspace-id> \
     --thread-id <thread-id> \
     --body "Updated the plan." \
     --json
   ```
7. Ack when the item has been incorporated or deliberately dispositioned:
   ```bash
   doct-agent plans ack \
     --base-url https://doct.nodaste.com \
     --workspace-id <workspace-id> \
     --thread-id <thread-id> \
     --claim-id <claim-id> \
     --summary "Integrated reviewer feedback on phase boundaries" \
     --json
   ```
8. Resolve only when the reviewer-visible issue is complete:
   ```bash
   doct-agent plans resolve \
     --base-url https://doct.nodaste.com \
     --workspace-id <workspace-id> \
     --thread-id <thread-id> \
     --claim-id <claim-id> \
     --summary "Plan now includes the missing verification gate" \
     --json
   ```

If you cannot act before the claim should be released:

```bash
doct-agent plans release \
  --base-url https://doct.nodaste.com \
  --workspace-id <workspace-id> \
  --thread-id <thread-id> \
  --claim-id <claim-id> \
  --reason "Cannot complete before handoff" \
  --json
```
