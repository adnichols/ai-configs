# 2026-07 Hermes compaction model-routing note

Use this when diagnosing Hermes context compaction that appears to hang, repeatedly times out, creates confusing continuation sessions, or delays Discord/Telegram responses.

## Observed failure pattern

- Main route: `openai-codex / gpt-5.5`.
- Problematic auxiliary route: `auxiliary.compression` configured as `custom / gpt-5.5` against a local OpenAI-compatible Codex/OpenCode app proxy such as `http://localhost:8317/v1`.
- Logs show compaction around `~170K–218K` prompt tokens.
- The custom `gpt-5.5` compression call times out, retries once, then falls back to the main `openai-codex / gpt-5.5` route, which can also be slow or hit the auxiliary timeout.
- Result: one user-visible turn can spend many minutes in compaction/retry/fallback before continuing.

Representative log markers:

```text
Preflight compression: ~... tokens >= ... threshold
context compression started: session=... tokens=~... model=gpt-5.5
Auxiliary compression: using custom (gpt-5.5) at http://localhost:8317/v1/
Auxiliary compression: transient transport error; retrying once ... Request timed out
Auxiliary compression: connection error on custom ... falling back to main agent model main-agent(openai-codex) (gpt-5.5)
Failed to generate context summary: Codex auxiliary Responses stream exceeded ... total timeout
```

## Diagnosis

The issue is usually an auxiliary route/model mismatch, not a generic session-store failure:

1. Compaction sends a large middle-window summarization request as a single auxiliary LLM call.
2. `gpt-5.5` is a poor fit for synchronous compression on the available Codex/proxy routes, even when fine as the main reasoning model.
3. A localhost proxy adds another failure/retry layer before fallback.
4. Falling back to the main model repeats the slow path on `gpt-5.5` instead of escaping to a smaller compressor.
5. Legacy rotation mode (`compression.in_place: false`) can create confusing continuation rows: the child session exists immediately, but compressed messages may not be durably visible until the next post-compression turn flushes; if the turn is still running, `hermes sessions list` can show a blank continuation.
6. If the protected tail contains very large tool outputs (session_search/read_file/skill_view), compaction can reduce message count but still leave a high rough-token estimate.

## Preferred fix when OpenRouter is not available

Use OpenAI Codex OAuth directly for compression with a smaller model, and trigger compaction earlier:

```bash
hermes config set auxiliary.compression.provider openai-codex
hermes config set auxiliary.compression.model gpt-5.4-mini
hermes config set auxiliary.compression.base_url ''
hermes config set auxiliary.compression.api_key ''
hermes config set auxiliary.compression.timeout 120

hermes config set compression.threshold 0.50
hermes config set compression.codex_gpt55_autoraise false
```

Why:

- Direct `openai-codex / gpt-5.4-mini` is fast enough for the auxiliary compression workload in local smoke tests.
- `gpt-5.4-mini` has enough Codex-route context for a 50% trigger on a `272K` main context (`~136K`).
- Disabling `compression.codex_gpt55_autoraise` avoids pushing compaction into the `~231K` zone where large summarization calls can time out.

## Optional local-proxy fallback

If a local proxy fallback is desired, keep it on the smaller compressor, not `gpt-5.5`:

```yaml
auxiliary:
  compression:
    provider: openai-codex
    model: gpt-5.4-mini
    timeout: 120
    fallback_chain:
      - provider: custom
        model: gpt-5.4-mini
        base_url: http://localhost:8317/v1
        api_key: no-key-required
```

## Verification

- Check live config: `hermes config` or parse `~/.hermes/config.yaml` for `auxiliary.compression` and `compression`.
- Search logs for the markers above in `~/.hermes/logs/agent.log` and `~/.hermes/logs/errors.log`.
- Check sessions with `hermes sessions list` plus `state.db` when needed; blank child sessions immediately after compaction may mean the post-compaction turn is still running, not that the DB is irrecoverably corrupt.
- After applying config, restart the gateway or start a new Hermes session before expecting the route change to affect live conversations.
