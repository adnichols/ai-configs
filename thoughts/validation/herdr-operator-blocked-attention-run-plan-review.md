# Herdr operator-blocked attention — Terra implementation review

Reviewer: repository `reviewer` (openai-codex/gpt-5.6-terra, medium)
Review cycle: 1
Candidate: live worktree at HEAD `1d763de` plus dirty/untracked plan-bound changes

## Verdict

VERDICT: FINDINGS_TO_RESOLVE

## Finding triage

| Finding | Source | Classification | Decision | Evidence |
|---|---|---|---|---|
| Pi marker reader accepts schema-incomplete matching JSON | `_pi/extensions/herdr-agent-state.ts` | IN_PLAN, P2 | Fix complete marker validation and add counterexample tests | Locked marker schema and fail-open valid-marker requirement |

## Reviewer coverage

The reviewer inspected the helper, Pi extension, delivery reconciliation family, Heddle gate wrapper, install/docs, and supplied verification evidence. It did not execute verification or live Herdr behavior.

## Required fix

Validate `paneId`, `message`, ISO-UTC `setAt`, enum `kind`, and boolean `notifyOnSet` before the Pi reporter treats a marker as active. Add incomplete/wrong-type marker tests.

## Targeted rereview

Review cycle: 2 (targeted after fix)

The Pi reader now validates every locked schema field and fails open for incomplete JSON, invalid enum/type/timestamp, mismatched pane, malformed JSON, and missing files. Targeted tests passed. The reviewer found no new in-scope P1/P2 issue.

VERDICT: PASS

Not examined: broader delivery/release wiring was not repeated in the targeted rereview; it remained covered by cycle 1 and unchanged by this fix.
