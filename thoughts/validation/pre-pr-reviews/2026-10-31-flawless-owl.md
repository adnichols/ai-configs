# Pre-PR review: workstream-owner skill (branch `flawless-owl`)

- Base: `origin/main`
- Scope: new shared skill `skills/workstream-owner` (SKILL.md, `assets/owner-brief.md`, `scripts/start_wks.py`), its tests (`scripts/tests/test_start_wks.py`, `scripts/tests/fixtures/start_wks_fakes.py`), the `install-matrix.json` entry and the CHANGELOG line. Non-goals: Paseo profiles (host-local), changes to the orchestrator's own tools.
- Reviewer: OMP `reviewer` agent (`WorkstreamOwnerReview`), read-only.

## Cycles

| Cycle | Trigger | Verdict |
| --- | --- | --- |
| 1 | Whole diff | CHANGES_REQUESTED, 9 findings |
| 2 | Targeted rereview of the fixes for 1-9 | APPROVE_WITH_NITS: 1-6, 8, 9 resolved; 7 partially resolved |

## Triage

| Finding | Severity | Decision | Evidence |
| --- | --- | --- | --- |
| 1 Create failure left a stray workspace reported as "nothing created" | P2 | Fixed | Every create failure raises `Failed`; `main` rolls back on `BaseException`; rollback finds the workspace by title. Test `test_a_create_that_fails_after_creating_is_rolled_back`. |
| 2 Owner closed replaced PRs itself | P2 | Fixed | SKILL.md: name them in reports; the orchestrator closes them through its close procedure. |
| 3 Owner never saw the repository's setup rule | P2 | Fixed | The `WKS_START` ask requests the item's worker brief rendered by `render_brief.py`; fallback is `references/worker-brief.md` plus the project's `[overlay]`. |
| 4 Usage exit code documented as 1, argparse exits 2 | P3 | Fixed | `Parser.error` prints JSON and exits 1; test covers it. |
| 5 Isolation and background assertions were vacuous | P2 | Fixed | The fake inherits background from `PASEO_AGENT_ID`; the test asserts through the orchestrator's plain `workspace ls` view. |
| 6 No ledger item for `land.py` | P2 | Fixed | `WKS_START` asks for an item with Repo, Branch, Source docs and Workspace / agent. |
| 7 Missing failure-path tests | P3 | Partly fixed | Added cross-host duplicate, unreachable host, moved branch kept, usage, local branch refusal. Not added: create exit 0 with bad JSON, local `workspace ls` failure, `paseo run` failure. Each raises `Failed` into the same tested rollback path. |
| 8 Duplicate check was per host | P2 | Fixed | `fleet()` plus parallel per-host listing; unreachable hosts reported in `unchecked_hosts`. |
| 9 Finish conditions | P3 | Fixed | session-cleanup first; final `WKS_STATUS` shape; orchestrator owns worktree cleanup. |
| Cycle-2 nits | P3 | Fixed | Re-list after an interrupted create; parallel remote listings; "owned by agent <first 8 hex>" wording; fallback no longer renders the brief by hand; CHANGELOG path. |

## Changes after cycle 2

Operator direction (2026-10-31 MDT): the skill must not be ccore2-specific. SKILL.md, the owner brief, the matrix notes and the CHANGELOG line now name the repository's own delivery and PR skills (verified-build where present), take setup, validation and landing rules from the rendered worker brief and the project profile, and leave merging to whoever the profile's `[merge]` rule names. Prose only; no code changed. Per the review budget (a third cycle only for a new concrete blocker), no third review ran.

## Verification

- `python3 -m unittest scripts/tests/test_start_wks.py`
- `cd _adn && bun test`; `cd _adn && bun tests/routing-eval.ts`
- Disposable install (temp HOME): `install.sh --skills` twice, then `--repo-skill workstream-owner` reports the skill unchanged; the installed copy's dry run works.
- Live dry runs on this host; one real launch (agent `b5fd6877`) seen by the orchestrator's `wks_nudge` sweep, then archived with its branch deleted.

## Result

PASS for PR creation: no unresolved in-scope P1/P2 findings. No external approval required.
