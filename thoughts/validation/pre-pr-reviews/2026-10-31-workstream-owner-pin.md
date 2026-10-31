# Pre-PR review: workstream-owner workspace pin and split-plan ownership (branch `workstream-owner-pin`)

- Base: `origin/main` (`028be75`)
- Scope: `skills/workstream-owner/scripts/start_wks.py` (pin step), new `skills/workstream-owner/scripts/pin_workspace.mjs`, SKILL.md and `assets/owner-brief.md` (split-plan ownership, fallback brief paths), tests (`scripts/tests/test_start_wks.py`, new fixture `scripts/tests/fixtures/start_wks_fake_client.mjs`), CHANGELOG. Non-goals: nod-fleet's orchestrator tools (cleanup, `WKS_START` handling).
- Reviewer: OMP `reviewer` agent (`PinReview`), read-only.

## Cycles

| Cycle | Trigger | Verdict |
| --- | --- | --- |
| 1 | Whole diff | REQUEST_CHANGES: 2 blockers, 4 nits |
| 2 | Targeted rereview of the fixes | APPROVE_WITH_NITS: both blockers resolved |

## Triage

| Finding | Severity | Decision | Evidence |
| --- | --- | --- | --- |
| 1 An interrupt or a non-`FileNotFoundError` OSError during the pin lost the started owner's report (traceback, no JSON) | P2 | Fixed | `pin()` catches `BaseException` around both `paseo_node()` and `run()` and returns `pin_error`; the docstring limits rollback to steps 3 to 5. Reviewer reproduced SIGTERM mid-pin: exit 0, full report, `pin_error: "KeyboardInterrupt: SIGTERM"`. |
| 2 The orchestrator's cleanup of the first merged item archives the shared WKS workspace, so a split owner loses its worktree | P2 | Fixed in the contract | SKILL.md step 3: at the split, the owner asks the orchestrator to keep its workspace and worktree out of the cleanup of every item but the last PR's, and names the PRs still to come in each `WKS_STATUS`. The mechanism stays with the orchestrator (nod-fleet unchanged). |
| 3 Later-PR branch wording conflicted with the brief's PR branch | P3 | Fixed | Later PRs: new branch from `origin/main`, item asked for with `Branch <branch>-2`, push to the PR branch the brief names; one branch at a time. |
| 4 Unrecognized install path untested | P3 | Fixed | `test_a_paseo_install_without_the_daemon_client_still_starts_the_owner_unpinned`. |
| 5 Linux desktop bundle unhandled | P3 | Fixed | `paseo_node()` tries the macOS helper, then `Paseo.bin`, then `Paseo`, in the app launcher's order. |
| 6 Docstring contradiction | P3 | Fixed | With finding 1. |
| Cycle-2 nits | P3 | 2 of 3 fixed | Empty interrupt message now reports the type alone; VALIDATED goes to "that PR's item". Not added: an in-process test of the interrupt branch (verified by the reviewer's and this session's throwaway runs). |

## Residual risk

Finding 2 depends on the orchestrator acting on the owner's request before the first item reaches MERGED; `tick_cleanup.py` otherwise archives the workspace. Recorded for the operator.

## Verification

- `python3 -m unittest scripts/tests/test_start_wks.py`: 13 OK.
- `cd _adn && bun test`: 38 pass; `cd _adn && bun tests/routing-eval.ts`: ok, 23.
- `bash test_install_shared_skills.sh`: 32 pass, 1 fail (`test_hermes_config_sync_preserves_cron_runtime_state`: `No module named 'yaml'`, this host's Python, unrelated to the skill).
- Real pin on mbp through the desktop app's helper: `pin()` on `wks_119da1c0dac33bb7` returned no error; a made-up id returned `pin wks_0000000000000000: Workspace not found`.

## Result

PASS for PR creation: no unresolved in-scope P1/P2 findings. Merge is authorized by the operator for this follow-up.
