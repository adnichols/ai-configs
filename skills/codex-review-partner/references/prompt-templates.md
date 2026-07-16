# Prompt Templates

Use these as starting points for the input file passed to `run-review.sh`.

## implementation-review

```md
Review this implementation.

Repo: /absolute/path/to/repo
Goal: <what the change is supposed to accomplish>
Files:
- path/to/file1
- path/to/file2

Changed behavior (author claims — verify against the code, do not assume true):
- <bullet>
- <bullet>

Checks already run (claims to confirm, not evidence of correctness):
- <command/result>

Review for:
- correctness
- missed callsites
- edge cases
- test gaps
- maintainability
- generic key-name matching/remapping where the key name may not uniquely determine the value's type or target (test non-target variants)
- fail-closed/bail paths reachable by valid input
- producer/consumer and round-trip parity (import vs export, encode vs decode)

If you find issues, rank them by severity and cite files/lines when possible.

End with exactly one final line: `VERDICT: FINDINGS_TO_RESOLVE`, `VERDICT: CLEAN_FOR_PR`, `VERDICT: BLOCKED_BY_QUESTION`, or `VERDICT: REVIEW_INCOMPLETE_RERUN_NEEDED`.
```

## adversarial-implementation-review

Use this after actionable PR feedback proves a prior local review missed issues.

```md
Adversarially review this implementation after a review escape.

Repo: /absolute/path/to/repo
Goal: <what the change is supposed to accomplish>
Scope contract:
- <plan acceptance criteria, in-scope surfaces, and non-goals>

Current PR diff:
- Base/range: <base...HEAD>
- Files:
  - path/to/file1
  - path/to/file2

Escaped PR feedback (treat the direct fix and suspected family as claims to verify or refute, not facts; re-derive the invariant from the code/schema):
- Reviewer/comment URL: <url>
- Direct issue: <summary>
- Direct fix: <summary or commit>
- Suspected failure family: <edge case / contract / callsite / validation / state / security / data-loss / test-gap pattern>

Checks already run (claims to confirm, not evidence of correctness):
- <command/result>

Review adversarially for:
- sibling callsites or analogous code paths with the same problem
- repeated assumptions or partial fixes
- missing tests that allowed the escaped issue through
- generic key-name matching/remapping where the key name may not uniquely determine the value's type or target (test non-target variants: numbers, booleans, objects, unrelated strings)
- fail-closed/bail paths reachable by valid, schema-conformant input
- producer/consumer and round-trip parity (import vs export, encode vs decode, rewrite vs collect)
- boundary, lifecycle, concurrency, auth, migration, or data-loss variants relevant to this plan
- evidence that the fix addresses the root cause rather than one symptom

Stay read-only and scope-bound. Do not propose unrelated cleanup or product expansion. Rank findings by severity and cite files/lines when possible.

End with exactly one final line from the generic implementation vocabulary above.
```

## plan-review

```md
Review this implementation plan.

Repo: /absolute/path/to/repo
Goal: <what the plan is trying to accomplish>
Constraints:
- <bullet>
- <bullet>

Plan:
<paste the plan here>

If the plan is HTML, treat the HTML file as the authoritative plan artifact. Do not require Markdown conversion.

Review for:
- missing steps
- unsafe assumptions
- architectural risks
- verification gaps
- rollback or migration issues

Return concrete objections and suggested corrections.

End with exactly one final line: `VERDICT: PLAN_EXECUTION_READY`, `VERDICT: PLAN_NEEDS_REVISION`, `VERDICT: BLOCKED_BY_QUESTION`, or `VERDICT: REVIEW_INCOMPLETE_RERUN_NEEDED`.
```

## pair

```md
Act as a pairing partner on this technical problem.

Repo: /absolute/path/to/repo
Question: <what needs to be figured out>
Relevant files:
- path/to/file1
- path/to/file2

Known facts:
- <bullet>
- <bullet>

Unknowns:
- <bullet>
- <bullet>

Help me reason through the tradeoffs, likely failure modes, and the next best debugging or implementation step.
```
