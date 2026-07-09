# Pi/Codex unexpected model usage tracing

Use this reference when Aaron sees unexplained Codex/OpenAI dashboard usage and asks where it came from.

## Durable findings from the Spark investigation

Unexpected `gpt-5.3-codex-spark` usage can come from Pi subagents even when Codex Desktop and the main Pi session appear configured for `gpt-5.6-sol`.

High-signal locations:

- Pi config on each host: `~/.pi/agent/settings.json`
  - Check `defaultProvider`, `defaultModel`, `defaultThinkingLevel`, and `enabledModels`.
- Codex CLI/Desktop config on each host: `~/.codex/config.toml`
  - Check `model`, `model_provider`, profiles, and migration notices.
- Main Pi sessions: `~/.pi/agent/sessions/**/*.jsonl`
- Codex Desktop/CLI sessions: `~/.codex/sessions/**/*.jsonl`
- Pi sidechain/subagent outputs: `/tmp/pi-subagents-*/.../tasks/*.output`
- Worktree side-agent runtime files: `<worktree>/.pi/side-agents/runtime/**`

## Distinguish actual usage from noise

Actual usage evidence:

- Pi JSONL assistant message with `message.model == "gpt-5.3-codex-spark"` and provider/usage fields.
- Pi sidechain `.output` records with `message.model == "gpt-5.3-codex-spark"` and nonzero `usage`/`cost`.

Weak/non-usage evidence:

- `model_change` events: selection intent, not necessarily a completed billable call.
- `session_meta.dynamic_tools` in Codex sessions: available model list shown in tool schemas.
- `models_cache.json` or provider model caches: availability only.
- Tool output that quotes another file/session: may duplicate evidence; follow the referenced file.

## Remote host checklist

When Aaron says "MBP and dever", inspect both hosts and compare:

1. Host/time/home: `hostname`, `date`, `$HOME`.
2. `command -v codex pi tmux`; `codex --version`; `pi --version`.
3. Pi and Codex config files above.
4. Active relevant processes (`ps -axo pid,ppid,etime,command`) for `pi`, `codex`, `herdr`, `aoe`, side-agent launchers.
5. Tmux panes and current paths when Pi/herdr is active.
6. Parse session JSON rather than relying on raw grep counts.
7. Inspect `/tmp/pi-subagents-*` if main sessions only contain tool results or summaries.

## Provider alias pitfall

If an agent definition names `model: openai-codex/gpt-5.6-sol` but `pi --list-models` shows only numbered providers such as `openai-codex-2`, `openai-codex-3`, and `openai-codex-4`, verify how Pi resolves that alias. A failed/ambiguous agent model can lead to fallback to the host Pi default, so an unexpected default like `openai-codex-4/gpt-5.3-codex-spark` can drive subagent usage.

## Example attribution language

> The usage is not from Codex Desktop's main config. It is from Pi sidechain/subagent runs on `<host>`, especially `<agent-name>` tasks under `/tmp/pi-subagents-*`. The evidence is actual assistant records with `provider=<provider>`, `model=<model>`, and nonzero usage/cost. Config/model-cache hits alone were not counted.
