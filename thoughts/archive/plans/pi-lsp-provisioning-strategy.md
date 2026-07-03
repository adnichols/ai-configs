# Pi LSP Provisioning Strategy

## Status

graduated

## Goal

Improve Pi's out-of-the-box LSP coverage in this repo by extending `install.sh` to provision a curated set of language-server binaries that current `lsp-pi` actually consumes, while avoiding an immediate fork/vendor of `lsp-pi`.

## Why this plan exists

The current `ai-configs` installer registers `lsp-pi`, but it does not provision the language-server binaries that `lsp-pi` expects to find. As a result, Pi exposes an `lsp` tool whose useful coverage depends on whatever binaries already happen to be installed on the host.

The user asked whether this repo can adopt OpenCode-style LSP provisioning and whether that implies vendoring `lsp-pi`. Discovery shows we can get most of the user-visible value with a simpler installer-first approach:
- provision only the small subset of servers that current `lsp-pi` already knows how to spawn,
- install those servers into npm global locations only when the resulting binaries will actually be discoverable by `lsp-pi`,
- strengthen verification so the repo can tell the difference between `lsp-pi` being registered and LSP binaries actually being usable,
- defer any runtime-managed/private-bin design until there is an explicit need for it.

## Authority and inputs

Primary authority:
- User request in this session
- Root `AGENTS.md`
- Shared planning doctrine from `/home/anichols/.agents/skills/planning-workflow/SKILL.md`
- Shared product doctrine from `/home/anichols/.agents/skills/product-principles/SKILL.md`

Evidence read:
- `install.sh`
- `scripts/verify-pi-install.sh`
- `/home/linuxbrew/.linuxbrew/lib/node_modules/lsp-pi/package.json`
- `/home/linuxbrew/.linuxbrew/lib/node_modules/lsp-pi/lsp-core.ts`
- `anomalyco/opencode/packages/opencode/src/lsp/server.ts` (via fetched GitHub source)
- `anomalyco/opencode/packages/opencode/src/global/index.ts` (via fetched GitHub source)

Product/planning guidance status:
- `thoughts/specs/product_intent.md` is absent.
- `thoughts/plans/AGENTS.md` is absent.
- This plan therefore aligns directly to the active user request, root `AGENTS.md`, and shared planning/product doctrine.

## Current implementation reality

### Repo installer behavior today
- `install.sh` installs Pi packages including `npm:lsp-pi`.
- `scripts/verify-pi-install.sh` verifies only that `lsp-pi` is registered with Pi.
- Neither file provisions or verifies the underlying language-server binaries required by `lsp-pi`.

### `lsp-pi` runtime behavior today
- `lsp-pi` advertises support for Dart/Flutter, TypeScript/JavaScript, Vue, Svelte, Python, Go, Kotlin, Swift, and Rust.
- Its active `LSP_SERVERS` list currently wires these commands:
  - `dart`
  - `typescript-language-server`
  - `vue-language-server`
  - `svelteserver`
  - `pyright-langserver`
  - `gopls`
  - `kotlin-lsp` / `kotlin-language-server`
  - `sourcekit-lsp`
  - `rust-analyzer`
- It contains a `.astro` language-id mapping but no actual Astro server entry in `LSP_SERVERS`.
- It does **not** include YAML, Bash, or Dockerfile language servers today.
- Its server lookup is primarily `PATH`-based, with extra search coverage for standard toolchain dirs such as:
  - `$HOME/.cargo/bin`
  - `$HOME/go/bin`
  - `$HOME/.pub-cache/bin`
- It does **not** include a generic managed `~/.pi/.../lsp/bin` search path.
- It contains custom runtime install logic only for Kotlin (`kotlin-lsp`), not for the rest of the matrix.

### Machine/tooling state observed during discovery
- Present on this machine: `bun`, `npm`, `python3`, `cargo`, `rustup`
- Absent on this machine: `go`, `dotnet`, `gem`, `dart`, `swift`, `xcrun`
- Currently visible binaries from the current `lsp-pi` matrix: `typescript-language-server`, `rust-analyzer`

### OpenCode packaging model relevant to this decision
OpenCode does not truly bundle all LSP binaries into its main binary. It lazily provisions them using a mix of:
- Bun/npm installs for JS servers,
- toolchain-native install commands (`go install`, `dotnet tool install`, `gem install`),
- direct archive downloads for native binaries,
- and PATH-only lookup for some toolchain-provided servers.

That model provides strong UX, but it also requires substantial per-language installer/runtime logic, release-asset maintenance, and cross-platform edge-case handling.

## Progress

- [x] P1 Add installer-side curated provisioning
- [x] P2 Extend verification semantics and docs
- [x] P3 Re-review and decide whether a runtime-managed follow-up is still necessary

## Resume instructions (agent)

Read this document fully. Start with the first unchecked item in `## Progress`. Execute phases in order. Keep Phase 1 scoped to installer-first provisioning for the locked curated subset below. Do not vendor or fork `lsp-pi` unless new repo evidence disproves the locked assumption that standard discoverable global installs are sufficient for that subset.

## Product intent alignment

This plan follows the golden-path-first doctrine:
- the default Pi install path should make the currently supported common LSP workflows work without hidden extra setup,
- the installer should provision what it can safely provision using already-supported package managers,
- unsupported or undiscoverable setups should fail with actionable guidance rather than quietly pretending full coverage exists,
- verification should distinguish between `lsp-pi` being registered and actual server binaries being usable end-to-end.

This plan intentionally avoids a Phase 1 architecture where the repo becomes a cross-platform LSP package manager. That keeps the default path maintainable and reduces blast radius.

## Locked decisions

1. Phase 1 will **not** vendor or fork `lsp-pi`.
2. Phase 1 will only provision servers that current `lsp-pi` already knows how to spawn without source changes.
3. The Phase 1 curated install set is locked to the current npm-manageable packages that map to real `lsp-pi` server entries or their required runtime support:
   - `typescript-language-server`
   - `typescript` (supplemental runtime package for TypeScript-family projects that lack a local workspace TypeScript install; not treated as a separate LSP server)
   - `@vue/language-server`
   - `svelte-language-server` (installs the `svelteserver` command expected by `lsp-pi`)
   - `pyright`
4. Failure to install `typescript` is treated as degraded TypeScript-family fallback support rather than total failure of the curated provisioning step. Verification and installer output must report that distinction explicitly.
5. Phase 1 explicitly excludes these packages because current `lsp-pi` does not consume them today:
   - `@astrojs/language-server`
   - `yaml-language-server`
   - `bash-language-server`
   - `dockerfile-language-server-nodejs`
6. Phase 1 also excludes toolchain-backed servers from new installer management:
   - `gopls`
   - `rust-analyzer`
   - `dart`
   - `sourcekit-lsp`
   - Kotlin servers beyond `lsp-pi`'s existing runtime behavior
7. `rust-analyzer` remains supported-but-unmanaged in Phase 1. Verification may report its current presence informationally, but curated provisioning success does **not** depend on installing it.
8. The installer strategy for the curated subset is:
   - use npm global installation only when npm global prefix/bin preflight proves the resulting binaries will be discoverable by `lsp-pi`,
   - otherwise skip curated provisioning and emit a clear actionable message explaining the PATH/prefix problem.
9. Preflight for curated npm provisioning is locked to these checks:
   - npm exists,
   - the resolved npm global prefix is writable without sudo for the current user,
   - the resolved npm global bin directory is either already on `PATH` for the current shell context that Pi will inherit or matches a stable hardcoded `lsp-pi` search directory currently present in `SEARCH_PATHS` (`/usr/local/bin` or `/opt/homebrew/bin`).
10. Phase 1 will not mutate shell startup files or invent new PATH management. If npm global bin discoverability is not already valid under the preflight rules above, the installer reports a remediation message and skips curated provisioning.
11. Phase 1 does **not** introduce a strict/fatal installer mode for LSP provisioning. Installer LSP provisioning remains best-effort, and the verification script is the enforcement surface.
12. Toolchain-backed server management may only be added in a future follow-up if the install command is all of:
   - official/upstream-supported,
   - single-command or clearly scripted without brittle release scraping,
   - idempotent,
   - and lands binaries in locations already discoverable by current `lsp-pi` without new PATH mutation.
13. `scripts/verify-pi-install.sh` exit semantics are locked as follows:
   - exit non-zero if expected Pi package registration is missing,
   - exit non-zero if curated provisioning preflight succeeds but any curated binary is missing or fails its executable smoke probe,
   - exit zero for unmanaged/toolchain-backed servers that are only being reported informationally,
   - exit non-zero with actionable explanation if curated provisioning preflight fails on a host where the user requested the Pi install path.
14. Verification for the curated subset is two-tiered:
   - binary discoverability/executability checks for every curated command,
   - at least one end-to-end Pi `lsp` smoke test against a real supported TypeScript fixture during execution validation. If no suitable fixture already exists, execution creates `thoughts/fixtures/lsp/typescript-smoke/index.ts` plus a minimal adjacent `tsconfig.json` and uses that as the canonical smoke fixture.
15. Idempotency for Phase 1 means:
   - a second installer run does not create duplicate package-manager actions or broken state,
   - curated-server log lines on rerun report `already available`/equivalent instead of reinstalling unnecessarily,
   - verification output remains stable apart from timestamps or naturally changing version text.
16. A future runtime-managed/private-bin model is deferred until there is explicit desire for either:
   - isolated/private LSP installation directories, or
   - on-demand/lazy installation during `lsp` tool execution.
17. Vendoring/forking `lsp-pi` becomes necessary only if the repo later chooses a managed private install directory or lazy runtime installs that cannot rely on current `PATH` discovery.

## Acceptance criteria

1. Running the repo installer in the relevant Pi/default modes provisions the locked curated subset using npm global commands only when npm preflight says the installed binaries will be discoverable by current `lsp-pi`.
2. After a successful curated install, current `lsp-pi` can discover those provisioned binaries without modifying `lsp-pi` source.
3. Installer output clearly reports installed, already-available, skipped, and unavailable curated servers with the reason for each outcome.
4. Verification tooling distinguishes missing Pi package registration from missing curated binaries and from unmanaged informational servers.
5. Verification fails non-zero when curated provisioning was expected to work but the curated subset is still not usable.
6. Repo docs describe the locked curated subset, npm prefix/PATH prerequisites, unmanaged server status, and the deliberate non-goal of full OpenCode-style runtime provisioning in Phase 1.
7. The plan leaves a clean architectural decision point for a later runtime-managed approach without forcing that complexity now.

## BDD scenarios

### B1 - Golden-path Pi install on an npm-global-compatible machine
Given a machine with `npm` available
And npm global prefix is writable for the current user
And npm global bin is already on `PATH`
When the user runs the Pi/default installer path
Then the locked curated subset is installed or reported already available
And `lsp-pi` can discover those commands without source changes
And installer output reports success for each curated server outcome

### B2 - npm global discoverability failure is explicit
Given a machine with `npm` available
But npm global bin is not on `PATH` or the global prefix is not writable
When the installer evaluates curated LSP provisioning
Then it skips curated provisioning
And it prints a concrete remediation message naming the failed preflight condition
And verification reports that curated provisioning prerequisites are unsatisfied

### B3 - Missing toolchain-backed servers do not block Phase 1
Given a machine without `go`, `dotnet`, `gem`, `dart`, or `swift`
When the installer completes the Phase 1 curated path
Then it does not claim those unmanaged servers are provisioned
And verification reports them, if at all, as informational unmanaged surfaces
And curated provisioning success is still judged only against the locked subset

### B4 - Verification tells the truth
Given `lsp-pi` is registered with Pi but one or more curated LSP binaries are missing or non-executable
When the verification script runs
Then it reports Pi package registration separately from curated binary availability
And it exits non-zero
And the operator can see exactly which command failed and why

### B5 - No-vendor initial architecture
Given the locked curated subset is installed into discoverable npm global locations
And the canonical smoke fixture exists at `thoughts/fixtures/lsp/typescript-smoke/index.ts` (creating it during execution if absent)
When Pi runs the `lsp` tool on that TypeScript fixture
Then existing `lsp-pi` discovery logic is sufficient
And no vendored/forked copy of `lsp-pi` is required

### B6 - Future runtime-managed pivot remains possible
Given a later decision to use a private managed install directory such as `~/.pi/.../lsp/bin`
When planning the follow-up
Then the repo recognizes that `lsp-pi` must be extended, wrapped, or forked to discover and/or install from that location
And that work is kept out of Phase 1

## Phase-by-phase execution plan

## Phase 1 - Add installer-side curated provisioning

### End State
`install.sh` provisions the locked curated subset on npm-global-compatible hosts and gives clear remediation output on incompatible hosts.

### Tests first
- Confirm the exact npm package names and expected installed command names for the curated subset.
- Confirm the npm global prefix/bin preflight commands that will be used by the installer.
- Confirm that the Svelte package installs `svelteserver`, not `svelte-language-server`.

### Work
- Add an installer helper dedicated to curated LSP provisioning.
- Run this helper from Pi/default/all flows after npm availability is already established.
- Implement npm global prefix/bin preflight and log each failing condition explicitly.
- For curated npm-backed servers, install globally with the repo's existing Node/npm assumptions only after preflight passes.
- Log per curated server: `already available`, `installed`, `skipped: preflight failed`, or `failed`.
- Keep Phase 1 scoped to the locked subset only.

### Expected files
- `install.sh`

### Verify
- Re-run installer twice and confirm the second run reports `already available` or equivalent for installed curated commands.
- Probe curated command discoverability with command checks matching current `lsp-pi` expectations:
  - `typescript-language-server`
  - `vue-language-server`
  - `svelteserver`
  - `pyright-langserver`
- Record the npm preflight output for both pass and fail conditions.
- Exercise the preflight-failure path deliberately by temporarily overriding `PATH`, npm prefix resolution, or another controllable preflight input so BDD scenario B2 is actually verified rather than assumed.

## Phase 2 - Extend verification semantics and docs

### End State
Verification and repo documentation tell the truth about package registration, curated binary usability, unmanaged server status, and npm preflight requirements.

### Tests first
- Define the verification script's exit-status rules before editing docs.
- Choose the executable smoke probe for each curated command (`--version`, `--help`, or equivalent lightweight check) before wiring the script.

### Work
- Extend `scripts/verify-pi-install.sh` with three explicit sections:
  - Pi package registration
  - curated provisioning preflight + curated binary probes
  - unmanaged informational server surface
- Make curated preflight or curated binary failures exit non-zero.
- Keep unmanaged/toolchain-backed server reporting informational in Phase 1.
- If no suitable TypeScript smoke fixture already exists, create the canonical smoke fixture at `thoughts/fixtures/lsp/typescript-smoke/index.ts` with a minimal adjacent `tsconfig.json` and document the expected smoke-test contract.
- Update README or `_pi/README.md` installation docs to explain:
  - `lsp-pi` package registration,
  - the locked curated subset,
  - why `typescript` is installed as a runtime prerequisite rather than a separate LSP,
  - how degraded TypeScript-family fallback support is reported if the `typescript` package install fails,
  - npm global prefix/PATH requirements,
  - unmanaged server status,
  - Phase 1 non-goals.

### Expected files
- `scripts/verify-pi-install.sh`
- `_pi/README.md` and/or another installer-facing doc chosen during execution

### Verify
- `bash scripts/verify-pi-install.sh`
- read the touched docs after editing to ensure command names and supported-server claims match `lsp-pi` reality
- run one end-to-end Pi `lsp` smoke test against `thoughts/fixtures/lsp/typescript-smoke/index.ts` (creating the fixture during execution if absent) to prove current `lsp-pi` discovers the curated install path and produces the expected smoke-test output

## Phase 3 - Re-review and decide whether a runtime-managed follow-up is still necessary

### End State
After the installer-first work lands, the repo has an explicit decision on whether the user still needs private-bin or lazy runtime provisioning.

### Tests first
- None beyond the evidence already produced by Phases 1-2.

### Work
- Evaluate whether the installer-first path solves the actual user problem.
- If yes, stop here.
- If no, create a separate follow-up plan for one of:
  - upstreaming changes to `lsp-pi`,
  - vendoring/forking `lsp-pi`, or
  - adding a wrapper extension that augments discovery/install behavior.

### Expected files
- optional future plan under `thoughts/plans/`

### Verify
- N/A unless a runtime-managed follow-up is explicitly started

## Verification strategy

- Verification must cover both package registration and curated binary usability.
- For every curated command, verification should check both discoverability and a lightweight executable smoke probe.
- Verification should use command names that match actual `lsp-pi` discovery logic, not just npm package names.
- At least one end-to-end Pi `lsp` smoke test should be run on a supported fixture to prove real tool discovery, not just shell visibility.
- Installer reruns must prove idempotent outcomes for the curated subset.

## Test coverage matrix

| Acceptance / Scenario | Planned evidence |
|---|---|
| AC1, AC2, B1, B5 | installer run + curated command probes + one end-to-end Pi `lsp` smoke test against `thoughts/fixtures/lsp/typescript-smoke/index.ts` |
| AC3, B2 | installer output for preflight failures, install success, and already-available states |
| AC4, AC5, B4 | updated `scripts/verify-pi-install.sh` output and exit code behavior |
| AC6, B3 | docs + verification output that clearly classify unmanaged servers as informational |
| AC7, B6 | locked decision + deferred separate follow-up plan only if needed |

## Delivery order

1. Implement installer preflight and curated provisioning helper.
2. Extend verification script with exit-status semantics and curated probes.
3. Update docs to match the locked subset and prerequisites.
4. Reassess whether a runtime-managed follow-up is still necessary.

## Non-goals

- Full OpenCode-style lazy runtime provisioning for every language server.
- Immediate support for every server in OpenCode's matrix.
- Astro support in Phase 1.
- YAML, Bash, or Dockerfile LSP support in Phase 1.
- New installer management for Go, Rust, Dart, Swift, or Kotlin LSP binaries in Phase 1.
- A private Pi-only LSP package store in Phase 1.
- Vendoring/forking `lsp-pi` in Phase 1.
- Automatic shell startup file mutation to fix PATH.
- Pinning or managing specific package versions for the curated npm subset in Phase 1.
- Cross-platform perfection beyond the repo's current Unix-like assumptions.

## Plan Changelog

- 2026-04-08: Integrated Claude review feedback by clarifying `typescript` as a runtime prerequisite, widening npm-bin preflight to match current `lsp-pi` discovery reality, making preflight-failure verification mandatory, and locking a canonical TypeScript smoke-fixture path.

## Decisions / Deviations log

- 2026-04-08: Chose installer-first provisioning as the recommended first step because it captures most of the UX win without turning this repo into a cross-platform LSP package manager.
- 2026-04-08: Locked the Phase 1 curated subset to the npm-manageable servers that current `lsp-pi` already consumes: TypeScript, Vue, Svelte, and Pyright.
- 2026-04-08: Explicitly excluded Astro, YAML, Bash, and Dockerfile servers from Phase 1 because current `lsp-pi` does not actually consume them.
- 2026-04-08: Explicitly deferred vendoring/forking `lsp-pi`; current evidence says it is unnecessary unless the repo later chooses private managed install directories or lazy runtime installation.
- 2026-04-08: During Phase 1 execution, used `npm prefix -g` with `npm config get prefix` fallback plus `<prefix>/bin` derivation because npm 11 on this host no longer supports `npm bin -g`; verified with `npm --version`, `npm prefix -g`, `npm config get prefix`, and the resulting installer rerun logs.
- 2026-04-08: Phase 2 verification treats a missing global `typescript` package as degraded TypeScript-family fallback support instead of a fatal curated-binary failure, matching the locked Phase 1 scope while still failing hard on missing or non-executable curated LSP commands.
- 2026-04-08: Chose `pyright-langserver --stdio </dev/null` as the Pyright smoke probe because `--help`/`--version` do not provide a zero-exit health check on this host; verification accepts a clean EOF exit as evidence that the executable is launchable.
- 2026-04-08: After installer reruns, curated-binary probes, preflight-failure simulation, and an end-to-end Pi `lsp` smoke test against `thoughts/fixtures/lsp/typescript-smoke/index.ts`, no runtime-managed/private-bin follow-up is necessary right now.
