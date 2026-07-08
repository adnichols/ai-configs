---
date: 2026-07-08
plan: thoughts/plans/pi-codex-goal-fork-compaction-persistence.html
type: implementation-pm-review
status: pass
---

# PM Review: pi-codex-goal Fork Compaction Persistence

## Scope Checked

- P1/P2 fork work is present on `adnichols/pi-codex-goal` main at `fe5f306579025c86b6d30b51203bf2451d349896`, matching the tested runtime patch from the fork checkout.
- P3 ai-configs changes switch package management from upstream `npm:pi-codex-goal` to `git:github.com/adnichols/pi-codex-goal` and remove stale npm registrations.
- `scripts/verify-pi-install.sh`, `test_install_shared_skills.sh`, and `_pi/README.md` now agree on the fork source and stale npm detection/removal.
- Dever rollout evidence shows `pi list` contains `git:github.com/adnichols/pi-codex-goal` and not `npm:pi-codex-goal`; `scripts/verify-pi-install.sh` passed.
- Installed-runtime smoke evidence under `/tmp/pi-goal-vcc-min-session` loaded only installed `pi-codex-goal` plus installed `pi-vcc`, created an active goal, invoked `compact_context`, observed no paused state in goal custom entries, verified marker content `PI_VCC_GOAL_OK`, and completed the goal.

## Verdict

PASS: The implemented outcome satisfies the plan intent for the current host. Routine pi-vcc compaction no longer leaves the installed goal runtime in a misleading paused state on the exercised installed-runtime path. P4 MBP rollout is pending only because the ai-configs changes are not yet pushed to `origin/main`; it should be completed after PR merge or by applying this branch on MBP.
