# pi-vcc (vendored)

Vendored into `ai-configs` from `sting8k/pi-vcc` so this repo can ship a pinned local install plus repo-specific compaction behavior.

- Source: `https://github.com/sting8k/pi-vcc`
- Local package version: `0.3.6-ai-configs.1`
- Reviewed upstream version: `0.3.18`
- Reviewed upstream commit: `45e93e85d30da774c7b20212f192cae40b5beef4`
- License: MIT
- Local changes and selective uptake:
  - `/pi-vcc` carries the `__PI_VCC_MANUAL_BYPASS__` marker directly in-source so repo-managed auto-compaction and manual compaction both use pi-vcc without global patching
  - the compaction hook keeps the repo-local agent-only fallback tail and shifts the cut backward so a live `toolResult` never outlives its matching assistant tool call; if the kept tail would contain an orphaned tool result, pi-vcc reports a no-cut classification instead of forcing an unsafe cut
  - no-cut paths record diagnostic classifications such as `tiny_session`, `post_compaction_tail_too_short`, and `active_turn_no_safe_cut` for hook debugging and future extension status surfaces
  - continuation protocol version 2 writes phase-specific timing/epoch evidence while dual-reading immutable version-1 history; durable matching top-level `custom_message` persistence or matching continuation `message_start` is the acceptance boundary, and the first later assistant/tool lifecycle reconciles that durable boundary before classifying progress
  - continuation transactions use a strict privacy allowlist in `~/.pi/logs/pi-vcc.jsonl`; records distinguish created, waiting, submitted, consumed, progressed, stalled, settled, superseded, retrying, and failed without preserve/message/tool content or raw tool IDs
  - when pi-vcc interrupts active work, one process-wide package coordinator persists the request, submits with `deliverAs: "steer"`, gives queued work a full 15-second acceptance budget, tracks 60-second idle/15-minute tool-stall windows, records acceptance-expiry retry intent, uses host idle readiness for dropped idle sends while preserving settlement gating during active runs, applies the 1s/2s backoff, and retains ownership while stalled
  - session replacement through reload, new, resume, or fork releases the old process lease during the old runner's shutdown; new/resume/fork attempt to terminalize old-session work, but a persistence failure is logged and surfaced without retaining stale lease/listener/timer ownership, so every replacement runner can still register exactly one functional coordinator, handler, command, and tool set
  - reload reconstruction derives V1 and V2 tool-call correlation from durable assistant calls minus durable results; when Pi has reduced the pending count before persisting a parallel batch's results, the unmatched IDs remain non-authoritative candidates until a matching live update/completion disambiguates the still-running call, while unrelated activity stalls fail-closed
  - the continuation audit requires every settled transaction to have exactly one runtime-matching durable delivery across all retry submission ordinals; failed attempts without durable delivery remain retryable, while zero delivery and cross-retry duplicate delivery fail the audit
  - package continuation authority is coordinator-only; `PI_VCC_CONTINUATION_AUTHORITY` accepts only `coordinator`, and rollback requires restoring/reinstalling an archived package release rather than a runtime switch that could strand requests
  - the percentage-compaction extension owns only compaction timing and attempt intent (`active`/`none`); it has no legacy authority switch, copied wire publisher, or direct-send continuation timers. The package coordinator is the sole continuation authority and the sole loud-failure notifier
  - `compact_context` always means active maintenance and has no `resumePolicy` argument. `/compact-now` and plain `/pi-vcc` are terminal; successful `/pi-vcc <follow-up>` sends exactly one direct user message without coordinator duplication
  - runtime intent maps once at the details/request boundary: `active→active`, `none→terminal`. V1 histories remain readable (`compact_context` auto→active); every V2 auto payload and non-compact-context V1 auto is invalid persistence
  - scoped `./install.sh --pi-vcc` transactionally swaps the stable package mirror, settings registration, and live `percentage-compaction.ts` extension as one unit with injected-failpoint rollback
  - high-value upstream `0.3.18` uptake is intentionally selective: TUI-safe wrapping, `bashExecution` normalization/search/report correctness fixes, keep-token parsing, compaction reason/willRetry metadata, and overflow retry fallback; upstream commit extraction is intentionally skipped/deferred because commit details remain available through transcript and recall
  - upstream `0.4.0` uptake is intentionally deferred while stabilizing the vendored fork; installer output suppresses the stale-upstream notice by default unless `PI_VCC_SHOW_UPSTREAM_STALE=1` is set
  - this vendored copy preserves redaction, including compressed bash command redaction, even though upstream removed `src/core/redact.ts`
  - this vendored copy intentionally does **not** append the upstream `vcc_recall` reminder note to every summary; this repo keeps the pre-existing summary output contract while still stripping older injected note lines during merge
  - this vendored copy intentionally skips upstream active-lineage recall, settings scaffold, compact-all sentinel/orphan recovery, broad summary-quality churn, peer dependency range changes, tool-error omission, and binary demo assets
  - local tests and harnesses cover the repo-specific compaction safety contract and package-wide verification flow

Algorithmic conversation compactor for [Pi](https://github.com/badlogic/pi-mono). No LLM calls — produces a brief transcript via extraction and formatting.

Inspired by [VCC](https://github.com/lllyasviel/VCC) **(View-oriented Conversation Compiler)**.

## Why pi-vcc

|  | Pi default | pi-vcc |
|---|---|---|
| **Method** | LLM-generated summary | Algorithmic extraction, no LLM |
| **Determinism** | Non-deterministic, can hallucinate | Same input = same output, always |
| **Token reduction** | Varies | 35-99% on real sessions (higher on longer sessions) |
| **Compaction latency** | Waits for LLM call | 30-470ms, no API calls |
| **History after compaction** | Gone — agent only sees summary | Fully searchable via `vcc_recall` |
| **Repeated compactions** | Each rewrite risks losing more | Sections merge and accumulate |
| **Cost** | Burns tokens on summarization call | Zero — no API calls |
| **Structure** | Free-form prose | Brief transcript + bounded semantic sections |

### Real session metrics

Measured on real session JSONLs under `~/.pi/agent/sessions` (chars = rendered message text).

| Session | Messages | Before | After | Reduction | Time |
|---|---|---|---|---|---|
| Session A | 2,943 | 997,162 | 7,959 | 99.2% | 64ms |
| Session B | 1,703 | 428,334 | 7,762 | 98.2% | 29ms |
| Session C | 1,657 | 424,183 | 9,577 | 97.7% | 54ms |
| Session D | 1,004 | 2,258,477 | 4,439 | 99.8% | 30ms |
| Session E | 486 | 295,006 | 11,163 | 96.2% | 30ms |
| Session F | 46 | 5,234 | 3,364 | 35.7% | 5ms |
| Session G | 27 | 8,595 | 2,489 | 71.0% | 2ms |

## Features

- **No LLM** — purely algorithmic, zero extra API cost
- **Brief transcript** — chronological conversation flow, each tool call collapsed to a one-liner with `(#N)` refs, `bashExecution` commands rendered as user actions, text truncated to keep it compact
- **Semantic sections** — session goal, files & changes, compaction intent when present, outstanding context, and user preferences
- **Bounded merge** — rolling sections re-capped after merge instead of growing unbounded
- **Lossless recall** — `vcc_recall` reads raw session JSONL, so old history stays searchable across compactions
- **Regex search** — `vcc_recall` supports regex patterns (`hook|inject`, `fail.*build`) and OR-ranked multi-word queries
- **Result ranking** — search results ranked by term relevance, rare terms weighted higher than common ones
- **`/pi-vcc-recall`** — slash command to search history directly, results shown as collapsible message and auto-fed to agent as context
- **Fallback cut** — still works when Pi core returns nothing to summarize
- **TUI-safe wrapping** — wraps long compiled summary lines so Pi's terminal UI stays readable
- **Redaction** — strips passwords, API keys, secrets, with redaction preserved as the final compiled-output safety transform
- **`/pi-vcc`** — manual compaction on demand

## Install

From this repo, use the top-level installer rather than registering this worktree path directly:

```bash
./install.sh --pi
```

The installer syncs this package into the durable mirror `~/.pi/agent/local-packages/ai-configs/pi-vcc` and registers that path with Pi. This avoids leaving global Pi pointed at deleted e2e/worktree checkouts.

Upstream alternatives:

```bash
pi install npm:@sting8k/pi-vcc
pi install https://github.com/sting8k/pi-vcc
pi -e https://github.com/sting8k/pi-vcc
```

## Usage

Once installed, pi-vcc registers a `session_before_compact` hook.

- When Pi triggers a compaction, pi-vcc supplies the summary.
- To trigger compaction manually, run `/pi-vcc`.
- To search older history after compaction, use `vcc_recall`.
- To search and feed results to agent yourself, run `/pi-vcc-recall <query> [page:N]`.
  - Tip: type `/recall` and Pi will autocomplete to `/pi-vcc-recall`.

### Compacted message structure

```
[Session Goal]
- Fix the authentication bug in login flow
- [Scope change]
- Also update the session token refresh logic

[Files And Changes]
- Modified: src/auth/session.ts
- Created: tests/auth-refresh.test.ts

[Outstanding Context]
- lint check still failing on line 42

[User Preferences]
- Prefer Vietnamese responses
- Always run tests before committing

[user]
Fix the auth bug, users can't log in after password reset

[assistant]
Root cause is a missing token refresh after password reset...
* bash "bun test tests/auth.test.ts" (#12)
Tests: 8 passed, 4 failed — the refresh token isn't being set.
* edit "src/auth/session.ts" (#14)
Added token refresh call after password reset flow.
* bash "bun test tests/auth.test.ts" (#16)
Tests: 12 passed, 0 failed ✓

[user]
also update the session expiry logic

[assistant]
* bash "grep -n 'expiry' src/auth/session.ts" (#18)
...(truncated)
```

**Sections:**

| Section | Description |
|---|---|
| `[Session Goal]` | Initial goal + scope changes (regex-based extraction) |
| `[Files And Changes]` | Modified/created files from tool calls (capped) |
| `[Outstanding Context]` | Unresolved items — errors, pending questions |
| `[User Preferences]` | Regex-extracted from user messages (`always`, `never`, `prefer`...) |
| Brief transcript | Chronological conversation flow — rolling window of ~120 recent lines, tool calls collapsed to one-liners with `(#N)` refs |

**Merge policy:**
- `Session Goal`, `User Preferences`: concise sticky sections
- `Outstanding Context`: fresh-only (replaced each compaction)
- `Files And Changes`: unique union across compactions
- Brief transcript: rolling window, older lines drop off

## Recall (Lossless History)

Pi's default compaction discards old messages permanently. After compaction, the agent only sees the summary.

`vcc_recall` bypasses this by reading the raw session JSONL file directly. It parses every message entry in the file, regardless of how many compactions have happened.

### Search

Queries support **regex** and **multi-word OR logic** ranked by relevance:

```
vcc_recall({ query: "auth token" })           // OR search, ranked
vcc_recall({ query: "auth token", page: 2 })  // paginated (5 results/page)
vcc_recall({ query: "hook|inject" })           // regex pattern
vcc_recall({ query: "fail.*build" })           // regex pattern
```

### Browse

Without a query, returns the last 25 entries as brief summaries:

```
vcc_recall()
```

### Expand

Returns full untruncated content for specific indices found via search:

```
vcc_recall({ expand: [41, 42] })
```

Typical workflow: **search → find relevant entry indices → expand those indices for full content**.

> Some tool results are truncated by Pi core at save time. `expand` returns everything in the JSONL but can't recover what Pi already cut.

## Pipeline

1. **Normalize** — raw Pi messages → uniform blocks (user, assistant, tool_call, tool_result, thinking)
2. **Filter noise** — strip system messages, empty blocks
3. **Build sections** — extract goal, file paths, blockers, preferences
4. **Brief transcript** — chronological conversation flow, tool calls collapsed to one-liners, text truncated
5. **Format** — render into bracketed sections + transcript
6. **Merge** — if previous summary exists: sticky sections merge, volatile sections replace, transcript rolls
7. **Wrap + redact** — wrap long final summary lines and apply final redaction for passwords, API keys, secrets

## Debug

Debug logging is off by default. Enable it in `~/.pi/agent/pi-vcc-config.json`:

```json
{ "debug": true }
```

When enabled, each compaction writes detailed info to `/tmp/pi-vcc-debug.json` — message counts, cut boundary, summary preview, sections.

Continuation rollout checks are read-only/no-network. They live in the
ai-configs repository's top-level `scripts/` directory (not the package's own
`scripts/`), so run them from the ai-configs repo root:

```bash
bash scripts/verify-pi-vcc-install.sh
bash scripts/run-pi-vcc-continuation-soak.sh --candidate source --compactions 20 --fault-matrix all
bun scripts/pi-vcc-real-host-integration.ts --candidate source --cases all --session-mode file-backed --provider deterministic-fake
python3 scripts/audit-pi-vcc-continuations.py --require-terminal --since 24h --sessions ~/.pi/agent/sessions --log ~/.pi/logs/pi-vcc.jsonl
```

The soak executes the selected source or installed candidate modules in an isolated Pi directory and records the no-provider host-faithful boundary explicitly; it never silently substitutes source for an installed candidate.

## Related Work

- [VCC](https://github.com/lllyasviel/VCC) — the original transcript-preserving conversation compiler
- [Pi](https://github.com/badlogic/pi-mono) — the AI coding agent this extension is built for

## License

MIT
