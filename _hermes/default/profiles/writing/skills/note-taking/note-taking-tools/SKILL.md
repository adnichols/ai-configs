---
name: note-taking-tools
description: "Manage notes in Notion and Obsidian: create, read, search, edit pages, databases, and markdown vaults."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [notes, notion, obsidian, markdown, knowledge-base]
    related_skills: [llm-wiki]
---

# Note Taking Tools

## Notion

Create, read, update pages and databases via the Notion API or `ntn` CLI.

### Setup
1. Create integration at https://www.notion.so/my-integrations
2. Copy the Internal Integration Token
3. Share databases/pages with the integration

### Pages
```bash
# Create page
ntn page create --parent-id <PAGE_ID> --title "Meeting Notes" --content "# Notes\n..."

# Read page
ntn page get <PAGE_ID>

# Update page
ntn page update <PAGE_ID> --content "# Updated Notes\n..."
```

### Databases
```bash
# Query database
ntn db query <DB_ID> --filter '{"property":"Status","select":{"equals":"Done"}}'

# Add entry
ntn db create <DB_ID> --properties '{"Name":{"title":[{"text":{"content":"New Task"}}]},"Status":{"select":{"name":"To Do"}}}'
```

### Markdown
```bash
ntn page create --from-file notes.md --parent-id <PAGE_ID>
```

### Workers (Serverless Functions)
```bash
ntn worker deploy --file worker.ts --name my-worker
```

### Pitfalls
- Page IDs are 32-char UUIDs, not URLs
- Database filters use JSON; quote carefully in shell
- `ntn` CLI requires Node.js 18+

## Obsidian

Read, search, create, and edit notes in an Obsidian vault.

### Vault Structure
```
vault/
├── Inbox/
├── Projects/
├── Concepts/
└── Daily/
```

### Create Note
```bash
# Write markdown file directly
cat > vault/Projects/new-feature.md << 'EOF'
# New Feature

## Goal
...

## Tasks
- [ ] ...
EOF
```

### Search
```bash
# Full-text search via ripgrep
rg "TODO" vault/ --type md

# Link search
rg "\[\[New Feature\]\]" vault/ --type md
```

### Backlinks
Obsidian auto-generates backlinks from `[[WikiLink]]` syntax. To find all notes linking to a topic:
```bash
rg "\[\[Topic Name\]\]" vault/ --type md
```

### Daily Notes
```bash
TODAY=$(date +%Y-%m-%d)
cat > vault/Daily/$TODAY.md << 'EOF'
# $TODAY

## Log
- ...

## Tasks
- [ ] ...
EOF
```

### Sync
- Obsidian Sync (official, encrypted)
- Git + Obsidian Git plugin (free, version controlled)
- iCloud/Dropbox (simple, no version history)

### Use Cases
- Personal knowledge base
- Project documentation
- Research notes (pair with `arxiv` and `blogwatcher`)
- Meeting notes (pair with `teams-meeting-pipeline`)

## Cross-Tool Workflow

1. **Capture:** Quick note in Obsidian Inbox or Notion
2. **Process:** Categorize, tag, and link related notes
3. **Synthesize:** Create evergreen pages from transient notes
4. **Share:** Publish from Obsidian (via plugin) or Notion (native sharing)
