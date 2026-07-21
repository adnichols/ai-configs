1. Scope checked

`HARD_LIMIT_RE` and direct launcher tests only.

2. Coverage table

| Case | Coverage |
|---|---|
| `You've hit your weekly rate limit · resets 3am` | Matched and asserts exit code 25 |
| `You've used 75% of your weekly limit · resets 3am` | Explicitly tested as non-hard-limit |

3. Findings

None.

4. Final verdict

VERDICT: PASS_SCOPED