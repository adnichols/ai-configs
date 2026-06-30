# Pinned skill update backlog — 2026-05 session

Context: during a Discord session with Aaron, the active work produced reusable lessons for two pinned skills. `skill_manage` refused direct updates.

## Blocked target: `aaron-good-morning`

Desired update: Good Morning / `/gm` signal presentation must include, for every surfaced signal in every bucket:

- **Status** — current vault or C-Core status
- **From** — sender/requester human or agent; use `Unknown` only when unavailable
- **Context** — concise request/context summary, not just title
- **Sent** — `created_at` / sent date, falling back to file modified time or C-Core `updated_at`
- **Responses sent** — content from `## Response` / response history; if empty, say `No response sent`; if C-Core exposes only `response_count`, say response count exists but text is unavailable in summary/doc views

Local source-of-truth file was successfully updated in the session:
`~/Documents/Obsidian/adn_vault/_agents/commands/gm.md`

The pinned Hermes skill should mirror this because it currently says to match that local command spec, but its SKILL.md lacks the explicit field list.

Unpin command if Aaron wants direct update:
`hermes curator unpin aaron-good-morning`

## Blocked target: `ccore-cli-operations`

Desired update: add a C-Core signal cleanup subsection.

Workflow verified live:

1. Inspect each signal and capture `current_version_id`:
   ```bash
   ccore signal get <signal-id>
   ```
2. Resolve with optimistic concurrency:
   ```bash
   ccore signal resolve <signal-id> --expected-current-version-id <version> --json
   ```
3. Remove from default active signal list:
   ```bash
   ccore signal delete <signal-id> --json
   ```
4. Verify:
   ```bash
   ccore signal list <space> --json
   ```
   Resolved/deleted signals should no longer appear in the default active list.

If resolve fails because the version changed, rerun `ccore signal get` and retry with the fresh `current_version_id`.

Also add `ccore signal delete <signal-id>` to the lifecycle command list.

Unpin command if Aaron wants direct update:
`hermes curator unpin ccore-cli-operations`
