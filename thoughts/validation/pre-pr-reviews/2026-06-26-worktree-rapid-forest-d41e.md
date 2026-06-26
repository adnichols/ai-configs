# Pre-PR Implementation Review — run-plan command surface cleanup

Date: 2026-06-26
Branch: `worktree/rapid-forest-d41e`
Plan: `thoughts/plans/run-plan-command-surface-cleanup.html`
Base/comparison: initial cycles reviewed the then-uncommitted working-tree diff against `origin/main`; after commit and rebase, post-rebase cycles review `origin/main..HEAD` / `origin/main...HEAD` plus the current uncommitted validation-artifact update. No staged changes at review start.

## Scope summary

Rename the `scoped-plan-run` shared skill/surface to `run-plan`, add ergonomic `/run-plan` wrappers, preserve `plan-reviewer-build` as the browser Build Plan bridge, align dispatch/docs, record archive candidates without deleting unrelated detritus, and verify installer cleanup plus plan-reviewer smoke behavior.

## Changed files summary

See `/tmp/run-plan-pre-pr-changed-files.txt` for the exact launch-time file list. Major groups:

- Runner rename: `skills/run-plan/**` added, `skills/scoped-plan-run/**` removed.
- Installer/matrix/tests: `skills/install-matrix.json`, `install.sh`, `test_install_shared_skills.sh`.
- Dispatch/wrappers: `_pi/prompts/run-plan.md`, `_codex/prompts/run-plan.md`, `_claude/commands/run-plan.md`, `_opencode/commands/run-plan.md`, `_omp/commands/run-plan.md`, `cmd:execute-plan` mirrors, Pi/OMP plan-mode extensions.
- Bridge/docs: `skills/plan-reviewer-build/SKILL.md`, `skills/codex-full-build/SKILL.md`, `skills/pre-pr-implementation-review/SKILL.md`, README/AGENTS/catalog docs.
- Planning artifacts: `thoughts/plans/run-plan-command-surface-cleanup.html`, `thoughts/research/run-plan-command-surface-inventory.md`.

## Verification before pre-PR gate

- `python3 -m json.tool skills/install-matrix.json` — passed.
- Python assertion: `run-plan.allowedConsumers` includes `codex`, `claude`, `opencode`, and `pi` — passed.
- `bash test_install_shared_skills.sh` — 13 passed, 0 failed.
- Active-surface stale grep for `scoped-plan-run|$scoped-plan-run` excluding `thoughts/plans/**` — passed.
- Dispatch/docs grep for `/run-plan`, `/skill:run-plan`, `/dev:run`, and `/cmd:execute-plan` — passed.
- Plan-reviewer Build Plan smoke: `buildPlanSkillName` is `plan-reviewer-build`; queued payload contained `plan-reviewer-build` and `thoughts/plans/run-plan-command-surface-cleanup.html`; temporary smoke comment was acked and resolved.
- Scoped quality rereviews after parity fixes: GPT and GLM both returned `PASS_NO_ISSUES`.

## Review cycle 1

| Reviewer | Verdict | Notes |
| --- | --- | --- |
| GPT-5.5 quality-reviewer | `CLEAN_FOR_PR` | Agent `a3bbaed8-56b3-4c6`; no findings. Reran `git diff --check` and `bash test_install_shared_skills.sh` (13 passed, 0 failed). |
| GLM-5 quality-reviewer-glm | `FINDINGS_TO_RESOLVE` | Agent `495c69e1-dbf4-4af`; one blocking P3 against this validation artifact because it still contained pending placeholders. |

## Triage table

| Finding | Reviewer | Severity | Scope | Decision | Evidence |
| --- | --- | --- | --- | --- | --- |
| Validation artifact still showed placeholder review status after reviews completed. | GLM-5 quality-reviewer-glm | P3 | REGRESSION_FROM_THIS_DIFF | Fixed by replacing placeholders with actual cycle-1 verdicts, triage, and fix notes. | Artifact lines for cycle 1, triage, fixes, and final gate result still contained placeholder text, making readiness evidence contradictory. |

## Fixes applied during pre-PR gate

- Updated this artifact to replace placeholder cycle-1 review status with the actual GPT clean verdict and GLM P3 finding.
- Recorded the GLM finding in the triage table with its fix disposition.

## Review cycle 2

| Reviewer | Verdict | Notes |
| --- | --- | --- |
| GPT-5.5 quality-reviewer | `CLEAN_FOR_PR` | Agent `c592415c-b5a4-4fb`; no unresolved in-scope P1/P2/P3 findings. Reran `json.tool`, allowedConsumers check, `git diff --check`, stale active-reference grep, and `bash test_install_shared_skills.sh` (13 passed, 0 failed). |
| GLM-5 quality-reviewer-glm | `CLEAN_FOR_PR` | Agent `da7ca116-3f63-477`; no unresolved in-scope P1/P2/P3 findings. Reran `git diff --check`, `python3 -m json.tool skills/install-matrix.json`, run-plan matrix assertions, and `bash test_install_shared_skills.sh` (13 passed, 0 failed). |

## Post-rebase review cycle 3

After cycle 2 passed, the branch was rebased onto current `origin/main`. Conflicts in `AGENTS.md`, `_pi/README.md`, `skills/install-matrix.json`, and `skills/pre-pr-implementation-review/SKILL.md` were resolved by preserving current-main GLM-5 Pi subagent wording while keeping the `run-plan` rename.

| Reviewer | Verdict | Notes |
| --- | --- | --- |
| GPT-5.5 quality-reviewer | `FINDINGS_TO_RESOLVE` | Agent `851f50d0-dc72-418`; one P3 validation evidence finding because the base/comparison line still claimed `git diff origin/main...HEAD` was empty after the rebase. |
| GLM-5 quality-reviewer-glm | `FINDINGS_TO_RESOLVE` | Agent `c683cf7f-adf4-45a`; same P3 validation evidence finding. |

### Cycle-3 triage

| Finding | Reviewer | Severity | Scope | Decision | Evidence |
| --- | --- | --- | --- | --- | --- |
| Base/comparison line falsely said `git diff origin/main...HEAD` was empty after the branch was rebased and committed. | GPT-5.5 and GLM-5 | P3 | REGRESSION_FROM_THIS_DIFF | Fixed by updating the line to describe the initial uncommitted review cycles and the post-rebase `origin/main..HEAD` / `origin/main...HEAD` review scope. | Current branch is one commit ahead of `origin/main` and the PR diff contains the committed implementation files. |

## Post-rebase review cycle 4

| Reviewer | Verdict | Notes |
| --- | --- | --- |
| GPT-5.5 quality-reviewer | `CLEAN_FOR_PR` | Agent `b4e7dd96-0b84-4cc`; no unresolved in-scope P1/P2/P3 findings after the cycle-3 artifact-scope fix. |
| GLM-5 quality-reviewer-glm | `CLEAN_FOR_PR` | Agent `d2427b89-7e00-4cc`; no unresolved in-scope P1/P2/P3 findings after the cycle-3 artifact-scope fix. |

## PR feedback disposition

CodeRabbit completed successfully on PR #25 and left four trivial nitpicks. Disposition: fixed all four with minimal doc/test clarity edits: added a plain-text fence label, aligned Pi execute-plan argument-hint ordering, renamed remaining "scoped runner" narrative phrasing to `run-plan` caller, and documented why the retired skill name is split in tests.

Codex reviewed the pre-nitpick-fix commit and left one P2 on `_pi/prompts/cmd:feeling-lucky-pr.md`: `/run-plan` now owns validation, final review, commit, push, PR creation, and monitoring, but the feeling-lucky PR flow still continued into `/dev:validate`, review, commit/push, and PR creation. Disposition: fixed across the mirrored normal and `-os` feeling-lucky PR prompts for Pi, Claude, OpenCode, and OMP by making `/run-plan ${plan_slug}` the terminal implementation-through-PR step and leaving only Linear linking/reporting after it.

CodeRabbit completed again after the Codex fix and left two trivial nitpicks. Disposition: fixed by making `_pi/README.md` explicitly say `/cmd:execute-plan` is the wrapper that chooses between `/run-plan` and `/dev:run`, and by clarifying in the command-surface inventory that `/skill:run-plan` is the explicit Pi skill invocation equivalent to the ergonomic cross-surface `/run-plan` wrapper.

## Final gate result

- GPT verdict: `CLEAN_FOR_PR`.
- GLM verdict: `CLEAN_FOR_PR`.
- Verification after rebase and before final cycle: `bash -n install.sh`; `bash -n test_install_shared_skills.sh`; `python3 -m json.tool skills/install-matrix.json`; run-plan/pre-pr matrix assertions; narrow conflict-marker grep; active stale-reference grep; `git diff --check`; `bash test_install_shared_skills.sh` with 13 passed, 0 failed.
- PR-feedback verification after CodeRabbit nitpick fixes: `bash -n test_install_shared_skills.sh`; `python3 -m json.tool skills/install-matrix.json`; run-plan/pre-pr matrix assertions; targeted grep for all four fixes; active stale-reference grep; `git diff --check`; `bash test_install_shared_skills.sh` with 13 passed, 0 failed.
- PR-feedback verification after Codex P2 fix: targeted grep proved all eight mirrored feeling-lucky PR prompts now use `### 5) Implement Through PR`, contain `/run-plan ${plan_slug}`, contain `### 6) Link Existing PR to Linear`, and no longer contain standalone `/dev:validate ${plan_slug}`, `/cmd:commit-push`, `/cmd:create-pr ${base_ref}`, `Final Code Review`, or `Commit, Push, PR` steps; `bash -n test_install_shared_skills.sh`; `python3 -m json.tool skills/install-matrix.json`; `git diff --check`; `bash test_install_shared_skills.sh` with 13 passed, 0 failed.
- PR-feedback verification after final CodeRabbit nitpick fixes: targeted grep confirmed `_pi/README.md` now names `/cmd:execute-plan` as the wrapper and the inventory clarifies `/skill:run-plan` as the explicit Pi skill invocation equivalent to `/run-plan`; `python3 -m json.tool skills/install-matrix.json`; `git diff --check`; `bash test_install_shared_skills.sh` with 13 passed, 0 failed.
- Remaining non-blocking out-of-scope follow-ups: none.
- Next step: `OPEN_PR_READY` for the scoped run; continue to push, PR creation, and post-PR monitoring.
