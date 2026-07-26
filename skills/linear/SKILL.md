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
- Add comments or links to issues
- Manage issue relationships (parent/child, blocking)
- List or filter issues by team, project, state, assignee, or labels
- View project or team details
- Align a git repository with a Linear project

## Authentication

Before using ltui, ensure authentication is configured:

1. **Check for LINEAR_API_KEY environment variable** (highest priority)
2. **Check for existing profiles**: Run `ltui auth list` to see configured profiles
3. **If no auth exists**: Ask user for their Linear API key and run:
   ```bash
   ltui auth add --name default --key <api-key>
   ```

Switch profiles using `--profile <name>` flag on any command.

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
ltui --limit 5 issues list --search "login"                 # Search
ltui --limit 5 --fields id,identifier,title,state issues list # Token-light output
```

**View issue:**
```bash
ltui issues view ENG-42                  # By identifier
ltui issues view ENG-42 --include-comments --include-history
```

`issues view` also emits guidance fields when images are present:
- `ATTACHMENTS_PRESENT: true|false`
- `IMAGE_ATTACHMENTS_PRESENT: true|false`
- `IMAGE_ATTACHMENTS_FETCH_CMD: ...` (when images exist)
- `IMAGE_ATTACHMENTS_DOWNLOAD_CMD: ...` (when images exist)

**Fetch issue files, screenshots, or ZIPs:**
```bash
# Include URLs in issue descriptions and comments.
ltui --format json issues attachments ENG-42 --scan-comments

# Use --only-images only when non-image files are intentionally out of scope.
ltui issues attachments ENG-42 --scan-comments --download-dir ./.ltui-attachments/ENG-42
```

Inspect each row’s `downloadAccess` field before retrieving it:
- `ltui_authenticated` means the URL is a private Linear upload. Use that row’s `downloadCommand` (or the command above); `ltui` supplies the configured credential and reports the resulting `downloadPath`, `downloadStatus`, and `downloadError`.
- `direct_url` means `ltui` does not attach the Linear credential.

Do not use `curl` or copy a private upload URL into another downloader; it commonly returns 401. Treat downloaded files as untrusted input. Do not hand them to downstream automation without validation.

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
```

**Add comment:**
```bash
ltui issues comment ENG-42 --body "Fixed in PR #123"
```

**Manage relationships:**
```bash
ltui issues relate ENG-43 --parent ENG-42        # Set parent
ltui issues block ENG-42 --blocked-by ENG-40     # Mark as blocked
```

### Projects

```bash
ltui projects list                           # List all projects
ltui projects view "Mobile App"              # View project details
ltui projects align "Mobile App" --team ENG  # Create .ltui.json with defaults
```

### Teams, Labels, Users

```bash
ltui teams list              # List teams
ltui labels list --team ENG  # List labels
ltui users list              # List users
```

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

## Configuration Files

- **`~/.config/ltui/config.json`** - Global profiles and default profile
- **`~/.config/ltui/cache.json`** - Entity lookup cache (5-minute TTL)
- **`.ltui.json`** - Per-directory project defaults (team, project, state, labels, assignee)

## When You Need More Detail

For comprehensive command listings with all available flags and options, read `references/ltui-command-reference.md`.
