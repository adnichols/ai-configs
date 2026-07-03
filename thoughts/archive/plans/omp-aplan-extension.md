# OMP `/aplan` extension

## Status

execution-ready

## Goal

Add a repo-managed OMP extension that mirrors the maintained Pi planning-mode workflow from `_pi/extensions/pi-plan-mode/index.ts`, exposes it as `/aplan`, and makes that extension the documented OMP planning entrypoint in this repo.

## Non-goals

- Replacing or patching upstream OMP core `/plan` behavior.
- Redesigning the Pi planning workflow instead of porting it.
- Overriding unrelated OMP commands or agents beyond the changes needed to support `/aplan` cleanly.
- Introducing a second OMP execution wrapper when `_omp/commands/cmd:execute-plan.md` already exists.

## Current State (Validated)

- `_pi/extensions/pi-plan-mode/index.ts` already implements the target workflow: planning-mode restrictions scoped to `thoughts/`, current-plan tracking, post-edit review offers, post-review execution offers, and `/cmd:execute-plan` staging.
- `_omp/` currently contains `agents/` and `commands/`, but no repo-managed `_omp/extensions/` tree.
- `install.sh` installs OMP commands and agents to `~/.omp/agent/`, but it does not currently copy repo-managed OMP extensions.
- `README.md` currently describes `_omp/` only as “Native OMP commands and agents.”
- `_omp/commands/` already contains the planning-review and execution surfaces the extension needs to reference, including `review:plan.md`, `review:plan-adversarial.md`, `cmd:execute-plan.md`, `dev:run.md`, and `ralph:run.md`.
- `_omp/agents/aplan.md` already exists, so the implementation must resolve repo-local coexistence between that file and the new runtime `/aplan` command.
- The local OMP runtime already auto-discovers extensions from `~/.omp/agent/extensions/`: `~/.omp/agent/extensions/pi-dcp/index.ts` exists and imports `@mariozechner/pi-coding-agent`, and `~/.omp/agent/config.yml` contains a `disabledExtensions` key. This is sufficient evidence to lock the port-vs-redesign decision in favor of a close TypeScript extension port.
- Upstream OMP documentation also describes extension discovery under `~/.omp/agent/extensions/` and `-e/--extension`, so a repo-managed OMP extension is a supported shape.
- `thoughts/specs/product_intent.md` is absent, and `thoughts/plans/AGENTS.md` is absent. This plan therefore aligns to the user request, root `AGENTS.md`, repo docs, and the validated local/runtime evidence above.

## Locked decisions

1. Treat `_pi/extensions/pi-plan-mode/index.ts` as the behavioral source of truth and port it with the smallest OMP-specific delta possible.
2. Add the OMP extension at `_omp/extensions/aplan/index.ts`, installed to `~/.omp/agent/extensions/aplan/index.ts`.
3. Register `/aplan` as the repo-managed OMP planning toggle. Do not override built-in `/plan`.
4. Keep `_omp/commands/cmd:execute-plan.md` as the OMP execution wrapper. The first cut does **not** register a second extension-level `/cmd:execute-plan` handler, which avoids command-surface conflict and keeps the handoff model explicit.
5. Update `_omp/agents/aplan.md` so it no longer competes with the runtime `/aplan` workflow. The chosen coexistence strategy is to rewrite that file into a legacy shim/documentation artifact that points users at the runtime `/aplan` command rather than acting like the primary planning surface.
6. Keep the Pi-style `setActiveTools()` flow in the OMP port. The installed `@mariozechner/pi-coding-agent` runtime used by OMP exposes the same ExtensionAPI surface, so no OMP-specific replacement is required.
7. The OMP port must explicitly rewrite Pi-only prompt/template paths and host text. Mandatory path deltas already known from review are:
   - `_pi/prompts` -> `_omp/commands`
   - `.pi/prompts` -> `.omp/commands`
   - `~/.pi/agent/prompts` -> `~/.omp/agent/commands`
   - injected host text such as “In Pi ...” -> OMP-specific or host-agnostic wording.
8. Verification must prove both positive and negative behavior: `/aplan` discoverability, `/plan` coexistence, plan-file happy path, and destructive/non-read-only bash blocking while `/aplan` is active.
9. No additional third-party dependency scan is required for this work. This is a reuse/port of existing in-repo TypeScript against the existing OMP extension runtime, not a new library-selection problem.

## Proposed Approach

Create `_omp/extensions/aplan/index.ts` as a close port of the Pi extension. Preserve the Pi state model, planning restrictions, review loop, and post-review execution menu wherever OMP supports the same extension APIs.

The port is not a blind copy-and-rename. The known mandatory OMP deltas are already identified and should be implemented directly rather than rediscovered later:
- OMP command-template discovery paths,
- OMP-specific install surface under `~/.omp/agent/extensions/`,
- coexistence between runtime `/aplan`, built-in `/plan`, and `_omp/agents/aplan.md`,
- the deliberate choice to keep `/cmd:execute-plan` prompt-backed in OMP rather than re-registering it inside the extension.

The first implementation should favor predictable behavior over perfect Pi parity where the host differs. That means the extension should mirror Pi planning mode closely, but avoid creating avoidable OMP command conflicts just to preserve one implementation detail.

## Acceptance Criteria

1. `_omp/extensions/aplan/index.ts` exists and loads as a repo-managed OMP extension.
2. The extension registers `/aplan` and leaves built-in `/plan` untouched.
3. While `/aplan` is active, edit/write mutations are limited to `thoughts/`, and plan files stay under `thoughts/plans/`.
4. The OMP extension mirrors the Pi workflow closely enough to:
   - track the current plan file,
   - offer `/review:plan` after plan updates,
   - optionally offer `/review:plan-adversarial` after standard review,
   - offer `/dev:run` and `/ralph:run` via the existing `/cmd:execute-plan` surface when review is complete.
5. Repo-managed OMP installation copies `_omp/extensions/` into `~/.omp/agent/extensions/`.
6. Repo docs describe `_omp/extensions/` and `/aplan` clearly.
7. Repo-managed OMP guidance no longer leaves `_omp/agents/aplan.md` competing with the runtime `/aplan` entrypoint.
8. Verification proves both `/aplan` and `/plan` are still discoverable after installation.
9. Runtime smoke verification proves the extension blocks a destructive/non-read-only bash command while planning mode is active.

## Verification Strategy

Use a mix of static inspection, installer smoke checks, and one fresh OMP runtime check.

Verification must prove:
- the extension is present in the repo and in the installed OMP runtime,
- the port includes the required OMP-specific path/host deltas,
- the installer actually copies extensions for OMP,
- `/aplan` loads in a fresh OMP session without shadowing built-in `/plan`,
- planning restrictions cover both write/edit scope and destructive bash gating.

Portable verification commands should use `find` and recursive `grep`, not `**` globstar assumptions.

## Resume Instructions (Agent)

- Read this document fully before making changes.
- Reuse `_pi/extensions/pi-plan-mode/index.ts` as the primary behavioral reference.
- Start with the first unchecked item in `## Progress`.
- Preserve minimal-delta parity with the Pi extension unless a locked OMP-specific decision in this plan says otherwise.
- Update `## Progress` only when a phase is complete.
- Record any execution-time deviations in `## Decisions / Deviations Log`.

## Progress

- [x] P1 - Lock the OMP-specific delta list and remove remaining command-surface ambiguity before code is copied.
- [x] P2 - Implement `_omp/extensions/aplan/index.ts` as a close Pi port with the required OMP-specific rewrites.
- [x] P3 - Wire `install.sh` and repo docs to the new OMP extension surface and `/aplan` workflow.
- [x] P4 - Verify install, fresh-session discoverability, `/plan` coexistence, and planning restrictions including destructive bash blocking.

## Phase 1: Lock the OMP-specific delta list

### End State

- The implementation target, install path, command-surface strategy, and coexistence rules are explicit.
- The team is not spending implementation time rediscovering already-known OMP deltas.
- Any remaining host-specific uncertainty is reduced to execution-time validation, not plan-shaping ambiguity.

### Tests first

- Confirm repo/runtime evidence for the port target:
  - `ls _omp`
  - `ls _pi/extensions/pi-plan-mode`
  - `ls /home/anichols/.omp/agent/extensions`
  - `grep -n "disabledExtensions" /home/anichols/.omp/agent/config.yml`
  - `read /home/anichols/.omp/agent/extensions/pi-dcp/index.ts`
- Confirm installer/doc baseline:
  - `grep -n "install_omp\|~/.omp/agent" install.sh`
  - `grep -n "_omp/" README.md`
- Confirm the existing competing repo-local planning artifact:
  - `read _omp/agents/aplan.md`

### Expected files

- `_pi/extensions/pi-plan-mode/index.ts`
- `_omp/agents/aplan.md`
- `install.sh`
- `README.md`

### Work

- Record the mandatory OMP deltas already known from research:
  - prompt/template path rewrites,
  - OMP install path for extensions,
  - host-text rewrites,
  - `/cmd:execute-plan` remaining prompt-backed,
  - coexistence plan for `_omp/agents/aplan.md`.
- Confirm the extension directory naming choice remains `_omp/extensions/aplan/index.ts`.
- Define the exact coexistence strategy for the three relevant surfaces:
  - runtime `/aplan`,
  - built-in `/plan`,
  - `_omp/agents/aplan.md`.
- Confirm whether the OMP port keeps Pi-style `setActiveTools()` behavior directly or uses an OMP-safe equivalent if the runtime differs.
- Confirm that no additional dependency/library evaluation is needed beyond the locked port-vs-redesign decision.

### Verify

- The plan explicitly names `_omp/extensions/aplan/index.ts` and `~/.omp/agent/extensions/aplan/index.ts`.
- The plan explicitly states that `/cmd:execute-plan` remains prompt-backed in OMP.
- The plan explicitly states how `_omp/agents/aplan.md` will stop competing with runtime `/aplan`.
- No foundational OMP-path or command-surface ambiguity remains in the plan text.

## Phase 2: Implement the OMP `/aplan` extension

### End State

- `_omp/extensions/aplan/index.ts` exists and ports the Pi extension logic with the locked OMP-specific rewrites.
- The extension registers `/aplan`, preserves planning restrictions, tracks the active plan file, and offers the Pi-style review loop and post-review execution menu.
- The extension does not create a conflicting second `/cmd:execute-plan` implementation.

### Tests first

- Keep a parity checklist against `_pi/extensions/pi-plan-mode/index.ts` for:
  - command registration,
  - state hydration/persistence,
  - plan-mode context injection,
  - destructive bash blocking,
  - write/edit restriction to `thoughts/`,
  - current-plan tracking,
  - post-edit review offer,
  - post-review execution offer,
  - OMP-specific prompt/template path rewrites.
- Predefine portable static checks that will be used after the port lands:
  - `find _omp/extensions -name index.ts -print`
  - `grep -R -n "registerCommand\|registerFlag\|cmd:execute-plan\|review:plan\|review:plan-adversarial" _omp/extensions`
  - `grep -R -n "_omp/commands\|~/.omp/agent/commands\|In OMP\|cmd:execute-plan" _omp/extensions`

### Expected files

- `_omp/extensions/aplan/index.ts`
- `_pi/extensions/pi-plan-mode/index.ts`

### Work

- Create `_omp/extensions/aplan/index.ts`.
- Port `_pi/extensions/pi-plan-mode/index.ts` with only the locked OMP-specific changes:
  - `/plan` -> `/aplan`,
  - Pi prompt directories -> OMP command directories,
  - Pi host wording -> OMP-specific or host-agnostic wording,
  - keep `/cmd:execute-plan` as a referenced command, not a new extension command.
- Preserve the Pi review loop behavior, including standard/adversarial review offers and the capped auto-loop count.
- Preserve tool-call gating for destructive/non-read-only bash plus non-`thoughts/` edit/write paths.
- Update any extension-injected planning instructions so they reference OMP surfaces accurately.
- Update or replace `_omp/agents/aplan.md` if that is required to keep `/aplan` as the preferred entrypoint.

### Verify

- `find _omp/extensions -name index.ts -print`
- `grep -R -n "registerCommand" _omp/extensions`
- `grep -R -n "aplan\|cmd:execute-plan\|review:plan\|review:plan-adversarial" _omp/extensions`
- `grep -R -n "_omp/commands\|~/.omp/agent/commands\|In OMP\|thoughts/plans" _omp/extensions`
- Static inspection confirms the extension registers `/aplan` but does not register a second `/cmd:execute-plan`.

## Phase 3: Install and document the OMP extension surface

### End State

- `install.sh --omp` installs repo-managed OMP extensions into `~/.omp/agent/extensions/`.
- Installer/help text and repo docs describe OMP extensions and `/aplan` accurately.
- Repo-local OMP guidance no longer frames commands and agents as the only managed runtime surfaces.

### Tests first

- Capture the current OMP installer/doc baseline:
  - `grep -n "install_omp\|commands and agents\|~/.omp/agent" install.sh`
  - `grep -n "_omp/" README.md`
  - `grep -R -n "aplan\|plan mode\|commands and agents" _omp README.md`

### Expected files

- `install.sh`
- `README.md`
- `_omp/agents/aplan.md`
- any OMP-local doc file added or updated during implementation

### Work

- Update `install_omp()` so it copies `_omp/extensions/` into `~/.omp/agent/extensions/` alongside commands and agents.
- Update installer messages/help text that currently imply OMP installs only commands and agents.
- Update repo docs to describe `_omp/extensions/` and `/aplan`.
- Update OMP-local guidance so `_omp/agents/aplan.md` no longer steers users toward the old prompt-only planning flow by default.

### Verify

- `grep -n "install_omp\|extensions\|~/.omp/agent" install.sh`
- `grep -n "_omp/" README.md`
- `grep -R -n "aplan\|plan mode\|extensions" _omp README.md`
- Static inspection confirms `install_omp()` handles `_omp/extensions/`.

## Phase 4: Verify install, discoverability, and restriction behavior

### End State

- The extension installs correctly into an OMP runtime.
- A fresh OMP session discovers `/aplan`.
- Verification proves `/aplan` works without shadowing `/plan`, and that planning restrictions include destructive bash blocking.

### Tests first

- Use two separate smoke surfaces:
  1. an isolated temp-HOME installer smoke check for file layout only,
  2. a fresh OMP runtime session using a valid OMP runtime (real home or a copied `~/.omp` runtime) for command/discoverability behavior.
- Require a fresh OMP restart for runtime checks; do not assume hot reload.

### Expected files

- installed files under `~/.omp/agent/extensions/` or the temp-home equivalent

### Work

- Run an isolated installer smoke check into a temp HOME and confirm the extension lands at the expected installed path.
- Run a fresh-session runtime smoke check using a valid OMP runtime and confirm:
  - `/aplan` is discoverable,
  - built-in `/plan` still exists,
  - `/aplan` can create/update a plan under `thoughts/plans/`,
  - a destructive or non-read-only bash command is blocked while `/aplan` is active,
  - post-edit review prompting appears,
  - post-review execution choices route through `/cmd:execute-plan`.
- Record any host-specific runtime caveats in `## Decisions / Deviations Log`.

### Verify

- `TMP_HOME="$(mktemp -d)" && HOME="$TMP_HOME" bash ./install.sh --omp`
- `find "$TMP_HOME/.omp/agent" -maxdepth 4 | sort`
- For runtime behavior, use either a copied runtime or the real runtime, then restart OMP fresh and verify manually:
  - `/aplan` is present,
  - `/plan` is still present,
  - a plan edit under `thoughts/plans/` succeeds,
  - a destructive bash command is blocked while `/aplan` is active.
- Treat runtime verification as incomplete unless it is run in a fresh OMP session after installation.

## Decisions / Deviations Log

- Initial plan decision: treat `_pi/extensions/pi-plan-mode/index.ts` as the canonical behavioral reference and port it to OMP with the smallest possible host-specific delta.
- Initial plan decision: `/aplan` becomes the repo-managed OMP planning entrypoint, while built-in `/plan` remains untouched.
- 2026-04-03: Locked the OMP extension path at `_omp/extensions/aplan/index.ts` and the installed runtime path at `~/.omp/agent/extensions/aplan/index.ts`.
- 2026-04-03: Locked the first-cut OMP command strategy so `/aplan` is registered by the extension, but `/cmd:execute-plan` remains the existing prompt-backed OMP command to avoid command-surface conflict.
- 2026-04-03: Locked the mandatory OMP path/text rewrites discovered in review: `_pi/prompts`/`.pi/prompts`/`~/.pi/agent/prompts` must become `_omp/commands`/`.omp/commands`/`~/.omp/agent/commands`, and Pi-specific injected host text must become OMP-specific or host-agnostic.
- 2026-04-03: Locked runtime verification to include both `/plan` coexistence and destructive bash blocking while `/aplan` is active; happy-path discoverability alone is insufficient.
- 2026-04-03: Locked the port-vs-redesign decision using local OMP runtime evidence (`~/.omp/agent/extensions/pi-dcp/index.ts`, `disabledExtensions` in `~/.omp/agent/config.yml`) plus upstream OMP extension documentation; no further library/dependency evaluation is required.
- 2026-04-03: Confirmed the OMP port can keep Pi-style `setActiveTools()` directly because the installed `@mariozechner/pi-coding-agent` ExtensionAPI exposed to OMP includes `setActiveTools()` in its runtime/types, so no host-specific tool-gating rewrite is needed.
- 2026-04-03: Locked `_omp/agents/aplan.md` to a legacy shim/documentation role that explicitly points users to runtime `/aplan`, which preserves the file without leaving it as a competing primary planning surface.
- 2026-04-03: Implemented `_omp/extensions/aplan/index.ts` as a close Pi port with OMP command-path rewrites, `/aplan` command/flag registration, retained `setActiveTools()`-based tool gating, and prompt-backed review automation. The extension intentionally prepares `/cmd:execute-plan ... --target ...` for the host to run instead of registering a second extension-level `/cmd:execute-plan` handler.
- 2026-04-03: Updated `install.sh` to copy `_omp/extensions/` into `~/.omp/agent/extensions/`, updated root/Omp docs to describe repo-managed OMP extensions and `/aplan`, and rewrote `_omp/agents/aplan.md` into a legacy shim that points users to the runtime `/aplan` entrypoint.
- 2026-04-03: Runtime smoke verification used a temp HOME seeded from the existing `~/.omp` runtime, then reinstalled `--omp` into that temp runtime before launching fresh `omp -p` sessions. `/aplan` successfully created a plan under `thoughts/plans/` and blocked `touch /tmp/...`; built-in `/plan` also created a plan in a separate fresh session. Non-interactive `omp -p` is sufficient for discoverability and bash-gating checks, but it does not exercise UI-only review/exit menus, so `/review:plan` prompting and `/cmd:execute-plan` exit routing remain statically verified from `_omp/extensions/aplan/index.ts`.
- 2026-04-03: Follow-up runtime testing showed `_omp/agents/aplan.md` was still intercepting `/aplan` in at least one host path. Renamed the shim to `_omp/agents/aplan-legacy.md` so the extension now owns `/aplan` without agent-surface collision.
- 2026-04-03: Interactive validation showed extension-command `/aplan` still behaved like a normal slash command (`Working`) instead of switching the host into native plan mode. Adjusted the extension so the interactive `input` event redirects `/aplan` into bare built-in `/plan`, while queueing the repo-managed workflow guidance as a hidden next-turn custom message. This preserves the native instant plan-mode UX, avoids auto-starting a planning turn, and lets the user discuss the plan before the custom workflow guidance is applied on the next real planning message.

## Plan Changelog

- 2026-04-03: Initial plan created after validating the maintained Pi extension, current `_omp/` repo structure, existing OMP command surfaces, missing OMP extension install path in `install.sh`, and upstream evidence that OMP supports repo-managed extensions under `~/.omp/agent/extensions/`.
- 2026-04-03: Integrated multi-model review feedback. Removed unresolved command/path ambiguity, pre-locked the mandatory OMP-specific deltas, kept `/cmd:execute-plan` prompt-backed to avoid command conflict, strengthened verification to cover `/plan` coexistence and destructive bash blocking, replaced non-portable glob-based checks with portable recursive commands, and clarified that runtime verification must happen in a fresh valid OMP session rather than a temp-home file-layout check alone.
