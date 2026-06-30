# Deterministic outbound response guards

Use this pattern when a Hermes behavior contract must be enforced at delivery time, not merely encouraged through memory or prompt instructions.

## When this applies

- The user requires a hard guarantee that certain wording, markers, or data never reaches a messaging platform.
- Prompt/memory/skill instructions reduce risk but are insufficient because model output can still violate the rule.
- The gateway may stream partial assistant text before final response hooks run.

## Implementation pattern

1. Put shared detection/rewrite helpers in a gateway-boundary module such as `gateway/response_filters.py`.
2. Apply the guard on the normal final-send path after empty-response normalization and platform sanitization, before platform delivery.
3. Apply the same guard inside `GatewayStreamConsumer` before any visible send/edit/draft frame.
4. For streaming, add prefix-risk detection for partial text that could become a banned phrase. Hold the risky prefix until later tokens make it safe or the final guard replaces it.
5. For native draft streaming, disable draft frames on unsafe/risky text because drafts are user-visible before a final message exists.
6. For fallback/tail/commentary paths, guard those sends separately; they often bypass the main final-send branch.
7. Add regression tests for:
   - banned final text is replaced or blocked;
   - incidental allowed text is not blocked;
   - risky partial streamed prefixes are not sent;
   - later safe continuations still deliver;
   - existing silence/no-reply handling still works.

## Important caveat

`transform_llm_output` is useful for final-response rewriting, but it runs after the turn completes. It does not by itself prevent progressive streaming or draft delivery from exposing text earlier in the turn. For a hard no-leak guarantee, guard streaming or disable/buffer streaming for the affected scope.

## Verification command shape

Run focused gateway tests first, then nearby regression tests:

```bash
python -m pytest \
  tests/gateway/test_response_filters.py \
  tests/gateway/test_stream_consumer_response_guard.py \
  tests/gateway/test_gateway_silence_tokens.py \
  tests/test_transform_llm_output_hook.py -q
```

If the running agent is inside the gateway process, do not restart from that same process. Run `hermes gateway restart` from a separate shell so the restart command is not killed by its own gateway shutdown.
