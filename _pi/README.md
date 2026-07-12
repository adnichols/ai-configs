# Pi Configuration

This directory contains Pi-specific resources:

- `prompts/` — prompt templates exposed as slash commands
- `agents/` — @tintinweb/pi-subagents-compatible agent definitions
- `extensions/` — Pi runtime extensions, including the maintained `/prd` workflow and utility integrations
- `models.json` — managed custom model entries merged into Pi's global `models.json`

Repo-owned default Pi/Codex shared skills live in the repo-level `skills/` tree, and `skills/install-matrix.json` also inventories package-backed and optional-profile shared skills fetched via `npx skills`. The installed default shared runtime location remains `~/.agents/skills`.


## Installation

These resources are installed by `install.sh` to Pi's global agent directory. There are three distinct Pi installation surfaces:

- repo-managed extensions: copied from this repo into `~/.pi/agent/extensions/`
- repo-managed model entries: merged from `_pi/models.json` into `~/.pi/agent/models.json` without replacing local API keys
- package-managed Pi installs: registered via `pi install` / `pi update` and visible in `pi list`

Plan-reviewer browser action comments route through default shared skills in `~/.agents/skills`: `plan-reviewer-execution-ready` for readiness review requests and `plan-reviewer-build` for Build Plan requests. Rarely used browser/CDP helper skills such as `brave-cdp` and `chrome-cdp` remain inventoried in `skills/install-matrix.json` under the optional `ops-browser` profile and are not loaded into Pi/Codex default context.

`pi list` only shows the package-managed set; it does not list repo-managed files like `todo.ts`, `simple-multi-status.ts`, or `pi-prd-mode`. See [Package-managed Pi extensions](#package-managed-pi-extensions) below for the exact git and npm package set.

```bash
./install.sh --pi      # Install Pi prompt templates + subagents + extensions and sync shared skills
./install.sh --all     # Install everything, including Pi
./install.sh --pi --update  # Update skills.sh-managed global skills first, then install Pi resources
```

`--update` runs `npx skills update -g -y` for globally installed skills tracked by skills.sh before the normal ai-configs sync re-normalizes shared skills in `~/.agents/skills`.

To verify the Pi install surfaces this repo manages, run:

```bash
bash scripts/verify-pi-install.sh
```

Installed layout:

```text
~/.agents/skills/
├── doct-document-ops/
└── ...

~/.pi/agent/
├── APPEND_SYSTEM.md
├── README.md
├── models.json
├── prompts/
│   ├── cmd:debug.md
│   ├── dev:plan.md
│   └── ...
├── agents/
│   ├── developer-mid.md
│   ├── developer-mm.md
│   ├── orchestrator-glm.md
│   ├── ui-design-glm.md
│   ├── quality-reviewer.md
│   ├── quality-reviewer-glm.md
│   ├── glm5.2-high.md
│   ├── glm5.2-xhigh.md
│   ├── explore.md
│   └── ...
└── extensions/
    ├── pi-prd-mode/
    │   └── index.ts
    ├── aoe-status/
    │   └── index.ts
    ├── simple-multi-status.ts
    ├── percentage-compaction.ts
    └── todo.ts
```

The installer copies the repo-root `APPEND_SYSTEM.md` into `~/.pi/agent/APPEND_SYSTEM.md`.

The installer also merges `_pi/models.json` into `~/.pi/agent/models.json`, upserting managed model metadata while preserving local provider fields such as API keys except for the repo-owned `openai-codex` provider. `openai-codex` is intentionally pinned to the local CLI Proxy API at `http://127.0.0.1:8318/v1` using Pi's `openai-responses` adapter, with Codex model IDs and thinking-level mappings preserved. This routes requests to `/v1/responses`, retaining encrypted reasoning items across tool turns instead of using Chat Completions or ChatGPT's separate `/codex/responses` route.

`install.sh --pi` now enforces `openai-codex/gpt-5.6-sol` as the Pi default, keeps that Sol route and `opencode/glm-5.2` enabled, and updates the web-search summary route to Sol. Repository-owned agents use Sol medium for normal capable work, Sol high for consequential implementation and review, and Luna medium only for bounded structured feedback.

## Structure

```text
_pi/
├── README.md
├── models.json         # Managed custom model entries merged into ~/.pi/agent/models.json
├── prompts/            # Pi prompt templates / slash commands
│   └── *.md
├── agents/             # Pi subagent definitions for @tintinweb/pi-subagents
│   └── *.md
└── extensions/         # Pi runtime extensions
    ├── */index.ts
    └── *.ts

skills/
├── install-matrix.json # Shared skill inventory and default/optional profile metadata used by install.sh
└── */SKILL.md          # Repo-owned default shared installable skills exposed to Pi via ~/.agents/skills
```

## Prompt Templates

Pi loads prompt templates from `~/.pi/agent/prompts/`.

Each Markdown file becomes a slash command using the filename:

- `cmd:debug.md` → `/cmd:debug`
- `cmd:execute-plan.md` → `/cmd:execute-plan`
- `dev:plan.md` → `/dev:plan`
- `dev:plan-from-prd.md` → `/dev:plan-from-prd`
- `dev:pm-review.md` → `/dev:pm-review`
- `prd:clarify-round.md` → `/prd:clarify-round`
- `review:change.md` → `/review:change`
- `review:prd.md` → `/review:prd`

Prompt templates in this repo are kept as top-level files in `_pi/prompts/`, so no extra nested prompt-directory discovery is required.

Planning remains available through prompt templates and shared skills such as `/dev:plan`, `/dev:reviewed-html-plan`, and `/skill:reviewed-html-plan`. The `/prd` command is provided by the `pi-prd-mode` extension.

## Extensions

Pi loads runtime extensions from `~/.pi/agent/extensions/`.

This repo also ships `aoe-status`, a lightweight lifecycle reporter for Agent of Empires (AoE) that:

- writes content-free Pi lifecycle metadata to `/tmp/aoe-pi-status/<uid>/<pid>.json`,
- reports `idle` on load/session start, `running` on agent/turn start, `idle` on agent end, and `stopped` on shutdown,
- refreshes the latest status every 30 seconds so AoE does not fall back to stale pane parsing after the registry TTL,
- stores only status, pid, cwd, session file path, and timestamps, never prompts, messages, tool arguments, or model output.

This repo also ships a maintained `pi-prd-mode` extension that:

- powers `/prd` mode for PRD/spec workflows,
- keeps PRD-mode writes scoped to `thoughts/plans/prd-*.md`, `thoughts/specs/spec-*.md`, and transient review artifacts under `thoughts/validation/prd-reviews/<prd-slug>/`,
- asks the model to compare each answer round against the intent/spec baseline and use `/prd:clarify-round` for the critical-thinker-first clarification loop,
- keeps `/review:prd` as an explicit review gate instead of auto-running it after edits,
- records PRD review approval in `thoughts/validation/prd-reviews/<prd-slug>/review-status.json`,
- prompts you to run `/review:prd` before handoff whenever the latest PRD review is missing, stale, or not approved,
- offers `/dev:plan-from-prd <prd>` as the reviewed-PRD handoff path,
- disables `/prd` before dispatching into the fresh planning session so PRD mode restrictions do not leak into execution planning.

This repo also ships `simple-multi-status.ts`, a lightweight multi-line status widget that auto-loads on install and shows:

- the active model,
- token, cache, and cost totals,
- current provider/model status when present,
- current context-window usage,
- the current working directory.

This repo also ships `percentage-compaction.ts`, which gives you percentage-based control over context compaction:

- sends soft/strong model-visible nudges at 60%/75% so agents can choose a safe `compact_context` boundary,
- uses an 80% hard backstop for automatic pi-vcc compaction,
- interrupts long tool-driven agent runs at a turn boundary, then lets pi-vcc resume the agent after successful compaction,
- if the hard backstop finds no safe compaction cut during an active turn, treats it as a recoverable skip, waits for pending tool results when needed, sends one bounded-retry continuation steer, and suppresses immediate same-percent no-cut retry loops,
- `/compact-status` to check current context usage,
- `/compact-now [instructions]` to trigger compaction manually,
- gates pi's built-in auto-compaction so repo-managed pi-vcc handles hard-backstop compaction with no-cut recovery,
- cancels compaction instead of falling back to Pi's default compactor when pi-vcc is not loaded.

To adjust nudge thresholds, edit `COMPACTION_NUDGE_PERCENT` / `COMPACTION_STRONG_NUDGE_PERCENT`; to adjust the automatic hard backstop, edit `HARD_AUTO_COMPACTION_PERCENT` in the extension file.
To use with pi-vcc, run `./install.sh --pi`; `pi list` should show the stable mirror under `~/.pi/agent/local-packages/ai-configs/pi-vcc`.

**Note:** With the vendored pi-vcc installed, no additional compaction configuration is needed. The extension proactively starts pi-vcc compaction at the configured hard-backstop percentage, and pi-vcc handles the actual algorithmic compaction when triggered. This repo now ships the `/pi-vcc` manual-bypass marker and the agent-only-tail fallback directly in the vendored package, so rerunning `./install.sh --pi` refreshes both behaviors without patching global npm files.

This repo also vendors Pi's `todo.ts` extension, which auto-loads on install and provides:

- a `todo` tool for branch-aware task tracking with **proactive planning guidance** — agents are encouraged to create comprehensive todo lists BEFORE beginning work,
- a `/todos` command for inspecting the current branch todo list,
- session-detail persistence so todo state follows Pi branching correctly,
- best practices baked into the tool description: decompose tasks into small steps, update progress as you go, keep todos specific and measurable.

## Subagents

Pi subagents load agent definitions from `~/.pi/agent/agents/`.

## Package-managed Pi extensions

In addition to the repo-managed files under `~/.pi/agent/extensions/`, `install.sh --pi` also registers Pi packages via `pi install` / `pi update`. These are the entries that appear in `pi list`. `pi-multi-pass` is intentionally not installed; multi-account Codex routing is replaced by the single local `openai-codex` CLI Proxy API provider.

Git-managed packages:
- `pi-gpt-config`

npm-managed packages:
- `@tintinweb/pi-subagents`
- `@aliou/pi-processes`
- `pi-web-access`
- `@fnnm/pi-ast-grep`
- `pi-updater`
- `pi-powerline-footer`
- `pi-side-agents`
- `pi-no-soft-cursor`
- `@tmustier/pi-files-widget`
- `@tmustier/pi-raw-paste`
- `@ff-labs/pi-fff`

local path packages:
- `~/.pi/agent/local-packages/ai-configs/pi-vcc` (a stable mirror synced from `./_pi/packages/pi-vcc`; install tests and worktrees must not register their transient checkout path)
- `../3p/pi-interactive-shell` (preferred when present; otherwise `git:github.com/adnichols/pi-interactive-shell`)

Use `pi list` on a host to verify what is currently registered. To verify both surfaces together, run `scripts/verify-pi-install.sh` from this repo.

The maintained agent files use the flat frontmatter expected by `@tintinweb/pi-subagents`: every agent has a `name`, and `tools` is a comma-separated Pi tool list when specified.

Example installed agents:

- `developer-mid`
- `developer-mm`
- `quality-reviewer`
- `quality-reviewer-glm`
- `glm5.2-high`
- `glm5.2-xhigh`
- `Explore`
- `research`
- `plan-gpt`
- `reviewer-plan-adversarial-gpt`
- `reviewer-plan-adversarial-opus`
- `worktree-creator`

## Skills Overview

### Canonical workflow
- `adn-dev-wf` — reviewed-plan workflow from plan creation through direct execution and PM follow-up
- `reviewed-html-plan` / `/dev:reviewed-html-plan` — creates/registers HTML plans in Doct, follows returned `listenerInstructions`, starts the durable queue-backed listener, processes browser feedback, runs PM plus GPT/GLM Pi subagent plan reviews, and stops at execution-ready handoff

### Dev / execution
- `run-plan` / `/run-plan` — full lifecycle execution for an explicit reviewed plan: durable Pi goal tracking, implementation, scoped reviews, implementation-stage PM review, applicable GPT/GLM pre-PR review, base freshness, PR creation, current PR feedback snapshot, local merge-readiness consensus, and safe auto-rebase when needed
- `dev:run` — direct GPT-5.6 Sol medium execution with one `quality-reviewer` pass after each phase
- `orchestrator-glm` — GLM-5.2 high planning/orchestration route for decomposition, routing, long debug-loop supervision, failure triage, and review synthesis; use it by switching the active scoped model to `opencode/glm-5.2` or delegating a bounded packet from the GPT-5.6 Sol parent
- `ui-design-glm` — GLM-5.2 high UI design specialist for visual direction, UX tradeoffs, accessibility-aware critique, and UI implementation review
- `pre-pr-implementation-review` — GPT-5.6 Sol plus applicable GLM-5.2 Pi subagent pre-PR implementation review loop until in-scope P1/P2/P3 findings are addressed; `glm5.2-high` handles normal high-risk bounded review, `glm5.2-xhigh` is reserved for final or exceptional-risk review, `quality-reviewer-glm` remains a legacy xhigh compatibility alias, and low-risk scopes record a truthful GLM skip; when invoked by `run-plan`, it returns `OPEN_PR_READY` so the caller continues to final verification, base freshness, PR creation, and local merge-readiness checking without waiting for a Codex thumbs-up

### Git / workflow
- `cmd-create-pr`
- `cmd-start-linear-issue`
- `cmd-start-linear-issue-branch`

### Development
- `cmd-research`
- `cmd-debug`
- `dev-plan`
- `dev:pm-review` — adversarial PM review that reshapes plans against intended outcomes, product principles, and early-stage scope fit
- `cmd-graduate`
- `doct-document-ops` — doct document operations, including publishing coding plans under personal `Coding Plans`
- `sentry-cli` — investigate Sentry orgs, projects, issues, and recent events; optionally mute/resolve/unresolve issues after confirmation

### Context / review
- `cmd-create-handoff`
- `cmd-resume-handoff`
- `review-plan`
- `review-plan-adversarial`
- `review-change`
- `review-change-integrate`
- `review-change-kimi`
- `review-change-opus`
- `review-change-claude-code` — Claude Code review-only pass through the shared private-tmux interactive launcher
- `pre-pr-implementation-review` — runnable independently or automatically from `run-plan` before PR creation; it is not a terminal replacement for PM review, base freshness, opening the PR, or proving local merge readiness

## Usage

Prompt templates:

```text
/cmd:debug login flake in CI
/dev:plan feature-name
/dev:reviewed-html-plan feature-name
/dev:pm-review thoughts/plans/my-plan.html
/dev:pm-review thoughts/plans/my-plan.html implementation
/prd
/prd:clarify-round thoughts/plans/prd-my-feature.md
/review:plan thoughts/plans/my-plan.html
/review:plan-adversarial thoughts/plans/my-plan.html
/review:prd thoughts/plans/prd-my-feature.md
/review:change thoughts/plans/my-plan.html
/review:change-kimi thoughts/plans/my-plan.html
/review:change-opus thoughts/plans/my-plan.html
/review:change-claude-code thoughts/plans/my-plan.html
/skill:pre-pr-implementation-review thoughts/plans/my-plan.html
/run-plan thoughts/plans/my-plan.html
/dev:plan-from-prd thoughts/plans/prd-my-feature.md
/cmd:send-plan-to-doct thoughts/plans/my-plan.md
```

## Reviewed-plan handoff

Use `/run-plan <plan>` after a reviewed plan is ready for full implementation-through-ready-PR execution: durable Pi goal tracking, implementation, implementation-stage PM review, applicable GPT/GLM pre-PR review, base freshness, PR creation, current PR feedback snapshot, local merge-readiness consensus, and safe auto-rebase when needed. Use `/dev:run <plan>` only for direct execution without the full PR lifecycle. For browser-reviewed plans, the active artifact is `thoughts/plans/<slug>.html` or the repo-selected Markdoc source, and `skills/doct-document-ops/SKILL.md` is the sole source for concrete Doct plan commands, HTML/Markdoc/Markdown publishing guidance, durable listener startup, readiness metadata, canonical URL rules, and comment mechanics.

Canonical browser-reviewed HTML plan flow:

```text
/dev:plan <plan>
/dev:reviewed-html-plan <plan>    # register, monitor browser comments, PM-review, and run GPT/GLM plan reviews
/cmd:execute-plan <plan>
```

Explicit inline review flow remains available when needed:

```text
/review:plan <plan>
/review:change-integrate <plan>
/review:plan-adversarial <plan>   # optional
/cmd:execute-plan <plan>
```

Optional second pass: run `/review:plan-adversarial <plan>` after `/review:change-integrate <plan>` when you want an explicit challenge review before execution.

Use `/dev:pm-review <plan> implementation` after execution when you want a corrective PM pass that checks whether the intended user outcome was actually realized and, if not, reshapes the plan with the missing completion work instead of stopping at findings.

- `/cmd:execute-plan` is the canonical wrapper for choosing between `/run-plan <plan>` and `/dev:run <plan>`.
- `/run-plan` is the full lifecycle reviewed-plan continuation through durable Pi goal tracking, PM review, applicable GPT/GLM pre-PR review, base freshness, PR creation, current PR feedback snapshot, local merge-readiness consensus, and safe auto-rebase when needed; `/dev:run` remains the direct execution-only path with one `quality-reviewer` pass after each phase.
- `/skill:pre-pr-implementation-review` can be run independently before opening a PR and is also invoked automatically by `run-plan` after scoped implementation reviews. In a scoped run, clean GPT/GLM consensus over all in-scope P1/P2/P3 findings means `OPEN_PR_READY`; the runner must then rerun final verification if needed, confirm base freshness, commit, push, open the PR, and prove local merge readiness without waiting for a Codex thumbs-up.
- In Pi, `/cmd:execute-plan` starts a fresh session and launches the selected execution flow from clean context.
- `/review:change-claude-code` remains available as an explicit manual review request; it is not an automatic planning-mode fallback.

Use `/dev:plan-from-prd <prd>` after a reviewed PRD delta is ready to become an execution plan.

The sequence below is the end-to-end reviewed-PRD path from PRD entry through handoff. Clarification continues in `/prd` and `/prd:clarify-round` until complete before the operator runs `/review:prd`.

```text
/prd
/review:prd thoughts/plans/prd-my-feature.md
/dev:plan-from-prd thoughts/plans/prd-my-feature.md
```

- It is the canonical wrapper for turning a reviewed PRD delta into a fresh single-file plan session.
- In Pi `/prd` mode, the typical sequence is `/prd` → update the PRD with the latest user answers → `/prd:clarify-round` → repeat that clarification loop as needed → `/review:prd` when a wider review is worthwhile → `/dev:plan-from-prd <prd>` after an approved review result.
- `/review:prd` is the explicit review gate before `/dev:plan-from-prd`.
- `/review:prd` writes seven per-reviewer files under `thoughts/validation/prd-reviews/<prd-slug>/`, integrates the combined findings back into the PRD, keeps `integration-ledger.md` plus `review-status.json`, and removes the seven reviewer output files after integration.
- `/dev:plan-from-prd` validates that `thoughts/validation/prd-reviews/<prd-slug>/review-status.json` exists, is approved, and is not older than the PRD.
- If the latest review result for the same PRD is `needs_changes`, resolve the inline `[REVIEW:...]` comments in that PRD and rerun `/review:prd <prd-path>`.
- If the latest review result for the same PRD is `review_failed`, inspect `thoughts/validation/prd-reviews/<prd-slug>/integration-ledger.md` for the failed reviewer row(s) and notes, resolve the failed review-cycle cause(s), and rerun `/review:prd <prd-path>`.
- If the latest review result for the same PRD is stale, or the same PRD does not yet have a current approved review result, rerun `/review:prd <prd-path>` before handoff.
- The extension does not auto-run `/review:prd`; that gate is explicit and should happen only once the intent is clarified.
- When the handoff path is used, `/prd` mode is disabled before planning so PRD-only tool restrictions do not leak into execution planning.
- In Pi, the handoff command starts a fresh session and then continues the planning work from that clean context.

Skills:

```text
/run-plan thoughts/plans/user-profile-redesign.html
/skill:reviewed-html-plan user-profile-redesign
/skill:cmd-start-linear-issue-branch ENG-123
/skill:doct-document-ops
/skill:sentry-cli
```

## Notes

- Pi global resources live under `~/.pi/agent/`, not `~/.pi/`.
- Repo-managed extensions live in `~/.pi/agent/extensions/`; package-managed installs are reported by `pi list`.
- `~/.pi/agent/APPEND_SYSTEM.md` is installed from the repo-root `APPEND_SYSTEM.md`.
- Project-local Pi resources can also live under `.pi/prompts/`, `.pi/skills/`, `.pi/agents/`, and `.pi/extensions/`.
- Pi natively auto-discovers both `~/.agents/skills/` and `~/.pi/agent/skills/`; this repo uses `~/.agents/skills/` as the canonical default shared runtime location and reserves `~/.pi/agent/skills/` for Pi-local-only entries. Repo-owned skill payloads come from `skills/`, while package-backed entries are fetched per `skills/install-matrix.json`. Skills marked `defaultInstall: false` stay in the inventory but are backed out of default discovery to reduce session context.
- `@tintinweb/pi-subagents`-compatible agent definitions install to `~/.pi/agent/agents/`.
- GPT-5.6 Sol medium is the normal repository-owned Pi OpenAI code-writing route. For planning/orchestration-heavy, review-synthesis-heavy, UI-design-heavy, or long test/debug-loop work, explicitly switch the active scoped model to `opencode/glm-5.2` or delegate a bounded packet to `orchestrator-glm`; do not reroute unrelated sessions. Use `Explore`/`explore` for broad discovery before sending scoped code-writing packets to `developer-mid`, and reserve `developer-high` for complex or failed scoped implementation work.
