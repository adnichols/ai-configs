# ADN Dev Workflow Stages

This reference file defines the exact stage behavior for `adn-dev-wf`.

## 1. Plan materialization

Use the single-file plan contract already established in this repo:
- one file in the repo's active plan format
- preserve existing completed progress items and append-only logs
- near-top Decision Attention exposes blockers, required user input, unresolved decisions, and weak evidence
- `## Progress` contains the only checkboxes and maps one-to-one with detailed phases
- each phase includes `### Tests first`, `### End State`, `### Work`, `### Expected files`, `### Open questions / decision dependencies`, and `### Verify`
- UI impact is explicitly triaged and is not `unknown` for execution-ready plans
- execution-ready plans must not leave unresolved open questions

If a legacy bundle exists under `thoughts/plans/<slug>/`, read it for migration but do not modify legacy files.

## 2. Plan-stage PM reshape

Use this stage when the work affects product outcomes, defaults, recovery flows, or operator or agent experience.
Edit the plan directly.
Focus on:
- smallest complete useful slice
- truthful defaults and status surfaces
- self-healing for routine faults
- fail-closed boundaries for ambiguous or risky paths
- verification that proves the user-visible outcome, not just code presence

If the PM reshape materially changes the plan, treat the reshaped plan as the new review target.

## 3. Blocker-only plan review

Review against the plan's own goal, non-goals, acceptance criteria, and validated scope.
Leave inline comments only for:
- blockers
- material risks
- missing decisions required to execute the stated scope
- wrong references or infeasible assumptions

Use this format:

```markdown
[REVIEW:Name] GAP: comment text [/REVIEW]
```

Do not integrate, rewrite, or clean the plan in this stage.

## 4. Review integration

Classify each review comment as material or optional.
Integrate only material comments into the plan.
Optional comments may be dropped or recorded as explicit non-goals or documented out-of-scope context. Do not classify plan-required work, BDD gaps, verification gaps, or acceptance-criteria gaps as optional/deferred.

Before leaving this stage:
- all inline `[REVIEW:...]` comments are removed
- the plan remains single-file and resumable
- `## Progress` still matches the phase headers
- each acceptance area still has verification coverage

## 5. Execution readiness check

Do not implement until all of these are true:
- no inline review comments remain
- the plan status is execution-ready
- `## Progress` exists and maps one-to-one with detailed phases
- `Resume Instructions (Agent)` exists
- Decision Attention does not hide blockers, required user input, or low-confidence decisions
- each active phase includes `### Tests first`, `### End State`, `### Work`, `### Expected files`, `### Open questions / decision dependencies`, and `### Verify`
- UI impact is explicitly triaged and is not `unknown`
- no unresolved open questions materially affect behavior
- for reviewed HTML plans, the closing ready verdict comes from an independent reviewer by substance, such as `PLAN_EXECUTION_READY` from `reviewed-html-plan` or an equivalent approved `PASS_NO_ISSUES` verdict, and readiness metadata is truthful

## 6. Direct execution

Execution follows the `dev:run` semantics rather than the retired multi-pass execution loop.

For each phase:
1. implement the phase
2. run its `### Verify` steps
3. delegate exactly one `quality-reviewer` pass
4. rerun impacted verification
5. mark the phase complete only if verification passed and the reviewer cleared it
6. append decisions and only true out-of-scope low-risk follow-ups to `## Decisions / Deviations Log`, with evidence and a tracking destination

If the phase is too large for one safe pass, same-scope re-chunk it in the plan and continue.
Do not widen scope during re-chunking.

## 7. Implementation-stage PM review loop

After execution and validation, re-check whether the work actually fulfills the intended outcome.
If not:
- edit the plan directly with the missing work
- rerun blocker-only plan review
- rerun review integration
- continue execution
- repeat validation

Cap this post-execution PM loop at three iterations.
If the branch still does not converge after three passes, stop and surface the blocker to the user.

## 8. Finalization

Before declaring success:
- run the repo's full validation bar
- ensure the plan truthfully shows completion
- ensure decisions and deviations are logged
- keep any PR or publish step separate unless the user asked for it

## Legacy command mapping

The workflow encoded here replaces the older prompt-chained reviewed-plan sequence. `adn-dev-wf` is now the canonical entry point for that path.
