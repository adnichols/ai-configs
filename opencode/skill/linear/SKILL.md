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

## Output Formats

ltui supports four output formats via `--format`:

### TSV (default, most token-efficient)
Tab-separated values with headers. Use for most operations.
```bash
ltui issues list --format tsv
```

### Table (human-readable)
Aligned columns for readability.
```bash
ltui issues list --format table
```

### Detail (key-value with sections)
Structured blocks with explicit markers for descriptions, comments. Use when full context needed.
```bash
ltui issues view ENG-42 --format detail
```
Output includes:
- `ISSUE:` - Issue identifier
- `DESCRIPTION_START` / `DESCRIPTION_END` - Description block
- `COMMENTS_START` / `COMMENTS_END` - Comments block
- `COMMENT_N` - Individual comment markers
- Fields as `key: value` pairs

### JSON (compact)
Compact JSON array without whitespace.
```bash
ltui issues list --format json
```

## Essential Commands

### Issues

**List issues:**
```bash
ltui issues list                              # All issues (paginated)
ltui issues list --team ENG                   # Filter by team
ltui issues list --assignee me --state "Todo" # Your todos
ltui issues list --label bug                  # By label
ltui issues list --search "login"             # Search
ltui issues list --fields id,key,title,state  # Specific fields only
```

**View issue:**
```bash
ltui issues view ENG-42                  # By identifier
ltui issues view ENG-42 --format detail  # With full context
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
ltui issues list --assignee me --state "Todo" --format table
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
ltui issues view ENG-42 --format detail
```

### Create parent-child issue relationship
```bash
ltui issues create --team ENG --title "Parent task" --format detail
# Output: ISSUE: ENG-42

ltui issues create --team ENG --title "Subtask" --format detail
# Output: ISSUE: ENG-43

ltui issues relate ENG-43 --parent ENG-42
```

## Best Practices for AI Agents

1. **Always check authentication first** - Run `ltui auth list` before first use in a session
2. **Use TSV format by default** - Most token-efficient for parsing
3. **Use detail format sparingly** - Only when descriptions/comments needed
4. **Filter early** - Use `--team`, `--project`, `--state` to reduce results
5. **Use `--fields`** - Select only needed columns to save tokens
6. **Parse errors first** - Don't proceed if output starts with `ERROR:`
7. **Respect pagination** - Use `--limit` and `--cursor` for large result sets
8. **Check for .ltui.json** - May contain project defaults for current directory
9. **Remember output is deterministic** - Same command = same output (for same Linear state)
10. **No interactivity** - All inputs must be via flags or environment variables

## Pagination

For large result sets:
```bash
ltui issues list --limit 50
# Output includes: CURSOR_NEXT: xyz789

ltui issues list --limit 50 --cursor xyz789  # Next page
```

## Configuration Files

- **`~/.config/ltui/config.json`** - Global profiles and default profile
- **`~/.config/ltui/cache.json`** - Entity lookup cache (5-minute TTL)
- **`.ltui.json`** - Per-directory project defaults (team, project, state, labels, assignee)

## When You Need More Detail

For comprehensive command listings with all available flags and options, read `references/ltui-command-reference.md`.
