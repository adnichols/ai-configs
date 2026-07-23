---
description: Run Playwright with process/log supervision and direct scoped fixes
argument-hint: "[optional playwright args/filter]"
---

# Test Run Playwright (Direct Supervision/Fix Mode)

Run Playwright in a background process/PTY session, monitor output incrementally, perform cheap failure investigation first, then have the driving agent apply narrow fixes directly. Do not delegate code changes to subagents.

Target arguments: `$ARGUMENTS`

## Defaults

- Base command: `pnpm run test:e2e -- --workers=4 --reporter=list,./tests/opencode-live-events-reporter.ts`
- Mode: **direct supervision/fix** (keep suite running; collect logs and narrow failure families before direct fixes)
- Apply mode: **narrow-fix** (the driving agent handles one bounded failure family at a time)
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
6. Build a failure packet with command, failing scenario, relevant logs, suspected files, and targeted verification.
7. If suspected files are ambiguous, prefer direct targeted search; use `scout` only for bounded read-only callsite discovery when that search is insufficient.
8. If the queue is non-empty, the driving agent investigates and fixes one scoped failure family directly, records the result, then resumes monitoring.

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

### 4) Build Failure Packets and Fix Directly

For each queued failure, first build a failure packet. If the relevant file area is not clear from the test path, stack, and recent changes, search directly and use `scout` only as an optional bounded read-only callsite lookup.

Failure packet requirements:

- Original command and arguments
- Failing project, scenario, test file, line, and title
- Relevant error message, stack, and attachment paths
- Suspected files or callsites, with evidence
- Minimal expected behavior
- Targeted verification command for the driving agent to run

Direct-fix requirements:

1. Investigate root cause for the specific failing test using the packet.
2. Apply a minimal code fix directly when the cause is product code.
3. Do **not** start another full Playwright suite while the parent live run is active.
4. If safe and cheap, run only narrowly scoped non-e2e checks related to changed code.
5. Record root cause, files changed, patch summary, targeted verification, and residual risk in `fixRecords`.
6. Continue the watch loop immediately after the bounded fix.

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
- If two queued failures target the same file area, deduplicate or process them together only when one root cause clearly explains both.
- If a failure appears flaky or env-related, mark it and avoid speculative app changes.
- Keep the driving agent responsible for both supervision and fixes; use the background process/PTY so no developer subagent is needed.
- Keep all outputs concise; include explicit file paths for any code edits.
