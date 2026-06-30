# Auxiliary goal judge routing

Session-derived note (2026-05-02): Aaron corrected the Hermes goal judge route to use OpenAI Codex mini.

## Confirmed behavior

- Goal continuation calls `get_text_auxiliary_client("goal_judge")` from `hermes_cli/goals.py`.
- `auxiliary.goal_judge` may be added to `~/.hermes/config.yaml` even though it is not present in the default config scaffold.
- Auxiliary task routing uses normal `provider` and `model` keys.

## Aaron's current preferred config

```yaml
auxiliary:
  goal_judge:
    provider: openai-codex
    model: gpt-5.4-mini
```

## Commands

```bash
hermes config set auxiliary.goal_judge.provider openai-codex
hermes config set auxiliary.goal_judge.model gpt-5.4-mini
hermes config check
```

Restart the gateway or start a new Hermes session for running agents to pick up the config change.
