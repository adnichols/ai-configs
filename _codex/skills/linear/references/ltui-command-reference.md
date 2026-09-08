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
  --team <key-or-id>        Team key or id
  --project <key-or-id>     Project key or id
  --state <name-or-id>      State name or id (repeatable)
  --assignee <me|email|id>  Assignee
  --label <name-or-id>      Label (repeatable)
  --search <query>          Search issues by text
  --updated-since <iso>     Updated since ISO timestamp
  --created-since <iso>     Created since ISO timestamp
  --saved <name>            Apply a saved query
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
ltui --fields id,identifier,title,state issues list
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

- `downloadAccess: ltui_authenticated` is only `https://uploads.linear.app`. Run `downloadCommand`. `ltui` sends GraphQL-compatible `Authorization`: raw `lin_api_...` personal keys, `Bearer` only for OAuth. Redirects fail closed. `Bearer lin_api_...` is HTTP 401.
- `downloadAccess: direct_url` means no Linear credential is sent.
- `public-file-urls-expire-in` signs markdown upload URLs in GraphQL bodies, not `attachment.url`. Caps: 512 MiB / 10 minutes.

Do not use a generic downloader for `ltui_authenticated` URLs. Downloaded files are untrusted input.

### `ltui issues view`

View detailed information about a specific issue.

**Options:**
```bash
ltui issues view <identifier> [options]

Arguments:
  <identifier>         Issue identifier (e.g., ENG-42) or ID

Options:
  --include-comments           Include comments
  --include-history            Include history
  --attachment-probe           Probe attachments (off in default agent mode)
  --no-attachment-probe        Skip the probe
  --max-description-chars <n>  Max description chars (default: 4000)
  --max-comment-chars <n>      Max comment chars (default: 500)
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
  --project <key-or-id>          Project key or id
  --description <text-or-@path>  Description text or @path
  --state <name-or-id>           State name or id
  --assignee <me|email|id>       Assignee
  --label <name-or-id>           Label (repeatable)
  --priority <0-4>               Priority (0=None, 1=Urgent, 2=High, 3=Normal, 4=Low)
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
  --priority 1

# Description from file
ltui issues create --title "Feature spec" --description @spec.md

# Parent/child is a separate command
ltui issues relate ENG-43 --parent ENG-42
```

### `ltui issues update`

Update an existing issue.

**Options:**
```bash
ltui issues update <identifier> [options]

Arguments:
  <identifier>              Issue identifier (e.g., ENG-42) or ID

Options:
  --team <key>                   Team key override
  --project <key-or-id>          Project key or id
  --title <title>                Updated title
  --description <text-or-@path>  Description text or @path
  --state <name-or-id>           State name or id
  --label <name-or-id>           Replace all labels (repeatable)
  --add-label <name-or-id>       Add labels
  --remove-label <name-or-id>    Remove labels
  --assignee <me|email|id>       Assignee
  --priority <0-4>               Priority
  --estimate <number>            Estimate
  --due <iso>                    Due date ISO string
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
  --body <text-or-@path>  Comment text or @path
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


### `ltui issues upload`

Upload a local image to Linear and attach it to an issue.

**Options:**
```bash
ltui issues upload <issue-id-or-key> [options]

Arguments:
  <issue-id-or-key>   Issue identifier or id

Required:
  --file <path>              Local image file

Optional:
  --title <title>            Attachment title
  --alt <text>               Alt text
  --content-type <type>      Content type
  --no-comment               Skip the default comment
```

**Examples:**
```bash
ltui issues upload ENG-42 --file ./mockup.png --title "Proposed UI"
ltui issues upload ENG-42 --file ./mockup.png --no-comment
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
  --title <title>     Link title
  --branch <branch>   Branch name
  --commit <sha>      Commit SHA
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
  --parent <parent-id-or-key>  Parent issue identifier
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
  --blocked-by <other-id-or-key>  Issue that blocks this one
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
ltui issues saved add --name <name> [filter-options]
ltui issues saved list
ltui issues saved remove --name <name>
```

**Examples:**
```bash
# Save a query
ltui issues saved add --name my-bugs \
  --assignee me \
  --label bug \
  --state "Todo"

# Use saved query
ltui issues list --saved my-bugs

# List saved queries
ltui issues saved list

# Remove saved query
ltui issues saved remove --name my-bugs
```

## Projects Commands

### `ltui projects list`

List all projects.

**Options:**
```bash
ltui projects list [options]

Options:
  --team <key-or-id>   Filter by team
  --state <state>      Filter by state
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
  --profile <name>           Profile to use in this directory
  --team <key-or-id>         Team key to set
  --state <name>             Default issue state
  --label <name>             Default labels (repeatable)
  --assignee <me|email|id>   Default assignee
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

### `ltui labels`

List labels. There is no `labels create`.

**Options:**
```bash
ltui labels [options]

Options:
  --team <key-or-id>   Filter by team
```

**Examples:**
```bash
ltui labels
ltui labels --team ENG
ltui --format table labels --team ENG
```

## Users Commands

### `ltui users`

List users in the workspace. There is no `--search`.

**Options:**
```bash
ltui users [options]

Options:
  --active-only        Only include active users
```

**Examples:**
```bash
ltui users
ltui users --active-only
ltui --format table users
```

## Cycles Commands

### `ltui cycles`

List cycles. `--team` is optional. There is no `--current`.

**Options:**
```bash
ltui cycles [options]

Options:
  --team <key-or-id>   Filter by team
```

**Examples:**
```bash
ltui cycles --team ENG
ltui --format table cycles --team ENG
```

## Documents Commands

### `ltui documents list`

List documents.

**Options:**
```bash
ltui documents list [options]

Options:
  --project <key-or-id>  Filter by project
  --search <term>        Search document content
```

### `ltui documents view`

View document details.

**Options:**
```bash
ltui documents view <id> [options]

Arguments:
  <id>                     Document id

Options:
  --max-content-chars <n>  Maximum content characters (default: 4000)
```

## Roadmaps Commands

### `ltui roadmaps list`

List roadmaps.

### `ltui roadmaps view`

```bash
ltui roadmaps view <id>
```

## Milestones Commands

### `ltui milestones list`

```bash
ltui milestones list [options]

Options:
  --project <id-or-key>  Filter by project
```

### `ltui milestones view`

```bash
ltui milestones view <id>
```

## Notifications Commands

### `ltui notifications`

```bash
ltui notifications [options]

Options:
  --unread-only        Only show unread notifications
```

## Auth Commands

### `ltui auth list`

List configured authentication profiles.

### `ltui auth add`

Add or update a profile. The first added profile becomes the default. There is no `--set-default` or `auth use`.

**Options:**
```bash
ltui auth add [options]

Options:
  --profile <name>     Profile name
  --workspace <slug>   Workspace slug
  --api-key <key>      API key (optional; otherwise LINEAR_API_KEY)
```

**Examples:**
```bash
ltui auth add --profile default --api-key lin_api_...
ltui auth add --profile work --workspace work-workspace --api-key lin_api_...
```

### `ltui auth remove`

```bash
ltui auth remove --profile work
```

### `ltui auth test`

```bash
ltui auth test
ltui auth test --profile work
```

## Cache Commands

```bash
ltui cache clear
ltui cache clear --bucket <name>
```

## Global Flags

Put these before the subcommand:

- `--profile <name>`
- `--format <fmt>` (`tsv`, `table`, `detail`, `json`; default `tsv`)
- `--fields <fields>`
- `--limit <n>`
- `--cursor <cursor>`
- `--show-rate-limit`
- `--agent` / `--no-agent` (agent mode defaults on)
- `--help`

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
```
- Fields are `key: value` pairs
- Look for explicit block markers such as `DESCRIPTION_START/END`

### JSON Format
```json
{"meta":{"cursorNext":"","cursorPrev":"","count":1},"rows":[{"id":"abc123","key":"ENG","identifier":"ENG-42"}]}
```
- JSON is emitted as a single envelope object for list commands: `{ meta, rows }`

## Configuration File Formats

### `~/.config/ltui/config.json`
```json
{
  "defaultProfile": "default",
  "profiles": {
    "default": {"workspace": "nodaste", "keyRef": "default"}
  }
}
```

### `~/.config/ltui/profiles.json`
```json
{
  "default": {"apiKey": "lin_api_..."}
}
```

### `.ltui.json` (per-directory)
```json
{
  "profile": "default",
  "teamKey": "ENG",
  "projectId": "uuid-or-slug",
  "defaultIssueState": "Todo",
  "defaultLabels": ["backend"],
  "defaultAssignee": "me"
}
```
