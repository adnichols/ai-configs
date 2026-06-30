---
name: creative-design-tools
description: "Design and prototype visual content: HTML artifacts, real design systems, hand-drawn diagrams, architecture diagrams, generative art, pixel art, and throwaway mockups."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [design, html, css, diagram, generative-art, pixel-art, prototype, mockup]
    related_skills: [baoyu-creative-suite]
---

# Creative Design Tools

A collection of tools for designing and prototyping visual content across different media and fidelity levels.

## HTML Artifacts (Claude Design)

Generate one-off HTML pages: landing pages, decks, prototypes, and interactive demos.

### Workflow
1. Gather requirements (audience, goal, brand constraints)
2. Generate a single `.html` file with inline CSS/JS
3. Use semantic HTML, accessible colors, and responsive layouts
4. Deliver the file; user opens it in a browser

### Tips
- Inline all assets (fonts, images as data URIs) for portability
- Use CSS Grid/Flexbox for layout
- Add `prefers-color-scheme` for dark mode
- Test on mobile viewport sizes

## Real Design Systems (Popular Web Designs)

54 real-world design systems (Stripe, Linear, Vercel, etc.) as copy-pasteable HTML/CSS.

### Usage
```html
<!-- Example: Stripe-style hero section -->
<section class="stripe-hero">
  <h1>...</h1>
  <p>...</p>
  <button class="stripe-button">...</button>
</section>
```

### Workflow
1. Ask the user which site's aesthetic they want
2. Reference the corresponding design system tokens (colors, spacing, typography)
3. Generate HTML/CSS that follows those tokens
4. Deliver as a single file or component

## DESIGN.md Token Specs

Author and validate Google's DESIGN.md token specification files.

### Structure
```markdown
# My Design System

## Colors
- Primary: #3B82F6
- Secondary: #10B981

## Typography
- Heading: Inter, 32px, 700
- Body: Inter, 16px, 400

## Spacing
- Base unit: 4px
- Scale: 1, 2, 4, 8, 16, 32, 64
```

### Validation
```bash
design-md validate design.md
```

### Export
```bash
design-md export design.md --format css    # Generates CSS custom properties
design-md export design.md --format json   # Generates token JSON
```

## Hand-Drawn Diagrams (Excalidraw)

Create hand-drawn style diagrams in Excalidraw JSON format.

### Output Format
Excalidraw JSON is a structured diagram format that can be:
- Imported into excalidraw.com
- Embedded in Notion, Obsidian, or VS Code extensions
- Rendered to PNG/SVG via CLI tools

### Diagram Types
- Architecture diagrams
- Flowcharts
- Sequence diagrams
- Mind maps

### Workflow
1. Describe the diagram in natural language
2. Generate Excalidraw JSON
3. User imports to excalidraw.com or compatible viewer

## Architecture Diagrams (SVG)

Dark-themed SVG diagrams for cloud, infrastructure, and system architecture.

### Style
- Dark background (default)
- Clean lines and minimal icons
- Color-coded by layer (compute, storage, network, security)
- Responsive SVG output

### Workflow
1. Gather system components and relationships
2. Generate SVG with labeled boxes, arrows, and groups
3. Deliver as `.svg` file or inline HTML

## p5.js Generative Art

Create generative art, shaders, interactive sketches, and 3D visuals with p5.js.

### Setup
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/p5.js/1.9.0/p5.min.js"></script>
```

### Sketch Template
```javascript
function setup() {
  createCanvas(800, 600);
  noLoop();
}

function draw() {
  background(20);
  // Generative art code here
}
```

### Modes
- **Static:** `noLoop()` — single frame
- **Animated:** `loop()` — continuous animation
- **Interactive:** Mouse/keyboard events
- **Shader:** WebGL mode with custom shaders
- **3D:** `WEBGL` renderer

### Output
Deliver as HTML file with embedded p5.js sketch.

## Pixel Art

Generate pixel art with authentic era palettes.

### Palettes
| Era | Colors | Characteristics |
|-----|--------|-----------------|
| NES | 54 usable | Limited, iconic |
| Game Boy | 4 greens | Monochrome, nostalgic |
| PICO-8 | 16 | Fantasy console palette |

### Workflow
1. Choose palette and canvas size (e.g., 32×32, 64×64)
2. Generate pixel art as PNG or sprite sheet
3. Deliver with palette reference

### Use Cases
- Game sprites
- Icons and avatars
- Retro-style illustrations

## Throwaway Mockups (Sketch)

Rapid HTML mockups for comparing 2–3 design variants.

### Rules
- Maximum 3 variants per session
- Each variant is a separate HTML file
- No external dependencies (inline CSS)
- Focus on layout and hierarchy, not polish

### Workflow
1. User describes the page/component
2. Generate 2–3 variant HTML files
3. User picks one; discard the rest

## Pretext Browser Demos

Build creative browser demos with the @chenglou/pretext library.

### Setup
```bash
npm install pretext
```

### Usage
```javascript
import { pretext } from 'pretext';
const demo = pretext`
  canvas {
    width: 800;
    height: 600;
  }
  // ...
`;
```

### Use Cases
- Algorithm visualizations
- Interactive math explanations
- Creative coding demos
