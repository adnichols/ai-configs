# Issue file template

One file per issue at `issues/BB-NN-<slug>.md`. IDs are sequential and never
reused. Keep the operator's words verbatim; mark anything you or a research
agent concluded as `[INFERRED]`.

```markdown
# BB-NN: <short title>

Type: BUG | FEATURE        Mode: BUG_FIX | FEATURE_CHANGE
State: <state>             Repo: <checkout path> @ <base branch>
Surface: <product area, e.g. Ava Signals › Requested by me>
Source: operator | secondhand (<who / meeting>)

## Operator report
> <verbatim message text> (<timestamp>)
> <verbatim follow-ups, each with timestamp>

## Evidence
- `<absolute image path>`: <what it shows: surface, state, what is wrong>
- <pasted errors or logs, verbatim>

## Observed / expected            (features: Current / desired)
- Observed: ...
- Expected: ...

## Reproduction
1. ... [INFERRED where not from the operator]

## Environment
<lab or hub URL, org/space, account role, browser or client; unknown is fine>

## Research findings
- Code: `<path>:<lines>`: <role>
- Recent changes: <commits or PRs touching the area>
- Related open PRs or issues: ...
- Hypotheses: ... [INFERRED]

## Acceptance criteria
- [ ] <observable result, including persistence or cross-client effects when relevant>

## Scope and non-goals
- ...

## Open questions
- Blocking: ...
- Non-blocking: ...

## Related
- <BB-MM: duplicate of | overlaps | blocked by>

## Handoff
Workspace: <id>   Worktree: <path>   Branch: <branch>   Agent: <id>   Launched: <time>

## Timeline
- <time> <state change, PR URL, head SHA, verdict, operator decision>
```

## States

`INTAKE` → `RESEARCHING` → `NEEDS_INFO` → `READY` → `QUEUED` (waiting for a
lab or an overlapping issue) → `HANDED_OFF` → `PROTOTYPE_REVIEW` /
`NEEDS_OPERATOR` / `BLOCKED` → `VALIDATED` → `APPROVED` → `MERGED` →
`CLEANED`.

Terminal states other than `CLEANED` require the operator's decision:
`DUPLICATE` (name the surviving issue), `NOT_REPRODUCED`, `WONT_FIX`, and
`DEFERRED`. Every terminal issue still gets `worktree-cleanup` run on its
workspace before the bugbash concludes.
