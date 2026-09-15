## Coding plan defaults

If the user asks to **create, send, publish, copy, save, register, review, or monitor a coding/implementation plan in Doct**, prefer a browser-reviewable Doct plan artifact over a plain text document.

- Use `doct-agent plans register` for all reviewer-facing plans; they are **HTML-only**. Do not produce or register Markdoc plans — write plan source as HTML.
- Use HTML when the user wants browser comments, plan review, annotations, readiness feedback, or a durable listener.
- Use Markdown/text documents only when the user explicitly asks for Markdown/text/no comments, supplies an existing Markdown plan that should stay Markdown-only, or repo guidance forbids HTML plans.
- Do not use `doct-agent documents create`, `documents replace-body`, or `documents publish-plan` for a reviewer-facing implementation plan unless `doct-agent onboard` or the CLI explicitly directs a legacy fallback. Plain text docs are not the default plan review surface.
- If you accidentally create a text doc for a reviewer-facing coding plan, register a replacement HTML plan with `doct-agent plans register`, start/verify the plan comment listener, and report the replacement URL as canonical.

Do not register a plan in Doct because the user said "create a plan" or "write a plan". Keep the local plan file local. Register only when they explicitly ask to send, publish, register, or review it in Doct, or invoke `reviewed-html-plan` / `send-plan-to-doct`.

### PR and deployment boundary in plans

Doct registration, lifecycle, board columns, readiness metadata, and progress rendering must preserve the canonical planning boundary:

- Executable phases and `Progress` cover the PR-reviewable slice: implementation, tests, docs, migration/release definitions, buildable artifacts, and truthful pre-merge verification.
- Environment deployment, promotion, merge-dependent smoke checks, production observation, and rollback execution are non-blocking post-merge delivery/operations work. Put them in a separate labeled section, not in the phase/progress one-to-one mapping and not in readiness criteria for PR creation.
- A pending deployment or missing deployment evidence must never prevent plan registration, execution-ready status, board movement to `in_progress`, source progress synchronization, or PR creation. Doct state describes plan/review workflow state; it does not turn an operational deployment checkpoint into an implementation gate.
- If an existing registered plan mixes post-merge deployment checkpoints into executable phases, preserve the operational obligation but correct the boundary during the next plan update: identify the PR-ready end state, move deployment/observation guidance to the non-blocking post-merge section, and do not claim the deployment occurred.

## Plan source formats

All reviewer-facing Doct plans are **HTML**. Resolve the plan source format from repo guidance, the user's explicit request, or the existing plan path:

- **HTML**: use `thoughts/plans/<slug>.html` for every reviewer-facing plan. The file must be real semantic HTML, not Markdown renamed as HTML. Do not produce Markdoc plan sources or register them with `--source-format markdoc`.
- **Markdown/text**: use `.md` only for explicit Markdown-only deliverables or non-reviewer-facing text documents. Publish with `documents create --kind text` or `documents replace-body`; do not promise browser plan-review comments on this surface.

Use lowercase, digits, and hyphens for generated slugs. In a repo, prefer `thoughts/plans/<slug>.html`. For standalone planning, a temporary handcrafted HTML source is acceptable when a browser-reviewable Doct plan is requested.

## HTML plan authoring contract

When writing or updating a handcrafted HTML plan:

1. Load repo planning guidance first: root `AGENTS.md`, product-intent docs, and any `thoughts/plans/AGENTS.md` or local planning overrides.
2. Use a dark-mode default theme with explicit dark background, light foreground, readable muted text, accessible accent/link colors, and `color-scheme: dark`.
3. Use a full-width single-column reviewer layout. Put a concise table of contents near the top after the title/status summary and before the main plan sections. Format the ToC as responsive columns; do not reserve a permanent left sidebar.
4. Add stable `id` attributes to major sections, phases, acceptance criteria, BDD scenarios, diagrams, figures, mockups, and likely comment targets. Doct comments on HTML plans are node/selector based, so stable IDs are part of the review contract.
5. Prefer semantic HTML: `section`, `article`, `figure`, `figcaption`, headings, lists, tables, and code blocks.
6. Keep plan-authored scripts, event handlers, forms, and active embeds out of the artifact; Doct owns review interactivity.
7. Keep images as relative repo assets when possible, with useful `alt`, `width`, and `height` attributes.

Reviewer-friendly structure:

- `Progress` contains checkboxes only for PR-bound executable phases; post-merge deployment/operations items are shown separately without blocking progress or readiness.
- The top table of contents links to every major plan section and each phase.
- Each phase has a stable wrapper ID, for example `id="phase-p1-contracts"`.
- Acceptance criteria and BDD scenarios have stable IDs, for example `id="ac-1"` and `id="bdd-retry-timeout"`.
- Add short context near diagrams and images so comments on visual elements are meaningful to the agent.

## Plan title contract (required)

Doct has **two** titles that reviewers see, and they must be the **same string**:

1. **Doct document / tree title** — set by `doct-agent plans register --title` (and repairable with `documents update-metadata --title` / `documents rename --title`).
2. **In-content plan title** — HTML `<title>` **and** top-level `<h1>`.

Never leave one fixed and the other stale. Filename stem inference is not a title.

**Failure modes to prevent:**

- Browser-review draft showing **Untitled Plan** with **No section entries generated** (missing HTML `<title>` / `<h1>`; Doct falls back to "Untitled Plan" when it cannot read the title).
- Doct sidebar/document name saying one thing while the plan body H1/chrome says another (register `--title` drifted from content, or only one side was updated).

### Canonical title (one string, three places)

Pick one concise human title (issue key optional), for example `NOD-1285 — Show signed-in Heddle account identity`. Write that **exact** string into every place below before handoff:

| Surface | Where |
|---------|--------|
| Source content | HTML: both `<title>` and top-level `<h1>`. |
| Register CLI | `doct-agent plans register ... --title '<Plan Title>'` sets the Doct document/tree title. |
| Doct document metadata | Created from `--title` on register. After any retitle, confirm with `documents get --id <id> --json` and repair with `documents update-metadata --id <id> --title '<Plan Title>'` (and `documents rename` when the tree label must move). `plans update` syncs plan **body/source only** and does **not** accept `--title`. |

### Before every `plans register`

1. Choose the canonical title.
2. **Write it into the source first** (`<title>`+`<h1>`), not only the CLI flag.
3. **Always** pass the same string as `--title '<Plan Title>'` on **register**. Do not rely on filename stem inference; it neither fixes Doct chrome nor guarantees document/content alignment.
4. For later body-only edits use `plans update` **without** `--title`. If the human title itself changes, update source title(s), then repair Doct with `documents update-metadata --title` (and rename if needed). Re-register with `--title` only when creating a replacement document.
5. **HTML** must set **both** `<title>…</title>` and a visible top-level `<h1>…</h1>` to that same string, then pass `--title` on register. For example:

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>NOD-1285 — Show signed-in Heddle account identity</title>
</head>
<body>
  <h1>NOD-1285 — Show signed-in Heddle account identity</h1>
```

   A leading `<h1>` alone is **not** enough for HTML browser review. Add stable `id` attributes on major sections and phases (see the HTML plan authoring contract above) so the Contents TOC and node/selector comments populate.
7. **After registration or retitle**, verify alignment:
   - `documents get --id <id> --json` → `title` equals the canonical string
   - Plan source still has the same string in frontmatter / `<title>` / `<h1>`
   - Browser chrome is not Untitled Plan and does not disagree with the tree name
8. **If anything is wrong**, fix **all** sides in one pass: edit source title(s) → `plans update` (body/source sync only; no `--title` flag) or re-register with `--title` → `documents update-metadata --title` (and rename if needed) so Doct metadata matches. Do not “fix” only the HTML body or only the Doct tree name.
9. After register/retitle, preserve the verified title in the scoped plan record. Codex does not mutate an external delivery ledger.
10. Resolve source/title mismatches before browser-review handoff.

## Register reviewer-facing plans

From the repo that owns the plan, register with `doct-agent plans register`.

For HTML plans (the only reviewer-facing plan format):

```bash
doct-agent plans register \
  --base-url https://doct.nodaste.com \
  --file thoughts/plans/<plan>.html \
  --source-format html \
  --allow-untemplated \
  --title '<Plan Title>' \
  --json
```

`--title '<Plan Title>'` is **required** on every registration (and should match HTML `<title>`+`<h1>`). Add `--workspace <workspace-slug-or-id>`, `--workspace-id <id>`, `--path '<path>'`, or `--parent-id <id>` only when repo guidance or the user specifies a destination; otherwise use the CLI defaults for those fields. Use `--allow-untemplated` for handcrafted HTML plans. Do not register Markdoc plans or pass `--source-format markdoc`.

Parse the JSON and preserve at least:

- Doct document/plan id,
- workspace id,
- current source/version or expected-version value when returned,
- canonical Doct URL,
- `sourceGuidance` when returned,
- the returned `listenerInstructions` object, especially `listenerCommand` (`doct-agent plans listen ... --jsonl`) and any source/version metadata returned for local tracking.

Show the user the canonical Doct URL from the registration response. If a command returns a relative path, resolve it against `https://doct.nodaste.com` before sharing it. Do not share `localhost`, local `plan-review` URLs, or Tailscale local-service URLs for the default flow.

Registration creates or updates the Doct review artifact. The repo file remains the source artifact for implementation; Doct is the review/registration surface.

## Update a registered plan

After editing a registered plan, push the updated source back through Doct:

```bash
doct-agent plans update \
  --base-url https://doct.nodaste.com \
  --id <document-id> \
  --workspace-id <workspace-id> \
  --file thoughts/plans/<plan>.html \
  --source-format html \
  --expected-version <version-from-last-read-or-register> \
  --json
```

If the expected version conflicts, read the current plan state with `doct-agent plans show --id <document-id> --json`, reconcile the conflict, and retry. Use `--force` only when you have confirmed you are overwriting your own stale registration state rather than discarding someone else's edits.

For continuous source sync while a reviewer is actively annotating a local source file, use the Doct watcher with the harness background-process tool:

```bash
doct-agent plans watch \
  --base-url https://doct.nodaste.com \
  --id <document-id> \
  --workspace-id <workspace-id> \
  --file thoughts/plans/<plan>.html \
  --json
```

Use background processing for the watcher when it is needed. Do not block the conversation on it. `plans watch` is source-sync/debug infrastructure only; it is not the correctness-critical comment listener and does not replace the listener startup gate above.

## Plan lifecycle and board state

Use Doct lifecycle commands for registered plan review status:

```bash
doct-agent plans lifecycle \
  --base-url https://doct.nodaste.com \
  --document-id <document-id> \
  --workspace-id <workspace-id> \
  --state active \
  --json
```

Registration should leave the board assignment at the service default, normally `backlog`. Do not move a newly registered plan to `in_progress` as part of browser-review setup. Execution workflows such as `run-plan` own the transition to `in_progress` when implementation actually starts. Do not delay that transition, readiness metadata, or later PR creation for deployment, promotion, merge-dependent validation, or production observation; those are separate post-merge operational states.

## Legacy local plan-review service

Use the old local `plan-review` CLI/service only when the user explicitly asks for the legacy local reviewer, a repo still mandates it, or you are migrating an existing local registration. In that case, follow the repo-local legacy instructions. Do not present local-service URLs as the default plan review surface.


Read [listener and feedback](listener.md) before handing off a registered reviewer-facing plan.
