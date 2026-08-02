# Retro Workflow Reliability Run Ledger

## Scope contract

- Plan: `thoughts/plans/retro-workflow-reliability-improvements.html`
- Target: `origin/main`
- Goal: consolidate existing review, verification, installer, delivery-ledger, transcript, fixture, and planning-evidence mechanisms into bounded, diagnosable contracts without adding a new review engine, test runner, installer architecture, daemon, or application behavior.
- PR-reviewable phases: P1–P5. Post-merge local/remote installer execution and Heddle template reconciliation remain non-blocking operator follow-ups.
- Exact acceptance contract: AC1–AC11 and BDD1–BDD12 in the reviewed plan.
- Current candidate started from `bdf4f70`; worktree initially contained only reviewed plan/review artifacts and the required before-inventory artifact.
- Current Doct registration: `https://doct.nodaste.com/d/2X-TgIwcTj2rUstH8ybtyQ`, document `d97f9380-8c1c-4e3d-ab52-cb47f326edc9`, workspace `759bfae3-44f1-4ce5-9bff-9077d9933a21`, source hash `a3a5559911a02786838fb507c9b2bd348cd28c8f2c647a371f8c1a8959b0eb98`; lifecycle active, board `in_progress`, execution-ready true. The final P1–P5 source was force-updated after the first Doct request failed before starting, then refreshed for the live Herdr production-path correction and visible completeness findings.

## Integration-integrity record

| Contract | Source of truth | Producers | Consumers / inventory | Coverage | Required proof | Status |
|---|---|---|---|---|---|---|
| Pi managed surfaces | `scripts/pi-review-stack-managed-surfaces.json` | `install.sh`, transaction wrapper | verifier, installer tests, docs | exhaustive-by-site | actual parser install, snapshot/restore, verification, foreign-sibling preservation | reconciled; focused tests green |
| Install summary v1 | locked plan schema and shared installer support | install, transaction, remote-host commands | operators/tests | exhaustive-by-command | success/failure JSON readback through actual CLIs; atomic mode-0600 path behavior | reconciled; focused tests green |
| Reviewer provenance/probe | canonical skills plus Pi agent definitions | planner/reviewer launch resolution | reviewed-plan/autoreview/run-plan | exhaustive-by-family | no-model effective transport probe plus live/fallback fixture cases | reconciled; focused tests green |
| Failure/scratch/final candidate guidance | `skills/run-plan/SKILL.md` and named mirrors | run-plan/test authoring/PR preparation | agents, PR evidence, tests | exhaustive-by-family | contract tests and committed-range parser examples | reconciled; focused tests green |
| Delivery ledger transaction | `skills/delivery-run/scripts/delivery` | all enumerated writer commands/callbacks | stage/show/check/board/completion acceptance | exhaustive-by-command | concurrent subprocesses, stale CAS, valid JSON, narrow launch lease | reconciled; 28/28 delivery tests green |
| Completeness response grammar | pure parser in delivery CLI | visible Grok transcript | `completion-review --accept` | exhaustive-by-grammar-case | exact/wrapped/duplicate/non-complete/malformed/truncated fixtures | reconciled; parser fixtures green |
| Fixture axes | local family fixture builders | test setup | installer/review/delivery tests | exhaustive-by-family | hostile inherited environment and missing-axis setup failure | reconciled; shared fixture-axis helper green |
| Conditional planning evidence | `skills/planning-workflow/SKILL.md` | planning workflows | supervisor and harness mirrors | exhaustive-by-family | positive multi-surface evidence and lightweight counterexample contracts | reconciled; planning contract tests green |

The exact six-command source inventory was captured before dependent edits in `thoughts/validation/retro-workflow-reliability-inventory-before.txt`. Reopen each contract source before editing consumers; repeat the identical inventory after reconciliation.

## Review-cycle ledger

- Round 1 (`reviewer`, Terra medium): four in-scope findings — full-mode preflight ordering, unsafe `--force` revision behavior, over-broad launch-lease mutation rejection, and symlinked managed ancestors. All fixed with focused regression coverage.
- Round 2 targeted rereview: force-replace and launch-lease findings resolved; fresh-transport staging and managed symlink leaves remained. Both fixed, including a production-path fresh-full-install staging-failure test and foreign-link-leaf tests for bounded and transactional commands.
- Round 3 was permitted because round 2 exposed the new managed-link-leaf case. It confirmed the symlink family resolved and raised one broader concern: a successful preflight should make every later failure in the legacy non-transactional full installer restore all earlier mutations. Disposition: outside AC5–AC6 and the explicit no-new-installer-architecture boundary. Exact rollback remains provided by `scripts/install-pi-transactionally.sh`; the full route now guarantees the plan-required real preflight before manifest-owned mutation and untouched managed state when that preflight fails.
- Gate status: no unresolved blocking in-scope finding. Review budget closed; no further review loop.

## Verification convergence ledger

Final focused gate: shell syntax and Python compilation passed; 50 focused Python tests, 30 delivery CLI tests, and 93 review-orchestration tests passed. `test_herdr_config_install.sh`, `test_herdr_remote_deploy.sh`, and `test_kitty_remote_workflow.sh` passed. The repository-wide Python discovery ran 144 tests in 420 seconds with one residual: the inherited real-host pi-vcc reload handler-count failure in `test_real_host_accepts_existing_empty_artifacts_directory`, reproduced on the pre-change candidate.

Repository-wide inherited evidence: `test_install.sh` passes 9/10 and fails only its obsolete assertion that `_claude/agents` must be absent, while repository policy requires the managed read-only Claude reviewer. `test_install_shared_skills.sh` improved from 16/30 at the pre-change baseline to 26/30 after explicit transport fixtures; the remaining failures are the inherited unavailable Herdr Navigator inspection/default-mode consequence and existing Pi/Codex prompt-parity drift. No residual is newly introduced in a plan-touched production contract.

The exact six-command after-inventory contains all named maintained workflow paths and all enumerated delivery writer families. Trailing spaces inherited from one matched archived skill line are normalized in both inventory artifacts so committed-range `git diff --check` remains green. Placeholder hits in changed workflow guidance/tests are the deliberate literal rejection examples; `CHANGELOG.md` itself contains no unresolved PR placeholder.

The first live completeness-review launch exposed that current Herdr emits JSON by default and rejects the removed `--json` option. The shared delivery adapter now uses the current production CLI form, bounds generated names to Herdr's 32-character contract, retries the transient new-pane shell-readiness race, and falls back to bounded exact Pi JSONL assistant text when narrow terminal rendering hard-wraps protocol labels. Regression coverage exercises the launch/name and exact transcript paths.

The initial visible Grok completeness pass found two remaining in-plan gaps: remote receipts used `strict|best-effort` instead of locked `mode=remote-kitty`, and P3 lacked the promised structural bypass guard. Both are corrected. The summary writer now validates the full mode enum; remote production-path tests assert `remote-kitty`; and an AST command/call-graph contract classifies every delivery subcommand and proves every writer reaches `write_json`.
