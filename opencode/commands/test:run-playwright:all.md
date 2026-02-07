---
description: Run full Playwright suite in PTY, stream failures, and spawn live fixer subagents
argument-hint: "[optional playwright args/filter]"
---

# Test Run Playwright All (Live Fix Mode B)

Run the full E2E suite in three sequential phases (`test:e2e:full`, `test:e2e:clerk`, `test:e2e:perf`) while monitoring PTY output incrementally and spawning `developer` subagents to investigate and apply fixes live.

Target arguments: `$ARGUMENTS`

## Defaults

- Phase order: `test:e2e:full` -> `test:e2e:clerk` -> `test:e2e:perf`
- Per-phase base command: `pnpm run <phase> -- --workers=4 --reporter=list,./tests/opencode-live-events-reporter.ts`
- Mode: **B** (keep each phase running; investigate/fix as failures arrive)
- Apply mode: **live-apply** (subagents apply code changes immediately)
- Max fixer concurrency: `3` (balanced parallel fixes)
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
   - `inFlightFixers = 0`

Maintain global state across all phases:
- `seenFailureKeys = Set()`
- `MAX_CONCURRENT_FIXERS = 3`
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
6. If queue is non-empty and `inFlightFixers < MAX_CONCURRENT_FIXERS`, dispatch fixer subagents.

Notes:
- Output may accumulate while a subagent runs; always catch up from `offset`.
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

### 4) Spawn Fixer Subagents (Live Apply)

For each queued failure, spawn a `Task` with `subagent_type="developer"`.

Subagent requirements:

1. Investigate root cause for the specific failing test.
2. Apply a minimal code fix directly (live-apply).
3. Do **not** run full Playwright suite while the parent phase run is active.
4. If safe and cheap, run only narrowly scoped non-e2e checks related to changed code.
5. Return:
   - root cause
   - files changed
   - patch summary
   - residual risk

Use this prompt template (fill placeholders):

```text
Investigate and fix this live Playwright failure from full-suite orchestration.

Failure context:
- phase: <phase>
- project: <project>
- test: <title>
- location: <file>:<line>:<column>
- status: <status>
- retry: <retry>/<retriesAllowed>
- errorMessage: <errorMessage>
- errorStack: <errorStack>
- attachmentPaths: <attachmentPaths>

Constraints:
- Apply a minimal fix now (live-apply mode).
- Avoid broad refactors.
- Do not run the full Playwright suite while the parent live phase is in progress.
- Return concise notes with exact file paths changed.
```

After subagent completion:
- decrement `inFlightFixers`
- append result to `fixRecords`
- continue watch loop immediately

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

- Allow up to three concurrent fixers, but keep shared-file failures sequential.
- If two queued failures target the same file area, process sequentially.
- If a failure appears flaky or env-related, mark it and avoid speculative app changes.
- Keep all outputs concise; include explicit file paths for any code edits.
