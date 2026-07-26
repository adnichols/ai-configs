# ltui Complete Command Reference

This document provides comprehensive command listings for ltui with all available flags and options. For quick reference and common workflows, see the main SKILL.md.

## Issues Commands

### `ltui issues list`

List and filter issues with extensive options.

Global options such as `--format`, `--fields`, `--limit`, `--cursor`, `--profile`, and `--show-rate-limit` must appear before the command path, for example `ltui --format json --fields id,title issues list --team ENG`.

**All filter options:**
```bash
ltui issues list [options]

Options:
  --team <key>           Filter by team key (e.g., ENG, PROD)
  --project <name|id>    Filter by project name or ID
  --state <name|id>      Filter by state name or ID (repeatable)
  --assignee <email|id>  Filter by assignee (use "me" for yourself)
  --label <name>         Filter by label (can be used multiple times)
  --search <query>       Search issues by text
```

**Examples:**
```bash
# All issues (paginated)
ltui issues list

# Filter by team
ltui issues list --team ENG

# Filter by project
ltui issues list --project "Mobile App"

# Filter by state
ltui issues list --state "In Progress"
ltui issues list --state "Todo" --state "In Progress"

# Filter by assignee
ltui issues list --assignee me
ltui issues list --assignee alice@example.com

# Filter by labels (multiple allowed)
ltui issues list --label bug --label critical

# Search issues
ltui issues list --search "login"

# Combine filters
ltui issues list --team ENG --state "Todo" --assignee me

# Limit results
ltui --limit 10 issues list

# Get specific fields only
ltui --fields id,key,title,state issues list
ltui --format json --show-rate-limit --fields id,identifier,title issues list

# Pagination
ltui --limit 50 issues list
ltui --limit 50 --cursor xyz789 issues list
```

### `ltui issues attachments`

List issue attachments and uploaded file URLs.

This command is optimized for agents that need to reliably discover screenshots/images associated with an issue. It combines:
- Linear link attachments (`issue.attachments`)
- `https://uploads.linear.app/...` URLs extracted from the issue description and comments

**Options:**
```bash
ltui issues attachments <identifier> [options]

Arguments:
  <identifier>              Issue identifier (e.g., ENG-42) or ID

Options:
  --only-images             Only include image-like entries
  --download-dir <dir>      Download matching entries to this directory
  --overwrite               Overwrite existing files
  --no-linear-attachments   Exclude Linear attachments (issue.attachments)
  --no-upload-urls          Exclude uploads.linear.app URLs extracted from markdown
  --scan-comments           Scan issue comments for uploads.linear.app URLs
  --max-comments <n>        Maximum comments scanned with --scan-comments (default: 50)
```

**Examples:**
```bash
# Fetch all discoverable files, including private uploads in comments
ltui --format json issues attachments ENG-42 --scan-comments

# Download screenshots and ZIPs.  Omit --only-images for non-image evidence.
ltui issues attachments ENG-42 --scan-comments --download-dir ./.ltui-attachments/ENG-42
```

Every row includes `downloadAccess`, `downloadCommand`, `downloadPath`, `downloadStatus`, and `downloadError`.

- `downloadAccess: ltui_authenticated` identifies a private `https://uploads.linear.app` file. Run its `downloadCommand`; `ltui` sends the configured Linear credential only to that exact origin and rejects authenticated redirects.
- `downloadAccess: direct_url` means no Linear credential is sent.

Do not use a generic downloader for `ltui_authenticated` URLs: it can fail with HTTP 401. Downloaded files are untrusted input. Validate them before using them in downstream tooling or automation.

### `ltui issues view`

View detailed information about a specific issue.

**Options:**
```bash
ltui issues view <identifier> [options]

Arguments:
  <identifier>         Issue identifier (e.g., ENG-42) or ID

Options:
  --include-comments         Include comments
  --include-history          Include history
  --no-attachment-probe      Skip default attachment/comment scan for image guidance
  --max-description-chars <n> Max description chars (default: 4000)
  --max-comment-chars <n>     Max comment chars (default: 500)
```

**Examples:**
```bash
# By identifier
ltui issues view ENG-42

# By ID
ltui issues view abc123-def-456

# Use detail format to see description and comments
ltui issues view ENG-42 --include-comments --include-history
```

### `ltui issues create`

Create a new issue.

**Options:**
```bash
ltui issues create [options]

Required (unless defaults in .ltui.json):
  --team <key>              Team key (e.g., ENG)
  --title <text>            Issue title

Optional:
  --project <name|id>       Project name or ID
  --description <text|@file> Issue description (use @file to read from file)
  --state <name|id>         State name or ID
  --assignee <email|id>     Assignee email or ID (use "me" for yourself)
  --label <name>            Label name (can be used multiple times)
  --priority <0-4>          Priority (0=None, 1=Urgent, 2=High, 3=Normal, 4=Low)
  --estimate <n>            Estimate in points
  --parent <identifier>     Parent issue identifier
  --cycle <name|id>         Cycle name or ID
```

**Examples:**
```bash
# Minimal (uses defaults from .ltui.json if present)
ltui issues create --title "Fix broken test"

# With team
ltui issues create --team ENG --title "Fix broken test"

# Full specification
ltui issues create \
  --team ENG \
  --project "Mobile App" \
  --title "Fix login bug" \
  --description "Users cannot login with email" \
  --state "Todo" \
  --assignee me \
  --label bug \
  --label high-priority \
  --priority 1 \
  --estimate 3

# Description from file
ltui issues create --title "Feature spec" --description @spec.md

# With parent issue
ltui issues create --team ENG --title "Subtask" --parent ENG-42
```

### `ltui issues update`

Update an existing issue.

**Options:**
```bash
ltui issues update <identifier> [options]

Arguments:
  <identifier>              Issue identifier (e.g., ENG-42) or ID

Options:
  --title <text>            Update title
  --description <text|@file> Update description
  --state <name|id>         Update state
  --assignee <email|id>     Update assignee (use "me" or "unassigned")
  --label <name>            Set labels (replaces all, can be used multiple times)
  --priority <0-4>          Update priority
  --estimate <n>            Update estimate
  --project <name|id>       Move to different project
  --cycle <name|id>         Move to different cycle
```

**Examples:**
```bash
# Update state
ltui issues update ENG-42 --state "In Progress"

# Update assignee
ltui issues update ENG-42 --assignee alice@example.com
ltui issues update ENG-42 --assignee me

# Update multiple fields
ltui issues update ENG-42 \
  --state "In Progress" \
  --assignee me \
  --priority 2

# Update labels (replaces all existing labels)
ltui issues update ENG-42 --label bug --label backend

# Update description from file
ltui issues update ENG-42 --description @updated-spec.md

# Move to different project
ltui issues update ENG-42 --project "Backend API"

# Unassign issue
ltui issues update ENG-42 --assignee unassigned
```

### `ltui issues comment`

Add a comment to an issue.

**Options:**
```bash
ltui issues comment <identifier> [options]

Arguments:
  <identifier>         Issue identifier (e.g., ENG-42) or ID

Required:
  --body <text|@file>  Comment text (use @file to read from file)

Options:
  (none; use global options before the command path)
```

**Examples:**
```bash
# Inline text
ltui issues comment ENG-42 --body "Fixed in PR #123"

# From file
ltui issues comment ENG-42 --body @comment.md

# Multi-line inline
ltui issues comment ENG-42 --body "Line 1
Line 2
Line 3"
```

### `ltui issues link`

Add a link/attachment to an issue.

**Options:**
```bash
ltui issues link <identifier> [options]

Arguments:
  <identifier>        Issue identifier (e.g., ENG-42) or ID

Required:
  --url <url>         URL to link

Optional:
  --title <text>      Link title (defaults to URL)
```

**Examples:**
```bash
# Basic link
ltui issues link ENG-42 --url "https://github.com/org/repo/pull/123"

# With custom title
ltui issues link ENG-42 \
  --url "https://github.com/org/repo/pull/123" \
  --title "PR #123"
```

### `ltui issues relate`

Set parent-child relationship between issues.

**Options:**
```bash
ltui issues relate <identifier> [options]

Arguments:
  <identifier>        Child issue identifier (e.g., ENG-43)

Required:
  --parent <id>       Parent issue identifier (e.g., ENG-42)

Options:
  (none; use global options before the command path)
```

**Examples:**
```bash
# Set parent-child relationship
ltui issues relate ENG-43 --parent ENG-42
```

### `ltui issues block`

Mark issue as blocked by another issue.

**Options:**
```bash
ltui issues block <identifier> [options]

Arguments:
  <identifier>          Issue identifier (e.g., ENG-42)

Required:
  --blocked-by <id>     Issue that blocks this one (e.g., ENG-40)

Options:
  (none; use global options before the command path)
```

**Examples:**
```bash
# Mark as blocked
ltui issues block ENG-42 --blocked-by ENG-40
```

### `ltui issues saved`

Manage saved queries for frequently used filters.

**Subcommands:**
```bash
ltui issues saved add <name> [filter-options]
ltui issues saved list
ltui issues saved remove <name>
```

**Examples:**
```bash
# Save a query
ltui issues saved add my-bugs \
  --assignee me \
  --label bug \
  --state "Todo"

# Use saved query
ltui issues list --saved my-bugs

# List saved queries
ltui issues saved list

# Remove saved query
ltui issues saved remove my-bugs
```

## Projects Commands

### `ltui projects list`

List all projects.

**Options:**
```bash
ltui projects list [options]

Options:
  --team <key>         Filter by team
```

**Examples:**
```bash
# List all projects
ltui projects list

# Filter by team
ltui projects list --team ENG

# Human-readable format
ltui --format table projects list
```

### `ltui projects view`

View detailed project information.

**Options:**
```bash
ltui projects view <name|id> [options]

Arguments:
  <name|id>           Project name or ID

Options:
  (none; use global options before the command path)
```

**Examples:**
```bash
# By name
ltui projects view "Mobile App"

# By ID
ltui projects view abc123-def-456

# Detail format
ltui --format detail projects view "Mobile App"
```

### `ltui projects align`

Create .ltui.json configuration file with project defaults.

**Options:**
```bash
ltui projects align <name|id> [options]

Arguments:
  <name|id>             Project name or ID

Options:
  --team <key>          Default team
  --state <name|id>     Default state for new issues
  --assignee <email|id> Default assignee for new issues
  --label <name>        Default labels (can be used multiple times)
  --profile <name>      Profile to use for this project
```

**Examples:**
```bash
# Basic alignment
ltui projects align "Mobile App" --team ENG

# With defaults
ltui projects align "Mobile App" \
  --team ENG \
  --state "In Progress" \
  --assignee me \
  --label backend

# Creates .ltui.json in current directory
```

## Teams Commands

### `ltui teams list`

List all teams.

**Options:**
```bash
ltui teams list [options]

Options:
  (none; use global options before the command path)
```

**Examples:**
```bash
ltui teams list
ltui --format table teams list
```

### `ltui teams view`

View team details.

**Options:**
```bash
ltui teams view <key|id> [options]

Arguments:
  <key|id>            Team key (e.g., ENG) or ID

Options:
  (none; use global options before the command path)
```

**Examples:**
```bash
ltui teams view ENG
ltui --format detail teams view ENG
```

## Labels Commands

### `ltui labels list`

List all labels.

**Options:**
```bash
ltui labels list [options]

Options:
  --team <key>         Filter by team
```

**Examples:**
```bash
# All labels
ltui labels list

# Team-specific labels
ltui labels list --team ENG

# Human-readable
ltui --format table labels list
```

### `ltui labels create`

Create a new label.

**Options:**
```bash
ltui labels create [options]

Required:
  --name <text>        Label name

Optional:
  --color <hex>        Hex color code (e.g., #FF5733)
  --description <text> Label description
  --team <key>         Team to create label for
```

**Examples:**
```bash
# Basic label
ltui labels create --name "needs-review"

# With color
ltui labels create --name "needs-review" --color "#FF5733"

# Team-specific label
ltui labels create --name "backend" --color "#0066CC" --team ENG

# With description
ltui labels create --name "critical" --color "#FF0000" --description "Critical priority issues"
```

## Users Commands

### `ltui users list`

List users in the workspace.

**Options:**
```bash
ltui users list [options]

Options:
  --search <text>      Search users by name or email
```

**Examples:**
```bash
# All users
ltui users list

# Search users
ltui users list --search alice

# Human-readable
ltui --format table users list
```

## Cycles Commands

### `ltui cycles list`

List cycles for a team.

**Options:**
```bash
ltui cycles list [options]

Required:
  --team <key>         Team key (e.g., ENG)

Optional:
  --current            Only show current cycle
```

**Examples:**
```bash
# All cycles for team
ltui cycles list --team ENG

# Current cycle only
ltui cycles list --team ENG --current

# Human-readable
ltui --format table cycles list --team ENG
```

## Documents Commands

### `ltui documents list`

List documents.

**Options:**
```bash
ltui documents list [options]

Options:
  (none; use global options before the command path)
```

### `ltui documents view`

View document details.

**Options:**
```bash
ltui documents view <id> [options]

Arguments:
  <id>                Document ID

Options:
  (none; use global options before the command path)
```

## Roadmaps Commands

### `ltui roadmaps list`

List roadmaps.

**Options:**
```bash
ltui roadmaps list [options]

Options:
  (none; use global options before the command path)
```

### `ltui roadmaps view`

View roadmap details.

**Options:**
```bash
ltui roadmaps view <id> [options]

Arguments:
  <id>                Roadmap ID

Options:
  (none; use global options before the command path)
```

## Milestones Commands

### `ltui milestones list`

List milestones.

**Options:**
```bash
ltui milestones list [options]

Options:
  (none; use global options before the command path)
```

### `ltui milestones view`

View milestone details.

**Options:**
```bash
ltui milestones view <id> [options]

Arguments:
  <id>                Milestone ID

Options:
  (none; use global options before the command path)
```

## Notifications Commands

### `ltui notifications`

List notifications.

**Options:**
```bash
ltui notifications [options]

Options:
  --unread-only        Only show unread notifications
```

## Auth Commands

### `ltui auth list`

List configured authentication profiles.

**Options:**
```bash
ltui auth list
```

**Example output:**
```
PROFILES:
default (active)
work
```

### `ltui auth add`

Add a new authentication profile.

**Options:**
```bash
ltui auth add [options]

Required:
  --name <name>        Profile name
  --key <api-key>      Linear API key

Optional:
  --set-default        Make this the default profile
```

**Examples:**
```bash
# Add profile
ltui auth add --name default --key lin_api_...

# Add and set as default
ltui auth add --name work --key lin_api_... --set-default
```

### `ltui auth remove`

Remove an authentication profile.

**Options:**
```bash
ltui auth remove <name>

Arguments:
  <name>              Profile name to remove
```

**Examples:**
```bash
ltui auth remove work
```

### `ltui auth use`

Set the default profile.

**Options:**
```bash
ltui auth use <name>

Arguments:
  <name>              Profile name to set as default
```

**Examples:**
```bash
ltui auth use work
```

## Global Flags

All commands support these global flags:

- `--profile <name>` - Use a specific profile instead of default
- `--format <fmt>` - Output format: `tsv`, `table`, `detail`, `json`
- `--help` - Show help for the command

## Output Parsing Details

### TSV Format
```
key	identifier	title	state
ENG-42	ENG-42	Fix bug	In Progress
```
- First line: header row with tab-separated field names
- Subsequent lines: data rows with tab-separated values
- Parse by splitting each line on `\t`

### Detail Format
```
ISSUE: ENG-42
id: abc123-def-456
key: ENG-42
title: Fix login bug
state: In Progress
DESCRIPTION_START
Users cannot login with email addresses
containing special characters.
DESCRIPTION_END
COMMENTS_START
COMMENT_1
id: comment-123
user: alice@example.com
body: I've identified the issue in the validation regex
createdAt: 2025-11-15T10:30:00Z
COMMENT_2
id: comment-124
user: bob@example.com
body: Thanks! I'll test the fix
createdAt: 2025-11-15T11:15:00Z
COMMENTS_END
```
- Look for explicit block markers: `DESCRIPTION_START/END`, `COMMENTS_START/END`
- Fields are `key: value` pairs
- Comments have `COMMENT_N` markers

### JSON Format
```json
{"meta":{"cursorNext":"","cursorPrev":"","count":1},"rows":[{"id":"abc123","key":"ENG","identifier":"ENG-42"}]}
```
- JSON is emitted as a single envelope object for list commands: `{ meta, rows }`
- Standard JSON parsing

## Configuration File Formats

### `~/.config/ltui/config.json`
```json
{
  "profiles": {
    "default": {"apiKey": "lin_api_..."},
    "work": {"apiKey": "lin_api_..."}
  },
  "defaultProfile": "default"
}
```

### `.ltui.json` (per-directory)
```json
{
  "profile": "default",
  "team": "ENG",
  "project": "Mobile App",
  "defaults": {
    "state": "Todo",
    "assignee": "me",
    "labels": ["backend"]
  }
}
```
