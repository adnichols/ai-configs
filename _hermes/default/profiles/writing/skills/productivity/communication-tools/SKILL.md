---
name: communication-tools
description: "Email and meeting communication tools: Himalaya CLI for IMAP/SMTP email, and Hermes Teams meeting pipeline for summaries and operations."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [email, imap, smtp, teams, meetings, communication, productivity, cli]
    related_skills: [google-workspace]
    category: productivity
---

# Communication Tools

Email and meeting communication workflows from the terminal. Covers two primary
areas: email management via the Himalaya CLI, and Microsoft Teams meeting
operations via the Hermes CLI pipeline.

## When to Use

Trigger this skill when the user asks about any of the following:

- Email: reading, sending, searching, listing, or managing emails
- IMAP/SMTP operations from the terminal
- Teams meeting summaries, transcripts, or action items
- Microsoft Graph webhook subscriptions or meeting pipeline operations
- "Summarize the Teams meeting", "check my email", "send an email", "reply to message"
- Pipeline status for Teams meeting ingestion, replay jobs, or troubleshooting

## Section 1: Email with Himalaya CLI

Himalaya is a CLI email client for IMAP, SMTP, Notmuch, and Sendmail backends.
Operates entirely through the terminal tool.

> **Email-only users note:** If the user only needs Gmail and no Calendar/Drive/Sheets,
> Himalaya is faster to set up than Google Workspace (no OAuth, just an App Password).
> If they need full Workspace access, use the `google-workspace` skill instead.

### Prerequisites

1. Himalaya CLI installed (`himalaya --version`)
2. Config file at `~/.config/himalaya/config.toml`
3. IMAP/SMTP credentials configured

### Installation

```bash
# Pre-built binary (Linux)
curl -sSL https://raw.githubusercontent.com/pimalaya/himalaya/master/install.sh | PREFIX=~/.local sh

# macOS via Homebrew
brew install himalaya
```

### Configuration

See `references/himalaya-configuration.md` for full config examples (Gmail, iCloud,
multiple accounts, Notmuch, OAuth2). The critical rules:

- Use `folder.aliases.X` (plural) — pre-v1.2.0 singular `alias` is silently ignored
- On Gmail, map `sent` to `[Gmail]/Sent Mail` to prevent duplicate sends
- Store passwords via `cmd` or keyring, never `raw` in committed files

### Common Email Operations

```bash
# List folders
himalaya folder list

# List emails (INBOX default)
himalaya envelope list
himalaya envelope list --folder "Sent" --page 1 --page-size 20

# Search
himalaya envelope list from john@example.com subject meeting

# Read a message
himalaya message read 42
himalaya message export 42 --full

# Reply / forward (non-interactive — pipe templates)
himalaya template reply 42 | sed 's/^$/\nYour reply text here\n/' | himalaya template send
himalaya template forward 42 | sed 's/^To:.*/To: newrecipient@example.com/' | himalaya template send

# Write new email (non-interactive — pipe via stdin)
cat << 'EOF' | himalaya template send
From: you@example.com
To: recipient@example.com
Subject: Test Message

Hello from Himalaya!
EOF

# Move / copy / delete
himalaya message move 42 "Archive"
himalaya message copy 42 "Important"
himalaya message delete 42

# Flags
himalaya flag add 42 --flag seen
himalaya flag remove 42 --flag seen

# Attachments
himalaya attachment download 42 --dir ~/Downloads

# Output as JSON for programmatic use
himalaya envelope list --output json
```

### Multiple Accounts

```bash
himalaya account list
himalaya --account work envelope list
```

### Debugging

```bash
RUST_LOG=debug himalaya envelope list
RUST_LOG=trace RUST_BACKTRACE=1 himalaya envelope list
```

### Hermes Integration Notes

- **Reading/listing/searching/moving/deleting** work directly through the terminal tool
- **Composing/replying/forwarding** — use piped stdin (`cat << EOF | himalaya template send`)
  for reliability. Interactive `$EDITOR` mode needs `pty=true` + background process.
- Use `--output json` for structured output
- `himalaya account configure` requires PTY mode: `terminal(command="himalaya account configure", pty=true)`

### Pitfalls

- **Always use `--folders-to-skip`** when crawling to avoid dependency directories
- **Folder aliases are plural** (`folder.aliases.X` not `folder.alias.X`)
- **Gmail requires App Password** if 2FA is enabled
- **Message IDs are folder-relative** — re-list after folder changes

## Section 2: Teams Meeting Pipeline

Operate the Hermes Teams meeting summary pipeline via the `hermes teams-pipeline`
CLI subcommands. All operator-facing commands run through the terminal tool.

### Prerequisites

Verify these are set in `${HERMES_HOME:-~/.hermes}/.env`:

```bash
MSGRAPH_TENANT_ID=...
MSGRAPH_CLIENT_ID=...
MSGRAPH_CLIENT_SECRET=...
```

If missing, direct the user to the Azure app registration guide.

### Command Reference

#### Status and inspection (start here)

```bash
hermes teams-pipeline validate              # config snapshot
hermes teams-pipeline token-health          # Graph token status
hermes teams-pipeline token-health --force-refresh
hermes teams-pipeline list                  # recent meeting jobs
hermes teams-pipeline list --status failed  # only failed jobs
hermes teams-pipeline show <job-id>         # full detail of one job
hermes teams-pipeline subscriptions         # current Graph webhook subscriptions
```

#### Re-running / debugging

```bash
hermes teams-pipeline run <job-id>          # replay a stored job
hermes teams-pipeline fetch --meeting-id <id>   # dry-run
hermes teams-pipeline fetch --join-web-url "<url>"   # dry-run by URL
```

#### Subscription management

```bash
hermes teams-pipeline subscribe \
  --resource communications/onlineMeetings/getAllTranscripts \
  --notification-url https://<your-public-host>/msgraph/webhook \
  --client-state "$MSGRAPH_WEBHOOK_CLIENT_STATE"

hermes teams-pipeline renew-subscription <sub-id> --expiration <iso-8601>
hermes teams-pipeline delete-subscription <sub-id>
hermes teams-pipeline maintain-subscriptions            # renew near-expiry
hermes teams-pipeline maintain-subscriptions --dry-run  # show what would be renewed
```

### Decision Tree

- "Why didn't I get a summary?" → `list --status failed`, then `show <job-id>`
- "Is setup working?" → `validate`, `token-health`, `subscriptions`
- "Re-run summary for meeting X" → `list` to find job ID, `run <job-id>`
- "Add meeting X to pipeline" → The pipeline is subscription-driven; for past meetings, use `fetch` then `run`

### Critical Pitfall: Graph subscriptions expire in 72 hours

Microsoft Graph caps webhook subscriptions at 72 hours and **does not auto-renew**.
If `maintain-subscriptions` is not scheduled, notifications silently stop.

When the user reports "worked yesterday but nothing today":
1. `subscriptions` — check if empty or expired
2. Recreate with `subscribe`
3. **Schedule automated renewal** via `hermes cron` or crontab at 12-hour intervals

### Other Pitfalls

- **Transcript not available yet** — Teams takes 2-5 minutes after a meeting ends
- **Delivery mode mismatch** — check `platforms.teams.extra.delivery_mode` in config
- **Graph app permissions** — token may acquire cleanly but 401/403 if admin consent wasn't re-granted after adding permissions

## Related Skills

- `google-workspace` — for Gmail, Calendar, Drive, Sheets, and Docs via OAuth
- `himalaya` was absorbed into this umbrella (email-only CLI client)
- `teams-meeting-pipeline` was absorbed into this umbrella (Teams meeting ops)
