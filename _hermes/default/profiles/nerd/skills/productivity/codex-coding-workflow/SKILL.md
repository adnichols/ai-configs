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
- In this workflow, Codex is the primary implementer. Plans and code changes must receive exactly one read-only review from the active harness's configured `reviewer` subagent before advancing. For OpenCode this is `cliproxyapi/gpt-5.6-terra` at medium reasoning effort; do not add a separate Codex or Claude Code review leg.
- Run from a git repository under `~/code/` unless Aaron gives another path.
- Read repo instructions first: `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, planning docs, `TESTING.md`, product-intent docs, PR/commit guidance.
- Prefer repo conventions over this generic workflow when they conflict.
- Codex CLI is available as `codex`; current verified CLI supports `codex exec`, `-C/--cd`, `-s/--sandbox`, `--output-last-message`, and `codex review --base/--uncommitted`.

## Core principles

- Preserve stage separation: planning, review, integration, plan commit, implementation, validation, PM review, code review, PR, post-PR follow-up.
- Do not let planning mutate production code. Plan-only runs may write/update the canonical plan file, but should not change app/library/source files.
- Use `codex exec` for non-interactive work. For repo-local autonomous edits prefer `-s workspace-write`; avoid `danger-full-access` or `--dangerously-bypass-approvals-and-sandbox` unless Aaron explicitly accepts the risk.
- Use exactly one fresh, read-only active-harness `reviewer` subagent for every plan or code-review gate. Do not let review passes edit files, run verification, or start a separate Codex or Claude Code review process.
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

### 3. Review the plan with the active-harness reviewer subagent

Run exactly one configured active-harness `reviewer` subagent pass. This is a hard gate: the reviewer must explicitly return `EXECUTION_READY` before implementation. For OpenCode, invoke the configured `reviewer` subagent (`cliproxyapi/gpt-5.6-terra`, medium effort) with a read-only plan-review packet and write its result to `/tmp/plan-review.md`. Do not start a separate Codex or Claude Code review process.

The packet must ask the reviewer to inspect `<plan path>` against the task, repository guidance, product intent, acceptance criteria, edge cases, sequencing, validation requirements, evidence requirements, and PR/rebase requirements. It must prohibit edits and executable verification. The reviewer returns exactly `EXECUTION_READY` or `NOT_READY`; `NOT_READY` includes concrete blockers, gaps, ambiguities, missing validation/evidence, and required plan changes.

Hermes must inspect the one returned artifact before proceeding. If the reviewer returns `NOT_READY`, integrate the feedback and rerun the same reviewer only on the updated plan.

### 4. Integrate plan feedback

```bash
codex exec -C <repo> -s workspace-write '
Integrate the active-harness reviewer feedback from /tmp/plan-review.md into <plan path>.
Do not make implementation changes. Keep the plan execution-ready and aligned with repo conventions.
'
```

Verify the plan diff again. If the reviewer returned `NOT_READY` or material blockers, rerun the same plan-review pass after integration and do not proceed until it returns `EXECUTION_READY`.

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

If it finds material gaps, integrate and commit the updated plan, then rerun the active-harness plan review if the PM feedback changed scope, sequencing, validation, acceptance criteria, or evidence requirements. Do not implement until the reviewer still finds the latest plan `EXECUTION_READY`.

### 7. Execute the plan with Codex

For short tasks, run foreground only after the active-harness plan reviewer returned `EXECUTION_READY` and the plan-stage PM review is acceptable. For longer tasks, run background with `notify_on_complete=true` and monitor with `process`.

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

Run exactly one active-harness `reviewer` subagent code review before PR. Keep it read-only and capture its findings. Do not add a separate Codex or Claude Code review leg.

Invoke the configured active-harness `reviewer` subagent with a read-only packet covering the current branch diff against `<base-branch>`, the plan, the scope contract, and verification evidence. For OpenCode, use `cliproxyapi/gpt-5.6-terra` at medium effort. Ask it to report prioritized findings with file/line references where possible, and prohibit edits and executable verification. Save the result as `/tmp/code-review.md`.

Treat findings from the reviewer as real work. Fix in-scope issues, rerun impacted validation, and run one targeted rereview limited to those findings and resulting edits. If the reviewer is unavailable, note the blocking infrastructure failure; do not silently substitute an external Codex or Claude Code review.

### 11. Open ready-for-review PR

Only after:
- the plan is complete
- the active-harness reviewer subagent returned `EXECUTION_READY` for the latest material plan version
- full validation and smoke tests pass
- PM/product review is acceptable
- active-harness reviewer-subagent code-review findings are addressed
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
