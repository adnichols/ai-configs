# Item file template

One file per work item at `items/WI-NN-<slug>.md`. IDs are sequential within
the tracker and never reused. Keep the operator's words verbatim; mark anything
you or a research agent concluded as `[INFERRED]`.

```markdown
# WI-NN: <short title>

Kind: BUG | FEATURE | REFACTOR | PERF | OTHER   (your read; the worker's ADN routing decides the playbook)
State: <state>             Repo: <checkout path> @ <base branch>
Surface: <product area, e.g. Ava Signals › Requested by me>
Source: operator | secondhand (<who / meeting>)

## Operator report
> <verbatim message text> (<timestamp>)
> <verbatim follow-ups, each with timestamp>

## Evidence
- `<absolute image path>`: <what it shows: surface, state, what is wrong>
- <pasted errors or logs, verbatim>

## Observed / expected            (features and other changes: Current / desired)
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
- <WI-MM: duplicate of | overlaps | blocked by>

## Handoff
Workspace: <id>   Worktree: <path>   Branch: <branch>   Agent: <id>   Launched: <time>

## Timeline
- <time> <state change, PR URL, head SHA, verdict, operator decision>
```

## States

`INTAKE` → `RESEARCHING` → `NEEDS_INFO` → `READY` → `QUEUED` (waiting for a
lab or an overlapping item) → `HANDED_OFF` → `PROTOTYPE_REVIEW` /
`NEEDS_OPERATOR` / `BLOCKED` → `VALIDATED` → `MERGED` → `CLEANED`.

Terminal states other than `CLEANED` need a recorded decision. The driver
decides `DUPLICATE` (name the surviving item), consulting the oracle when
unsure. `NOT_REPRODUCED`, `EXPECTED_BEHAVIOR`, `WONT_FIX`, and `DEFERRED` are the
operator's, via a card, because each turns on whether the behavior is expected or wanted. Every
terminal item still gets `worktree-cleanup` run on its
workspace before the tracker concludes.
