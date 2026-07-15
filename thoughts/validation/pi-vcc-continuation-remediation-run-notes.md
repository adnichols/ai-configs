# Pi VCC Continuation Remediation Run Notes

## Objective

Execute `thoughts/plans/pi-vcc-continuation-interruption-remediation.html` through implementation, verification, implementation-stage PM review, scoped Codex and applicable Claude Code review, base freshness, commit, push, PR creation, PR feedback snapshot, and evidence-backed local merge readiness without expanding beyond the plan.

## Scope contract

- **Goal:** make compaction continuation self-healing with exactly one durably accepted continuation, truthful active-progress recognition, full queue activation budgets, safe retry/backoff, correct custom-message supersession, singleton coordinator ownership, and trustworthy audit/install evidence.
- **In scope:** plan phases P1–P6; `_pi/packages/pi-vcc` continuation protocol/coordinator/package surfaces; percentage-compaction producer parity; audit, soak, real-host integration, verifier, tests/fixtures, README validation guidance, plan progress, and sanitized validation evidence.
- **Out of scope:** summarization/pruning/recall/context accounting; general task supervision; process-kill/machine-shutdown/permanent-outage guarantees; direct edits to installed mirrors/live extensions; Pi session-writer repair unless current Pi main proves a small upstream prerequisite; unrelated upstream adoption.
- **Locked verification:** phase commands and final gates listed in the plan, including package tests, percentage-compaction tests, audit self-test, portable source verifier, source/installed fault matrix, real-host integration, and bounded recent-session audit.
- **Target branch:** `main` (`origin/main`).
- **Working branch:** `pi-vcc-continuation-remediation`.
- **Initial worktree state:** only the supplied plan file was untracked; no unrelated tracked modifications were present.

## Doct alignment

- Canonical existing reviewed plan document: `1aeb915c-6159-42d5-aef6-4e27f9764e5a`
- Workspace: `759bfae3-44f1-4ce5-9bff-9077d9933a21`
- URL: `https://doct.nodaste.com/d/workspace_759bfae3-44f1-4ce5-9bff-9077d9933a21/docs/1aeb915c-6159-42d5-aef6-4e27f9764e5a`
- State: lifecycle `active`, board `in_progress`, execution-ready metadata true.
- Durable listener: process `proc_6` with repeating `plan_comment_dispatch` watch.
- Note: an initial registration command discovered the source was already registered and created an unintended duplicate document `f8dbb7d4-0ae2-491c-a4d5-3bbd82b650c1`; the existing execution-ready document above remains canonical. No destructive cleanup was performed.

## Review / verification ledger

### Source implementation (P1-P5)

- Package suite: `229 passed, 0 failed`.
- Percentage-compaction suite: `54 passed, 0 failed`.
- Named post-fix regressions: `13 passed, 0 failed`.
- Audit self-test: PASS.
- Source install verifier: PASS; Bash 3.2 portability and exact-one checks present.
- File-backed real-host source integration: PASS.
- Source fault-matrix soak (20 compactions): PASS with embedded audit.
- `git diff --check`: PASS.
- Doct source updated after P1-P5 verification; P6 remains unchecked.

### Base freshness

- The implementation checkpoint was rebased successfully onto `origin/main` at `764fede` with no conflicts.
- All source gates were rerun after rebase and passed before installation.
- The upstream `install.sh` auto-discovery behavior exposed a stale explicit extension registration on dever; the installer/verifier remediation is included and validated.

### Review state

- First bounded Codex scoped review: `FIX_IN_SCOPE_FINDINGS` with five findings:
  1. fold durable acceptance before settlement/retry and V1 retry rehydration;
  2. retry error/abort after partial progress;
  3. refresh tool-stall ceiling on correlated tool updates;
  4. align audit correlation with runtime identity;
  5. exercise actual AgentSession delivery/persistence in the real-host gate.
- All five findings were addressed with regression coverage.
- Post-fix package suite: `237 passed, 0 failed`; all source gates pass, including the upgraded four-host AgentSession harness.
- The first Claude job produced no review artifact and was classified as review infrastructure failure, not a clean verdict.
- Second bounded Codex review found five remaining in-plan sibling issues: no-start post-persistence progress, reload singleton lifecycle, readiness-gated acceptance retries, V1 active-tool watchdog adaptation, and mixed-version audit duplicate identity.
- All five second-pass findings were fixed with regressions.
- Latest package suite: `241 passed, 0 failed`; named regression gate now covers 17 cases; actual AgentSession harness passes across five hosts including no-start and reload paths.
- The second Claude job was cancelled because implementation changed materially before it completed; it is not a verdict.
- Third Codex review found three final bounded issues: idle async-rejection readiness, singleton release for new/resume/fork, and V2 active-tool reload correlation.
- Those issues were fixed and covered by package plus actual-host tests.
- Current source evidence: `247 passed, 0 failed` package suite; `54 passed, 0 failed` percentage suite; 20 named regressions; audit PASS; 7-host AgentSession harness PASS; soak/verifier/diff checks PASS.
- Earlier Claude attempts either produced no artifact or were superseded/cancelled; none count as a verdict.
- Release-candidate Codex found three remaining bounded issues: partial parallel-tool reload correlation, audit zero/cross-retry exact-one cardinality, and singleton release when replacement terminalization persistence throws.
- All three were fixed with V1/V2 parallel-tool and failure-injection coverage.
- Current source evidence: `256 passed, 0 failed` package suite; 28 named regressions; all other source gates pass.
- The previous Claude job was superseded and cancelled after these fixes; it is not a verdict.
- Convergence Codex found three additional bounded issues: failed-ordinal acceptance could suppress retry, the real-host all-case gate lacked explicit matrix completeness, and audit wire validation had drifted from the strict runtime parser.
- All three were fixed with persisted error/abort retry tests, an explicit 14-host required-case registry, and strict V1/V2 audit wire/enum/privacy parity fixtures.
- Current source evidence: package `261 passed, 0 failed`; percentage `54 passed, 0 failed`; 31 named regressions; audit/14-host harness/soak/verifier/diff checks all PASS.
- Claude produced substantive `PASS_SCOPED` text twice but the canonical launcher classified both artifacts invalid; per policy they remain infrastructure failures, not clean verdicts.
- Final-current Codex found four remaining issues: retry-aware audit cardinality, crash recovery between terminal snapshot/outcome writes, V1 retrying ambiguity after accepted failure, and a V1 percentage-compaction producer. All were fixed.
- A final native GPT-5.6 scoped quality review then found one producer budget mismatch (60s vs locked 15s); it was fixed and covered by an explicit percentage-compaction assertion.
- Final scoped quality verdict: `PASS_SCOPED`; evidence is in `thoughts/validation/pi-vcc-final-quality-review.md`.
- Implementation-stage PM verdict: `Ready after integration`; no product decision remains open. P6 and base integration remain the only readiness gates.
- Canonical Claude Code review was applicable and attempted repeatedly after a successful smoke. Each substantive review text reported `PASS_SCOPED`, but the launcher classified every artifact `CLAUDE_REVIEW_ARTIFACT_INVALID`. Per policy this is recorded as a persistent review-infrastructure failure, not a clean Claude verdict and not replaced with an alternate transport.

### Final source and P6 rollout

- Final source suite after rebase: `267 passed, 0 failed` package tests; `54 passed, 0 failed` percentage-compaction tests; 31 named regressions; audit self-test, source verifier, 14-host source real-runtime matrix, 20-compaction source soak, and `git diff --check` PASS.
- Installed the committed candidate on mbp and dever using `./install.sh --pi`; no installed package or live extension was edited directly.
- mbp installed verification: exact-one package registration, one auto-discovered percentage-compaction path, source/installed hashes equal — PASS.
- dever installed verification: exact-one package registration, stale explicit extension path removed by installer, one auto-discovered path, source/installed hashes equal — PASS.
- mbp and dever installed fault matrix: 20 terminal transactions with embedded audit — PASS on both.
- mbp and dever installed real-host matrix: 14 file-backed AgentSession hosts — PASS on both.
- Bounded post-install audit since `2026-07-15T02:35:35Z` with `--require-terminal` — PASS on both.
- Rollout prerequisites fixed during P6: auto-discovered extension de-duplication, fail-closed ambiguous relative registrations, global Pi runtime resolution for installed harnesses without development dependencies, and mtime-bounded stale JSONL filtering.
- P6 is complete; no unresolved continuation interruption or product decision remains.
