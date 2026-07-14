---
date: 2026-07-12T23:10:11Z
author: codex
git_commit: 0321d74c4d1fba3bf78973d90c37ac830b16993e
branch: main
repository: ai-configs
type: research
status: complete
tags: [pi, codex, gpt-5.6, terminal-bench, responses-api, code-mode]
last_updated: 2026-07-12
---

# Research: Why Codex Outperforms Pi on GPT-5.6 Sol

## Research Question

Why did Codex CLI move from an exact tie with Pi on GPT-5.5 to a seven-task lead on GPT-5.6 Sol/high, and which Codex behaviors can be ported into Pi?

## Summary

The benchmark gap is real, but the GPT-5.6 comparison is not a model-only A/B. Codex and Pi use different protocol, prompt, tool, and loop stacks, and both CLI versions changed between the GPT-5.5 and GPT-5.6 runs.

The strongest release-specific explanation is that Codex 0.144 introduced a GPT-5.6-specific execution contract:

1. `tool_mode: code_mode_only`: GPT-5.6 receives one grammar-constrained JavaScript orchestration tool instead of the normal direct tool collection.
2. `use_responses_lite: true`: Codex uses native Responses semantics and preserves encrypted reasoning across tool turns with all-turn reasoning context.
3. A rewritten GPT-5.6 base prompt and updated execution loop.
4. GPT-5.6-specific context, truncation, verbosity, and multi-agent defaults.

Pi's benchmark path did not adopt that contract. It registered GPT-5.6 as `openai-completions`, used Chat Completions messages and Pi's stock `read`/`bash`/`edit`/`write` tools, and round-tripped only exposed reasoning text rather than encrypted reasoning state. Pi already contains an `openai-codex-responses` adapter with the missing Responses features, so the first port should be a benchmark provider that uses that adapter before attempting a larger tool-runtime rewrite.

## Benchmark Findings

### Headline result

| Run | Passed | Score | Errors | Cost |
| --- | ---: | ---: | ---: | ---: |
| Codex GPT-5.6 Sol/high | 71/89 | 79.8% | 4 | $77.20 |
| Pi GPT-5.6 Sol/high | 64/89 | 71.9% | 5 | $56.39 |
| Codex GPT-5.5/high | 63/89 | 70.8% | 4 | $74.07 |
| Pi GPT-5.5 neutral | 63/89 | 70.8% | 5 | $70.09 |

Codex gained eight net tasks between its GPT-5.5 and GPT-5.6 runs. Pi gained one. The GPT-5.6 comparison had 56 shared passes, 10 shared failures, 15 Codex-only passes, and 8 Pi-only passes.

Evidence: `/home/anichols/bench/pi-harness-evals/reports/terminal-bench-results-summary-2026-07-11.html:24`, `/home/anichols/bench/pi-harness-evals/reports/codex-vs-pi-terminal-bench-c4-comparison.md:3`.

### Iteration behavior changed in opposite directions

Aggregated from raw trajectories:

| Run | Model turns | Tool calls | Output tokens |
| --- | ---: | ---: | ---: |
| Codex GPT-5.6 | 2,210 | 2,125 | 566,663 |
| Pi GPT-5.6 | 1,075 | 1,392 | 393,742 |
| Codex GPT-5.5 | 1,560 | 2,325 | 727,536 |
| Pi GPT-5.5 | 1,335 | 1,310 | 418,563 |

Codex 5.6 used about twice as many model turns as Pi 5.6. Pi's turns fell relative to its GPT-5.5 run, while Codex's rose. This supports an agent-loop or tool-contract effect, but does not alone establish causality.

Codex's 81.2M input tokens were 94.6% cached; Pi's 16.5M were 50.9% cached. Those totals primarily reflect different request replay and accounting behavior, not five times more fresh useful context.

Evidence: raw results and transcripts under `/home/anichols/bench/pi-harness-evals/runs/codex-gpt56-sol-high-preheated-full-20260711T131557Z` and `/home/anichols/bench/pi-harness-evals/runs/pi-gpt56-sol-high-preheated-full-20260711T025328Z`.

### Controls and confounders

The comparable GPT-5.6 runs used all 89 Terminal-Bench 2.0 tasks, concurrency four, fresh containers, and complete agent-specific setup-image caches. Setup/install time was excluded.

The comparison still has important confounders:

- Codex changed from 0.142.5 in the GPT-5.5 run to 0.144.1 in the GPT-5.6 run.
- Pi changed from 0.73.1 in the GPT-5.5 run; the GPT-5.6 report did not preserve a usable Pi version.
- Each condition has one full-suite run, so stochastic task flips are not bounded by repeat measurements.
- Same model and effort did not mean same API, system prompt, tool schema, edit mechanism, context formatting, compaction, or continuation policy.

## Codex GPT-5.6 Release Contract

The bundled Codex 0.144.1 model catalog gives GPT-5.6 Sol settings that differ materially from GPT-5.5:

| Setting | GPT-5.6 Sol | GPT-5.5 |
| --- | --- | --- |
| Tool mode | `code_mode_only` | normal/direct tools |
| Responses Lite | `true` | `false` |
| Context window | 372,000 | 272,000 |
| Multi-agent version | `v2` | unset |
| Default reasoning | low | medium |
| Default verbosity | low | low |
| Apply-patch tool | freeform | freeform |
| Parallel tool calls | enabled | enabled |

The relevant model-catalog change is OpenAI Codex commit `3380969a29134630d56feb6218e8e8dcc5e8196d`, included in the July 9 0.144 release. That release also moved Code Mode to hosted mode by default and included Code Mode crash fixes.

Upstream evidence:

- https://github.com/openai/codex/releases/tag/rust-v0.144.0
- https://github.com/openai/codex/commit/3380969a29134630d56feb6218e8e8dcc5e8196d
- https://github.com/openai/codex/commit/3f6157004419e21547962670026c6f6001d06fe8

### Code Mode

Code Mode exposes a single freeform JavaScript `exec` tool. JavaScript running in an isolated V8 environment calls nested tool functions and can compose or parallelize their results. The live Codex benchmark trajectory shows this contract: shell checks were emitted as JavaScript that called `tools.exec_command`, and file creation used `tools.apply_patch`.

This is likely important because GPT-5.6 was released with an explicit `code_mode_only` preset. Pi instead presents separate `read`, `bash`, `edit`, and `write` schemas. Even when both ultimately execute shell commands, the model sees a different action language and orchestration affordance.

### Responses reasoning continuity

Codex's GPT-5.6 Responses Lite path includes reasoning parameters on each request, requests encrypted reasoning content, and carries that content forward with `reasoning.context = "all_turns"`. The associated 0.144.1 change is `d2d00b6632dc991aa4471db0529773029cae5d68`.

Pi's benchmark route uses its `openai-completions` adapter and sends Chat Completions `messages` plus `reasoning_effort`. The proxy translates this to the backing model, but Pi receives and stores only visible `reasoning_content`; it does not request or persist encrypted reasoning items. This can make each post-tool turn reconstruct hidden reasoning instead of continuing it.

This protocol delta aligns especially well with the timing of the benchmark split: Codex GPT-5.5 did not use Responses Lite, while GPT-5.6 does.

## Pi Findings

### Benchmark Pi does not use the native Responses adapter

`harbor_proxy_pi.py` registers the proxy provider with `api: "openai-completions"`. Pi therefore calls its Chat Completions implementation. The installed Pi package also contains an `openai-codex-responses` implementation that already supports:

- separate `instructions` and `input`;
- `store: false`;
- `text.verbosity`;
- nested `reasoning.effort` and `reasoning.summary`;
- encrypted reasoning continuity;
- `prompt_cache_key`;
- `tool_choice: auto`;
- parallel tool calls.

This makes transport parity a smaller and cleaner first port than recreating Codex wholesale.

Evidence: `/home/anichols/bench/pi-harness-evals/scripts/harbor_proxy_pi.py:25`, installed package files `@earendil-works/pi-ai/dist/api/openai-completions.js` and `@earendil-works/pi-ai/dist/api/openai-codex-responses.js`.

### The neutral GPT-config profile was probably not active

The benchmark wrapper writes neutral `gptConfig` settings, but only adds the `pi-gpt-config` package for forced-compaction profiles. `neutral` is not one of those profiles. Therefore the reported neutral verbosity and summary settings were probably not applied to requests.

Even if installed, the extension currently injects Responses-style `text` and nested `reasoning` fields into a Chat Completions payload. Whether the proxy honors those non-native Chat Completions fields requires wire capture.

Evidence: `/home/anichols/bench/pi-harness-evals/scripts/harbor_proxy_pi.py:106`, `:392`, and `:414`.

### The benchmark is not the live Pi setup

The live Pi executable is `@earendil-works/pi-coding-agent@0.80.6`, with a larger extension/package setup and local append-system instructions. The benchmark installs `@mariozechner/pi-coding-agent@latest` into its images and does not copy the live `APPEND_SYSTEM.md`. Results should therefore be described as Codex versus the benchmark Pi image, not Codex versus the complete live Pi configuration.

### Prompt and tools

Benchmark Pi receives Pi's stock compact coding prompt and four primary tools. Codex receives its release-specific base/developer prompt, permissions/environment messages, skills metadata, unified exec/code-mode schema, apply-patch semantics, and stronger instructions to inspect, implement, verify, and persist.

A task transcript illustrates the effect. For `cancel-async-tasks`, Codex inspected Python, chose a fixed worker pool with `asyncio.TaskGroup`, wrote via apply-patch, and tested both concurrency and cancellation. Pi created all tasks immediately behind a semaphore, which violated the verifier's queued-task behavior. This is one example rather than proof of the aggregate cause, but it demonstrates that the Codex loop induced a more targeted boundary test.

## Ranked Porting Hypotheses

### 1. Native Responses transport and reasoning continuity — highest confidence

Use Pi's Responses adapter against the same proxy. Preserve encrypted reasoning content across tool turns and set all-turn reasoning context. Keep prompt and tools unchanged for the first A/B.

Why first: this is a confirmed protocol mismatch, is explicitly enabled only for the new Codex GPT-5.6 preset, and Pi already has most of the implementation.

### 2. GPT-5.6 Code Mode tool contract — high confidence

Give Pi a single grammar-constrained JavaScript orchestration tool backed by its existing tools, or build a thin experimental extension that presents a Codex-compatible schema while dispatching to Pi operations.

Why second: `code_mode_only` is the clearest GPT-5.6-specific Codex feature. It may be part of the model's post-training action distribution.

### 3. Codex GPT-5.6 prompt and continuation policy — medium/high confidence

Run prompt parity separately from transport and tools. Include the concrete inspect/edit/test/persist behavior, but avoid importing Codex-only UI or collaboration instructions that do not affect Terminal-Bench.

Also test an explicit continuation policy that prevents early completion until the requested artifact exists and a relevant verification has run. Codex 5.6 used about twice as many model turns as Pi 5.6.

### 4. Unified/persistent exec semantics — medium confidence

Match Codex's session-aware execution, output truncation, and process polling behavior. Pi's blocking bash tool truncates to the last 2,000 lines or 50 KB. This may matter on compilation, training, and long-running tasks.

### 5. Compaction and context policy — lower confidence for this suite

Normal Pi runs compact only near the 372k limit, and many Terminal-Bench tasks likely finish below it. Retest only after the protocol/tool/prompt layers, unless individual failing transcripts show compaction.

## Recommended Ablation Matrix

Use a discriminating subset containing the 15 Codex-only GPT-5.6 wins plus several shared wins and Pi-only wins as controls. Pin exact Pi and Codex versions and repeat each condition at least three times.

| Stage | Transport | Prompt | Tools | Purpose |
| --- | --- | --- | --- | --- |
| A | Current Chat Completions | Current Pi | Current Pi | reproduce baseline |
| B | Native Responses + encrypted continuity | Current Pi | Current Pi | isolate protocol |
| C | B | Codex-aligned execution prompt | Current Pi | isolate prompt/loop |
| D | B | Current Pi | Code Mode wrapper | isolate tool contract |
| E | B | Codex-aligned | Code Mode wrapper | combined candidate |
| F | E | E | persistent/unified exec | long-task reliability |

Capture for every task:

- exact CLI/package version;
- serialized request shape with secrets redacted;
- tool schemas and system/developer prompt hashes;
- reasoning item IDs/encrypted-content presence;
- model turns, tool calls, verification commands, duration, reward, and exception;
- setup-image identity and proxy version.

The first implementation target should be Stage B. If it recovers a meaningful portion of the seven-task gap, then Code Mode and prompt parity can be evaluated without conflating the transport failure.

## Code References

- `/home/anichols/bench/pi-harness-evals/scripts/harbor_proxy_pi.py:25` - Pi benchmark provider uses `openai-completions`.
- `/home/anichols/bench/pi-harness-evals/scripts/harbor_proxy_pi.py:291` - Pi benchmark CLI invocation.
- `/home/anichols/bench/pi-harness-evals/scripts/run_codex_terminal_bench_baseline.py:59` - Codex benchmark environment and reasoning configuration.
- `/home/anichols/bench/pi-harness-evals/reports/terminal-bench-results-summary-2026-07-11.html:24` - GPT-5.6 result summary.
- `/home/anichols/bench/pi-harness-evals/reports/terminal-bench-results-summary-2026-07-11.html:51` - token, cost, and runtime comparison.
- `/home/anichols/bench/pi-harness-evals/reports/terminal-bench-results-summary-2026-07-11.html:60` - task overlap.
- `/home/anichols/bench/pi-harness-evals/reports/codex-vs-pi-terminal-bench-c4-comparison.md:3` - GPT-5.5 exact tie.
- `@earendil-works/pi-ai/dist/api/openai-completions.js` - Pi Chat Completions request construction.
- `@earendil-works/pi-ai/dist/api/openai-codex-responses.js` - Pi native Responses request construction and reasoning continuity.
- `codex-rs/models-manager/models.json` at `rust-v0.144.1` - GPT-5.6-specific Codex preset.

## Open Questions

- Does CLIProxyAPI preserve and return encrypted reasoning content on the Pi Responses route?
- Which Codex model-catalog source won during the measured run: bundled 0.144.1 metadata, proxy-fetched metadata, or a merged result?
- How much of the seven-task difference survives three or more repeated full or discriminating-subset runs?
- Can Pi expose Code Mode through an extension without forking the core agent loop?
- Did any of the 15 Codex-only tasks trigger Pi compaction or bash-output truncation?
