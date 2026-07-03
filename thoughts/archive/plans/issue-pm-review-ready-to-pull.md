# Feeling Lucky issue triage command

Status: execution-ready

## Goal

Add a focused single-issue triage command that reviews a Feeling Lucky Linear issue, reuses the existing workplanner compatibility markers/comments, and stops after either moving the issue to `Needs Feedback` or `Ready to pull`.

## Why this plan exists

The repo already has two adjacent but mismatched surfaces:
- `_opencode/commands/cmd:workplanner.md` performs project-wide cron-style triage with text parsing and candidate scanning.
- `_pi/prompts/cmd:feeling-lucky-pr*.md` assumes an issue is already `Ready to pull` and then continues into branch/plan/review/PR flow.

What is missing is a repo-local command for one explicit issue that performs the PM-style clarification-vs-ready triage step without the cron loop and without any downstream implementation or PR automation.

## Authority and inputs

- User constraints from this session:
  - primary path `_pi/prompts/cmd:triage-feeling-lucky-issue.md`
  - optional parity mirror `_opencode/commands/cmd:triage-feeling-lucky-issue.md`
  - exact `[workplanner]` prefix / `review-marker` / `clarification-needed` compatibility
  - preserve skip-if-waiting-for-external-feedback logic
  - no cron loop and no downstream build/PR flow
  - prefer `ltui issues view --format json --include-comments --include-history` if supported
  - focused validation candidates: `NOD-448` and `NOD-389`
- `AGENTS.md`
- `_pi/prompts/dev:plan.md`
- `_opencode/commands/README.md`
- `_opencode/commands/cmd:workplanner.md`
- `_pi/prompts/cmd:feeling-lucky-pr.md`
- `tools/ltui/README.md`
- `tools/ltui/SPEC.md`

## Current implementation reality

- There is no `_pi/prompts/cmd:triage-feeling-lucky-issue.md` today.
- `_opencode/commands/cmd:workplanner.md` already defines the compatibility contract for:
  - `[workplanner]` progress prefix
  - `[workplanner] clarification-needed` comments
  - `[workplanner] review-marker` comments with `reviewedAt` and `outcome`
  - skip-if-waiting-for-external-feedback behavior after a `needs-feedback` marker
  - terminal state changes to `Needs Feedback` or `Ready to pull`
- The current workplanner command is intentionally broad: it resolves the DocThingy project, lists candidates, iterates, and is designed for cron/headless use.
- `_pi/prompts/cmd:feeling-lucky-pr.md` and `_pi/prompts/cmd:feeling-lucky-pr-os.md` are downstream automation flows from a `Ready to pull` issue to branch/plan/review/implementation/PR. They should not be copied wholesale into the new triage command.
- `ltui` repo evidence confirms structured JSON support:
  - `tools/ltui/SPEC.md` documents `ltui issues view <issue> [--include-comments] [--include-history]`
  - `tools/ltui/SPEC.md` documents JSON envelope output for `--format json`
  - repo code/tests under `tools/ltui/src` reference `issues view json` and the include flags
- Product-intent docs are absent (`PRODUCT_INTENT.md` and `thoughts/specs/product_intent.md` do not exist), so this plan aligns to the validated repo workflow docs and the user’s constraints.

## Product intent alignment

This command should make the correct triage step the easiest next action:
- take one explicit issue key,
- inspect the issue plus prior discussion in a structured way,
- reuse the existing marker protocol so automation stays compatible,
- avoid exporting cron/candidate-scan complexity into the command surface,
- stop before branch/plan/PR flows so the user can make a clear handoff into the existing downstream commands.

## Locked decisions

1. The primary deliverable is `_pi/prompts/cmd:triage-feeling-lucky-issue.md`.
2. `_opencode/commands/cmd:triage-feeling-lucky-issue.md` is optional parity work, not required for correctness of the first cut.
3. The new command is single-issue and explicit-input driven; it does not scan the project or behave like cron.
4. Reuse the exact `[workplanner]` marker/comment compatibility from `_opencode/commands/cmd:workplanner.md`.
5. Preserve skip-if-waiting-for-external-feedback logic as an early no-op exit. When the command takes an action, the only terminal state transitions are `Needs Feedback` or `Ready to pull`.
6. Prefer `ltui issues view --format json --include-comments --include-history` over fragile detail/text parsing because repo evidence supports the JSON path.
7. Do not include branch creation, `/dev:plan`, implementation, validation, commit, push, or PR creation in this command.
8. Focused live verification should prefer `NOD-448` for the ready path and `NOD-389` for the clarification path if current issue content still supports those paths.

## Acceptance criteria

1. `_pi/prompts/cmd:triage-feeling-lucky-issue.md` exists and describes a single-issue triage flow, not a project-wide cron flow.
2. The prompt requires or strongly expects an explicit `ISSUE_KEY` input.
3. The command uses `ltui issues view --format json --include-comments --include-history` unless implementation-time evidence disproves support.
4. The command preserves compatibility with the existing workplanner marker/comment format:
   - `[workplanner] clarification-needed`
   - `[workplanner] review-marker`
   - `reviewedAt: ...`
   - `outcome: needs-feedback | ready-to-pull`
5. The command preserves skip-if-waiting-for-external-feedback behavior before re-reviewing an issue.
6. When requirements are unclear, the command posts the clarification comment, moves the issue to `Needs Feedback`, posts the review marker, and stops.
7. When change is warranted and requirements are clear, the command moves the issue to `Ready to pull`, posts the review marker, and stops.
8. The command does not include cron candidate scanning or downstream branch/plan/PR flow.
9. Verification includes at least one likely-ready issue and one likely-clarification-needed issue, with `NOD-448` and `NOD-389` used when still applicable.

## BDD scenarios

### B1 — ready-to-pull path
Given a Feeling Lucky issue whose requirements are clear and whose requested delta is warranted
When `/cmd:triage-feeling-lucky-issue <ISSUE_KEY>` runs
Then it reviews the issue context, does not enter any candidate-scan loop, moves the issue to `Ready to pull`, posts a compatible `[workplanner] review-marker` comment, and stops without launching any downstream build/PR flow.

### B2 — clarification-needed path
Given a Feeling Lucky issue whose requested delta is ambiguous after codebase evaluation
When `/cmd:triage-feeling-lucky-issue <ISSUE_KEY>` runs
Then it posts a compatible `[workplanner] clarification-needed` comment, moves the issue to `Needs Feedback`, posts a compatible `[workplanner] review-marker` comment with `outcome: needs-feedback`, and stops.

### B3 — waiting-for-feedback skip path
Given an issue whose latest compatible marker outcome is `needs-feedback`
And no newer external comment exists after that marker
When `/cmd:triage-feeling-lucky-issue <ISSUE_KEY>` runs
Then it skips re-review without changing state, preserving the existing waiting-for-feedback contract.

### B4 — structured issue fetch path
Given ltui support for `--format json --include-comments --include-history`
When the command fetches issue context
Then it uses the structured JSON path instead of brittle text parsing for comment/history inspection.

### B5 — no downstream automation path
Given the command completes either main triage outcome
When it stops
Then it does not create a branch, does not create a plan, and does not open or prepare a PR.

## Proposed approach

Start from `_opencode/commands/cmd:workplanner.md`, but narrow the workflow from project-wide autonomous triage to one explicit issue. Keep the compatibility-critical comment and marker conventions intact while removing:
- project resolution,
- candidate listing,
- oldest-updated iteration,
- cron/headless framing,
- and all downstream implementation/PR steps.

Use structured ltui JSON issue view for the new command’s decision logic so the marker/skip checks are less fragile than the current text parsing path. Keep the evaluation section repo-aware: inspect relevant docs and implementation before deciding whether the issue is already covered or still needs a concrete delta.

If parity remains cheap after the Pi prompt is correct, mirror the command into `_opencode/commands/cmd:triage-feeling-lucky-issue.md` with the same behavior. Do not let that optional mirror block the primary Pi delivery.

## Verification strategy

- Static verification proves the prompt exists, uses the intended ltui JSON fetch path, preserves compatibility markers, and excludes cron/downstream flow.
- Live verification proves one likely-ready issue and one likely-clarification-needed issue follow the intended stop behavior.
- If `NOD-448` or `NOD-389` no longer fit their expected path at execution time, substitute current issues with equivalent evidence and log the deviation.

## Test coverage matrix

| Acceptance / scenario | Planned evidence |
| --- | --- |
| AC1, AC2, B5 | Static prompt inspection of command arguments, scope, and stop conditions |
| AC3, B4 | Static grep/read for `ltui issues view --format json --include-comments --include-history` |
| AC4, AC5, B3 | Static inspection of marker/comment format and skip logic |
| AC6, B2 | Focused live run against likely clarification-needed issue (`NOD-389` if still applicable) |
| AC7, B1 | Focused live run against likely ready issue (`NOD-448` if still applicable) |
| AC8 | Static inspection confirming no project-scan / branch / PR flow remains |
| AC9 | Verification notes from both focused issue runs |

## Delivery order

1. Land the Pi command prompt with the narrowed single-issue contract.
2. Add any required Pi-local documentation updates for discoverability.
3. Optionally mirror to OpenCode only if it is a straight parity copy.
4. Run focused live triage verification on one likely-ready and one likely-clarification-needed issue.

## Non-goals

- Replacing `_opencode/commands/cmd:workplanner.md`.
- Reworking the broader Feeling Lucky branch/plan/PR flows.
- Adding cron support, project-level candidate scanning, or random issue selection to the new command.
- Changing the workplanner compatibility marker format.
- Guaranteeing the optional OpenCode mirror in the first cut.

## Resume instructions (agent)

- Read this document fully.
- Start with the first unchecked item in `## Progress`.
- Keep the primary focus on `_pi/prompts/cmd:triage-feeling-lucky-issue.md`.
- Reuse the workplanner compatibility contract exactly where this plan says it is locked.
- If live issue evidence differs from the expected `NOD-448` / `NOD-389` paths, choose current equivalent issues, log the deviation, and continue.
- Ask the user only if ltui support or issue-state permissions make the flow non-executable.

## Progress

- [ ] P1 - Draft the single-issue Pi triage command from the existing workplanner logic with JSON-based issue fetch and compatibility markers.
- [ ] P2 - Update Pi-local discoverability docs for the new command and decide whether the optional OpenCode parity mirror is still worth landing.
- [ ] P3 - Run focused verification against likely ready and clarification-needed issues and capture any live deviations.

## Phase 1: Draft the single-issue Pi triage command

### Tests first

- Confirm no command already exists:
  - `test -f _pi/prompts/cmd:triage-feeling-lucky-issue.md && echo exists || echo missing`
- Confirm the compatibility source:
  - `rg -n "\[workplanner\]|clarification-needed|review-marker|needs-feedback|ready-to-pull" _opencode/commands/cmd:workplanner.md`
- Confirm structured ltui support:
  - `rg -n "include-comments|include-history|issues view json|--format json" tools/ltui/SPEC.md tools/ltui/src tools/ltui/README.md`
- Confirm the downstream flows that must not be copied into this command:
  - `rg -n "branch|dev:plan|create-pr|Ready to pull" _pi/prompts/cmd:feeling-lucky-pr*.md`

### End State

- `_pi/prompts/cmd:triage-feeling-lucky-issue.md` exists.
- The prompt targets one explicit issue key.
- The prompt preserves compatibility markers/comments and the waiting-for-feedback skip logic.
- The prompt stops before any downstream build/branch/plan/PR workflow.

### Work

- Create `_pi/prompts/cmd:triage-feeling-lucky-issue.md`.
- Base its logic on `_opencode/commands/cmd:workplanner.md`, but remove project resolution, candidate listing, and iteration.
- Require or strongly guide explicit `ISSUE_KEY` input.
- Switch the issue-fetch recommendation to `ltui issues view <ISSUE_KEY> --format json --include-comments --include-history` and parse the JSON envelope instead of the detail-text format when implementing marker/skip checks.
- Preserve the exact compatibility strings for `[workplanner] clarification-needed` and `[workplanner] review-marker`.
- Preserve the existing distinction between:
  - early skip because the issue is still waiting for external feedback,
  - `Needs Feedback` action,
  - `Ready to pull` action.
- Remove all cron framing and any downstream build/PR flow.

### Expected files

- `_pi/prompts/cmd:triage-feeling-lucky-issue.md`
- `_opencode/commands/cmd:workplanner.md`
- `_pi/prompts/cmd:feeling-lucky-pr.md`
- `tools/ltui/SPEC.md`

### Verify

- `rg -n "triage-feeling-lucky-issue|include-comments|include-history|review-marker|clarification-needed|Ready to pull|Needs Feedback" _pi/prompts/cmd:triage-feeling-lucky-issue.md`
- `rg -n "candidate|cron|create-pr|gh pr|git checkout|dev:plan|review:plan|skill:ralph-run" _pi/prompts/cmd:triage-feeling-lucky-issue.md`
- Read the new prompt and confirm it only supports the single-issue triage surface.

## Phase 2: Update discoverability and decide on optional parity mirror

### Tests first

- Capture current Pi command docs baseline:
  - `rg -n "FeelingLucky|feeling-lucky|cmd:" _pi/README.md`
- If considering parity, confirm whether `_opencode/commands/README.md` needs an entry or whether the mirror can remain intentionally undocumented in the first pass:
  - `rg -n "workplanner|FeelingLucky|cmd:" _opencode/commands/README.md`

### End State

- Pi-local docs mention the new triage command if discoverability would otherwise be poor.
- The optional OpenCode mirror is either implemented as a straight parity copy or explicitly deferred without blocking the plan.

### Work

- Update `_pi/README.md` where command examples or notable command lists should mention the new triage command.
- Decide whether `_opencode/commands/cmd:triage-feeling-lucky-issue.md` is worth landing immediately.
- If the mirror is landed, keep it behaviorally aligned with the Pi command and update any lightweight OpenCode discoverability docs only if needed.
- If the mirror is deferred, do not broaden required scope; log that decision if it comes up during execution.

### Expected files

- `_pi/README.md`
- `_pi/prompts/cmd:triage-feeling-lucky-issue.md`
- optional `_opencode/commands/cmd:triage-feeling-lucky-issue.md`
- optional `_opencode/commands/README.md`

### Verify

- `rg -n "triage-feeling-lucky-issue" _pi/README.md _pi/prompts _opencode/commands 2>/dev/null`
- If the parity mirror lands: `diff -u _pi/prompts/cmd:triage-feeling-lucky-issue.md _opencode/commands/cmd:triage-feeling-lucky-issue.md || true`
- If the mirror does not land: confirm the Pi path is still fully documented enough for use.

## Phase 3: Run focused live verification

### Tests first

- Confirm ltui auth before issuing writes:
  - `ltui auth test`
- Inspect candidate issues with structured output before acting:
  - `ltui issues view NOD-448 --format json --include-comments --include-history`
  - `ltui issues view NOD-389 --format json --include-comments --include-history`

### End State

- The command has been exercised against one likely ready issue and one likely clarification-needed issue, or equivalent substitutes if those keys no longer fit.
- Verification records whether the ready path, clarification path, and waiting-for-feedback skip path behave as planned.

### Work

- Run the new command against `NOD-448` if its current state/content still makes it the strongest ready-to-pull candidate.
- Run the new command against `NOD-389` if its current state/content still makes it the strongest clarification-needed candidate.
- If one of those issues no longer fits, choose a current equivalent and record the reason in the plan log.
- Confirm the command stops after the triage outcome and does not cascade into downstream flows.
- Confirm comment compatibility and marker updates in Linear after each run.

### Expected files

- `_pi/prompts/cmd:triage-feeling-lucky-issue.md`
- optional `_opencode/commands/cmd:triage-feeling-lucky-issue.md`

### Verify

- `ltui issues view NOD-448 --format json --include-comments --include-history`
- `ltui issues view NOD-389 --format json --include-comments --include-history`
- Review resulting comments/history for:
  - `[workplanner] clarification-needed`
  - `[workplanner] review-marker`
  - `outcome: needs-feedback | ready-to-pull`
- Confirm no branch was created and no PR-related command was triggered by this flow.

## Decisions / Deviations log

- 2026-04-17: Locked the new command as Pi-first under `_pi/prompts/cmd:triage-feeling-lucky-issue.md`; OpenCode parity is explicitly optional.
- 2026-04-17: Locked structured ltui JSON issue view as the preferred fetch path because repo docs/spec/tests already prove support for `--format json --include-comments --include-history`.
- 2026-04-17: Preserved the workplanner waiting-for-feedback skip contract as a no-op early exit rather than treating it as a third state-transition outcome.

## Plan changelog

- 2026-04-17: Created execution-ready plan for a single-issue Feeling Lucky triage command, grounded in workplanner compatibility and ltui JSON support.