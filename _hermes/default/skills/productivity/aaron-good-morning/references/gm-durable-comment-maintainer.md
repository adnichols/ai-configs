# Good Morning durable plan-review comment maintainer

Session-derived pattern for Aaron's `/gm` HTML plan workflow.

## Problem

A `plan-review agent next <planId> --wait --json` listener is not durable by itself. It exits as soon as it claims one comment. If the surrounding Hermes session/cron run has already completed, no agent remains to process/ack the claim or restart the listener, so later comments can sit pending.

## Durable pattern

For Good Morning plans, treat the passive `--wait` listener as best-effort only. Add a recurring watchdog/goal-like cron job that:

1. Finds active DailyGM plans (`DailyGM/*-gm.html`) and skips archived plans.
2. Runs `plan-review agent next <planId> --url http://mbp.braid-python.ts.net:4317 --no-wait --json` to claim pending comments.
3. Processes the claimed comment immediately: read the full HTML artifact, make the requested update or investigation, then `ack` and `resolve` with the claim/comment IDs.
4. Drains until empty or until a reasonable work cap is reached.
5. Verifies with `plan-review queue list --plan-id <planId> --json`.
6. Optionally starts a single passive `--wait` listener if none is already running, but does not depend on it for durability.
7. Responds `[SILENT]` when no active DailyGM plan or pending/comment work exists.

Recommended cadence: every 5 minutes while a GM plan is active.

## Delivery pitfall

For cron delivery to Discord home, do not use bare `deliver: "discord"` when the job was created from a Discord thread. Bare `discord` can resolve to the saved origin thread. Use an explicit channel target such as:

```text
discord:1492535022811480126
```

Use `discord:<channel_id>:<thread_id>` only when targeting an existing thread.

## Listener architecture update (2026-06-25)

The original GM listener was blocking: it claimed one comment, ran `hermes chat -Q` synchronously to process it, then returned to `agent next`. This failed operationally because one slow or stuck comment could block the entire queue for 10–30 minutes.

The current script at `/Users/anichols/.hermes/scripts/gm_plan_comment_listener.py` is a **dispatcher**:

1. The listener claims a comment via `plan-review agent next <planId> --wait --json`.
2. It writes the claim JSON under `/Users/anichols/.hermes/state/gm-plan-maintainer/runs/`.
3. It starts a detached `hermes chat -Q` worker to process/ack/resolve that exact claim.
4. It records worker metadata under `/Users/anichols/.hermes/state/gm-plan-maintainer/workers/`.
5. It immediately returns to the queue and claims more comments until `GM_PLAN_COMMENT_MAX_WORKERS` is reached.

Default worker cap: `GM_PLAN_COMMENT_MAX_WORKERS=3`.
Default worker timeout: `GM_PLAN_COMMENT_WORKER_TIMEOUT_SECONDS=2700`.

This means seeing multiple `hermes chat ... plan_<id>` processes is expected: they are worker agents, not duplicate listeners. There should still be only one `gm_plan_comment_listener.py <plan_id>` process per active GM plan.

### Diagnosis

```bash
PLAN_ID=<plan_id>
LISTENER_PID=$(cat /Users/anichols/.hermes/state/gm-plan-maintainer/pids/$PLAN_ID.pid)

# Listener plus workers for one GM plan
ps -axo pid,ppid,stat,etime,%cpu,command \
  | grep -E "gm_plan_comment_listener.py $PLAN_ID|hermes chat.*$PLAN_ID|plan-review agent next $PLAN_ID" \
  | grep -v grep

# Worker records
for f in /Users/anichols/.hermes/state/gm-plan-maintainer/workers/${PLAN_ID}_*.json; do
  [ -e "$f" ] && python3 -m json.tool "$f"
done

# Pending queue
plan-review queue list --url http://mbp.braid-python.ts.net:4317 --plan-id $PLAN_ID --json
```

### What is normal now

- One `gm_plan_comment_listener.py <plan_id>` dispatcher.
- Up to 3 `hermes chat -Q ... <plan_id>` worker agents.
- Pending comments may remain while all worker slots are full; they should be claimed as workers finish.
- The dispatcher log should show `dispatched worker pid=... comment=...` rather than blocking on `processing comment=...` for a long time.

### If workers hang

Kill only the stuck worker PID if it is idle/stuck past the timeout window. Do not kill the dispatcher unless the dispatcher itself is wedged or duplicated.

```bash
kill <worker_pid>
# Escalate only if it does not exit.
kill -9 <worker_pid>
```

The dispatcher will clean dead worker records and continue. If a claim expired or a worker was interrupted before ack/resolve, the comment may reappear and be claimed again.

### If duplicate listeners appear

There should be one dispatcher per GM plan. If multiple `gm_plan_comment_listener.py <same_plan_id>` processes exist, keep the newest PID from `pids/<plan_id>.pid` and terminate the older duplicate listener processes. Do not disable supervisor cron `544dbd1c6d84`; it is responsible for keeping the dispatcher alive.
## Current limitation

Hermes cron delivery can post to a fixed Discord channel/thread, but does not currently create a fresh Discord thread per cron run before final delivery. A future `/goal` or delivery-mode integration should tie the GM report message/thread to the durable comment-maintainer lifecycle until the plan is archived.
