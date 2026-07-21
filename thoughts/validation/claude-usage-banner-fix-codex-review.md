1. Scope checked

Working-tree diff limited to the three requested launcher, fake-TUI, and test files.

2. Coverage table

| Area | Result |
|---|---|
| Informational weekly banner with reset time | Covered; does not match the new regex. |
| Post-submit fake-TUI path | Covered; banner is emitted after Enter and test verifies successful review metadata plus transcript. |
| Existing post-submit hard-session-limit path | Retained; still expects exit code 25. |
| Required hard-limit phrases | Covered for the listed session/weekly/usage/rate examples, with one wording gap below. |

3. Findings

- P1 — IN_PLAN — [claude_interactive_review.py:39](/Users/anichols/code/ai-configs/skills/claude-code-review/scripts/claude_interactive_review.py:39), [test_claude_interactive_review.py:237](/Users/anichols/code/ai-configs/skills/claude-code-review/tests/test_claude_interactive_review.py:237): `HARD_LIMIT_RE` does not match `You've hit your weekly rate limit`. The `hit` branch permits `weekly` and `rate` independently, but not the common combined `weekly rate limit` form. The launcher would not return required code 25 for that hard-exhaustion wording. Add `weekly rate` coverage and recognition.

4. Final verdict

VERDICT: FIX_IN_SCOPE_FINDINGS