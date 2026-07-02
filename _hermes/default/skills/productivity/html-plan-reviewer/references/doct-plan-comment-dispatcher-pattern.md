# Durable Doct plan comment dispatcher pattern

Use this reference when a Doct HTML/Markdoc plan listener exists but comments remain pending or Aaron says the listener is not taking action.

## Failure mode observed

A script-only cron listener can appear healthy while doing no useful work if it:

- polls `doct-agent plans queue list`,
- prints a notification for new queue items,
- stores thread IDs in `seen_item_keys`, and
- exits without calling `doct-agent plans agent next`, editing/updating the plan, replying, acking, and resolving.

That is notification-only behavior, not a comment listener. It creates the worst state: cron is green, comments are pending, and the user must intervene.

## Correct pattern

A quiet-by-default listener should be a script-only cron gate plus a real action path:

1. Poll exactly one `<workspace-id>/<document-id>` with `doct-agent plans queue list`.
2. If no pending items exist, print nothing.
3. If pending items exist, acquire a state/lock file under `~/.hermes/state/` so the next 1-minute tick does not overlap.
4. Either process directly or launch a bounded Hermes worker with `html-plan-reviewer` and `doct-document-ops` loaded.
5. The worker must claim one item at a time with `doct-agent plans agent next` and capture `threadId` plus `claim.id`.
6. Read current plan state with `doct-agent plans show` before editing.
7. Apply the smallest plan source change that addresses the comment; update through `doct-agent plans update`.
8. Add a visible reply, then `ack`, then `resolve`. If the item cannot be handled safely, `release` it with a reason before the lease expires.
9. Recheck the queue and continue until the exact document has no pending items.

## Cron design

- `no_agent=true` for the polling script.
- `deliver=origin` is acceptable for worker summaries/failures, but stdout should stay empty when there is no work.
- Non-empty stdout should be reserved for processed-work summaries, unresolved blockers, or listener errors.
- Do not persist `seen_item_keys` as the action source of truth. Doct queue state is authoritative. If legacy `seen_item_keys` remain in state, treat them as diagnostic only.

## Verification checklist

- `python3 -m py_compile <script>` passes.
- Manual script run with an empty queue exits `0` and prints no stdout/stderr.
- `doct-agent plans queue list ... --json` returns `{"items":[]}` after processing.
- `doct-agent plans show ... --json` verifies expected plan changes and nonzero anchors.
- `cronjob(action='run', job_id=...)` succeeds once after the update.
- If the script is managed in `ai-configs`, run `scripts/hermes_config_sync.py export`/`verify` or update manifest hashes intentionally, then commit/push only the relevant managed files.
