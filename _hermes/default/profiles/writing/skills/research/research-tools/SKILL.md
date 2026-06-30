---
name: research-tools
description: "Research and knowledge discovery: arXiv papers, RSS/Atom blog feeds, Polymarket prediction markets, and LLM Wiki KB construction."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [research, arxiv, blog, rss, polymarket, wiki, knowledge-base]
    related_skills: []
---

# Research Tools

Structured research workflows covering academic literature, content feeds, prediction markets, and knowledge-base construction.

## arXiv Papers

Search, fetch, and summarize papers from arXiv.

### Search
```bash
# By keyword
curl -s "http://export.arxiv.org/api/query?search_query=all:transformer+AND+cat:cs.CL&start=0&max_results=10"

# By ID
curl -s "http://export.arxiv.org/api/query?id_list=2304.03442"
```

### Download PDF
```bash
curl -L -o paper.pdf "https://arxiv.org/pdf/2304.03442.pdf"
```

### Extract and Summarize
Use `ocr-and-documents` (pymupdf / marker-pdf) to extract text, then ask the LLM to summarize methodology, results, and limitations.

### Bulk Monitoring
Set up a cron job or `blogwatcher`-style RSS feed on the arXiv API query URL.

## Blogwatcher (RSS/Atom Feeds)

Monitor blogs and feeds via the `blogwatcher-cli` tool.

### Add a Feed
```bash
blogwatcher add "https://example.com/feed.xml" --name "Example Blog"
```

### List Feeds
```bash
blogwatcher list
```

### Fetch New Items
```bash
blogwatcher fetch
```

### Filter by Keyword
```bash
blogwatcher fetch --grep "machine learning"
```

### Use Case
Pair with `llm-wiki` to auto-ingest new posts into an interlinked knowledge base.

## Polymarket

Query prediction markets for prices, order books, and historical data.

### List Markets
```bash
# Via polymarket-cli or direct API
curl -s "https://gamma-api.polymarket.com/markets?active=true&closed=false&limit=20"
```

### Market Prices
```bash
curl -s "https://gamma-api.polymarket.com/markets/<market-slug>"
```

### Order Book
```bash
curl -s "https://gamma-api.polymarket.com/orderbook/<condition-id>"
```

### Historical Prices
```bash
curl -s "https://gamma-api.polymarket.com/prices-history?conditionId=<id>&fidelity=hourly"
```

### Use Case
Track political, tech, or economic sentiment in real time. Combine with `arxiv` research to validate market assumptions.

## LLM Wiki

Build and query an interlinked markdown knowledge base.

### Structure
```
llm-wiki/
├── index.md          → hub page with links to topics
├── concepts/
│   ├── attention.md
│   └── transformers.md
├── papers/
│   └── attention-is-all-you-need.md
└── people/
    └── vaswani.md
```

### Workflow
1. Read `index.md` to discover topics
2. Follow links (`[[Concept Name]]` or `[text](path.md)`) to dive deeper
3. Add new pages in the appropriate subdirectory
4. Back-link from related pages

### Query Pattern
```bash
# Search within the wiki
grep -r "RLHF" llm-wiki/ --include="*.md"
```

### Use Case
Personal research notebook. Combine with `arxiv` and `blogwatcher` to auto-populate from new sources.

## Cross-Tool Workflow

1. **Discover:** `blogwatcher fetch` → spot trending topic
2. **Validate:** `arxiv` search for peer-reviewed backing
3. **Quantify:** `polymarket` for real-world sentiment / economic signal
4. **Archive:** `llm-wiki` to build persistent, interlinked knowledge
