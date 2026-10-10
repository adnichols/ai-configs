# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Changed

- `cmd-create-pr` defers to a repository-specific PR skill. When any guidance (an instruction file, a repo-local skill, a plan or handoff, or the operator) routes a repository's PR work to its own skill, the agent follows that skill for the whole PR and does not combine the two; only this skill's authority boundary still applies. The description now limits it to repositories without their own PR skill. The first case is ccore2's `ccore2-pr` (Nodaste-Lab/ccore2#776).

- `orchestrate` treats an operator's approval of a design, template, prototype or decision as covering the spec and ADR text that only records it, including amendments to the earlier ADRs that the design reverses. The driver checks that text itself, with the oracle when doubtful, and sends wording problems back to the worker; it posts a card only for a product choice nobody has approved, and the card names only that choice. The worker brief makes workers report such text as `IN_PROGRESS` for the driver instead of asking the operator. Operator ruling 2026-10-10 23:04Z, after ADR 0113 (Katie's Settings template) was carded a second time.

- `orchestrate` requires the driver to have the oracle challenge every Needs-you card before posting it, including product decisions and credential or access asks. A claimed blocker is re-tested through the worker's actual launch path and session, not a separate diagnostic shell, and `Decide:` records the oracle's verdict. Quoted product text in an approval ask is checked against `apps/`, `packages/` or `spec/` (and a live lab when available), never a prototype, and cited by file:line. "Asking the operator" drops the sentence telling the driver to post nothing for non-product questions. Operator-approved text (2026-10-09, dashboard thread 32a009ff).

- `orchestrate` dashboards show a Worker column in the active table, labeling the ledger's `Workspace / agent` cell as host, Paseo workspace and agent. The status-table parser no longer splits on an escaped pipe (`\|`) inside a cell, which used to shift cells so the workspace landed in the PR column (from #78, ported from the old `bugbash` copy).

- `orchestrate` dashboards hold the PR column at a fixed 7.5rem width. `dashboard.py` shortens every GitHub PR URL in a cell to `repo#N`, one per line, instead of only a cell holding exactly one URL; a cell with two PR URLs used to print both in full and squeeze the other columns.

- `orchestrate` runs workers on more than one host. A machine-level hosts file (`~/.config/orchestrate/hosts.json`) lists each host's Paseo target, checkouts and admission limits. `scripts/pick_host.py` probes every host's running agents, available memory, swap and load and picks the one with the most room, or exits 3 so the item is `QUEUED`. Remote workers are launched and managed with `paseo --host`, the listener relays their turn endings as `WORKER_TURN_ENDED`, and cleanup runs `worktree_cleanup.py` over ssh. With no hosts file the single-host flow is unchanged.

- `orchestrate` publishing no longer fails with "Argument list too long" on large pages: `dashboard.py` `ava()` sends the JSON body on stdin (`--file -`) instead of `--data`, which covers dashboard and spec diff publishes. Spec diff pages show bare `<tag>` text in a spec (for example `/assets/<rev>/`) as written instead of dropping it as raw HTML (`spec_diff.py` renders through `raw_html_as_text.lua`, because `pandoc -f gfm-raw_html` does not stop the passthrough).

- `orchestrate` spec diff pages (`spec_diff.py`) show each change as one inline diff instead of a Before and After table. A similar changed line is one line with `<del>` and `<ins>` words, unrelated lines are removed and added rows, and the "change in place" view is collapsed for modified files. `SKILL.md` describes the new page.

- `computer-use` (shared and Codex) gains cua-driver browser rules. On Linux, `browser_prepare` with `existing_profile` foregrounds the target window and injects global input, so agents must not use it in background-only or unattended work, must prefer `isolated_new` or `isolated_named` or the native background action ladder, and must never retry a failed `browser_prepare` on the user's desktop. `route: global_input` on a native click is a transport label, verified with a fresh state and screenshot. Typed grants can end about 5 minutes after preparation (cause unconfirmed), so agents re-check binding before typed actions instead of rerunning `browser_prepare`.

- `orchestrate` asks the operator only for product behavior decisions, meaning what users experience or what the product does. Technical choices, design trade-offs inside a settled direction, where to file findings, lab and access chores, tooling and process questions, and internal-infrastructure risk calls go to the oracle first, or the driver or worker decides them with tools. `SKILL.md` gains an "Asking the operator" section: the driver records the oracle's answer and whether it accepted it, re-screens every worker `NEEDS_OPERATOR` before posting a card, and answers non-product asks itself. The worker brief tells workers to consult the oracle before ending a turn with `NEEDS_OPERATOR`, to reserve it for product decisions or irreversible operator-reserved actions, and to include the oracle's recommendation in `question:`. A Waiting-on-you card's `Problem:` says why it is a product decision. The card format and `dashboard.py` are unchanged.

- Agents release their lab claims as soon as the work using them is done, with no operator agreement step. Done means every PR using the lab has merged, or the work is abandoned or concluded without a merge (`NOT_REPRODUCED`, `EXPECTED_BEHAVIOR`, duplicate, won't fix, superseded). The claim stays while a PR using it is open or a prototype review is pending. `verified-build` (OMP and Codex) also drops "agreed cleanup" from the exploration path, and renames "Release during agreed cleanup" to "Release when the work is done" and no longer lists a lost claim among the reasons to stop and ask. `worktree-cleanup`, `session-cleanup`, `orchestrate`, and its worker brief drop the operator-agreement condition. The orchestrator releases a worker's claim right after the merge or the concluded report, using `--abandon <reason>` when nothing merged. `worktree_cleanup.py` behavior is unchanged: its preflight never asked for operator agreement. Its `--abandon` help and refusal hint now describe concluded work, and its malformed-claim-file message points to the lab-manager's agent release path for your own orphaned claim instead of the operator. That path is added in ccore2, so the skills refer to it generically.

- `orchestrate` dashboards sort the "All items" table into three tiers, by ID within each: waiting on the operator (a Needs you state, or `waiting on` starting with `operator`), then in progress or blocked, then done. `dashboard.py` sorts the rows itself, so ledger order no longer matters; the chips keep their existing order, which already matches the tiers. `SKILL.md` and the ledger template state the order, and the template tells orchestrators to keep the ledger table in it.

- `orchestrate` Needs-you asks must be `###` cards. `dashboard.py` drops the fallback that rendered top-level bullets as title-only cards and exits 2, naming the card format, when `## Waiting on you` holds anything but `###` cards, a card has no `Problem:` (or `Broken:`) or no `Decide:`, or a card uses bold. The ledger template and `SKILL.md` state the rule: the heading names the problem and the change, `Problem:` is plain technical-founder language, `Decide:` says exactly what the operator must do or choose.

- Work tracker dashboards publish to the Ava Development Space (`spc_16ef6d824e21402b9a42560b13436034`), which holds development tracking, instead of Nodaste. An open tracker is a document directly inside the root folder `Coding Work`; when the ledger's mode is `CONCLUDED`, `dashboard.py` moves it into `Archive / Coding Work`, creating the folders when missing. A remembered folder id is reused only while it is still a folder at that exact path, and the refusal to use a root folder outside the old `Coding Work / Bug Bash` path is removed.

- `bugbash` is renamed `orchestrate` (`/orchestrate`) and covers features and other changes as well as bugs. Each run is a work tracker that lasts until the operator says done, may run in parallel with others, and publishes its dashboard to the Ava Development Space as a document directly inside `Coding Work`, titled with the weekday and date or the operator's theme. State moves to `~/.local/state/orchestrate/<YYYYMMDD>-<slug>/` with item files under `items/`; items are `WI-NN` on `orchestrate/wi-NN-<slug>` branches. Workers route each item by its description through ADN mode and verify it through verified-build, which picks `BUG_FIX` or `FEATURE_CHANGE`; the status block is `WORKER_STATUS` and names the chosen playbook and mode. Needs-you cards use `Problem:` and the status table's column is `Kind`; `spec_diff.py` takes `--tracker-dir`. `bugbash` stays as an indefinite alias: its `SKILL.md` hands off to `orchestrate`, and its `scripts/` and `references/` are links to the orchestrate copies, so commands in existing bug bash ledgers keep working. The scripts still read a bug bash ledger's `Type` column and `Broken:` field, and `spec_diff.py` still accepts `--bugbash-dir`.

- No agent deploys to production, asks whether to, or offers to. The `AGENTS.md` for OMP, Codex, and Devin drops "production deployment requires separate authorization" and states an absolute prohibition: deploy and verify only in a lab, and after a merge say the change is merged and that production deploy is a human operator action. `bugbash` states the same in Merge authority, the merged notice, and Boundaries. The bugbash worker brief and `verified-build` (OMP and Codex) say the lab is the only deploy target. Merge authority wording is unchanged.

- `bugbash` merges without asking. Once a PR is validated at its exact head, every operator decision on the issue (spec or ADR diff, prototype, product or scope choice) is answered, and every gate passes, the driver merges it and runs `worktree-cleanup`, then sends a short merged notice. The "approve BB-NN" review packet and the `APPROVED` state are removed; the operator is asked only for what the gates cannot settle. Merging after the base moved now requires checking what landed since the validated base for overlap in files, migrations, or ADR numbers.

- Every merging skill stops passing `--delete-branch` to `gh pr merge`: `bugbash`, the Paseo `pr-merge-gates` bot skill, the Hermes autobuild PR monitor, and the Hermes GitHub PR docs. `bugbash` and `pr-merge-gates` run `worktree-cleanup` after the merge instead of messaging the worker. `session-cleanup` keeps the PR, schedule, and agent inventory and delegates worktree teardown to the script. `verified-build` (OMP and Codex) writes `demos.json` for each published prototype. The Hermes autobuild PR monitor records each PR it merges or auto-merges and runs `worktree-cleanup` on the one local worktree that has the branch checked out once GitHub reports the PR merged, retrying each tick and reporting refusals.

- Agents are told not to use Paseo's built-in browser (the `browser_*` tools) for browser work. The same one-line rule is in the OMP and Codex `AGENTS.md`, the `paseo` and `computer-use` skills (shared and Codex), `verified-build` (OMP and Codex), `prototype`, and the `bugbash` validation gate and worker brief. A gate failure for interaction evidence gathered in Paseo's browser is added to `bugbash`. `_adn` is pinned and unchanged.

- ADN re-pins to cursor/plugins pstack `e43c7ee` (0.15.9). New skills: `correct` finds the mistakes agents keep repeating, including corrections in OMP and Paseo session history, and removes each class with architecture, types, a lint, or a test; `benchmark-checklist` vets a measured perf number and picks Linux or macOS tools by `uname -s`; `principle-explain-the-number` requires a named limiter and ruled-out alternatives before trusting a number. `architect` screens designs for agent contributors and adds four red flags. `perf-issue` uses ordered performance mantras, and `hillclimb` vets its harness with the checklist. Declined items are listed in `_adn/PROVENANCE.md`.

- `verified-build` (OMP and Codex) now requires UI prototypes to look and behave like the target product. Before building one, the worker finds the repository's own prototype template or clickable demo (`AGENTS.md`, `thoughts/prototypes/`, `prototypes/`, template README) and builds from it, reusing its components, tokens, icons, menus, and publish conventions. Only without a template does it build from the product's real DOM and CSS captured from the lab baseline. Screenshots must read as the same product as the lab baseline before publishing, and the prototype note and `run.md` record the template path and commit or why none applied.

- `bugbash` dashboard now fills the full viewport width by default. `references/dashboard-template.html` drops the `max-width:1040px` centered column on `main` and keeps its padding and the 640px mobile rules. The issue table spans the width and long URLs still wrap.

### Removed

- Retired the AI-configs-managed `ava` skill. The Ava CLI owns and reconciles `~/.agents/skills/ava`, `~/.claude/skills/ava`, and `~/.ava/SKILL.md`; `skills/ava` and its install-matrix entry are removed and `ava` joins `DEPRECATED_SHARED_SKILLS`, which removes only copies carrying the ai-configs marker and preserves Ava-owned (`managed-by: ava`) or unmarked skills.

### Added

- Added the shared `worktree-cleanup` skill and `scripts/worktree_cleanup.py`. One idempotent script tears down a finished worktree in a fixed order: preflight (refuses on uncommitted changes, a head that is not the head of a merged PR, or a running agent, unless `--abandon <reason>`), lab claim release with the repo's lab CLI (a failed release keeps the claim file and removes nothing), published demos listed in the new `artifacts/verified-build/<run-id>/demos.json`, Paseo workspace archive (or `git worktree remove`), and the remote branch. It prints a JSON report and exits 0, 2 (refused), 3 (step failed, rerun), or 4 (work left for someone else), and a rerun finishes a partial job or does nothing. This fixes the bugbash case where `gh pr merge --delete-branch` removed the worker's worktree, and the lab claim file with it, before the lab was released.

- `bugbash` now shows spec and ADR changes as a generated diff page instead of quoted wording. `scripts/spec_diff.py REPO --base REF --path spec [--head REF]` reads the changed files from git (a worktree's uncommitted and untracked edits, or a head commit), renders one Ava-safe page with before and after lines per change, the whole file with the change marked, and changed table rows as single rows, then publishes or updates it as a subdocument of the bugbash's dashboard document (`parent_id` from `dashboard.json`'s `plan_id`, verified and moved when the create ignored it) using `dashboard.py`'s Ava helpers. It needs only Python and pandoc, rewrites relative links to GitHub URLs at the commit that holds the target, and writes a `manifest.json` of file hashes so `--check` proves the landed text is byte-identical to what the operator approved. `SKILL.md` and `references/worker-brief.md` require the flow for any `spec/` or ADR proposal and keep the wording out of the "Waiting on you" card. Both also state the rule that every Ava document a bugbash creates is a subdocument of its dashboard, never a sibling.

- `bugbash` now publishes a live Ava dashboard and listens to it. `scripts/dashboard.py <bugbash-dir>` renders `ledger.md` (and only the ledger) through `references/dashboard-template.html`: Needs you cards from `### <ID>: <what's broken> → <what we're fixing>` items with `Broken:`, `Fix:`, `Decide:` and `Links:` fields (written in technical-founder language), state-group counts, the issue table, and the latest eight operator decisions (newest first), with light/dark and narrow layouts. It registers the document once (retry-safe), places it under the root folder path `Coding Work / Bug Bash` of the Space (default Nodaste), found by title through `ava document tree` and created only when missing, never duplicating and refusing a stray root "Bug Bash"; edits in place afterwards; verifies the source with `ava document plan-source`; and exits non-zero when `ava` is missing or unauthenticated. `scripts/listener.py <bugbash-dir> <driver-agent-id>` is a stdlib-only persistent service that polls the dashboard's comment threads every 30s, replies "Received" once per new operator comment (idempotent), and relays it to the driver with `paseo send --no-wait`; it does not use `ava agent listen`, whose scope is the whole Space. The skill starts the listener with the dashboard, records `Listener:` in the ledger, drops the comment heartbeat, republishes on every ledger change, turns dashboard feedback into a skill follow-up, and stops the listener at conclusion.

- Added the shared `bugbash` skill. One conversation collects rapid-fire bug and feature reports with screenshots, enriches each with read-only background research into an issue file under `~/.local/state/bugbash/`, and hands every ready issue to its own Paseo worktree running OMP from the `omp` profile with verified-build and ADN mode. When the operator says done, it switches to orchestration: it relays questions and prototype approvals, presents a review packet per validated PR, merges only on "approve BB-NN", then releases labs and archives worker worktrees. `scripts/collect_images.py` exports pasted screenshots from the OMP or Codex session transcript so workers in other worktrees can read them.

- `bugbash` now requires interactive reproduction (#71). Workers drive the operator's reported interaction in a real browser and record an interaction table (step, expected, observed, evidence) with per-step screenshots or video; DOM counts, render checks, data checks, and static screenshots do not count. The driver bounces `NOT_REPRODUCED`, `EXPECTED_BEHAVIOR`, and `VALIDATED` reports lacking that evidence for the exact reported interaction and inspects it before relaying to the operator. Research briefs phrase reproduction steps as interactions with expected observations.

- Tracked the `paseo-bots` plugin's `pr-merge-gates` skill in `_paseo/bots/skills/`; it was previously only in `~/.paseo/plugin-data/paseo-bots/library/skills/` with no history. `_paseo/install.sh` installs it there on hosts where the plugin has run, backing up a locally edited copy. It adds `ruling-check.py`: each operator ruling in the bot's `journal/aaron-decisions.md` must be `encoded:` in a rule, skill, or check (verified on ccore2 `origin/main`, including a quoted phrase), `transient:`, or `pending:`, and the monitor pass fails until none are pending.

- Added a managed Paseo runtime surface under `_paseo/`: the daemon config deep-merges into `~/.paseo/config.json` (agent profiles merge by name, unmanaged keys preserved, first differing file backed up), `agents.providers.omp.additionalModels` pins `@default` as the default model so profile-less launches resolve OMP's configured `modelRoles.default`, and `agents.skills.selection` is set to `custom`/empty so the daemon stops reverting repo-owned `paseo*` skills at startup. `_paseo/skills/` holds the tuned skill copies installed to `~/.agents`, `~/.claude`, and `~/.codex` skills roots. `install.sh --tools`/`--all` installs locally and streams the bundle to `mbp`/`dever`/`thump` via `scripts/install-paseo-remote-hosts.sh`.

- Added the shared `typesafe-ai` skill (external package `typesafe-ai/skills`) so Codex, Claude, Pi, and Devin get TypeSafe's System One guidance — typed Choice, Score, and Noul questions answered by Jev — instead of prompting an LLM and parsing generated text. It joins the default shared install rather than an optional profile.

- Added ADN Architecture principle `principle-modes-not-exceptions`. Lab, test, CI, and production differences are a designed operating mode parsed at the edge, not hostname or env ifs in product code. Wired into shared and Pi `adn-mode`.

- Always-on writing rule against mannered prose: metaphor and flourish used in place of a direct statement. Catalogued as unslop rule 32, installed into Codex `~/.codex/AGENTS.md`, and added to managed OMP `AGENTS.md` plus ADN/Pi `adn-mode` reply checklists.

- Added a repo-owned `luvus` skill so Codex, Claude, Pi, and Devin can drive Luvus agent panes from inside or outside a managed session.

- Added `adversarial-fix-review` so a claimed bug fix or "this change is necessary" handoff gets a second-model reviewer who must prove the claim from artifacts, not the implementer's brief. Wired from adn-mode and the bug-fix playbook, not from always-on Pi/OMP doctrine.
- Switched managed OMP compaction to an absolute 200k-token threshold (`thresholdPercent: -1`, `thresholdTokens: 200000`), idle compact at 100k after 60s, and pinned Grok `contextWindow` to 200000.
- Upserted DeepInfra Kimi K3 (`deepinfra/moonshotai/Kimi-K3`) into managed `models.json` so it remains available in the Pi catalog.

- Added a Pi `imaging` subagent on GPT-5.6 Luna xhigh so non-vision models can proactively hand screenshots and other visual input to a vision-capable analyst instead of guessing.

- Added a Pi-adapted `adn-mode` (`_pi/skills/adn-mode/SKILL.md`) installed into `~/.pi/agent/skills/adn-mode`, where Pi's skill precedence shadows the shared `~/.agents/skills` copy for Pi sessions only. Same doctrine as the shared/OMP version; the subagent contract uses Pi's `Agent` tool and Pi model routes (`xai/grok-4.6:high` for the Grok role and default code, `synthetic/hf:moonshotai/Kimi-K3:max|high` for the Kimi architect/reviewer roles, DeepSeek Flash for cheap bulk work). The shared ADN playbooks/references payload is assembled underneath it at install time, and skill sync keeps repo-owned `_pi/skills` entries Pi-local instead of promoting them into `~/.agents/skills`.

- Vendored the `cobanov.herdr-ntfysh` Herdr plugin into `tools/herdr-ntfysh` (pinned upstream commit) with two added capabilities: notification titles now use the agent's human-readable session title (`agent get` name, else pane terminal title) instead of bare agent/pane IDs, and `HERDR_NTFY_BODY_LINES=N` appends the last N lines of the agent pane's recent output to the notification body. Both fail safe when the Herdr CLI is unreachable. `herdr/install.sh` now builds, links, and enables the vendored copy (replacing any upstream GitHub-managed install), and keeps the existing plugin config (`.env`) intact.

- Permanent-document disposition in the shared pre-PR path: `run-plan` and `cmd-create-pr` hard-stop when a repo-local permanent-docs skill is present; `delivery-run` records recommended `permanentDocs` evidence and completeness prompt coverage; `cmd-graduate` stays generic with a pointer to local `*-permanent-docs`; `autoreview` accepts caller-supplied disposition in the packet baseline. Pairs with Heddle `heddle-permanent-docs`.
- Tracked Amp CLI config under `amp/` (`settings.json` + `plugins/subscription-models.ts` ADN/Grok modes), with local install via `amp/install.sh` / `install.sh --tools` and macOS remote streaming to `mbp`/`dever`/`thump`.

### Fixed

- Restored Herdr Option/Alt+`[` / `]` tab switching over mosh by having Kitty inject complete xterm modifyOtherKeys sequences (`CSI 27;3;91/93 ~`). Bare `ESC [` / `ESC ]` never complete as alt-bracket events in Herdr's legacy framer, and Kitty `send_key` does not survive mosh.
- Stopped overlaying live Paseo daemon config from `_paseo/config.json`. Profiles, providers, relay, listen, CORS, and feature flags are host-local; the installer only writes `agents.skills.selection` so repo-owned `paseo*` skills are not reverted, and no longer resets host `omp` profiles or disables mobile relay.
- Fixed remote OMP installs failing on hosts where bun was installed but not on the non-interactive PATH: `scripts/install-omp-remote-hosts.sh` now prepends `~/.bun/bin` (the bun.sh install location) to PATH inside the remote shell.

### Changed
- One required review per gate, chosen by complexity. Every place that requires a reviewer now means exactly one reviewer other than the driver: `autoreview`, `run-plan`, `adversarial-fix-review`, the ADN OMP runtime contract, and the ADN `bug-fix` and `opening-a-pr` playbooks. Fix-necessity is answered by that one reviewer, not a second pass. On OMP the role is `reviewer` for routine work and `reviewer-two` or `reviewer-three` for complex or high-risk work. A different model family is preferred; same-family is a recorded note, not a blocker. No gate compares a role's resolved model to a name in a brief, so reconfiguring `modelRoles` never invalidates a review. The ADN council agent prompts no longer assert that each role runs on a different family.
- Replaced `devin/swe-2:high` with `anthropic/claude-sonnet-5-5:high` in ADN `pstack-models.mdc` (feature/refactoring, arena, architect, and interrogate pools) and the ADN config-state test fixture. No OMP-managed file references `swe-2` now.
- Synced managed OMP `modelRoles` from this host: `designer` moves to `anthropic/claude-sonnet-5-5:high`, `reviewer` to `synthetic/hf:moonshotai/Kimi-K3:high`, and `task` to `anthropic/claude-sonnet-5-5:medium`; the unused `advisor` role is removed. The OMP installer test now expects `advisor.enabled: false`.
- Synced managed OMP `config.yml` from this host: `advisor.enabled` is now `false`, disabling the advisor tier. Also captures `theme.dark: dark`, `spelling.autocomplete: "off"`, and `tui.hyperlinks: auto`.

- `install.sh` with no arguments and `install.sh --all` no longer install Pi. They skip the Pi prompts, agents, extensions, config, npm packages, and review-stack reconciliation. Run `install.sh --pi` to install Pi.
- Captured the live OMP setup as authoritative: `config.yml` (with `eval` `py`/`js` enabled), `AGENTS.md`, and the Herdr (`HERDR_INTEGRATION_VERSION=9`, skips `willContinue` turn ends) and Orca (bounded hook-post retries) status extensions. OMP guidance and ADN `adn-mode` now allow `eval` for computation and scratch work and still forbid it from writing tracked files, which `eval-no-file-writes` enforces.
- ADN and OMP now reference model roles, not models. `setup-adn` no longer writes `modelRoles`, no longer reports role drift, and fails closed when a role named by an ADN agent's `model: "@<role>"` frontmatter is undefined in OMP config. The ADN manifest drops its `roles` block. OMP delivery doctrine (README, run-plan, delivery-run, planner agent) names the `default` role.
- Replaced the ADN agents `architect-grok`, `architect-kimi`, and `reviewer-kimi` with `arch-one`, `arch-two`, `arch-three`, `reviewer-two`, and `reviewer-three`. Each runs on the same-named OMP role, and the live config puts each numbered role on a different model family, so the architect council is three families. `setup-adn apply` deletes the old agent files. The ADN OMP runtime contract maps leaf-skill model lines to these agents and picks panels by distinct configured family; `adversarial-fix-review` picks the reviewer whose family differs from the implementer.
- Synced managed OMP `config.yml` from this host: `default` is `anthropic/claude-opus-5-5:medium`, `task` is `xai-oauth/grok-4.7:high`, `reviewer` is `devin/swe-2:medium`, `reviewer-two` is `openai-codex/gpt-5.6-sol:medium`, `reviewer-three` is `anthropic/claude-opus-5-5:medium`, `arch-one`/`arch-two`/`arch-three` are Claude Opus 5.5, Grok 4.7, and GPT-5.6 Sol at `:auto`. Removed the `completeness`, `architect-grok`, `architect-kimi`, and `reviewer-kimi` roles and the `completeness`/`reviewer` retry fallback chains.
- Verified-build starts the OMP worker through Paseo using the named `omp` profile and leaves model selection to OMP without orchestrator interference.
- Synced managed OMP `config.yml` from this host: `default` is `xai-oauth/grok-4.6:high`. Updated OMP delivery doctrine (README, run-plan, delivery-run, planner agent) and the pinned roster test to the new default.
- Synced managed OMP `config.yml` from this host: `plan` is `openai-codex/gpt-5.6-sol:high`, `advisor` is `devin/swe-2:high` with retry fallback `openai-codex/gpt-5.6-sol`.
- Synced managed OMP `config.yml` from this host: `default` is `devin/swe-2:high`; removed the `default` (`cursor/cursor-grok-4.6`) and `advisor` (`openai-codex/gpt-5.6-sol`) retry fallback chains. Updated OMP delivery doctrine (AGENTS.md, README, run-plan, delivery-run, planner agent) and the pinned routing test to the new default.

- Synced managed OMP `config.yml` from this host: `smol` is `synthetic/hf:zai-org/GLM-5.3-Flash:max`, `vision` is `openai-codex/gpt-5.6-luna:xhigh`, `commit` is `openai-codex/gpt-5.6-luna:xhigh`, `tiny` is `openai-codex/gpt-5.6-luna:low`, `advisor` is `synthetic/hf:moonshotai/Kimi-K3:high` with retry fallback `openai-codex/gpt-5.6-sol`.

- Synced managed OMP `config.yml` from this host: `advisor.enabled` is true, `todo.enabled` is true.

- Synced managed OMP `config.yml` from this host: bash auto-background on with `direnv: auto`, ast-grep on, idle compact off, LSP on.

- Synced managed OMP `config.yml` from this host: `advisor` is `openai-codex/gpt-5.6-sol:medium` with retry fallback `xai-oauth/grok-4.6`.

- Synced managed OMP `config.yml` from this host: `smol` is `openai-codex/gpt-5.6-luna:high`, `designer` is `synthetic/hf:moonshotai/Kimi-K3:high`, `advisor` is `devin/claude-fable-5-1:medium` with retry fallback `openai-codex/gpt-5.6-sol`.

- Synced managed OMP `config.yml` from this host: `smol` is DeepSeek V4 Flash high, `vision` and `advisor` are `synthetic/hf:zai-org/GLM-5.3-Flash` (auto/high), `commit` and `tiny` are `openai-codex/gpt-5.6-luna:auto`, `Oracle` is `openai-codex/gpt-6-astra:medium`, and `task` is `xai-oauth/grok-4.6:medium`.
- Default planning stays local. Do not register a plan in Doct unless the user explicitly asks to send, publish, register, or review it there, or invokes `reviewed-html-plan` / `send-plan-to-doct`.
- Pinned OMP `openai-codex/gpt-6-astra` thinking `defaultLevel` to `low`. Selecting unsuffixed Astra no longer falls through to High under `defaultThinkingLevel: auto`. `_omp/install.sh` now installs managed `models.yml` on every run so remotes pick up the pin.
- Synced managed OMP `config.yml` from this host: dropped `gpt-6-astra` from OMP roles — `slow` is `openai-codex/gpt-5.6-sol:high`, `Oracle` is `openai-codex/gpt-5.6-sol:high`.
- Synced managed OMP `config.yml` from this host: `slow` is `openai-codex/gpt-6-astra:medium`, `Oracle` is `openai-codex/gpt-6-astra:high`. `designer` stays `openai-codex/gpt-5.6-sol:high` (the local `devin/claude-fable-5-1:medium` value was a one-host project override and is not captured). `prewalk.enabled` is false.


- Switched the managed Pi `xai` and `cursor` Grok routes from `grok-4.5` to `grok-4.6` now that Pi ships `xai/grok-4.6` natively: the Pi completeness reviewer runs on `xai/grok-4.6:high`, and install keeps unsuffixed `cursor/grok-4.6` plain (`fastDefaults.grok-4.6=false`) with the legacy `grok-4.5` routes migrated to `grok-4.6`. The managed `xai/grok-4.6` entry still advertises a 200k context window, and the `opencode/grok-4.5` context-ceiling policy is unchanged.

- OMP `adn-mode` and `run-plan` pin generic implementation `task` workers to `model: "@default"` so they do not inherit a temporary Fireworks or DeepInfra parent. Named roles keep frontmatter. Cancel and respawn if a child tool-loops.

- Synced managed OMP `config.yml` from this host: `slow` is `openai-codex/gpt-5.6-sol:high`, `architect-grok` is `cursor/cursor-grok-4.6:high`. Retry fallbacks match live (Synthetic Kimi for the Kimi roles, `xai-oauth/grok-4.6` for architect-grok and reviewer, Cursor Grok for completeness and default). `extendedContext` is false.

- Synced managed OMP `config.yml` from this host: `slow` is `synthetic/hf:moonshotai/Kimi-K3:max`, `plan` is `synthetic/hf:moonshotai/Kimi-K3:high`, `advisor` is `xai-oauth/grok-4.6:high`, `reviewer` is `cursor/cursor-grok-4.6:high`. Retry fallbacks: Oracle drops `cursor/kimi-k3-max`; reviewer falls back to `xai-oauth/grok-4.6` then Synthetic Kimi; slow falls back to Fireworks Kimi; advisor falls back to `cursor/cursor-grok-4.6`; plan falls back to Sol.

- Removed Pi's always-on `APPEND_SYSTEM.md`. Conditional procedures stay in skills. `cmd-create-pr` now loads for any `gh pr` create, update, comment, or similar mutating PR action, including forks. Install removes leftover `~/.pi/agent/APPEND_SYSTEM.md`.

- Synced managed OMP `config.yml` from this host: `statusLine.preset` is `default`, `statusLine.sessionAccent` is false.

- Synced managed OMP `config.yml` from this host: `advisor` is `openai-codex/gpt-5.6-sol:high`, with retry fallback `xai-oauth/grok-4.6`.

- Synced managed OMP `config.yml` from this host: `Oracle` is `openai-codex/gpt-5.6-sol:xhigh`. Retry fallbacks now cover Oracle, advisor, architect-kimi, reviewer-kimi, architect-grok, completeness, reviewer, default, smol, and slow.

- Renamed remote host `mbp14` to `thump` in WezTerm/Kitty paste helpers, Amp/OMP remote defaults, clipssh aliases, and docs.

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

- Retired the shared `lab-manager` skill: it now lives in the ccore2 repo at `.agents/skills/lab-manager`, versioned with the Lab Manager contract it documents. Installers delete the managed `~/.agents/skills/lab-manager` copy and its consumer links with a backup. `verified-build` and `session-cleanup` point to the repo-local skill.
- Removed the plan-completeness review: the shared and Codex `completeness` skills, the OMP and Devin `completeness` agents, the delivery `COMPLETENESS_REVIEW` stage and `completion-review` command, and the routing text that sent work there. Installers delete the retired skill and agent copies.
- Removed leftover Gemini CLI surfaces: root `GEMINI.md`, `_claude/commands/review:change-gemini.md`, and `scripts/gemini-review.sh`.
- Retired the Pi model-picker allowlist: install no longer ships `model-allowlist.ts` and clears `enabledModels` so Pi shows the live catalog. The default execution route remains DeepSeek Flash.
- Retired the ai-configs code built around Pi workflows now that Pi sessions run adn-mode: the repo-owned `pi-extensible-workflows` settings/roles (`_pi/pi-extensible-workflows/`), the Heddle release workflow and prompts (`_pi/workflows/`, `_pi/prompts/heddle:*`), and the evidence-closed investigation prompt (`_pi/prompts/investigate.md`). The `pi-extensible-workflows` npm package stays installed with plugin defaults. `install.sh --pi` removes stale live copies from `~/.pi/agent` with a timestamped backup under `~/.pi/agent/extension-backups/`.

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
