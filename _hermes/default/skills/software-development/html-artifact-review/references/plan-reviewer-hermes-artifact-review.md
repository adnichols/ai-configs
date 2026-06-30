# Plan Reviewer as Hermes HTML Artifact Review Substrate

Session context: Aaron asked whether `~/code/plan-reviewer` is worth evolving into a variation where Hermes can post HTML content, subscribe to comments added through DOM selection, watch multiple documents, and converse/update documents through the HTML review surface.

## Observed fit

`plan-reviewer` already has many primitives needed for general HTML artifact review:

- local Fastify daemon and CLI for registering HTML documents
- sanitized HTML render in a no-script iframe, with the comment UI in the parent shell
- DOM, text-range, and image anchors
- stable review URLs and an index/navigator for active documents
- file-backed source sync and snapshot mode
- durable SQLite-backed comments
- idempotent comment creation via `clientMutationId`
- queue-backed delivery with claim -> ack -> resolve/release lifecycle
- SSE and polling event paths with replay semantics
- `browser.comment.v1` conversation payloads intended for agent adapters
- Codex delivery as proof of an adapter/outbox pattern

## Main product gaps for Hermes

The gaps are mostly product-shape gaps, not core infrastructure gaps:

1. The model is plan-specific: execution readiness, repo metadata, branches, commits, Linear issues, PR state, phases/progress.
2. It is not a visible threaded chat product yet; ack/resolve metadata is not the same as inline agent replies and user follow-ups.
3. There is no Hermes delivery adapter/session routing layer analogous to Codex delivery.
4. General artifacts need an explicit source-of-truth decision: file-backed source, DB blob, Obsidian/doct document, repo artifact, or generated snapshot.
5. Security needs more attention before broad exposure; current MVP is intentionally unauthenticated.

## Recommended product direction

Do not fork too early. Prefer a generalization/extension:

- Introduce a broader `Artifact` or `artifactKind` model; keep `plan` as one kind.
- Reuse the renderer, iframe shell, anchor capture, comment schema, queue, idempotency, events, and source sync.
- Add Hermes as a first-class delivery target.
- Add visible threaded replies and a document update loop.
- Keep file-backed artifacts as the default for editability and inspectability; snapshots remain useful for detached historical reviews.

Suggested milestones:

1. Hermes can publish one HTML artifact, register it, watch comments through a Hermes delivery adapter, reply inline in the browser, and update the source HTML file.
2. Multi-document watch queue with routing to the correct Hermes session/context.
3. General artifact types beyond plans: mockup, brief, diagram, report, dashboard, plan.

## Key framing

The value is not merely hosting HTML. The valuable substrate is precise anchored human feedback routed reliably into an agent loop that can answer and update the artifact.
