# Run Plan Command Surface Inventory

Date: 2026-06-26
Plan: `thoughts/plans/run-plan-command-surface-cleanup.html`

## Scope

This inventory records command and skill usage evidence for the `scoped-plan-run` to `run-plan` rename. It is a recommendation manifest, not approval to delete detritus surfaces. The only removal approved by the current plan is the old installed `scoped-plan-run` surface as part of the rename/deprecated-skill cleanup.

## Audit method

- Source: Pi session JSONL files newer than 2026-05-25.
- Sample size from the planning audit: 445 session files.
- Counting rule: strict filtered pass over known prompt-template, skill, and built-in command names.
- False-positive exclusions: path fragments and API route fragments such as `/repos`, `/issues`, `/usr`, and file paths.

## Recent usage summary

| Command / skill | User count | Total mentions | Sessions | Disposition |
| --- | ---: | ---: | ---: | --- |
| `/skill:pre-pr-implementation-review` | 76 | 77 | 17 | Keep. Regularly used pre-PR review gate. |
| `/review:plan` | 5 | 23 | 18 | Keep. Active plan-review workflow surface. |
| `/cmd:execute-plan` | 4 | 7 | 4 | Keep, but update target naming to `run-plan` / `dev:run`. |
| `/review:change-integrate` | 6 | 6 | 3 | Keep. Used for review-comment cleanup. |
| `/review:plan-adversarial` | 4 | 4 | 2 | Keep. Low-volume but deliberate plan gate. |
| `/review:change-claude-code` | 2 | 7 | 4 | Keep as explicit opt-in review surface. |
| `/skill:scoped-plan-run` | 1 | 9 | 4 | Renamed to `/skill:run-plan`; no alias retained. |
| `/skill:adn-dev-wf` | 0 | 2 | 1 | Keep for now as a broader reviewed-plan workflow. Reassess after `run-plan` usage settles. |
| `/dev:reviewed-html-plan` | 0 | 2 | 2 | Keep. Browser-reviewed plan workflow surface. |
| `/scoped-models` | 1 | 1 | 1 | Built-in Pi command; collision source, not repo-owned. |

## High-confidence archive or rename candidates

These are recommendations only unless an explicit future approval names the exact item and action.

| Candidate | Evidence | Recommended action | Reasoning |
| --- | --- | --- | --- |
| `_pi/prompts/functional-review.md` plus mirrored consumer copies | 0 strict recent direct uses. | Archive after approval. | Older spec/openspec systemic review prompt; overlaps current plan/PM/product review workflows. |
| `_pi/prompts/lean-functional-review.md` plus mirrored consumer copies | 0 strict recent direct uses. | Archive after approval. | Older increment review prompt; overlaps product-principles and plan-review readiness checks. |
| `_pi/prompts/cmd:local-review.md` | 0 strict recent direct uses. | Archive after approval. | Manual isolated review worktrees are superseded by dedicated review skills/agents and explicit PR review commands. |
| `_pi/prompts/dev:reflect.md` | 0 strict recent direct uses. | Archive after approval. | Phase reflection is no longer in the current reviewed-plan golden path. |
| `skills/ccore_DONOTUSE/` | 0 strict recent skill invocations and directory name says `DONOTUSE` while frontmatter says `name: ccore`. | Do not leave as-is. Rename to `skills/ccore/` if wanted, or remove from install matrix if obsolete, after approval. | Current naming is confusing and undermines discoverability. |
| `skills/scoped-plan-run/` | Collision with built-in `/scoped-models`; one direct user invocation in audit window. | Completed: renamed to `skills/run-plan/`; old name added to deprecated installer cleanup. | Primary approved cleanup for this plan. |

## Medium-confidence candidates requiring review

| Candidate | Evidence | Recommended action | Review question |
| --- | --- | --- | --- |
| `_pi/prompts/cmd:review-pr-comments.md` | 0 strict recent direct uses. | Review before archiving. | Is this superseded by `run-plan` post-PR monitoring, or still useful as an emergency command? |
| `_pi/prompts/cmd:feeling-lucky-pr.md` and `_pi/prompts/cmd:feeling-lucky-pr-os.md` | 0 strict recent direct uses. | Review before archiving. | Are these experimental one-shot PR flows still wanted now that reviewed plans and `run-plan` exist? |
| `_pi/prompts/dev:plan-from-prd.md`, `_pi/prompts/prd:clarify-round.md`, `_pi/prompts/review:prd.md` | 0 strict recent direct uses. | Review as a PRD bundle. | Is the PRD flow still active, or has reviewed HTML planning replaced it? |
| `_pi/prompts/cmd:send-plan-to-doct.md` | 0 strict recent direct uses. | Review before archiving. | Do plan-reviewer/browser plans now replace Doct plan publishing? |
| `_pi/prompts/doc:fetch.md` and `_pi/prompts/doc:update.md` | 0 strict recent direct uses. | Review before archiving. | Are these still useful outside this repo's normal coding workflow? |

## Zero-use but keep for now

| Surface | Reason to keep |
| --- | --- |
| `/dev:plan`, `/dev:run`, `/dev:reviewed-html-plan` | Core plan lifecycle commands; usage may be assistant-suggested or extension-dispatched rather than user-typed. |
| `plan-reviewer-build`, `plan-reviewer-execution-ready` | Browser action bridge skills are invoked by plan-reviewer comments, not necessarily typed by users. |
| `review-change*` provider-specific prompts | Explicit opt-in review surfaces; low frequency is expected. |
| Domain commands such as `macos:*`, `test:run-playwright*`, `qa:run` | Specialized commands should not be archived solely because this month did not include that domain. |

## Recommendation-only policy

- Do not delete, move, or rename any low/no-use command or skill from this inventory unless a later user message or plan-review browser comment explicitly names the exact item and action.
- Approved archive destinations must be outside active install roots such as `_pi/prompts`, `skills`, `_codex/prompts`, `_claude/commands`, `_opencode/commands`, and `_omp/commands`.
- If archive approval is later granted, prefer `thoughts/archive/pi-command-detritus/<date>/` for historical copies or `git rm` for explicitly approved deletion.

## Current approved rename

- New canonical full lifecycle command: `/run-plan <plan>`.
- Explicit Pi skill invocation: `/skill:run-plan <plan>`; it is equivalent to `/run-plan` for the full lifecycle runner, while `/run-plan` is the ergonomic cross-surface wrapper name.
- Removed installed alias: `/skill:scoped-plan-run` after installer cleanup.
- Stable browser bridge: `plan-reviewer-build`, which delegates to `run-plan`.
- Direct execution-only path remains: `/dev:run <plan>`.

## Archive follow-up status

- No detritus prompts, mirrored commands, or low/no-use skills were archived or deleted in this run.
- The only approved removal behavior is installer cleanup of stale installed `scoped-plan-run` copies after the rename.
- `functional-review`, `lean-functional-review`, `cmd:local-review`, `dev:reflect`, `cmd:review-pr-comments`, `cmd:feeling-lucky-pr*`, PRD flow prompts, Doct plan publishing, doc fetch/update prompts, and `ccore_DONOTUSE` remain recommendation-only follow-ups pending explicit approval.
- Future cleanup should first decide whether `/skill:adn-dev-wf` remains a broader reviewed-plan workflow or becomes a later archive candidate after `run-plan` usage is established.
