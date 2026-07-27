# Pre-PR review — review result transport

## Scope and baseline

- **Branch:** `fix-the-shit-review-result-transport`
- **Comparison:** `origin/main`; the implementation is unstaged in this worktree.
- **Intent:** make Herdr review-result capture resilient to terminal wraps and repeated complete fences, preserve fail-closed nonce safety for malformed fences, support a sidecar result without changing the candidate fingerprint, and prevent sidecar/transcript cleanup drift.
- **Supported paths:** transcript result capture from `recent-unwrapped`/terminal output; production-length nonce fences with presentation prefixes; optional reviewer-written structured JSON result; cleanup after durable evidence; opaque pane-ID targets; Herdr-safe name helper for launchers.
- **Non-goals:** launch/rework reviewer tabs, alter candidate fingerprint coverage for candidate files, or change unrelated review orchestration.

## Integration record

| Contract | Source / producers | Consumers | Reconciliation / proof |
|---|---|---|---|
| Result nonce, fence, verdict | Reviewer prompt and `HerdrReviewAdapter` | `_extract_result_block`, `_validate_result`, receipt, cleanup | Wrap, sequential duplicate, malformed nested/extra boundary tests; live narrow-pane proof |
| Structured sidecar | Prompt path outside checkout; reviewer writes `nonce`, `verdict`, `body` | `_validate_result`, accepted block/receipt, cleanup | Production test proves acceptance without fingerprint change; cleanup revalidates same file and digest |
| Candidate fingerprint | `candidate_fingerprint()` including complete untracked manifest | `_wait_and_validate`, aggregate | Sidecar is OS-temporary; non-transport untracked mutation remains stale |
| Accepted evidence / cleanup | `LegOutcome` and result receipt fields | `cleanup_request_file`, `HerdrReviewAdapter.cleanup_leg_is_current` | Transcript and structured sources are dispatched separately; tampered sidecar prevents close |
| Herdr target/name | Existing opaque target request; `short_herdr_agent_name` helper | Launch callers / request loader | Pane IDs remain accepted; name helper tests Herdr’s 1–32-character rule |

## Review cycle ledger

| Cycle | Reviewer | Result | Triage / action |
|---|---|---|---|
| 1 | Active-harness `reviewer` (`gpt-5.6-terra`, medium) | `FINDINGS_TO_RESOLVE` | P1: sidecar in worktree invalidated full fingerprint. P2: cleanup used transcript even for structured acceptance. P2: nested/unmatched same-nonce fences became accepted. All verified and fixed. |
| 2 | Same reviewer, narrowed follow-up | `PASS` | Initial isolated checkout did not contain unstaged work; the one permitted live-worktree follow-up inspected the absolute worktree read-only and passed all three corrected families. `Not examined:` unrelated launcher/general Herdr behavior and executable validation. |

## Triage

| Finding | Severity / scope | Decision | Evidence |
|---|---|---|---|
| Sidecar wrote under candidate worktree | P1 / `REGRESSION_FROM_THIS_DIFF` | Fixed | Result directory now uses private OS temp storage; production test proves structured acceptance leaves candidate fingerprint valid. |
| Structured result digest could not be cleanup-verified | P2 / `REGRESSION_FROM_THIS_DIFF` | Fixed | Evidence source/path persist in receipt; cleanup reloads structured source and compares canonical digest; tampering test blocks cleanup. |
| Nested/unmatched same-nonce markers accepted | P2 / `REGRESSION_FROM_THIS_DIFF` | Fixed | Stack-style boundary validation permits only sequential completed blocks and rejects nested/extra markers. |

## Verification

- `python3 -m unittest tests.test_review_orchestration -q` — **93 tests passed** after the final code/doc changes.
- `git diff --check` — **passed**.
- Five focused repetitions of seven transport tests — **5/5 passed**.
- Five post-review live Herdr narrow-pane trials — **5/5 passed**. Each proved a hard-wrapped result from `recent`, sequential duplicate last-block selection, nested-fence rejection, and structured-result fallback. Evidence: `thoughts/validation/review-result-transport-stability-proofs.jsonl` entries with `phase: post-review-fixes`.
- Production tests additionally prove external structured result acceptance, cleanup success, tamper rejection, and continued stale detection for ordinary candidate untracked mutations.

## Final gate

- **Selected review surface:** active-harness `reviewer` subagent, GPT-5.6 Terra at medium reasoning.
- **Reviewer verdict:** `PASS`; no unresolved in-scope P1/P2 findings.
- **Reviewer-result capture:** cycle 1 findings captured and fixed; cycle 2 targeted rereview passed after its one live-worktree follow-up.
- **Base freshness:** branch is currently `[behind 1]` relative to `origin/main`; no commit or rebase was requested in this task.
- **Remaining follow-ups:** none in scope.
