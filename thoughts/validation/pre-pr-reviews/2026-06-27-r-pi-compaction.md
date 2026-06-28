# Pre-PR Implementation Review — r-pi-compaction

Date: 2026-06-27
Branch: `r-pi-compaction`
Plan: `thoughts/plans/pi-vcc-semantic-compaction-plan.html`

## Scope

Pi VCC semantic compaction implementation:

- keep VCC as the default compaction path;
- change 60%/75% thresholds to model-visible nudges, not automatic compaction;
- add queued `compact_context` semantic-boundary compaction with marker+JSON intent;
- retain 80% hard-backstop compaction and overflow retry safety;
- add deterministic pruning before summary rendering;
- remove/defer commit extraction after review showed low value and high parser complexity;
- preserve recall, redaction, fallback-tail, and in-flight continuation behavior;
- keep upstream drift metadata/checker aligned with reviewed upstream `0.3.18`.

## Current changed files

```text
_pi/extensions/percentage-compaction.ts
_pi/packages/pi-vcc/src/core/brief.ts
_pi/packages/pi-vcc/src/core/build-sections.ts
_pi/packages/pi-vcc/src/core/format.ts
_pi/packages/pi-vcc/src/core/summarize.ts
_pi/packages/pi-vcc/src/extract/commits.ts (deleted)
_pi/packages/pi-vcc/src/hooks/before-compact.ts
_pi/packages/pi-vcc/tests/before-compact.test.ts
_pi/packages/pi-vcc/tests/compile.test.ts
scripts/check-pi-vcc-upstream.sh
scripts/percentage-compaction.test.ts
thoughts/plans/pi-vcc-semantic-compaction-plan.html
```

Diff size after commit-extraction removal: 13 files, 243 insertions, 252 deletions.

## Verification before commit-extraction removal (stale)

| Command | Result |
| --- | --- |
| `bun test _pi/packages/pi-vcc/tests/compile.test.ts` | PASS — 170 tests, 376 expects |
| `bun test scripts/percentage-compaction.test.ts` | PASS — 21 tests, 66 expects |
| `bun test _pi/packages/pi-vcc/tests` | PASS — 290 tests, 634 expects |
| `bash ./scripts/check-pi-vcc-upstream.sh --summary` | PASS — reviewed upstream matches npm/upstream head; only intentional diffs |
| `git diff --check` | PASS |
| `./install.sh --pi` | PASS — Installation complete |

## Verification after commit-extraction removal

| Command | Result |
| --- | --- |
| `bun test _pi/packages/pi-vcc/tests/compile.test.ts` | PASS — 20 tests, 50 expects |
| `bun test _pi/packages/pi-vcc/tests` | PASS — 140 tests, 308 expects |
| `bun test scripts/percentage-compaction.test.ts` | PASS — 21 tests, 66 expects |
| `bash ./scripts/check-pi-vcc-upstream.sh --summary` | PASS — reviewed upstream matches npm/upstream head; only intentional diffs |
| `git diff --check` | PASS |
| `./install.sh --pi` | PASS — Installation complete |

## Review cycle 1

Current-diff review gates launched after the latest quiet-setup fix and verification:

| Reviewer | Agent ID | Slice | Status |
| --- | --- | --- | --- |
| GPT quality-reviewer | `3126c88d-e588-45a` | Whole current diff | Running |
| GLM quality-reviewer-glm | `3442f726-8d1e-4b6` | Commit/git extraction and `[Commits]` context | Running |
| GLM quality-reviewer-glm | `b4e1bcbe-37f8-49c` | Runtime compaction, pruning/summary, verification truthfulness | Queued/running |

### Triage table

Several older/stale review gates completed after subsequent patches. Their still-valid findings were treated as in scope and fixed. Stale GPT gates `c961a2f5-d465-4b0` and `3126c88d-e588-45a` reported no issues for earlier snapshots; both are superseded by refreshed cycle 2 gates.

| Finding | Reviewer | Severity | Scope | Decision | Evidence |
| --- | --- | --- | --- | --- | --- |
| Valid env-prefixed git commands such as `GIT_PAGER=cat git log --oneline -1` were ignored. | GLM stale gates `f219054d-a903-492`, `0608fb7f-c3ad-4b7` | P3 | REGRESSION_FROM_THIS_DIFF | Fixed | `readGitCommandName` now skips leading shell env assignments; regression `keeps log evidence after env assignment prefixes` passes. |
| Successful multiline `git commit -m` messages dropped the real commit. | GLM stale gate `f219054d-a903-492` | P3 | REGRESSION_FROM_THIS_DIFF | Fixed | `cleanLiteralSubject` now matches only the first subject line; regression `keeps multiline commit message evidence by matching the subject line` passes. |
| Valid bounded multi-commit `git log --oneline --name-only -2` output without blank separators lost later commits. | GLM stale gate `37f62164-efe1-455` | P2 | REGRESSION_FROM_THIS_DIFF | Fixed | Bounded name-only output now accepts in-record headers when candidate count matches max-count while preserving ambiguity guards; regression `keeps bounded in-record name-only log headers without blank separators` passes. |
| Bounded `--name-only -N` could promote a hash-shaped root filename when fewer than N commits matched. | GLM commit slice `3442f726-8d1e-4b6`, GPT latest gate `d7f99fb5-0c20-458` | P2 | REGRESSION_FROM_THIS_DIFF / IN_PLAN | Fixed | Removed bound-count-as-proof shortcut and reject ambiguous file-like in-record rows; regressions `does not promote bounded name-only root filenames when fewer commits match` and `does not fabricate commits from name-only root files followed by paths` pass. |
| Valid fewer-than-N bounded `--name-only` output could lose later real commits or misattribute files. | GPT post-fix gate `cd33338e-8824-40b` | P2 | REGRESSION_FROM_THIS_DIFF | Fixed | Fewer-than-bound in-record headers are accepted when not ambiguous and candidate slices drive file attribution; regression `keeps fewer-than-bound in-record name-only log headers` passes. |
| Semicolon/newline-separated `git commit ...; git status` could record hook output as a commit after the commit failed but status returned 0. | GPT latest gate `d7f99fb5-0c20-458`, GPT cycle 5 gate `1e02dead-c6b4-4dd` | P2 | IN_PLAN | Fixed | Commit extraction now fails closed across `;` and newline exit-masking boundaries, including no-literal-subject commit forms; regressions `does not parse hook output when semicolon status masks a failed commit` and `does not parse hook output when semicolon status masks a file-message commit` pass. |
| Implicit repo/global `format.pretty` could make body text fabricate full-header commits for `git log` / `git log -1`. | GLM commit slice `3442f726-8d1e-4b6`, GLM post-fix commit review `1f8075ed-cd13-433`, GPT cycle 5 gate `1e02dead-c6b4-4dd` | P2/P3 | REGRESSION_FROM_THIS_DIFF / IN_PLAN | Fixed | Implicit full-header parsing now requires default full-header metadata while explicit full-header pretty formats still parse; regressions `keeps implicit default full-header single log output with metadata`, `does not parse commit-shaped body text from implicit pretty config`, `does not parse unbounded commit-shaped body text from implicit pretty config`, and `does not parse commit-shaped body text starting implicit pretty config output` pass. |
| Full-header path-only output could attribute path-like commit-message text as changed files. | GLM latest commit review `a476130c-5d39-46e` | P3 | REGRESSION_FROM_THIS_DIFF | Fixed | Path extraction skips indented commit-message lines; regression `does not attribute full-header commit message paths as changed files` passes. |
| Multi-commit file lists were extracted from the whole git output for every commit. | GLM commit slice `3442f726-8d1e-4b6` | P3 | REGRESSION_FROM_THIS_DIFF | Fixed | Commit file extraction now uses the candidate's output slice; regression checks per-commit files for bounded name-only output. |
| Empty env assignment prefixes and `env VAR=value git ...` were not recognized as git commands. | GPT refreshed gate `b9d567c4-6e25-469` | P3 | IN_PLAN | Fixed | Env prefix recognition now accepts empty assignment values and simple `env` assignment prefixes; expanded `keeps log evidence after env assignment prefixes` regression passes. |
| Leading spaces in custom format values were trimmed before hash-first classification, allowing indented non-hash-first formats to fabricate commits from path rows. | GLM stale gate `cb32f2bb-87b6-491` | P2 | REGRESSION_FROM_THIS_DIFF | Fixed | Format value classification now preserves leading whitespace; regression `does not trim leading spaces when classifying hash-first formats` passes. |
| Title Case multi-word extensionless root filenames in bounded `--name-only` output could still fabricate commits. | GPT cycle 6 gate `2b475ac4-3337-496` | P2 | REGRESSION_FROM_THIS_DIFF | Fixed | Name-only in-record ambiguity now requires subject text to match common commit-subject verbs before promotion; regression `does not fabricate commits from title-case extensionless name-only root files` passes. |
| Implicit `git log` / `git log -1` body output copied from a full header with `Date:` could fabricate commits. | GPT cycle 6 gate `2b475ac4-3337-496` | P3 | REGRESSION_FROM_THIS_DIFF | Fixed | Implicit full-header log parsing now fails closed for single copied default-looking blocks while still accepting multi-entry full logs and explicit full-header pretty formats; regression `does not parse copied default-looking body text from implicit pretty config` passes. |
| Runtime GLM verification-truthfulness finding reported failing compile/full tests for an intermediate patch. | GLM cycle 6 runtime gate `c3cd10d5-572c-4ed` | P2 | REGRESSION_FROM_THIS_DIFF | Fixed | The failing intermediate patch was corrected; current verification now passes with `compile.test.ts` 164/0 and full pi-vcc tests 284/0. |
| Copied merge-commit body text under implicit body-only pretty config could still fabricate a commit because `Merge:` alone was accepted as default full-header metadata. | GLM cycle 6 commit gate `7a05a8a4-9291-40d` | P2 | REGRESSION_FROM_THIS_DIFF | Fixed | Implicit full-header metadata no longer accepts `Merge:` alone; regression `does not parse copied merge-header body text from implicit pretty config` passes. |
| Real default `git log -1` output was dropped because the positive fixture used an indented `Date:` line rather than git's unindented `Date:   ...` metadata. | GPT/GLM cycle 7 gates `c7c3417f-3526-41a`, `fcad57d8-a21d-4f2` | P2 | IN_PLAN / REGRESSION_FROM_THIS_DIFF | Fixed | Implicit full-header single-log parsing now accepts real default `Date:   ...` metadata while copied body false-positive regressions keep one-space `Date:` blocked. |
| Filtered implicit default `git log --grep=...` with a single real full-header result was still dropped. | GPT cycle 8 gate `07a264c7-dc31-479` | P2 | IN_PLAN | Fixed | Implicit full-header log parsing now accepts single-result filtered logs with default metadata; regression `keeps implicit default full-header filtered log output with one result` passes. |
| Copied full-header body text with real `Date:   ...` spacing could still be promoted as a fake implicit `git log` commit. | GLM cycle 8 commit gate `1180fc2f-cc83-458` | P2 | IN_PLAN | Fixed | Single implicit full-header log blocks now require default-looking author identity as well as date metadata; regression `does not parse real-spacing copied default body text from implicit pretty config` passes. |
| Real bounded `--name-only` commits with ordinary subjects such as `Initial import` / `Polish UI` were dropped and could bleed files into the prior commit. | GLM cycle 8 commit gate `1180fc2f-cc83-458` | P2 | REGRESSION_FROM_THIS_DIFF | Fixed | Complete unfiltered bounded name-only pages accept ordinary subjects while ambiguous fewer-than-bound root-file cases remain blocked; regression `keeps bounded name-only headers with ordinary subjects` passes. |
| Safe setup commands separated from `git commit` by newline or semicolon lost real commit evidence. | GLM cycle 8 commit gate `1180fc2f-cc83-458` | P3 | REGRESSION_FROM_THIS_DIFF | Fixed | Commit exit-masking checks are now segment-relative; regressions `keeps commit evidence after newline setup commands` and `keeps commit evidence after semicolon setup commands` pass. |
| Bracket-style `git commit` file attribution could scan subject/free-form output as changed files. | GLM cycle 8 commit gate `1180fc2f-cc83-458` | P3 | IN_PLAN | Fixed | Commit file extraction ignores the bracket subject line and only accepts path-shaped indented detail lines; regression `does not attribute commit subject paths as changed files` passes. |

### Verification after stale-gate fixes

| Command | Result |
| --- | --- |
| `bun test _pi/packages/pi-vcc/tests/compile.test.ts` | PASS — 150 tests |
| `bun test scripts/percentage-compaction.test.ts` | PASS — 20 tests |
| `bun test _pi/packages/pi-vcc/tests` | PASS — 269 tests |
| `bash ./scripts/check-pi-vcc-upstream.sh --summary` | PASS — reviewed upstream matches npm/upstream head; only intentional diffs |
| `git diff --check` | PASS |
| `./install.sh --pi` | PASS — Installation complete |

### Verification after GLM commit-slice fixes

| Command | Result |
| --- | --- |
| `bun test _pi/packages/pi-vcc/tests/compile.test.ts` | PASS — 152 tests |
| `bun test scripts/percentage-compaction.test.ts` | PASS — 20 tests |
| `bun test _pi/packages/pi-vcc/tests` | PASS — 271 tests |
| `bash ./scripts/check-pi-vcc-upstream.sh --summary` | PASS — reviewed upstream matches npm/upstream head; only intentional diffs |
| `git diff --check` | PASS |
| `./install.sh --pi` | PASS — Installation complete |

### Verification after latest review fixes

| Command | Result |
| --- | --- |
| `bun test _pi/packages/pi-vcc/tests/compile.test.ts` | PASS — 164 tests, 367 expects |
| `bun test scripts/percentage-compaction.test.ts` | PASS — 21 tests, 66 expects |
| `bun test _pi/packages/pi-vcc/tests` | PASS — 284 tests, 625 expects |
| `bash ./scripts/check-pi-vcc-upstream.sh --summary` | PASS — reviewed upstream matches npm/upstream head; only intentional diffs |
| `git diff --check` | PASS |
| `./install.sh --pi` | PASS — Installation complete |

## Review cycle 2

Refreshed current-diff review gates launched after fixing stale-gate findings and rerunning verification:

| Reviewer | Agent ID | Slice | Status |
| --- | --- | --- | --- |
| GPT quality-reviewer | `b9d567c4-6e25-469` | Whole current diff | Queued/running |
| GLM quality-reviewer-glm | `9c0d2b42-be4a-429` | Commit/git extraction and `[Commits]` context | Queued/running |
| GLM quality-reviewer-glm | `ce732f76-06bd-4ba` | Runtime compaction, pruning/summary, verification truthfulness | Queued/running |

## Review cycle 3

Post-GLM-commit-fix review gates launched after fixing `3442f726-8d1e-4b6` findings and rerunning verification:

| Reviewer | Agent ID | Slice | Status |
| --- | --- | --- | --- |
| GPT quality-reviewer | `cd33338e-8824-40b` | Whole current diff | Queued/running |
| GLM quality-reviewer-glm | `1f8075ed-cd13-433` | Commit/git extraction and `[Commits]` context | Queued/running |
| GLM quality-reviewer-glm | `15417a1c-1961-458` | Runtime compaction, pruning/summary, verification truthfulness | Queued/running |

## Review cycle 4

Latest review gates launched after fixing `b9d567c4-6e25-469` and `cb32f2bb-87b6-491` findings and rerunning verification:

| Reviewer | Agent ID | Slice | Status |
| --- | --- | --- | --- |
| GPT quality-reviewer | `d7f99fb5-0c20-458` | Whole current diff | Completed — findings fixed in cycle 5 |
| GLM quality-reviewer-glm | `a476130c-5d39-46e` | Commit/git extraction and `[Commits]` context | Running/superseded by cycle 5 fixes |
| GLM quality-reviewer-glm | `47562a09-b879-4e7` | Runtime compaction, pruning/summary, verification truthfulness | Running/superseded by cycle 5 fixes |

## Review cycle 5

Fresh current-diff review gates launched after fixing latest GPT findings and rerunning verification:

| Reviewer | Agent ID | Slice | Status |
| --- | --- | --- | --- |
| GPT quality-reviewer | `1e02dead-c6b4-4dd` | Whole current diff | Completed — findings fixed in cycle 6 |
| GLM quality-reviewer-glm | `76f19dbc-6c3e-400` | Commit/git extraction and `[Commits]` context | Running; steered to current cycle 6 diff |
| GLM quality-reviewer-glm | `0581874f-7422-421` | Runtime compaction, pruning/summary, verification truthfulness | Completed with no output; superseded by cycle 6 runtime gate |

## Review cycle 6

Fresh current-diff review gates launched/steered after fixing cycle 5 GPT and GLM findings and rerunning verification:

| Reviewer | Agent ID | Slice | Status |
| --- | --- | --- | --- |
| GPT quality-reviewer | `2b475ac4-3337-496` | Whole current diff | Completed — findings fixed in cycle 7 |
| GLM quality-reviewer-glm | `76f19dbc-6c3e-400` | Commit/git extraction and `[Commits]` context | Completed without verdict; superseded by `7a05a8a4-9291-40d` |
| GLM quality-reviewer-glm | `7a05a8a4-9291-40d` | Commit/git extraction and `[Commits]` context | Running/superseded by cycle 7 current-diff gates |
| GLM quality-reviewer-glm | `c3cd10d5-572c-4ed` | Runtime compaction, pruning/summary, verification truthfulness | Completed — intermediate verification finding fixed in cycle 7 |

### Verification after cycle 7 fixes

| Command | Result |
| --- | --- |
| `bun test _pi/packages/pi-vcc/tests/compile.test.ts` | PASS — 164 tests, 367 expects |
| `bun test scripts/percentage-compaction.test.ts` | PASS — 21 tests, 66 expects |
| `bun test _pi/packages/pi-vcc/tests` | PASS — 284 tests, 625 expects |
| `bash ./scripts/check-pi-vcc-upstream.sh --summary` | PASS — reviewed upstream matches npm/upstream head; only intentional diffs |
| `git diff --check` | PASS |
| `./install.sh --pi` | PASS — Installation complete |

## Review cycle 7

Fresh current-diff review gates launched after fixing cycle 6 findings and rerunning verification:

| Reviewer | Agent ID | Slice | Status |
| --- | --- | --- | --- |
| GPT quality-reviewer | `c7c3417f-3526-41a` | Whole current diff | Completed — real `git log -1` finding fixed in cycle 8 |
| GLM quality-reviewer-glm | `d5e1bf64-5904-427` | Runtime compaction, pruning/summary, verification truthfulness | Completed clean; superseded by cycle 8 current-diff gates |
| GLM quality-reviewer-glm | `fcad57d8-a21d-4f2` | Commit/git extraction and `[Commits]` context | Completed — real `git log -1` finding fixed in cycle 8 |

## Review cycle 8

Fresh current-diff review gates launched after fixing the cycle 7 real default `git log -1` extraction finding and rerunning verification:

| Reviewer | Agent ID | Slice | Status |
| --- | --- | --- | --- |
| GPT quality-reviewer | `07a264c7-dc31-479` | Whole current diff | Completed — filtered implicit log finding fixed in cycle 9 |
| GLM quality-reviewer-glm | `394cf384-790c-415` | Runtime compaction, pruning/summary, verification truthfulness | Completed clean / superseded by cycle 9 current-diff gates |
| GLM quality-reviewer-glm | `1180fc2f-cc83-458` | Commit/git extraction and `[Commits]` context | Completed — four commit-slice findings fixed in cycle 9 |

### Verification after cycle 8 fixes

| Command | Result |
| --- | --- |
| `bun test _pi/packages/pi-vcc/tests/compile.test.ts` | PASS — 170 tests, 376 expects |
| `bun test scripts/percentage-compaction.test.ts` | PASS — 21 tests, 66 expects |
| `bun test _pi/packages/pi-vcc/tests` | PASS — 290 tests, 634 expects |
| `bash ./scripts/check-pi-vcc-upstream.sh --summary` | PASS — reviewed upstream matches npm/upstream head; only intentional diffs |
| `git diff --check` | PASS |
| `./install.sh --pi` | PASS — Installation complete |

## Review cycle 9

Fresh current-diff review gates launched after fixing cycle 8 findings and rerunning verification:

| Reviewer | Agent ID | Slice | Status |
| --- | --- | --- | --- |
| GPT quality-reviewer | `b4f0e94a-1a41-4ea` | Whole current diff | Completed — reported one P2 in commit extraction; resolved by removing/deferring commit extraction |
| GLM quality-reviewer-glm | `668094ba-c4a3-47f` | Commit/git extraction and `[Commits]` context | Stopped by operator request; no verdict |
| GLM quality-reviewer-glm | `c750c30a-6a07-481` | Runtime compaction, pruning/summary, verification truthfulness | Stopped by operator request; incomplete verdict |

## Pause / reassessment

Review loop paused by operator request after cycle 9 started. The remaining completed GPT finding was another ambiguous `git log --oneline --name-only -N` edge case in `_pi/packages/pi-vcc/src/extract/commits.ts`, confirming commit extraction had become the unstable/high-cost slice.

Decision: remove/defer commit extraction instead of continuing to patch parser edge cases. Keep the lower-risk compaction threshold, queued compaction, and pruning changes.

## Review cycle 10 — simplified no-commit-extraction diff

Fresh current-diff review gates launched after removing/deferring commit extraction and rerunning verification. Base is `origin/main`; same-named upstream `origin/r-pi-compaction` was not used as the PR base.

| Reviewer | Agent ID | Slice | Status |
| --- | --- | --- | --- |
| GPT quality-reviewer | `4bbcece0-f808-41b` | Whole current diff | Completed — findings to resolve |
| GLM quality-reviewer-glm | `ce046ddf-9fa0-42d` | Runtime compaction lifecycle | Completed — findings to resolve |
| GLM quality-reviewer-glm | `b8c4f774-570b-443` | Summary/pruning/docs/verification | Completed — findings to resolve |

### Cycle 10 triage — partial, GPT only

| Finding | Reviewer | Severity | Scope | Decision | Evidence |
| --- | --- | --- | --- | --- | --- |
| Mixed-tool `compact_context` can compact before sibling tool output is interpreted. | GPT `4bbcece0-f808-41b` | P2 | IN_PLAN | Pending fix after GLM results | GPT simulated real event order: assistant emits multiple tool calls, `compact_context.execute()` creates pending state with `sawSiblingTools: false`, then compact tool result boundary triggers compaction too early. |
| Current PR diff unintentionally reverts recent `origin/main` changes. | GPT `4bbcece0-f808-41b` | P2 | REGRESSION_FROM_THIS_DIFF | Pending rebase/merge resolution after GLM results | GPT observed `origin/main` advanced; current branch diff removes unrelated newer main behavior in PR prompt, Claude review launcher, install model override merging, and model override blocks. |
| README still claims commit extraction was adapted after feature removal. | GPT `4bbcece0-f808-41b` | P3 | IN_PLAN | Pending doc fix after GLM results | `_pi/packages/pi-vcc/README.md` still says commit extraction adapted, while active plan defers/removes `[Commits]`. |
| Required E2E verification remains incomplete. | GPT `4bbcece0-f808-41b`, GLM summary `b8c4f774-570b-443` | P3 | IN_PLAN | Pending owner decision or E2E evidence | Plan says PR remains draft until remaining E2E matrix is completed or explicitly waived. |
| Duplicate pruning can drop the only completed error evidence when latest duplicate call has no result yet. | GLM summary `b8c4f774-570b-443` | P2 | REGRESSION_FROM_THIS_DIFF | Pending fix | `_pi/packages/pi-vcc/src/core/prune.ts` builds latest duplicate state from tool calls only, so an in-flight repeated call can cause the older completed result to be pruned before a newer result exists. |
| Hard backstop can repeatedly fail with `Compaction cancelled` when pi-vcc cannot form a cut. | GLM runtime `ce046ddf-9fa0-42d` | P2 | IN_PLAN | Pending fix | 80% hard path uses manual bypass marker; marked compaction with no own cut cancels instead of allowing overflow/default fallback, and `triggerCompaction` does not ratchet `Compaction cancelled`. |

## Final gate result

All cycle 10 reviewers completed; GPT, GLM runtime, and GLM summary verdicts are `FINDINGS_TO_RESOLVE`.

### Cycle 10 fixes applied

| Finding | Fix | Verification |
| --- | --- | --- |
| Mixed-tool `compact_context` could compact before sibling output interpretation | `compact_context.execute()` now initializes `sawSiblingTools` from the most recent assistant tool batch, and regression coverage models the real assistant-tool-result event order. | `bun test scripts/percentage-compaction.test.ts` PASS — 22 tests, 68 expects |
| Duplicate pruning could drop completed evidence when newest duplicate call was in-flight | Duplicate result pruning now only prunes older results when a newer duplicate call has a completed result in the summarized input. | `bun test _pi/packages/pi-vcc/tests/compile.test.ts _pi/packages/pi-vcc/tests/before-compact.test.ts` PASS — 39 tests, 105 expects |
| Hard backstop no-cut path could repeatedly cancel | Hard backstop extension-triggered compaction no longer uses the manual/model bypass marker, and pi-vcc permits core fallback for non-marker `manual`/`threshold`/`overflow` no-cut compactions while marker/model/manual-bypass no-cut compactions still cancel. | `bun test scripts/percentage-compaction.test.ts`; `bun test _pi/packages/pi-vcc/tests/before-compact.test.ts` PASS |
| Stale README commit-extraction wording | README now states upstream commit extraction is intentionally skipped/deferred and describes bounded semantic sections instead of fixed “4 semantic sections.” | `bun test _pi/packages/pi-vcc/tests`; `bash ./scripts/check-pi-vcc-upstream.sh --summary` PASS |
| Branch stale vs `origin/main` | Rebasing onto current `origin/main` removed unrelated main-drift paths from `git diff origin/main`; current diff contains only pi-vcc/percentage-compaction plan scope. | `git diff --name-only origin/main` checked after rebase |

### Post-fix verification

| Command | Result |
| --- | --- |
| `bun test scripts/percentage-compaction.test.ts` | PASS — 22 tests, 68 expects |
| `bun test _pi/packages/pi-vcc/tests/compile.test.ts _pi/packages/pi-vcc/tests/before-compact.test.ts` | PASS — 39 tests, 105 expects |
| `bun test _pi/packages/pi-vcc/tests` | PASS — 142 tests, 311 expects |
| `bash ./scripts/check-pi-vcc-upstream.sh --summary` | PASS — reviewed upstream version/commit match npm/upstream head; only intentional diffs |
| `git diff --check` | PASS |
| `./install.sh --pi` | PASS — Installation complete |

## Runtime harness and partial live evidence

Operator selected “Run the E2E matrix now” after cycle 10 fixes. A large-prompt disposable Pi attempt was killed before writing a session transcript, so it is not counted as evidence. The completed evidence below is runtime-harness coverage plus one disposable Pi smoke session; it does **not** satisfy the plan’s full real-session multi-compaction E2E matrix by itself.

| Scenario | Status | Evidence |
| --- | --- | --- |
| Disposable Pi smoke session | PASS | `pi --session-dir /tmp/pi-vcc-e2e --session-id e2e-smoke --provider ollama --model minimax-m2.7:cloud -p "Reply exactly: E2E_SMOKE_OK"` returned `E2E_SMOKE_OK`; transcript `/tmp/pi-vcc-e2e/2026-06-28T04-46-32-009Z_e2e-smoke.jsonl`. |
| No threshold-only compaction at 60%/75% | Real Pi PASS for soft band; harness PASS for soft+strong | Real Codex session `/tmp/pi-vcc-e2e/2026-06-28T12-58-01-482Z_e2e-codex-soft.jsonl` reported assistant input `175091` tokens (64.38%) and wrote a `custom_message` `compaction-nudge` with band `soft`; no compaction entries. Harness covered both soft and strong bands with `compactCalls: 0`, `sentBands: ["soft", "strong"]`. |
| Model-driven nudging behavior | Real Pi PARTIAL plus harness PASS | Real Codex session `/tmp/pi-vcc-e2e/2026-06-28T12-58-33-142Z_e2e-codex-hard.jsonl` wrote a soft `compaction-nudge`. Real TUI session `/tmp/pi-vcc-e2e/2026-06-28T13-00-27-365Z_e2e-codex-model-tui.jsonl` shows the model invoked `compact_context` three times and received queued tool results, but successful compaction did not occur because Pi reported “Nothing to compact (session too small).” Harness verified successful queued compaction and mixed-tool deferral. |
| Hard backstop / overflow compaction | Real Pi PASS plus harness PASS | Real Codex session `/tmp/pi-vcc-e2e/2026-06-28T12-58-33-142Z_e2e-codex-hard.jsonl` first reached 256961 input tokens (~94% of 272K), then continuing the session wrote two real pi-vcc compaction entries: one `reason: manual` and one `reason: overflow`, `willRetry: true`, each with `compactor: pi-vcc`. Harness verified 80.5% hard-backstop compaction uses no custom instructions and no-cut threshold fallback returns undefined. |
| Continuation after in-flight compaction | Runtime harness PASS plus active-session observation | Harness drove `agent_start` → `session_before_compact` → `session_compact`; emitted hidden `pi-vcc-continuation` via `deliverAs: "steer"`. Active session also observed a real continuation steer during this run. |
| Recall across repeated compactions | Real Pi PASS plus harness PASS | Real hard session `/tmp/pi-vcc-e2e/2026-06-28T12-58-33-142Z_e2e-codex-hard.jsonl` produced repeated real compaction entries, then a later model-requested `vcc_recall` tool result returned 4 matches for `ORCHID_REAL_E2E` (`toolResult` id `a4bcd63c`, `isError: false`). Harness also used real `renderMessage` + `searchEntries`; recall query `ORCHID-DELTA` returned `recallHits: 1`. |
| Pruning safety | Runtime harness PASS; real-session matrix pending | Harness used real `compile`: older duplicate error pruned, latest duplicate evidence retained, protected subagent result remained recoverable through recall (`protectedResultRecallHits: 3`). |

## Review cycle 11 — post-fix rerun

| Reviewer | Agent ID | Slice | Status |
| --- | --- | --- | --- |
| GPT quality-reviewer | `dcbfdc10-e1ce-497` | Whole current diff | Review infrastructure failure — no verdict/output; must rerun once with narrower prompt |
| GLM quality-reviewer-glm | `f8076483-74fa-4f2` | Runtime compaction lifecycle | Review infrastructure failure — no verdict/output; must rerun once with narrower prompt |
| GLM quality-reviewer-glm | `2257c020-682a-438` | Summary/pruning/docs/verification | Completed — findings to resolve |

### Cycle 11 triage — partial

| Finding | Reviewer | Severity | Scope | Decision | Evidence |
| --- | --- | --- | --- | --- | --- |
| Validation artifact overclaims real E2E coverage. | GLM summary `2257c020-682a-438` | P3 | IN_PLAN | Partially resolved; final owner decision still needed for remaining partial live scenarios | Artifact now labels evidence as runtime harness plus partial live evidence, records real threshold/hard/overflow/recall evidence explicitly, and keeps model-driven successful compaction and pruning safety as partial/harness-backed instead of full real-session PASS. |

## Final gate result

Pending narrow GPT/runtime-GLM reruns and final E2E disposition.

## Review cycle 12 — narrow post-infrastructure rerun

| Reviewer | Agent ID | Slice | Status |
| --- | --- | --- | --- |
| GPT quality-reviewer | `39e13851-52c9-438` | Whole simplified current diff | Completed — P2 protected result rendering fixed below |
| GLM quality-reviewer-glm | `8e474bf4-ae6b-4de` | Runtime lifecycle and E2E wording | Completed clean — `No issues found.` |

### Cycle 12 verification refresh

| Command | Result |
| --- | --- |
| `bun test scripts/percentage-compaction.test.ts` | PASS — 22 tests, 68 expects |
| `bun test _pi/packages/pi-vcc/tests` | PASS — 142 tests, 311 expects |
| `bash ./scripts/check-pi-vcc-upstream.sh --summary` | PASS — reviewed upstream version/commit match npm/upstream head; only intentional diffs |
| `git diff --check` | PASS |
| `./install.sh --pi` | PASS — Installation complete |

### Cycle 12 triage and fix

| Finding | Reviewer | Severity | Decision | Evidence |
| --- | --- | --- | --- | --- |
| Protected successful subagent/review tool results were retained by pruning but hidden by brief summary rendering. | GPT `39e13851-52c9-438` | P2 | Fixed | Added shared protected-tool predicate in `_pi/packages/pi-vcc/src/core/protected-tools.ts`; `buildBriefSections` now renders bounded non-error protected tool results under `[tool_result]`; regression `renders protected successful subagent results in the summary` passes. |

### Verification after cycle 12 fix

| Command | Result |
| --- | --- |
| `bun test _pi/packages/pi-vcc/tests/compile.test.ts` | PASS — 22 tests, 55 expects |
| `bun test _pi/packages/pi-vcc/tests/brief.test.ts` | PASS — 15 tests, 36 expects |
| `bun test scripts/percentage-compaction.test.ts` | PASS — 22 tests, 68 expects |
| `bun test _pi/packages/pi-vcc/tests` | PASS — 143 tests, 314 expects |
| `bash ./scripts/check-pi-vcc-upstream.sh --summary` | PASS — reviewed upstream version/commit match npm/upstream head; only intentional diffs |
| `git diff --check` | PASS |
| `./install.sh --pi` | PASS — Installation complete |

## Review cycle 13 — final post-fix clean gate

| Reviewer | Agent ID | Slice | Status |
| --- | --- | --- | --- |
| GPT quality-reviewer | `577ded53-9cbf-4fd` | Whole current diff | Completed — P2 late protected finding retention fixed below |
| GLM quality-reviewer-glm | `6fdd851e-4238-49e` | Runtime lifecycle, summary safety, E2E wording | Completed — P2 sibling-boundary and tail-cap protected-result retention fixed below |

### Cycle 13 triage and fixes

| Finding | Reviewer | Severity | Decision | Evidence |
| --- | --- | --- | --- | --- |
| Protected successful review/subagent results could miss findings after the first 8 lines. | GPT `577ded53-9cbf-4fd` | P2 | Fixed | Protected result rendering now keeps leading context plus full-output signal lines matching P1/P2/P3, impact, minimal-fix, and clean-verdict markers. Regression `keeps late protected review finding lines` passes. |
| `capBrief()` could tail-drop earlier protected review/subagent findings after many later turns. | GLM `6fdd851e-4238-49e` | P2 | Fixed | `capBrief()` now pins omitted `[tool_result]` sections before the retained tail. Regression `pins protected review results when capping long brief transcripts` passes. |
| `compact_context` could still run before sibling output interpretation when execute preceded assistant tool-use turn-end. | GLM `6fdd851e-4238-49e` | P2 | Fixed | Pending delivery detection now checks both `event.message` and `event.toolResults`; assistant tool-use batches update sibling state whenever they contain the pending tool call; unrelated tool results no longer count as safe boundaries. Regressions `compact_context detects sibling batches when execute precedes assistant toolUse turn_end` and `compact_context ignores unrelated tool results before its own result` pass. |

### Verification after cycle 13 fixes

| Command | Result |
| --- | --- |
| `bun test scripts/percentage-compaction.test.ts` | PASS — 24 tests, 72 expects |
| `bun test _pi/packages/pi-vcc/tests/compile.test.ts _pi/packages/pi-vcc/tests/format.test.ts` | PASS — 30 tests, 73 expects |
| `bun test _pi/packages/pi-vcc/tests` | PASS — 145 tests, 321 expects |
| `bash ./scripts/check-pi-vcc-upstream.sh --summary` | PASS — reviewed upstream version/commit match npm/upstream head; only intentional diffs |
| `git diff --check` | PASS |
| `./install.sh --pi` | PASS — Installation complete |

## Review cycle 14 — final replacement clean gate

| Reviewer | Agent ID | Slice | Status |
| --- | --- | --- | --- |
| GPT quality-reviewer | `70a759d3-57c5-44c` | Whole current diff after cycle 13 fixes | Completed — P2 protected-result budget issue fixed below |
| GLM quality-reviewer-glm | `ec74ace0-f72d-4f2` | Runtime lifecycle, summary safety, E2E wording | Completed — same P2 protected-result budget issue fixed below |

### Cycle 14 triage and fixes

| Finding | Reviewer | Severity | Decision | Evidence |
| --- | --- | --- | --- | --- |
| Long leading protected-result preamble could still push late P1/P2/P3/Impact/Minimal-fix lines past the 900-char clip; many omitted protected sections could exceed the pin cap. | GPT `70a759d3-57c5-44c`, GLM `ec74ace0-f72d-4f2` | P2 | Fixed | Protected result rendering now emits signal/finding lines before bounded leading context and clips each line before final clipping. `capBrief()` pins all omitted signal-bearing `[tool_result]` sections and only caps non-signal protected sections. Regressions `keeps protected findings after very long leading preamble` and `pins all signal-bearing protected review results when capping` pass. |

### Verification after cycle 14 fixes

| Command | Result |
| --- | --- |
| `bun test scripts/percentage-compaction.test.ts` | PASS — 24 tests, 72 expects |
| `bun test _pi/packages/pi-vcc/tests/compile.test.ts _pi/packages/pi-vcc/tests/format.test.ts` | PASS — 32 tests, 78 expects |
| `bun test _pi/packages/pi-vcc/tests` | PASS — 147 tests, 326 expects |
| `bash ./scripts/check-pi-vcc-upstream.sh --summary` | PASS — reviewed upstream version/commit match npm/upstream head; only intentional diffs |
| `git diff --check` | PASS |
| `./install.sh --pi` | PASS — Installation complete |

## Review cycle 15 — clean gate after protected-result budget fix

| Reviewer | Agent ID | Slice | Status |
| --- | --- | --- | --- |
| GPT quality-reviewer | `6091a0f5-599c-4e0` | Whole current diff after cycle 14 fixes | Completed — P2 multi-finding protected-result rendering fixed below |
| GLM quality-reviewer-glm | `875bed00-589b-458` | Runtime lifecycle, summary safety, E2E wording | Completed — same P2 multi-finding protected-result rendering fixed below |

### Cycle 15 triage and fixes

| Finding | Reviewer | Severity | Decision | Evidence |
| --- | --- | --- | --- | --- |
| Protected review/subagent output with many findings in one tool result could still lose later findings due to single-line signal clipping; uncapped signal-bearing pinned sections could overgrow summaries. | GPT `6091a0f5-599c-4e0`, GLM `875bed00-589b-458` | P2/P3 | Fixed | Protected result rendering now emits bounded multi-line signal/status lines, preserving many P1/P2/P3/Impact/Minimal-fix lines from one result with explicit omission notice when needed. `capBrief()` now caps pinned protected signal lines with a `vcc_recall` omission notice while preserving head/tail signal evidence. Regressions `keeps many findings from one protected review result` and `caps excessive pinned protected signal lines with a recall notice` pass. |

### Verification after cycle 15 fixes

| Command | Result |
| --- | --- |
| `bun test scripts/percentage-compaction.test.ts` | PASS — 24 tests, 72 expects |
| `bun test _pi/packages/pi-vcc/tests/compile.test.ts _pi/packages/pi-vcc/tests/format.test.ts` | PASS — 34 tests, 84 expects |
| `bun test _pi/packages/pi-vcc/tests` | PASS — 149 tests, 332 expects |
| `bash ./scripts/check-pi-vcc-upstream.sh --summary` | PASS — reviewed upstream version/commit match npm/upstream head; only intentional diffs |
| `git diff --check` | PASS |
| `./install.sh --pi` | PASS — Installation complete |

## Review cycle 16 — clean gate after multi-finding protected-result fix

| Reviewer | Agent ID | Slice | Status |
| --- | --- | --- | --- |
| GPT quality-reviewer | `ff725f57-dc03-4f2` | Whole current diff after cycle 15 fixes | Completed — P2 protected-section cap/header issues fixed below |
| GLM quality-reviewer-glm | `3575b5bb-522d-495` | Runtime lifecycle, summary safety, E2E wording | Completed — P2 protected-section cap/header and path/repro retention issues fixed below |

### Cycle 16 triage and fixes

| Finding | Reviewer | Severity | Decision | Evidence |
| --- | --- | --- | --- | --- |
| Protected sections could be split or dropped when `capBrief()` started inside a `[tool_result]` section; bracket-style finding lines such as `[P2]` could be mistaken for transcript headers. | GPT `ff725f57-dc03-4f2`, GLM `3575b5bb-522d-495` | P2 | Fixed | `capBrief()` now uses a real transcript header regex and pins complete omitted protected sections through the next real transcript header before applying signal caps. Regression `pins complete protected sections when capping starts inside them` passes. |
| Protected review findings could drop `Path:` and `Reproducible condition:` lines, making findings less actionable. | GLM `3575b5bb-522d-495` | P2 | Fixed | Protected signal matching now includes `Path:`, `File:`, `Reproducible condition:`, and `Condition:` lines. Regression `keeps protected finding path and reproducible condition lines` passes. |
| New shared helper file was untracked. | GPT `ff725f57-dc03-4f2` | P2 | To be resolved at commit/stage step | `_pi/packages/pi-vcc/src/core/protected-tools.ts` is present in the working tree and listed by the upstream drift manifest; it must be staged with the final patch. |

### Verification after cycle 16 fixes

| Command | Result |
| --- | --- |
| `bun test scripts/percentage-compaction.test.ts` | PASS — 24 tests, 72 expects |
| `bun test _pi/packages/pi-vcc/tests/compile.test.ts _pi/packages/pi-vcc/tests/format.test.ts` | PASS — 36 tests, 91 expects |
| `bun test _pi/packages/pi-vcc/tests` | PASS — 151 tests, 339 expects |
| `bash ./scripts/check-pi-vcc-upstream.sh --summary` | PASS — reviewed upstream version/commit match npm/upstream head; only intentional diffs |
| `git diff --check` | PASS |
| `./install.sh --pi` | PASS — Installation complete |

## Review cycle 17 — clean gate after staging helper file

| Reviewer | Agent ID | Slice | Status |
| --- | --- | --- | --- |
| GPT quality-reviewer | `0a29ca6d-6241-4cc` | Whole staged/current diff after cycle 16 fixes | Completed clean — `No issues found.` |
| GLM quality-reviewer-glm | `68be9ae4-a57e-409` | Runtime lifecycle, summary safety, E2E wording | Completed — P3 validation artifact trailing blank line fixed |

### Cycle 17 triage and fix

| Finding | Reviewer | Severity | Decision | Evidence |
| --- | --- | --- | --- | --- |
| Validation artifact had an extra blank line at EOF, making `git diff --check` fail after recording it as pass. | GLM `68be9ae4-a57e-409` | P3 | Fixed | Removed trailing blank line; `git diff --check` and `git diff --cached --check` pass; narrow GLM rerun `d06a7d98-97ad-497` returned `No issues found.` |
