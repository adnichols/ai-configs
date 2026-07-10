# Architectural Decision Records

This document captures key architectural decisions and their rationale.

## ADR 0003: Provision the curated `lsp-pi` server subset in the installer instead of forking `lsp-pi`
**Status:** Superseded (removed from setup 2026-04-12)
**Date:** 2026-04

**Context:** The repo already installed `npm:lsp-pi`, but it did not provision the language-server binaries that current `lsp-pi` expects to find on `PATH` or in its small set of hardcoded search directories. That left Pi's `lsp` tool present but inconsistently useful across hosts. The open question was whether to copy OpenCode's more expansive provisioning model immediately, which would likely require extending or forking `lsp-pi`.

**Decision:**
- Add installer-side curated provisioning in `install.sh` for only the npm-manageable server subset that current `lsp-pi` already knows how to spawn: TypeScript, Vue, Svelte, and Pyright.
- Install global `typescript` as a runtime fallback package for TypeScript-family workspaces that do not provide a local `typescript` dependency.
- Gate curated provisioning on npm preflight proving that the resulting global binaries will already be discoverable by current `lsp-pi` search rules.
- Extend `scripts/verify-pi-install.sh` so it separately verifies Pi package registration, curated preflight/binary usability, and unmanaged informational server surfaces.
- Add a canonical TypeScript smoke fixture for end-to-end Pi `lsp` validation.
- Stop after the installer-first solution; do not add a private managed LSP directory, lazy runtime installs, or a vendored/forked `lsp-pi` in Phase 1.

**Alternatives considered:**
- Vendor or fork `lsp-pi` immediately so the repo can manage a private `~/.pi/.../lsp/bin` directory.
- Expand Phase 1 to include Astro, YAML, Bash, Dockerfile, or more toolchain-backed servers.
- Mutate user shell startup files so npm global bins become discoverable automatically.
- Treat `lsp-pi` package registration alone as sufficient verification.

**Current state:**
- Historical record only; the active installer and verification flow no longer install or validate `lsp-pi`.
- `thoughts/fixtures/lsp/typescript-smoke/index.ts`
- `thoughts/fixtures/lsp/typescript-smoke/tsconfig.json`
- `spec/architecture/pi-lsp-provisioning-strategy.md`

---

## ADR 0002: Add an OpenCode-native `review:plan` wrapper on top of existing reviewer surfaces
**Status:** Retired (historical)
**Date:** 2026-04

**Context:** OpenCode already had stronger single-reviewer review commands (`review:change-gpt` and `review:change-k2.5`) but lacked an explicit `review:plan` entrypoint. Pi had a reviewed-plan wrapper, but its prompt depended on Pi-specific reviewer agents, model strings, and transport assumptions that should not be copied into OpenCode unchanged.

**Decision:**
- Add `_opencode/commands/review:plan.md` as a review-only wrapper command instead of replacing the existing `review:change*` commands.
- Reuse the existing OpenCode reviewer agents `reviewer-gpt` and `reviewer-kimi` plus their current provider/model configuration.
- Normalize the reviewed plan path once, launch both reviewer legs in parallel with `Task`, wait for both results, and stop before `/review:change-integrate`.
- Report reviewer-leg failures explicitly instead of silently falling back to another reviewer.

**Alternatives considered:**
- Copy `_pi/prompts/review:plan.md` literally, including Pi-only `reviewer-plan-*` agents and Pi model/provider strings.
- Add compatibility aliases such as `review:change-kimi.md` as part of the same change.
- Expand the change to include adversarial review, PRD workflow parity, or Pi interactive review transports.

**Current state:**
- Historical record only. The `_opencode/` source tree and installer support were removed in July 2026.
- See `spec/architecture/opencode-review-plan-wrapper.md` for the retired design.

---

## ADR 0001: Add first-class issue attachment retrieval to ltui
**Status:** Accepted (implemented and verified)
**Date:** 2026-04

**Context:** `ltui` needed a deterministic way for agents to discover screenshots and other issue assets from Linear issues. The original working plan also needed JSON-safe pagination metadata for list-style JSON output and a safe way to download image assets locally.

**Decision:**
- Model issue assets as a union of Linear attachment nodes and `uploads.linear.app` URLs discovered in issue descriptions and comments.
- Extend `ltui issues view` with explicit attachment/image guidance fields rather than requiring agents to infer image availability from free-form text.
- Use a JSON envelope with `meta` and `rows` for paginated JSON list output.
- Keep downloads opt-in and enforce path, size, timeout, and symlink safety checks.

**Alternatives considered:**
- Keep `issues view` unchanged and require agents to scrape markdown or comments.
- Support only `issue.attachments()` and ignore uploaded file URLs embedded in descriptions/comments.
- Retain plaintext pagination headers for paginated JSON output instead of emitting a JSON envelope.

**Current state:**
- `tools/ltui/src/commands/issues.ts`
- `tools/ltui/src/format.ts`
- `tools/ltui/src/__tests__/cli-regression.test.ts`
- `tools/ltui/src/__tests__/output.test.ts`

---

<!--
Entries are prepended by /cmd:graduate after completing features.
Format:
## ADR NNNN: [Decision Title]
**Status:** Accepted
**Date:** YYYY-MM

**Context:** ...
**Decision:** ...
**Alternatives considered:** ...
**Current state:** ...
-->
