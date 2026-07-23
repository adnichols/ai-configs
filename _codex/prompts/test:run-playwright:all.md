---
description: Run full Playwright suite in PTY, stream failures, and apply direct scoped fixes
argument-hint: "[optional playwright args/filter]"
---

# Test Run Playwright All (Direct Live Fix Mode)

Run the full E2E suite in three sequential phases (`test:e2e:full`, `test:e2e:clerk`, `test:e2e:perf`) while monitoring PTY output incrementally and applying scoped fixes directly in the driving session. Do not delegate code changes to subagents.

Target arguments: `$ARGUMENTS`

## Defaults

- Phase order: `test:e2e:full` -> `test:e2e:clerk` -> `test:e2e:perf`
- Per-phase base command: `pnpm run <phase> -- --workers=4 --reporter=list,./tests/opencode-live-events-reporter.ts`
- Mode: **direct live-fix** (keep each phase running; investigate/fix as failures arrive)
- Apply mode: **live-apply** (the driving agent applies code changes directly)
- Max fixer concurrency: `1`
- Failure dedupe key: `phase + project + file + line + title`

## Process

### 0) Autopilot Rules

- Continue until all phases complete or an unrecoverable blocker occurs.
- Do not stop after status updates.
- Do not ask for permission to proceed unless blocked by an unresolvable decision.
- Keep user updates concise and factual.

### 1) Build Phase Commands

For each phase in order:

1. Build command:
   - `pnpm run <phase> -- --workers=4 --reporter=list,./tests/opencode-live-events-reporter.ts`
   - If `$ARGUMENTS` is non-empty, append those arguments after the reporter.

2. Start phase with `pty_spawn`:
   - `command`: `pnpm`
   - `args`: `run`, `<phase>`, `--`, `--workers=4`, `--reporter=list,./tests/opencode-live-events-reporter.ts`, plus parsed `$ARGUMENTS`
   - `title`: `Playwright <phase> Live Run`
   - `description`: `Run <phase> with live failure orchestration`
   - `notifyOnExit`: `true`

3. Initialize per-phase state:
   - `sessionId`
   - `offset = 0`
   - `queue = []`

Maintain global state across all phases:
- `seenFailureKeys = Set()`
- `fixRecords = []`
- `phaseSummaries = []`

### 2) Per-Phase Watch Loop (PTY Polling)

For the active phase, loop until PTY is no longer running:

1. Check session status with `pty_list`.
2. Read new lines with `pty_read` using current `offset`.
3. Advance `offset` by number of new lines processed.
4. Parse each new line:
   - Preferred: sentinel events from reporter lines matching `@@OC_PW_EVENT@@{json}`.
   - Fallback: parse `list` reporter failure lines when sentinel parsing fails.
5. When a new failure is found, enqueue it unless deduped by key.
6. If the queue is non-empty, investigate and fix one bounded failure family directly, append the result to `fixRecords`, then resume monitoring.

Notes:
- Output may accumulate while the driving agent fixes a failure; always catch up from `offset` afterward.
- Always perform one final drain read when a phase exits.

### 3) Failure Event Parsing

Use `./tests/opencode-live-events-reporter.ts` events:

- Prefix: `@@OC_PW_EVENT@@`
- Failure event: `event === "test-failed-final"`
- Fields to extract:
  - `project`, `file`, `line`, `column`, `title`, `titlePath`
  - `status`, `durationMs`, `retry`, `retriesAllowed`
  - `errorMessage`, `errorStack`, `errors[]`, `attachmentPaths[]`

Build dedupe key:
- `${phase}|${project}|${file}:${line}|${title}`

Fallback parser (if needed):
- Parse list reporter lines beginning with `x` and extract `[project] file:line:col > title`.

### 4) Investigate and Fix Directly

For each queued failure, the driving agent:

1. Builds a bounded failure packet from the phase, test location, error, stack, attachments, and recent changes.
2. Uses direct targeted repository search to identify the root cause.
3. Applies a minimal fix when the cause is product or test code.
4. Does **not** start another full Playwright suite while the parent phase is active.
5. Runs only cheap targeted non-e2e checks when safe.
6. Records root cause, files changed, patch summary, verification, and residual risk in `fixRecords`.
7. Continues the watch loop immediately.

### 5) Phase Completion Policy

When a phase PTY exits:

1. Final-drain with `pty_read` from current `offset`.
2. Parse `run-end` event (or fallback Playwright summary).
3. Save phase summary in `phaseSummaries`.
4. If phase exit code is non-zero, stop remaining phases (match `test:e2e:all` fail-fast semantics).

### 6) Final Verification Pass

After final successful phase (or after first failed phase stop):

1. If fixes were applied, rerun targeted failures sequentially (file/line or grep) in the relevant phase context.
2. Keep reporter override: `--reporter=list,./tests/opencode-live-events-reporter.ts`
3. Summarize:
   - phases completed
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
