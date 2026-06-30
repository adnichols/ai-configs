---
name: obsidian-clippings-capture
description: Capture web articles into Aaron's Obsidian vault with frontmatter and cleaned markdown. Default article captures go to ADN vault reference_articles; ask before putting captured articles into studio. Handles Substack pages that expose body_html in embedded JSON.
---

# Obsidian clippings capture

Use this when Aaron asks to capture an article into Obsidian.

## Target location

Default destination:

`~/Documents/Obsidian/adn_vault/Clippings/`

- Default captured articles to ADN vault root `Clippings`.
- Ask Aaron before putting a captured article into `studio`.
- If Aaron explicitly asks for clippings in studio, save to `~/Documents/Obsidian/studio/Clippings/`.
- Only use `research_and_notes/reference_articles/` when Aaron explicitly wants a reference article, index entry, and category placement there.

## Workflow

1. Confirm the page renders and get the canonical article title/description.
   - For dynamic pages, use browser tools first.
   - Dismiss share/subscribe modals if needed.

2. Check the destination folder and inspect an existing note for format.
   - For default ADN clippings, inspect `adn_vault/Clippings/` and read a representative clipping note to match schema.
   - For ADN reference-article captures requested explicitly, inspect `adn_vault/research_and_notes/reference_articles/` and read `_article_index.md` plus a representative article note to match schema.
   - For explicit studio clippings, inspect `studio/Clippings/*.md` and read a representative clipping.

3. Prefer direct extraction from page source when possible.
   - For Substack, fetch the article HTML with `curl` or `requests`.
   - Search the HTML for embedded JSON fields such as `body_html`, `description`, and `post_date`.
   - `body_html` is often easier to extract reliably than DOM scraping.

4. Convert article HTML to markdown-like text.
   - Preserve headings, paragraphs, links, emphasis, blockquotes, lists, and images.
   - Decode escaped URLs and HTML entities.
   - Normalize excessive blank lines.

5. Write the note using the schema appropriate to the destination.

For default ADN vault clippings, use frontmatter like the existing notes in `adn_vault/Clippings/`:

```yaml
---
title: <article title>
source: <canonical/article URL>
author: <Author Name>|null
published: YYYY-MM-DD
created: <today YYYY-MM-DD>
description: <subtitle or summary>|null
tags:
- clippings
ccore_id: <uuid>
---
```

Then preserve the article body in a readable markdown form.

For ADN vault reference articles, use frontmatter like:

```yaml
---
title: <article title>
source_url: <canonical/article URL>
authors:
- <Author Name>
publication_date: YYYY-MM-DD
added_date: <today YYYY-MM-DD>
category: ai_and_ml|leadership|technology
tags:
- <relevant tags>
relevance_to_projects:
- <project slugs if relevant>
permalink: research-and-notes/reference-articles/<category>/<slug>
ccore_id: <uuid>
---
```

Then include:
- `# Summary`
- `# Key Concepts`
- `# Relevance to My Work`
- `# Action Items`
- `# Full Content`

For explicit studio clippings, use frontmatter like:

```yaml
---
title: <article title>
source: <canonical/article URL>
author:
- '[[Author Name]]'
published: YYYY-MM-DD
created: <today YYYY-MM-DD>
description: <subtitle or meta description>
tags:
- clippings
ccore_id: <uuid>
---
```

6. Use a clean filename.
   - For default ADN vault clippings, the article title is fine.
   - For ADN reference articles, prefer a normalized slug such as `<topic-slug>-<year>.md` in the appropriate category folder.
   - For studio clippings, the article title is fine.
   - Strip trailing periods so you do not create `Title..md`.
   - Replace `/` with `-` if present.

7. Verify the saved file with `read_file`.
   - If you created a mistaken duplicate during iteration, delete the bad file and keep the clean one.
   - Only update `research_and_notes/reference_articles/_article_index.md` when saving to ADN reference articles.
   - If you first saved to the wrong vault or wrong ADN subfolder, move or recreate it in the correct location and remove the mistaken duplicate.

## Substack-specific notes

- Browser snapshots can confirm the article is fully accessible and reveal the exact title/subtitle.
- If DOM extraction returns null, inspect raw HTML instead.
- In Substack page source, `body_html` may appear as escaped JSON embedded in the page. Decode it before converting.
- Meta description is usually a good `description` field for the clipping.

## Pitfalls

- Do not assume BeautifulSoup is installed.
- Do not rely on `head`/truncated shell output for extraction; use targeted parsing.
- Watch for escaped quotes in extracted URLs like `\"https://...\"`; strip/decode them before writing markdown.
- Check for accidental duplicate filenames from punctuation.

## Verification

- Confirm the note exists in `studio/Clippings`.
- Read the first ~50-80 lines to verify frontmatter and initial body formatting.
- Report the final saved path back to Aaron.
