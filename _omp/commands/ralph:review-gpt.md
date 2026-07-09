---
description: Iterative code review loop (GPT-5.6 Sol) — run /review, apply quick fixes, stop when no straightforward fixes remain
argument-hint: "[BASE_REF]"
agent: build
subtask: true
model: openai-codex/gpt-5.6-sol
reasoningEffort: medium
---

# Review Loop (Auto-Fix)

Run Oh My Pi's `/review` command in a loop on GPT-5.6 Sol medium reasoning. Apply quick / straightforward fixes surfaced by the review, then re-run. Stop when there are no more quick fixes to apply (or after 3 iterations) and report remaining issues.

## Inputs

`$ARGUMENTS` may be:

- `BASE_REF` (optional) - e.g. `origin/main`, `origin/develop`

If omitted, default to `origin/develop`.

## Process

### 0) Autopilot Rules

- Execute continuously; do not pause between iterations.
- Do not stop after a status update (e.g., "reviewing" or "fixing issues").
- Every response must either (a) take the next concrete action by invoking a tool (read/search/edit/run), or (b) ask for user input due to an unresolvable decision. Narration alone is not an action.
- Use `question` only when a decision between viable options materially changes behavior and cannot be resolved from the repo.

### 1) Resolve Review Base

Resolve `base_ref`:

1. If `$ARGUMENTS` is non-empty, treat it as `base_ref`.
2. Otherwise use `origin/develop`.

### 2) Establish Context (Git)

Collect the state that the reviewer should consider:

```bash
git status
git diff --stat "${base_ref}...HEAD"
git diff "${base_ref}...HEAD"
```

If there are uncommitted changes, they are in-scope for review.

### 3) Review / Fix Loop

Repeat until termination (max 3 iterations):

1. Run Oh My Pi's `/review` on the current working tree and diff against `base_ref`.
2. From the review output, split issues into:
   - **Quick / straightforward fixes**: small, local, high-confidence changes (formatting, obvious bug fix, missing null-check, incorrect import, broken command snippet, etc.).
   - **Not quick**: anything that requires broader refactor, unclear intent, architectural redesign, product decision, or investigation beyond a short tight loop.
3. If there are one or more quick fixes, apply them all:
   - Make the smallest change that resolves the issue.
   - Do not introduce new features or refactors unless required to fix the issue.
   - If a fix requires a choice that materially changes behavior and cannot be resolved from the repo, stop and ask exactly one targeted `question`.
4. If there are zero quick fixes to apply, STOP and report remaining issues (including why they are not quick).
5. If you have completed 3 iterations total, STOP and report remaining issues (even if more quick fixes may exist).
6. Otherwise loop back to step 1.

### 4) Completion

When the loop terminates:

- Provide a brief summary of fixes made.
- List any remaining issues that were not quick/straightforward.
