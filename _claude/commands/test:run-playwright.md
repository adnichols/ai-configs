---
description: Run Playwright in PTY, watch failures live, and apply direct scoped fixes
argument-hint: "[optional playwright args/filter]"
---

# Test Run Playwright (Direct Live Fix Mode)

Run Playwright in a background PTY session, monitor output incrementally, and have the driving agent investigate and apply scoped fixes directly while the suite is still running. Do not delegate code changes to subagents.

Target arguments: `$ARGUMENTS`

## Defaults

- Base command: `pnpm run test:e2e -- --workers=4 --reporter=list,./tests/opencode-live-events-reporter.ts`
- Mode: **direct live-fix** (keep suite running; investigate/fix as failures arrive)
- Apply mode: **live-apply** (the driving agent applies code changes directly)
- Max fixer concurrency: `1`
- Failure dedupe key: `project + file + line + title`

## Process

### 0) Autopilot Rules

- Continue until the PTY process exits and final reruns finish.
- Do not stop after status updates.
- Do not ask for permission to proceed unless blocked by an unresolvable decision.
- Keep user updates concise and factual.

### 1) Build and Start the Playwright Command

1. Build the run command as:
   - `pnpm run test:e2e -- --workers=4 --reporter=list,./tests/opencode-live-events-reporter.ts`
   - If `$ARGUMENTS` is non-empty, append it as additional Playwright arguments after the reporter.

2. Start it with `pty_spawn`:
   - `command`: `pnpm`
   - `args`: `run`, `test:e2e`, `--`, `--workers=4`, `--reporter=list,./tests/opencode-live-events-reporter.ts`, plus parsed `$ARGUMENTS`
   - `title`: `Playwright Live Run`
   - `description`: `Run Playwright with live failure orchestration`
   - `notifyOnExit`: `true`

3. Record:
   - `sessionId`
   - `offset = 0`
   - `seenFailureKeys = Set()`
   - `queue = []`
   - `fixRecords = []`

### 2) Watch Loop (PTY Polling)

Loop until PTY is no longer running:

1. Check session status with `pty_list`.
2. Read new lines with `pty_read` using current `offset`.
3. Advance `offset` by number of new lines processed.
4. Parse each new line:
   - Preferred: sentinel events from reporter lines matching `@@OC_PW_EVENT@@{json}`.
   - Fallback: parse `list` reporter failure lines when sentinel parsing fails.
5. When a new failure is found, enqueue it unless deduped by key.
6. If the queue is non-empty, investigate and fix one bounded failure family directly, append the result to `fixRecords`, then resume monitoring.

Notes:
- It is acceptable that output accumulates while the driving agent fixes a failure; catch up from `offset` afterward.
- Always do a final drain read when run exits so no late events are missed.

### 3) Failure Event Parsing

Use this event schema from `./tests/opencode-live-events-reporter.ts`:

- Prefix: `@@OC_PW_EVENT@@`
- Failure event: `event === "test-failed-final"`
- Fields to extract:
  - `project`, `file`, `line`, `column`, `title`, `titlePath`
  - `status`, `durationMs`, `retry`, `retriesAllowed`
  - `errorMessage`, `errorStack`, `errors[]`, `attachmentPaths[]`

Build dedupe key:
- `${project}|${file}:${line}|${title}`

Fallback parser (if needed):
- Parse list reporter lines beginning with `x` and extract `[project] file:line:col > title`.

### 4) Investigate and Fix Directly

For each queued failure, the driving agent:

1. Builds a bounded failure packet from the test location, error, stack, attachments, and recent changes.
2. Uses direct targeted repository search to identify the root cause.
3. Applies a minimal fix when the cause is product or test code.
4. Does **not** start another full Playwright suite while the main run is active.
5. Runs only cheap targeted non-e2e checks when safe.
6. Records root cause, files changed, patch summary, verification, and residual risk in `fixRecords`.
7. Continues the watch loop immediately.

### 5) Completion + Verification Pass

When PTY exits:

1. Do a final `pty_read` drain from current `offset`.
2. Parse `run-end` event (or fallback Playwright summary) and report totals.
3. If fixes were applied, rerun targeted failures sequentially using Playwright file/line or grep filters.
   - Keep reporter override: `--reporter=list,./tests/opencode-live-events-reporter.ts`
4. Summarize:
   - failures detected
   - failures investigated
   - fixes applied
   - rerun outcomes
   - remaining blockers

## Guardrails

- Process failure families sequentially in the driving session.
- If two queued failures target the same file area, process sequentially.
- If a failure appears flaky or env-related, mark it and avoid speculative app changes.
- Keep all outputs concise; include explicit file paths for any code edits.
