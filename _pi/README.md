# Pi Configuration

This directory contains Pi-specific resources:

- `prompts/` — prompt templates exposed as slash commands
- `agents/` — @tintinweb/pi-subagents-compatible agent definitions
- `extensions/` — Pi runtime extensions and utility integrations
- `lib/` — shared import-only TypeScript modules used by extensions; never auto-loaded as extensions
- `models.json` — managed custom model entries merged into Pi's global `models.json`

Repo-owned default Pi/Codex shared skills live in the repo-level `skills/` tree, and `skills/install-matrix.json` also inventories package-backed and optional-profile shared skills fetched via `npx skills`. The installed default shared runtime location remains `~/.agents/skills`.


## Installation

These resources are installed by `install.sh` to Pi's global agent directory. There are three distinct Pi installation surfaces:

- repo-managed extensions: copied from this repo into `~/.pi/agent/extensions/`, including `vent.ts` (shared feedback log at `~/.pi/VENT.md`) and `delivery-reflect.ts` (end-of-run delivery reflections at `~/.pi/DELIVERY_REFLECTIONS.md` + `~/.pi/delivery-reflections.jsonl`)
- repo-managed Pi libraries: copied from `_pi/lib/` into `~/.pi/agent/lib/`; this keeps import-only helpers out of Pi's auto-loaded `extensions/` directory
- repo-managed model entries: merged from `_pi/models.json` into `~/.pi/agent/models.json` without replacing local API keys
- package-managed Pi installs: registered via `pi install` / `pi update` and visible in `pi list`

Plan review and execution use the maintained `reviewed-html-plan` and `run-plan` workflows directly. Rarely used browser/CDP helper skills such as `brave-cdp` and `chrome-cdp` remain inventoried in `skills/install-matrix.json` under the optional `ops-browser` profile and are not loaded into Pi/Codex default context.

`pi list` only shows the package-managed set; it does not list repo-managed files like `simple-multi-status.ts`. See [Package-managed Pi extensions](#package-managed-pi-extensions) below for the exact git and npm package set.

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
├── README.md
├── models.json
├── prompts/
│   ├── cmd:debug.md
│   ├── dev:plan.md
│   └── ...
├── agents/
│   ├── planner.md        # GPT-5.6 Sol medium; planning + independent plan-readiness review
│   ├── reviewer.md       # GPT-5.6 Terra medium; read-only review
│   ├── scout.md          # GPT-5.6 Terra low; read-only discovery
│   └── Explore.md        # disabled bundled persona override
├── extensions/
│   ├── simple-multi-status.ts
│   └── percentage-compaction.ts
└── lib/
    └── grok-context-ceiling-policy.ts
```

Pi does not install an always-on `APPEND_SYSTEM.md`. Older copies under `~/.pi/agent/APPEND_SYSTEM.md` are removed on install. Conditional procedures load through skills; `cmd-create-pr` covers any `gh pr` create, update, comment, or similar mutating PR action, including forks.

The bounded review-stack route is `./install.sh --pi-review-stack`. Its source of truth is `scripts/pi-review-stack-managed-surfaces.json`; install, rollback, and scoped verification expand that same manifest. The route probes effective planner/reviewer isolation, model, reasoning, and target-checkout handling without a model call. Add `--summary-json <path>` for an atomic private install-summary-v1 receipt, or use `scripts/install-pi-transactionally.sh --summary-json <path>` when rollback evidence is required.

The installer also merges `_pi/models.json` into `~/.pi/agent/models.json`, upserting managed model metadata while preserving local provider fields such as API keys except for the repo-owned `openai-codex` provider. Managed overrides expose DeepSeek V4 Flash `max` reasoning on both `deepinfra/deepseek-ai/DeepSeek-V4-Flash-0731` and `opencode/deepseek-v4-flash` (cycle pins remain `:high`; raise thinking to `max` in-session when needed), and cap both routes at a 400k context window instead of Pi's 128k default, which is a conservative size under the model's 1M-token ceiling. `openai-codex` is pinned to the local CLI Proxy API at `http://127.0.0.1:8318/v1` using Pi's `openai-responses` adapter, with Codex model IDs and thinking-level mappings preserved. xAI models use Pi's built-in `xai` provider and the local xAI login; ai-configs does not configure an xAI endpoint, headers, or key, but may upsert missing native model entries (currently `xai/grok-4.6`) into that provider via `_pi/models.json` until a Pi/`pi-ai` release ships them. The managed `xai/grok-4.6` entry advertises a 200k context window rather than the 500k catalog size, and rerunning install repairs a stale 500k window on an existing native entry. Cursor and OpenCode remain separate providers, so removing either removes only that provider's models.

`install.sh --pi` enforces `deepinfra/deepseek-ai/DeepSeek-V4-Flash-0731` as the generic Pi startup/default execution model. The same install copies `_pi/clarify.json` to `~/.pi/agent/clarify.json`, pinning the `pi-clarify` `/clarify` rewrite to that DeepInfra Flash route with thinking off (the extension does not send a thinking level). Delivery and plan-driven implementation override that route to GPT-5.6 Luna at xhigh by default (or GPT-5.6 Terra at high for judgment-heavy correctness), while the web-search summary route stays on GPT-5.6 Terra. The driving Pi session is the primary code-writing route. The planning and review agents use GPT-5.6 Terra medium (pegged by agent frontmatter), the read-only scout uses GPT-5.6 Terra low, and the imaging agent uses GPT-5.6 Luna xhigh for visual analysis when the driving model cannot see images. Vendored `pi-prewalk` (`_pi/packages/pi-prewalk`) can hand mechanical implementation off to a named execution profile at the first `edit`/`write` once a strong model has committed to a plan — defaults to DeepSeek Flash (`flash`), with built-in `terra` / `glm` (`deepinfra/zai-org/GLM-5.2:high`) / `luna` profiles and optional `~/.pi/agent/prewalk-profiles.json` overrides. GPT-5.6 Sol remains available in Pi-scoped model routes for execution workflows, while GLM-5.2 is removed; GPT-5.4 and GPT-5.4-mini are also retired exactly from Pi-owned agents, managed `openai-codex` model entries, and Pi settings aliases while caller-owned providers/models remain untouched.

## Structure

```text
_pi/
├── README.md
├── models.json         # Managed custom model entries merged into ~/.pi/agent/models.json
├── clarify.json        # Managed /clarify rewrite-model pin copied to ~/.pi/agent/clarify.json
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

Planning remains available through prompt templates and shared skills such as `/dev:plan`, `/dev:reviewed-html-plan`, and `/skill:reviewed-html-plan`.

## Extensions

Pi loads runtime extensions from `~/.pi/agent/extensions/`. Every TypeScript file in that directory is auto-loaded and must export an extension factory. Import-only helpers, including the Grok context-ceiling policy used by `percentage-compaction.ts`, live in `~/.pi/agent/lib/` instead.

This repo ships `thinking-shortcuts.ts`, which adds Codex-style bidirectional reasoning controls:

- `Alt+.` increases the current model's thinking level,
- `Alt+,` decreases the current model's thinking level,
- both shortcuts stop at the model's supported boundaries instead of wrapping.

Run `bun test scripts/thinking-shortcuts.test.ts` for the extension contract tests and `scripts/test-thinking-shortcuts-e2e.sh` for the real Pi TUI keypress test.

Install no longer ships `model-allowlist.ts` and clears `enabledModels`, so Pi shows the live catalog instead of a managed picker cycle. The default execution route remains `deepinfra/deepseek-ai/DeepSeek-V4-Flash-0731` with thinking `high`. Install still persists `fastDefaults.grok-4.6=false` so unsuffixed `cursor/grok-4.6` stays plain instead of Cursor's catalog-default Fast variant. Custom model metadata continues to merge from `_pi/models.json`.

The managed `herdr-agent-state.ts` integration reports **interactive Pi TUI** lifecycle state directly to Herdr; RPC, JSON, and print-mode Pi runs never claim the inherited terminal pane. It treats `agent_settled` as the foreground-idle boundary, preserves same-session Herdr authority across Pi `/reload`, `/new`, `/resume`, and `/fork`, and releases it only when Pi quits. It forwards Pi's session-start provenance when Pi provides it so Herdr can re-anchor a replacement runtime, retries a report when a socket closes before acknowledging it, and, by default, keeps the pane working while any tracked `process` job remains live except known passive listeners, monitors, dev servers, and watchers. Configure the policy with `HERDR_PI_BACKGROUND_PROCESS_MODE=none|finite|all`; extend the passive ignore list with comma- or newline-separated literal name/command fragments in `HERDR_PI_BACKGROUND_PROCESS_IGNORE`. Doct `plans listen` and blocking `plans agent next --wait` commands are ignored explicitly. The shared-skills install also places `herdr-operator-attention` in `~/.agents/scripts` and `~/.local/bin`; workflow-owned human waits write a per-pane marker that this integration honors above working/idle while retaining `herdr:pi` authority, and shell-only panes receive a best-effort fixed-source `report-agent` signal. Run `node tests/test_herdr_agent_state.mjs` for the lifecycle, reload, process-policy, and operator-wait latch contract test.

The repo-owned `claude-review` and `codex-review` Pi extensions are temporarily disabled and retained under `_pi/disabled-extensions/` for comparison and possible rollback. `install.sh --pi` removes any stale installed copies from `~/.pi/agent/extensions/`, so the `claude_review` and `codex_review` tools are unavailable after a fresh Pi session starts.

Required Pi plan and code reviews use the repository-owned `reviewer` Pi subagent (`openai-codex/gpt-5.6-terra`, medium reasoning). The coordinating Pi session gives it a bounded, read-only review packet and captures its result in the normal review artifact. A Herdr delivery run also opens a visible adjacent Pi session on `xai/grok-4.6:high` for the separate plan-completeness loop: the driving agent addresses its in-plan findings and requests rereview until it returns `COMPLETE`. That visible reviewer is read-only and does not replace the active-harness code-review gate. Separate Codex or Claude Code sessions remain unnecessary.

This repo also ships `simple-multi-status.ts`, a lightweight multi-line status widget that auto-loads on install and shows:

- the active model,
- token, cache, and cost totals,
- current provider/model status when present,
- current context-window usage,
- the current working directory.

This repo also ships `percentage-compaction.ts`, which provides semantic, extension-only context maintenance:

- sends soft/strong model-visible nudges at 60%/75% so agents can call `compact_context` after a completed subtask or evidence loop,
- records one in-memory semantic request and invokes released Pi's existing `ctx.compact()` only after `agent_settled` reports the session idle,
- never interrupts an active run, sends a continuation message, schedules a retry timer, or starts another provider turn,
- clears pending maintenance on Escape/abort, native compaction, session replacement, and shutdown,
- treats 80% as a warning boundary while released Pi remains authoritative for threshold and overflow recovery,
- provides `/compact-status` for context usage and `/compact-now [instructions]` for immediate idle compaction or settled-run maintenance when active,
- cancels compaction instead of falling back to Pi's default compactor when pi-vcc is not loaded.

To adjust nudge and warning thresholds, edit `COMPACTION_NUDGE_PERCENT`, `COMPACTION_STRONG_NUDGE_PERCENT`, and `HARD_AUTO_COMPACTION_PERCENT` in the extension file.
To install only these managed surfaces, run `./install.sh --pi-vcc`; `pi list` should show the stable mirror under `~/.pi/agent/local-packages/ai-configs/pi-vcc`.

**Note:** Native Pi auto-compaction/overflow recovery remains enabled and owns urgent recovery during a long active run. The vendored package supplies the deterministic `session_before_compact` summary, preserves Pi's native token-bounded recent tail by default, and keeps `/pi-vcc keep:N` as an explicit idle-only override. Rerunning `./install.sh --pi-vcc` refreshes the package and percentage extension without patching Pi or global npm files.

### Grok 4.5 context ceiling

The exact `opencode/grok-4.5` model uses an absolute warning policy rather than the shared percentage warning. At **180,000 tokens** the extension warns that released Pi owns urgent threshold/overflow recovery; it does not interrupt the run or manufacture a continuation. The advertised context window remains **200,000 tokens**. Other providers and Grok model IDs, including Pi's built-in `xai/grok-4.6`, retain the normal 60%/75%/80% nudge/warning policy.

The 200K guarantee applies to the estimated **outbound provider request**: transformed messages, tool definitions, system prompt, and output reservation. It does not promise that the persisted session transcript can never briefly exceed 200K before Pi reaches its next dispatch boundary. A Pi runtime containing the matching pre-dispatch `context_ceiling` gate must compact and rebuild the request, or fail closed without calling Grok, whenever that estimate would be 200,000 tokens or more.

Run `/compact-status` while `opencode/grok-4.5` is selected to see the current token count, 180K trigger, 200K provider-request ceiling, and last compaction reason. If the runtime reports that it cannot make a safe cut at the ceiling, do not retry an oversized request: use `/compact-now` if a safe boundary is available or start a new session. After installing, verify the native xAI catalog with:

```bash
./install.sh --pi
pi --list-models xai
```

Task tracking is provided exclusively by the package-managed `@juicesharp/rpiv-todo` extension. Use its `todo` tool for structured work tracking and `/todos` to inspect the current list. The extension renders a live overlay and replays task state from the conversation across `/reload` and compaction; ai-configs does not manage a task-state file. Optional display and guidance settings live in `~/.config/rpiv-todo/config.json` and are owned by the package user.

## Subagents

Pi subagents load agent definitions from `~/.pi/agent/agents/`.

## Package-managed Pi extensions

In addition to the repo-managed files under `~/.pi/agent/extensions/`, `install.sh --pi` also registers Pi packages via `pi install` / `pi update`. These are the entries that appear in `pi list`. `pi-multi-pass` is intentionally not installed; multi-account Codex routing is replaced by the single local `openai-codex` CLI Proxy API provider.

npm-managed packages:
- `@tintinweb/pi-subagents`
- `@juicesharp/rpiv-todo` — the structured task-tracking extension for Pi; it provides the `todo` tool, `/todos`, and a live overlay that survives `/reload` and compaction
- `@aliou/pi-processes`
- `@aliou/pi-synthetic`
- `@narumitw/pi-goal`
- `@narumitw/pi-btw` — a `/btw` side-question command for Pi
- `pi-web-access`
- `pi-no-soft-cursor`
- `@tmustier/pi-files-widget`
- `@tmustier/pi-raw-paste`
- `@pi-kaush/pi-inline-skill-identifier`
- `@howaboua/pi-explore-subagents`
- `pi-deepinfra` — DeepInfra provider for Pi (dynamic model catalog, reasoning-effort thinking, vision, usage/billing footer)
- `pi-updater` — codex-style auto-updater for Pi; checks pi and extension packages on startup and prompts to install updates
- `pi-clarify` — `/clarify` prompt rewriter; install copies `_pi/clarify.json` so rewrites use DeepInfra DeepSeek V4 Flash with thinking off
- `pi-prewalk` (vendored) — lets a strong model commit to a plan, then hands mechanical implementation off to a configured execution profile (model + thinking level) at the first `edit`/`write` (todo-gated one-way switch). Arm with `--prewalk`, `--prewalk-into <profile|model>`, `/prewalk`, `/prewalk terra`, or `/prewalk profiles`. Source: `_pi/packages/pi-prewalk`; user overrides: `~/.pi/agent/prewalk-profiles.json`.
- `pi-extensible-workflows` — multi-agent workflow orchestration (`workflow` tool, parallel/pipeline, checkpoints, worktrees)
- `pi-cursor-sdk` — Cursor SDK-backed provider extension; requires Node.js 22.19+ and a Cursor SDK API key. ai-configs vendors its reviewed fork and installs production dependencies into a stable local mirror. Its interactive `cursor_ask_question` bridge is disabled by default; set `PI_CURSOR_ASK_QUESTION=1` for an explicit one-run opt-in.

local path packages:
- `~/.pi/agent/local-packages/ai-configs/pi-vcc` (a stable mirror synced from `./_pi/packages/pi-vcc`; install tests and worktrees must not register their transient checkout path)
- `~/.pi/agent/local-packages/ai-configs/pi-cursor-sdk` (a stable mirror synced from `./_pi/packages/pi-cursor-sdk`, with `pnpm install --prod --ignore-scripts --frozen-lockfile` run after copying; source provenance is recorded in `VENDORED_FROM.md`)

Use Herdr to launch and manage visible interactive agent sessions.

`@howaboua/pi-codex-conversion` is retired from the managed install; the installer removes stale npm and git registrations.

`@ff-labs/pi-fff` is intentionally retired from the managed install because its native FFF search library can abort the Pi process on macOS during concurrent live grep and filesystem watcher activity.

Use `pi list` on a host to verify what is currently registered. To verify both surfaces together, run `scripts/verify-pi-install.sh` from this repo.

The maintained agent files use the flat frontmatter expected by `@tintinweb/pi-subagents`: every agent has a `name`, and `tools` is a comma-separated Pi tool list when specified.

The installed agent directory is an exact replacement with this roster:

- `oracle` — GPT-5.6 Sol high; inherited-context, read-only decision support for risky, ambiguous, drifting, or non-converging choices
- `planner` — GPT-5.6 Sol medium; planning plus independent read-only plan-readiness review
- `reviewer` — GPT-5.6 Terra medium; read-only material review
- `scout` — GPT-5.6 Terra low; bounded read-only discovery
- `imaging` — GPT-5.6 Luna xhigh; read-only visual analysis for non-vision models
- `Explore.md` — disabled override, not an active agent

`oracle`, `planner`, and `reviewer` declare `isolation: none`. `imaging` also declares `isolation: none` so it can read live checkout files and Pi clipboard image paths. During Pi installation, `scripts/patch_pi_subagents_review_isolation.py` extends `@tintinweb/pi-subagents` with that authoritative sentinel, rewrites Agent-tool guidance to stop advertising worktree isolation for those personas, and strips caller `isolation: "worktree"` (plus Oracle `inherit_context: false` / non-high `thinking`) before spawn so runtime stays on the live inherited checkout even when a model still emits bad args. Review and Oracle skills still require callers to omit those properties; the patch is a hard backstop and is reapplied after package updates. Oracle also pins inherited parent context so it can reconstruct established decisions and detect drift rather than acting as a generic fresh-context reviewer. Its frontmatter deliberately carries both the current tintinweb keys (`thinking: high`, `inherit_context: true`) and nicobailon's equivalent fork-context key (`defaultContext: fork`), alongside the repository's `reasoningEffort: high` policy marker. This keeps the new Oracle's core model/context contract executable now and compatible with the planned orchestrator migration.

**Oracle caller launch contract:** pass only `subagent_type: "oracle"`, a short description, and the decision prompt. Omit caller-side `model`, `thinking`, `reasoningEffort`, `inherit_context`, and `isolation`. Setting `inherit_context: false` or `isolation: "worktree"` is a workflow violation even when transport prefers persona defaults. Invoke Oracle proactively on trigger-class ambiguity without waiting for the operator to request it. After return, record disposition (`accepted` / `partially-accepted` / `rejected` / `escalated`) with why.

Callers must supply the artifact or allowed surfaces, specialized lens, output destination/format, authority boundary, verification evidence, and stop/verdict vocabulary. Oracle callers additionally supply one bounded decision, credible options, the driving agent's current recommendation, uncertainty, and one narrow question ending with `?`. There is no implementation **subagent**: the active driving session performs code edits, test changes, fixes, verification, and repository management directly. Delivery approval creates a new top-level Herdr Pi driving session pinned to the planner-selected implementation profile (Luna xhigh by default, Terra high for judgment-heavy correctness); it does not delegate edits through the `Agent` subagent tool. `/cmd:start-linear-issue` likewise performs its deterministic Git/Linear worktree workflow directly.

## Skills Overview

### Canonical workflow
- `reviewed-html-plan` / `/dev:reviewed-html-plan` — creates/registers HTML plans in Doct, follows returned `listenerInstructions`, starts the durable queue-backed listener, processes browser feedback, and runs PM plus the independent Sol-medium `planner` subagent review. In a delivery-managed Herdr run, `delivery stage EXECUTION_READY` then automatically authorizes the exact reviewed plan and launches the planner-selected GPT-5.6 Luna xhigh or Terra-high implementation profile without another routine approval pause; planning-only use still stops at the execution-ready plan.

### Dev / execution
- `run-plan` / `/run-plan` — full lifecycle execution for an explicit reviewed plan. In a delivery run it is invoked only from the dedicated recorded implementation pane. The Sol planner recommends `openai-codex/gpt-5.6-luna` at xhigh by default, or `openai-codex/gpt-5.6-terra` at high when correctness depends materially on technical judgment. Unresolved consequential choices can escalate to Oracle; Sol is not used for implementation. This is a default, not a prohibition: a manual model/reasoning choice may be recorded at approval or adopted in the same implementation pane with a reason. Implementation then proceeds through scoped reviews, implementation-stage PM review, Terra-medium reviewer-subagent pre-PR review, then base freshness, PR creation, current PR feedback snapshot, local merge-readiness consensus, and safe auto-rebase when needed
- `dev:run` — direct GPT-5.6 Luna xhigh execution by default, with Terra high for judgment-heavy correctness and one shared `reviewer` pass after each phase
- `autoreview` — canonical reviewer-subagent pre-PR implementation review with one targeted rereview after fixes and no unresolved blocking in-scope P1/P2 findings; plan-required, verification-required, or regression-caused P3 findings still block. After the bounded three-cycle local budget, unresolved review non-convergence uses exactly one read-only advisory consultation through Pi's Sol-high `oracle` and, only if authorized, one scope-bound `REVIEW_ESCAPE` adversarial reviewer-pair pass plus the existing single pass-after-fixes allowance. This route applies before or after PR creation and does not require a PR URL or PR feedback. When invoked by `run-plan`, it returns `OPEN_PR_READY` so the caller continues to final verification, base freshness, PR creation, and local merge-readiness checking without waiting for a Codex thumbs-up

### Git / workflow
- `cmd-create-pr`
- `safe-git-index` — loaded before index-mutating Git commands or lock recovery

### Development
- `dev-plan`
- `integration-integrity` — loaded for exact non-type-checked contracts or behavior distributed across production sites
- `oracle-consultation` — loaded proactively when targeted evidence leaves a consequential choice unresolved
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
/consult:oracle choose ownership boundary for retry policy
/dev:plan feature-name
/dev:reviewed-html-plan feature-name
/dev:pm-review thoughts/plans/my-plan.html
/dev:pm-review thoughts/plans/my-plan.html implementation
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

Use `/run-plan <plan>` after a reviewed plan is ready for full implementation-through-ready-PR execution: durable Pi goal tracking, implementation, implementation-stage PM review, reviewer-subagent pre-PR review, base freshness, PR creation, current PR feedback snapshot, local merge-readiness consensus, and safe auto-rebase when needed. Use `/dev:run <plan>` only for direct execution without the full PR lifecycle. For browser-reviewed plans, the active artifact is `thoughts/plans/<slug>.html`, and `skills/doct-document-ops/SKILL.md` is the sole source for concrete Doct plan commands, HTML publishing guidance, durable listener startup, readiness metadata, canonical URL rules, and comment mechanics. Do not produce Markdoc plans.

Canonical browser-reviewed HTML plan flow:

```text
/dev:plan <plan>
/dev:reviewed-html-plan <plan>    # browser comments + PM review + independent Sol-medium planner review
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

The sequence below is the end-to-end reviewed-PRD path from a PRD delta through handoff. Use `/prd:clarify-round` until clarification is complete before running `/review:prd`.

```text
/prd:clarify-round thoughts/plans/prd-my-feature.md
/review:prd thoughts/plans/prd-my-feature.md
/dev:plan-from-prd thoughts/plans/prd-my-feature.md
```

- `/dev:plan-from-prd` is the canonical wrapper for turning a reviewed PRD delta into a fresh single-file plan session.
- The typical sequence is update the PRD with the latest user answers → `/prd:clarify-round` → repeat that clarification loop as needed → `/review:prd` when a wider review is worthwhile → `/dev:plan-from-prd <prd>` after an approved review result.
- `/review:prd` is the explicit review gate before `/dev:plan-from-prd`.
- `/review:prd` runs five distinct reviewer lenses and writes five per-reviewer files under `thoughts/validation/prd-reviews/<prd-slug>/`, integrates the combined findings back into the PRD, keeps `integration-ledger.md` plus `review-status.json`, and removes the five reviewer output files after integration. The final status contract records `reviewersExpected: 5`, `reviewersCompleted: 5`, `integratedCount` from `0` through `5`, `pendingCount: 0`, and `reviewerFilesRemoved: true`.
- `/dev:plan-from-prd` validates that `thoughts/validation/prd-reviews/<prd-slug>/review-status.json` matches that approved five-reviewer contract and is not older than the PRD.
- If the latest review result for the same PRD is `needs_changes`, resolve the inline `[REVIEW:...]` comments in that PRD and rerun `/review:prd <prd-path>`.
- If the latest review result for the same PRD is `review_failed`, inspect `thoughts/validation/prd-reviews/<prd-slug>/integration-ledger.md` for the failed reviewer row(s) and notes, resolve the failed review-cycle cause(s), and rerun `/review:prd <prd-path>`.
- If the latest review result for the same PRD is stale, or the same PRD does not yet have a current approved review result, rerun `/review:prd <prd-path>` before handoff.
- `/review:prd` is explicit and should happen only once the intent is clarified.
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
- Project-local Pi resources can also live under `.pi/prompts/`, `.pi/skills/`, `.pi/agents/`, and `.pi/extensions/`.
- Pi natively auto-discovers both `~/.agents/skills/` and `~/.pi/agent/skills/`; this repo uses `~/.agents/skills/` as the only skill runtime location so OMP and Pi discover the same skills. During skill sync, valid Pi-local skills are promoted into `~/.agents/skills/`, conflicts are backed up in favor of the shared copy, and stale or dangling Pi-local entries are removed. Repo-owned skill payloads come from `skills/`, while package-backed entries are fetched per `skills/install-matrix.json`. Skills marked `defaultInstall: false` stay in the inventory but are backed out of default discovery to reduce session context.
- `@tintinweb/pi-subagents`-compatible agent definitions install to `~/.pi/agent/agents/`. The global `oracle` and `imaging` agents are available to ordinary Pi sessions and delivery workflows. Load `oracle-consultation` proactively for consequential unresolved choices and invoke `imaging` when the current model cannot see visual input; `/consult:oracle <decision>` is the explicit Oracle shortcut.
- `_pi/agents/Explore.md` is only an `enabled: false` override for tintinweb's bundled `Explore` persona; it does not define a repository-owned Explore persona. It does not affect the separately installed `@howaboua/pi-explore-subagents` extension or its `explore_subagent` tool, which remains the intended isolated-discovery path.
- For delivery and plan-driven execution, GPT-5.6 Luna xhigh in the driving session is the default repository-owned Pi GPT code-writing route. Use GPT-5.6 Terra high when correctness depends materially on technical judgment; unresolved consequential choices can escalate to Oracle. Perform implementation, test changes, fixes, and repository management directly with native tools. Prefer direct targeted reads for discovery; use `explore_subagent` only as a bounded read-only exception when broad discovery materially benefits from isolated context. Never route code-writing through a subagent or persona.

## Supervisor (skills/supervise)

The supervisor is deliberately **not** a `_pi/agents/` persona — it runs as an opt-in top-level Pi process in its own Herdr pane so it can watch a worker session from outside. `run-plan`, `dev:run`, and other execution workflows never launch it automatically; use it only when the operator explicitly requests supervision. Its launch, checkpoint, and shutdown protocol live in `skills/supervise/SKILL.md` (deployed to `~/.agents/skills/supervise/`). The Pi subagent roster (`test_pi_agent_roster.py`) is unaffected.
