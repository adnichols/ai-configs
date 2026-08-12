# Amp configuration

Canonical Amp CLI config tracked by ai-configs.

## Managed surfaces

| Path | Purpose |
| --- | --- |
| `settings.json` | Host settings (`amp.remoteThreadCreation.enabled`) |
| `plugins/subscription-models.ts` | ADN Low/High main modes + `adn_oracle` (Sol) and `adn_alt` (Grok) second-opinion tools/modes |

Not managed (left alone on install):

- `~/.local/share/amp/**` (runtime state, secrets, threads)
- Amp model-provider subscriptions (ChatGPT / SuperGrok OAuth links)

## Install

Local only:

```bash
bash amp/install.sh
```

Via the main installer (also streams to remote hosts on macOS):

```bash
bash ./install.sh --tools
```

Override remote targets:

```bash
AMP_REMOTE_HOSTS="dever mbp14" bash ./install.sh --tools
# or
AMP_REMOTE_HOSTS="dever mbp14" bash scripts/install-amp-remote-hosts.sh
```

## ADN modes and second opinions

Amp does **not** let plugins overwrite built-in mode keys (`low`, `medium`, `high`, `ultra`). The managed plugin adds parallel ADN modes instead.

| Surface | Kind | Model | Reasoning |
| --- | --- | --- | --- |
| `ADN Low` | main mode | `openai/gpt-5.6-luna` | `max` |
| `ADN High` | main mode | `openai/gpt-5.6-terra` | `high` |
| `adn_oracle` | tool (second opinion) | `openai/gpt-5.6-sol` | `high` |
| `adn_alt` | tool (second opinion) | `xai/grok-4.6` | `high` |
| `ADN Oracle` | optional direct mode | `openai/gpt-5.6-sol` | `high` |
| `ADN Alt` | optional direct mode | `xai/grok-4.6` | `high` |

Intended use:

1. Start implementation threads in **ADN Low** or **ADN High**.
2. Escalate hard analysis/review with “use the oracle” / `adn_oracle` (Sol).
3. Get an alternate frontier take with “ask Grok” / `adn_alt`.
4. Use **ADN Oracle** or **ADN Alt** as main modes only when you want to drive those models directly.

After install, reload plugins in Amp (`plugins: reload` from the command palette) or restart Amp so the modes and tools appear.

## Provider subscriptions on a new host

Modes use `openai/*` and `xai/*` models. After installing files, link subscriptions once per host:

```bash
amp config model-providers add-chatgpt-subscription
amp config model-providers list
amp config model-providers activate <id>
```

SuperGrok / xAI is linked the same way through Amp's model-provider UI/commands when available.
