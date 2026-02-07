---
description: "Fetch and convert documentation for libraries, frameworks, and languages into AI-friendly Markdown format"
argument-hint: "[library_name] [--version VERSION] [--topic TOPIC] [--url URL]"
---

# Documentation Fetch Command

Fetch documentation for programming libraries, frameworks, languages, and toolsets. This command uses **Context7 MCP** as the primary source for up-to-date, version-specific documentation, with fallback to direct URL fetching. Think harder.

## Input

Library name and options: $ARGUMENTS

The user will provide:

## Usage

```bash
/doc:fetch react                    # Fetch React documentation via Context7
/doc:fetch typescript --topic generics  # Specific topic
/doc:fetch prisma --version 5       # Specific version
/doc:fetch mylibrary --url https://docs.mylibrary.com/  # Manual URL fallback
```

## Arguments

- **library_name** (required): Name of library/framework to fetch documentation for
- **--version** (optional): Specific version to fetch (passed to Context7)
- **--topic** (optional): Specific topic to focus on (e.g., "hooks", "routing", "api")
- **--url** (optional): Manual URL for fallback when Context7 doesn't have the library

## Process

### Step 1: Parse Arguments

Extract from $ARGUMENTS:
- Library name (required)
- Version (optional)
- Topic (optional)
- Manual URL (optional)

### Step 2: Try Context7 MCP (Primary Method)

Context7 provides up-to-date documentation directly in the prompt context. Use the MCP tools:

1. **Resolve the library ID:**
   ```
   Use mcp__context7__resolve-library-id with the library name
   ```

2. **Fetch documentation:**
   ```
   Use mcp__context7__get-library-docs with:
   - context7CompatibleLibraryID: The resolved ID
   - topic: The specific topic if provided
   - page: Start with 1, paginate if needed
   ```

3. **Process and save:**
   - Save the fetched documentation to `docs/libraries/[library-name]/`
   - Create an index file with metadata
   - Update CLAUDE.md to reference the new documentation

### Step 3: Fallback to URL Fetching

If Context7 doesn't have the library (resolve fails), fall back to URL-based fetching:

1. **If --url provided:** Use the specified URL
2. **Otherwise:** Attempt common documentation URL patterns

Run the fallback script:
```bash
python .claude/scripts/docs-fetch.py [library_name] [options]
```

### Step 4: Update References

After successful fetch, update CLAUDE.md's "Available Documentation" section to include:
```markdown
- **[Library Name]** (library): `docs/libraries/[library-name]/` - [completeness]% complete - *Updated [date]*
```

## Context7 Integration

**REQUIREMENT**: The Context7 MCP server must be configured in your OPENCODE environment to use this method. If not available, the command will automatically fall back to URL-based fetching.

Context7 MCP provides:

- **Real-time documentation**: Fetches current docs, not stale training data
- **Version-specific**: Can target specific library versions
- **Topic filtering**: Focus on specific areas (hooks, routing, API, etc.)
- **Pagination**: Access up to 100 snippets per topic

### Supported Libraries

Context7 supports most popular libraries. To check if a library is available:

```
1. Try resolve-library-id with the library name
2. If it returns a valid ID, the library is supported
3. If not, use the --url fallback method
```

### Installation

To enable Context7 MCP, install and configure it in your OPENCODE environment:

```bash
npx @upstash/context7-mcp
```

### Example Context7 Workflow

```
User: /doc:fetch react --topic hooks

1. resolve-library-id("react") -> "react/react.dev"
2. get-library-docs("react/react.dev", topic="hooks", page=1)
3. Save response to docs/libraries/react/hooks.md
4. Update CLAUDE.md
```

## Output Structure

Documentation is saved to:

```
docs/
  libraries/
    [library-name]/
      index.md           # Overview and metadata
      api-reference.md   # API documentation (if available)
      [topic].md         # Topic-specific docs
      examples/          # Code examples
```

## When to Use This Command

- **Spec creation**: Use via `/dev:1:create-spec` documentation discovery
- **Manual fetch**: When you need documentation for a specific library
- **Updates**: Refresh documentation for libraries already in `docs/`
- **Unknown libraries**: Fetch docs for libraries not in Claude's training data

## Troubleshooting

### Context7 Not Available

If Context7 MCP tools are not responding:
1. Check that the MCP server is configured in your Claude Code settings
2. Verify Node.js 18+ is installed
3. Try: `npx @upstash/context7-mcp` to test the server

### Library Not Found

If a library isn't in Context7:
1. Use `--url` with the official documentation URL
2. Check for alternate package names (e.g., "react-dom" vs "react")
3. Some niche libraries may only have GitHub README documentation

### Fetch Failures

If fetching fails:
1. Check network connectivity
2. Verify the documentation URL is accessible
3. Some sites block automated fetching - try a different source URL

## Related Commands

- `/doc:fetch-batch`: Batch fetch documentation from markdown lists
- `/dev:1:create-spec`: Uses documentation discovery during spec creation
