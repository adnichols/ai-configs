---
name: trace-agent-action-provenance
description: Determine exactly when an action happened and which agent/system performed it by cross-checking Hermes sessions, cron jobs, watcher logs, vault artifacts, and Pi history.
version: 1.0.0
author: Hermes Agent
---

# Trace agent action provenance

Use this when Aaron asks questions like:
- "Who responded to this signal?"
- "Did Hermes or Pi do this?"
- "Exactly when did we respond?"
- "Dig through Hermes history and Pi history and figure it out"
- "Where is this unexpected model/API usage coming from?"
- "Which Pi/Codex session or subagent burned these tokens?"

Related reference:
- `references/pi-codex-model-usage-tracing.md` — concrete patterns for tracing unexpected Codex model usage across MBP/dever, Pi sidechains, Codex Desktop sessions, and subagent output files.

## Goal

Produce an evidence-backed attribution of:
1. **what acted** (Hermes chat session, Hermes cron job, watcher bridge, Pi session, etc.)
2. **when it acted** (detection time, session start, file-write time, session finish)
3. **which identity it used** (for example `aaron-agent`)

## High-value evidence sources

Check these in roughly this order:

1. **Target artifact itself**
   - Signal/note/task file that was changed
   - Look for `status`, `last_updated_at`, `## Response`, linked mirror path
   - This is the best source for **when the change landed**

2. **Hermes session recall**
   - Use `session_search` with broad OR queries containing:
     - signal id
     - project names
     - distinctive phrases from the response
   - If session_search finds a matching Hermes session, note:
     - `session_id`
     - `source` / `platform`
     - timestamp summary

3. **Hermes cron metadata**
   - `cronjob(action='list')` to identify relevant jobs
   - `~/.hermes/cron/jobs.json` to confirm:
     - job id
     - job name
     - schedule
     - prompt
     - whether it references identity files like `adn_vault/_pi/agents/aaron-agent.md`

4. **Hermes cron run outputs and raw session files**
   - `~/.hermes/cron/output/<job_id>/<timestamp>.md`
   - `~/.hermes/sessions/session_<session_id>.json`
   - Use these to confirm:
     - `platform` (for example `cron`)
     - `session_start`
     - `last_updated`
     - final assistant line like `Processed SIG-... -> done.`
     - any tool calls that read the relevant identity file or target artifact

5. **Watcher logs**
   - Especially useful for inbound signal detection and failed thread/webhook routing
   - Example path:
     - `~/.hermes/watchers/aaron-realtime/watcher.log`
   - Useful fields:
     - signal detection time
     - whether a Discord thread/webhook was attempted
     - whether watcher only notified vs actual processing happened elsewhere

6. **Live automation config vs documented policy**
   - When the question involves whether an automated agent was *allowed* to act, compare the live job config to the documented watcher policy.
   - Check both:
     - `~/.hermes/cron/jobs.json` for the actual active prompt
     - the relevant vault/runbook doc (for example `Watcher/Aaron Signal Watcher - Hermes Cron Setup.md`) for intended behavior
   - Explicitly look for prompt drift such as:
     - live cron says to `process`, update `status`, or write `## Response`
     - docs say the watcher is notify-only and should leave signals unchanged by default
   - If those disagree, report it as a **policy/config drift** issue, not just provenance.

7. **Pi history**
   - Search `~/.pi/agent/sessions/**/*.jsonl` for:
     - exact signal id
     - filename stem
     - project titles
     - unique phrases from the final written response
   - If no matches on multiple queries, say **no evidence found in Pi history**

8. **Unexpected model/API usage**
   - Check live config first on each relevant host:
     - `~/.pi/agent/settings.json` (`defaultProvider`, `defaultModel`, `enabledModels`)
     - `~/.codex/config.toml` (`model`, `model_provider`, profiles)
   - Then separate **actual usage** from **model availability/config mentions**:
     - Actual Pi calls: `message.model == <model>` in `~/.pi/agent/sessions/**/*.jsonl` or sidechain task outputs.
     - Model switches only: `type == "model_change"` may show selection intent, but not necessarily a completed billable call.
     - Codex Desktop availability: `session_meta.dynamic_tools` and model caches list available models; do not count these as usage.
   - For Pi subagents/sidechains, inspect output/task stores as well as main sessions:
     - `/tmp/pi-subagents-*/.../tasks/*.output`
     - worktree-local `.pi/side-agents/runtime/**` when present
     - active tmux/herdr panes and their working directories
   - If an agent definition names an unavailable/ambiguous provider alias (for example plain `openai-codex/gpt-5.6-sol`) but the host's registered providers are numbered (`openai-codex-2`, `openai-codex-3`, `openai-codex-4`), check whether the runtime fell back to the Pi default model.

## Recommended query strategy

### Hermes
Start broad, then narrow.

Examples:
- `SIG-20260414-1953 OR tinker OR Christie OR audit OR ana`
- exact distinctive final-response phrase

### Pi
Search multiple patterns, not just the signal id:
- exact signal id
- filename stem
- project note name
- doc names read during processing
- a distinctive sentence from the inserted response

If all Pi searches return zero, say so explicitly.

## Timestamp hierarchy

When multiple timestamps exist, report them separately:

1. **Watcher noticed it** — when the external watcher detected the item
2. **Processing session started** — when Hermes/Pi began handling it
3. **Artifact updated** — when the note/signal itself was changed (`last_updated_at`)
4. **Run finished** — when the cron/session output finalized

For "exactly when did we respond?", prefer:
- **artifact update time** as the best answer for when the response landed
- then optionally include session start and run-finish times for context

## Attribution rules

### Attribute to Hermes cron when all are true:
- matching Hermes session exists with `platform: cron`
- matching cron job prompt clearly covers the task
- cron output/session includes the target signal id or artifact
- artifact timestamps line up with the cron run

### Attribute to Pi only when supported by evidence:
- Pi session search finds the signal/project/response text
- and the timing aligns with the artifact update

### Identity attribution

If Hermes cron/job prompt references an identity file like:
- `~/Documents/Obsidian/adn_vault/_pi/agents/aaron-agent.md`
and the session read that file during execution, report:
- Hermes performed the action
- using the `aaron-agent` identity

Do **not** say Pi performed the action just because the identity file lives under `_pi/`.
That file can be used by Hermes as an identity source.

## Output pattern

Use a compact evidence-backed structure:

- **Response landed:** `<artifact update time>`
- **Detected:** `<watcher time>`
- **Processing session:** `<session id>`, `<platform>`, `<start time>`
- **Agent/system:** `<Hermes cron watcher / Hermes session / Pi>`
- **Identity used:** `<aaron-agent / Chief / unknown>`
- **Pi evidence:** `<found / no evidence found>`
- **Why I believe this:** 2-4 bullets citing concrete files

## Pitfalls

- Do not rely on just one timestamp.
- Do not infer Pi involvement from `_pi/` paths alone.
- Do not confuse watcher notification with actual processing.
- Do not stop after session_search; verify with files/logs.
- Do not claim certainty about Pi unless Pi history actually contains the target.
- For usage attribution, do not count raw grep hits in model caches, available-model tool schemas, or quoted transcripts as actual calls; parse the JSON records and distinguish `message.model` usage from `model_change` and configuration text.
- When tracing across MBP/dever, check both machines' live config and active process/session state; a local Codex Desktop session may be clean while remote Pi defaults or sidechains are producing usage.
