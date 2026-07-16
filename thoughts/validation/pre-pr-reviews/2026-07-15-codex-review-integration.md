## 1. Scope checked

Reviewed P3–P5 and AC1/AC9–AC15 against `origin/main` plus the current worktree. Inspected all named files and direct installer, extension-host, scanner, and runtime references. No files were edited.

## 2. Coverage table

| Surface | Check performed | Result | Coverage |
|---|---|---|---|
| Workflow migration/profiles | Traced maintained Pi and non-Pi launch instructions and verdict budgets | Current callsites use the correct profiles | Complete |
| Source-policy enforcement | Reviewed scanner logic and tests against multiline bypasses | Finding 5 | Complete |
| Bounded installation | Checked configuration preservation and mutation allowlist | Findings 1–2 | Complete |
| Transaction/rollback | Traced snapshots, failure traps, restoration, and tests | Finding 2 | Complete |
| Check-only verifier | Traced scoped and full execution paths | Finding 3 | Complete |
| Installed-host evidence | Confirmed installed loader/session path, completion callback, shutdown case, and real opt-in route | No additional material finding | Complete |
| Session audit | Checked state, artifact, classification, session, and duplicate-completion evidence | Finding 4 | Complete |
| Documentation/progress | Compared claims with installed behavior and verification evidence | Finding 1; completion claims are premature | Complete |

## 3. Findings

1. **P1 — IN_PLAN — [install.sh](/home/anichols/.herdr/worktrees/ai-configs/codex-review-plugin/install.sh:2174)**  
   The bounded installer replaces `models.json` wholesale and copies the unresolved `APPEND_SYSTEM.md` template directly. This bypasses the canonical merge path, which preserves local providers/API keys, and the renderer, which replaces `{{AI_CONFIGS_VERSION}}`. Successful transactions delete their snapshots, so overwritten local model configuration is not recoverable through rollback. This violates AC15’s foreign-entry preservation and installed system-guidance requirements. The verifier also blesses the unresolved template by comparing it directly with the source at [verify-pi-install.sh](/home/anichols/.herdr/worktrees/ai-configs/codex-review-plugin/scripts/verify-pi-install.sh:43).

2. **P2 — IN_PLAN — [install.sh](/home/anichols/.herdr/worktrees/ai-configs/codex-review-plugin/install.sh:2160)**  
   The installer creates and chmods `~/.agents` and `~/.agents/skills`, although the allowlist contains only `~/.pi` and four skill directories. The transaction snapshots only those bounded roots at [install-pi-transactionally.sh](/home/anichols/.herdr/worktrees/ai-configs/codex-review-plugin/scripts/install-pi-transactionally.sh:25), so a pre-existing parent changed from mode 0755 to 0700 remains changed even after rollback. Tests use absent parent directories and therefore miss this counterexample. AC15 requires no mutations outside the allowlist and exact restoration after structural failure.

3. **P2 — IN_PLAN — [verify-pi-install.sh](/home/anichols/.herdr/worktrees/ai-configs/codex-review-plugin/scripts/verify-pi-install.sh:280)**  
   Full-scope `--check-only` still invokes `repair_pi_model_defaults`, which writes both Pi settings and `web-search.json`. `CHECK_ONLY` is enforced only for the review-stack branch and is otherwise ignored. The locked decision explicitly requires `--check-only` to be non-mutating in every scope; the transaction tests cover only review-stack check-only and do not catch this.

4. **P2 — IN_PLAN — [audit-codex-review-sessions.py](/home/anichols/.herdr/worktrees/ai-configs/codex-review-plugin/scripts/audit-codex-review-sessions.py:8)**  
   The “session audit” reads only controller state files and output artifacts; it never correlates Codex sessions or completion-delivery evidence. It also accepts any uppercase final verdict rather than the state’s selected profile vocabulary. The supposed duplicate-completion fixture at [test_audit_codex_review_sessions.py](/home/anichols/.herdr/worktrees/ai-configs/codex-review-plugin/scripts/tests/test_audit_codex_review_sessions.py:17) merely duplicates a `jobId`, so duplicate or missing completion notifications remain undetectable. P5 explicitly requires corresponding-session auditing and fixtures for missing/duplicate completion, making the reported 20-job audit insufficient evidence.

5. **P3 — IN_PLAN — [check_no_direct_codex_review_launches.py](/home/anichols/.herdr/worktrees/ai-configs/codex-review-plugin/skills/codex-review-partner/scripts/check_no_direct_codex_review_launches.py:10)**  
   The source scanner examines one line at a time. A conventional multiline prompt command such as `run-review.sh \` followed by `--mode plan-review` passes undetected. Its only test executes the scanner against the currently clean repository rather than supplying positive and exempt fixtures. P3 and AC1 require source-policy tests to prevent maintained workflow drift, including shell-indirection variants.

## 4. Remaining checks

Review coverage is complete. No additional follow-up slice is needed before addressing these findings; P3–P5 should not remain marked complete until the affected tests and verification evidence pass.

VERDICT: FIX_IN_SCOPE_FINDINGS