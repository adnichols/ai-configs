---
name: pi-tmux-event-bridge
description: Use when running pi inside tmux and you need grounded worker-pane detection, phase-progress events, explicit tmux-state observation, or automatic next-message injection in Hermes CLI sessions. Prefer this whenever pi work is visible in tmux and you want a watcher instead of manual pane polling.
---

# Pi tmux event bridge

This plugin provides:
- a plugin tool: `pi_tmux_watch_control`
- a CLI command: `hermes pi-tmux`

## Core rules

- Run the authoritative controller in Hermes CLI if you want autonomous next-step injection.
- Treat Discord as a reporting surface, not the autonomous control loop.
- Prefer targeting a pane id like `%73`.
- If you only know the tmux window, the watcher now resolves the actual pi worker pane first and refuses untrusted targets when `require_pi=true`.
- Use one watcher per worker. Do not mix multiple supervisors for the same run.

## Observe once

Use this to verify the watcher is looking at the real pi pane before arming anything:

```json
{"action":"observe","target":"main-17:doct-nod-447","plan_file":"~/code/doct-nod-447/thoughts/plans/nod-447-add-table-support-to-doct-text-documents.md"}
```

Returned fields include:
- `resolved_target`
- `worker`
- `controller`
- `trusted_target`
- `events`
- `markers`
- `tail_excerpt`

## Arm a watcher

Example review watcher with phase-progress reporting:

```json
{
  "action":"arm",
  "target":"main-17:doct-nod-447",
  "event":"review_complete",
  "phase":"review",
  "plan_file":"~/code/doct-nod-447/thoughts/plans/nod-447-add-table-support-to-doct-text-documents.md"
}
```

The watcher now writes:
- machine-readable status JSON under `~/.hermes/tmp/`
- rolling log under `~/.hermes/tmp/`

Tool `status` returns those paths.

## Important limitation

`ctx.inject_message()` only works in Hermes CLI sessions. In gateway sessions (Discord/Telegram/etc.), the watcher can still observe tmux state, write status/log files, and emit `EVENT:*` progress lines, but it cannot autonomously re-enter the active gateway conversation without Hermes core support.

## Reliable Discord progress reporting

If you want phase progress visible in Discord, launch the CLI watcher as a background Hermes terminal job and watch for phase events:

```bash
hermes pi-tmux watch \
  --target main-17:doct-nod-447 \
  --phase review \
  --plan-file ~/code/doct-nod-447/thoughts/plans/nod-447-add-table-support-to-doct-text-documents.md
```

Use Hermes `terminal(background=true, watch_patterns=[...])` with patterns such as:
- `EVENT:PHASE_PROGRESS`
- `EVENT:TARGET_UNTRUSTED`
- `EVENT:WATCHER_ERROR`
- `EVENT:TIMEOUT`
- `EVENT:REVIEW_COMPLETE`
- `EVENT:INTEGRATE_COMPLETE`
- `EVENT:PM_REVIEW_COMPLETE`

This gives Discord phase-level notifications without streaming literal pi output.

## Completion detection improvements

The watcher now handles real pi outputs better, including markers such as:
- `Review Summary`
- `Recommendation:`
- `Integration Complete`
- `plan is now clean`
- `PM Review Complete`

It no longer relies only on generic prompt visibility.

## Inspection workflow

1. `observe` once to confirm the real worker pane.
2. `arm` one watcher for the current phase.
3. Check `status` for `resolved_target`, `state_classification`, `status_path`, and `log_path`.
4. If the watcher becomes untrusted or times out, inspect the pane manually and replace the watcher instead of stacking a second monitor.
