**Findings**

1. **P2 / REGRESSION_FROM_THIS_DIFF**: Playwright fixer concurrency is still initialized to `3` despite the new guidance saying max `2`.
   Evidence: [test:run-playwright.md](_pi/prompts/test:run-playwright.md:48) and [test:run-playwright:all.md](_pi/prompts/test:run-playwright:all.md:53) set `MAX_CONCURRENT_FIXERS = 3`, while both files now document max `2` in defaults and guardrails. Agents following the process block can still dispatch three concurrent fixers, undermining the split supervision/fix guidance.

**Prior Finding**

Resolved. [run-plan.md](_pi/prompts/run-plan.md:1) and [dev:run.md](_pi/prompts/dev:run.md:1) no longer contain frontmatter `model:` pins.

VERDICT: FIX_IN_SCOPE_FINDINGS
