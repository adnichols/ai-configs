# Pre-PR review: workstream-owner progress heartbeat (branch `workstream-owner-heartbeat`)

- Base: `origin/main` (`1d8a1d1`)
- Scope: `skills/workstream-owner/scripts/start_wks.py` (heartbeat step), new `skills/workstream-owner/assets/progress-heartbeat.md`, SKILL.md and `assets/owner-brief.md` (heartbeat contract), tests (`scripts/tests/test_start_wks.py`, `scripts/tests/fixtures/start_wks_fakes.py`), CHANGELOG. Non-goals: nod-fleet's orchestrator tools; the orchestrator's 4-hour `WKS_STATUS` request is unchanged.
- Reviewer: OMP `reviewer` agent (`HeartbeatReview`), read-only.

## Cycles

| Cycle | Trigger | Verdict |
| --- | --- | --- |
| 1 | Whole diff | CHANGES REQUIRED: 0 blockers, 3 should-fix |
| 2 | Targeted rereview of the fixes | APPROVE: all three resolved, no new findings |

## Triage

| Finding | Severity | Decision | Evidence |
| --- | --- | --- | --- |
| 1 The owner learns the heartbeat id only from a firing, yet Finish requires it | should-fix | Fixed in the contract | SKILL.md: the `fired (id=...)` line is the id's source (`paseo heartbeat` has no list command, and `paseo schedule ls` filters to new-agent schedules); Finish item 2: without a firing yet, report the final `WKS_STATUS`, end the turn and delete it when it next fires; the orchestrator's cleanup, which archives the owner, also ends it. |
| 2 Tests did not prove the heartbeat prompt is the new asset; dry-run fields unasserted | should-fix | Fixed | The success test asserts the name `WKS Ava format progress`, cron, status, report id, heartbeat-specific text and the brief's source absent from the prompt; the dry-run test asserts `heartbeat_cron` and `heartbeat_prompt`. |
| 3 The fake printed JSON without `--json`, so dropping the flag went untested | should-fix | Fixed | The fake prints a text table for `heartbeat create` unless `--json` is passed, as the real CLI does. |

## Residual risk

The heartbeat relies on Paseo daemon behavior read from the 0.13 and 0.14 server source: a firing while the agent has an in-flight run fails and the schedule stays active, and archiving an agent completes its heartbeats. A Paseo release that changes either would need the contract revisited.

## Verification

- `python3 -m unittest scripts/tests/test_start_wks.py`: 15 OK.
- `cd _adn && bun test`: 38 pass; `cd _adn && bun tests/routing-eval.ts`: ok, 23.
- `bash test_install_shared_skills.sh`: 1 fail, `test_hermes_config_sync_preserves_cron_runtime_state` (`No module named 'yaml'`, this host's Python, unrelated to the skill); the rest pass.
- `start_wks.py --dry-run` on mbp shows `heartbeat_cron` `*/30 * * * *` and the rendered prompt.
- Real heartbeat through this branch's `add_heartbeat()` on the running owner `74cdad35` (mbp, Paseo 0.14): heartbeat `4ab375e0`, stored target `{type: agent, agentId: 74cdad35-…}`, cron `*/30 * * * *`, status active; the target check passed against the real CLI's `agent:<7>` row.

## Result

PASS for PR creation: no unresolved findings. Merge is authorized by the operator for this follow-up.
