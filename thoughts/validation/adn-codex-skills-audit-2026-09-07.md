# ADN and Codex skills audit

Audit date: 2026-09-07. Repository revision: `a28f9a222ecc58298b490c93d82b6e7b38abc25a`.

Recommendation: retain ADN's engineering principles and task routing, extract runtime-specific instructions, and provide an explicit `adn-codex` entrypoint. Port its routed dependencies together. A new wrapper with renamed models would leave broken tool calls and conflicting lifecycle rules underneath it.

This is an audit and adaptation proposal. No runtime configuration or installed skills were changed. The audit inventories the shared matrix and ADN package, examines the central routing, installation, review, setup, and delegation contracts, and samples supporting skills. It is not a line-by-line certification of every optional skill or a live run of every workflow.

## Inventory and installation

- `skills/install-matrix.json` declares 83 skills. 81 allow Codex, including 58 in the default profile and 23 in optional profiles.
- `_adn/skills` contains another 48 skill entrypoints and 23 playbooks. None of those 48 entrypoints appears in the shared matrix.
- This machine has 129 immediate skill entrypoints under `~/.agents/skills`, plus five under `~/.codex/skills`. These counts exclude bundled plugin and system catalogs and do not represent unique names across all discovery locations.
- All 48 ADN entrypoints are installed under `~/.agents/skills`. Their entrypoint contents match the checkout except `adn-mode`. The installed version adds `principle-modes-not-exceptions` references absent from the audited checkout entrypoint. This is observed drift, not proof of unauthorized adoption.
- `_omp/install.sh:68` copies ADN into `~/.agents/adn`; `_adn/scripts/setup-adn.ts:14` links the default installation into `~/.agents/skills`. Codex therefore receives ADN through OMP's shared installation, without a Codex-specific compatibility decision.
- `install.sh:2049` documents Pi's separate overlay. It copies the shared ADN payload and overlays `_pi/skills/adn-mode/SKILL.md`. The routed playbooks and other skills remain shared.

Codex officially discovers user skills under `~/.agents/skills` and follows symlinked folders. Same-name skills are not merged. An install matrix's consumer label alone cannot hide files placed in a globally scanned directory. [Official skill documentation](https://learn.chatgpt.com/docs/build-skills).

## Findings

| Priority | Evidence | Consequence |
| --- | --- | --- |
| High | `_adn/skills/adn-mode/SKILL.md:88` defines OMP and Cursor dispatch, with no Codex branch. | Codex discovers a mode whose concrete execution instructions target other clients. |
| High | `how` calls Cursor `Task` even on its simple path; `swarm` asks for cloud workers; `arena` and `interrogate` read `~/.cursor/rules/pstack-models.mdc`. | Adapting only the mode entrypoint leaves direct and transitive invocations incompatible. |
| High | `_pi/skills/adn-mode/SKILL.md:101` adds general-purpose council agents and implementation workers. `AGENTS.md` specifies the exact five-agent Pi roster and driving-session implementation. | The Pi overlay contradicts repository authority. It is not a safe template to copy into Codex. |
| High | `_adn/skills/setup-adn/SKILL.md` writes Cursor model rules, while `_adn/scripts/setup-adn.ts` configures OMP roles. | The same setup name describes different configuration owners and offers no Codex model setup. |
| High | `skills/run-plan/SKILL.md:14` explicitly forbids loading or emulating ADN outside OMP. | A Codex adaptation requires an intentional integration change, including the test that currently enforces this restriction. |
| High | `skills/autoreview/SKILL.md:130` requires the active client's configured reviewer but lists Pi, Claude, OpenCode, and Devin only. `_codex` contains no maintained agent profiles. | The required Codex reviewer contract is incomplete. Native delegation exists, but the repository does not define how this route selects and invokes its reviewer. |
| High | `skills/adversarial-fix-review/SKILL.md` requires a different model family, without a Codex route. | Fresh GPT review cannot honestly be labeled the Grok/Kimi/Claude diversity promised by ADN. This needs an explicit policy adaptation. |
| Medium | `_adn/skills/audit-adn/SKILL.md` promises checksums, roles, and markers. Its command reaches `_adn/scripts/audit-adn.ts:115`, which projects session invocation counts and normally writes an audit report. | A successful command is not an installation-integrity verdict. Split integrity auditing from usage reporting. |
| Medium | `skills/delivery-run` permits Codex in the matrix, but its CLI accepts only OMP and Pi runtimes. `_codex/prompts/review:plan.md` invokes `pi -p --approve`. | Some Codex workflows are external-runtime bridges. Document them as such; do not silently treat them as native Codex execution. |
| Medium | `_codex/prompts/consult:oracle.md` loads `oracle-consultation`, whose matrix entry permits Pi and Devin and whose launch instructions are Pi-specific. | The prompt and supported-consumer declaration disagree. Global discovery may expose the skill anyway, without making it compatible. |
| Medium | `no-comments` spawns `Comment Sicko`; `automate-me`, `reflect`, and `show-me-your-work` assume Cursor authoring or transcript facilities. The mode also requires OMP `deslop` and control skills. | Non-model dependencies need explicit replacement or an unsupported outcome. |
| Medium | The mode authorizes team-chat and ticket actions broadly and requests a separate PR for a broken skill. | These rules must defer to actual user authorization and repository boundaries. Mode activation cannot authorize messaging or unrelated PRs. |

Some issues are existing portability defects rather than Codex-only defects. Keep their repairs separately attributable so the Codex port does not silently alter Pi or OMP policy.

## Proposed structure

Use one common source for task classification, evidence requirements, design principles, and review rubrics. Put model selection, tool calls, transcript access, and lifecycle integration in explicit runtime adapters. Each directly callable operational skill must reach its adapter itself. Loading the adapter only from `adn-codex` is insufficient when users invoke `how` or `interrogate` directly.

Suggested repository ownership:

| Proposed location | Owns |
| --- | --- |
| `_adn` | Pinned provenance, common principles, playbooks, rubrics, and cross-runtime contract tests. |
| `_codex/skills/adn-codex` | Explicit Codex mode entrypoint, native tool mapping, supported routes, and invocation metadata. |
| `_codex/agents` | Codex role definitions for clients that support loading custom agent files. |
| `skills/install-matrix.json` or a linked inventory | ADN ownership, runtime support, dependencies, and installation profiles. |
| Existing `run-plan`, `autoreview`, and PR skills | Lifecycle, review budget, and authorized publication. ADN should compose with their policies. |

Start with a distinct `adn-codex` name so installation does not overwrite OMP's `adn-mode`. This alone does not remove the old mode from Codex discovery. Either make the shared entrypoint a runtime-aware dispatcher or explicitly disable the incompatible entrypoint for Codex. A disable entry changes user config, so it belongs to a reviewed setup operation, not the current installer that promises to preserve `config.toml`.

Use `agents/openai.yaml` to make the opinionated mode explicitly invoked with `policy.allow_implicit_invocation: false`. Keep principle skills available on demand. Avoid adding the complete mode to global `AGENTS.md`. Official guidance describes progressive loading, invocation policy, local disabling, and duplicate-name behavior. [Official skill documentation](https://learn.chatgpt.com/docs/build-skills).

## Codex execution and model policy

The driving agent implements, runs tests, and manages Git. Authorize bounded read-only delegation for independent discovery, design alternatives, and review. A narrow explanation stays local. Do not inherit the current `how` requirement to spawn a separate explainer for every small question.

Use the native tools actually exposed by the client. In this desktop session those are `collaboration.spawn_agent`, `send_message`, `followup_task`, and `wait_agent`. The session has four total active-agent slots. It has no Cursor `Task`, cloud-worker flag, or role-selector parameter. Full-history forks cannot take model overrides here; selected-model packets need explicit context with a supported fork setting. Treat these as session capabilities, not permanent Codex API guarantees.

For local clients supporting named custom agents, current documentation places personal TOML definitions under `~/.codex/agents`. It supports model and effort settings. Documented defaults do not override the actual tool schema or live permission policy. [Official subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents).

Initial model choices below are recommendations to evaluate, based on the models exposed in this session and the repository's existing role split. They are not benchmark conclusions or universal account entitlements.

| Role | Proposed default | Authority |
| --- | --- | --- |
| Driving implementation | Keep the user's selected parent model and effort. | Implementation, tests, Git, synthesis. |
| Scout | GPT-5.6 Terra, low. | Bounded read-only evidence gathering. |
| Planner or design reviewer | GPT-5.6 Sol, medium. | Design alternatives or readiness findings. |
| Implementation reviewer | GPT-5.6 Terra, medium. | Material in-scope findings. |
| Oracle | GPT-5.6 Sol, high; consider Astra for a separately configured demanding role. | One unresolved decision, advisory only. |
| Imaging | Use parent vision when available. | No routine extra model call. |

Keep model IDs and effort in one runtime-owned configuration source. Validate requested values against exposed capabilities. Do not write Cursor slugs into Codex files or pretend a skill can change the running parent model.

Separate `independent review` from `cross-family review`. Fresh context and distinct review questions can provide an independent check within GPT models. They do not reproduce cross-provider diversity. For ordinary Codex work, recommend the former with explicit disclosure. If the user specifically requires cross-family review, use an explicitly selected external route or report that requirement unavailable. Never silently count a same-model pass as satisfying it.

Read-only role instructions are an authority boundary, not proof of OS-enforced isolation. The current collaboration tool has no per-call sandbox setting. Verify the client configuration if enforcement matters.

## Adaptation scope

| Group | Treatment |
| --- | --- |
| 21 principle skills, `bro`, `unslop`, technical writing, TypeScript guidance | Reuse the substantive guidance; inspect incidental runtime references and avoid mandatory principle-name recitations in every reply. |
| `how`, `why`, `architect`, `arena`, `swarm`, `interrogate`, `reflect`, `no-comments`, `blast-radius`, `figure-it-out` | Adapt delegation and model selection, cap fan-out, preserve bounded outputs, keep implementation in the driver. |
| `recall`, `automate-me`, `show-me-your-work` | Replace Cursor transcript paths with authorized Codex task/history access or supplied artifacts. Do not scan unrelated conversations. |
| Verification creation and maintenance | Retain real-product proof and feature mapping; bind browser, native UI, and CLI control to tools actually installed. |
| `setup-adn`, `audit-adn`, `adopt-skill` | Add explicit runtime ownership, true integrity checks, and preserve pin/adoption policy. |
| `poteto-mode`, `setup-pstack` | Keep explicit compatibility aliases outside the default Codex route. |
| `run-plan`, `autoreview`, necessity review, Oracle, Doct and PR integration | Define the Codex contracts before claiming an end-to-end supported workflow. |
| Shipping, autopilot, cloud programs, delivery ledger | Mark unsupported or external until deliberately adapted. Do not invent `runtime=codex` support. |

For the first complete release, support investigation, feature, bug fix, refactoring, and skill authoring. Preserve all required dependencies for these routes. Keep TDD explicitly requested, honor repository-specific branch rules, and let the user's task determine whether PR creation is included. Do not create a Codex goal from an ordinary task unless goal creation is explicitly authorized.

## Public pstack comparison

The repository pins Lauren Tan's MIT-licensed pstack at `46756f89270d7e7dcb8c28c90fd0f957ade4ce2c`. Its useful core is the router, small principle files, task-specific playbooks, and evidence-based verification. Preserve the pin and attribution; research is not authorization to adopt newer upstream code. [Pinned upstream README](https://github.com/cursor/plugins/blob/46756f89270d7e7dcb8c28c90fd0f957ade4ce2c/pstack/README.md).

The public `michael-denyer/pstack-claude` port uses a shared skill tree with an explicit Codex mapping referenced from affected entrypoints. That is a useful precedent for direct-invocation coverage. [Port README](https://github.com/michael-denyer/pstack-claude/blob/main/README.md).

Do not copy its mapping verbatim. It says Codex has no structured-choice tool and assumes a `multi_agent` feature flag and `close_agent`. Those assumptions do not match this session's exposed capabilities, and current official documentation describes delegation as enabled by default. Reuse the separation pattern, then verify the concrete mapping locally. [Community mapping](https://github.com/michael-denyer/pstack-claude/blob/main/plugins/pstack/skills/poteto-mode/references/codex-tools.md), [official subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents).

## Verification and promotion

Existing checks run during this audit:

- `cd _adn && bun test`: 35 passed, zero failed, 1,889 assertions.
- `cd _adn && bun tests/routing-eval.ts`: passed, 23 playbooks, 28 fixtures, six formal thresholds, no missing playbook fixtures.

These results do not certify Codex. For example, `tests/manifest.test.ts` reads `~/.agents/adn` and hardcodes `/Users/anichols/code/ai-configs`; `adn-contract.test.ts` checks OMP-specific strings and the current prohibition on non-OMP ADN activation. The routing eval tests a deterministic router, not a model executing the playbooks.

Promotion should require an isolated Codex-only install with OMP and Cursor absent, dependency resolution for direct and routed invocations, source-versus-installed integrity checks, and tests for foreign tool leakage. Preserve unrelated user configuration and prove repeated installs are stable.

Run live prompt evaluations for a narrow investigation, feature, reproduced bug, no-behavior refactor, and skill edit. Include missing-model and missing-subagent cases, insufficient cross-family coverage, main-only Git policy, no unsolicited messaging, no automatic delivery arming, and an independently invoked supporting skill. Compare current Codex behavior with the proposed adaptation on completion, material defects, unauthorized actions, tool failures, elapsed time, and token use. Reject a port that merely adds ceremony without improving outcomes.
