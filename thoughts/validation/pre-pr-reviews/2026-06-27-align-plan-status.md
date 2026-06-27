# Pre-PR Implementation Review: align-plan-status

Date: 2026-06-27
Plan: `thoughts/plans/align-plan-status.html`
Primary repo: `/Users/anichols/.herdr/worktrees/ai-configs/align-plan-status`
External repo: `/Users/anichols/.herdr/worktrees/plan-reviewer/align-plan-status-instructions`

## Scope

Two coordinated PRs are required by the plan:

- ai-configs guidance/prompt changes:
  - `skills/run-plan/SKILL.md`
  - `skills/plan-reviewer-build/SKILL.md`
  - `_pi/prompts/cmd:create-pr.md`
  - `thoughts/plans/align-plan-status.html`
- plan-reviewer service instruction contract changes:
  - `src/registrationInstructions.ts`
  - `src/__tests__/contracts.test.ts`

## Verification

- Primary ai-configs grep checks passed for:
  - `Plan-reviewer status alignment`
  - `ltui issues view`
  - `columns list --json`
  - `column set ... in_progress`
  - `source sync`
  - Build Plan bridge parity
  - Linear-backed PR title guidance
- plan-reviewer targeted gate after review fix: `bun run build && node --test dist/__tests__/contracts.test.js` passed.
- plan-reviewer full gate after review fix: `bun run test` passed, 144 tests, 0 failures.
- plan-reviewer card status: active / in_progress.
- plan-reviewer source progress synced at 5/5 after P5 completion.
- Primary ai-configs PR: https://github.com/adnichols/ai-configs/pull/26
- Companion plan-reviewer PR: https://github.com/Nodaste-Lab/plan-reviewer/pull/67

## Review cycle 1

Runtime scoped implementation reviews:

| Reviewer | Verdict | Findings |
| --- | --- | --- |
| GPT quality-reviewer | `FIX_IN_SCOPE_FINDINGS` | New plan-reviewer status commands omitted the registration service URL. |
| GLM quality-reviewer-glm | `FIX_IN_SCOPE_FINDINGS` | Same service-URL omission. |

### Triage

| Finding | Reviewer | Severity | Scope | Decision | Evidence |
| --- | --- | --- | --- | --- | --- |
| Status-alignment commands omitted `--url <registration service URL>` | GPT + GLM | P2 | IN_PLAN / REGRESSION_FROM_THIS_DIFF | Fixed | P2 explicitly required command templates to use the registration service URL pattern; without it commands could hit the wrong plan-review service. |

### Fix

Updated `src/registrationInstructions.ts` so the emitted lifecycle, columns list, and column set instructions include either:

- `--url <registration service URL>`, or
- the concrete service URL for API-rendered instructions.

Updated `src/__tests__/contracts.test.ts` to assert both placeholder and concrete service URL behavior.

## Review cycle 2

Runtime scoped follow-up reviews:

| Reviewer | Verdict | Findings |
| --- | --- | --- |
| GPT quality-reviewer | `PASS_SCOPED` | None |
| GLM quality-reviewer-glm | `PASS_SCOPED` | None |

## Pre-PR gate

| Reviewer | Verdict | Findings |
| --- | --- | --- |
| GPT quality-reviewer | `CLEAN_FOR_PR` | None |
| GLM quality-reviewer-glm | `CLEAN_FOR_PR` | None |

No unresolved in-scope P1/P2/P3 findings remain.

## PR feedback follow-up

Codex reviewed the first primary PR commit and reported two in-scope findings:

| Finding | Severity | Scope | Resolution |
| --- | --- | --- | --- |
| `skills/run-plan/SKILL.md` status-alignment commands omitted `--url <registration service URL>` | P1 | IN_PLAN | Added service URL placeholder to lifecycle, columns list, and column set commands. |
| `_pi/prompts/cmd:create-pr.md` reset `TITLE` before `gh pr create`, undermining Linear-aware title resolution | P2 | IN_PLAN | Changed the create block to preserve a precomputed Linear-aware `TITLE` and only fall back to the commit subject when `TITLE` is unset. |
| `_pi/prompts/cmd:create-pr.md` also reset `TITLE` during evidence collection, causing the later fallback to preserve the commit subject | P2 | IN_PLAN | Changed the prompt to set `TITLE` from the verified Linear issue title for Linear-backed work and fail closed if that title is missing. |

Follow-up verification:

- `rg` checks confirmed service-URL-qualified status commands and explicit Linear-backed `TITLE` assignment/fail-closed checks in both PR prompt command blocks.
- `git diff --check` passed.

## Remaining follow-ups

None.

## Final gate result

`OPEN_PR_READY`
