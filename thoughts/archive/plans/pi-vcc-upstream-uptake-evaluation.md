# pi-vcc upstream uptake and compaction safety

## Status

execution-ready

## Goal

Update the vendored `pi-vcc` package to selectively uptake upstream `0.3.1`/`0.3.2` improvements while fixing the newly observed post-compaction GPT Responses failure where Pi resumes from a `toolResult` whose matching tool call was compacted away.

## Why this plan exists

Two issues now need to be handled together:

1. `bash ./install.sh --pi` reports that the vendored `pi-vcc` snapshot is behind upstream and has broader-than-expected local drift.
2. GPT model sessions are now failing after `pi-vcc` compaction with:
   - `Error: No tool call found for function call output with call_id call_F9axV0xmAqYY5VXvVuMivuy3.`

The second issue is not speculative. Session evidence shows the compaction hook kept a `toolResult` entry live while compacting the assistant message that contained the matching `toolCall`. That leaves the resumed Responses API context internally inconsistent.

The user explicitly asked to pull in upstream changes and evaluate the new GPT error. This plan turns that evidence into an implementation-ready uptake + bugfix path.

## Authority and inputs

Primary authority:
- User request in this session
- Root `AGENTS.md`
- Shared planning doctrine from `/home/anichols/.agents/skills/planning-workflow/SKILL.md`
- Shared workflow/recovery doctrine from `/home/anichols/.agents/skills/product-principles/SKILL.md`

Evidence read:
- `_pi/packages/pi-vcc/package.json`
- `_pi/packages/pi-vcc/README.md`
- `_pi/packages/pi-vcc/src/commands/pi-vcc.ts`
- `_pi/packages/pi-vcc/src/hooks/before-compact.ts`
- `_pi/packages/pi-vcc/src/core/brief.ts`
- `_pi/packages/pi-vcc/src/core/build-sections.ts`
- `_pi/packages/pi-vcc/src/core/content.ts`
- `_pi/packages/pi-vcc/src/core/format.ts`
- `_pi/packages/pi-vcc/src/core/sanitize.ts`
- `_pi/packages/pi-vcc/src/core/summarize.ts`
- `_pi/packages/pi-vcc/src/extract/goals.ts`
- `_pi/packages/pi-vcc/tests/before-compact.test.ts`
- `_pi/packages/pi-vcc/tests/brief.test.ts`
- `_pi/packages/pi-vcc/tests/fixtures.ts`
- `_pi/packages/pi-vcc/tests/format.test.ts`
- `scripts/check-pi-vcc-upstream.sh`
- Session file: `/home/anichols/.pi/agent/sessions/--home-anichols-code-ccore--/2026-04-10T14-10-04-311Z_40614319-f3d6-4558-9032-656f819795df.jsonl`

Observed upstream facts:
- Vendored version: `0.3.0-ai-configs.1`
- Vendored upstream snapshot: `0.3.0` at `8487c9d55e119aa3de270cdf552b6b88eb374b39`
- npm latest upstream package: `0.3.2`
- Upstream head observed by the checker: `82e31a5e4bd22d81bcf08b33750cbcf11e603157`
- Upstream commits since the vendored snapshot:
  - `9804278` — `v0.3.1: semantic improvements`
  - `82e31a5` — `v0.3.2: merge dedup, tool collapse, skill sanitize`

Planning/product guidance status:
- `thoughts/specs/product_intent.md` is absent.
- `thoughts/plans/AGENTS.md` is absent.
- This plan therefore aligns directly to the active user request, root `AGENTS.md`, and shared planning/product doctrine.

## Current implementation reality

### Vendored package shape today
- The repo installs the local vendored package from `./_pi/packages/pi-vcc`, not upstream npm directly.
- The vendored copy already carries repo-local behavior in at least these explicit places:
  - `src/commands/pi-vcc.ts` embeds the `__PI_VCC_MANUAL_BYPASS__` marker directly in source.
  - `src/hooks/before-compact.ts` adds the agent-only fallback tail compaction behavior.
- The vendored README currently documents only those two local deltas, but the upstream checker shows broader divergence in core summarization files.

### Upstream drift reality today
Running `bash ./scripts/check-pi-vcc-upstream.sh` reports:
- vendored upstream version `0.3.0`
- npm latest `0.3.2`
- upstream head changed since the recorded snapshot
- unexpected local diffs in:
  - `src/core/brief.ts`
  - `src/core/build-sections.ts`
  - `src/core/content.ts`
  - `src/core/format.ts`
  - `src/core/summarize.ts`
  - `src/extract/goals.ts`
  - `tests/brief.test.ts`
  - `tests/format.test.ts`
  - plus upstream-only `src/core/skill-collapse.ts`

### Upstream changes worth considering
From the captured upstream commit summaries and file list, the meaningful upstream improvements are:
- stronger `<skill>` content collapsing / sanitization
- better summary merge and file-path dedup behavior
- collapse of repeated identical tool lines in the brief transcript
- safer text clipping/formatting edge handling
- test updates that codify those semantics

These are valuable for this repo because Pi sessions here frequently include skill markup and long tool-heavy transcripts.

### Root cause of the GPT post-compaction failure
The session evidence shows a concrete compaction-boundary bug.

In the cited session file:
- assistant message `4b9e05dd` contains a `bash` tool call with id `call_F9axV0xmAqYY5VXvVuMivuy3|...`
- the following `toolResult` message is `c9396f98`
- the compaction entry `5130bda2` records `firstKeptEntryId: "c9396f98"`
- the assistant tool-call message `4b9e05dd` was summarized into the compaction output, not kept live
- later, when GPT resumed, Pi surfaced:
  - `No tool call found for function call output with call_id call_F9axV0xmAqYY5VXvVuMivuy3.`

The immediate cause is the fallback-tail cut logic in `_pi/packages/pi-vcc/src/hooks/before-compact.ts`:
- when there is no later user boundary, it keeps the last `AGENT_ONLY_FALLBACK_TAIL_MESSAGES = 4` live messages
- that policy can begin at a `toolResult`
- Pi/OpenAI Responses requires the corresponding assistant tool call to remain in the live window if the tool result remains live

This is exactly the kind of overly aggressive tool-call compaction the user described from prior failures.

### Specific design gap in current tests
`_pi/packages/pi-vcc/tests/before-compact.test.ts` covers agent-only fallback tails, but its current fallback test keeps `firstKeptEntryId = "5"`, which starts at an assistant text message, not a tool result. There is no regression test that proves compaction never starts the live tail at a `toolResult` or otherwise orphans tool-call/result pairs.

## Progress

- [x] P1a Add fixture support for distinct tool-call ids
- [x] P1b Add the orphaned-tool-result regression in red
- [x] P2 Fix fallback-tail cut policy so live context never starts mid tool-call/result pair
- [x] P3 Uptake selected upstream `0.3.1`/`0.3.2` semantic improvements
- [x] P4 Restore truthful drift reporting, docs, and install verification

## Resume instructions (agent)

Read this document fully. Start with the first unchecked item in `## Progress`. Execute phases in order. Preserve the repo-local manual compaction command behavior and the agent-only fallback concept, but change the fallback cut policy so tool results are never kept without their matching assistant tool-call message. Keep the uptake selective and evidence-driven rather than doing a blind re-vendor.

## Product intent alignment

`pi-vcc` is workflow infrastructure. Its default path must be safe for long-running agent sessions without forcing operators to understand compaction internals.

That means:
- compaction must preserve a valid live context for the active model/runtime, not just a compact readable summary,
- routine agent-only tails should still compact automatically,
- known recoverable context-boundary problems should be prevented in the compactor rather than exported as opaque post-compaction model errors,
- the vendored drift signal should remain truthful so operators know whether they are on a clean pinned fork or a silently diverged one.

The correct default is: if a tool result remains live, the matching tool call must also remain live.

## Locked decisions

1. Do not replace the vendored package with the upstream npm package directly; this repo intentionally installs `./_pi/packages/pi-vcc`.
2. Preserve the repo-local `__PI_VCC_MANUAL_BYPASS__` behavior in `src/commands/pi-vcc.ts`.
3. Preserve the repo-local agent-only fallback concept in `src/hooks/before-compact.ts`.
4. Fix the compaction bug at the cut-policy/source-selection layer, not by suppressing or rewording the downstream GPT error.
5. The live window after compaction must never begin on a `toolResult` whose matching assistant tool call was compacted away.
6. Uptake upstream `0.3.1`/`0.3.2` selectively and manually; do not do a blind bump or wholesale overwrite.
7. Do not update `scripts/check-pi-vcc-upstream.sh` to bless broader drift unless the vendored tree is intentionally reconciled and documented.
8. Treat summary-output changes as behavioral changes that require test updates, not as incidental churn.
9. Prefer adding explicit regression tests for tool-call/result pairing over relying on informal session repros.

## Acceptance criteria

1. `pi-vcc` compaction never leaves a live `toolResult` without the matching live assistant tool call.
2. The cited GPT Responses failure mode is covered by regression tests at the compaction hook level.
3. The vendored package retains the repo-local manual bypass and agent-only fallback behaviors.
4. Selected upstream `0.3.1`/`0.3.2` improvements are merged without regressing local compaction behavior.
5. `bash ./scripts/check-pi-vcc-upstream.sh` becomes either clean or truthfully reports only intentionally documented remaining local deltas.
6. `bash ./install.sh --pi` still installs the vendored package successfully after the uptake.
7. `_pi/packages/pi-vcc` tests pass after the merge.

## BDD scenarios

### B1 - Tool result cannot outlive its tool call
Given a session with assistant tool call A followed by tool result R
And no later user boundary exists before compaction
When `pi-vcc` falls back to keeping a recent non-user tail
Then the kept live window must include both A and R
And the first kept entry must not be R alone

### B2 - Agent-only tails still compact
Given a long agent-only tail with no later user boundary
When compaction runs
Then `pi-vcc` still compacts the older prefix
And still keeps a recent live tail
But does not cut in the middle of a tool-call/result pair

### B3 - Previous summary skill markup is sanitized
Given a previous summary that contains `<skill>` blocks or skill markup artifacts
When new summary content is merged
Then the merged summary should not carry raw skill markup forward

### B4 - Repeated tool lines are reduced
Given a tool-heavy brief transcript with consecutive identical tool summaries
When the summary is compiled
Then repeated identical lines collapse according to the chosen upstream behavior
Without hiding materially distinct tool invocations

### B5 - Drift reporting becomes trustworthy again
Given the vendored tree after the selected uptake
When `bash ./scripts/check-pi-vcc-upstream.sh` runs
Then the output reflects the real intentional local patch set
And no longer treats reconciled files as unexplained drift

## Phase-by-phase execution plan

## Phase 1a - Add fixture support for distinct tool-call ids

### End State
The compaction-hook test fixtures can represent multiple tool-call/result pairs unambiguously, so pair-integrity regressions are not blocked by shared synthetic ids.

### Tests first
- Extend `_pi/packages/pi-vcc/tests/fixtures.ts` so assistant tool calls and tool results can opt into distinct synthetic tool-call ids.
- Update existing `before-compact` coverage to use explicit ids where multiple tool pairs appear in one transcript.

### Work
- Keep the fixture change minimal and backwards-compatible for untouched tests.
- Limit edits to the compaction-hook test support and touched `before-compact` cases.

### Expected files
- `_pi/packages/pi-vcc/tests/fixtures.ts`
- `_pi/packages/pi-vcc/tests/before-compact.test.ts`

### Verify
- `cd _pi/packages/pi-vcc && bun test tests/before-compact.test.ts --test-name-pattern '(falls back|still prefers)'`

## Phase 1b - Add the orphaned-tool-result regression in red

### End State
A focused regression demonstrates the current bug by proving fallback-tail compaction can start the live window at a `toolResult`, orphaning its assistant tool call.

### Tests first
- Add a failing regression in `_pi/packages/pi-vcc/tests/before-compact.test.ts` covering:
  - assistant tool call
  - matching tool result
  - additional assistant/tool activity after that pair
  - fallback-tail compaction with no later user boundary
  - assertion that the first kept entry is the assistant tool call, not the tool result

### Work
- Keep the regression focused on cut selection and `firstKeptEntryId`, because that is where the root cause lives.
- Preserve the current failing expectation as the handoff contract into Phase 2.

### Expected files
- `_pi/packages/pi-vcc/tests/before-compact.test.ts`

### Verify
- `cd _pi/packages/pi-vcc && ! bun test tests/before-compact.test.ts --test-name-pattern 'keeps the matching assistant tool call live when fallback would start at a tool result'`

## Phase 2 - Fix the fallback-tail cut policy

### End State
The compaction hook preserves a coherent live tail for Responses-based GPT models by ensuring tool-call/result pairs stay together.

### Tests first
- Use the new failing regression from Phase 1.
- Add a second focused case if needed for multiple consecutive tool-call/result pairs.

### Work
- Update `_pi/packages/pi-vcc/src/hooks/before-compact.ts` so the computed `cutIdx` is adjusted when the would-be first kept live message is a `toolResult`.
- Preserve the current preference order:
  - latest user boundary first,
  - recent non-user tail fallback second.
- Ensure the fallback cut keeps the preceding assistant tool-call message whenever the first kept message would otherwise be a tool result.
- Keep the fix minimal; do not redesign unrelated summary behavior in this phase.

### Expected files
- `_pi/packages/pi-vcc/src/hooks/before-compact.ts`
- `_pi/packages/pi-vcc/tests/before-compact.test.ts`

### Verify
- `cd _pi/packages/pi-vcc && bun test tests/before-compact.test.ts`
- optionally replay the cited session structure in a focused fixture if needed

## Phase 3 - Uptake selected upstream semantic improvements

### End State
The vendored tree adopts the chosen upstream `0.3.1`/`0.3.2` summary-quality improvements while preserving repo-local hook/command behavior.

### Tests first
- Capture the current drift baseline:
  - `bash ./scripts/check-pi-vcc-upstream.sh`
- Run package tests before merging upstream changes:
  - `cd _pi/packages/pi-vcc && bun test`

### Work
- Review and merge the overlapping upstream changes in:
  - `src/core/brief.ts`
  - `src/core/build-sections.ts`
  - `src/core/content.ts`
  - `src/core/format.ts`
  - `src/core/summarize.ts`
  - `src/extract/goals.ts`
  - related tests
- Decide explicitly whether to add upstream `src/core/skill-collapse.ts` as-is or fold its logic into the existing sanitize/normalize flow.
- Preserve:
  - `src/commands/pi-vcc.ts`
  - `src/hooks/before-compact.ts`
  - any repo-local behavior these files require

### Expected files
- `_pi/packages/pi-vcc/src/core/brief.ts`
- `_pi/packages/pi-vcc/src/core/build-sections.ts`
- `_pi/packages/pi-vcc/src/core/content.ts`
- `_pi/packages/pi-vcc/src/core/format.ts`
- `_pi/packages/pi-vcc/src/core/summarize.ts`
- `_pi/packages/pi-vcc/src/core/skill-collapse.ts` (if adopted)
- `_pi/packages/pi-vcc/src/extract/goals.ts`
- `_pi/packages/pi-vcc/tests/brief.test.ts`
- `_pi/packages/pi-vcc/tests/format.test.ts`
- `_pi/packages/pi-vcc/tests/*` as needed for upstream behavior changes

### Verify
- `cd _pi/packages/pi-vcc && bun test`
- Confirm summary-formatting and merge tests reflect the intended new semantics

## Phase 4 - Reconcile drift reporting, docs, and installation

### End State
The repo documents the final vendored state accurately, and installer/upstream-check output tells the truth again.

### Tests first
- Re-run the upstream checker on the merge candidate:
  - `bash ./scripts/check-pi-vcc-upstream.sh`
- Re-run local Pi installation:
  - `bash ./install.sh --pi`

### Work
- Update `_pi/packages/pi-vcc/README.md` so the documented local deltas match reality after the uptake.
- Update `_pi/packages/pi-vcc/package.json` metadata if the effective upstream snapshot changes.
- Update `scripts/check-pi-vcc-upstream.sh` expected local diffs only if the reconciled vendored state intentionally changes the patch set.
- Confirm the installer still surfaces useful upstream status rather than hiding divergence.

### Expected files
- `_pi/packages/pi-vcc/README.md`
- `_pi/packages/pi-vcc/package.json`
- `scripts/check-pi-vcc-upstream.sh`
- `install.sh` only if implementation reveals real installer coupling that must change

### Verify
- `bash ./scripts/check-pi-vcc-upstream.sh`
- `bash ./install.sh --pi`
- `git diff -- _pi/packages/pi-vcc scripts/check-pi-vcc-upstream.sh install.sh`

## Verification strategy

Primary execution gates:
- `_pi/packages/pi-vcc` unit/regression tests
- upstream drift checker output
- a real `bash ./install.sh --pi` rerun after the uptake

Critical semantic verification:
- the compaction hook must keep tool-call/result pairs coherent in live context
- summary hygiene improvements must be intentionally reviewed because transcript output will change

## Delivery order

1. Lock the orphaned-tool-result regression first.
2. Fix the cut-policy bug second.
3. Merge selected upstream semantic changes third.
4. Reconcile docs, drift reporting, and installation last.

## Non-goals

- Replacing vendored `pi-vcc` with direct upstream npm install
- Redesigning the entire compaction algorithm
- Suppressing the downstream GPT error without fixing the cut-policy root cause
- Broad unrelated Pi plan-mode changes

## Decisions / Deviations log

### 2026-04-11 - Root cause confirmed for GPT post-compaction failure
- The failure is not a generic OpenAI glitch.
- The compaction entry in the cited session kept `firstKeptEntryId = c9396f98`, which is a `toolResult` message.
- The matching assistant tool call lived in `4b9e05dd` and was compacted into the summary.
- This leaves an invalid Responses resume context and matches the historical class of aggressive tool-call purging called out by the user.

### 2026-04-11 - Uptake recommendation
- Upstream uptake is still worthwhile.
- The most valuable upstream changes are the summary-hygiene improvements around skill markup, dedup, and tool-line collapse.
- The cut-policy bug should be fixed before or alongside the upstream merge, because it is an active correctness issue for GPT sessions rather than merely an upstream drift concern.

### 2026-04-11 - Phase 1 same-scope split after review
- The original P1 mixed two independently verifiable outcomes: fixture support for distinct tool-call ids and the expected-red regression that exposes the orphaned `toolResult` bug.
- The required post-implementation review concluded `Phase needs same-scope split.` because the red regression is correct but cannot satisfy pass-style verification until Phase 2 fixes the hook.
- P1 was split into P1a (fixture support) and P1b (expected-red regression) without changing scope, acceptance criteria, or the later cut-policy fix work.
- Evidence: `cd _pi/packages/pi-vcc && bun test tests/before-compact.test.ts` produced `Expected: "3" Received: "4"` for the new regression.

### 2026-04-11 - Phase 3 selective uptake scope
- Adopted upstream summary-quality changes in `src/core/brief.ts`, `src/core/build-sections.ts`, `src/core/content.ts`, `src/extract/goals.ts`, and merge logic in `src/core/summarize.ts`, plus upstream `src/core/skill-collapse.ts`.
- Preserved repo-local compaction hook and manual command behavior, and kept a repo-local extension in `src/core/summarize.ts` that strips raw `<skill>` markup from previously merged brief text.
- Intentionally did **not** uptake the upstream summary tail note about `vcc_recall`; the review pass found it changed the shipped summary contract without being part of this plan's acceptance criteria.
- Evidence: `cd _pi/packages/pi-vcc && bun test` passed after removing the injected note and adding a regression that strips previously injected note lines during future merges.

### 2026-04-11 - Phase 3 test harness repair
- Full package verification initially failed because `tests/support/load-session.ts` assumed a vendored local `node_modules` copy of `@mariozechner/pi-coding-agent` that does not exist in this repo.
- The test helper now resolves `session-manager.js` from an override path, a repo-local install if present, or the globally installed Pi package path used in this environment.
- This was required to satisfy the plan's package-wide `bun test` verification and acceptance criterion that `_pi/packages/pi-vcc` tests pass after the uptake.

### 2026-04-11 - Phase 4 drift reporting and metadata reconciliation
- Updated vendored metadata to `0.3.2-ai-configs.1` and recorded upstream commit `82e31a5e4bd22d81bcf08b33750cbcf11e603157` in `_pi/packages/pi-vcc/README.md` and `package.json`.
- `scripts/check-pi-vcc-upstream.sh` now treats the current repo-local patch set as expected and prints an explicit `drift status:` line so success output says whether the vendored fork is clean, expectedly patched, or unexpectedly drifted.
- `install.sh` now forwards that drift status and says the vendored copy matches the pinned upstream snapshot **with the expected local patch set**, avoiding the earlier ambiguous success wording.
- The remaining intentional local patch set is: manual bypass command wiring, compaction-hook cut safety, summary merge/format deltas, repo-specific tests/fixtures, and the local session-loader harness for package-wide verification.
