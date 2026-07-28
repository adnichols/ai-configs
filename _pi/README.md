# Pi Configuration

This directory contains Pi-specific resources:

- `prompts/` — prompt templates exposed as slash commands
- `agents/` — @tintinweb/pi-subagents-compatible agent definitions
- `extensions/` — Pi runtime extensions, including the maintained `/prd` workflow and utility integrations
- `lib/` — shared import-only TypeScript modules used by extensions; never auto-loaded as extensions
- `models.json` — managed custom model entries merged into Pi's global `models.json`
- `tasks-config.json` — managed global defaults for the package-managed `@tintinweb/pi-tasks` extension

Repo-owned default Pi/Codex shared skills live in the repo-level `skills/` tree, and `skills/install-matrix.json` also inventories package-backed and optional-profile shared skills fetched via `npx skills`. The installed default shared runtime location remains `~/.agents/skills`.


## Installation

These resources are installed by `install.sh` to Pi's global agent directory. There are three distinct Pi installation surfaces:

- repo-managed extensions: copied from this repo into `~/.pi/agent/extensions/`, including `vent.ts`, which writes the shared feedback log to `~/.pi/VENT.md`
- repo-managed Pi libraries: copied from `_pi/lib/` into `~/.pi/agent/lib/`; this keeps import-only helpers out of Pi's auto-loaded `extensions/` directory
- repo-managed model entries: merged from `_pi/models.json` into `~/.pi/agent/models.json` without replacing local API keys
- repo-managed task defaults: copied from `_pi/tasks-config.json` to `~/.pi/agent/tasks-config.json`
- package-managed Pi installs: registered via `pi install` / `pi update` and visible in `pi list`

Plan review and execution use the maintained `reviewed-html-plan` and `run-plan` workflows directly. Rarely used browser/CDP helper skills such as `brave-cdp` and `chrome-cdp` remain inventoried in `skills/install-matrix.json` under the optional `ops-browser` profile and are not loaded into Pi/Codex default context.

`pi list` only shows the package-managed set; it does not list repo-managed files like `simple-multi-status.ts` or `pi-prd-mode`. See [Package-managed Pi extensions](#package-managed-pi-extensions) below for the exact git and npm package set.

```bash
./install.sh --pi      # Install Pi prompt templates + read-only/planning subagents + extensions and sync shared skills
./install.sh --all     # Install everything, including Pi
./install.sh --pi --update  # Update skills.sh-managed global skills first, then install Pi resources
```

`--update` runs `npx skills update -g -y` for globally installed skills tracked by skills.sh before the normal ai-configs sync re-normalizes shared skills in `~/.agents/skills`.

To verify the Pi install surfaces this repo manages, run:

```bash
bash scripts/verify-pi-install.sh
bash scripts/test-pi-extension-autoload-e2e.sh  # real fresh Pi TUI startup
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
├── tasks-config.json
├── prompts/
│   ├── cmd:debug.md
│   ├── dev:plan.md
│   └── ...
├── agents/
│   ├── planner.md        # GPT-5.6 Sol medium; planning-only
│   ├── reviewer.md       # GPT-5.6 Terra medium; read-only review
│   ├── scout.md          # GPT-5.6 Terra low; read-only discovery
│   └── Explore.md        # disabled bundled persona override
├── extensions/
│   ├── pi-prd-mode/
│   │   └── index.ts
│   ├── aoe-status/
│   │   └── index.ts
│   ├── simple-multi-status.ts
│   └── percentage-compaction.ts
└── lib/
    └── grok-context-ceiling-policy.ts
```

The installer renders the repo-root `APPEND_SYSTEM.md` into `~/.pi/agent/APPEND_SYSTEM.md` through `scripts/render_pi_append_system.py`. It replaces `{{AI_CONFIGS_VERSION}}` with `YYYY-MM-DD+<git-sha>` and appends `-dirty` only when the doctrine file differs from that commit, so behavior reports can be tied back to repository history. Installation fails outside a Git checkout, when the doctrine is untracked, or if the template token is missing, duplicated, or remains unresolved.

The doctrine is request-type-first: questions, explanations, inspection, research, diagnosis, review, planning discussion, and status requests remain read-only unless the user separately authorizes a change. Persistence instructions increase effort only within the already-authorized scope.

The installer also merges `_pi/models.json` into `~/.pi/agent/models.json`, upserting managed model metadata while preserving local provider fields such as API keys except for the repo-owned `openai-codex` provider. `openai-codex` is intentionally pinned to the local CLI Proxy API at `http://127.0.0.1:8318/v1` using Pi's `openai-responses` adapter, with Codex model IDs and thinking-level mappings preserved. This routes requests to `/v1/responses`, retaining encrypted reasoning items across tool turns instead of using Chat Completions or ChatGPT's separate `/codex/responses` route. It also copies `_pi/tasks-config.json` into `~/.pi/agent/tasks-config.json`; the tracked default uses `taskScope: "memory"`.

`install.sh --pi` now enforces `openai-codex/gpt-5.6-sol` as the Pi default, keeps that Sol route and `opencode/glm-5.2` enabled, and updates the web-search summary route to Sol. The driving Pi session is the only code-writing route. The planning agent uses GPT-5.6 Sol medium, the review agent uses GPT-5.6 Terra medium, and the read-only scout uses GPT-5.6 Terra low. GPT-5.4 and GPT-5.4-mini are retired exactly from Pi-owned agents, managed `openai-codex` model entries, and Pi settings aliases while caller-owned providers/models remain untouched.

## Structure

```text
_pi/
├── README.md
├── models.json         # Managed custom model entries merged into ~/.pi/agent/models.json
├── tasks-config.json   # Global pi-tasks defaults copied into ~/.pi/agent/tasks-config.json
├── prompts/            # Pi prompt templates / slash commands
│   └── *.md
├── agents/             # Pi subagent definitions for @tintinweb/pi-subagents
│   └── *.md
├── extensions/         # Pi runtime extensions; every .ts here must export a factory
│   ├── */index.ts
│   └── *.ts
└── lib/                # Import-only shared modules, copied to ~/.pi/agent/lib
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

Pi loads runtime extensions from `~/.pi/agent/extensions/`. Every TypeScript file in that directory is auto-loaded and must export an extension factory. Import-only helpers, including the Grok context-ceiling policy used by `percentage-compaction.ts`, live in `~/.pi/agent/lib/` instead.

This repo ships `thinking-shortcuts.ts`, which adds Codex-style bidirectional reasoning controls:

- `Alt+.` increases the current model's thinking level,
- `Alt+,` decreases the current model's thinking level,
- both shortcuts stop at the model's supported boundaries instead of wrapping.

Run `bun test scripts/thinking-shortcuts.test.ts` for the extension contract tests and `scripts/test-thinking-shortcuts-e2e.sh` for the real Pi TUI keypress test.

The managed `herdr-agent-state.ts` integration reports Pi lifecycle state directly to Herdr. It treats `agent_settled` as the foreground-idle boundary, preserves same-session Herdr authority across Pi `/reload`, and, by default, keeps the pane working while any tracked `process` job remains live except known passive listeners, monitors, dev servers, and watchers. Configure the policy with `HERDR_PI_BACKGROUND_PROCESS_MODE=none|finite|all`; extend the passive ignore list with comma- or newline-separated literal name/command fragments in `HERDR_PI_BACKGROUND_PROCESS_IGNORE`. Doct `plans listen` and blocking `plans agent next --wait` commands are ignored explicitly. Run `node tests/test_herdr_agent_state.mjs` for the lifecycle, reload, and process-policy contract test.

This repo also ships `aoe-status`, a lightweight lifecycle reporter for Agent of Empires (AoE) that:

- writes content-free Pi lifecycle metadata to `/tmp/aoe-pi-status/<uid>/<pid>.json`,
- reports `idle` on load/session start, `running` on agent/turn start, `idle` on agent end, and `stopped` on shutdown,
- refreshes the latest status every 30 seconds so AoE does not fall back to stale pane parsing after the registry TTL,
- stores only status, pid, cwd, session file path, and timestamps, never prompts, messages, tool arguments, or model output.

This repo also ships a maintained `pi-prd-mode` extension that:

- powers `/prd` mode for PRD/spec workflows,
- keeps PRD-mode writes scoped to `thoughts/plans/prd-*.md`, `thoughts/specs/spec-*.md`, and transient review artifacts under `thoughts/validation/prd-reviews/<prd-slug>/`,
- asks the model to compare each answer round against the intent/spec baseline and use `/prd:clarify-round` for a clarification-gap reviewer pass followed by optional bounded scout research,
- keeps `/review:prd` as an explicit review gate instead of auto-running it after edits,
- records PRD review approval in `thoughts/validation/prd-reviews/<prd-slug>/review-status.json`,
- prompts you to run `/review:prd` before handoff whenever the latest PRD review is missing, stale, or not approved,
- offers `/dev:plan-from-prd <prd>` as the reviewed-PRD handoff path,
- disables `/prd` before dispatching into the fresh planning session so PRD mode restrictions do not leak into execution planning.

The repo-owned `claude-review` and `codex-review` Pi extensions are temporarily disabled and retained under `_pi/disabled-extensions/` for comparison and possible rollback. `install.sh --pi` removes any stale installed copies from `~/.pi/agent/extensions/`, so the `claude_review` and `codex_review` tools are unavailable after a fresh Pi session starts.

Required Pi plan and code reviews use the repository-owned `reviewer` Pi subagent (`openai-codex/gpt-5.6-terra`, medium reasoning). The coordinating Pi session gives it a bounded, read-only review packet and captures its result in the normal review artifact. Separate Codex or Claude Code sessions and Herdr tabs are not required review transports.

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

### Grok 4.5 context ceiling

The exact `opencode/grok-4.5` model uses an absolute policy rather than the shared percentage backstop. The extension requests pi-vcc compaction at **180,000 tokens** and advertises a **200,000-token** context window. Other providers and Grok model IDs retain the normal 60%/75%/80% percentage policy.

The 200K guarantee applies to the estimated **outbound provider request**: transformed messages, tool definitions, system prompt, and output reservation. It does not promise that the persisted session transcript can never briefly exceed 200K before Pi reaches its next dispatch boundary. A Pi runtime containing the matching pre-dispatch `context_ceiling` gate must compact and rebuild the request, or fail closed without calling Grok, whenever that estimate would be 200,000 tokens or more.

Run `/compact-status` while `opencode/grok-4.5` is selected to see the current token count, 180K trigger, 200K provider-request ceiling, and last compaction reason. If the runtime reports that it cannot make a safe cut at the ceiling, do not retry an oversized request: use `/compact-now` if a safe boundary is available or start a new session. After installing, verify the model override with:

```bash
./install.sh --pi
pi --list-models grok
```

Task tracking is provided exclusively by the package-managed `@tintinweb/pi-tasks` extension. Use `TaskCreate`, `TaskList`, `TaskGet`, and `TaskUpdate` for structured work tracking; `/tasks` is its interactive UI.

This configuration sets pi-tasks to `taskScope: "memory"` globally. Tasks stay available during normal turns and context compactions, but `/new` and a Pi restart clear them; no task files are written in project repositories. To keep persistent task state outside repositories instead, launch Pi with `PI_TASKS` set to a named list (for example, `PI_TASKS=work`) or to an absolute path. Named lists are stored at `~/.pi/tasks/<name>.json`; absolute paths are used verbatim. A named global list is shared by every Pi session that uses it, so it is not automatically isolated by project. `PI_TASKS=off` disables task persistence entirely.

## Subagents

Pi subagents load agent definitions from `~/.pi/agent/agents/`.

## Package-managed Pi extensions

In addition to the repo-managed files under `~/.pi/agent/extensions/`, `install.sh --pi` also registers Pi packages via `pi install` / `pi update`. These are the entries that appear in `pi list`. `pi-multi-pass` is intentionally not installed; multi-account Codex routing is replaced by the single local `openai-codex` CLI Proxy API provider.

npm-managed packages:
- `@tintinweb/pi-subagents`
- `@tintinweb/pi-tasks` — the sole structured task-tracking extension for Pi; the managed default is in-memory, while `PI_TASKS` can select a named list or absolute path for external persistence
- `@aliou/pi-processes`
- `@narumitw/pi-goal`
- `pi-web-access`
- `@fnnm/pi-ast-grep`
- `pi-updater`
- `pi-powerline-footer`
- `pi-no-soft-cursor`
- `@tmustier/pi-files-widget`
- `@tmustier/pi-raw-paste`
- `@pi-kaush/pi-inline-skill-identifier`
- `@howaboua/pi-explore-subagents`
- `pi-service-tier` — service-tier controls, patched during installation for CLIProxyAPI's `openai-responses` Codex route
- `pi-cursor-sdk` — Cursor SDK-backed provider extension; requires Node.js 22.19+ and a Cursor SDK API key

local path packages:
- `~/.pi/agent/local-packages/ai-configs/pi-vcc` (a stable mirror synced from `./_pi/packages/pi-vcc`; install tests and worktrees must not register their transient checkout path)

Use Herdr to launch and manage visible interactive agent sessions.

`@howaboua/pi-codex-conversion` is retired from the managed install; the installer removes stale npm and git registrations.

`@ff-labs/pi-fff` is intentionally retired from the managed install because its native FFF search library can abort the Pi process on macOS during concurrent live grep and filesystem watcher activity.

Use `pi list` on a host to verify what is currently registered. To verify both surfaces together, run `scripts/verify-pi-install.sh` from this repo.

The maintained agent files use the flat frontmatter expected by `@tintinweb/pi-subagents`: every agent has a `name`, and `tools` is a comma-separated Pi tool list when specified.

The installed agent directory is an exact replacement with this roster:

- `planner` — GPT-5.6 Sol medium; planning-only
- `reviewer` — GPT-5.6 Terra medium; read-only material review
- `scout` — GPT-5.6 Terra low; bounded read-only discovery
- `Explore.md` — disabled override, not an active agent

Callers must supply the artifact or allowed surfaces, specialized lens, output destination/format, authority boundary, verification evidence, and stop/verdict vocabulary. There is no implementation subagent: the driving session performs code edits, test changes, fixes, verification, and repository management directly. `/cmd:start-linear-issue` likewise performs its deterministic Git/Linear worktree workflow directly.

## Skills Overview

### Canonical workflow
- `reviewed-html-plan` / `/dev:reviewed-html-plan` — creates/registers HTML plans in Doct, follows returned `listenerInstructions`, starts the durable queue-backed listener, processes browser feedback, runs PM plus the reviewer subagent plan review, and stops at execution-ready handoff

### Dev / execution
- `run-plan` / `/run-plan` — full lifecycle execution for an explicit reviewed plan: durable Pi goal tracking, implementation, scoped reviews, implementation-stage PM review, reviewer-subagent pre-PR review, base freshness, PR creation, current PR feedback snapshot, local merge-readiness consensus, and safe auto-rebase when needed
- `dev:run` — direct GPT-5.6 Sol medium execution with one shared `reviewer` pass after each phase
- `autoreview` — canonical reviewer-subagent pre-PR implementation review with one targeted rereview after fixes and no unresolved blocking in-scope P1/P2 findings; plan-required, verification-required, or regression-caused P3 findings still block. After the bounded three-cycle local budget, unresolved review non-convergence uses exactly one read-only advisory external consultation and, only if authorized, one scope-bound `REVIEW_ESCAPE` adversarial reviewer-pair pass plus the existing single pass-after-fixes allowance. This route applies before or after PR creation and does not require a PR URL or PR feedback. When invoked by `run-plan`, it returns `OPEN_PR_READY` so the caller continues to final verification, base freshness, PR creation, and local merge-readiness checking without waiting for a Codex thumbs-up

### Git / workflow
- `cmd-create-pr`

### Development
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
- `review-change-opus` — compatibility pointer to `/review:change-claude-code`; no provider-specific Pi subagent
- `review-change-claude-code` — compatibility alias that runs the repository-owned Pi `reviewer` subagent; it does not open a Claude Code or Herdr review session
- `autoreview` — runnable independently or automatically from `run-plan` before PR creation; it is not a terminal replacement for PM review, base freshness, opening the PR, or proving local merge readiness
- `pre-pr-implementation-review` — indefinite compatibility alias for `autoreview`; it preserves arguments and the `OPEN_PR_READY` handoff without duplicating the canonical policy

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
/review:change-opus thoughts/plans/my-plan.html
/review:change-claude-code thoughts/plans/my-plan.html
/skill:autoreview thoughts/plans/my-plan.html
/run-plan thoughts/plans/my-plan.html
/dev:plan-from-prd thoughts/plans/prd-my-feature.md
/cmd:send-plan-to-doct thoughts/plans/my-plan.md
```

## Reviewed-plan handoff

Use `/run-plan <plan>` after a reviewed plan is ready for full implementation-through-ready-PR execution: durable Pi goal tracking, implementation, implementation-stage PM review, reviewer-subagent pre-PR review, base freshness, PR creation, current PR feedback snapshot, local merge-readiness consensus, and safe auto-rebase when needed. Use `/dev:run <plan>` only for direct execution without the full PR lifecycle. For browser-reviewed plans, the active artifact is `thoughts/plans/<slug>.html` or the repo-selected Markdoc source, and `skills/doct-document-ops/SKILL.md` is the sole source for concrete Doct plan commands, HTML/Markdoc/Markdown publishing guidance, durable listener startup, readiness metadata, canonical URL rules, and comment mechanics.

Canonical browser-reviewed HTML plan flow:

```text
/dev:plan <plan>
/dev:reviewed-html-plan <plan>    # register, monitor browser comments, PM-review, and run the reviewer-subagent plan review
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
- `/run-plan` is the full lifecycle reviewed-plan continuation through durable Pi goal tracking, PM review, reviewer-subagent pre-PR review, base freshness, PR creation, current PR feedback snapshot, local merge-readiness consensus, and safe auto-rebase when needed; `/dev:run` remains the direct execution-only path with one shared `reviewer` pass after each phase.
- `/skill:autoreview` can be run independently before opening a PR and is also invoked automatically by `run-plan` after scoped implementation reviews. In a scoped run, a clean reviewer-subagent verdict with no unresolved blocking in-scope P1/P2 findings means `OPEN_PR_READY`; plan-required, verification-required, or regression-caused P3 findings remain blocking. The runner must then rerun final verification if needed, confirm base freshness, commit, push, open the PR, and prove local merge readiness without waiting for external approval. `/skill:pre-pr-implementation-review` remains supported indefinitely as a thin argument-preserving compatibility alias.
- In Pi, `/cmd:execute-plan` starts a fresh session and launches the selected execution flow from clean context.
- `/review:change-claude-code` remains available as a compatibility alias; it is not an automatic planning-mode fallback. It runs the repository-owned Pi `reviewer` subagent with the same bounded, read-only packet and never creates a Herdr tab or starts an external Claude Code reviewer.

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
- `/review:prd` runs five distinct reviewer lenses and writes five per-reviewer files under `thoughts/validation/prd-reviews/<prd-slug>/`, integrates the combined findings back into the PRD, keeps `integration-ledger.md` plus `review-status.json`, and removes the five reviewer output files after integration. The final status contract records `reviewersExpected: 5`, `reviewersCompleted: 5`, `integratedCount` from `0` through `5`, `pendingCount: 0`, and `reviewerFilesRemoved: true`.
- `/dev:plan-from-prd` validates that `thoughts/validation/prd-reviews/<prd-slug>/review-status.json` matches that approved five-reviewer contract and is not older than the PRD.
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
/skill:doct-document-ops
/skill:sentry-cli
```

## Notes

- Pi global resources live under `~/.pi/agent/`, not `~/.pi/`.
- Repo-managed extensions live in `~/.pi/agent/extensions/`; package-managed installs are reported by `pi list`.
- `~/.pi/agent/APPEND_SYSTEM.md` is rendered from the repo-root `APPEND_SYSTEM.md` with its install date and source Git SHA recorded on the `Doctrine-Version` line.
- Project-local Pi resources can also live under `.pi/prompts/`, `.pi/skills/`, `.pi/agents/`, and `.pi/extensions/`.
- Pi natively auto-discovers both `~/.agents/skills/` and `~/.pi/agent/skills/`; this repo uses `~/.agents/skills/` as the canonical default shared runtime location and reserves `~/.pi/agent/skills/` for Pi-local-only entries. Repo-owned skill payloads come from `skills/`, while package-backed entries are fetched per `skills/install-matrix.json`. Skills marked `defaultInstall: false` stay in the inventory but are backed out of default discovery to reduce session context.
- `@tintinweb/pi-subagents`-compatible agent definitions install to `~/.pi/agent/agents/`.
- `_pi/agents/Explore.md` is only an `enabled: false` override for tintinweb's bundled `Explore` persona; it does not define a repository-owned Explore persona. It does not affect the separately installed `@howaboua/pi-explore-subagents` extension or its `explore_subagent` tool, which remains the intended isolated-discovery path.
- GPT-5.6 Sol medium in the driving session is the only repository-owned Pi GPT code-writing route. Perform implementation, test changes, fixes, and repository management directly with native tools. Prefer direct targeted reads for discovery; use `explore_subagent` only as a bounded read-only exception when broad discovery materially benefits from isolated context. Never route code-writing through a subagent or persona.

## Supervisor (skills/supervise)

The supervisor is deliberately **not** a `_pi/agents/` persona — it runs as an opt-in top-level Pi process in its own Herdr pane so it can watch a worker session from outside. `run-plan`, `dev:run`, and other execution workflows never launch it automatically; use it only when the operator explicitly requests supervision. Its launch, checkpoint, and shutdown protocol live in `skills/supervise/SKILL.md` (deployed to `~/.agents/skills/supervise/`). The Pi subagent roster (`test_pi_agent_roster.py`) is unaffected.
