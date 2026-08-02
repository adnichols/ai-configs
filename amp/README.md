# Amp configuration

Canonical Amp CLI config tracked by ai-configs.

## Managed surfaces

| Path | Purpose |
| --- | --- |
| `settings.json` | Host settings (`amp.remoteThreadCreation.enabled`) |
| `plugins/subscription-models.ts` | Custom plugin modes: ADN Low/Med/High/Ultra + Grok 4.5 |

Not managed (left alone on install):

- `~/.config/amp/plugins/orca-agent-status.ts` (Orca-owned)
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

## Provider subscriptions on a new host

Modes use `openai/*` and `xai/*` models. After installing files, link subscriptions once per host:

```bash
amp config model-providers add-chatgpt-subscription
amp config model-providers list
amp config model-providers activate <id>
```

SuperGrok / xAI is linked the same way through Amp's model-provider UI/commands when available.
