# Visible completeness review

- Reviewer: completeness-final
- Model: xai/grok-4.5:high
- Accepted: 2026-08-02T17:35:58Z

## Transcript

I'll inspect the plan, worktree changes, and verification evidence read-only, then judge completeness against the acceptance criteria.
Next I’ll extract acceptance criteria from the plan and compare them to the committed and working-tree diffs.
I'm checking progress markers and sampling the key contract implementations against each acceptance criterion.
I'll sample the locked contracts and the delivery/ledger writer paths next, including the unstaged completeness-launch fixes.
The writer inventory needs a closer look—`write_json` may already own the transaction path.
The settings-surface source looks wrong — verifying against install behavior and remaining AC coverage.
Checking whether the completeness-reviewer naming regression and remaining AC gaps are real.
Confirming the install-summary mode enum against the locked schema and other summary field mismatches.
COMPLETENESS_REVIEW_RESPONSE_ID: b5c64f516b70470fb0de0fa3e95c8710
VERDICT: FINDINGS_TO_RESOLVE

## Finding 1 — AC6 / install-summary-v1 `mode` enum (BDD8 receipt contract)

**Criterion:** AC6 — remote deployment must emit the locked install-summary-v1 object. Locked schema requires:
`mode: pi-review-stack|all|pi|tools|skills|remote-kitty`.

**Evidence:** `scripts/install-kitty-remote-hosts.sh` writes:

```bash
--mode "$([[ "$STRICT" == 1 ]] && echo strict || echo best-effort)"
```

So remote receipts get `mode=strict` or `mode=best-effort`, not `remote-kitty`.
`scripts/pi_review_stack_contract.py` `write-summary` accepts any `--mode` string (no enum check).
`scripts/tests/test_remote_host_receipts.py` asserts hosts/status/cwd/permissions but never asserts `payload["mode"] == "remote-kitty"`.

**User impact:** Machine-readable remote receipts do not match the locked contract. Automation/operators keying on `mode` cannot classify remote-host runs; strictness is already expressed by `status` (`failed` vs `partial`) and exit code, so the current `mode` values are both non-compliant and redundant.

**Smallest correction:**
1. Emit `--mode remote-kitty` from `install-kitty-remote-hosts.sh`.
2. Validate `mode` against the locked enum in `write-summary`.
3. Assert `mode == "remote-kitty"` in `test_remote_host_receipts.py`.

---

## Finding 2 — AC7 / P3 writer-routing regression guard

**Criterion:** AC7 and P3 work item: route every enumerated ledger writer through the transaction helper; **“add a test that fails when a new writer bypasses the helper.”**

**Evidence:** Concurrent/stale lock tests exist (`test_ledger_lock_serializes_and_rejects_stale_writer`, timeout holder metadata, launch-lease note test). There is **no** structural test that scans `skills/delivery-run/scripts/delivery` for ledger mutations outside `write_json` / the lock helper. A source search for that guard phrase/AST inventory in the delivery test suite is empty.

**User impact:** The lock/CAS path itself looks wired through `write_json` today, but the plan-required guard against a future writer silently bypassing `.delivery/ledger.lock` is missing. That is exactly the regression this phase was supposed to lock down.

**Smallest correction:** Add one source/contract test that fails if any ledger-mutating `cmd_*` (and launch callback path) writes `ledger.json` without going through the locked helper.

---

## Notes (not separate blockers, but fix while touching delivery)

- Worktree has **unstaged** delivery fixes: completeness agent name capped to ≤32 chars and `agent_pane_busy` start retry. Include those in the same delivery patch set so the long-slug completeness path stays launchable; committed code still uses `max_len=36` (`completeness-` + 36 > Herdr’s 32-char names).
- Progress checkboxes P1–P5 are marked complete; inventory before/after artifacts and most AC1–AC5/AC8–AC11 surfaces look present. Re-open completeness only after the AC6 mode contract and AC7 bypass guard are fixed and reflected in the candidate (including any still-dirty delivery launch fixes).
Rereviewing prior findings against the live worktree and plan acceptance criteria.
Finding 1 looks fixed. Checking whether the AC7 writer-bypass guard and remaining ACs are fully covered.
Both prior findings appear addressed. Sampling remaining AC/BDD coverage and verification evidence.
Spot-checking a few remaining edge contracts before deciding COMPLETE.
Checking harness mirror parity — the thin prompt wrappers may intentionally defer to skills.
COMPLETENESS_REVIEW_RESPONSE_ID: e4cbc002b67f45b28cd995f966f274c2
VERDICT: COMPLETE

Prior findings are resolved in the clean candidate (`90f5911`):

1. **AC6 mode enum** — remote receipts emit `--mode remote-kitty`; `SUMMARY_MODES` validates the locked set; invalid `strict` is rejected; remote tests assert `mode == "remote-kitty"`.
2. **AC7 writer bypass guard** — `test_every_ledger_writer_is_classified_and_reaches_locked_write_json` classifies every delivery subcommand and proves each writer reaches locked `write_json`, with no alternate `json.dump` / extra `os.replace` ledger path.
3. **Live completeness launch notes** — reviewer names bounded to 32 chars (`max_len=19`), Herdr JSON-default adapter, and `agent_pane_busy` retry are committed.

Progress P1–P5 are checked. Working tree is clean. Non-goals hold (no new review engine, test runner, daemon, or app code). Amp/Heddle remain external follow-ups. Claimed verification residuals are labeled inherited, not newly introduced plan-contract failures.

## AC / BDD coverage

| ID | Status | Evidence in candidate |
|---|---|---|
| **AC1** / BDD1–2 | Covered | `scripts/probe_pi_review_transport.py` reports effective isolation/model/reasoning without a model call; installer/transaction pre+post probe; isolation/roster tests |
| **AC2** / BDD3–4 | Covered | `skills/run-plan/SKILL.md` partition order, one bounded no-fail-fast pass, signature cap, merge-base inheritance; Hermes mirror + contract tests |
| **AC3** / BDD5 | Covered | Owned-scratch marker/count/bytes/cleanup/refuse-unowned contract in run-plan + contract tests |
| **AC4** / BDD6 | Covered | Final checklist in run-plan and `cmd-create-pr` (`git diff --check` on committed range, plan/Doct currency, base freshness, placeholder search); changelog has no real placeholders |
| **AC5** / BDD7 | Covered | `scripts/pi-review-stack-managed-surfaces.json` drives install/transaction/verify; foreign-sibling and rollback failpoint tests |
| **AC6** / BDD8 | Covered | Atomic summary v1; host first-seen dedupe; explicit remote `mktemp` cwd; `mode=remote-kitty`; strict→`failed`/non-zero vs best-effort→`partial`/0 |
| **AC7** / BDD9 | Covered | `.delivery/ledger.lock` 50ms/10s CAS + holder metadata; concurrent/stale/timeout tests; launch lease remains separate; AST writer routing guard |
| **AC8** / BDD10 | Covered | Pure `parse_completeness_transcript` grammar; wrapped/duplicate/malformed/truncated fixtures; prior-round reject; 500-line bound; requestId/plan/worktree binding |
| **AC9** / BDD11 | Covered | `workflow_fixture_axes.py`; hostile-env override + missing-axis failure in remote receipt tests; installer family uses explicit transport fixture |
| **AC10** | Covered | Canonical skills, thin harness wrappers, Hermes mirrors, README/`_pi` README, CHANGELOG coherent; Amp external-only |
| **AC11** / BDD12 | Covered | Conditional planning-evidence checkpoint replaces mandatory Socratic block; supervisor judges existing sections; planning contract tests |

## Not examined
- Did not execute tests, installs, or live Herdr/Doct/network commands in this review.
- Did not re-validate remote Doct document hash against the live service.
- Did not re-prove concurrent ledger races beyond reading the committed subprocess tests.
- Did not inspect a real post-install `~/.pi` host state on this machine.
- Post-merge host install receipts and Heddle schema-v2 reconciliation remain non-blocking operator follow-ups per plan.
Re-inspecting the live worktree and prior-finding fixes for this completeness rereview.
Commit moved; verifying the full candidate still holds the prior COMPLETE bar.
Noting additional delivery transcript handling since the last pass — checking it against AC8.
COMPLETENESS_REVIEW_RESPONSE_ID: d0df17b87513470495cae679d9f73b42
VERDICT: COMPLETE

Re-reviewed clean candidate `57ddbf3` (worktree clean, P1–P5 checked). Prior completeness findings remain fixed, and the additional delivery transcript path (rendered `recent-unwrapped` first, then bounded Pi session JSONL fallback under the sessions root) strengthens AC8 without leaving plan gaps.

## AC / BDD coverage

| ID | Status | Evidence |
|---|---|---|
| **AC1** / BDD1–2 | Covered | No-model `probe_pi_review_transport.py`; installer/transaction pre+post probe; isolation/roster tests |
| **AC2** / BDD3–4 | Covered | Run-plan partition order, one bounded no-fail-fast inventory, signature cap, merge-base inheritance; Hermes + contract tests |
| **AC3** / BDD5 | Covered | Owned-scratch marker/count/bytes/cleanup/refuse-unowned contract |
| **AC4** / BDD6 | Covered | Committed-range `git diff --check`, plan/Doct currency, base freshness, placeholder search in run-plan + cmd-create-pr; changelog free of real placeholders |
| **AC5** / BDD7 | Covered | Single managed-surface manifest drives install/transaction/verify; foreign-sibling/rollback tests |
| **AC6** / BDD8 | Covered | Summary v1 atomic write; host first-seen dedupe; explicit remote cwd; **`mode=remote-kitty`** emit + enum validation + remote test assert; strict vs partial status/exit |
| **AC7** / BDD9 | Covered | `ledger.lock` CAS/timeout/holder metadata; concurrent/stale tests; separate launch lease; **AST writer-routing guard** proves every writer reaches `write_json` |
| **AC8** / BDD10 | Covered | Pure response-block grammar; wrapped/dup/malformed/truncated fixtures; prior-round reject; 500-line bound; requestId/plan/worktree binding; terminal-wrap fallback to exact session text |
| **AC9** / BDD11 | Covered | Explicit Hub/profile/transport fixture axes + hostile-env/missing-axis failures |
| **AC10** | Covered | Skills, thin harness wrappers, Hermes mirrors, README/`_pi` README, CHANGELOG coherent; Amp external-only |
| **AC11** / BDD12 | Covered | Conditional planning-evidence checkpoint replaces mandatory Socratic block; supervisor judges existing sections |

Non-goals hold (no new review engine, universal test runner, daemon, or app/Heddle migration). Inventory before/after artifacts and run-ledger residuals are classified as inherited where applicable.

**Not examined:** Did not execute tests/installs/network/Doct/Herdr commands in this review; did not re-prove concurrency beyond reading committed subprocess tests; did not inspect a live post-install host `~/.pi` tree; post-merge host receipts and Heddle schema-v2 reconciliation remain non-blocking operator follow-ups.
Re-inspecting the live worktree for this completeness rereview.
HEAD moved again; verifying the full candidate and run-ledger still match the plan.
COMPLETENESS_REVIEW_RESPONSE_ID: e9e661bb2798491a82665041d3952f9b
VERDICT: COMPLETE

Re-reviewed clean candidate `c76cb2c` (no staged/unstaged/untracked drift). P1–P5 are checked. Prior completeness findings remain fixed: locked `mode=remote-kitty` with enum validation, AST writer→`write_json` guard, Herdr launch/name bounds, and exact Pi JSONL transcript fallback for AC8 acceptance.

## AC / BDD coverage

| ID | Status | Evidence |
|---|---|---|
| **AC1** / BDD1–2 | Covered | No-model transport probe; installer/transaction pre+post probe; isolation/roster tests |
| **AC2** / BDD3–4 | Covered | Run-plan partition order, bounded no-fail-fast inventory, signature cap, merge-base inheritance; Hermes + contract tests |
| **AC3** / BDD5 | Covered | Owned-scratch marker/count/bytes/cleanup/refuse-unowned guidance |
| **AC4** / BDD6 | Covered | Committed-range `git diff --check`, plan/Doct currency, base freshness, placeholder search; changelog free of real placeholders |
| **AC5** / BDD7 | Covered | Single managed-surface manifest for install/transaction/verify; foreign-sibling/rollback coverage |
| **AC6** / BDD8 | Covered | Summary v1 atomic receipts; host dedupe; explicit remote cwd; `mode=remote-kitty` emit/validate/assert; strict vs partial status/exit |
| **AC7** / BDD9 | Covered | `ledger.lock` CAS/timeout/holder metadata; concurrent/stale tests; separate launch lease; structural writer-routing guard |
| **AC8** / BDD10 | Covered | Pure response-block grammar; wrapped/dup/malformed/truncated fixtures; prior-round reject; requestId/plan/worktree binding; rendered + JSONL transcript path |
| **AC9** / BDD11 | Covered | Explicit Hub/profile/transport fixture axes with hostile-env/missing-axis failures |
| **AC10** | Covered | Canonical skills, thin harness wrappers, Hermes mirrors, README/`_pi` README, CHANGELOG coherent; Amp external-only |
| **AC11** / BDD12 | Covered | Conditional planning-evidence checkpoint replaces mandatory Socratic block; supervisor judges existing sections |

Non-goals hold. Inventory before/after and run-ledger residuals remain classified as inherited where applicable. Completeness artifact is present in-tree.

**Not examined:** Did not execute tests, installs, Doct, Herdr, or network commands in this review; did not re-prove concurrency beyond reading committed tests; did not inspect a live post-install host `~/.pi` tree; post-merge host receipts and Heddle schema-v2 reconciliation remain non-blocking operator follow-ups.
