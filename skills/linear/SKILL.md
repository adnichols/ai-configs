---
name: linear
description: Use this skill when users request Linear issue tracking operations - creating, updating, viewing, or managing issues, projects, teams, or cycles. Linear is an issue tracker for software development.
---

# ltui - Linear CLI for AI Agents

Use this skill when you need to interact with Linear (issue tracking, project management) on behalf of the user.

## What is ltui?

`ltui` is a token-efficient Linear CLI designed specifically for AI coding agents. It provides:
- Deterministic, compact outputs optimized for LLM consumption
- Multiple output formats (tsv, table, detail, json)
- Structured error handling
- Common Linear workflow operations without requiring web browsing

## When to Use ltui

Use `ltui` when the user asks you to:
- Check Linear issues, projects, or teams
- Create or update Linear issues
- Add comments, links, or uploaded images to issues
- Fetch private Linear uploads (screenshots, ZIPs) with `issues attachments`
- Manage issue relationships (parent/child, blocking)
- List or filter issues by team, project, state, assignee, labels, or saved queries
- View project or team details

## Authentication

Before using ltui, ensure authentication is configured:

1. **Check for LINEAR_API_KEY environment variable** (highest priority)
2. **Check for existing profiles**: Run `ltui auth list` to see configured profiles
3. **If no auth exists**: Ask user for their Linear API key and run:
   ```bash
   ltui auth add --profile default --api-key <api-key>
   ```
4. **Verify**: `ltui auth test`

Switch profiles with `--profile <name>` or `LTUI_PROFILE`. There is no `auth use`.

## Rate Limits and Request Budget

Linear rate limits apply to the authenticated user, shared across that user's API keys and tools. Check the live response headers when diagnosing limits; common headers include `x-ratelimit-requests-limit`, `x-ratelimit-requests-remaining`, `x-ratelimit-requests-reset`, `x-ratelimit-complexity-limit`, and `x-ratelimit-complexity-remaining`.

For the Nodaste workspace checked on 2026-05-03, the live headers reported a 2,500 requests/hour request bucket and a 3,000,000 complexity/hour bucket for the current API user. Treat this as a live-header fact, not a permanent contract; Linear plan details and limits can change.

`ltui issues list` shapes its GraphQL request from `--fields`, so cheap field sets reduce both output tokens and relation fetching. Prefer `id,identifier,title,state,updatedAt` for grooming scans, and include `project`, `assignee`, or `labels` only when needed for the decision. Other commands may still use SDK convenience paths unless documented otherwise. Use `--show-rate-limit` when you need live budget metadata.

Put global options before the subcommand:
```bash
ltui --limit 5 --fields id,identifier,title,state issues list --team ENG
ltui --format json --show-rate-limit --fields id,identifier,title issues list --team ENG
ltui --format json issues view ENG-42
```

## Output Formats

ltui supports four output formats via `--format`:

### TSV (default, most token-efficient)
Tab-separated values with headers. Use for most operations.
```bash
ltui --format tsv issues list
```

### Table (human-readable)
Aligned columns for readability.
```bash
ltui --format table issues list
```

### Detail (key-value with sections)
Structured blocks with explicit markers for descriptions, comments. Use when full context needed.
```bash
ltui --format detail issues view ENG-42
```
Output includes:
- `ISSUE:` - Issue identifier
- `DESCRIPTION_START` / `DESCRIPTION_END` - Description block
- `COMMENTS_START` / `COMMENTS_END` - Comments block
- `COMMENT_N` - Individual comment markers
- Fields as `key: value` pairs

### JSON (compact)
Compact JSON envelope without whitespace.
```bash
ltui --format json issues list
```

For list commands, JSON is a single envelope object:

```json
{"meta":{"cursorNext":"","cursorPrev":"","count":1},"rows":[{"id":"..."}]}
```

## Essential Commands

### Issues

**List issues:**
```bash
ltui --limit 5 issues list                                  # Small page while exploring
ltui --limit 10 issues list --team ENG                      # Filter by team
ltui --limit 10 issues list --assignee me --state "Todo"    # Your todos
ltui --limit 10 issues list --label bug                     # By label
ltui --limit 5 issues list --search "login"
ltui --limit 5 --fields id,identifier,title,state issues list
ltui issues list --saved my-bugs --updated-since 2026-08-01
```

**View issue:**
```bash
ltui issues view ENG-42
ltui issues view ENG-42 --include-comments --include-history
ltui issues view ENG-42 --attachment-probe
```

Agent mode is on by default, so `issues view` does **not** scan attachments unless you pass `--attachment-probe`. Non-agent mode probes unless you pass `--no-attachment-probe`. When a probe runs it may emit:
- `ATTACHMENTS_PRESENT` / `IMAGE_ATTACHMENTS_PRESENT`
- `IMAGE_ATTACHMENTS_FETCH_CMD` / `IMAGE_ATTACHMENTS_DOWNLOAD_CMD` (images only; includes `--only-images`)
- `ATTACHMENTS_DOWNLOAD_CMD` / `ATTACHMENTS_DOWNLOAD_GUIDANCE` (any private `uploads.linear.app` file, including ZIPs; omits `--only-images`)

Do not treat view as the download path. Use `issues attachments`.

**Fetch issue files, screenshots, or ZIPs:**
```bash
ltui --format json issues attachments ENG-42 --scan-comments
ltui issues attachments ENG-42 --scan-comments --download-dir ./.ltui-attachments/ENG-42
```

`--scan-comments` is opt-in. `--only-images` drops ZIPs and other non-images. Downloads happen only with `--download-dir`. Caps are 512 MiB and 10 minutes.

Every JSON row includes `downloadAccess`, `downloadCommand`, `downloadPath`, `downloadStatus`, and `downloadError`:
- `ltui_authenticated`: origin is exactly `https://uploads.linear.app`. Run that row's `downloadCommand` (or `--download-dir`). `ltui` sends a GraphQL-compatible `Authorization` header: raw `lin_api_...` personal keys, `Bearer` only for OAuth tokens. Redirects fail closed. `Bearer lin_api_...` is HTTP 401.
- `direct_url`: no Linear credential is sent.

`public-file-urls-expire-in` signs markdown upload URLs in GraphQL bodies, not `attachment.url`. The same file can appear twice (unsigned attachment node + signed comment/description URL). Do not `curl` either URL. Treat downloaded files as untrusted.

**Upload a local image:**
```bash
ltui issues upload ENG-42 --file ./mockup.png --title "Proposed UI"
ltui issues upload ENG-42 --file ./mockup.png --no-comment
```

**Create issue:**
```bash
ltui issues create --team ENG --title "Fix bug"
ltui issues create --team ENG --title "Add feature" --description @spec.md
ltui issues create --title "Task" # Uses .ltui.json defaults if present
```

**Update issue:**
```bash
ltui issues update ENG-42 --state "In Progress"
ltui issues update ENG-42 --state "In Progress" --assignee me
ltui issues update ENG-42 --add-label bug --due 2026-09-01
```

`--label` replaces all labels. Use `--add-label` / `--remove-label` to change one. There is no `--cycle` on create/update; parent/child is `issues relate`.

**Add comment:**
```bash
ltui issues comment ENG-42 --body "Fixed in PR #123"
```

**Manage relationships:**
```bash
ltui issues relate ENG-43 --parent ENG-42
ltui issues block ENG-42 --blocked-by ENG-40
```

### Projects

```bash
ltui projects list                           # List all projects
ltui projects view "Mobile App"              # View project details
ltui projects align "Mobile App" --team ENG  # Create .ltui.json with defaults
```

### Teams, Labels, Users, and other list surfaces

```bash
ltui teams list
ltui labels --team ENG
ltui users --active-only
ltui cycles --team ENG
ltui documents list --search rfc
ltui notifications --unread-only
```

`labels` / `users` / `cycles` / `notifications` are list-only. There is no `labels create` or `auth use`.

For comprehensive command reference with all flags and options, see `references/ltui-command-reference.md`.

## Error Handling

All errors follow this structure:
```
ERROR: <code> <message>
HINT: <optional-hint>
```

Error codes:
- `auth_missing` - No API key configured (run `ltui auth add`)
- `auth_invalid` - Invalid API key
- `not_found` - Entity not found (check with list commands)
- `validation_error` - Invalid input (check `--help`)
- `api_error` - Linear API error
- `network_error` - Network failure
- `unknown` - Unexpected error

Always check for `ERROR:` prefix before parsing output.

## Common Workflows

### Check your assigned issues
```bash
ltui --limit 10 --format table issues list --assignee me --state "Todo"
```

### Create issue in current project context
```bash
# If .ltui.json exists with team/project defaults:
ltui issues create --title "New feature" --description @spec.md

# Otherwise specify explicitly:
ltui issues create --team ENG --project "API" --title "New feature"
```

### Move issue to in-progress and self-assign
```bash
ltui issues update ENG-42 --state "In Progress" --assignee me
```

### View issue with full context (description, comments)
```bash
ltui --format detail issues view ENG-42
```

### Create parent-child issue relationship
```bash
ltui --format detail issues create --team ENG --title "Parent task"
# Output: ISSUE: ENG-42

ltui --format detail issues create --team ENG --title "Subtask"
# Output: ISSUE: ENG-43

ltui issues relate ENG-43 --parent ENG-42
```

## Best Practices for AI Agents

1. **Always check authentication first** - Run `ltui auth list` before first use in a session
2. **Use TSV format by default** - Most token-efficient for parsing
3. **Use detail format sparingly** - Only when descriptions/comments needed
4. **Filter early** - Use `--team`, `--project`, `--state` to reduce results
5. **Keep list pages small** - Start with `--limit 5` or `--limit 10`; increase only when you truly need more rows
6. **Use cheap `--fields` for list scans** - `issues list` fetches only supported requested fields; start with `id,identifier,title,state,updatedAt` and add relation fields only when needed
7. **Avoid broad polling loops** - Do not repeatedly run unfiltered `issues list`, `projects list`, or search commands; reuse IDs and cached context from earlier output
8. **Operate on many issues only with explicit intent** - Bulk reads or updates should start from a known issue ID list, use narrow filters, and pause/back off when rate headers are low
9. **Parse errors first** - Don't proceed if output starts with `ERROR:`
10. **Respect pagination** - Use `--limit` and `--cursor` for large result sets
11. **Check for .ltui.json** - May contain project defaults for current directory
12. **Remember output is deterministic** - Same command = same output (for same Linear state)
13. **No interactivity** - All inputs must be via flags or environment variables

## Pagination

For large result sets:
```bash
ltui --limit 50 issues list
# TSV/table output includes: CURSOR_NEXT: xyz789

# JSON output includes: {"meta":{"cursorNext":"xyz789", ...},"rows":[...]}

ltui --limit 50 --cursor xyz789 issues list  # Next page
```

- **`~/.config/ltui/profiles.json`** - API keys by profile
- **`~/.config/ltui/config.json`** - default profile and workspace metadata
- **`~/.config/ltui/cache.json`** - entity lookup cache
- **`.ltui.json`** - per-directory project defaults (team, project, state, labels, assignee)

## When You Need More Detail

For comprehensive command listings with all available flags and options, read `references/ltui-command-reference.md`.
