---
description: "Batch fetch documentation from markdown lists containing multiple libraries and frameworks"
argument-hint: "[markdown_content] [--dry-run] [--parallel] [--skip-existing] [--update] [--format FORMAT]"
---

# Batch Documentation Fetch Command

Process markdown lists containing multiple libraries/frameworks to fetch documentation for each item. This command parses bullet point lists with `[Library Name](URL)` format, intelligently maps display names to fetchable identifiers, and calls the existing docs:fetch command for each library. Think harder.

## Usage

```bash
/docs:fetch-batch "### Boilerplate
* [Next.js 15](https://nextjs.org/) - React framework
* [Tailwind CSS v4](https://tailwindcss.com/) - Utility CSS
* [TypeScript](https://typescriptlang.org/) - Type safety"

/docs:fetch-batch --file README.md --section "### Dependencies"  # From file section
/docs:fetch-batch "..." --dry-run                               # Preview without fetching
/docs:fetch-batch "..." --parallel                             # Parallel processing
/docs:fetch-batch "..." --skip-existing                        # Skip already fetched
/docs:fetch-batch "..." --update                               # Update all existing docs
```

## Arguments

- **markdown_content** (required): Markdown content containing bullet point lists with libraries
- **--file** (optional): Read from file instead of inline content
- **--section** (optional): Extract specific section from file (requires --file)
- **--dry-run** (optional): Show what would be fetched without actually fetching
- **--parallel** (optional): Process libraries in parallel (faster but more resource intensive)
- **--skip-existing** (optional): Skip libraries that already have documentation
- **--update** (optional): Update existing documentation for all libraries
- **--format** (optional): Output format passed to individual docs:fetch calls (full, minimal, api-only)

## Parsing Intelligence

The command intelligently handles various markdown patterns:
- `[Next.js 15](https://nextjs.org/)` → `nextjs --version 15`
- `[Tailwind CSS v4](https://tailwindcss.com/)` → `tailwindcss --version 4`
- `[React Testing Library](https://testing-library.com/react)` → `react-testing-library`
- `[TypeScript](https://typescriptlang.org/)` → `typescript`
- Uses URLs for `--url` parameter when auto-discovery fails
- Skips non-library items (Perfect Lighthouse score, etc.)

## Input

Markdown content and options: $ARGUMENTS

The user will provide:

## Implementation

I'll help you batch process documentation fetching from your markdown content. Let me parse the libraries and process each one:

1. **Parse Markdown**: Extract `[Name](URL)` patterns from bullet points
2. **Map Library Names**: Convert display names to fetchable identifiers with versions
3. **Filter Libraries**: Skip non-library entries and handle edge cases
4. **Batch Process**: Call docs:fetch for each library with appropriate parameters
5. **Progress Tracking**: Report progress and collect any errors
6. **Update Documentation**: Batch update CLAUDE.md with all fetched references

Let me start by parsing your markdown content and executing the batch documentation fetch process.

<function_calls>
<invoke name="Bash">
<parameter name="command">python .claude/scripts/docs-fetch-batch.py $ARGUMENTS</parameter>
<parameter name="description">Execute batch documentation fetch script with user arguments

Now let me update CLAUDE.md to reference all the newly fetched documentation so Claude Code knows where to find it for future assistance.

<function_calls>
<invoke name="Read">
<parameter name="file_path">CLAUDE.md</parameter>
<parameter name="offset">80</parameter>
<parameter name="limit">30</parameter>
</invoke>