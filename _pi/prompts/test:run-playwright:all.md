---
description: Run full Playwright suite with process/log supervision and scoped fixer delegation
argument-hint: "[optional playwright args/filter]"
---

# Test Run Playwright All (Split Supervision/Fix Mode)

Run the full E2E suite in three sequential phases (`test:e2e:full`, `test:e2e:clerk`, `test:e2e:perf`) while monitoring process/PTY output incrementally, performing cheap failure investigation first, and spawning `developer-mid` only with narrow failure packets. Keep long-running E2E supervision separate from code-writing fixes.

Target arguments: `$ARGUMENTS`

## Defaults

- Phase order: `test:e2e:full` -> `test:e2e:clerk` -> `test:e2e:perf`
- Per-phase base command: `pnpm run <phase> -- --workers=4 --reporter=list,./tests/opencode-live-events-reporter.ts`
- Mode: **split supervision/fix** (keep each phase running; collect logs and narrow failure families before fix delegation)
- Apply mode: **narrow-fix** (subagents receive bounded failure packets; no whole-suite supervision)
- Max fixer concurrency: `2` (only for independent files/failure families)
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
- `MAX_CONCURRENT_FIXERS = 2`
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
7. If suspected files are ambiguous, use `Explore`/`explore` for callsite discovery before spawning a fixer.
8. If queue is non-empty and `inFlightFixers < MAX_CONCURRENT_FIXERS`, dispatch scoped fixer subagents.

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

### 4) Build Failure Packets and Spawn Fixer Subagents

For each queued failure, first build a failure packet. If the relevant file area is not clear from the test path, stack, and recent changes, run `Explore`/`explore` to identify likely callsites before spawning a fixer.

Failure packet requirements:

- Original command, phase, and arguments
- Failing project, scenario, test file, line, and title
- Relevant error message, stack, and attachment paths
- Suspected files or callsites, with evidence
- Minimal expected behavior
- Targeted verification command for the fixer or parent to run

Spawn a `Task` with `subagent_type="developer-mid"` only after the packet is narrow enough that the fixer does not need to rediscover the repo or supervise the whole E2E loop.

Subagent requirements:

1. Investigate root cause for the specific failing test using the provided packet.
2. Apply a minimal code fix directly when the cause is product code.
3. Do **not** run the full Playwright suite or supervise the parent live phase.
4. If safe and cheap, run only narrowly scoped non-e2e checks related to changed code.
5. Return:
   - root cause
   - files changed
   - patch summary
   - targeted verification run or recommended
   - residual risk

Use this prompt template (fill placeholders):

```text
Investigate and fix this live Playwright failure from full-suite orchestration.

Failure packet:
- command: <command>
- phase: <phase>
- project: <project>
- test: <title>
- location: <file>:<line>:<column>
- status: <status>
- retry: <retry>/<retriesAllowed>
- errorMessage: <errorMessage>
- errorStack: <errorStack>
- attachmentPaths: <attachmentPaths>
- suspectedFiles: <Explore or log-derived files>
- expectedBehavior: <minimal expected behavior>
- targetedVerification: <command/filter>

Constraints:
- Apply a minimal fix only for this packet.
- Avoid broad refactors.
- Do not run the full Playwright suite or supervise the parent live phase.
- Return concise notes with exact file paths changed and targeted verification performed/recommended.
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

- Allow up to two concurrent fixers only for independent failure families; keep shared-file failures sequential.
- If two queued failures target the same file area, process sequentially.
- If a failure appears flaky or env-related, mark it and avoid speculative app changes.
- Prevent GPT-5.6 Sol agents from supervising whole E2E loops unless the operator explicitly escalates.
- Keep all outputs concise; include explicit file paths for any code edits.
