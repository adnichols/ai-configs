# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added

- Allowlisted DeepInfra Kimi K3 (`deepinfra/moonshotai/Kimi-K3`) for direct selection and upserted it into managed `models.json` so it appears in the Pi picker. It stays outside the managed Pi `enabledModels` cycle.

- Added a Pi `imaging` subagent on GPT-5.6 Luna xhigh so non-vision models can proactively hand screenshots and other visual input to a vision-capable analyst instead of guessing.

- Vendored the `cobanov.herdr-ntfysh` Herdr plugin into `tools/herdr-ntfysh` (pinned upstream commit) with two added capabilities: notification titles now use the agent's human-readable session title (`agent get` name, else pane terminal title) instead of bare agent/pane IDs, and `HERDR_NTFY_BODY_LINES=N` appends the last N lines of the agent pane's recent output to the notification body. Both fail safe when the Herdr CLI is unreachable. `herdr/install.sh` now builds, links, and enables the vendored copy (replacing any upstream GitHub-managed install), and keeps the existing plugin config (`.env`) intact.

- Permanent-document disposition in the shared pre-PR path: `run-plan` and `cmd-create-pr` hard-stop when a repo-local permanent-docs skill is present; `delivery-run` records recommended `permanentDocs` evidence and completeness prompt coverage; `cmd-graduate` stays generic with a pointer to local `*-permanent-docs`; `autoreview` accepts caller-supplied disposition in the packet baseline. Pairs with Heddle `heddle-permanent-docs`.
- Tracked Amp CLI config under `amp/` (`settings.json` + `plugins/subscription-models.ts` ADN/Grok modes), with local install via `amp/install.sh` / `install.sh --tools` and macOS remote streaming to `mbp`/`dever`/`mbp14`.

### Fixed

- Added shared `completeness` skill so `skill://completeness` resolves and OMP can launch request-bound `@completeness` review instead of failing on a missing skill.
- Restored Herdr Option/Alt+`[` / `]` tab switching over mosh by having Kitty inject complete xterm modifyOtherKeys sequences (`CSI 27;3;91/93 ~`). Bare `ESC [` / `ESC ]` never complete as alt-bracket events in Herdr's legacy framer, and Kitty `send_key` does not survive mosh.

### Changed

- Synced managed OMP `config.yml` from this host: default is `xai-oauth/grok-4.6:high`. Captured `architect-grok`, `architect-kimi`, and `reviewer-kimi` roles from this host.
- Synced managed OMP `config.yml` from this host: `vision`/`plan`/`designer` are `openai-codex/gpt-5.6-sol` (medium/high/high), `commit` is `openai-codex/gpt-5.6-sol:medium`, `tiny` is `deepinfra/deepseek-ai/DeepSeek-V4-Flash-0731:low`, `reviewer` is `xai-oauth/grok-4.6:high`. Cycle includes Oracle; retry fallbacks are Oracle→Sol and advisor→`cursor/cursor-grok-4.6`.

- Synced managed OMP `config.yml` from this host: `slow` is `openai-codex/gpt-5.6-sol:high`, `plan` is `openai-codex/gpt-5.6-sol:xhigh`, `reviewer` is `xai-oauth/grok-4.6:xhigh`, `completeness` is `xai-oauth/grok-4.6:high`. Dropped unused `cursork3` role.

- Synced managed OMP `config.yml` from this host: `smol` is `deepinfra/deepseek-ai/DeepSeek-V4-Flash-0731:max`, `plan` and `Oracle` are `cursor/kimi-k3-max:max`, advisor is `xai-oauth/grok-4.6:high`.

- Synced managed OMP `config.yml` from this host: `ask.enabled` is false.

- Synced managed OMP `config.yml` from this host: advisor is `cursor/kimi-k3-high:high`; setupVersion 2; composer shape claude; status line powerline-thin; spelling and emoji autocomplete off; openai/anthropic tiers none.

- Pointed OMP Lite implementation doctrine at the configured default `xai-oauth/grok-4.6:medium` instead of Luna xhigh. The OMP planner no longer selects a Pi `luna-xhigh` implementation profile.

- Synced managed OMP `config.yml` from this host: `smol` is `xai-oauth/grok-4.6:medium`, `reviewer` is `cursor/kimi-k3-high:high`.

- Pointed the managed OMP `planner` agent at the `@plan` role instead of a hardcoded Sol-medium model.
- Synced managed OMP `config.yml` from this host: `slow` is `cursor/kimi-k3-max:max`, `plan` is `xai-oauth/grok-4.6:high`, advisor is `xai-oauth/grok-4.6:medium`.
- Synced managed OMP `config.yml` from this host: default is `xai-oauth/grok-4.6`, advisor is `xai-oauth/grok-4.6:high`, Oracle is `fireworks/kimi-k3:max`, slow is `openai-codex/gpt-5.6-sol:high`.
- Synced managed OMP `config.yml` from this host: ast-grep, computer use, GitHub, and security tools off; interrupt mode immediate.
- Synced managed OMP `config.yml` from this host: reviewer is `xai-oauth/grok-4.6:medium`, thinking blocks hidden, personality pragmatic.
- Synced managed OMP `config.yml` from this host: computer use on, bash auto-background off, AutoQA off, task effort off, Herdr worktree base, and GitHub/security tools on.
- Trimmed managed OMP `AGENTS.md` to OMP-specific authority, agent routing, delivery activation, and secret-handling rules not already covered by OMP's default system prompt or this repository's own guidance.
- Capped managed `xai/grok-4.5` at a 200k context window instead of the 500k catalog size, and pinned unsuffixed `cursor/grok-4.5` to plain (not Cursor Fast or the `:fast`/`:slow` aliases).

- Pointed every managed xAI Grok pin at `xai/grok-4.5`, including the Pi model cycle, completeness review, Amp ADN Alt, and OMP completeness. Cursor cycles `cursor/grok-4.5`; both routes are allowlisted. Synthetic Kimi K3 (`synthetic/hf:moonshotai/Kimi-K3`) is allowlisted again for direct selection.
- Pinned Pi `/clarify` (`pi-clarify`) to DeepInfra DeepSeek V4 Flash via `_pi/clarify.json`, and install that package plus the pin on `install.sh --pi`.

- Centralized bounded Pi review-stack install, rollback, and verification surfaces in one validated manifest, with deterministic planner/reviewer transport probing and atomic private JSON receipts for local, transactional, and remote-host runs.
- Added revision-checked blocking delivery-ledger writes, diagnostic completeness-response parsing, and install-receipt references that coexist in the delivery ledger.
- Strengthened run-plan strict-suite partitioning, bounded failure inventory, owned scratch, and final committed-candidate checks; replaced the universal Socratic questionnaire with conditional evidence in existing plan-review sections.

### Removed

- Removed leftover Gemini CLI surfaces: root `GEMINI.md`, `_claude/commands/review:change-gemini.md`, and `scripts/gemini-review.sh`.

## [Retire pi-side-agents] - 2026-07-16

### Removed

- Removed `pi-side-agents` from the managed Pi package set.
- Added installer cleanup and verification so existing host registrations are removed on the next `install.sh --pi` run.

## [Retire legacy configuration surfaces] - 2026-07-09

### Removed

- Removed the `_gemini/`, `_omp/`, and `_opencode/` source trees and their installer modes.
- Removed the repo-managed Pi `pi-plan-mode` extension; planning remains available through maintained prompts and shared skills.
- Removed the retired `omp-review-partner` shared skill and added managed-install cleanup for existing copies and compatibility links.

### Changed

- Default and `--all` installation now cover Claude, Codex, Pi, shared skills, and optional tools only.
- Updated README, setup, Pi, agent, architecture, ADR, changelog, and Hermes workflow guidance to reflect the maintained surfaces.
- OpenCode-based Hermes workflows are now explicitly compatibility-only and require independent component preflight; maintained Pi/Codex workflows are the fallback.
- Ambiguous user-modified Gemini, OMP, OpenCode, and Pi plan-mode runtime files are preserved for explicit host cleanup rather than deleted automatically.

## [Pi LSP provisioning strategy] - 2026-04-08

### Added

- Added installer-side curated `lsp-pi` provisioning in `install.sh` for TypeScript, Vue, Svelte, Pyright, and a global `typescript` runtime fallback.
- Added `thoughts/fixtures/lsp/typescript-smoke/` as the canonical end-to-end Pi `lsp` smoke fixture.
- Added `spec/architecture/pi-lsp-provisioning-strategy.md` as the permanent architecture record for this work.

### Changed

- `scripts/verify-pi-install.sh` now distinguishes Pi package registration, curated LSP preflight/probes, and unmanaged informational server surfaces.
- Pi installation docs now describe the curated subset, npm prefix/PATH prerequisites, degraded TypeScript fallback semantics, and explicit Phase 1 non-goals.

### Technical Notes

- npm prefix/bin detection now uses `npm prefix -g` with `npm config get prefix` fallback because npm 11 on the execution host no longer supports `npm bin -g`.
- Verified with repeated `bash install.sh --pi` reruns, explicit preflight-failure simulation, `bash scripts/verify-pi-install.sh`, and a live Pi `lsp` smoke test against the TypeScript fixture.
- The implementation deliberately keeps `lsp-pi` unforked and leaves runtime-managed/private-bin provisioning as a future opt-in decision.

## [OpenCode `review:plan` wrapper] - 2026-04-06

> **Retired:** The `_opencode/` source tree and installer support were removed in July 2026. This entry is retained as release history only.

### Added

- Added `_opencode/commands/review:plan.md` as a first-class OpenCode reviewed-plan entrypoint.
- The new wrapper normalizes a single plan path, launches the existing GPT and Kimi review legs in parallel, and returns a combined review-only summary.

### Changed

- At the time, the OpenCode reviewed-plan flow became discoverable without requiring users to invoke the lower-level `review:change*` surfaces directly.
- Runtime verification established that command changes needed installation into `~/.config/opencode/commands` before `opencode run` saw them.

### Technical Notes

- The wrapper intentionally reuses `_opencode/commands/review:change-gpt.md`, `_opencode/commands/review:change-k2.5.md`, `reviewer-gpt`, and `reviewer-kimi` instead of adding Pi-specific `reviewer-plan-*` agents.
- Verified against the completed plan and live CLI behavior; the wrapper launched both review legs and stopped before integration, while the Kimi leg failed in this environment with `ProviderModelNotFoundError` and is documented as an operational constraint.

## [ltui image attachments] - 2026-04-03

### Added

- Added `ltui issues attachments <issue>` for deterministic asset discovery across Linear attachments and `uploads.linear.app` links found in issue descriptions/comments.
- Added `ATTACHMENTS_PRESENT`, `IMAGE_ATTACHMENTS_PRESENT`, `IMAGE_ATTACHMENTS_FETCH_CMD`, and `IMAGE_ATTACHMENTS_DOWNLOAD_CMD` fields to `ltui issues view`.

### Changed

- Paginated JSON list output now uses a JSON envelope with `meta` and `rows` instead of plaintext pagination headers for JSON mode.
- Linear skill docs now include attachment retrieval/download examples and an explicit untrusted-file warning.

### Technical Notes

- Downloads are opt-in, streamed to disk, guarded against unsafe paths/symlinks, and capped by timeout and max-size checks.
- Verified with `bun run test` in `tools/ltui`, including attachment and JSON-envelope regression coverage.

<!--
Entries are added by /cmd:graduate after completing features.
Format:
## [Feature Name] - YYYY-MM-DD
### Added/Changed/Fixed
- Description of change
-->
