---
description: Execute a single-file plan with resumable progress tracking
argument-hint: '<slug | existing-plan-path>'
---

# Run Plan (Single File)

Execute a single plan document (spec + phases + progress) in a straightforward, single-agent way:

- Follow the plan, but keep implementation flexibility.
- Track progress by updating `## Progress` in the plan file.

## Inputs

`$ARGUMENTS` may be:

- A slug
- A direct path to a plan file in the repo's active plan format

## Process

### 0) Autopilot Rules

- Execute continuously; do not pause between phases.
- Do not stop after a status update (e.g., "I'm starting Phase 1" or "gathering context").
- Every response must either (a) take the next concrete action by actually invoking a tool (read/search/edit/run) or updating the plan file, or (b) ask for user input due to an unresolvable decision. Narration is not an action.
- If unsure, investigate and retry until evidence supports a decision; do not ask the user just for uncertainty.
- Use `question` only when a decision between viable options requires user input due to insufficient evidence.

Unresolvable decision examples:

- Conflicting requirements in the plan with no priority rule.
- A security/billing/production-risk choice that materially changes behavior and is not specified.
- Multiple viable interpretations that change external behavior and cannot be resolved by existing code patterns.

### 0.5) Attach Supervisor

Before implementation, attach a trajectory-guarding supervisor per `skills/supervise/SKILL.md`: a second reactive session in an adjacent Herdr pane that owns trajectory and budget, never technical judgment, and never fences investigation or testing.

```bash
herdr pane split <worker-pane> --direction right --no-focus
# read result.pane.pane_id from the JSON response, then:
herdr agent start supervisor-<worker-name> --kind pi --pane <new-pane-id> --timeout 45000 -- \
  --provider openai-codex --model gpt-5.6-sol --thinking high \
  --append-system-prompt ~/.agents/skills/supervise/supervisor-prompt.md \
  --tools read,bash
herdr agent prompt supervisor-<worker-name> \
  "Worker agent: <worker-name>. Plan: <plan-path>. Begin supervision." \
  --wait --timeout 60000
```

Record the supervisor's agent name and pane ID in the plan's expansion-log header, or record `SUPERVISOR: none — <reason>` there if none can be started. Two checkpoints block, using a correlated-id handshake: **plan-ready** before the first code change and **pre-PR** before any push/PR handoff. The worker generates a fresh unique request id and runs `herdr agent prompt supervisor-<worker-name> "CHECKPOINT REQUEST[<id>]: <plan-ready|pre-pr> — plan <path>" --wait --timeout 600000`, then reads the transcript and accepts **only** a receipt with the same id: `CHECKPOINT[<id>]: PROCEED` or `CHECKPOINT[<id>]: REVISE — <items>`. If the wait returns without a matching receipt, loop `herdr agent wait supervisor-<worker-name> --until idle --until done --timeout 60000` → reread until it appears or 10 minutes elapse from the original request; on deadline expiry, proceed and record `SUPERVISOR: timeout at <checkpoint>[<id>]`. At each phase boundary, send a fire-and-forget `herdr agent prompt supervisor-<worker-name> "PHASE COMPLETE: <n> — plan <path>"` (no `--wait`) and acknowledge any returned nudge in the next expansion-log entry. As the final wrap-up step, the caller that created the pane closes it.

### 1) Resolve Plan Path

Resolve to:

- `plan_path`

Rules:

- If `$ARGUMENTS` starts with `@`, treat it as a workspace-relative path and strip the leading `@`.
- If `$ARGUMENTS` is a path to an existing file, use it as `plan_path`.
- If `$ARGUMENTS` is a slug, resolve it using repo-local active plan guidance. Do not infer a markdown path. If repo guidance does not define slug-to-plan-path resolution, ask for the explicit existing plan path and stop.

Legacy migration support (do not delete legacy files):

- Only migrate legacy bundles when repo-local guidance explicitly allows migration to the repo's active plan format.

### 2) Read Plan

Read `plan_path` fully.

Immediately begin execution:

- Identify the first unchecked item in `## Progress`.
- Find the corresponding phase section and start implementing it right away; do not pause to recap the plan.

### 3) Execute Phase-by-Phase

For each phase in order (as tracked by `## Progress`):

1. Implement the phase as written.
2. Run the phase `### Verify` steps.
3. After the phase is complete (including verification), immediately flip its checkbox from `- [ ]` to `- [x]` in `## Progress`.
4. If implementation required a decision or revealed a constraint, append a structured entry to `## Decisions / Deviations Log` in the plan file.

#### Autonomy / Do Not Pause

- Proceed autonomously through phases.
- If you are not blocked, do not hand control back to the user; take the next concrete action (run commands, edit files, update progress) until you either finish or hit an unresolvable decision.
- Do not stop after announcing intent, listing next steps, or completing "context gathering".
- Only stop to ask the user when you hit an unresolvable decision that cannot be answered from the plan or codebase.

When you must ask:

- Ask exactly one targeted question (batch sub-choices into that one question).
- Provide a recommended default and say what would change with each option.

When you do not need to ask:

- Choose the most conservative, plan-aligned default.
- Log the decision in `## Decisions / Deviations Log` with evidence (files/commands) and proceed.

#### Tests Policy

- You MAY add/update tests when behavior changes.
- You MAY refactor for testability.
- You MUST NOT change product code merely to satisfy a failing test if acceptance criteria + observed behavior indicate the code is correct.
  - In that case, fix the test or update the test assumptions (and log the decision).

### 4) Completion

When all items in `## Progress` are complete:

- Ensure the plan file reflects completion accurately.
- Run any verification commands listed in the plan's `Verification Strategy` and/or phase `### Verify` sections.
