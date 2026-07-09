# Auxiliary compression routing with OpenAI Codex / ChatGPT accounts

Session-derived pitfall: Hermes can fail context compression with a 400 like:

```text
Compression summary failed: Error code: 400 - {'detail': "The 'google/gemini-3-flash-preview' model is not supported when using Codex with a ChatGPT account."}. Inserted a fallback context marker.
```

Cause:
- Main model/provider is OpenAI Codex via ChatGPT account, e.g.:
  ```yaml
  model:
    provider: openai-codex
    default: gpt-5.6-sol
    base_url: https://chatgpt.com/backend-api/codex
  ```
- Auxiliary compression has `provider: auto` with a non-Codex model, e.g.:
  ```yaml
  auxiliary:
    compression:
      provider: auto
      model: google/gemini-3-flash-preview
  ```
- `auto` resolves to the active provider (`openai-codex`), then the Codex/ChatGPT backend rejects the Gemini model ID.

Preferred fix when staying on Codex auth:

```bash
hermes config set auxiliary.compression.provider openai-codex
hermes config set auxiliary.compression.model gpt-5.4-mini
hermes config check
```

Alternative fix when intentionally using Gemini:

```bash
hermes config set auxiliary.compression.provider openrouter
hermes config set auxiliary.compression.model google/gemini-3-flash-preview
hermes config check
```

Operational notes:
- A fallback context marker means Hermes did not lose the session, but real compression did not occur, so long threads may degrade faster until fixed.
- Running gateway sessions usually need a gateway restart or fresh session before config changes are picked up.
- Before restarting a gateway, consider whether any active agent turns are running. Idle sessions are safe; active turns drain for `agent.restart_drain_timeout` seconds then may be interrupted and marked resumable.
