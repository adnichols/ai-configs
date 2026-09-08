# Codex runtime contract

This contract applies to the parallel skills installed under `$CODEX_HOME/skills`, normally `~/.codex/skills`. Read it once per task. These copies retain their public names. Resolve another skill to the Codex copy when present, otherwise to the active skill catalog. Never load a disabled shared copy to recover an older runtime procedure.

## Authority and execution

The driving agent owns implementation, tests, fixes, Git operations, synthesis, and external actions. Delegate bounded read-only discovery, design alternatives, and independent review when a skill requests them and useful independent work remains for the driver. A skill name is not a native agent type. Do not delegate implementation just because a source playbook says to use a worker.

Follow the user's task and repository instructions for scope and branch choice. Mode activation does not authorize a PR, a merge, messaging another person, deployment, a new worktree, or editing another repository. Existing task authorization remains effective. Keep unrelated changes intact. Never reset a checkout or delete dirty work to simplify a workflow.

Use a local task list or the client's planning tool for multi-step work. Use Codex goal tools only when the user explicitly requested a goal. Use automation tools only for authorized automation requests. Neither long duration nor a request to implement implies either action.

## Tools

- Read and search with native filesystem tools or `exec_command` running `rg` and targeted reads. Edit with native patch/edit tools. The prohibition on OMP's eval tool does not prohibit Codex's `functions.exec` tool orchestration.
- Use the currently exposed native collaboration tools. Desktop may expose `collaboration.spawn_agent`, messaging, and `wait_agent`; other clients may use different schemas. Inspect the actual schema. Do not call Cursor `Task`, Pi `Agent`, OMP `task`, or invent `subagent_type`, `environment`, `readonly`, `cloud_base_branch`, or `run_in_background` arguments.
- Respect active capacity. Queue work when slots are occupied. These agents share the checkout unless the actual tool contract says otherwise. Give a read-only authority boundary in every packet; that instruction is not a sandbox guarantee.
- Include allowed files, the question or review lens, expected output, authority, existing verification evidence, and the stopping condition. Use file paths instead of pasted files. Collect and inspect every required result. Missing coverage is not a pass.
- When the tool accepts named configured agents, use them. Otherwise pass the role's instructions in a bounded packet. A fresh reviewer gets raw requirements and artifacts, not the implementer's conclusion as evidence.
- If the native tool requires an explicit context packet to select a model, provide one. In clients where full-history forks cannot accept model overrides, do not combine those options. Preserve inherited context for decisions that require it and keep the parent model when necessary.
- Prefer a relevant installed browser, computer-use, CLI, or verification skill to prove behavior. OMP control plugins and Cursor built-ins are not prerequisites. Read the selected tool's real instructions before driving it.
- Use asynchronous questions when available for missing preferences while independent work continues. Ask a direct concise question when required information is blocking. Do not invent a question tool or treat silence as permission.

## Models

Keep the user's selected driving model. This skill cannot change a running parent session. Read `codex-models.json` beside this contract for role defaults. Optional user overrides live at `$CODEX_HOME/adn-models.json`; validate them against the native spawn tool's available models and supported effort levels before using them. Do not pass provider-prefixed OMP or Cursor slugs.

If a suggested model is unavailable, inherit the parent for ordinary independent discovery/review and disclose the substitution. If the task explicitly requires a named model or a different family, report that requirement unavailable instead of silently substituting. A configured role never grants extra authority.

Independent review means a fresh evaluation of the artifacts. Different GPT variants do not establish cross-provider diversity. Ordinary Codex review uses independent agents. A request explicitly requiring cross-family review needs an authorized external route; do not launch another client or provider implicitly.

## Lifecycle and history

`run-plan` owns an explicitly requested implementation-through-PR lifecycle. `autoreview` owns the bounded material-review budget. `adn-mode` owns task routing and evidence discipline. Do not multiply review gates for the same unchanged candidate. Review static artifacts independently; the driver runs commands and supplies their outputs unless the user expressly authorized reviewer execution.

Use Codex task/history tools when available and only for the user's named project and time window. Otherwise use supplied handoffs, current task context, and Git evidence. Never invent Cursor transcript directories, scrape unrelated projects, or claim unavailable history was checked.

The existing delivery CLI is an OMP/Pi product. Codex can inspect an existing ledger without changing its owner. Do not arm it as Codex, fake runtime evidence, or launch Pi to satisfy a native task. Use the Codex `delivery-run` copy for native lifecycle routing.

Within retained operational guides, explicit commands targeting an external product remain valid only when that product is the user's task, such as administering Herdr or Pi. References to another client's agent dispatch, model defaults, transcript paths, or lifecycle never override this contract.
