1. Scope checked

Reviewed the specified installer/model/verifier/test slice against AC1, AC6, AC7, AC9, BDD7, and installed-side BDD8. Re-derived exact-ID and scoped-value matching, direct and transactional review-stack paths, symlink guards, and actual temporary-home test coverage.

2. Coverage table

| Area | Result |
|---|---|
| Exact retired model IDs | Correctly limited to `gpt-5.4` and `gpt-5.4-mini` under `openai-codex` |
| Caller-owned models/providers | Preserved for unrelated providers and custom same-provider IDs; suffix-based pruning is gone |
| `enabledModels` | Unscoped, `openai-codex/`, and normal historical alias forms are pruned; non-string entries are retained |
| Exact agent roster | Review-stack now uses the same exact-directory helper as full install; stale agents are removed |
| Verifier parity | Both scopes compare agent filename sets exactly and reject retired IDs |
| Transaction path | Actual review-stack install and failpoint rollback paths are exercised; symlink rejection is covered for `.pi` and `.pi/agent` |

3. Findings

- **P2 — REGRESSION_FROM_THIS_DIFF**
  [install.sh](/Users/anichols/code/ai-configs/install.sh:2033)
  Evidence: the installer writes `models.json` at lines 2033–2036 before parsing and validating `settings.json` at lines 2039–2045. A malformed settings object or non-list `enabledModels` therefore exits after model pruning/merging has already changed local state. Direct `./install.sh --pi-review-stack` also replaces the agent directory before reaching this failure. The transaction wrapper restores this case, but the advertised bounded installer itself can leave a partial install. No test covers this malformed-settings failure path.
  Plan requirement: P4’s isolated installation/local-data-loss safety and assigned malformed-data/transaction-safety failure family.

- **P3 — IN_PLAN**
  [scripts/verify-pi-install.sh](/Users/anichols/code/ai-configs/scripts/verify-pi-install.sh:93) and [scripts/verify-pi-install.sh](/Users/anichols/code/ai-configs/scripts/verify-pi-install.sh:442)
  Evidence: installer matching accepts every provider beginning `openai-codex-`, including `openai-codex-/gpt-5.4` (`startswith("openai-codex-")`, [install.sh](/Users/anichols/code/ai-configs/install.sh:2057)). Both verifier regexes require at least one post-hyphen character (`[^/]+`), so that stale scoped value passes verification. The test fixture also omits this boundary case.
  Plan requirement: AC6/AC9 require historical `openai-codex-*` matching and verifier proof using the same effective rules.

4. Remaining checks/follow-up

Fix the two in-scope items, then rerun the supplied targeted suites and syntax/JSON/diff checks.

5. Final verdict

VERDICT: FIX_IN_SCOPE_FINDINGS