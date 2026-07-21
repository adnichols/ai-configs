1. Scope checked

`git diff HEAD` for the specified roster test and start-linear-issue prompt only.

2. Coverage table

| Required contract | Test coverage |
|---|---|
| Retains `Title` | `assertIn("- Title", prompt)` |
| Exact context-note heading | `assertIn("# <ISSUE_KEY>: <Title>", prompt)` |

3. Findings

None.

4. Final verdict

VERDICT: PASS_SCOPED