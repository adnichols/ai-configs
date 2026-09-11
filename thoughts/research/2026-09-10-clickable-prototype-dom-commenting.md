---
date: 2026-09-10
author: grok
type: research
status: complete
tags: [prototypes, visual-feedback, comments, cloudflare, agents, pastel, marker, bugherd, liveblocks]
last_updated: 2026-09-10
---

# Clickable prototypes with DOM comments on Cloudflare

Researched 2026-09-10. Primary sources: product docs, GitHub READMEs, Cloudflare docs. Not blog roundups.

## Contents

- [Question](#question)
- [Short answer](#short-answer)
- [What design feedback actually captures](#what-design-feedback-actually-captures)
- [Existing commercial widgets](#existing-commercial-widgets)
- [Open-source and embeddable libraries](#open-source-and-embeddable-libraries)
- [Clickable prototypes themselves](#clickable-prototypes-themselves)
- [Cloudflare hosting](#cloudflare-hosting)
- [Agent processing](#agent-processing)
- [What not to do](#what-not-to-do)
- [Recommendation](#recommendation)
- [Try this first](#try-this-first)
- [Open questions](#open-questions)
- [Sources](#sources)

## Question

What already exists for publishing a clickable HTML prototype, letting a reviewer pick a DOM element and leave a comment, and handing that comment to an agent? Hosting target is Cloudflare Pages or Durable Objects.

## Short answer

The product you want is two products glued together, not one.

1. A **real HTML prototype** you host yourself. Figma/Framer comments stay in Figma/Framer. They do not travel with a Cloudflare URL.
2. A **comment overlay** that pins to elements, not just a screenshot. Most "visual feedback" widgets capture a picture. That is useful for bugs. It is a weaker input for an agent that needs to edit a component.

Three workable stacks, ranked by how fast they get you to "someone commented, an agent acted":

| Path | What you buy vs build | Element pin | Agent loop | Own the data |
| --- | --- | --- | --- | --- |
| **Pastel around a CF-hosted prototype** | Buy Pastel. Host the prototype. | Yes. Comments sit on live elements, not a screenshot. | Native MCP at `https://api.usepastel.com/mcp`. 19 tools. Investigation guide per comment. | No |
| **BugHerd / Marker.io / Feedbucket script tag** | Buy a widget. One `<script>` in the prototype. | BugHerd pins to the element and records a CSS selector. Marker and Feedbucket are screenshot/video first. | Webhooks. You write a Worker that wakes the agent. | No |
| **Vercel Toolbar comments** | Host the prototype on Vercel instead of Cloudflare. | Yes. Pins store a DOM path such as `body > main > form > div.promo-container`. | `vercel comments` / `inspect --format json`. Official agent prompt. No public `comment.created` webhook. | No |
| **Own overlay on Workers + Durable Object** | Build a small picker + thread UI. Steal Liveblocks' pin model. | Yes, if you store selector + relative x/y + screenshot. | Same shape as Doct's `plans listen` JSONL dispatch. | Yes |

Do not host the prototype inside Doct. Doct HTML comments already use node/selector anchors and already wake an agent. The plan authoring contract forbids scripts, forms, and active embeds. A clickable prototype is the opposite of that.

Do not use Sideshow as the review surface for a multi-page prototype. It comments on HTML snippets, not on DOM nodes in a live app.

Cloudflare: put the prototype on **Workers with static assets**, not classic Pages, if comments need Durable Objects or a Queue consumer. Pages can bind a separate Worker that owns the Durable Object. Cloudflare's own matrix calls that a workaround and recommends Workers.

## What "design feedback" actually captures

Review tools split into two families. Mixing them up is why a lot of prototypes feel commentable but then starve the agent.

**Element pin.** Reviewer hovers, the page highlights a node, click drops a pin that stays attached as they scroll. Stored payload includes a CSS selector (and often xpath, bounding box, screenshot). BugHerd, Pastel, Liveblocks overlay comments, Feedbacker, `@sirendesign/markup`.

**Screenshot annotation.** Reviewer captures the viewport, draws arrows on a bitmap, submits a ticket. The pin is not a live DOM node. Marker.io, Usersnap, Feedbucket, Sentry User Feedback. Fine for "this looks broken." An agent then has to re-find the component from a picture and a URL.

You want the first family. Keep a screenshot as extra evidence. Do not make the screenshot the only locator.

A comment the agent can act on needs at least:

- `pageUrl` / route
- unique CSS selector (`@medv/finder` is the small library for this)
- relative x/y inside that element (Liveblocks stores `cursorSelectors`, `cursorX`, `cursorY`)
- visible text / `htmlSnippet`
- screenshot URL
- viewport and user agent
- thread id so the agent can reply and resolve

That is the same idea Doct already uses for HTML plan comments: stable ids plus selector context, then a listener that claims work.

## Existing commercial widgets

### Pastel (closest to the whole loop)

[usepastel.com/agents](https://usepastel.com/agents) and [help.usepastel.com MCP setup](https://help.usepastel.com/en/articles/16399713-connect-your-ai-agent-to-pastel-mcp-server)

You do not embed Pastel in the prototype. You create a **canvas** pointed at the prototype URL. Reviewers open a Pastel link, toggle Browse vs Comment, and pin comments to elements of the live site. Pastel proxies the live page and layers comments; it does not copy the site. A Chrome extension exists for VPN/firewall URLs. The prototype still has to be reachable as HTTP(S), not `file://`.

Agent side is already built:

- MCP at `https://api.usepastel.com/mcp`
- Works with Cursor, Claude, ChatGPT, or any MCP client
- Read: `list_canvases`, `get_canvas`, `list_canvas_comments`, `get_comment`, screenshots, attachments
- Write: `create_reply`, `update_comment_status`, assign, share
- Every comment fetch includes an investigation guide: which page, which pinned element, where the screenshot is, then "find it in the codebase, fix, reply, resolve"
- Agent acts as the connected user. Nothing runs unattended unless you run the agent.

Limits that matter here:

- Comments live in Pastel, not on your Cloudflare origin
- Website canvases are URL-based. Changing the canvas URL rewrites existing comments
- Browse vs Comment is a known UX footgun on clickable prototypes. Reviewers click through flows in Browse, then switch to Comment
- Free canvases historically had a short commenting window. Paid plans remove that
- CLI for "agent uploads a local page without deploying" is listed as coming soon, not shipping

This is the fastest way to get "prototype on Cloudflare, reviewer comments, agent processes." You host `https://proto.example.workers.dev/checkout`. You make a Pastel canvas of that URL. You connect MCP.

### BugHerd (best embeddable element pin)

[bugherd.com/feature/easy-website-annotations](https://bugherd.com/feature/easy-website-annotations), [JS install](https://support.bugherd.com/en/articles/11424426-installing-bugherd-using-javascript), [REST v2](https://docs.bugherd.com/api), webhooks via `task_create` / `task_update` / `comment` / `task_destroy`

Drop `sidebarv2.js?apikey=...` into `<head>`. Reviewers click an element. BugHerd highlights sections, drops a pin that stays on the element, captures a screenshot, and records browser/OS. Product copy and the Jira integration also advertise the **CSS selector of the pinned element**. The public REST task schema does not clearly name that field, so confirm the JSON before you treat BugHerd as an agent locator. Public feedback tab exists for unauthenticated visitors.

Agent path: REST + webhooks. No first-party MCP. You would POST into a Cloudflare Worker, then wake the same kind of listener Doct uses.

Fits if you want the widget *inside* the prototype instead of wrapping the prototype.

### Vercel Toolbar comments (closest hosted analogue, wrong host)

[Using comments](https://vercel.com/docs/comments/using-comments), [CLI changelog](https://vercel.com/changelog/manage-vercel-toolbar-comments-from-the-cli)

Overlay on preview deployments (and localhost/production via `@vercel/toolbar`). Pin on the live page, threads, mentions, screenshots, Markdown, Git PR sync, Slack two-way.

Agent side: `vercel comments` / `inspect --format json` includes a DOM path, for example `body > main > form > div.promo-container`. Vercel documents using that CLI from an agent. Public webhooks cover **deployment** events, not `comment.created`.

This is the product you would copy if you were on Vercel. It is not portable to Cloudflare. If Cloudflare hosting is a hard requirement, treat Vercel Comments as the UX reference, not the stack.

### Marker.io (best screenshot widget, weaker locator)

[github.com/marker-io/browser-sdk](https://github.com/marker-io/browser-sdk), [webhooks](https://help.marker.io/en/articles/3738778-webhook-notifications)

`@marker.io/browser` or a snippet. `widget.capture('fullscreen' | 'advanced')`. Issues include screenshot, console, network, viewport, custom metadata. Linear/Jira/GitHub destinations. Webhooks on Business: `issue.created`, `comment.created`, HMAC `X-Hub-Signature-256`. Payload has `website.url` and `screenshotUrl`. It does not give you a CSS selector of the clicked node.

Use Marker if the output is a Linear ticket. Do not use it as the primary agent locator.

### Feedbucket (agency widget, Linear 2-way)

[feedbucket.app](https://feedbucket.app/), [integrations](https://feedbucket.app/integrations)

Script tag. Clients click anywhere, annotate a screenshot, or record video. No account required. Two-way Linear/Jira/Asana. Webhooks on feedback created, comment created, resolved, unresolved.

Screenshot/video family, not a durable DOM pin. Linear 2-way is the selling point, not agent-ready selectors.

### Usersnap

[help.usersnap.com screenshot docs](https://help.usersnap.com/docs/feedback-with-a-screenshot), [webhooks](https://help.usersnap.com/docs/webhook)

Snippet + JS API. Annotate a captured screenshot (highlight, comment, pen, arrow, hide). Webhooks and REST are gated. Same family as Marker.

### Sentry User Feedback

[docs.sentry.io JS user feedback](https://docs.sentry.io/platforms/javascript/user-feedback/)

`feedbackIntegration({ enableScreenshot: true })`. Form plus optional screenshot plus session replay. Not a design-review pin overlay. Skip unless the prototype is already a Sentry-instrumented app and you only want a "report a bug" button.

## Open-source and embeddable libraries

### Liveblocks Comments overlay (best reference implementation)

[liveblocks.io overlay example](https://liveblocks.io/examples/overlay-comments/nextjs-comments-overlay), source [`CommentsOverlay.tsx`](https://github.com/liveblocks/liveblocks/blob/main/examples/nextjs-comments-overlay/src/components/comments/CommentsOverlay.tsx)

Apache-2.0 example. Pins threads on a live page. Thread metadata is:

```ts
{
  cursorSelectors: string; // comma-joined selectors
  cursorX: number;
  cursorY: number;
  zIndex: number;
}
```

On resize it re-resolves the selector list to pixel coords. Dragging a pin re-runs `getElementBeneath` and writes new metadata. Threads, composer, resolve, mentions, and realtime already exist. Liveblocks itself runs on Cloudflare Durable Objects.

This is the pin model to copy if you build your own. You can also just use Liveblocks and skip writing a comment store.

Cost: SaaS rooms, React-shaped SDK. Hosting the prototype on Cloudflare is fine. Comments would live in Liveblocks, not in your DO, unless you only steal the overlay code.

### Feedbacker (`feedbacker-react`)

[github.com/bebsworthy/feedbacker](https://github.com/bebsworthy/feedbacker)

MIT. React provider. Click an element, comment, screenshot via SnapDOM or html2canvas. Detects React Fiber / DevTools, falls back to `data-component`, `data-testid`, tag/id/class. `onFeedbackSubmit` POSTs:

```
id, componentName, componentPath[], comment, screenshot, url, timestamp, browserInfo, htmlSnippet
```

Default storage is localStorage. You supply the backend. Closest open-source match to "embed a picker in a React prototype."

### `@sirendesign/markup`

[npmjs.com/package/@sirendesign/markup](https://www.npmjs.com/package/@sirendesign/markup)

React widget. Detects React components and HTML elements. Expects your API:

- `GET/POST/PATCH /projects/:id/feedback`
- comments and screenshot upload endpoints

You would implement those on a Worker.

### Point Feedback (`pointfeedback`)

[github.com/RutgerGeerlings/pointfeedback](https://github.com/RutgerGeerlings/pointfeedback)

Next.js. Click-to-pin at a page coordinate. Feedback rounds. Storage adapters (memory, filesystem, Vercel Blob). Coordinate pins, not selector pins. Weaker when the layout reflows.

### Hypothesis

[hypothes.is embed docs](https://web.hypothes.is/help/embedding-hypothesis-in-websites-and-platforms/)

One script: `https://hypothes.is/embed.js`. Anchors with W3C Web Annotation selectors (XPath, text position, text quote). Built for documents and research annotation, not "this button is too big." Sidebar UX fights a clickable prototype. Open API is excellent. Wrong product shape.

### Annotator.js

[github.com/openannotation/annotator](https://github.com/openannotation/annotator)

Library, not a product. Text/image annotation building blocks. You would still build the pin UI, storage, and agent dispatch.

### CSS selector generators (you will need one)

- [`@medv/finder`](https://github.com/antonmedv/finder) — 1.5kb, shortest unique selector. Default pick.
- [`css-selector-generator`](https://github.com/fczbkk/css-selector-generator) — Shadow DOM, multiple elements.
- [`unique-selector`](https://github.com/ericclemmons/unique-selector) — older, still used.

Prefer `data-comment-id` or stable `id` on prototype components. Finder is the fallback when the markup is messy.

### Other drop-ins worth knowing

- **`@reviewjs/annotate`** ([github.com/reviewjs/annotate](https://github.com/reviewjs/annotate)). One script. Overlay pins, geometry, text. localStorage + JSON export. No screenshot, no unique CSS selector for an arbitrary click. Best zero-backend overlay if you only need humans to mark a page.
- **`qa-overlay`**. Coordinate pins (`x`, `y`, viewport). README describes a Claude Code handoff. Coordinates lie after reflow.
- **`annotated-feedback`**. React widget + Convex backend + MCP. Closer to a full product than Feedbacker, Convex-shaped rather than Cloudflare-shaped.
- **Filestage**. Import a public HTTPS URL or an HTML zip into their proofing viewer. Click-to-pin on the imported view. Not a widget inside your prototype. Enterprise API.
- **`pick-dom-element`** ([hmarr/pick-dom-element](https://github.com/hmarr/pick-dom-element)). Tiny overlay picker: `start({ onHover, onClick })`. You still write comments, storage, and selectors.
- **BugPin** (two products). `aranticlabs/bugpin` is a screenshot markup widget. [bugpin.tech](https://www.bugpin.tech/) is a Chrome extension that pins to a live element and stores a CSS selector **plus a fingerprint** (text, attributes, parent/sibling, `data-testid` / `aria-label`, nth-of-type fallback, multi-candidate scoring) so the pin can be re-found after deploys. Copy the fingerprint idea if you build your own overlay. Do not confuse the two.
- HTML prototype kits if you are not generating from Pencil/v0: [GOV.UK Prototype Kit](https://prototype-kit.service.gov.uk/prototyping/), [NHS prototype kit](https://prototype-kit.service-manual.nhs.uk/), [ptyped Kit](https://github.com/ptyped/kit), [Patternslib](https://github.com/Patternslib/Patterns). These produce real HTML. They do not include a comment overlay.

## Clickable prototypes themselves

The prototype should be a real HTML/JS app: routing, forms, hover states. Image-map "clickable PDF" prototypes cannot survive DOM comments.

| Tool | What it produces | Comments | Host on Cloudflare |
| --- | --- | --- | --- |
| **pen.dev (Pencil)** | `.pen` canvas. CLI `Export()` can emit HTML. MCP can generate React/HTML into a repo. | Not a review product. | Yes. Export HTML, deploy Worker assets. |
| Hand-authored HTML / Vite / React | Full control. Add `id` and `data-comment-id` as you build. | Whatever overlay you add. | Yes |
| v0 / Claude HTML artifact | Fast first pass. | None. | Yes, if you take the files |
| Framer | Real hosted site. Official answer: **no HTML/static export**. Custom domains still go through Framer. | Editor collab and cursor chat, not a portable overlay. | No |
| Maze Website Test | Research harness on any public URL, including a CF-hosted prototype. | Insights stay in Maze. | You host the URL; Maze wraps it |
| Figma prototype | Artboard hotspots, not DOM. | Figma comments. | No useful DOM to pin |
| Storybook | Component explorer, not a user flow. | Chromatic UI Review, not Storybook core. | Yes, as a static build |
| Useberry / ProtoPie | High-fidelity players. ProtoPie has no HTML export. | Stay in those products. | No |

Pencil in this repo's MCP is a design canvas, not a comment system. Use it to *make* the prototype, then publish the HTML.

## Cloudflare hosting

Cloudflare's current guidance: **start new full-stack work on Workers with static assets**. Pages still works. New features go to Workers.

Sources:

- [Migrate from Pages to Workers](https://developers.cloudflare.com/workers/static-assets/migration-guides/migrate-from-pages/)
- [Workers vs Pages matrix](https://developers.cloudflare.com/workers/static-assets/compatibility-matrix)
- [Durable Objects on Pages](https://developers.cloudflare.com/pages/functions/bindings/#durable-objects)
- [Realtime chat DO example](https://developers.cloudflare.com/workers/tutorials/deploy-a-realtime-chat-app/)
- [Full-stack on Workers](https://blog.cloudflare.com/full-stack-development-on-cloudflare-workers/)

Facts that change the architecture:

- A Worker can serve `assets.directory` (the prototype) and a `main` script (the comment API) in one deploy.
- Durable Objects are first-class on Workers.
- Pages cannot define a Durable Object class. You create a Worker that owns the DO, then bind it. Same for Queue **consumers** (Pages can produce, not consume).
- One DO per prototype (or per room) is the comment thread coordinator: hibernating WebSockets, in-memory fanout, SQLite storage on the object.
- D1 if you want to list comments across prototypes. R2 for screenshots. Queues to wake an agent without holding the WebSocket.

Recommended shape if you own comments:

```
Worker (static assets = prototype HTML/JS)
  GET  /*                  → ASSETS (SPA)
  GET  /overlay.js         → comment widget
  GET  /api/comments       → D1 or DO storage
  POST /api/comments       → DO room + enqueue
  GET  /ws                 → Durable Object hibernating WebSocket

Durable Object "PrototypeRoom" keyed by prototypeId
  threads, presence, broadcast

Queue "comment-created"
  consumer Worker POSTs to agent listener
  payload: selector, snippet, screenshot R2 key, threadId
```

If you only need static hosting and Pastel/BugHerd owns comments, Pages or a static-only Worker is enough. You do not need a Durable Object.

### PartyKit / PartyServer and the Agents SDK

[How PartyKit works](https://docs.partykit.io/how-partykit-works/), [cloudflare/partykit](https://github.com/cloudflare/partykit), [Agents SDK](https://developers.cloudflare.com/agents/runtime/execution/queue-tasks/)

A PartyKit **Party** is a Durable Object with `onConnect` / `onMessage` / `room.broadcast` and hibernating WebSockets. PartyServer is the same library on *your* Workers. `y-partyserver` is Yjs collab editing, closer to Doct than to pin comments.

The Cloudflare Agents SDK (`agents` npm) is a Durable Object with SQLite, WebSockets, `schedule()`, and an **in-process** FIFO queue. That in-process queue is not Cloudflare Queues. It runs while the agent isolate is awake. For "comment created, wake something even if nobody is looking," use **Cloudflare Queues** into an Agent DO, not only `this.queue()`.

There is no first-party Cloudflare annotation product. The official pattern to steal is [workers-chat-demo](https://github.com/cloudflare/workers-chat-demo): one DO per room, WebSockets, stored history.

## Agent processing

You already have two in-house patterns. Reuse the contract, not the host.

**Doct plan comments.** Browser comment on a node/selector. `doct-agent plans listen --jsonl` emits `plan_comment_dispatch`. Agent claims, edits, replies, acks, resolves. HTML plans even require stable `id`s because comments are selector-based. That is the right *loop*. The host is wrong for a clickable app.

**Sideshow.** Publish HTML, user comments, plugin notifies the session. Snippet-scoped, not element-scoped, not a public prototype URL.

**Pastel MCP.** Closest off-the-shelf loop. Agent pulls comments with element + screenshot + investigation steps, patches the repo, replies, resolves.

**Webhook → Worker → agent.** Marker, BugHerd, Feedbucket, Usersnap. The Worker should normalize into one envelope:

```json
{
  "prototypeId": "checkout-v3",
  "pageUrl": "https://proto.example.workers.dev/checkout",
  "route": "/checkout",
  "selector": "form > button.pay",
  "cssPath": "body > main > form > button.pay",
  "nodeId": "pay-now",
  "quote": "Pay now",
  "fingerprint": {
    "tag": "button",
    "text": "Pay now",
    "attrs": { "type": "submit", "data-testid": "pay-now" },
    "parentText": "Order summary"
  },
  "cursorX": 0.5,
  "cursorY": 0.4,
  "bbox": { "x": 12, "y": 4, "w": 120, "h": 40 },
  "screenshotKey": "r2://comments/th_123.png",
  "body": "This should say Place order",
  "threadId": "th_...",
  "submitAction": "agent",
  "author": "alex@..."
}
```

Then treat it like a Doct dispatch: one claim, one reply, one resolve. Split `submitAction: "conversation"` from `submitAction: "agent"` so chat replies do not wake the agent. Do not invent a second review product.

A CSS selector alone breaks after a restyle. Store the selector plus a fingerprint (text, attributes, parent context, `data-testid` or `aria-label`) and score candidates when the selector is stale. BugPin's Chrome extension does this. Liveblocks stores `cursorSelectors` plus relative x/y instead.

## What not to do

- Put the prototype in Doct so people can comment. Doct forbids the interactivity the prototype needs.
- Use Hypothesis because it is "open annotation." Reviewers will bounce off the sidebar.
- Use Sentry feedback as a design-review tool.
- Store only `{x, y}` page coordinates. Layout changes make every pin lie. Store selector + relative coords + screenshot.
- Classic Pages plus an in-project Durable Object. That is not how Pages works.
- Expect Figma prototype comments to show up on a Cloudflare URL.

## Recommendation

If the goal is to try the loop on a real prototype this month: **host the HTML on a Worker, wrap the URL in Pastel, connect Pastel MCP.** You get element pins and an agent that already knows how to resolve comments. Cloudflare stays a static host.

If the goal is a first-party "comment on our prototypes" product that an agent owns: **do not buy Marker.** Copy the Liveblocks overlay pin metadata, embed a Feedbacker-class picker (or 200 lines of `finder` + composer), store threads on a Durable Object, screenshot to R2, dispatch on a Queue. Put stable `data-comment-id`s on prototype components the same way Doct plans get stable section ids.

BugHerd is the commercial middle: embeddable, real element pins, CSS selector in the product UI, webhooks. Use it if you want a widget inside the prototype and do not want to run MCP through Pastel's iframe. Confirm the REST JSON includes the selector before you depend on it.

## Try this first

1. Export or write a real HTML prototype (Pencil HTML export, Vite, or a static checkout flow). Put stable `id` or `data-comment-id` on the components you expect comments on.
2. Deploy it with a Worker that serves `assets.directory`. A static-only Worker is enough for this trial. You do not need a Durable Object yet.
3. Create a Pastel canvas pointed at that URL. Invite one reviewer. Have them pin two comments: one copy change, one interaction bug.
4. Connect Pastel MCP in Cursor, Claude, or ChatGPT. Ask the agent to list unresolved comments and fix one of them in the repo.
5. Decide from that trial. If Pastel's iframe and MCP are enough, stop. If you need the widget inside the prototype and owned threads, build the overlay on a Durable Object using the Liveblocks pin metadata and the envelope above.

## Open questions

- BugHerd product copy says it captures the CSS selector. The public REST task schema does not clearly name that field. Confirm a live `GET /api_v2/projects/{id}/tasks/{id}.json` payload before using BugHerd as the agent locator.
- Pastel's free commenting window and current paid limits change. Recheck [usepastel.com/plans](https://usepastel.com/plans) before committing a trial.
- Liveblocks overlay comments are a Next.js example, not a drop-in script. Porting the pin metadata to vanilla JS on a Worker is unproven in this research.
- No inspected Cloudflare page documents a first-party comment overlay. Chat-demo Durable Objects are the pattern, not a product.
- Vercel Toolbar comments have no public `comment.created` webhook. Agent access is CLI poll, not push.

## Sources

- Pastel agents: https://usepastel.com/agents
- Pastel MCP: https://help.usepastel.com/en/articles/16399713-connect-your-ai-agent-to-pastel-mcp-server
- Pastel features: https://usepastel.com/features
- Marker SDK: https://github.com/marker-io/browser-sdk
- Marker webhooks: https://help.marker.io/en/articles/3738778-webhook-notifications
- BugHerd annotations: https://bugherd.com/feature/easy-website-annotations
- BugHerd JS install: https://support.bugherd.com/en/articles/11424426-installing-bugherd-using-javascript
- BugHerd API: https://docs.bugherd.com/api
- Feedbucket: https://feedbucket.app/ and https://feedbucket.app/integrations
- Usersnap screenshots: https://help.usersnap.com/docs/feedback-with-a-screenshot
- Usersnap webhooks: https://help.usersnap.com/docs/webhook
- Sentry user feedback: https://docs.sentry.io/platforms/javascript/user-feedback/
- Hypothesis embed: https://web.hypothes.is/help/embedding-hypothesis-in-websites-and-platforms/
- Annotator.js: https://github.com/openannotation/annotator
- Liveblocks overlay: https://liveblocks.io/examples/overlay-comments/nextjs-comments-overlay
- Liveblocks overlay source: https://github.com/liveblocks/liveblocks/blob/main/examples/nextjs-comments-overlay/src/components/comments/CommentsOverlay.tsx
- Liveblocks Comments: https://liveblocks.io/docs/collaboration-features/comments
- Feedbacker: https://github.com/bebsworthy/feedbacker
- @sirendesign/markup: https://www.npmjs.com/package/@sirendesign/markup
- Point Feedback: https://github.com/RutgerGeerlings/pointfeedback
- @medv/finder: https://github.com/antonmedv/finder
- Cloudflare Pages vs Workers: https://developers.cloudflare.com/workers/static-assets/migration-guides/migrate-from-pages/
- Cloudflare DO on Pages: https://developers.cloudflare.com/pages/functions/bindings/#durable-objects
- Cloudflare realtime chat: https://developers.cloudflare.com/workers/tutorials/deploy-a-realtime-chat-app/
- Cloudflare full-stack Workers: https://blog.cloudflare.com/full-stack-development-on-cloudflare-workers/
- Pencil CLI export: https://docs.pencil.dev/for-developers/pencil-cli
- Framer no HTML export: https://www.framer.com/help/articles/can-i-export-my-website-to-html-and-self-host-it/
- Vercel comments: https://vercel.com/docs/comments/using-comments
- Vercel comments CLI: https://vercel.com/changelog/manage-vercel-toolbar-comments-from-the-cli
- PartyKit: https://docs.partykit.io/how-partykit-works/
- Cloudflare Agents queue: https://developers.cloudflare.com/agents/runtime/execution/queue-tasks/
- Doct HTML comment contract: `skills/doct-document-ops/SKILL.md`
