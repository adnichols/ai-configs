# Skill Consolidation to Shared `~/.agents/skills`

## Status

execution-ready

## Goal

Make `skills/` the single canonical installable-skill source in this repo, sync those installable skills into `~/.agents/skills`, and expose them across Claude, OpenCode, Pi, and OMP using consumer-appropriate wiring instead of maintaining divergent copied skill trees.

## Why this plan exists

The repo currently has multiple competing skill trees (`skills/`, `.agents/skills/`, `opencode/skills/`, `_pi/skills/`) plus installer and doc flows that copy different subsets into tool-specific home directories. That creates drift, stale docs, and path-specific command behavior.

The requested end state is:
- one canonical installable-skill source in-repo,
- one canonical installed skill store on disk,
- additive installation that preserves foreign skills,
- per-consumer compatibility wiring only where the consumer actually needs it,
- consistent docs and command paths pointing at the same canonical runtime location.

## Authority and inputs

Primary authority:
- User request in this session
- `thoughts/handoffs/2026-04-01_17-00-00_skill-consolidation-to-agents.md`

Repo guidance read:
- `AGENTS.md`
- `install.sh`
- `README.md`
- `SETUP.md`
- `_pi/README.md`
- `OPENCODE_ONBOARDING.md`
- `opencode/OPENCODE_ONBOARDING.md`
- `opencode/QUICKSTART.md`
- `_omp/commands/cmd:send-plan-to-doct.md`
- `opencode/commands/cmd:send-plan-to-doct.md`
- `_pi/prompts/cmd:send-plan-to-doct.md`
- `opencode/skills/opencode-conversation-reviewer/SKILL.md`
- `opencode/skills/template/SKILL.md`

Pi documentation read:
- `/home/linuxbrew/.linuxbrew/lib/node_modules/@mariozechner/pi-coding-agent/docs/skills.md`

Product/planning guidance status:
- `thoughts/specs/product_intent.md` is absent.
- `thoughts/plans/AGENTS.md` is absent.
- This plan therefore aligns directly to the active user request, the handoff, root `AGENTS.md`, and the shared `product-principles` doctrine.

## Current implementation reality

### Current repo skill trees
- `skills/`
  - `linear`
  - `product-principles`
- `.agents/skills/`
  - `dependency-selection`
- `opencode/skills/`
  - 29 skill directories, including shared-looking skills such as `linear`, `product-principles`, `doct-document-ops`, `theme-factory`, `web-design-guidelines`, `playwright-skill`, etc.
- `_pi/skills/`
  - 16 skill directories, including workflow skills such as `cmd-debug`, `cmd-research`, `dev-plan`, `review-change`, `ralph-run`, and `sentry-cli`

### Verified drift / duplication
- `skills/linear/SKILL.md` and `opencode/skills/linear/SKILL.md` are duplicate shared skills.
- `skills/product-principles/SKILL.md`, `opencode/skills/product-principles/SKILL.md`, and `_pi/skills/product-principles/SKILL.md` are duplicate shared skills.
- `opencode/skills/doct-document-ops/SKILL.md` and `_pi/skills/doct-document-ops/SKILL.md` are duplicate shared skills.

### Verified installer behavior that conflicts with the target model
- `install.sh --skills` still installs to `~/.claude/skills`.
- `install_opencode()` still copies `opencode/skills/*` into `~/.config/opencode/skills`.
- `install_pi()` still copies `_pi/skills/*` into `~/.pi/agent/skills` and recreates that directory wholesale.
- `install_omp()` currently installs commands and agents only; there is no verified OMP-native skill directory contract in the repo.
- Default mode (`install.sh` with no flags) does not call `install_skills()` today.
- `install_opencode()` and `install_pi()` currently use destructive directory replacement patterns that conflict with additive ownership-aware shared-skill management.

### Verified consumer reality
- **Claude**: has an established `~/.claude/skills/` surface.
- **OpenCode**: has an established `~/.config/opencode/skills/` surface.
- **Pi**: official Pi docs list both `~/.pi/agent/skills/` and `~/.agents/skills/` as standard global discovery paths. That means Pi already natively discovers `~/.agents/skills` and should not need extra settings wiring for shared-skill discovery.
- **OMP**: repo evidence shows commands/agents under `~/.omp/agent`, but no verified native OMP `skills/` discovery directory. Existing OMP doct command content shells through Pi-installed skill paths today.

### Verified stale path assumptions in docs/commands
- `OPENCODE_ONBOARDING.md` and `opencode/OPENCODE_ONBOARDING.md` still tell users to copy `opencode/skills/playwright-skill/` into `~/.config/opencode/skills/playwright-skill/`.
- `opencode/QUICKSTART.md` still assumes OpenCode owns `~/.config/opencode/skills/playwright-skill`.
- `opencode/commands/cmd:send-plan-to-doct.md` hardcodes `~/.config/opencode/skills/doct-document-ops/...`.
- `_omp/commands/cmd:send-plan-to-doct.md` and `_pi/prompts/cmd:send-plan-to-doct.md` hardcode Pi-specific skill paths rather than the canonical shared path.
- `AGENTS.md` still contains a Pi settings example using `"skills": [".agents/skills", "opencode/skills"]`.
- `opencode/skills/playwright-skill/SKILL.md` and `API_REFERENCE.md` still reference `~/.claude/skills/playwright-skill`.

### Pre-existing external skill state to preserve
This machine already has foreign skills in `~/.agents/skills`, including:
- different-name foreign skills not present in the repo,
- same-name collisions for some repo candidates,
- some installed variants that appear richer than their current repo copies.

The new installer must therefore:
- preserve different-name foreign skills,
- exercise same-name collision handling explicitly,
- avoid wiping consumer-local skill directories that may contain unrelated user/package-managed entries,
- and use home-directory variants only as reference inputs during audit, never as the authoritative source of truth.

### Worktree caution
The repo is already dirty and the implementation must preserve unrelated in-flight changes:
- `AGENTS.md`
- `_pi/README.md`
- `_pi/prompts/review:plan.md`
- `install.sh`
- `_pi/skills/sentry-cli/`

## Product intent alignment

This work aligns with the repo's current product direction and `product-principles` doctrine:
- **single source of truth**: installable skills should exist in one canonical repo location and one canonical installed location,
- **golden path first**: the common install path should be “sync installable skills once, then let each consumer use the canonical store through an explicit supported contract,”
- **safe defaults**: only proven consumer surfaces should receive compatibility wiring,
- **self-healing**: installer should migrate stale copied installs into the new model safely,
- **actionable docs**: onboarding and command examples should point at the same canonical shared path.

Because `thoughts/specs/product_intent.md` does not exist yet, this section is derived from the user's explicit request and the repo's current guidance rather than a dedicated product-intent artifact.

## Consumer compatibility matrix

| Consumer | Proven repo/runtime surface | Planned installable-skill contract |
|---|---|---|
| Claude | `~/.claude/skills/` | Per-skill symlinks for consumer-compatible skills: `~/.claude/skills/<skill> -> ~/.agents/skills/<skill>` |
| OpenCode | `~/.config/opencode/skills/` | Per-skill symlinks for consumer-compatible skills: `~/.config/opencode/skills/<skill> -> ~/.agents/skills/<skill>` |
| Pi | Native global discovery of `~/.agents/skills/` and `~/.pi/agent/skills/` | Do not mirror shared skills into `~/.pi/agent/skills`; rely on Pi's native `~/.agents/skills` discovery for shared skills; only keep Pi-consumer-only entries under `~/.pi/agent/skills` if they remain outside the shared installable set |
| OMP | Commands/agents under `~/.omp/agent`, no verified native `skills/` dir | Do not invent `~/.omp/agent/skills`; update OMP command/templates that need shared skill scripts to reference `~/.agents/skills/...` directly |

## Locked decisions

1. **Canonical repo source**: `skills/` is the only authoritative installable-skill tree in this repo.
2. **Canonical installed location**: installable skills sync into `~/.agents/skills`.
3. **Shared installer entrypoint**: `install.sh --skills` becomes the canonical installable-skill sync path.
4. **Required shared-sync callers**: the same shared-skill sync helper must be used by `--skills`, `--default`, `--all`, `--claude`, `--opencode`, `--pi`, and `--omp` wherever those modes claim or rely on installable skill availability.
5. **Additive installation**: shared-skill sync must be additive. It may update repo-managed skill names, but it must not wipe `~/.agents/skills` or remove unrelated foreign skills.
6. **Foreign skill definition**: a foreign skill is any installed skill directory lacking the repo ownership marker for this repo. Different-name foreign skills are preserved in place. Same-name foreign skills trigger backup + replace.
7. **Managed ownership marker**: repo-managed installed skills use a concrete marker file named `.ai-configs-managed.json` at the skill root.
8. **Ownership marker shape**: `.ai-configs-managed.json` contains at least `{ "repo": "ai-configs", "source": "skills/<name>", "managed": true }` plus optional version/commit metadata.
9. **Backup location**: same-name collision backups go to `~/.agents/skill-backups/ai-configs/<timestamp>/<skill-name>/`.
10. **Same-name collision policy**: if a repo-managed skill name already exists in `~/.agents/skills` and is not already marked as repo-managed, the installer must back up that existing directory to the backup location before replacing it with the repo version.
11. **Compatibility classes**: installable skills must be classified as one of:
    - **universal installable**: safe to expose to Claude, OpenCode, and Pi,
    - **consumer-specific installable**: canonical in `skills/`, but exposed only to compatible consumers,
    - **repo-local-only**: remains outside the canonical installable set.
12. **Pi-consumer-only handling**: skills that depend on Pi-only APIs/extensions (for example `subagent()` / `pi-subagents`) are **consumer-specific installable** skills. They may live canonically under `skills/`, but they must not be exposed to Claude or OpenCode.
13. **Classification manifest**: Phase 1 must create a durable machine-readable manifest at `skills/install-matrix.json` describing each canonical installable skill's class, allowed consumers, source path, and any special notes needed by the installer.
14. **Claude/OpenCode fan-out filtering**: Claude/OpenCode compatibility links are generated only from `skills/install-matrix.json`, not by blindly symlinking every directory under `~/.agents/skills`.
15. **Pi shared-skill discovery**: Pi natively discovers `~/.agents/skills`; the installer must not add redundant Pi settings pointing at that same path and must not duplicate shared skills into `~/.pi/agent/skills`.
16. **Pi consumer-specific install location**: if any Pi-consumer-only skills remain outside the shared installable set after Phase 1 classification, they stay under `_pi/skills` and continue installing to `~/.pi/agent/skills` non-destructively. If they are promoted into canonical `skills/`, Pi discovers them via `~/.agents/skills` and no duplicate mirror is created.
17. **Consumer exposure model**:
    - Claude and OpenCode receive per-skill compatibility symlinks only for consumer-compatible skills.
    - Pi does **not** receive mirrored shared entries under `~/.pi/agent/skills`.
    - OMP does **not** get a new native `skills/` contract without repo evidence.
18. **Default/all behavior**: after refactor, `install.sh` with no flags and `install.sh --all` must both ensure installable skills are synced into `~/.agents/skills` before claiming installation is complete.
19. **Consumer directory ownership**: consumer installers may manage only repo-owned shared-skill links/entries for known installable skill names. They must not wipe unrelated user/package-managed entries in those consumer skill directories.
20. **Destructive-path replacement**: current `rm -rf` behavior for consumer skill directories must be replaced with per-skill ownership-aware updates and directory→symlink transitions for repo-managed names.
21. **In-repo transition safety**: legacy source trees under `opencode/skills/` and `_pi/skills/` must remain intact until the installer has been switched to consume canonical `skills/` content. Only after that switch lands may those duplicate trees be removed.
22. **Duplicate merge strategy**: when the same skill exists in multiple repo trees, Phase 1 must compare payloads and choose a canonical winner explicitly. Prefer the richer payload or manually merged superset; record the decision when content differs materially.
23. **Home-install comparison rule**: when a same-name skill already exists in `~/.agents/skills`, inspect it as a reference input before overwrite to determine whether the repo candidate is missing important payload. Do not treat home-directory content as authoritative; only backport if the richer payload is clearly the intended canonical skill.
24. **Executable/runtime audit**: before standardizing on one shared installed copy for a promoted skill, Phase 1 must explicitly check whether that skill assumes consumer-specific writable state, bootstrap state, or conflicting runtime dependencies.
25. **Skill payload completeness**: a complete installable-skill payload includes `SKILL.md` plus any present `scripts/`, `references/`, `lib/`, assets, and root-level config/runtime files such as `package.json`, `run.js`, `tsconfig.json`, or similar.
26. **Repo-local-only criteria**: a skill is repo-local-only if it clearly depends on `ai-configs`-specific paths/workflows, internal-only tooling not expected in downstream environments, or is explicitly marked as template/experimental/internal rather than installable.
27. **Initial exclude list from shared promotion**:
    - `opencode-conversation-reviewer` — OpenCode-specific, depends on `opencode db`
    - `template` — scaffold placeholder, not an installable skill
28. **Initial Pi-consumer-only candidates requiring classification**:
    - `cmd-debug`
    - `cmd-research`
    - `dev-plan`
    - `ralph-run`
    - `ralph-run-simple`
    - `review-change`
    - `review-change-integrate`
29. **Migration rollback rule**: a failed migration must not leave partial state. Per-skill migration must either complete successfully or leave the original destination intact/recoverable with a clear actionable error.
30. **Failure-injection contract**: shared-sync must support a test-only failpoint via environment variable `AI_CONFIGS_FAILPOINT`, with at least `after-backup:<skill-name>` supported so rollback can be verified deterministically.
31. **Rollback procedure**: the operator recovery path is to restore the affected skill from `~/.agents/skill-backups/ai-configs/<timestamp>/<skill-name>/` and rerun `./install.sh --skills` after resolving the underlying failure.
32. **Idempotency**: rerunning `./install.sh --skills` without input changes must not create duplicate links, duplicate backups, or mutate preserved foreign entries.
33. **Documentation path contract**: docs and command examples should describe `~/.agents/skills` as the canonical runtime location. Consumer-specific locations may appear only as compatibility-link destinations where applicable.
34. **Platform assumption**: this migration targets Unix-like environments where `~` home paths and symlink semantics are standard. Windows-native path/symlink support is out of scope for this plan.

## Migration inventory (initial)

### Already canonical in `skills/`
- `linear`
- `product-principles`

### Candidate promotions from `.agents/skills/`
- `dependency-selection`

### Candidate promotions from `opencode/skills/`
- `algorithmic-art`
- `brand-guidelines`
- `canvas-design`
- `ccore`
- `design-skill`
- `doc-coauthoring`
- `doct-document-ops`
- `docx`
- `frontend-design`
- `internal-comms`
- `linear`
- `mcp-builder`
- `pdf`
- `planning-workflow`
- `playwright-skill`
- `pptx`
- `product-principles`
- `repo-agents-bootstrap`
- `rust-engineer`
- `skill-creator`
- `slack-gif-creator`
- `theme-factory`
- `vercel-react-best-practices`
- `web-artifacts-builder`
- `web-design-guidelines`
- `webapp-testing`
- `xlsx`

### Candidate promotions from `_pi/skills/`
- `cmd-create-handoff`
- `cmd-create-pr`
- `cmd-debug`
- `cmd-graduate`
- `cmd-research`
- `cmd-resume-handoff`
- `cmd-start-linear-issue`
- `cmd-start-linear-issue-branch`
- `dev-plan`
- `doct-document-ops`
- `product-principles`
- `ralph-run`
- `ralph-run-simple`
- `review-change`
- `review-change-integrate`
- `sentry-cli`

### Pre-classified non-shared exceptions
- `opencode/skills/opencode-conversation-reviewer`
- `opencode/skills/template`

## Acceptance criteria

1. `skills/` is the only authoritative installable-skill source tree in the repo.
2. Installable skills sync into `~/.agents/skills` via the repo's canonical shared-skill sync path.
3. `skills/install-matrix.json` exists and deterministically drives consumer fan-out/filtering.
4. Claude and OpenCode expose only consumer-compatible installable skills through per-skill symlinks rather than copied skill directories.
5. Pi uses its native `~/.agents/skills` discovery for shared skills and does not receive duplicate mirrored shared entries under `~/.pi/agent/skills`.
6. OMP command/templates that rely on installable skill scripts resolve them through `~/.agents/skills/...` and do not introduce an unverified `~/.omp/agent/skills` contract.
7. Pre-existing foreign skills in `~/.agents/skills` are preserved when names do not collide.
8. Same-name collisions with foreign skills are handled predictably via backup + replace, not silent destruction.
9. Existing foreign entries in `~/.claude/skills` and `~/.config/opencode/skills` are preserved when they are not repo-managed names.
10. Full skill payloads still work after relocation, including scripts and relative references.
11. No shared-skill docs or command templates describe tool-specific copied skill locations as the primary source of truth.
12. `--skills`, `--default`, and `--all` are all verified to result in the expected shared-skill availability.
13. `--claude`, `--opencode`, `--pi`, and `--omp` explicitly reuse the shared-sync path where they claim or rely on installable skill availability.
14. Idempotent reruns do not create duplicate links, duplicate backups, or mutate preserved foreign entries.
15. Migration failure leaves the system in a consistent, recoverable state with actionable errors.
16. At least one relocated skill with relative-path assets is functionally smoke-tested from `~/.agents/skills`.

## BDD scenarios

### BDD-1: Canonical repo source
**Given** installable skills currently live in multiple in-repo trees  
**When** the consolidation is complete  
**Then** each installable skill has exactly one authoritative source under `skills/`  
**And** any remaining non-authoritative legacy paths are temporary compatibility remnants scheduled for cleanup.

### BDD-2: Shared install
**Given** a machine without existing shared skill installs  
**When** `bash ./install.sh --skills` runs  
**Then** the installer populates `~/.agents/skills` from the repo's `skills/` tree  
**And** it does not wipe unrelated foreign skills already present there.

### BDD-3: Claude/OpenCode compatibility fan-out
**Given** Claude and OpenCode are installed  
**When** shared-skill sync finishes  
**Then** `~/.claude/skills/<skill>` and `~/.config/opencode/skills/<skill>` are symlinks to `~/.agents/skills/<skill>` for compatible skills only  
**And** those consumers do not discover Pi-consumer-only or otherwise incompatible skills.

### BDD-4: Pi native shared-skill discovery
**Given** a fresh Pi install  
**When** shared-skill sync and Pi installation finish  
**Then** Pi discovers shared skills via its native `~/.agents/skills` global path  
**And** the installer does not create duplicate mirrored shared entries under `~/.pi/agent/skills`.

### BDD-5: OMP canonical path usage
**Given** OMP command/templates need to call scripts inside installable skills  
**When** the plan is fully implemented  
**Then** they call `~/.agents/skills/...` directly  
**And** they do not depend on Pi-only or OpenCode-only copied skill paths.

### BDD-6: Unconfigured consumer skip
**Given** one or more consumer config directories are absent  
**When** shared-skill sync runs  
**Then** the installer skips compatibility link creation for those missing consumers without error  
**And** still syncs the canonical `~/.agents/skills` store.

### BDD-7: Same-name collision handling
**Given** `~/.agents/skills/<skill>` already exists from a foreign source for a repo-managed skill name  
**When** shared-skill sync runs  
**Then** the existing directory is backed up to the backup location  
**And** the repo-managed version is installed in its place with repo ownership metadata.

### BDD-8: Consumer-directory preservation
**Given** `~/.claude/skills` or `~/.config/opencode/skills` contains foreign entries unrelated to repo-managed skill names  
**When** shared-skill sync runs  
**Then** those foreign entries remain intact  
**And** only repo-managed names are converted to symlinks or updated.

### BDD-9: Idempotent rerun
**Given** the shared-skill sync has already completed successfully  
**When** `./install.sh --skills` runs again with no input changes  
**Then** the resulting layout is unchanged  
**And** no duplicate links or duplicate backups are created.

### BDD-10: Migration rollback
**Given** migration of a copied install fails after backup but before final replacement  
**When** the installer exits  
**Then** the destination is either fully migrated or left recoverable/intact  
**And** the error message explains the exact next step and backup location.

### BDD-11: Documentation alignment
**Given** onboarding and quickstart docs for Claude, Pi, OMP, and OpenCode  
**When** a user follows the updated guidance  
**Then** the docs consistently describe `skills/` as the repo source of truth and `~/.agents/skills` as the installed source of truth  
**And** any consumer-specific paths are clearly labeled as compatibility wiring rather than primary install targets.

## Progress

- [x] P1 - Classify universal vs consumer-specific vs repo-local skills, create `skills/install-matrix.json`, and promote canonical installable skill sources into `skills/` without breaking current installers.
- [x] P2 - Refactor shared-skill sync, destructive-path replacement, collision handling, failpoint testing, and consumer ownership rules around `~/.agents/skills`.
- [x] P3 - Update docs/commands and remove obsolete duplicate source trees after installer cutover.
- [x] P4 - Validate migration behavior, preservation rules, consumer compatibility wiring, and final repo alignment.

## Resume instructions (agent)

- Read this plan fully before editing anything.
- Preserve unrelated dirty worktree changes already present in the repo.
- Start with the first unchecked item in `## Progress`.
- Complete work phase-by-phase in order; do not skip ahead.
- Run each phase's `### Verify` steps before marking that phase complete.
- Update `## Progress` immediately after completing a phase.
- Record any execution-time exceptions or consumer-specific deviations in `## Decisions / Deviations log`.

## Phase-by-phase execution plan

## Phase 1 - Canonicalize skill sources without breaking current installer paths

### End State
- Installable skill content has been promoted into canonical directories under `skills/`.
- Universal installable, consumer-specific installable, and repo-local-only skills are explicitly classified.
- `skills/install-matrix.json` exists as the durable compatibility manifest.
- Legacy source trees needed by the old installer remain available until Phase 2 switches installer inputs.

### Tests first
- Capture baseline source inventory and payload completeness evidence:
  - `find skills .agents/skills opencode/skills _pi/skills -maxdepth 3 -type f | sort`
  - `find skills .agents/skills opencode/skills _pi/skills -maxdepth 2 -name 'SKILL.md' | sort`
- For representative complex skills (for example `doct-document-ops`, `playwright-skill`), capture file lists before moving:
  - `find opencode/skills/playwright-skill -type f | sort`
  - `find opencode/skills/doct-document-ops -type f | sort`
- Capture currently stale path references that Phase 3 must eliminate:
  - `git grep -n 'opencode/skills/\|_pi/skills/' README.md AGENTS.md _pi opencode install.sh OPENCODE_ONBOARDING.md`
- Where same-name home installs exist for repo candidates, capture their file lists as reference inputs before deciding canonical payloads.

### Work
- Audit each skill directory in `opencode/skills/`, `_pi/skills/`, and `.agents/skills/` using the locked compatibility classes and repo-local criteria.
- Explicitly move `.agents/skills/dependency-selection` to `skills/dependency-selection` if it remains installable after classification.
- Promote installable skills into `skills/` by moving full payloads, not partial files.
- Keep the initial exclude list out of `skills/` unless later evidence proves they are truly installable.
- Classify Pi-originated skills that depend on Pi-only APIs/extensions as **consumer-specific installable** rather than universal.
- Include `cmd-research` in that Pi-consumer-only check.
- Deduplicate known overlaps (`linear`, `product-principles`, `doct-document-ops`) and any others found during the audit.
- When duplicates differ materially, choose a canonical source explicitly, merge any missing payload pieces, and record the decision in `## Decisions / Deviations log`.
- Inspect same-name home-installed variants for richer payloads worth backporting into the canonical repo source.
- Audit whether promoted executable skills are safe as one shared installed copy across consumers or need reclassification/exclusion.
- Write `skills/install-matrix.json` with at least: skill name, class, allowed consumers, canonical source, and notes.
- Preserve legacy repo paths that current installers still depend on until Phase 2 completes the installer cutover.

### Expected files
- `skills/**`
- `skills/install-matrix.json`
- `.agents/skills/**`
- `opencode/skills/**`
- `_pi/skills/**`

### Verify
- `find skills -maxdepth 2 -name 'SKILL.md' | sort`
- `test -f skills/install-matrix.json`
- Confirm each promoted installable skill now has a canonical home under `skills/`.
- Confirm excluded/non-shared candidates such as `opencode-conversation-reviewer` and `template` were not promoted.
- Confirm Pi-only API-dependent skills are marked/classified so they will not be exposed to incompatible consumers later.
- Manually inspect one moved complex skill to confirm complete payload preservation (`SKILL.md`, scripts, refs, config/runtime files).
- Confirm current installer source paths still exist until Phase 2 switches them.

## Phase 2 - Refactor shared-skill sync, destructive-path replacement, and consumer ownership rules

### End State
- Shared-skill sync installs canonical content into `~/.agents/skills` additively.
- `--skills` is explicitly tested as the canonical sync path.
- Default/all and relevant single-surface installs invoke the shared-skill sync helper.
- Claude/OpenCode receive per-skill symlink wiring for compatible skills only.
- Pi no longer duplicates shared skills into `~/.pi/agent/skills`.
- Ownership, backup, directory→symlink transitions, failpoint testing, and rollback rules are explicit in installer behavior.

### Tests first
- Establish a temp-home smoke harness that reuses one temp `HOME` across the full verify block:
  - `TMP_HOME="$(mktemp -d)"`
  - `mkdir -p "$TMP_HOME/.claude/skills/custom-local" "$TMP_HOME/.config/opencode/skills/custom-local" "$TMP_HOME/.pi/agent" "$TMP_HOME/.omp/agent"`
  - `mkdir -p "$TMP_HOME/.agents/skills/external-skill"`
  - `printf 'external' > "$TMP_HOME/.agents/skills/external-skill/SKILL.md"`
  - Seed a mandatory same-name collision for one repo-managed skill, e.g. `linear`, in `~/.agents/skills`.
  - Seed an existing real-directory consumer entry for one repo-managed skill name (e.g. `~/.claude/skills/linear`) so directory→symlink replacement is exercised.
- Audit `install.sh` for hidden old-path dependencies before modifying behavior:
  - `git grep -n '~/.claude/skills\|~/.config/opencode/skills\|~/.pi/agent/skills' install.sh`

### Work
- Refactor `install.sh` so shared-skill syncing is centralized in one helper used by:
  - `--skills`
  - `--default`
  - `--all`
  - `--claude`
  - `--opencode`
  - `--pi`
  - `--omp`
- Change the canonical shared install destination from `~/.claude/skills` to `~/.agents/skills`.
- Install repo-managed skill names additively into `~/.agents/skills`; do not wipe that directory.
- Add `.ai-configs-managed.json` ownership markers.
- Implement same-name collision handling with backup + replace for foreign occupants of repo-managed names.
- Implement test-only failure injection via `AI_CONFIGS_FAILPOINT`, with at least `after-backup:<skill-name>` supported.
- Replace destructive consumer-directory `rm -rf` behavior with per-skill ownership-aware management.
- Support directory→symlink transition for existing repo-managed names in consumer directories.
- Implement per-skill compatibility symlinks only for proven compatible consumers:
  - `~/.claude/skills/<skill> -> ~/.agents/skills/<skill>`
  - `~/.config/opencode/skills/<skill> -> ~/.agents/skills/<skill>`
- Filter consumer-specific installable skills out of incompatible Claude/OpenCode fan-out using `skills/install-matrix.json`.
- Update `install_pi()` so it stops copying shared skills from `_pi/skills/`; if Pi-consumer-only skills still remain outside the shared installable set, manage only those explicitly and non-destructively.
- Update `install_omp()` and related OMP docs/templates only as needed to reference `~/.agents/skills` directly; do not invent `~/.omp/agent/skills`.
- Ensure consumer installers only manage repo-owned shared-skill entries and do not wipe unrelated entries in consumer skill directories.
- Update `print_usage()` and installer messaging to describe the new contract truthfully.

### Expected files
- `install.sh`

### Verify
Run against a single reused temp home:
- `TMP_HOME="$(mktemp -d)"`
- `mkdir -p "$TMP_HOME/.claude/skills/custom-local" "$TMP_HOME/.config/opencode/skills/custom-local" "$TMP_HOME/.pi/agent" "$TMP_HOME/.omp/agent" "$TMP_HOME/.agents/skills/external-skill"`
- `printf 'external' > "$TMP_HOME/.agents/skills/external-skill/SKILL.md"`
- `mkdir -p "$TMP_HOME/.agents/skills/linear" && printf 'foreign-linear' > "$TMP_HOME/.agents/skills/linear/SKILL.md"`
- `mkdir -p "$TMP_HOME/.claude/skills/linear" && printf 'old-claude-linear' > "$TMP_HOME/.claude/skills/linear/SKILL.md"`
- `HOME="$TMP_HOME" bash ./install.sh --skills`
- `test -d "$TMP_HOME/.agents/skills"`
- `test -f "$TMP_HOME/.agents/skills/external-skill/SKILL.md"`
- Verify the `linear` collision backup exists at `~/.agents/skill-backups/ai-configs/<timestamp>/linear/`.
- Verify the active `linear` install contains `.ai-configs-managed.json`.
- Verify `custom-local` remains intact in both `~/.claude/skills` and `~/.config/opencode/skills`.
- Verify `~/.claude/skills/linear` is now the expected symlink target if `linear` is consumer-compatible.
- Verify consumer-incompatible Pi-only skills are absent from Claude/OpenCode fan-out.
- Verify Pi did not receive duplicate mirrored shared entries under `~/.pi/agent/skills`.
- `TARGET_ROOT="$(mktemp -d)"`
- `HOME="$TMP_HOME" bash ./install.sh --default "$TARGET_ROOT"`
- Re-verify additive preservation, collision behavior, and idempotency after default-mode installation.
- Run a deterministic rollback test using `AI_CONFIGS_FAILPOINT=after-backup:linear` and confirm the destination remains recoverable/intact with an actionable error message.

## Phase 3 - Update docs/commands and remove obsolete duplicate source trees

### End State
- Docs and command templates consistently describe `skills/` and `~/.agents/skills` as the source-of-truth model.
- Stale Pi/OpenCode/Claude copied-path instructions are removed or clearly labeled as compatibility-only.
- After the installer cutover, obsolete duplicate repo skill trees are removed.

### Tests first
- Capture stale path references across all known touched surfaces:
  - `git grep -n '~/.claude/skills\|~/.config/opencode/skills\|~/.pi/agent/skills\|opencode/skills/\|_pi/skills/' README.md SETUP.md AGENTS.md _pi opencode _omp OPENCODE_ONBOARDING.md install.sh`
- Capture install-instruction-specific references separately:
  - `git grep -n 'install.*to.*~/\|cp -r .*skills' README.md SETUP.md AGENTS.md _pi opencode _omp OPENCODE_ONBOARDING.md`
- Perform a pre-deletion impact assessment for in-repo references before removing large duplicate trees.

### Work
- Update root docs:
  - `README.md`
  - `SETUP.md`
  - `AGENTS.md`
- Update the `AGENTS.md` Pi settings example explicitly from `{"skills": [".agents/skills", "opencode/skills"]}` to the final supported local-dev form based on canonical repo `skills/` plus any repo-local-only `.agents/skills` usage.
- Update Pi docs:
  - `_pi/README.md`
- Update OpenCode docs:
  - `OPENCODE_ONBOARDING.md`
  - `opencode/OPENCODE_ONBOARDING.md`
  - `opencode/QUICKSTART.md`
- Update shared-script command templates to use `~/.agents/skills/...`:
  - `_omp/commands/cmd:send-plan-to-doct.md`
  - `_pi/prompts/cmd:send-plan-to-doct.md`
  - `opencode/commands/cmd:send-plan-to-doct.md`
- Update moved skill docs that still reference stale install locations, especially `playwright-skill`.
- Remove obsolete duplicate source trees from `opencode/skills/` and `_pi/skills/` only after Phase 2 has fully switched installer inputs to canonical `skills/`.
- Remove `.agents/skills/dependency-selection` after its canonical promotion if it is no longer repo-local.
- Apply large-tree cleanup in discrete subtree-scoped edits so deletions are auditable and reversible during implementation review.
- Add a migration note warning that external scripts or CI outside this repo may need path updates if they referenced old repo trees directly.

### Expected files
- `README.md`
- `SETUP.md`
- `AGENTS.md`
- `_pi/README.md`
- `OPENCODE_ONBOARDING.md`
- `opencode/OPENCODE_ONBOARDING.md`
- `opencode/QUICKSTART.md`
- `_omp/commands/cmd:send-plan-to-doct.md`
- `_pi/prompts/cmd:send-plan-to-doct.md`
- `opencode/commands/cmd:send-plan-to-doct.md`
- moved skill docs under `skills/**`
- `opencode/skills/**`
- `_pi/skills/**`
- `.agents/skills/**`

### Verify
- `git grep -n '~/.claude/skills\|~/.config/opencode/skills\|~/.pi/agent/skills\|opencode/skills/\|_pi/skills/' README.md SETUP.md AGENTS.md _pi opencode _omp OPENCODE_ONBOARDING.md skills install.sh`
- Confirm remaining matches, if any, are intentional compatibility explanations rather than primary install/source-of-truth instructions.
- Manually inspect the doct publish command docs and one moved skill doc to confirm they now point at `~/.agents/skills/...`.
- Confirm obsolete duplicate source trees have been removed only after installer cutover.

## Phase 4 - Validate migration behavior and final repo alignment

### End State
- The repo and installer reflect a single installable-skill model.
- Installable skills are available consistently through the proven consumer contracts.
- Verification proves preservation, safety, idempotency, and functional path integrity rather than only happy-path file layout.

### Tests first
- Reuse the temp-home harness from Phase 2.
- Add failure-oriented checks: dangling symlinks, preserved foreign skills, no Pi duplicate mirror, and no stale primary install-path docs.

### Work
- Run the updated installer in a clean temp `HOME` and inspect the resulting layout.
- If practical, run the installer in the real environment only after temp-home validation passes.
- Verify at least one relocated installable skill with relative-path assets still works from `~/.agents/skills`.
- Perform a final repo audit for:
  - stale duplicate source trees,
  - stale copied-path documentation,
  - stale command templates using tool-specific shared-skill paths,
  - stale Pi config examples pointing at old repo-local skill trees.
- Record any intentional exceptions or follow-up work in `## Decisions / Deviations log`.

### Expected files
- no new permanent files required unless implementation adds installer tests

### Verify
- Reuse `TMP_HOME` across the entire verification flow.
- `TARGET_ROOT="$(mktemp -d)"`
- `HOME="$TMP_HOME" bash ./install.sh --skills`
- `HOME="$TMP_HOME" bash ./install.sh --all "$TARGET_ROOT"`
- `find "$TMP_HOME/.agents/skills" -maxdepth 2 -name 'SKILL.md' | sort`
- `find "$TMP_HOME/.claude/skills" -mindepth 1 -maxdepth 1 -type l | sort`
- `find "$TMP_HOME/.config/opencode/skills" -mindepth 1 -maxdepth 1 -type l | sort`
- Confirm no mirrored shared entries were created under `~/.pi/agent/skills`.
- If any Pi-consumer-only skills remain outside the shared installable set, confirm `~/.pi/agent/skills` contains only those entries and no duplicated shared skills.
- `find "$TMP_HOME/.claude/skills" "$TMP_HOME/.config/opencode/skills" -maxdepth 1 -type l ! -exec test -e {} \; -print`
- `test -f "$TMP_HOME/.agents/skills/external-skill/SKILL.md"`
- If `doct-document-ops` remains installable after Phase 1 classification, run a safe smoke check against its relocated script path; otherwise perform the same smoke check with another guaranteed installable skill that includes relative-path assets.
- `git grep -n 'opencode/skills/\|_pi/skills/' README.md SETUP.md AGENTS.md _pi opencode _omp OPENCODE_ONBOARDING.md skills install.sh`
- `git grep -n 'install.*to.*~/\|cp -r .*skills' README.md SETUP.md AGENTS.md _pi opencode _omp OPENCODE_ONBOARDING.md skills install.sh`
- Final manual audit confirms the remaining references match the locked decisions.

## Verification strategy

Primary verification is shell-level because the work is mostly file-layout, installer, and documentation contract changes.

Execution-time verification must prove:
1. **Repo reality**: `skills/` is the only authoritative installable-skill source tree.
2. **Installer correctness**: shared-skill sync populates `~/.agents/skills` additively and wires Claude/OpenCode correctly.
3. **Single-surface correctness**: `--skills`, `--claude`, `--opencode`, `--pi`, and `--omp` all reuse the shared-sync path where they claim or rely on installable skill availability.
4. **Default/all correctness**: common install flows result in installable-skill availability, not just `--skills`.
5. **Pi correctness**: Pi relies on native `~/.agents/skills` discovery for shared skills and does not receive duplicate mirrored shared entries.
6. **Non-repo preservation**: foreign skills with different names survive installer runs.
7. **Collision safety**: same-name collision backup/replace is exercised and verified explicitly.
8. **Consumer-directory preservation**: foreign consumer-directory entries survive while repo-managed names transition correctly.
9. **OMP correctness**: OMP command/templates reference the canonical shared path without inventing a false native skill surface.
10. **Rollback safety**: partial failures do not leave silently corrupted destination state.
11. **Idempotency**: reruns do not create duplicate links, duplicate backups, or drift.
12. **Functional path integrity**: at least one relocated installable skill with relative-path assets still works from `~/.agents/skills`.
13. **Doc alignment**: no primary docs/commands describe copied tool-specific shared-skill locations as the source of truth.

## Delivery order

1. Classify/promote canonical installable skill sources first, but keep legacy installer-dependent repo paths until cutover.
2. Switch installer/shared-sync behavior and destructive-path replacement second.
3. Update docs/commands and remove obsolete duplicate trees third.
4. Run final validation last.

## Non-goals

- Redesigning skill behavior beyond relocation/path/frontmatter/reference fixes required by consolidation and compatibility classification.
- Changing prompts, agents, or extensions unrelated to installable-skill installation.
- Introducing an unverified OMP-native skill directory contract.
- Mirroring shared skills into `~/.pi/agent/skills` when Pi natively discovers `~/.agents/skills`.
- Implementing Windows-native path/symlink support.
- Cleaning unrelated dirty worktree changes that predate this plan.

## Decisions / Deviations log

- Initial planning decision: treat `install.sh --skills` as the repo's shared-skill sync entrypoint because no standalone `skills.sh` exists in this repo today.
- 2026-04-02 (P1): Promoted 42 installable skills into canonical `skills/` directories and wrote `skills/install-matrix.json` as the durable classification manifest while preserving legacy source trees for Phase 2 installer cutover.
- 2026-04-02 (P1): Duplicate audits found `linear`, `product-principles`, and `doct-document-ops` copies to be byte-identical across their legacy trees; retained existing `skills/` copies for `linear` and `product-principles`, and promoted `opencode/skills/doct-document-ops` as the canonical `skills/doct-document-ops` source.
- 2026-04-02 (P1): Classified `cmd-debug`, `cmd-research`, `dev-plan`, `ralph-run`, `ralph-run-simple`, `review-change`, and `review-change-integrate` as Pi-only consumer-specific installable skills because they depend on Pi subagent orchestration.
- 2026-04-02 (P1): Excluded transient `opencode/skills/playwright-skill/.temp-execution-1768143037101.js` from the canonical payload; preserved the rest of the runtime files (`SKILL.md`, `run.js`, `package*.json`, `lib/`, `prisma/`).
- 2026-04-02 (P1 review fix): Same-name repo-candidate installs were present under `~/.agents/skills` for `ccore`, `frontend-design`, `skill-creator`, `theme-factory`, `vercel-react-best-practices`, and `web-design-guidelines`; the richer home-installed payloads for `skill-creator` and `vercel-react-best-practices` were backported into `skills/` before Phase 2 backup/replace work to avoid shipping regressions, while the remaining overlaps did not provide clearly authoritative payload additions.
- 2026-04-02 (P1 low-risk deferral): Home-installed overlaps for `ccore`, `frontend-design`, `theme-factory`, and `web-design-guidelines` still differ in text/metadata-level content, but review found no missing functional payload that would make Phase 2 unsafe; defer any editorial harmonization unless later phases surface compatibility evidence.
- 2026-04-02 (P2 verify correction): Updated the Phase 2/4 `--default` and `--all` verification commands to install into a temp target directory rather than the repo root, because running them without an explicit target would mutate the already-dirty working tree and violate the plan's preservation constraint.
- 2026-04-02 (P2): Refactored `install.sh` to sync canonical installable skills into `~/.agents/skills` with `.ai-configs-managed.json` ownership markers, backup+replace handling for foreign same-name collisions, `AI_CONFIGS_FAILPOINT=after-backup:<skill>` rollback coverage, Claude/OpenCode per-skill compatibility links filtered by `skills/install-matrix.json`, and Pi cleanup that stops mirroring shared skills into `~/.pi/agent/skills`.
- 2026-04-02 (P2 review fix): Consumer compatibility rewiring now backs up foreign same-name entries in `~/.claude/skills` and `~/.config/opencode/skills` before replacement/removal, eliminating the silent data-loss path left by unconditional `rm -rf` consumer entry transitions.
- 2026-04-02 (P3): Updated root/Pi/OpenCode docs plus doct publish command templates to describe `skills/` and `~/.agents/skills` as canonical, rewired doct helper examples to `~/.agents/skills/...`, updated the canonical `skills/playwright-skill` docs for the shared install model, removed duplicate trees from `_pi/skills/`, removed promoted duplicates from `opencode/skills/` while preserving the repo-local-only `opencode-conversation-reviewer` and `template` directories, and removed the obsolete `.agents/skills/dependency-selection` copy.
- 2026-04-02 (P3 review fix): Re-synced the OMP, Pi, and OpenCode `cmd:send-plan-to-doct` templates so all three surfaces keep the same `~/.agents/skills` helper path, REST fallback instructions, and auth recovery guidance instead of drifting after the path migration.
- 2026-04-02 (P3 verify): Remaining Phase 3 grep matches are intentional compatibility-path explanations (`~/.config/opencode/skills`, `~/.pi/agent/skills`) plus the README migration warning about legacy `opencode/skills/...` and `_pi/skills/...` references; no primary source-of-truth instructions still point at copied legacy skill trees.
- 2026-04-02 (P4): Ran the final temp-home validation flow (`./install.sh --skills`, then `./install.sh --all <temp-target>`) with preserved foreign skills, collision backups, Claude/OpenCode compatibility links, no Pi shared-skill mirroring, no dangling consumer symlinks, and a relocated `doct-document-ops` script smoke check from `~/.agents/skills`; skipped a real-HOME installer run to avoid mutating the operator's active workstation during this already-dirty migration branch.
- 2026-04-02 (P4 verify follow-up): Re-ran the relocated `doct-document-ops` smoke check against the shipped executable `~/.agents/skills/doct-document-ops/scripts/publish-coding-plan.sh --help`; an initial ad hoc probe against a non-existent `doct-helper.js` path was not part of the canonical payload and was discarded.

## Plan changelog

- 2026-04-02: Initial plan created from the shared-skills handoff, current installer/docs audit, and user request for a single repo location plus symlink-based consumer compatibility.
- 2026-04-02: Integrated first multi-model review feedback. Narrowed consumer wiring to a proven-contract matrix, removed blanket Pi/OMP symlink assumptions, added additive ownership/collision/rollback rules, fixed default/all installer semantics, tightened phase ordering, added external-skill preservation requirements, and strengthened verification gates.
- 2026-04-02: Integrated second multi-model review feedback. Added explicit universal vs consumer-specific vs repo-local classification, same-name collision testing, consumer-directory preservation and directory→symlink transition checks, explicit `--skills` verification, `dependency-selection` promotion, duplicate-merge strategy details, and functional smoke validation for relocated relative-path assets.
- 2026-04-02: Integrated third multi-model review feedback. Corrected the Pi discovery model to use Pi's documented native `~/.agents/skills` support, added concrete marker/backup/failpoint contracts, made `skills/install-matrix.json` the durable compatibility manifest, expanded acceptance criteria to cover idempotency and single-surface installs, clarified Pi-consumer-only handling, and strengthened rollback plus foreign-entry preservation requirements.
