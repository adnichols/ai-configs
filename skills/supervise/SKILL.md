---
name: supervise
description: Attach a trajectory-guarding supervisor to a worker coding agent in a labeled sibling Herdr tab when the operator explicitly asks for supervision. It is never started automatically by plan execution (run-plan / dev:run). The supervisor guards outcome aim and expansion reasoning; it never fences investigation.
---

# Supervise

A supervisor is an optional second Pi session in a labeled sibling Herdr tab that watches a worker agent execute a plan. Launch it only when the operator explicitly requests supervision; plan-execution workflows must not start it by default. The worker owns technical judgment; the supervisor owns trajectory: is the work still aimed at the promised outcome, is expansion reasoned and logged, and are the plan's triggered contract inventory, acceptance/BDD proof, residual-risk disclosure, and decisions/deviations real. Its charter lives in `supervisor-prompt.md` beside this file.

## Launch

From the worker's session (or by the operator), with the worker's pane ID, workspace ID, worktree, and agent name known:

```bash
# If the workspace id is not already available, read result.pane.workspace_id:
herdr pane get <worker-pane>
herdr tab create --workspace <workspace-id> --label "supervise · <worker-name>" \
  --cwd <worktree> --no-focus
# Read result.root_pane.pane_id and result.tab.tab_id from the JSON response, then:
herdr agent start supervisor-<worker-name> --kind pi --pane <new-root-pane-id> --timeout 45000 -- \
  --provider openai-codex --model gpt-5.6-sol --thinking high \
  --append-system-prompt ~/.agents/skills/supervise/supervisor-prompt.md \
  --tools read,bash
# --append-system-prompt takes a file path and loads its contents; --system-prompt takes
# literal text and multi-line text cannot be encoded through herdr's argv passing.
herdr agent prompt supervisor-<worker-name> \
  "Worker agent: <worker-name>. Plan: <plan-path>. Begin supervision." \
  --wait --timeout 60000
```

Record the supervisor's agent name, tab ID, and root pane ID in the plan's session metadata (expansion log header). Keep the agent name as the prompt/read target; the tab label is for human orientation. If no supervisor can be started, record `SUPERVISOR: none — <reason>` there instead; the pre-PR review surfaces that to the human.

Tool posture: `--tools read,bash` removes Pi's structured edit/write tools. Bash can still mutate, so repository non-mutation is prompt-enforced, not technically enforced — the charter forbids it and the dry run verifies the refusal.

## Checkpoints (worker side)

Two checkpoints block: **plan-ready** (before implementation starts) and **pre-PR** (before push/PR). For each, the worker:

1. Generates a fresh unique request id (any short unique string).
2. Runs `herdr agent prompt supervisor-<worker-name> "CHECKPOINT REQUEST[<id>]: <plan-ready|pre-pr> — plan <path>" --wait --timeout 600000`.
3. Reads the supervisor transcript (`herdr agent read supervisor-<worker-name> --source recent-unwrapped`) and accepts **only** a receipt bearing the same id: `CHECKPOINT[<id>]: PROCEED` or `CHECKPOINT[<id>]: REVISE — <items>`. A receipt with any other id is stale — ignore it.
4. If the wait returned without a matching receipt (Herdr's prompt wait is state-based, and an in-flight phase ping can end the wait early), loop: `herdr agent wait supervisor-<worker-name> --until idle --until done --timeout 60000` → reread → check for `CHECKPOINT[<id>]` — until the matching receipt appears or 10 minutes have elapsed since the original request.
5. On `PROCEED`: continue. On `REVISE`: address the items or record a reasoned disagreement in the expansion log, then submit a fresh request with a **new id**. On deadline expiry with no matching receipt: proceed, recording `SUPERVISOR: timeout at <checkpoint>[<id>]` in the expansion log.

Mid-build, at each phase boundary, the worker sends a fire-and-forget ping — `herdr agent prompt supervisor-<worker-name> "PHASE COMPLETE: <n> — plan <path>"` with **no `--wait`** — and acknowledges any resulting `SUPERVISOR NUDGE:` in its next expansion-log entry. Nudges are advisory and never block.

## Shutdown

Orderly: the caller that created the tab closes it as the final wrap-up step of the worker session, so the supervisor does not outlive the work. If the worker crashes, no further wakes occur and the idle supervisor persists until the operator closes the tab — crashed-worker cleanup is an operator responsibility (an idle session costs nothing meanwhile). A supervisor whose wake finds the worker gone ends its own session.

An operator ship or stand-down directive for the worker's stream is also a shutdown signal: the supervisor discards its queued prompts and pending demands for that stream, acknowledges, and treats its supervision as complete. Stale supervision must never outlive an operator decision.
