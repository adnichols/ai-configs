---
name: pi-coding-workflow
description: "End-to-end pi development workflow for repo-based software work: branch, create a plan without code changes, review and integrate plan feedback, commit the reviewed plan, execute with pi until the plan is 100% complete, run the repo's full validation bar, do a PM-style product-intent review, and open a ready-for-review PR. Use this whenever the user wants work done through pi in an existing repo, especially when they describe a development process, issue workflow, plan/review/execute loop, or ask you to drive pi faithfully instead of improvising your own flow."
command: pi-workflow
---

# Pi Coding Workflow

Use this skill to drive pi in the user's preferred repo-native development workflow. This skill is the default for substantive pi-based implementation work.

Do **not** assume a specific issue source such as Linear, Sentry, or `thoughts/issues` unless the user explicitly gives one. The source of work can vary. What matters is faithfully following the development loop.

## Core operating principles

- Prefer the repo's existing conventions over generic habits.
- Read repo instructions first (`AGENTS.md`, local planning docs, testing docs, product-intent docs, PR/commit guidance).
- Treat planning, review, execution, validation, and PR creation as separate stages.
- Do not let planning spill into implementation.
- Do not quit pi during the workflow just to get a fresh context. Use `/new` when a fresh context is needed; `/exit` does not quit pi and should not be part of the normal development loop.
- Launch pi in tmux always so Aaron can watch it work live: target the currently attached `main-*` tmux session when available, otherwise another attached tmux session, otherwise create a tmux session rather than falling back to a hidden/background launch. Create a task window named after the work (for example `doct-nod-447`) and prefer a split layout with pi in the left pane and a Hermes CLI controller in the right pane.
- Direct RPC-only/headless pi starts are not acceptable for this workflow. If a tool or shortcut would launch pi without a visible tmux pane, do not use it for initial launch.
- Launch both the pi pane and the Hermes controller pane through Aaron's login shell (for example `zsh -l -c '...'`) so user-scoped env such as dotenvx decryption/auth variables are present. Do not assume tmux inherited those vars.
- If Hermes-side `terminal` git/network operations fail with SSH agent signing errors (for example `sign_and_send_pubkey ... agent refused operation`) while the visible tmux controller pane has a healthy login-shell agent, retry the push/fetch from the tmux login-shell pane rather than treating GitHub access as broken. On Aaron's machine, the pane session can have working agent state that the standalone terminal tool process does not inherit.
- Start pi deterministically. Do **not** rely on pi's remembered last-used interactive model/provider. Constrain default launches to the `openai-codex` family and default to the model/provider in `~/.pi/agent/settings.json` when available, but verify the concrete provider with `pi --list-models <model>` before launch because provider names change. As of 2026-07-04 on Aaron's machine, `gpt-5.5` is offered by provider `openai-codex` (not `openai-codex-4`), so the verified launch form is `pi --provider openai-codex --model gpt-5.5 ...` unless Aaron overrides it.
- If a launch pins only the model but leaves provider implicit, treat that as insufficient. In practice pi may fall back to another configured provider or fail provider resolution; the launcher must make provider selection explicit as well.
- After launching, verify the live pi header in tmux before trusting the worker. The header must show the intended model and an active provider in the expected family (for default coding workflow, `gpt-5.5` on `openai-codex-4` unless Aaron explicitly overrides it). If it does not, stop immediately and repair the launcher instead of continuing the workflow.
- When creating a fresh worktree, do not assume dependencies are already usable even if env files were copied correctly. In pnpm repos especially, missing `node_modules` can surface as misleading failures like `dotenvx: command not found`, `tsx: not found`, or build/test wrappers failing before the real code is exercised. After copying `.env.local` and running `pnpm check:env`, verify/install dependencies (`pnpm install`) before treating validation failures as product or implementation problems.
- Start pi deterministically with explicit provider and model selection. Default to the currently verified coding model/provider pair (currently `--provider openai-codex --model gpt-5.5` on Aaron's machine) instead of inheriting pi's last-used interactive model; allow explicit overrides only through launcher-controlled settings such as `PI_MODEL` / `PI_PROVIDER`.
- On Aaron's machine specifically, if `zsh -l` still lacks `DOTENV_PRIVATE_KEY_LOCAL`, check shell startup files before blaming dotenvx or tmux: the durable fix is to load `~/.env.zshrc` from `~/.zprofile` for login shells and guard the existing `~/.zshrc` source so interactive shells do not double-source it.
- When starting from a gateway session and you need autonomous progression, do not rely on the gateway thread to self-advance. Instead, run a Hermes CLI controller in the right pane and let that controller supervise/advance the pi worker, because plugin message injection is CLI-only.
- If Aaron explicitly asks for "a Hermes observer in the right-hand pane," launch a real interactive `hermes` CLI instance in that tmux pane (or split a fresh right pane if the old controller pane no longer exists). Do **not** substitute a shell loop, wrapper script, or background watcher and call that the right-pane Hermes observer. The visible pane should actually be running Hermes so Aaron can watch and, if needed, intervene directly.
- Critical authority boundary: the right-hand Hermes observer is read-only by default. Unless Aaron explicitly delegates stronger authority, that observer may inspect state, emit progress, and monitor readiness, but it must not commit, push, open/edit/close PRs, or make direct repo code/document changes. Side-effecting workflow actions remain with the main orchestrator.
- After launching the right-pane Hermes instance, immediately inject a grounded observer/controller prompt that tells it the worker pane id, repo path, completed stages, remaining stages, and the requirement not to redo already-completed workflow phases.

- In practice, the pattern that has worked best is a **visible long-lived controller running directly in the right-hand pane** (via `zsh -l`) that watches the left pi pane and sends nudges with tmux `load-buffer`/`paste-buffer`/`send-keys`. That visible pane-local controller succeeded to completion where gateway/plugin-side watchers were less reliable.
- Use `~/.hermes/scripts/pi_workflow_ctl.py` to advance staged workflow commands instead of hand-typing them from memory. It enforces valid stages, rejects removed commands like `/dev:run-direct`, persists per-pane stage state under `~/.hermes/tmp/`, and includes explicit `create-pr` and `post-pr-followup` stages so PR creation plus the first post-PR feedback/check cycle are not left to memory.
- If a persistent tmux supervisor/watcher dies mid-workflow, do not restart the whole loop blindly. First inspect the live worker pane tail, repo git status/log, and any supervisor status/log files under `~/.hermes/tmp/` to identify the last completed stage. Then resume from the next unfinished stage with a stage-specific supervisor/controller so you do not duplicate review/integrate/commit-plan work or send conflicting commands into an already-advanced pi session.
- When supervising from a gateway thread with a local helper script, treat the `pi_workflow_ctl.py` state file under `~/.hermes/tmp/pi-workflow-<pane>.json` as the source of truth for the current stage and compute the next legal stage from that file instead of inferring stage progression purely from pane text.
- For tmux-based auto-advance watchers, detect "still actively working" only from the recent tail (for example the last ~10-15 lines), not the full captured pane history. Old `Thinking...` / `Working...` lines linger in scrollback and can prevent idle detection forever even after pi has returned to a prompt.
- If env-gated verification was previously blocked, explicitly re-check it after any worker relaunch instead of assuming the login shell fixed it. Verify the actual shell state (`DOTENV_PRIVATE_KEY_LOCAL`, dotenvx decryption, Clerk test auth) and rerun the blocked verifier truthfully.
- If the relaunch still does not restore env-gated verification, do not keep retrying the same Playwright/auth gate. Record the exact residual blocker in the plan/progress log, run any remaining meaningful non-env-gated verification, and if those checks hold, commit only the real implementation files so the work is resumable.
- If PM review or validation says there is still a build/test blocker, verify the exact live failure from a fresh command log before steering pi. Do not assume the cited error is still current: subsequent fixes may have changed the failure mode, and transient issues (for example `.next/lock` contention from overlapping Next builds) can look like product blockers. Treat stale diagnoses as hints, not ground truth.
- Do not stop when pi pauses early; inspect the result carefully, compact if needed, and continue until the approved plan is actually complete.
- When pi claims it created a plan file or other artifact, verify the artifact on disk from Hermes before advancing stages. Do not trust pane text like `write <path>` or an inline preview by itself; confirm with `read_file`, `search_files`, or a shell `test -f`/`git status` check. If the artifact is missing, send a direct nudge to materialize it now and verify again before moving on.
- In tmux group sessions, launcher output may name one attached `main-*` session while pane inspection resolves the worker under another grouped sibling session. Treat pane ids (for example `%108`) as the source of truth for watchers and workflow control, and communicate the pane id when reporting status.
- For any destructive stop/cleanup action on Aaron's shared machine, never broad-kill `pi` by name and never kill a whole tmux container first. Resolve the exact worker pane, session, window, and cwd/worktree, then use `python3 ~/.hermes/scripts/tmux_scoped_kill_pi.py --pane <pane> --expected-session <session> --expected-window <window> --expected-cwd <cwd>` in dry-run mode before `--execute`. If the helper finds zero or multiple `pi` processes, stop and do nothing destructive.
- When supervising an already-running pane, prefer the live tmux pane tail over the persisted workflow state file under `~/.hermes/tmp/`. The state file can lag behind the real run (for example still saying `integrate` after pi has already integrated review comments and explicitly printed `Next step: /cmd:execute-plan ...`). If live pane evidence and the saved stage disagree, trust the pane.
- If the canonical controller refuses the correct next stage because of stale stage history, use the same controller with `--force` after grounding the decision from the pane tail. Typical case: review/integrate already completed in the worker, `commit-plan` is now obsolete or blocked by an incidental artifact, and pi is explicitly prompting for execution. In that case, force-send `execute` rather than stopping on the stale transition guard.
- Use lighter validation while iterating if helpful, but do **not** open a PR until the repo's full validation bar passes, including the full smoke test suite whenever the repo defines one.
- Before PR, interrogate the result like a product manager, not just a coder.
- Before PR, run an explicit full code-review pass in addition to PM review, and fix any issues it finds before creating the PR.
- After PR creation, do not stop at "PR opened": wait for GitHub jobs/checks and PR feedback at least once, address what comes back, and confirm the PR is mergeable. If GitHub reports conflicts, rebase onto `develop`, resolve them, push again, and re-check jobs/feedback.

## When to use this skill

Use this skill whenever the user wants you to:
- work through a repo issue or task with pi
- follow their pi development process
- generate a plan and then execute it with pi
- review and integrate plan feedback before implementation
- keep pi moving through a multi-step dev loop until completion
- validate a repo change and open a PR after pi has done the work

If the task is only "launch pi in this repo with this prompt" and the user does **not** want the full staged workflow, the lighter `launch-pi` skill may be enough.

## Canonical workflow

### 0. Gather repo context first

Before launching pi, inspect the repo for:
- `AGENTS.md`
- plan-specific guidance (for example `thoughts/plans/AGENTS.md`)
- product-intent entrypoints (for example `thoughts/specs/product_intent.md` and `PRODUCT_INTENT.md`)
- testing instructions (for example `TESTING.md`)
- PR / commit / branch conventions documented anywhere in-repo

Use the repo's documented commands and file locations. Do not substitute your own defaults if the repo already specifies them.

### 1. Create the branch first

Create the implementation branch **before** planning.

Why: the reviewed plan should be committed onto the actual work branch before implementation starts.

### 2. Planning phase: plan only

Have pi read the task source and create or update the canonical plan.

When launching directly into planning from tmux, keep the first prompt tightly scoped and outcome-oriented. Tell pi explicitly to write the plan in this turn and avoid open-ended discovery expansion once it has enough repo evidence. If you leave the prompt too open, pi may spend many turns exploring examples/tests/docs before producing the plan artifact.

Planning requirements:
- pi may read the task, repo docs, and relevant files
- pi should write the plan in the repo's canonical plan location/format
- pi should **not** make code changes during planning
- if the repo already codifies plan format/location, you do not need to insist on separate "plan mode" wording as long as pi only changes the plan

Typical planning prompt requirements:
- identify the exact task/input source
- cite the canonical plan path
- instruct pi to avoid code changes
- require repo-specific verify steps and relevant product-intent linkage

### 3. Plan review in a fresh context

After the plan exists, start a fresh pi context and run exactly one review pass for ordinary work:

```text
/review:change <plan file>
```

Guidance:
- default to a single review pass
- if the work clearly needs repeated plan-review loops, that falls outside this preferred workflow unless the user explicitly wants it

### 4. Integrate review feedback

Use a fresh pi context as needed and integrate the review comments into the plan:

```text
/review:change-integrate <plan file>
```

The goal is an execution-ready plan that reflects the review feedback while still matching repo planning conventions.

### 5. Commit the reviewed plan

Commit the reviewed/integrated plan **before** implementation.

Why: the branch should contain the approved execution plan as its own committed artifact before pi starts changing code.

Follow repo-specific commit-message guidance rather than inventing a format.

### 6. Run `/dev:pm-review` for the plan stage

Before implementation starts, run:

```text
/dev:pm-review stage=plan
```

Tell pi explicitly that this is the **plan-stage** PM review. Use it to pressure-test the approved plan against product intent, expected functional outcomes, assumptions, edge cases, risks, and tradeoffs.

If the PM review surfaces gaps or misalignment, update the plan so those expectations are explicit before execution begins.

If the plan-stage PM review materially reshapes the plan, commit the updated plan artifact before starting implementation. Treat this like a second plan-approval checkpoint: the branch should record the PM-reviewed execution contract, not just the pre-PM version.

### 7. Execute the plan with pi

Run:

```text
/dev:run
```

Execution rules:
- continue until the plan is **100% complete**
- if pi stops early, read the result carefully and determine whether it simply needs a continuation nudge
- if context is getting heavy, compact before continuing
- minor implementation drift is acceptable when it preserves the approved plan's intent
- material drift is **not** acceptable; update the plan before continuing

### 7. Compact aggressively enough

Any time pi context exceeds **60%**, compact with:

```text
/pi-vcc
```

After compaction, continue execution rather than treating compaction as a stopping point.

### 8. Validate incrementally, then hit the full repo bar

During implementation you may run lighter, targeted validation loops to move faster.

Before opening a PR, all required tests/quality gates must pass according to the repo's documented instructions. Default to the repo's `TESTING.md` and related docs if present.

Treat the repo's full smoke suite as an explicit pre-PR gate whenever the repo defines one. A good default steering prompt to pi is effectively: "run all smoke tests and fix any issues you find." Do not treat targeted unit tests or partial validation as a substitute for the repo's defined smoke coverage.

Example completion bar sources:
- `TESTING.md`
- `AGENTS.md`
- package / workspace-specific validation docs

After the tests and smoke suite are passing, start a fresh pi context and run pi's validate command: `/dev:validate <plan file>` (or just `/dev:validate` to let pi pick the most recently modified plan) before creating the PR.

Do not open the PR with only partial validation, with a failing smoke suite, or without the fresh-context pi validate step.

### 10. Run `/dev:pm-review` for the implementation stage

Before PR creation, run:

```text
/dev:pm-review stage=implementation
```

Tell pi explicitly that this is the **implementation-stage** PM review. Use it to ask adversarial questions about whether the implementation actually achieved the intended functional outcome and whether it matches the expectations established during the plan-stage PM review.

Important follow-up behavior:
- the PM review may rewrite the plan
- if it rewrites the plan, run another plan review pass:

```text
/review:change <plan file>
/review:change-integrate <plan file>
```

- if the PM-review output says the plan changes require execution, run another:

```text
/dev:run
```

- then repeat validation and the implementation-stage PM review as needed
- allow up to **3** post-execution PM-review → re-plan/re-review → re-execution loops total
- if the work still is not coalescing into a deliverable increment after 3 loops, pause and notify Aaron instead of continuing indefinitely

If the implementation is not yet acceptable, guide pi toward the missing work rather than stopping at "tests pass".

You may write PM-review feedback back into the original plan wherever it fits best (for example a deviations log, notes section, or completion notes) as long as it remains clear and useful for resuming or reviewing the work.

### 11. Run a full code review before PR

Before PR creation, run a full code-review pass that is separate from PM review.

Expect to steer pi with something like:

```text
Perform a full code review of the implementation, call out correctness, regression, maintainability, and risk issues, and fix the issues you find before we open the PR.
```

Treat review findings as real work: fix them, then rerun any impacted validation so the branch is green after the fixes rather than only before them.

### 12. Open a ready-for-review PR

Only after:
- the approved plan is complete
- the repo's full validation bar passes
- the PM/product-intent review is acceptable
- the explicit full code-review pass has been completed and its findings addressed
- if the shipped change affects app visuals, fresh screenshots from the implemented branch are included in the PR
- if the shipped change affects a user flow or interaction sequence, a fresh video/screen recording of that flow is included in the PR

Then create a **ready-for-review** PR, not a draft, following repo-specific PR formatting instructions.

For Hermes-side orchestration, do not leave this as a memory step. Use the workflow controller's explicit PR stage:

```bash
python ~/.hermes/scripts/pi_workflow_ctl.py \
  --pane <pane> \
  --repo <repo> \
  --plan <plan> \
  --stage create-pr \
  --base develop \
  --pr-title "<title>" \
  --pr-body "<body>"
```

### 13. Wait for jobs, review feedback, and mergeability after PR creation

After the PR is opened, do not consider the workflow done immediately.

Post-PR requirements:
- wait for GitHub jobs/checks to finish at least once
- inspect PR comments, review feedback, and failing-check output at least once
- address the feedback/issues that appear in that first pass
- confirm the PR is mergeable
- if the PR has conflicts, rebase onto `develop`, resolve the conflicts, push again, and re-check jobs/feedback

The workflow controller has a matching follow-up stage for this:

```bash
python ~/.hermes/scripts/pi_workflow_ctl.py \
  --pane <pane> \
  --repo <repo> \
  --plan <plan> \
  --stage post-pr-followup
```

The workflow is not complete until the branch has survived at least one full post-PR feedback/check cycle and is mergeable.

The controller should:
- refuse PR creation on a dirty tree
- refuse when the branch has no upstream
- return the existing PR instead of creating a duplicate when one is already open for the branch
- when the plan path encodes a Linear issue key (for example `nod-445-...`), sync that issue to `In Review` once the PR exists; if the PR already exists, still perform the Linear sync instead of treating create-pr as a no-op

Current implementation note:
- `~/.hermes/scripts/pi_workflow_ctl.py` performs the Linear sync during `create-pr` via `~/code/ai-configs/tools/ltui/bin/ltui issues update <ISSUE> --state "In Review"`
- issue detection should be case-insensitive on the plan path and normalized to uppercase (`nod-445` -> `NOD-445`)

## Practical execution loop

Use this mental loop while supervising pi:

1. Read repo docs and task source
2. Create branch
3. Have pi write/update plan only
4. Review the plan once
5. Integrate plan feedback
6. Commit reviewed plan
7. Run `/dev:pm-review stage=plan`
8. Run `/dev:run`
9. Compact at >60% context with `/pi-vcc`
10. Nudge pi to continue whenever it pauses before the plan is complete
11. Run full repo validation
12. Run the full smoke suite and fix any issues it finds
13. In a fresh context, run `/dev:validate <plan file>` (or `/dev:validate` for the latest plan)
14. Run `/dev:pm-review stage=implementation`
15. If PM review rewrote the plan, run `/review:change <plan file>` then `/review:change-integrate <plan file>`
16. If PM review says execution is needed, run `/dev:run`, re-validate, and repeat the implementation-stage PM review
17. Run a full implementation code review and fix any findings
18. Re-run impacted validation/smoke checks after review-driven fixes
19. Cap the post-execution PM-review/re-execution loop at 3 total cycles; if it still is not coalescing into a deliverable increment, pause and notify Aaron
20. If the delivered change affects app visuals, capture fresh screenshots from the implemented branch and include them in the PR
21. If the delivered change affects a user flow or interaction sequence, capture a fresh video/screen recording and include it in the PR
22. Open ready-for-review PR
23. Run `post-pr-followup`: wait for GitHub jobs/review feedback, address at least one pass of what comes back, and make sure the PR is mergeable; if needed, rebase onto `develop`, resolve conflicts, push again, and re-check

Preferred control surface for Hermes orchestration:
- `python ~/.hermes/scripts/pi_workflow_ctl.py --pane <pane> --repo <repo> --plan <plan> --stage review`
- `... --stage integrate`
- `... --stage commit-plan`
- `... --stage pm-plan`
- `... --stage execute`
- `... --stage validate`
- `... --stage pm-implementation`
- `... --stage create-pr --base develop --pr-title "..." --pr-body "..."`
- `... --stage post-pr-followup`

This avoids freehand command mistakes and enforces legal stage transitions including PR creation.

## Guardrails

### Do
- preserve the staged workflow
- use fresh contexts for plan review / integration when appropriate
- use repo documentation as the source of truth
- keep pushing pi until the plan is genuinely complete
- inspect whether a pause is harmless before assuming failure
- keep controller/supervisor artifacts out of the repo state (`.tmp*`, `.supervisor-status.json`, helper scripts). Remove or exclude them before lint/commit/clean-tree checks so they do not create false blockers or pollute the decision record.

### Don't
- don't let planning mutate production code
- don't assume work selection always starts from the same folder or ticket system
- don't open a PR before full validation passes
- don't confuse code-complete with product-complete
- don't accept material scope drift without updating the plan

## Minimal prompt patterns

### Plan-only prompt

Use a prompt shaped like:

```text
Read the task and repo guidance, then create or update the canonical execution plan at <plan path>. Follow repo planning conventions exactly. Do not make any code changes in this phase.
```

### Review prompt

```text
/review:change <plan file>
```

### Review integration prompt

```text
/review:change-integrate <plan file>
```

### Plan-stage PM review prompt

```text
/dev:pm-review stage=plan
```

### Implementation-stage PM review prompt

```text
/dev:pm-review stage=implementation
```

### Post-implementation loop

When `/dev:pm-review stage=implementation` rewrites the plan or says more execution is required:

```text
/review:change <plan file>
/review:change-integrate <plan file>
/dev:run
```

Then re-run the appropriate validation steps and `/dev:pm-review stage=implementation`.

Do not continue this loop forever — stop after **3** total post-execution PM-review/re-execution cycles and notify Aaron that the plan is not coalescing into a deliverable increment.

### Execution prompt

```text
/dev:run
```

### Compaction prompt

```text
/pi-vcc
```

### Continuation nudge

Use a direct continuation prompt when pi pauses early, such as:

```text
Continue executing the approved plan from the current state. Finish the remaining work and do not stop until the plan is complete unless you hit a real blocker.
```

## Notes specific to Aaron's workflow

- Branch creation happens before planning.
- The reviewed plan is committed before implementation.
- Single review pass is the default for most plans.
- Compaction threshold is 60% context.
- Incremental tests can be lighter, but the pre-PR bar is the repo's full documented test/quality-gate surface, including the full smoke suite whenever the repo has one.
- Final judgment must include two `/dev:pm-review` passes: one at `stage=plan` before execution, and one at `stage=implementation` after implementation to judge the result against those expectations.
- Before PR, run a full implementation code review in addition to PM review and fix what it finds.
- For app UI changes, include fresh screenshots in the PR from the implemented branch.
- For user-flow or interaction changes, include a fresh video/screen recording in the PR.
- After PR creation, run the controller's `post-pr-followup` stage (or equivalent manual loop) so the branch survives at least one GitHub jobs/review-feedback cycle and is confirmed mergeable.
- If implementation-stage PM review rewrites the plan, re-run `/review:change` + `/review:change-integrate`, then execute again if PM review says re-execution is required.
- Cap post-execution PM-review/re-execution loops at 3 before pausing and notifying Aaron that the work is not coalescing into a deliverable increment.
