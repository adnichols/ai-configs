---
name: linear
description: "Linear: manage issues, projects, teams via GraphQL + curl."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
prerequisites:
  env_vars: [LINEAR_API_KEY]
  commands: [curl]
metadata:
  hermes:
    tags: [Linear, Project Management, Issues, GraphQL, API, Productivity]
---

# Linear — Issue & Project Management

Manage Linear issues, projects, and teams directly via the GraphQL API using `curl`. No MCP server, no OAuth flow, no extra dependencies.

## Setup

1. Get a personal API key from **Linear Settings > Account > Security & access > Personal API keys** (URL: https://linear.app/settings/account/security). Note: the org-level *Settings > API* page only shows OAuth apps and workspace-member keys, not personal keys.
2. Set `LINEAR_API_KEY` in your environment (via `hermes setup` or your env config)

## API Basics

- **Endpoint:** `https://api.linear.app/graphql` (POST)
- **Auth header:** `Authorization: $LINEAR_API_KEY` (no "Bearer" prefix for API keys)
- **All requests are POST** with `Content-Type: application/json`
- **Both UUIDs and short identifiers** (e.g., `ENG-123`) work for `issue(id:)`

Base curl pattern:
```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ viewer { id name } }"}' | python3 -m json.tool
```

## Python helper script (ergonomic alternative)

For faster one-liners that don't need hand-written GraphQL, this skill ships a stdlib Python CLI at `scripts/linear_api.py`. Zero dependencies. Same auth (reads `LINEAR_API_KEY`).

```bash
SCRIPT=$(dirname "$(find ~/.hermes -path '*skills/productivity/linear/scripts/linear_api.py' 2>/dev/null | head -1)")/linear_api.py

python3 "$SCRIPT" whoami
python3 "$SCRIPT" list-teams
python3 "$SCRIPT" get-issue ENG-42
python3 "$SCRIPT" get-document 38359beef67c      # fetch a doc by slugId from the URL
python3 "$SCRIPT" raw 'query { viewer { name } }'
```

All subcommands: `whoami`, `list-teams`, `list-projects`, `list-states`, `list-issues`, `get-issue`, `search-issues`, `create-issue`, `update-issue`, `update-status`, `add-comment`, `list-documents`, `get-document`, `search-documents`, `raw`. Run with `--help` for flags.

Use the script when: you want a quick answer without crafting GraphQL. Use curl when: you need a query the script doesn't wrap, or you want to compose filters inline.

## Repo-local `ltui` fallback / preferred path in code repos

When working inside Aaron's code repos, first check for repo-local Linear configuration such as `.ltui.json` and the `ltui` CLI before falling back to raw GraphQL. This is especially useful when `LINEAR_API_KEY` is not exported in the Hermes process but the local `ltui` profile is already authenticated.

Typical pattern from a repo root:
```bash
# Inspect repo defaults; Heddle/ccore normally has team/project defaults here.
python3 -m json.tool .ltui.json

# Discover the supported surface.
ltui --help
ltui issues create --help

# Create a well-scoped issue using the repo defaults or explicit project id.
ltui issues create \
  --team NOD \
  --project <project-id-from-.ltui.json> \
  --title "<concise outcome>" \
  --description @/tmp/issue-description.md \
  --priority 2 \
  --state Backlog
```

For evidence-heavy issues, write the description to `/tmp/<slug>.md` first, then pass `--description @/tmp/<slug>.md`. Include observed code paths, local data evidence, impact, and acceptance criteria. Do not propose a full solution if the user asked only to collect evidence and open a tracking issue.

### `ltui` command-shape gotchas

- Global flags such as `--format json` and `--limit N` belong **before** the subcommand: `ltui --format json --limit 20 issues list ...`, not `ltui issues list --limit 20`.
- Some `ltui issues view` output can omit labels even when the issue has them. Verify label mutations with `ltui --format json issues list --search '<title>' --team <key>` or the mutation response, not only `issues view`.
- When Aaron asks to “just open the Linear” and explicitly says not to build, create the issue only, set the requested workflow state/labels, verify the row, and stop. For Doct autobuild intake this commonly means project `Doc Thingy`, state `Ready to Pull`, and label `autobuild`.
- `ltui issues update <KEY> --state Done` generally does not need `--project`; prefer the narrow issue-key update and add only `--team <KEY>` if required. Passing `--project` or running from a repo with `.ltui.json` can trigger an extra broad project lookup, which is painful when the Linear API is near rate limit.

### Reviewing In Review issues for completion

When Aaron asks to review Linear issues in a repo/project and move completed work to Done:

1. Use the repo-local project defaults first (`.ltui.json`) and list the target state with JSON output, e.g. `ltui --format json --limit 100 issues list --team NOD --project <project-id> --state 'In Review'`.
2. For each candidate, gather evidence from Linear issue attachments (`ltui --format json issues attachments NOD-123`) and GitHub PR search/view. Attachments often contain the exact PR URL; `gh pr view <num> --json state,mergedAt,title,body,statusCheckRollup` gives authoritative merge state.
3. Move to `Done` only when there is direct completion evidence: linked/mentioned PR is `MERGED`, merged body explicitly covers the issue identifier or acceptance scope, and no issue description says the work was only a partial/deferred slice.
4. Do **not** close items merely because a related PR or nearby epic is merged. Leave ambiguous issues in review/backlog and report why (e.g. no direct PR attachment, only indirect docs, or related PR was still open).
5. After mutations, re-list the source state and the Done state to verify the final rows. Treat mutation output as provisional until a fresh list/view confirms the state.

Reference example: `references/ccore-identity-fragmentation-issue.md` captures a C-Core/Heddle account identity fragmentation investigation and the evidence shape used for NOD-1084.

## Workflow States

Linear uses `WorkflowState` objects with a `type` field. **6 state types:**

| Type | Description |
|------|-------------|
| `triage` | Incoming issues needing review |
| `backlog` | Acknowledged but not yet planned |
| `unstarted` | Planned/ready but not started |
| `started` | Actively being worked on |
| `completed` | Done |
| `canceled` | Won't do |

Each team has its own named states (e.g., "In Progress" is type `started`). To change an issue's status, you need the `stateId` (UUID) of the target state — query workflow states first.

**Priority values:** 0 = None, 1 = Urgent, 2 = High, 3 = Medium, 4 = Low

## Common Queries

### Get current user
```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ viewer { id name email } }"}' | python3 -m json.tool
```

### List teams
```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ teams { nodes { id name key } } }"}' | python3 -m json.tool
```

### List workflow states for a team
```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ workflowStates(filter: { team: { key: { eq: \"ENG\" } } }) { nodes { id name type } } }"}' | python3 -m json.tool
```

### List issues (first 20)
```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ issues(first: 20) { nodes { identifier title priority state { name type } assignee { name } team { key } url } pageInfo { hasNextPage endCursor } } }"}' | python3 -m json.tool
```

### List my assigned issues
```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ viewer { assignedIssues(first: 25) { nodes { identifier title state { name type } priority url } } } }"}' | python3 -m json.tool
```

### Get a single issue (by identifier like ENG-123)
```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ issue(id: \"ENG-123\") { id identifier title description priority state { id name type } assignee { id name } team { key } project { name } labels { nodes { name } } comments { nodes { body user { name } createdAt } } url } }"}' | python3 -m json.tool
```

### Search issues by text
```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ issueSearch(query: \"bug login\", first: 10) { nodes { identifier title state { name } assignee { name } url } } }"}' | python3 -m json.tool
```

### Filter issues by state type
```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ issues(filter: { state: { type: { in: [\"started\"] } } }, first: 20) { nodes { identifier title state { name } assignee { name } } } }"}' | python3 -m json.tool
```

### Filter by team and assignee
```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ issues(filter: { team: { key: { eq: \"ENG\" } }, assignee: { email: { eq: \"user@example.com\" } } }, first: 20) { nodes { identifier title state { name } priority } } }"}' | python3 -m json.tool
```

### List projects
```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ projects(first: 20) { nodes { id name description progress lead { name } teams { nodes { key } } url } } }"}' | python3 -m json.tool
```

### List team members
```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ users { nodes { id name email active } } }"}' | python3 -m json.tool
```

### List labels
```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ issueLabels { nodes { id name color } } }"}' | python3 -m json.tool
```

## Common Mutations

### Create an issue
```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation($input: IssueCreateInput!) { issueCreate(input: $input) { success issue { id identifier title url } } }",
    "variables": {
      "input": {
        "teamId": "TEAM_UUID",
        "title": "Fix login bug",
        "description": "Users cannot login with SSO",
        "priority": 2
      }
    }
  }' | python3 -m json.tool
```

### Update issue status
First get the target state UUID from the workflow states query above, then:
```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "mutation { issueUpdate(id: \"ENG-123\", input: { stateId: \"STATE_UUID\" }) { success issue { identifier state { name type } } } }"}' | python3 -m json.tool
```

### Assign an issue
```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "mutation { issueUpdate(id: \"ENG-123\", input: { assigneeId: \"USER_UUID\" }) { success issue { identifier assignee { name } } } }"}' | python3 -m json.tool
```

### Set priority
```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "mutation { issueUpdate(id: \"ENG-123\", input: { priority: 1 }) { success issue { identifier priority } } }"}' | python3 -m json.tool
```

### Add a comment
```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "mutation { commentCreate(input: { issueId: \"ISSUE_UUID\", body: \"Investigated. Root cause is X.\" }) { success comment { id body } } }"}' | python3 -m json.tool
```

### Set due date
```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "mutation { issueUpdate(id: \"ENG-123\", input: { dueDate: \"2026-04-01\" }) { success issue { identifier dueDate } } }"}' | python3 -m json.tool
```

### Add labels to an issue
```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "mutation { issueUpdate(id: \"ENG-123\", input: { labelIds: [\"LABEL_UUID_1\", \"LABEL_UUID_2\"] }) { success issue { identifier labels { nodes { name } } } } }"}' | python3 -m json.tool
```

### Add issue to a project
```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "mutation { issueUpdate(id: \"ENG-123\", input: { projectId: \"PROJECT_UUID\" }) { success issue { identifier project { name } } } }"}' | python3 -m json.tool
```

### Create a project
```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation($input: ProjectCreateInput!) { projectCreate(input: $input) { success project { id name url } } }",
    "variables": {
      "input": {
        "name": "Q2 Auth Overhaul",
        "description": "Replace legacy auth with OAuth2 and PKCE",
        "teamIds": ["TEAM_UUID"]
      }
    }
  }' | python3 -m json.tool
```

## Documents

Linear **Documents** are prose docs (RFCs, specs, notes) stored alongside issues. They have their own `documents` root query and `document(id:)` single-fetch.

### Document URLs and `slugId`

Document URLs look like:
```
https://linear.app/<workspace>/document/<slug>-<hexSlugId>
```

The trailing hex segment is the `slugId`. Example: `https://linear.app/nousresearch/document/rfc-hermes-permission-gateway-discord-38359beef67c` → `slugId` is `38359beef67c`.

**Important schema detail:** the Markdown body is in the `content` field. The ProseMirror JSON is in `contentState` (not `contentData` — that field does not exist and the API returns 400).

### Fetch a document by slugId

`document(id:)` only accepts UUIDs. To fetch by the URL's hex slug, filter the collection:

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "query($s: String!) { documents(filter: { slugId: { eq: $s } }, first: 1) { nodes { id title content contentState slugId url creator { name } project { name } updatedAt } } }", "variables": {"s": "38359beef67c"}}' \
  | python3 -m json.tool
```

Or via the Python helper:
```bash
python3 scripts/linear_api.py get-document 38359beef67c
```

### Fetch a document by UUID

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ document(id: \"11700cff-b514-4db3-afcc-3ed1afacba1c\") { title content url } }"}' \
  | python3 -m json.tool
```

### List recent documents

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ documents(first: 25, orderBy: updatedAt) { nodes { id title slugId url updatedAt project { name } } } }"}' \
  | python3 -m json.tool
```

### Search documents by title

Linear's schema has no `searchDocuments` root. Use a title-substring filter instead:

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ documents(filter: { title: { containsIgnoreCase: \"RFC\" } }, first: 25) { nodes { title slugId url } } }"}' \
  | python3 -m json.tool
```

## Pagination

Linear uses Relay-style cursor pagination:

```bash
# First page
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ issues(first: 20) { nodes { identifier title } pageInfo { hasNextPage endCursor } } }"}' | python3 -m json.tool

# Next page — use endCursor from previous response
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ issues(first: 20, after: \"CURSOR_FROM_PREVIOUS\") { nodes { identifier title } pageInfo { hasNextPage endCursor } } }"}' | python3 -m json.tool
```

Default page size: 50. Max: 250. Always use `first: N` to limit results.

## Filtering Reference

Comparators: `eq`, `neq`, `in`, `nin`, `lt`, `lte`, `gt`, `gte`, `contains`, `startsWith`, `containsIgnoreCase`

Combine filters with `or: [...]` for OR logic (default is AND within a filter object).

## Typical Workflow

1. **Query teams** to get team IDs and keys
2. **Query workflow states** for target team to get state UUIDs
3. **List or search issues** to find what needs work
4. **Create issues** with team ID, title, description, priority
5. **Update status** by setting `stateId` to the target workflow state
6. **Add comments** to track progress
7. **Mark complete** by setting `stateId` to the team's "completed" type state

## Rate Limits

- 5,000 requests/hour per API key
- 3,000,000 complexity points/hour
- Use `first: N` to limit results and reduce complexity cost
- Monitor `X-RateLimit-Requests-Remaining` response header

## Important Notes

- Always use `terminal` tool with `curl` for API calls — do NOT use `web_extract` or `browser`
- Always check the `errors` array in GraphQL responses — HTTP 200 can still contain errors
- If `stateId` is omitted when creating issues, Linear defaults to the first backlog state
- The `description` field supports Markdown
- Use `python3 -m json.tool` or `jq` to format JSON responses for readability
