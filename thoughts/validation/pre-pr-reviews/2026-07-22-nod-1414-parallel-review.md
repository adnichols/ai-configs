# NOD-1414 P1 pre-PR implementation review

- Branch: `nod-1414-parallel-review`
- Comparison: current uncommitted candidate against `HEAD 4e40025b41fbbc14d491086296ca3fadb0fe94b3`
- Intended PR base: `origin/main`
- Base freshness: pending; branch was behind `origin/main` by 3 commits before the review. Rebase must rerun invalidated verification and applicable review before PR creation.
- Plan: Heddle `thoughts/plans/heddle-claude-codex-review-performance.html`, P1 only
- PM gate: `PM_PASS_IMPLEMENTATION`
- Review surface: visible Herdr Codex `gpt-5.6-terra/high/read-only/no-approval` and Claude Code `claude-sonnet-5/xhigh/Read,Grep,Glob`

## Pre-review scope baseline

P1 adds the shared parallel review coordinator, benchmark fixture, installation/runtime propagation, fail-closed result/fingerprint/cleanup contracts, and the operator-requested review-policy correction. Supported behavior includes prompt dispatch before waits, independent concurrent settlement, one complete candidate fingerprint, strict nonce/verdict validation, one narrowed unusable-output retry, truthful transition/settlement/wall timing, exact coordinator-owned tab cleanup after durable clean evidence, bounded installer parity/rollback, and at least 35% controlled median improvement with 100% accepted/applicable coverage.

Explicitly outside this slice: P2 bounded packet classification, P3 slice reuse, P4 malicious coherent receipt authentication, P5 generated-output/worktree lifecycle, P6 durable jobs, and unrelated ai-configs installer-baseline repair.

The initial candidate contained 22 modified/untracked paths across two independent review slices: runtime/transport/installer/evidence and review-policy propagation.

## Cycle 1 — full split review

### Runtime / transport / installer slice

- Codex: `FINDINGS_TO_RESOLVE`
- Claude Code: `FINDINGS_TO_RESOLVE`

| Finding | Reviewer | Severity | Scope | Decision | Evidence |
|---|---|---:|---|---|---|
| Delayed Enter recovery polled the first stalled leg before dispatching the sibling prompt | Codex | P2 | IN_PLAN | Fixed | Parallel initial dispatch now sends every prompt/Enter first, then confirms pending transitions concurrently; any failure starts zero result waits. |
| Cleanup proved target state and tab workspace membership separately but not target-to-tab binding | Codex | P1 | IN_PLAN | Fixed | Cleanup now parses current `agent.tab_id` from supported envelopes and requires exact equality for every leg before any close. |
| Candidate wall time began after prompt transport returned; benchmark omitted separate startup/cleanup evidence | Codex | P2 | PLAN_PREREQUISITE | Fixed | Timing begins before first submission transport; benchmark v2 reports startup N/A truthfully and cleanup distribution/success/coverage, and rejects incomplete cleanup. |
| Bounded installer permanently narrows pre-existing `~/.pi` mode | Claude | P2 claimed | OUT_OF_SCOPE_FOLLOW_UP | Rejected as a P1 blocker | The line predates this diff; historical bounded-installer guidance intentionally owns/snapshots the complete mode-0700 `~/.pi` tree. No newly reachable path or P1 regression was established. |
| Outer transaction symlink guard omits `settings.json` while inner installer rejects it | Claude | P3 | OUT_OF_SCOPE_FOLLOW_UP | Deferred | Current supported path fails before mutation and rollback remains exact. Track with existing ai-configs bounded-installer hardening, not NOD-1414 P1. |
| Non-standard JSON `Infinity` can produce an uncaught traceback | Claude | P3 | OUT_OF_SCOPE_FOLLOW_UP | Deferred | Invalid non-standard coordinator input still exits nonzero and cannot produce false clean status. Graceful invalid-input JSON reporting is later runtime hardening. |

### Review-policy propagation slice

- Codex: `FINDINGS_TO_RESOLVE`
- Claude Code: `FINDINGS_TO_RESOLVE`

| Finding | Reviewer | Severity | Scope | Decision | Evidence |
|---|---|---:|---|---|---|
| Native Codex `dev:run` named an undefined high-risk second reviewer | Codex + Claude | P2 | PLAN_PREREQUISITE | Fixed | It now names installed `claude-code-review` + `herdr-reviewers`, visible read-only Claude, bounded packet/verdict, and pinned model/tool policy while preserving `quality-reviewer` primary. |
| Bootstrap skill/template only said not to consult repeatedly | Codex | P2 | PLAN_PREREQUISITE | Fixed | Both now preserve stable family+scope identity, no rename/reconsult, distinct later-family budgets, advisory-only authority, all four dispositions, and unresolved-evidence handling. |
| Direct prompts implied but did not state advisory/no-implementation-authority boundary | Claude | P3 regression-caused | IN_PLAN | Fixed | Pi and Codex direct prompts now explicitly prohibit consultation edits, fixes, implementation authority, and persona rerouting. |

## Cycle 2 — targeted rereview after fixes

- Codex completed the six-finding targeted rereview: `CLEAN_FOR_PR`.
- Claude's prompt transport returned success but left the exact rendered prompt visibly unsubmitted; `state_change_seq` did not advance within 5 seconds. The helper truthfully returned `REVIEW_INFRASTRUCTURE_FAILURE` without resubmission or unusable-output retry.
- After exact visible proof, one manual Enter started the already-rendered Claude prompt. Claude completed the same targeted rereview and returned `CLEAN_FOR_PR` for the six prior blockers.
- The dogfood event exposed one new concrete supported-path blocker: success-return-but-unsubmitted prompt transport was not covered by the one proven Enter recovery.

## Cycle 3 — permitted new-blocker review

The runtime now, after the normal no-transition boundary, reads the same target's visible output and sends exactly one Enter only when it ends with the exact current rendered prompt. It resets the allowance per submission/retry, uses remaining timeout, preserves first-action time, never resubmits, and fails transport without sibling/budget reset on mismatch, unreadable/malformed/decreasing state, failed Enter, or a second non-transition.

- Codex: `CLEAN_FOR_PR`
- Claude Code: `CLEAN_FOR_PR`
- Aggregate helper status: `CLEAN_FOR_PR`
- Candidate fingerprint: `ea58c36269d29222f5d1d36ee472e0989e16749d5018de65b57d4ec729b395eb`
- All prompts submitted before first wait: `true`
- Codex elapsed: `49.675s`
- Claude elapsed: `221.263s`
- Candidate wall: `221.496s`
- Narrowed unusable-output retry: not used
- Durable receipt: `thoughts/validation/pre-pr-reviews/2026-07-22-nod-1414-parallel-review-final-receipt.json`
- Reviewer-tab cleanup: `CLEANUP_COMPLETE`; exact coordinator-owned tabs `w8H:tD` and `w8H:tC` closed and confirmed absent. Durable cleanup: `thoughts/validation/pre-pr-reviews/2026-07-22-nod-1414-parallel-review-final-cleanup.json`.

## Final verification after last fix

- Applicable Python surfaces: 256 passed, 3 skipped.
- Focused orchestration suite: 73 passed.
- Bounded installer transaction suite: 16 passed.
- `python3 -m py_compile scripts/review_orchestration.py scripts/benchmark_review_orchestration.py tests/test_review_orchestration.py` — PASS.
- Shell syntax and `git diff --check` — PASS.
- `bash test_install_shared_skills.sh` — documented unchanged baseline: 20 passed / 7 failed. The directly affected parallel-protocol and policy assertions pass.
- Benchmark schema: `review-orchestration-benchmark-v2`.
- Serial one-warmup/five-sample: median `0.194042s`, p75 `0.195179s`, p90 `0.196472s`, accepted/applicable `10/10`, coverage `1.000`, cleanup complete `5/5` with median `0.000006s`.
- Parallel one-warmup/five-sample: median `0.107436s`, p75 `0.108576s`, p90 `0.109924s`, accepted/applicable `10/10`, coverage `1.000`, cleanup complete `5/5` with median `0.000006s`.
- Median improvement: `44.633%` (required `>=35%`).
- Startup: explicitly `not_applicable` because the deterministic fixture uses pre-created in-memory reviewer legs and no tabs.
- Raw external JSON SHA-256: serial `18bcf893cf5352b7465a4373eea4661ef314101543f26eee26aa21fd6036d9a1`; parallel `bb5310f89dc9d7424aa2976da4dbd0df3acf1f080bf4e591d0431e1ced80ba68`; fixture `d7a0bc728f41d3906dbc3187349eb1e2c1524aef719e1cad424fef6def854ce3`.

## Remaining non-blocking follow-ups

- Preserve the existing ai-configs bounded-installer owner for redundant outer `settings.json` symlink-guard parity.
- Preserve later runtime-hardening ownership for graceful receipts on non-standard non-finite JSON numeric input.
- P4 remains the plan destination for malicious coherent receipt authentication; P1's supported coordinator path is bound to exact request identity, fingerprint, nonce, raw result block, target/tab/workspace, and durable cleanup evidence.

## Post-rebase consultation and targeted review

The branch rebased from `4e40025` to current `origin/main` `fbbd817`. Conflicts were limited to `AGENTS.md` and `skills/run-plan/SKILL.md`: current main added complete PR-reviewable-slice and non-blocking post-merge deployment guidance while this branch adds the no-PR-prerequisite external consultation route. The resolution preserved both.

Because the ordinary three-cycle budget was consumed and run-plan requires review after material conflict resolution, the coordinator assigned stable identifier `nod-1414-p1-post-rebase-policy-conflict-v1`. Gemini council run `20260722-160036-04cb` authorized exactly one bounded Codex+Claude pass limited to the two conflict resolutions and direct base-integration regressions, plus the existing one pass after fixes.

The authorized pass returned Claude `CLEAN_FOR_PR` and one Codex P2 blocker: ordinary-budget and monitoring guards still prohibited any pass after three cycles, contradicting the later consultation-authorized exception. The bounded fix:

- preserves the ordinary three-cycle budget and PR-neutrality;
- routes an exhausted stable `REVIEW_ESCAPE` family through its one-per-family consultation before convergence;
- permits no fourth or renamed pass except the single explicitly authorized bounded exception plus one pass after fixes;
- aligns the primary and Hermes monitoring steps; and
- adds exact source/install policy assertions.

The allowed pass after fixes returned Codex `CLEAN_FOR_PR` and Claude Code `CLEAN_FOR_PR`.

- Post-rebase fingerprint: `e788b5e6154b1b52267214f3c08b42a03db7f01851fecf04823fef908420fe73`
- All prompts submitted before first wait: `true`
- Codex elapsed: `48.954s`
- Claude elapsed: `83.854s`
- Candidate wall: `84.023s`
- Retry used: no
- Durable receipt: `thoughts/validation/pre-pr-reviews/2026-07-22-nod-1414-post-rebase-final-receipt.json`
- Cleanup: `CLEANUP_COMPLETE`; exact tabs `w8H:tE` and `w8H:tF` closed
- Durable cleanup: `thoughts/validation/pre-pr-reviews/2026-07-22-nod-1414-post-rebase-final-cleanup.json`

Post-rebase verification: 260 applicable Python passes with 3 skips; focused orchestration plus transaction 89 passed; compile, shell syntax, and diff checks passed; shared installer candidate 19 passed / 8 failed versus current-main 18 passed / 8 failed, with the candidate's new protocol test passing and the same eight baseline failures remaining.

## Final gate

- Codex verdict: `CLEAN_FOR_PR`
- Claude Code verdict: `CLEAN_FOR_PR`
- Final local gate: `OPEN_PR_READY`
- Base freshness: current with `origin/main` at `fbbd817` before final push.
- No Codex PR thumbs-up is required beyond this clean local review artifact.
- Next step: amend the final commit, push, open the PR, and inspect the current PR snapshot for actionable feedback and mergeability.
