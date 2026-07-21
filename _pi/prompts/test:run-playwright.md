---
description: Run Playwright with process/log supervision, narrow failure packets, and scoped fixer delegation
argument-hint: "[optional playwright args/filter]"
---

# Test Run Playwright (Split Supervision/Fix Mode)

Run Playwright in a background process/PTY session, monitor output incrementally, perform cheap failure investigation first, then delegate narrow fix packets to `developer-mid`. Keep long-running E2E supervision separate from code-writing fixes.

Target arguments: `$ARGUMENTS`

## Defaults

- Base command: `pnpm run test:e2e -- --workers=4 --reporter=list,./tests/opencode-live-events-reporter.ts`
- Mode: **split supervision/fix** (keep suite running; collect logs and narrow failure families before fix delegation)
- Apply mode: **narrow-fix** (subagents receive bounded failure packets; no whole-suite supervision)
- Max fixer concurrency: `2` (only for independent files/failure families)
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
   - `inFlightFixers = 0`
   - `MAX_CONCURRENT_FIXERS = 2`
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
7. If suspected files are ambiguous, use `scout` for callsite discovery before spawning a fixer.
8. If queue is non-empty and `inFlightFixers < MAX_CONCURRENT_FIXERS`, dispatch one scoped fixer subagent.

Notes:
- It is acceptable that output accumulates while a subagent runs; catch up from `offset` after it returns.
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

### 4) Build Failure Packets and Spawn Fixer Subagents

For each queued failure, first build a failure packet. If the relevant file area is not clear from the test path, stack, and recent changes, run `scout` to identify likely callsites before spawning a fixer.

Failure packet requirements:

- Original command and arguments
- Failing project, scenario, test file, line, and title
- Relevant error message, stack, and attachment paths
- Suspected files or callsites, with evidence
- Minimal expected behavior
- Targeted verification command for the fixer or parent to run

Spawn a `Task` with `subagent_type="developer-mid"` only after the packet is narrow enough that the fixer does not need to rediscover the repo or supervise the whole E2E loop.

Subagent requirements:

1. Investigate root cause for the specific failing test using the provided packet.
2. Apply a minimal code fix directly when the cause is product code.
3. Do **not** run the full Playwright suite or supervise the parent live run.
4. If safe and cheap, run only narrowly scoped non-e2e checks related to changed code.
5. Return:
   - root cause
   - files changed
   - patch summary
   - targeted verification run or recommended
   - residual risk

Use this prompt template (fill placeholders):

```text
Investigate and fix this live Playwright failure.

Failure packet:
- command: <command>
- project: <project>
- test: <title>
- location: <file>:<line>:<column>
- status: <status>
- retry: <retry>/<retriesAllowed>
- errorMessage: <errorMessage>
- errorStack: <errorStack>
- attachmentPaths: <attachmentPaths>
- suspectedFiles: <scout or log-derived files>
- expectedBehavior: <minimal expected behavior>
- targetedVerification: <command/filter>

Constraints:
- Apply a minimal fix only for this packet.
- Avoid broad refactors.
- Do not run the full Playwright suite or supervise the parent live run.
- Return concise notes with exact file paths changed and targeted verification performed/recommended.
```

After subagent completion:
- decrement `inFlightFixers`
- append result to `fixRecords`
- continue watch loop immediately

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

- Allow up to two concurrent fixers only for independent failure families; keep shared-file failures sequential.
- If two queued failures target the same file area, process sequentially.
- If a failure appears flaky or env-related, mark it and avoid speculative app changes.
- Prevent GPT-5.6 Sol agents from supervising whole E2E loops unless the operator explicitly escalates.
- Keep all outputs concise; include explicit file paths for any code edits.
