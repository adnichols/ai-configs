---
name: aaron-good-morning
description: Run Aaron's Obsidian-based good-morning routine from Hermes while adopting the aaron-agent / Nodaste signal protocol.
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [obsidian, morning-briefing, chief-of-staff, signals, aaron]
---

# Aaron Good Morning Routine

## Purpose

Use this skill to run Aaron's `/gm` morning briefing directly from Hermes, while honoring the same identity and operating protocol used by the Pi/shared-agents setup.

## When to Use

Trigger this skill when Aaron asks for any of:
- "good morning"
- `/gm`
- morning briefing
- chief-of-staff briefing
- start-of-day review

## Identity and Protocol Requirements

For this workflow, operate as **Aaron's agent** in the Obsidian workspace.

Adopt these identity values whenever reviewing or drafting Nodaste signals:
- `from_human: Aaron`
- `from_agent: aaron-agent`

Protocol constraints:
- Only scan Aaron's signal inbox unless Aaron explicitly asks otherwise.
- Inbox: `studio/Nodaste Agents/Signals/inbox/aaron/`
- Outbox: `studio/Nodaste Agents/Signals/outbox/aaron/`
- Follow the mirrored Nodaste signal protocol from the studio vault.
- Do not send messages or modify signals unless Aaron explicitly asks for that action.
- Treat acknowledged inbox signals as noise unless something changed after acknowledgment.
- Treat `done`, `cancelled`, and legacy `completed` statuses as terminal.

Startup assertion for this workflow:
> I am Aaron's agent. I monitor `studio/Nodaste Agents/Signals/inbox/aaron/`. I communicate as `from_human: Aaron`, `from_agent: aaron-agent`.

## Source of Truth

When these sources disagree, use them in this order:
1. `~/Documents/Obsidian/AGENTS.md`
2. `~/Documents/Obsidian/adn_vault/AGENTS.md`
3. `~/Documents/Obsidian/adn_vault/_agents/AGENTS.md`
4. `~/Documents/Obsidian/adn_vault/_pi/agents/aaron-agent.md`
5. `~/Documents/Obsidian/adn_vault/_agents/commands/gm.md`
6. `~/Documents/Obsidian/adn_vault/_agents/gm-calendars.yaml`
7. `~/Documents/Obsidian/studio/Nodaste Agents/Protocol - Team Signal Standard.md`
8. `~/Documents/Obsidian/studio/Nodaste Agents/Operating Model.md`
9. Any explicitly referenced local files under `_agents/agents/` or `_agents/skills/`

## Required Working Directory

Run the workflow from:
- `~/Documents/Obsidian`

This matters because the repo-local AGENTS files and the `adn_vault/_agents/...` paths are part of the workflow contract. Treat `adn_vault/.opencode` only as a compatibility alias if it still exists.

## Execution Checklist

### 0. Load context before acting
Read these files first:
- `~/Documents/Obsidian/AGENTS.md`
- `~/Documents/Obsidian/adn_vault/AGENTS.md`
- `~/Documents/Obsidian/adn_vault/_agents/AGENTS.md`
- `~/Documents/Obsidian/adn_vault/_pi/agents/aaron-agent.md`
- `~/Documents/Obsidian/adn_vault/_agents/commands/gm.md`
- `~/Documents/Obsidian/adn_vault/_agents/gm-calendars.yaml`
- `~/Documents/Obsidian/studio/Nodaste Agents/Protocol - Team Signal Standard.md`
- `~/Documents/Obsidian/studio/Nodaste Agents/Operating Model.md`

If `gm.md` references an `_agents/skills/*` skill or helper file, read that file too before continuing.

### 1. Get authoritative current time
Always use shell time/date commands. Never infer the day or timezone.

### 2. Run the `/gm` workflow order from `adn_vault/_agents/commands/gm.md`
Keep that file as the behavioral source of truth for:
- workflow order
- priorities
- fallback behavior
- final output structure

### 3. Calendar rule
Use `accli` only, and only for calendars listed in:
- `~/Documents/Obsidian/adn_vault/_agents/gm-calendars.yaml`

Do not substitute Outlook, Fantastical, or other calendar query methods for this routine.

Implementation note from live runs:
- If the shell is Bash, do **not** `source ~/.zshrc` and then call `accli`; Aaron's machine emits Oh My Zsh/autoload errors in that path.
- Prefer running calendar commands with `zsh -lc 'accli events ... --json'` when you need Zsh-initialized CLI state.

### 4. Task and reminder rule
Use the same source hierarchy the command expects:
- Todoist via `td` **as the primary task system**
- local mirror: `.agents/my-tasks.yaml`
- Apple Reminders via `remindctl` as an additional intake source

Interpretation rule for Aaron's workflow:
- Tasks are tracked primarily in Todoist.
- Apple Reminders may also receive tasks, but should not be treated as the canonical task list when Todoist is available.
- The local `.agents/my-tasks.yaml` mirror is supporting context, not the source of truth.

Live CLI notes from Hermes runs:
- Prefer `td today --json` for due-today + overdue in one parseable call.
- Prefer `td upcoming 3 --json` for the next 3 days. Older guesses like `td next 3` or `td overdue` may fail on Aaron's current CLI.
- Parse Todoist results, dedupe by task id, and overwrite `.agents/my-tasks.yaml` from the current merged Todoist set so stale completed/no-longer-listed mirror tasks stop surfacing.
- For Apple Reminders, do **not** use guessed options like `remindctl list --due today --json`; Aaron's current `remindctl` reports `Unknown option --due` for that form. Use `remindctl today --json`, `remindctl overdue --json`, and `remindctl week --json` instead.
- The local `.agents/my-tasks.yaml` mirror may lag Todoist; treat Todoist output as authoritative and use the YAML as fallback/context.

### 5. Signal review rule
Combine:
- studio vault signals under `studio/Nodaste Agents/Signals/...`
- C-Core signals via `ccore`

Live CLI notes from Hermes runs:
- `ccore health` works as expected.
- `ccore space list` normally returns real JSON on Aaron's machine; do not append `--json`.
- If `ccore health` is OK but `ccore space list` returns `unauthenticated` / `node_bootstrap_proof_required`, treat only C-Core signal scanning as unavailable for `/gm` and report `[CCORE SIGNALS UNAVAILABLE] ccore space discovery requires bootstrap/auth`; continue the rest of the briefing.
- Parse `spaces` from the `ccore space list` object and prefer each space's `slug` when calling `ccore signal list <space> --json` (for example `nodaste`, `import-ddb69efd`). Filtering only by display-name-like plain-text lines can miss spaces.
- `ccore signal list <space> --json` works for space scans once space discovery succeeds.
- For `/gm`, filter C-Core results for actual actionability, not merely nonterminal status. Low-priority acknowledged/test/social signals like "Hello Aaron!", "It's working", or "Excited to play with HUD next" should not be surfaced unless there is a new update, explicit decision request, due date, high priority, or clear Aaron-owned follow-up. Put C-Core items under NEEDS RESPONSE / DECISION or CCORE ONLY only when they affect today's plan.

But present them as one action-oriented view:
- NEEDS ACKNOWLEDGMENT
- NEEDS RESPONSE / DECISION
- WAITING ON OTHERS
- CCORE ONLY
- URGENT/ESCALATED

### 6. Carry-forward review rule
Also scan the recent-input sources described in `gm.md`, including:
- recent conversations
- Granola transcripts
- Snipd / clipped articles
- research queue candidates
- open coding sessions
- writing momentum
- important personal email

Keep this concise. Surface only what should influence today's plan.

Fastmail implementation note from live runs:
- The personal inbox mailbox name works as `Inbox` (capital I, lowercase rest) on Aaron's machine.
- `INBOX` may fail with `Mailbox not found`, so prefer querying `fastmail mail list --mailbox Inbox ...`.
- Aaron's current `fastmail mail list` CLI does **not** support `--unread`; fetch a bounded recent set (for example `--limit 20 --output json`) and filter client-side.
- The JSON payload is wrapped: top-level email items may live under `result.emails` rather than as a bare array. `keywords` is a map/object of flags (for example `$seen`, `$flagged`), not necessarily a list, so unread/flagged detection should check for key presence.

Todoist implementation note from live runs:
- `td today --json` and `td upcoming 3 --json` currently return an object with a `results` array, not a bare array.
- For `/gm`, parse `results`, dedupe by task id across the two calls, and then sync `.agents/my-tasks.yaml` from that merged set.

Granola implementation note from live runs:
- `granola meeting list -o json` can return very large rich-note payloads.
- When a tool path has stdout caps, that JSON may be truncated and produce a false `[GRANOLA SYNC UNAVAILABLE]` result even though Granola auth/list are healthy.
- Prefer the repo-local script `python3 .agents/scripts/granola_sync_recent.py --days 7 --limit 10 --json` for `/gm` instead of parsing the raw list output directly.
- After sync, do not assume the returned relative path is the only valid local transcript location. In Aaron's vault layout, Granola transcripts may resolve under either `adn_vault/Granola/...` or `adn_vault/adn_vault/Granola/...` depending on the script working directory and vault nesting. If the reported path is not found, search both locations before treating the transcript as missing.
- In practice, recent synced meetings like `Sync on Fueled Readout`, `Aaron - Munair`, and `STS (optional)` may exist only under the nested `adn_vault/adn_vault/Granola/<date>/...` path even when the sync summary reports `adn_vault/Granola/<date>/...`. For transcript follow-up during `/gm`, fall back to a filename search under both Granola roots before concluding the transcript is unavailable.

## Pi-to-Hermes Adaptation Notes

This skill is the Hermes adaptation of the existing Pi routine.

Translate the setup this way:
- Pi prompt `/gm` -> Hermes skill `aaron-good-morning`
- Pi identity file `adn_vault/_pi/agents/aaron-agent.md` -> Hermes adopts the same Aaron-agent identity for this workflow
- Shared team protocol -> use the studio vault's Nodaste signal standard and operating model
- Repo-local command spec -> `adn_vault/_agents/commands/gm.md` remains the workflow spec

Do not improvise a different morning routine when the local `/gm` command already defines the sequence.

## Output Format

Match the final format in `adn_vault/_agents/commands/gm.md`, including these sections in order:
- CALENDAR
- CROSS-BLOCK
- TASKS
- REMINDERS
- AGENT SIGNALS
- RECENT INPUTS
- WRITING
- PERSONAL EMAIL
- URGENT
- FOCUS RECOMMENDATION

End with:
> Want me to run a full triage, prep for meetings, or process agent signals?

## Guardrails

- Be concise; the final briefing should fit on one screen when possible.
- Lead with the most important constraints and time-sensitive items.
- Agent signals are high priority.
- Do not surface stale acknowledged signals with no new updates.
- Treat legacy `completed` signal files as closed/archived noise for briefing purposes, the same as `done`.
- Do not wrap the whole `/gm` collection in one large `execute_code` script with many sequential tool calls; a timeout can discard all intermediate output. Prefer parallel/batched direct tool calls or small scripts with bounded outputs for each subsystem, then synthesize.
- When Aaron explicitly says a signal is obsolete, clear it from active workflows by cancelling it, keeping only an archived record, and removing any active outbox mirror so it stops surfacing in `/gm`.
- If a supporting AGENT-COMMS or similar note still reads like live work after a signal is cancelled, move it to archive and rewrite it so it is clearly historical/obsolete.
- Do not scan other agents' inboxes unless Aaron explicitly asks.
- Do not send outbound communications without explicit approval.
- If a dependency is unavailable, continue with the prescribed fallback and clearly mark the unavailable section.

## Verification

Before finalizing the briefing, verify:
- date/day/timezone came from live system commands
- calendar data came from `accli`
- queried calendars were only those in `gm-calendars.yaml`
- signal review respected Aaron-only inbox scope
- protocol terminology matches the Nodaste standard
- final output follows the `/gm` section order
