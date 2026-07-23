---
description: Run full Playwright suite with process/log supervision and direct scoped fixes
argument-hint: "[optional playwright args/filter]"
---

# Test Run Playwright All (Direct Supervision/Fix Mode)

Run the full E2E suite in three sequential phases (`test:e2e:full`, `test:e2e:clerk`, `test:e2e:perf`) while monitoring process/PTY output incrementally, performing cheap failure investigation first, and applying narrow fixes directly in the driving session. Do not delegate code changes to subagents.

Target arguments: `$ARGUMENTS`

## Defaults

- Phase order: `test:e2e:full` -> `test:e2e:clerk` -> `test:e2e:perf`
- Per-phase base command: `pnpm run <phase> -- --workers=4 --reporter=list,./tests/opencode-live-events-reporter.ts`
- Mode: **direct supervision/fix** (keep each phase running; collect logs and narrow failure families before direct fixes)
- Apply mode: **narrow-fix** (the driving agent handles one bounded failure family at a time)
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
6. Build a failure packet with command, phase, failing scenario, relevant logs, suspected files, and targeted verification.
7. If suspected files are ambiguous, prefer direct targeted search; use `scout` only for bounded read-only callsite discovery when that search is insufficient.
8. If the queue is non-empty, the driving agent investigates and fixes one scoped failure family directly, records the result, then resumes monitoring.

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

### 4) Build Failure Packets and Fix Directly

For each queued failure, first build a failure packet. If the relevant file area is not clear from the test path, stack, and recent changes, search directly and use `scout` only as an optional bounded read-only callsite lookup.

Failure packet requirements:

- Original command, phase, and arguments
- Failing project, scenario, test file, line, and title
- Relevant error message, stack, and attachment paths
- Suspected files or callsites, with evidence
- Minimal expected behavior
- Targeted verification command for the driving agent to run

Direct-fix requirements:

1. Investigate root cause for the specific failing test using the packet.
2. Apply a minimal code fix directly when the cause is product code.
3. Do **not** start another full Playwright suite while the parent live phase is active.
4. If safe and cheap, run only narrowly scoped non-e2e checks related to changed code.
5. Record root cause, files changed, patch summary, targeted verification, and residual risk in `fixRecords`.
6. Continue the watch loop immediately after the bounded fix.

### 5) Phase Completion Policy

When a phase PTY exits:

1. Final-drain with `pty_read` from current `offset`.
2. Parse `run-end` event (or fallback Playwright summary).
3. Save phase summary in `phaseSummaries`.
4. If phase exit code is non-zero, record the failed phase in `phaseSummaries` and continue to the next phase so this full-suite wrapper still reports later-phase regressions in the same invocation. Stop remaining phases only for a truly unrecoverable blocker such as missing required environment, broken test harness startup, corrupted reporter output, or an operator stop request.

### 6) Final Verification Pass

After the final phase completes, or after an unrecoverable blocker stops the remaining phases:

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
- If two queued failures target the same file area, deduplicate or process them together only when one root cause clearly explains both.
- If a failure appears flaky or env-related, mark it and avoid speculative app changes.
- Keep the driving agent responsible for both supervision and fixes; use the background process/PTY so no developer subagent is needed.
- Keep all outputs concise; include explicit file paths for any code edits.
