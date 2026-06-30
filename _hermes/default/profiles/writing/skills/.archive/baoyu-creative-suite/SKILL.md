---
name: baoyu-creative-suite
description: "Generate consistent visual content with the Baoyu creative suite: article illustrations, knowledge comics, and infographics."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [baoyu, creative, image-generation, illustration, comic, infographic]
    related_skills: []
---

# Baoyu Creative Suite

The Baoyu creative suite produces consistent, structured visual content using the `image_generate` tool. It covers three media types that share a common workflow (analyze → confirm → outline → prompt → generate → finalize) but differ in output structure and visual dimensions:

1. **Article Illustrator** — themed illustrations for articles and blog posts
2. **Knowledge Comic** — educational / biography / tutorial comics
3. **Infographic** — dense visual summaries with 21 layouts × 21 styles

All three enforce:
- Prompt-first reproducibility (save every prompt to `prompts/` before generating)
- Data integrity (never alter source statistics)
- Secret stripping (scan for API keys/tokens before writing outputs)
- Absolute-path downloads (never rely on shell CWD for `curl -o`)

## Article Illustrator

Analyze articles, identify illustration positions, and generate images with **Type × Style × Palette** consistency.

### Three Dimensions
| Dimension | Controls | Examples |
|-----------|----------|----------|
| **Type** | Information structure | infographic, scene, flowchart, comparison, framework, timeline |
| **Style** | Rendering approach | notion, warm, minimal, blueprint, watercolor, elegant |
| **Palette** | Color scheme (optional) | macaron, warm, neon |

### Workflow
1. Detect reference images (if any) → record vision descriptions
2. Analyze content → write `analysis.md`
3. Confirm settings with `clarify` (preset/type, density, style, palette, language)
4. Generate outline → `outline.md`
5. Generate prompts → `prompts/*.md` (BLOCKING: no image without a saved prompt)
6. Generate images via `image_generate` → download with absolute-path `curl`
7. Finalize: insert markdown image tags and report

### Output Directory
- Article file path → `{article-dir}/imgs/`
- Pasted content → `illustrations/{topic-slug}/`

### Core Principles
- Visualize concepts, not metaphors
- Labels use actual article data (numbers, terms, quotes)
- Strip secrets before writing anything to disk

## Knowledge Comic

Create original knowledge comics with flexible **art style × tone × layout** combinations.

### Visual Dimensions
| Option | Values |
|--------|--------|
| Art | ligne-claire, manga, realistic, ink-brush, chalk, minimalist |
| Tone | neutral, warm, dramatic, romantic, energetic, vintage, action |
| Layout | standard, cinematic, dense, splash, mixed, webtoon, four-panel |
| Aspect | 3:4 (portrait), 4:3 (landscape), 16:9 (widescreen) |

### Presets (special rules beyond plain art+tone)
| Preset | Equivalent | Hook |
|--------|-----------|------|
| `ohmsha` | manga + neutral | Visual metaphors, no talking heads, gadget reveals |
| `wuxia` | ink-brush + action | Qi effects, combat visuals, atmospheric |
| `shoujo` | manga + romantic | Decorative elements, eye details, romantic beats |
| `concept-story` | manga + warm | Visual symbol system, growth arc |
| `four-panel` | minimalist + neutral + four-panel | 起承转合 structure, B&W + spot color |

### Workflow
1. Analyze content → `analysis.md`
2. Confirm style, focus, audience, reviews via `clarify`
3. Generate storyboard + characters → `storyboard.md`, `characters/`
4. Generate prompts → `prompts/*.md` (BLOCKING)
5. Generate images → download via absolute-path `curl`
6. Completion report

### Output Directory
`comic/{topic-slug}/`

### Character Consistency
Character descriptions from `characters/characters.md` are embedded inline in every page prompt. A PNG character sheet is generated as a human-facing review artifact, not as model input (`image_generate` does not accept images).

### Pitfalls
- Always download the URL returned by `image_generate` — downstream expects local files
- Use absolute paths for `curl -o`
- Step 2 confirmation required — do not skip
- Strip secrets from source content

## Infographic

Two dimensions: **layout** (information structure) × **style** (visual aesthetics). Freely combine any layout with any style.

### Layout Gallery (selected)
| Layout | Best For |
|--------|----------|
| `linear-progression` | Timelines, processes |
| `binary-comparison` | A vs B |
| `hierarchical-layers` | Pyramids, priority levels |
| `hub-spoke` | Central concept with related items |
| `bento-grid` | Multiple topics, overview (default) |
| `funnel` | Conversion, filtering |
| `circular-flow` | Cycles, recurring processes |
| `dense-modules` | High-density data-rich guides |

### Style Gallery (selected)
| Style | Description |
|-------|-------------|
| `craft-handmade` | Hand-drawn, paper craft (default) |
| `cyberpunk-neon` | Neon glow, futuristic |
| `bold-graphic` | Comic style, halftone |
| `technical-schematic` | Blueprint, engineering |
| `pixel-art` | Retro 8-bit |
| `pop-laboratory` | Blueprint grid, lab precision |
| `morandi-journal` | Hand-drawn doodle, warm tones |

### Workflow
1. Analyze content → `analysis.md`
2. Generate structured content → `structured-content.md`
3. Recommend combinations (check keyword shortcuts first)
4. Confirm options via `clarify`
5. Generate prompt → `prompts/infographic.md` (load layout + style refs)
6. Generate image via `image_generate`
7. Output summary

### Output Directory
`infographic/{topic-slug}/`

### Pitfalls
- Data integrity is paramount — never alter statistics
- Strip secrets before including in outputs
- `image_generate` only supports `landscape`, `portrait`, `square` — map custom ratios to nearest
