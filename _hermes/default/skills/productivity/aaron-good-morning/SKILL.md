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
1. `~/Obsidian/AGENTS.md`
2. `~/Obsidian/adn_vault/AGENTS.md`
3. `~/Obsidian/adn_vault/_agents/AGENTS.md`
4. `~/Obsidian/adn_vault/_pi/agents/aaron-agent.md`
5. `~/Obsidian/adn_vault/_agents/commands/gm.md`
6. `~/Obsidian/adn_vault/_agents/gm-calendars.yaml`
7. `~/Obsidian/studio/Nodaste Agents/Protocol - Team Signal Standard.md`
8. `~/Obsidian/studio/Nodaste Agents/Operating Model.md`
9. Any explicitly referenced local files under `_agents/agents/` or `_agents/skills/`

## Required Working Directory

Run the workflow from:
- `~/Obsidian`

This matters because the repo-local AGENTS files and the `adn_vault/_agents/...` paths are part of the workflow contract. Treat `adn_vault/.opencode` only as a compatibility alias if it still exists.

## Execution Checklist

### 0. Load context before acting
Read these files first:
- `~/Obsidian/AGENTS.md`
- `~/Obsidian/adn_vault/AGENTS.md`
- `~/Obsidian/adn_vault/_agents/AGENTS.md`
- `~/Obsidian/adn_vault/_pi/agents/aaron-agent.md`
- `~/Obsidian/adn_vault/_agents/commands/gm.md`
- `~/Obsidian/adn_vault/_agents/gm-calendars.yaml`
- `~/Obsidian/studio/Nodaste Agents/Protocol - Team Signal Standard.md`
- `~/Obsidian/studio/Nodaste Agents/Operating Model.md`

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
- `~/Obsidian/adn_vault/_agents/gm-calendars.yaml`

Do not substitute Outlook, Fantastical, or other calendar query methods for this routine.

Implementation note from live runs:
- If the shell is Bash, do **not** `source ~/.zshrc` and then call `accli`; Aaron's machine emits Oh My Zsh/autoload errors in that path.
- Prefer running calendar commands with `zsh -lc 'accli events ... --json'` when you need Zsh-initialized CLI state.

### 4. Task, Linear, and reminder rule
Use the same source hierarchy the command expects:
- Todoist via `td` **as the primary task system**
- Linear via `LINEAR_API_KEY` / GraphQL for newly created issue awareness
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
- For Linear, query issues created this week (since the most recent Monday) across the NOD team, covering both the `Doc Thingy` and `Heddle` projects. Use `ltui --format json --limit 250 issues list --team NOD --created-since <monday-iso>` when `LINEAR_API_KEY` is not exported but `ltui` is available and `.ltui.json` is configured. If `ltui` is unavailable, fall back to `LINEAR_API_KEY` + GraphQL curl. Present the results as a weekly issue inventory, not a bare last-24h list:
  - Lead the weekly review with a "New Open Issues Assigned to Aaron" table — only issues newly created in the weekly window, assigned to Aaron, and still open/active (`Backlog`, `In Progress`, `Ready`, `In Review`, etc.) belong here. Do **not** include `Done`, `Canceled`/`Cancelled`, duplicate, or other terminal items in this table; terminal Aaron-assigned items belong in "Closed This Week" only.
  - Do **not** include a separate "By priority" / priority-breakdown section in the Good Morning Linear section; Aaron finds it redundant and wants the prior-week focus to stay on current Aaron-assigned work.
  - Within each Linear table (daily delta, Assigned to Aaron, Closed This Week), render issues in an aligned responsive grid/table with stable columns: linked ID, description/title, state badge, requestor/creator, assignee, project badge, compact updated date. Do not use spacer cells or colspan-based two-row layouts; they wrap poorly and misalign headers from values. On narrow screens, collapse each issue into a labeled card while preserving all seven fields. If creator is missing from the list snapshot, enrich via `ltui issues view <key> --include-history` plus `ltui users` and use the creation/earliest history actor when available; if still unavailable, say `Unknown` rather than omitting the field.
  - Include a "Closed This Week" list at the bottom.
  - Include an "Attention" subsection noting which Aaron-assigned issues are still open, which were created by others and assigned to Aaron but not yet picked up, and the highest-impact unassigned Backlog items as triage candidates.

  - The Linear section must lead with a "New in the Last 24 Hours" subsection (id="linear-last-24h") at the very top, before the weekly review. Query issues created in the last 24 hours (use `ltui --created-since <yesterday-iso>` or equivalent date filter). Present them in a highlighted table (same columns as the weekly tables). If no issues were created in the last 24 hours, show an empty-state note. This subsection is always present so Aaron can see the daily delta at a glance, then scroll down to the prior-week Aaron-assigned work.
  - The Linear section must not collapse to only the daily delta plus Doct plan/Linear audit. It must include a "Review of Prior Week" subsection with: New Open Issues Assigned to Aaron table, Closed This Week table, and Attention notes for Aaron-assigned open work and highest-impact unassigned Backlog candidates. Do not add a separate priority breakdown. If source data lacks creator fields, say that explicitly instead of guessing which Aaron-assigned issues were created by others.
  - The Linear section must include a compact Doct plan / Linear consistency audit for Heddle and Doc Thingy/Doct work whenever Doct plan data is available. Use `doct-agent plans board list --base-url https://doct.nodaste.com --workspace-id <workspace-id> --json` / `doct-agent plans queue list --base-url https://doct.nodaste.com --workspace-id <workspace-id> --all --json` plus `ltui --format json issues view <key>` evidence. For every active Doct plan card/document, verify there is exactly one linked Linear issue in the matching project, that the Linear state is active (`In Progress` or a clearly active review state such as `In Review`), and that the issue description links the exact Doct review URL. If a plan is already completed or its linked Linear issue is terminal, move the Doct plan state/board column to the appropriate done/completed state; if a non-ready plan is only planning/review, keep it in a planning/review column rather than surfacing it as in-progress. If an actually in-progress Doct/Heddle plan has no Linear issue, create/link one before publishing or explicitly flag `[DOCT PLAN/LINEAR MISMATCH]` with the blocker.
  - Every displayed Linear issue identifier (`NOD-###`) in the Linear section must be an HTML link to the Linear issue in all subsections, including tables, Attention bullets, and the Doct plan / Linear consistency audit. If the source payload lacks a URL, link to `https://linear.app/nodaste/issue/<identifier>` instead of rendering the ID as plain text or `<strong>` only.
- For Apple Reminders, do **not** use guessed options like `remindctl list --due today --json`; Aaron's current `remindctl` reports `Unknown option --due` for that form. Use `remindctl today --json`, `remindctl overdue --json`, and `remindctl week --json` instead.
- The local `.agents/my-tasks.yaml` mirror may lag Todoist; treat Todoist output as authoritative and use the YAML as fallback/context.

### 5. Signal review rule
Combine:
- studio vault signals under `studio/Nodaste Agents/Signals/...`
- C-Core signals via `ccore`

Live CLI notes from Hermes runs:
- `ccore health` works as expected.
- `ccore space list` normally returns real JSON on Aaron's machine; do not append `--json`.
- If `ccore health` is OK but `ccore space list` returns `unauthenticated` / `node_bootstrap_proof_required`, treat C-Core signal scanning as unavailable for `/gm` and report `[CCORE SIGNALS UNAVAILABLE] ccore space discovery requires bootstrap/auth`; continue the rest of the briefing.
- **Exception:** `ccore signal list nodaste --inbox-actor-id aaron --json` can succeed even when `ccore space list` fails with auth/discovery issues. If space list fails, try the direct inbox-actor-id signal query before declaring C-Core unavailable — it may still return Aaron's nonterminal signals.
- Parse `spaces` from the `ccore space list` object and prefer each space's `slug` when calling `ccore signal list <space> --json` (for example `nodaste`, `import-ddb69efd`). Filtering only by display-name-like plain-text lines can miss spaces.
- `ccore signal list <space> --json` works for space scans once space discovery succeeds.
- For `/gm`, filter C-Core results for actual actionability, not merely nonterminal status. Low-priority acknowledged/test/social signals like "Hello Aaron!", "It's working", or "Excited to play with HUD next" should not be surfaced unless there is a new update, explicit decision request, due date, high priority, or clear Aaron-owned follow-up. Put C-Core items under NEEDS RESPONSE / DECISION or CCORE ONLY only when they affect today's plan.
- If Aaron later says the surfaced signals are handled / obsolete, close them in C-Core with `ccore signal resolve ...` using each signal's `current_version_id`, then re-list and resolve any remaining nonterminal signals with fresh versions before declaring the signal queue clear.

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
- open coding sessions — do not render a generic session titled `develop` or `main`: Heddle's long-lived `develop` integration branch and `main` release branch are context, not resumable work. Named sessions currently on either branch remain eligible when they have specific evidence.
- writing momentum
- important personal email

Keep this concise. Surface only what should influence today's plan.

Coding-session exclusions: Aaron has retired `agent-of-empires`, and `plan-reviewer` is on ice. Exclude all historical coding-session records for either group from Active / resume candidates and any follow-up reporting; do not infer that an existing worktree makes either resumable. Do not render missing-path stale session records as cleanup or follow-up items in `/gm`; a missing historical worktree is archival noise unless Aaron explicitly asks to recover a named session. A direct Aaron instruction naming a specific session is a narrow exception: preserve that stable AoE ID in the deterministic priority-continuation registry, render it above ordinary resume candidates with grounded path/branch/dirty-state evidence, and retain the group-level exclusion for all other sessions. If Aaron names a successor project/worktree (including one on `dever`), render only the successor—not the legacy record—with its replacement path, linked issue/review artifact, remote state, and concrete first-resume step. Do not infer broad project reactivation from the exception.

Fastmail implementation note from live runs:
- The personal inbox mailbox name works as `Inbox` (capital I, lowercase rest) on Aaron's machine.
- `INBOX` may fail with `Mailbox not found`, so prefer querying `fastmail mail list --mailbox Inbox ...`.
- Aaron's current `fastmail mail list` CLI does **not** support `--unread`; fetch a bounded recent set (for example `--limit 20 --output json`) and filter client-side.
- The JSON payload is wrapped: top-level email items may live under `result.emails` rather than as a bare array. `keywords` is a map/object of flags (for example `$seen`, `$flagged`), not necessarily a list, so unread/flagged detection should check for key presence.

Todoist implementation note from live runs:
- `td today --json` and `td upcoming 3 --json` currently return an object with a `results` array, not a bare array.
- For `/gm`, parse `results`, dedupe by task id across the two calls, and then sync `.agents/my-tasks.yaml` from that merged set.

Granola implementation note from live runs:
- Aaron's current Granola transcript tool is the official public API CLI `granola-cli` (observed v0.2.5), not the old `granola meeting ...` CLI.
- Use `granola-cli --skip-updates auth status --json` and `granola-cli --skip-updates status --check-api --json` for health/auth checks. If auth is missing, the fix is `granola-cli auth <token>`; do **not** run the old `granola auth login` flow.
- `granola-cli notes list --all --json` returns a top-level object with `notes`, `hasMore`, and `cursor`. Each note has `id`, `title`, `created_at`, `updated_at`, and owner metadata; fetch details with `granola-cli notes get <note-id> --include transcript --json`.
- Prefer the repo-local script `python3 .agents/scripts/granola_sync_recent.py --days 7 --limit 10 --json` for `/gm`. It uses `granola-cli notes list/get/summary/transcript`, filters recent notes locally, writes transcripts under `adn_vault/Granola/<date>/`, writes summaries when available, and returns compact JSON.
- After sync, do not assume the returned relative path is the only valid local transcript location. During the transition, Granola transcripts may exist under either `adn_vault/Granola/...` or the historical nested `adn_vault/adn_vault/Granola/...`. If the reported path is not found, search both locations before treating the transcript as missing.
- New transcript frontmatter should include both compatibility `granola_meeting_id` and new `granola_id`, plus `granola_web_url`, `created_at`, `updated_at`, `source: granola_public_api`, and `cli: granola-cli`. Link the local Obsidian transcript and the Granola web URL in Recent Inputs when available.

## Pi-to-Hermes Adaptation Notes

This skill is the Hermes adaptation of the existing Pi routine.

Translate the setup this way:
- Pi prompt `/gm` -> Hermes skill `aaron-good-morning`
- Pi identity file `adn_vault/_pi/agents/aaron-agent.md` -> Hermes adopts the same Aaron-agent identity for this workflow
- Shared team protocol -> use the studio vault's Nodaste signal standard and operating model
- Repo-local command spec -> `adn_vault/_agents/commands/gm.md` remains the workflow spec

Do not improvise a different morning routine when the local `/gm` command already defines the sequence.

## Output Format and Delivery

Future `/gm` / good-morning runs should produce a Doct-backed HTML review artifact, not post the full briefing inline in chat. Use `doct-agent plans` through `doct-document-ops` for the current review surface. Do **not** use the legacy local `plan-review` CLI/service for new GM artifacts unless Aaron explicitly asks for the legacy local reviewer.

For cron delivery to Discord, prefer delivering the scheduled job to Aaron's configured Discord home channel via an explicit channel target (`deliver: "discord:1492535022811480126"`, currently `<#1492535022811480126>`) unless Aaron gives an existing thread target. Do **not** use bare `deliver: "discord"` for GM cron jobs created from a Discord thread: cron can resolve bare `discord` back to the saved origin thread instead of the configured home channel. Cron can target an existing thread via `discord:<channel_id>:<thread_id>` or `DISCORD_HOME_CHANNEL_THREAD_ID`, but it does not currently create a fresh Discord thread per run before final delivery. See `references/gm-cron-discord-delivery.md` for the tested pattern and limitation.

Session-specific examples and comment-handling patterns from the 2026-06-21 GM review are captured in `references/gm-plan-review-comment-patterns-2026-06-21.md`, but treat that reference as legacy-local-plan-review history. For current GM publishing and comment processing, follow this Doct-backed section and `doct-document-ops`.

Linear responsive table guidance from the 2026-06-28 deterministic GM review is captured in `references/gm-linear-responsive-tables.md`; use it when adjusting Linear formatting, column alignment, compact timestamps, linked IDs, or redundant priority sections.

Granola public-API CLI migration details from the 2026-06-28 rebuild are captured in `references/gm-granola-cli-migration-2026-06-28.md`; use it when adjusting `/gm` transcript sync, source links, or troubleshooting `granola-cli` auth/API shape.

Durable comment-listener history is captured in `references/gm-durable-comment-maintainer.md`, but it is historical only. Good Morning publishing must not start a Doct comment listener, register listener ownership, or launch a maintainer. If Aaron explicitly asks to process comments on a specific briefing, inspect and drain that document's queue interactively with `doct-agent plans queue list` / `plans agent next`; do not make the listener persistent. The migration/pitfall notes in `references/gm-doct-publish-listener-migration-2026-07-03.md` remain useful for Doct update versioning, same-date dry-run overwrite hazards, and duplicate-document cleanup.

Cron timeout recovery should recover the already-created artifact instead of rerunning the full collection pipeline, but registration now goes through Doct. If the scheduled GM run times out after creating `adn_vault/DailyGM/YYYY-MM-DD-gm.html` but before final delivery, recover the existing artifact: register/update it with `doct-agent plans register` / `doct-agent plans update`, preserve the returned Doct document id/workspace id/canonical URL/version, inspect the Doct queue once, create/verify the Todoist review task, then report the exact Doct URL and task ID.

Required delivery flow:
1. Generate a dark-mode semantic HTML document with stable `id` attributes for each major section and likely comment targets.
2. Store the canonical artifact under `adn_vault/DailyGM/YYYY-MM-DD-gm.html` unless the local command spec says otherwise.
3. Confirm Doct production auth/context before registration:
   ```bash
   doct-agent auth status --all --json
   doct-agent context --base-url https://doct.nodaste.com --json
   ```
4. Ensure the Personal workspace contains a top-level `Good Morning` folder (`path: good-morning`) and register the HTML with Doct into that folder using the `doct-document-ops` workflow:
   ```bash
   doct-agent plans register --base-url https://doct.nodaste.com --workspace-id 759bfae3-44f1-4ce5-9bff-9077d9933a21 --parent-id <good-morning-folder-id> --file adn_vault/DailyGM/YYYY-MM-DD-gm.html --source-format html --allow-untemplated --title "Good Morning YYYY-MM-DD" --json
   ```
   If updating an already-registered same-day artifact, prefer `doct-agent plans update --base-url https://doct.nodaste.com --id <document-id> --workspace-id 759bfae3-44f1-4ce5-9bff-9077d9933a21 --file adn_vault/DailyGM/YYYY-MM-DD-gm.html --source-format html --expected-version <version> --json`. For `<version>`, use the integer `version` from `doct-agent documents get --base-url https://doct.nodaste.com --id <document-id> --json`; do not use UUID-like `htmlVersionId` values from `plans show`. Cron reruns/retries for the same date should update the active same-day document instead of registering duplicates. If a same-day GM document is registered outside the `Good Morning` folder, move it with `doct-agent documents move --base-url https://doct.nodaste.com --id <document-id> --workspace-id 759bfae3-44f1-4ce5-9bff-9077d9933a21 --new-parent-id <good-morning-folder-id> --json` before finalizing.
5. Share only the canonical Doct URL returned by the command. If the response gives a relative URL, resolve it against `https://doct.nodaste.com` without reconstructing IDs from memory. Never share loopback, Tailscale, or local `plan-review` URLs for the default GM flow.
6. Inspect pending Doct work once with `doct-agent plans queue list --base-url https://doct.nodaste.com --workspace-id <workspace-id> --document-id <document-id> --json`.
7. Do not automatically start a comment listener in either interactive or cron mode. Do not write the briefing into `~/.hermes/state/gm-plan-maintainer/active-plans.json`.
8. If Aaron explicitly asks to process comments on one briefing, claim one item at a time with `doct-agent plans agent next --base-url https://doct.nodaste.com --workspace-id <workspace-id> --document-id <document-id> --json`; update the HTML artifact; push with `doct-agent plans update`; then `reply`, `ack`, and `resolve` with the returned thread/claim ids. Stop when the requested queue work is complete.

### Cron-mode Todoist review task

When running from a scheduled cron job, create a Todoist task due at 8:00 AM local time today: `Review good morning report: <exact Doct URL>`. Prefer `td task add` with `--due "YYYY-MM-DDT08:00:00" --priority p2`. Include the exact Doct URL in the task content so it is visible from Todoist. Verify the task creation output before finalizing.

The HTML briefing should still preserve the `/gm` section order from `adn_vault/_agents/commands/gm.md`:
- CALENDAR
- CROSS-BLOCK
- TASKS
- LINEAR
- REMINDERS
- AGENT SIGNALS
- RECENT INPUTS
- WRITING
- PERSONAL EMAIL
- URGENT
- FOCUS RECOMMENDATION

Additional HTML-specific requirements learned from review:
## Independent Review (mandatory)

Every `/gm` run must pass an independent accuracy review before the HTML artifact is registered and published.

### Protocol

1. **Build** the GM HTML artifact with the default model (the model configured in `model.default`, currently `glm-5.2:cloud`).
2. **Review** with GPT via OpenAI Codex (`--provider openai-codex -m gpt-5.6-sol`), reasoning level high, regardless of the builder model.
3. The reviewer receives the full HTML artifact text and is asked to verify: (a) every section is present and follows the `/gm` section order, (b) data items are internally consistent (no contradictions between sections), (c) no section is obviously incomplete or missing required fields, (d) no stale/duplicate/ghost items remain, and (e) the artifact is a faithful, accurate, and complete briefing for the day.
4. If the reviewer raises substantive issues, fix them in the HTML before publishing.
5. If the reviewer confirms the artifact is accurate and complete, proceed to register and publish.
6. Record the review outcome in the HTML artifact as a hidden or footer comment: `<!-- independent-review: <default_model> built, <reviewer_model> reviewed, <PASS|ISSUES_FIXED> <ISO timestamp> -->`.

### Implementation notes

- Use `delegate_task` to run the review in an isolated subagent context so the full HTML content does not pollute the main conversation.
- The subagent goal should be: "Review the Good Morning HTML briefing for accuracy, completeness, and internal consistency. Return PASS or a list of specific issues."
- Pass the full HTML content and the `/gm` section-order checklist as context.
- Do not register the artifact with Doct or create the Todoist review task until the review passes.
- If the OpenAI Codex provider is unavailable (auth expired, network issue), record `[INDEPENDENT REVIEW SKIPPED — <reason>]` in the HTML footer comment and proceed with publishing — do not block the morning briefing on reviewer unavailability.
- This protocol applies to both interactive and cron-mode GM runs.

## Guardrails

- Be concise; the final briefing should fit on one screen when possible.
- Lead with the most important constraints and time-sensitive items.
- Agent signals are high priority.
- Do not surface stale acknowledged signals with no new updates.
- Treat legacy `completed` signal files as closed/archived noise for briefing purposes, the same as `done`.
- When Aaron explicitly retires an historical coding-session record, add its stable Agent of Empires session ID to `RETIRED_SESSION_IDS` in `/Users/anichols/Obsidian/.agents/scripts/gm/coding_sessions_phase.py` and add a regression test. Do not render it as active, resumable, or stale work in future GM briefings.
- Do not wrap the whole `/gm` collection in one large `execute_code` script with many sequential tool calls; a timeout can discard all intermediate output. Prefer parallel/batched direct tool calls or small scripts with bounded outputs for each subsystem, then synthesize.
- Cron finalization robustness: after the HTML passes review, run Doct `doct-agent plans register`/update finalization, ownership-registry update, Todoist task creation, queue inspection, and verification as one bounded terminal/script step before returning to any long model reasoning. The 2026-06-27 run generated and reviewed the HTML but then hit the 600s cron inactivity watchdog before registration/Todoist because the parent model stalled after a nested `hermes chat` review subprocess returned PASS. Avoid leaving publish/finalize work dependent on another unbounded model turn; if necessary checkpoint the artifact and have a small recovery/publisher script finalize it.
- Cron context/compression robustness: the 2026-06-28 run failed earlier, before writing the HTML, after the GM agent reached ~170k prompt tokens and triggered context compression. The configured auxiliary compression route used the main reasoning model via `custom` at `http://localhost:8317/v1` with a 120s timeout, then timed out/retried long enough that the cron inactivity watchdog killed the job at 600s. Prevent recurrence by keeping the daily GM cron below the compression threshold (split collection/render/finalize into bounded scripts or smaller chained jobs, reduce loaded skill/prompt/tool output, and checkpoint intermediate JSON), or by changing cron/compression config so compression cannot out-idle the watchdog. Raising `HERMES_CRON_TIMEOUT` alone is a mitigation, not the primary fix.
- Deterministic runner introduced 2026-06-28: `/Users/anichols/Obsidian/.agents/scripts/gm_deterministic.py` wraps the package under `.agents/scripts/gm/`. It implements deterministic checkpoints for calendar, cross-block audit, Todoist mirror/tasks, Apple Reminders, Linear issue inventory, Doct plan/Linear consistency audit, vault + direct C-Core signal classification, Granola/recent-input carry-forward, cross-repo coding-session/merge scan, writing scan, bounded Fastmail importance filtering, dark-mode HTML rendering, deterministic review-marker checks, and dry-run/publish finalization. It writes phase JSON to `adn_vault/DailyGM/runs/YYYY-MM-DD/`, writes canonical HTML to `adn_vault/DailyGM/YYYY-MM-DD-gm.html`, and can be smoke-tested with `python3 .agents/scripts/gm_deterministic.py --date YYYY-MM-DD --dry-run`. Unit tests live at `adn_vault/_agents/tests/test_gm_deterministic.py` and pass with `python3 adn_vault/_agents/tests/test_gm_deterministic.py -v` from `/Users/anichols/Obsidian`. The production GM cron job `039f96dcecfc` runs script-only (`no_agent=true`) via `~/.hermes/scripts/gm_deterministic_cron.py` so daily delivery no longer depends on a long LLM turn or context compression. Dry-run verification on 2026-06-28 completed 11 phases in ~44s and produced HTML with review marker, Recent Inputs, Coding Sessions, and Linear audit sections. **2026-06-29 cron timeout fix:** Hermes no-agent scripts have a default 120s scheduler timeout even if the wrapper's internal subprocess timeout is longer; GM publish can take ~60-75s and previously timed out at 120s after already registering/creating side effects. Keep `cron.script_timeout_seconds: 900` in `~/.hermes/config.yaml` and verify with `hermes config check` / `cronjob run 039f96dcecfc` after changes. The publish finalizer now reuses an existing same-day Todoist review task for the exact plan URL before adding a new one, so repeated cron-trigger tests should not create duplicates. **Publish-state pitfall:** after a real same-day `--publish`, do not run `GM_DRY_RUN=1` or `--dry-run` for the same `YYYY-MM-DD` as a casual validation because it overwrites `runs/YYYY-MM-DD/manifest.json` and `publish.json` with dry-run metadata. Validate with unit tests, a non-publishing test date, or direct checks of the artifact, plan-review URL, Todoist task, and maintainer registry. If this already happened, restore the publish metadata from the verified plan id / URL / Todoist task. See `references/gm-deterministic-publish-state-2026-06-28.md`. Runtime comparison evidence for old LLM-agent cron vs deterministic no-agent cron is captured in `references/gm-deterministic-runtime-comparison-2026-06-29.md`; use it when Aaron asks whether the deterministic runner is faster, how long it takes, or where the current bottlenecks are.
### Rolling ecosystem intelligence monitoring

When Aaron asks to add rolling ecosystem/tool/project intelligence to `/gm`, use a deterministic, evidence-first collector rather than a free-form daily web-research prompt.

1. **Manifest is the authority.** Maintain a human-reviewed ecosystem manifest that declares tool/project IDs, aliases, upstream repositories/official feeds, lifecycle (`active`, `watch`, `inactive-broad`), local evidence patterns, relevance notes, and source preferences. Local inventory may propose additions or demotions, but must not silently rewrite the manifest. A clone alone is not evidence of active use.
2. **Inventory before relevance.** Collect local evidence from installed CLI versions, Hermes config/cron/skill/plugin references, declared source roots, and repository metadata. A remote host may contribute a narrow SSH JSON inventory probe, but that probe must not read secrets or publish a Good Morning/Doct/Todoist artifact. Confirm a remote host’s script/workdir paths and delivery entitlement before treating a copied GM cron as an independent publisher.
3. **Bounded primary sources.** Use manifest-declared GitHub official API targets, project-maintained RSS/Atom or release feeds, and official version metadata first. Configure one licensed web-search provider deliberately for broader discovery; do not depend on accidental provider fallback. X and Reddit are optional official-API adapters only—never browser/cookie scraping, CAPTCHA bypass, or protected-page automation fallbacks.
4. **Classify before narrative.** Normalize and fingerprint events with source + canonical identifier/URL + project + version/release/commit ID. Persist first/last seen, rolling-window membership, material updates, dismissals, and uptake status. Use deterministic relevance signals: manifest lifecycle, direct-use evidence, change class, uptake burden, source confidence, and novelty. A model may expand selected candidates only after this selection.
5. **Evidence bar.** `action_required` / mandatory uptake items require a primary official source and a direct local relevance link. Social/community/search-only findings may be `watch` items but cannot create mandatory uptake work. Routine commits should be compact or suppressed; materially updated items may reappear, ordinary duplicate fingerprints must not.
6. **Report contract.** Render stable section ID `ecosystem-intelligence` with six subsections: New since yesterday, This week, Uptake required/recommended, Discovery/patterns, Usage/manifest drift, and Collector health. Collector health must distinguish “no meaningful changes” from source/credential failure. Inactive tools remain in `inactive-broad` discovery coverage; they are not silently filtered out.
7. **Scheduling.** Prefer a quiet nightly pre-collector that checkpoints inventory/evidence before the deterministic 06:00 GM publisher runs. The GM job may use recent pre-collection state or a bounded fallback; do not add an unbounded LLM research step to the morning cron.

See `references/gm-ecosystem-intelligence-planning-2026-07-18.md` for the 2026-07-18 design details, source/credential posture, and audited remote-host caution.

### Active Doct plan portfolio Kanban

When Aaron asks to show plans in flight across Doct and agent sessions, add a deterministic plan-centric portfolio section rather than expanding the free-form Coding Sessions narrative.

1. Collect `plans board list` and `plans queue list` for both Personal and Shared workspaces. Include active registered plans in Backlog, Planning, and In Progress; exclude archived, Done, Not visible, routine Good Morning artifacts, and non-plan text documents.
2. Collect structured herdr pane/workspace inventory locally and, when configured, through a bounded remote JSON probe. Keep `remote unavailable`, `no match`, and `possible match` distinct.
3. Correlate with explainable evidence: exact Doct URL/document ID, Linear key, branch/worktree, source path, then repo + unique slug as a low-confidence candidate. Generic title similarity alone must not establish active work.
4. Render stable section ID `plan-kanban` before Coding Sessions. Each card includes title/link, workspace/project, update age, comment/action state, execution readiness, Doct working status, matched agent state, deterministic assessment, and named inconsistency flags.
5. Doct author colors represent identity, not pending/resolved semantics. Use explicit semantic rails/badges. Lifetime `commentCount` is not proof of unresolved work; when exact unresolved ordinary-comment counts are unavailable, say `resolution unknown`. Queued/claimed agent actions may be shown exactly.
6. Flag, but do not automatically repair: work started in Backlog, execution-ready plans still in Planning, In Progress plans without execution evidence, likely-complete work not moved to Done, stale plans, and duplicate/parallel sessions.
7. Keep the daily path model-free and read-only. Thresholds such as staleness age must be configurable and emitted with evidence.

See `references/gm-doct-herdr-plan-kanban.md` for the card contract, scoring model, assessment states, inconsistency rules, collector shape, and verification checklist.

### External client-repository change monitoring

When Aaron asks to fold a client/support portfolio into `/gm`, use a two-stage design rather than letting an LLM enumerate repositories ad hoc:

1. **Deterministic collector first.** Add a small checkpoint phase to the deterministic runner which enumerates the declared repository root, records the rolling-window commits, changed files, diff size, local dirty state, and canonical GitHub commit/PR links. Query GitHub as well as local Git history: local clones can be stale even when GitHub has recent activity. Persist the result as a named run checkpoint such as `client_changes.json`.
2. **Risk classification remains explainable.** Classify changes using explicit threshold rules and path/topic signals. High-signal categories include auth/authorization and Firebase rules, payments/payroll/financial data, booking/membership/inventory/customer data, schema/migrations, deployment/CI, backend/API behavior, destructive operations, unusually large diffs, and cross-application integration. Treat documentation-only changes as low signal.
3. **Agent review is bounded by the collector.** Schedule an LLM follow-up after the deterministic GM job; it should inspect only classifier-selected candidates and must read the actual diff plus relevant code context before recommending review. It should never infer risk from commit subjects alone or make changes to client repos.
4. **Keep it quiet by default.** If the collector finds neither commits nor local changes, report a single no-action line. Otherwise report activity level, `Review now` items with grounded reasons/links, optional `Watch / opportunity` items, and a clear recommendation.
5. **Schedule ordering.** Run the agent assessment after the deterministic collector has published its checkpoint, so it consumes the exact same evidence shown in the morning report.

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
