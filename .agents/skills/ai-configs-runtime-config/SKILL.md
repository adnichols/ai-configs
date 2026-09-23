---
name: ai-configs-runtime-config
description: Maintain agent definitions, model routing, and runtime-specific prompts in ai-configs.
---

# Agent Catalog

Current Pi subagent roster and Claude/Codex execution boundaries defined in this repository.

## Pi Subagents (Exact Five-Agent Roster)
Located under `_pi/agents/` and invoked through Pi's subagent system:

- `oracle` (GPT-6 Sol, high; `_pi/agents/oracle.md`) — inherited-context, read-only decision support for risky, ambiguous, drifting, or non-converging choices; it advises while the driving agent keeps decision and implementation authority.
- `planner` (GPT-6 Sol, medium; `_pi/agents/planner.md`) — planning and independent plan-readiness-review authority; it may write only a caller-named plan artifact and otherwise returns review findings without edits.
- `reviewer` (GPT-5.6 Terra, medium; `_pi/agents/reviewer.md`) — read-only materiality-focused review authority, except for an explicitly named review artifact when the caller authorizes comments or output there.
- `scout` (GPT-5.6 Terra, low; `_pi/agents/scout.md`) — bounded read-only local/web discovery and evidence gathering.
- `imaging` (GPT-5.6 Luna, xhigh; `_pi/agents/imaging.md`) — read-only visual analysis for non-vision models; it inspects image paths or URLs and returns what the caller cannot see.

`_pi/agents/Explore.md` is not an active persona. It is the required `enabled: false` override for the bundled Explore persona. Pi has no repository-owned implementation subagent: the driving agent performs code changes, test changes, fixes, and repository management directly.

Planner, reviewer, and scout caller packets must name the artifact or allowed surfaces, task-specific lens, output destination/format, authority boundary, verification evidence, and stop/verdict contract. Oracle packets instead name one bounded decision, inherited constraints, relevant evidence, credible options, the driving agent's current recommendation and uncertainty, and one narrow question ending with `?`; they still state the advisory authority boundary and stopping condition. Imaging packets name the exact image path(s) or URL(s), the question to answer, and any task context needed to know what to look for. Permanent agent prompts define capability and authority; callers own workflow-specific meaning.

Oracle launch contract (Pi): call `Agent` with only `subagent_type: "oracle"`, a short description, and the decision prompt. Omit caller-side `model`, `thinking`, `reasoningEffort`, `inherit_context`, and `isolation`. Frontmatter pins Sol high, inherited/forked context, and `isolation: none`. Setting `inherit_context: false` or `isolation: "worktree"` is a workflow violation. After return, record disposition (`accepted` / `partially-accepted` / `rejected` / `escalated`) with why before acting. Invoke Oracle proactively on trigger-class ambiguity; do not wait for the operator to request it.

Imaging launch contract (Pi): call `Agent` with only `subagent_type: "imaging"`, a short description, and a self-contained prompt that includes the image path or URL. Omit caller-side `model`, `thinking`, `reasoningEffort`, and `isolation`. Frontmatter pins Luna xhigh and `isolation: none`. Invoke imaging proactively when the current model cannot see visual input; do not guess about screenshots, diagrams, or other images.

`/cmd:start-linear-issue` is a direct deterministic driving-agent workflow. It validates Linear/Git state and creates the exact issue branch and sibling worktree without delegating repository management to a Pi subagent.

### Pi Subagent Reasoning-Effort Policy

- Agent frontmatter is authoritative: Oracle decision support uses GPT-6 Sol high with inherited context and live-checkout `isolation: none`; planning and independent plan-readiness review use GPT-6 Sol medium; implementation/code review uses GPT-5.6 Terra medium; scout uses GPT-5.6 Terra low; imaging uses GPT-5.6 Luna xhigh with live-checkout `isolation: none`. Do not pass caller-side model, thinking, `inherit_context`, or `isolation` overrides on Oracle, planner, reviewer, or imaging launches.
- In Pi delivery runs, the Sol-medium readiness reviewer recommends the dedicated implementation runtime. Use `openai-codex/gpt-5.6-luna` at xhigh by default. Use `openai-codex/gpt-5.6-terra` at high when correctness depends materially on critical technical judgment. Escalate unresolved consequential choices to Oracle rather than routing implementation through Sol. This is a default, not a prohibition: a deliberate manual model/reasoning choice is allowed when the delivery ledger records the override and reason.
- Do not pass caller-side reasoning overrides merely because a task appears difficult.
- Development stays in the driving session. Do not route code-writing, tests, fixes, or repository operations through any Pi persona; use subagents only for bounded planning, read-only discovery, read-only decision support, read-only review, or read-only visual analysis.
- GPT-5.4 and GPT-5.4-mini are retired from Pi-owned agents, the managed `openai-codex` model catalog, and Pi settings aliases. This is an exact Pi-only retirement and does not rewrite caller-owned providers or models.

## Claude and Codex Execution Model

- Claude's driving session performs discovery, planning, implementation, testing, documentation, review, and repository management directly with native tools. The repository no longer ships a Claude subagent.
- Devin's driving session likewise implements directly with native tools. Its repository-owned custom subagent profiles live in `_devin/agents/` and install to `~/.config/devin/agents/`: `reviewer` and `planner` (sonnet), `oracle` and `completeness` (opus). Invoke them by profile name via `run_subagent` only for bounded planning, decision support, or read-only review. The shared delivery ledger supports only the `omp`/`pi` runtimes; Devin sessions use `run-plan` with the standalone `completeness` packet instead of arming delivery.
- Required code reviews run through the active harness's configured `reviewer` subagent. Completeness is an on-request plan walk, not a merge-readiness gate. Do not make Codex or Claude Code a required review transport.
- On Cursor Grok or Composer parents, launch required reviewers with `run_in_background: true` and join via `get_subagent_result` (`wait: true`). The vendored `pi-cursor-sdk` bridge also forces background for `Agent` on those models.
- Codex driving agents likewise implement authorized changes directly with their native repository tools.


## Runtime-specific configuration

Read `_pi/README.md` for Pi installation and legacy delivery operations, `_omp/AGENTS.md` for OMP, `_devin/AGENTS.md` for Devin, `_codex/README.md` for Codex, and `_paseo/README.md` for the managed Paseo daemon config and skills. These files describe their respective runtimes; they do not authorize switching the active runtime.
