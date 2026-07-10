---
name: codex-coding-workflow
description: "Codex-based workflow for substantive repo work under ~/code/. Use this when Aaron asks for Codex or when the compatibility-only OpenCode workflow is unavailable, unprovisioned, or unsuitable."
version: 0.1.1
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [codex, coding-workflow, aaron, github, pull-request]
    related_skills: [codex, claude-code, pi-coding-workflow, github-pr-workflow]
---

# Codex Coding Workflow

Use this when Aaron explicitly asks for Codex, when the compatibility-only OpenCode workflow is unavailable or not independently provisioned, or when comparing implementations. Before routing to `hermes-opencode-linear-build`, verify its command and both helper scripts exist under `~/.config/opencode`; otherwise use this maintained Codex workflow or the maintained Pi workflow.

It preserves the proven Pi workflow discipline, but drives implementation through OpenAI Codex CLI instead of Pi.

## Non-negotiable rule

For repositories under `~/code/`, Hermes must not directly edit repo files with `patch`, `write_file`, ad-hoc shell rewriting, or equivalent tools. Codex must be the implementer for all repo edits — code, tests, scripts, docs, configs, and release automation — unless Aaron directly authorizes bypassing Codex for that specific edit. Hermes may inspect, plan, verify, run small focused validation commands, commit/push, operate GitHub, and report results, but repo mutations go through Codex.

## Preconditions

- Load the `codex` skill too, and use its current CLI guidance.
- Load the `claude-code` skill too. In this workflow, Codex is the primary implementer. Plans must receive both Codex and Claude Code read-only reviews before implementation, and both must agree the plan is execution-ready. Code changes must also receive both Codex and Claude Code reviews before PR.
- Run from a git repository under `~/code/` unless Aaron gives another path.
- Read repo instructions first: `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, planning docs, `TESTING.md`, product-intent docs, PR/commit guidance.
- Prefer repo conventions over this generic workflow when they conflict.
- Codex CLI is available as `codex`; current verified CLI supports `codex exec`, `-C/--cd`, `-s/--sandbox`, `--output-last-message`, and `codex review --base/--uncommitted`.

## Core principles

- Preserve stage separation: planning, review, integration, plan commit, implementation, validation, PM review, code review, PR, post-PR follow-up.
- Do not let planning mutate production code. Plan-only runs may write/update the canonical plan file, but should not change app/library/source files.
- Use `codex exec` for non-interactive work. For repo-local autonomous edits prefer `-s workspace-write`; avoid `danger-full-access` or `--dangerously-bypass-approvals-and-sandbox` unless Aaron explicitly accepts the risk.
- Use Codex and Claude Code as fresh, independent read-only plan reviewers. Before implementation, both must explicitly agree the latest plan is execution-ready. Use the installed `claude-code-review` private-tmux launcher for Claude review gates; do not let review passes edit files.
- Hermes remains responsible for verifying filesystem/git/PR state. Do not trust Codex's or Claude's claims without checking files, git status, test output, and PR/check state.
- Run verification as small, focused commands with one clear purpose each. Do not bundle unrelated validation, git inspection, release checks, and quoting-heavy shell snippets into a giant combined command; if a command hits quoting trouble or times out, split it into simpler probes.
- Before PR, the repo's full validation bar must pass; targeted tests alone are not enough.
- Before PR, review the result like a product manager and like a code reviewer.

## Canonical stages

### 0. Gather repo context

Inspect the repo for guidance and determine:
- branch base and naming convention
- canonical plan location/format
- validation commands and smoke suites
- product intent / acceptance criteria source
- PR template and evidence requirements

### 1. Create the branch before planning

Create the work branch first so the reviewed plan and implementation share one auditable branch.

```bash
git switch -c <branch-name>
```

### 2. Plan-only Codex run

Ask Codex to read the task and repo guidance, then create/update only the plan artifact.

```bash
codex exec -C <repo> -s workspace-write '
Read the task and repo guidance, then create or update the canonical execution plan at <plan path>.
Do not change production code, tests, configs, or docs outside the plan artifact in this phase.
Include repo-specific validation steps, product-intent linkage, assumptions, risks, and acceptance criteria.
'
```

Verify the plan exists and review `git diff` to ensure only plan files changed.

### 3. Review the plan with both Codex and Claude Code in fresh contexts

Run both review passes read-only. This is a hard gate: **both Codex and Claude Code must explicitly return `EXECUTION_READY` before implementation**. If either returns `NOT_READY`, integrate feedback and rerun both reviews on the updated plan.

Codex plan review:

```bash
codex exec -C <repo> -s read-only --output-last-message /tmp/codex-plan-review.md '
Review <plan path> against the task, repo guidance, product intent, acceptance criteria, edge cases, sequencing, validation requirements, evidence requirements, and PR/rebase requirements.
Do not edit files.
Return one of two verdicts exactly: EXECUTION_READY or NOT_READY.
Use EXECUTION_READY only if the plan is specific, scoped, testable, sequenced correctly, and safe to implement without unresolved product/technical ambiguity.
If NOT_READY, list blockers, gaps, ambiguities, missing validation/evidence, and concrete plan changes required.
'
```

Claude Code plan review:

```bash
python3 ~/.agents/skills/claude-code-review/scripts/claude_interactive_review.py \
  --cwd <repo> \
  --prompt-file <claude-plan-review-input-file> \
  --output /tmp/claude-plan-review.md \
  --review-name claude-plan-review \
  --timeout-seconds 3600
```
Hermes must inspect both artifacts and verify both reviewers agree before proceeding.

### 4. Integrate plan feedback

```bash
codex exec -C <repo> -s workspace-write '
Integrate the Codex and Claude Code plan review feedback from /tmp/codex-plan-review.md and /tmp/claude-plan-review.md into <plan path>.
Do not make implementation changes. Keep the plan execution-ready and aligned with repo conventions.
'
```

Verify the plan diff again. If either reviewer returned `NOT_READY` or material blockers, rerun both plan reviews after integration and do not proceed until both return `EXECUTION_READY`.

### 5. Commit the reviewed plan

Commit the reviewed/integrated plan before implementation.

```bash
git status --short
git add <plan path>
git commit -m "plan: <concise task>"
```

Follow repo commit conventions when present.

### 6. Plan-stage PM review

Run a fresh read-only Codex pass that pressure-tests the plan as product work, not just code work.

```bash
codex exec -C <repo> -s read-only --output-last-message /tmp/codex-pm-plan.md '
Perform a plan-stage PM review of <plan path>. Judge functional outcome, product intent, assumptions, edge cases, risks, and tradeoffs. Return required plan changes, if any. Do not edit files.
'
```

If it finds material gaps, integrate and commit the updated plan, then rerun both Codex and Claude Code plan reviews if the PM feedback changed scope, sequencing, validation, acceptance criteria, or evidence requirements. Do not implement until both reviewers still agree the latest plan is `EXECUTION_READY`.

### 7. Execute the plan with Codex

For short tasks, run foreground only after Codex and Claude Code plan reviews both returned `EXECUTION_READY` and the plan-stage PM review is acceptable. For longer tasks, run background with `notify_on_complete=true` and monitor with `process`.

```bash
codex exec -C <repo> -s workspace-write '
Execute the approved plan in <plan path>. Continue until the plan is complete unless you hit a real blocker.
Follow repo conventions. Run targeted validation as you work. Do not open a PR.
'
```

If Codex stops early, inspect state and send a continuation prompt rather than assuming completion.

### 8. Validate fully

Run the repo's documented validation bar from `TESTING.md`, `AGENTS.md`, package scripts, and smoke-test docs. Fix failures before PR. If the repo defines smoke tests, they are required pre-PR.

For user-visible UI or desktop/macOS changes, capture visual evidence before PR: screenshots at minimum and video when practical. When the OpenCode workflow skill is available, its `scripts/pr_evidence.py` helper can package evidence under `docs/pr-evidence/<slug>/` and generate PR-ready Markdown. If desktop video capture is blocked by macOS TCC/Screen Recording permissions or missing ffmpeg, document that limitation and include still images rather than skipping visual validation entirely.

### 9. Implementation-stage PM review

```bash
codex exec -C <repo> -s read-only --output-last-message /tmp/codex-pm-implementation.md '
Perform an implementation-stage PM review. Compare the current branch against <plan path> and product intent. Identify functional gaps, missed edge cases, UX regressions, or acceptance-criteria failures. Do not edit files.
'
```

If this review requires changes, run a Codex implementation follow-up, then rerun impacted validation. Cap repeated PM-review/re-execution loops at 3 before pausing for Aaron.

### 10. Full code reviews before PR

Always run both Claude Code and Codex code reviews for changes before PR. Keep both review passes read-only and capture their findings separately so disagreements or complementary findings are visible.

Claude Code review:

```bash
python3 ~/.agents/skills/claude-code-review/scripts/claude_interactive_review.py \
  --cwd <repo> \
  --prompt-file <claude-code-review-input-file> \
  --output /tmp/claude-code-review.md \
  --review-name claude-code-review \
  --timeout-seconds 3600
```
Codex review:

```bash
codex review --base <base-branch> > /tmp/codex-code-review.md
```

If `codex review` is insufficient for repo-specific context, use a read-only `codex exec` review prompt instead:

```bash
codex exec -C <repo> -s read-only --output-last-message /tmp/codex-code-review.md '
Review the current branch diff against <base-branch> for correctness, security, data-loss risk, concurrency/race issues, missing tests, maintainability, and repo-convention violations.
Return prioritized findings with file/line references where possible. Do not edit files.
'
```

For GitHub PR-number review, Claude can also be used with `--from-pr <number>` when appropriate.

Treat findings from both reviewers as real work. Fix issues, then rerun impacted validation. If one reviewer is unavailable, note the blocker explicitly and do not silently substitute a single-review workflow.

### 11. Open ready-for-review PR

Only after:
- the plan is complete
- Codex and Claude Code both returned `EXECUTION_READY` for the latest material plan version
- full validation and smoke tests pass
- PM/product review is acceptable
- full Claude Code and Codex code review findings are addressed
- visual/user-flow evidence is captured if relevant
- the branch has been rebased onto the latest intended target branch and conflicts are resolved
- the tree is clean except intentional committed changes

Before opening the PR:

```bash
git fetch origin <base-branch>
git rebase origin/<base-branch>
git status --short
git merge-base --is-ancestor origin/<base-branch> HEAD
```

If rebase creates conflicts, resolve through Codex, rerun impacted validation/reviews, refresh visual evidence if behavior changed, and only then open the PR.

Create a ready PR following repo template. Do not open as draft unless Aaron asks.

### 12. Post-PR follow-up

After PR creation:
- wait for GitHub checks at least once
- inspect comments/reviews/failing checks
- address at least one pass of feedback
- confirm mergeability
- if conflicts exist, rebase onto the intended base, resolve, push, and re-check

The workflow is not complete at "PR opened"; it completes after one feedback/check cycle and mergeability confirmation.

## Minimal prompt snippets

Plan-only:
```text
Create/update only <plan path>. Do not change production code in this phase.
```

Continuation:
```text
Continue executing the approved plan from the current repo state. Finish remaining work unless you hit a real blocker.
```

Fix review findings:
```text
Address the PM/code review findings, keep scope aligned with <plan path>, and rerun the impacted validation commands.
```

## Open refinement items

This is an initial Codex adaptation of the Pi workflow. Refine after real runs, especially around:
- whether Aaron wants visible tmux panes for Codex like he did for Pi
- whether to build a `codex_workflow_ctl.py` controller analogous to `pi_workflow_ctl.py`
- preferred model/profile flags for Codex and Claude Code on Aaron's machines
- repo-specific automation for Linear state sync and PR evidence capture
