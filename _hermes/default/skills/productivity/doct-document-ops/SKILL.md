---
name: doct-document-ops
description: Interact with doct through the doct-agent CLI. Use when asked to open a doct URL, list doct workspaces or documents, view/create/edit doct documents, update metadata, rename/move/delete, add or inspect comments, create/register/update/monitor HTML, Markdoc, or Markdown coding plans in Doct, publish plans for browser review, or run read-only doct DB/log triage. For reviewer-facing coding plans, use `doct-agent plans register` on `https://doct.nodaste.com` and start/verify the comment listener; use text-document publishing only when Markdown/text is explicitly requested.
---

# Doct document operations

Use this skill when the user wants work done **inside doct itself** or wants a coding plan created, published, registered, updated, or monitored in Doct.

## Golden rule: doct-agent only

Every doct operation goes through the `doct-agent` CLI on PATH. Do **not** use `doct-cli`, raw `curl`/REST calls, hand-written Hocuspocus/Yjs scripts, local wrapper scripts, or token-store fallbacks. `doct-agent` wraps REST for discovery, reads, creation, plan registration, metadata, and Yjs/Hocuspocus-safe edits/comments — with verified readback where supported. If a task seems to need raw REST or a custom Yjs script, you are on the wrong path: find the matching `doct-agent` subcommand or run `doct-agent onboard`.

- **Install/update via Homebrew only.** From the doct repo root: `brew tap local/doct "$(pwd)"` then `brew install --build-from-source local/doct/doct-agent`. Refresh with `brew reinstall --build-from-source local/doct/doct-agent`.
- Most discovery and mutation commands accept `--json`.
- `references/doct-agent-commands.md` is the local command reference. `doct-agent onboard` prints the canonical, always-current spec from the installed CLI — consult it if anything here looks stale.

## Auth and endpoint

Production Doct is the default target for plan registration:

```bash
https://doct.nodaste.com
```

Check first:

```bash
doct-agent auth status --all --json
doct-agent context --base-url https://doct.nodaste.com --json
```

If production is authenticated but not default, either pass `--base-url https://doct.nodaste.com` on every command or set it:

```bash
doct-agent auth default --base-url https://doct.nodaste.com
```

If not authenticated:

1. Ask the doct owner to generate and approve a selected-agent enrollment code.
2. `doct-agent auth login --base-url https://doct.nodaste.com` (develop: `https://doct.develop.nodaste.com`).
3. Paste the enrollment code when prompted, or pass `--enrollment-code <code>`.
4. Fallback: `doct-agent auth import-pat --base-url <url> --token <doct_pat_v1_...>`.

The CLI discovers and stores the collaboration websocket URL after auth; pass `--websocket-url` only to override. For one-off automation, `DOCT_AGENT_PAT` overrides the stored token only when paired with an explicit `--base-url`.

## Resolve the target first

Accept any of: a full doct URL, document id, workspace + path/title, or registered plan URL/id.

- Doct document URLs look like `https://doct.nodaste.com/d/<workspace-handle>/docs/<document-id>` — parse `<document-id>` from `/docs/<uuid>`, then use `doct-agent documents get --id <id>` or `doct-agent plans show --id <id>` for plan artifacts.
- Discover with `doct-agent workspaces list --base-url https://doct.nodaste.com --json`, then `doct-agent documents list --workspace-id <id> --json`.
- If still ambiguous, ask for exactly one missing locator: document URL, document/plan id, or workspace + path.

## Command map by task

| Task | Command |
|------|---------|
| Check auth / identity | `doct-agent auth status --all --json` · `doct-agent context --base-url https://doct.nodaste.com --json` |
| Set default endpoint | `doct-agent auth default --base-url https://doct.nodaste.com` |
| List workspaces | `doct-agent workspaces list --base-url https://doct.nodaste.com --json` |
| List documents | `doct-agent documents list --workspace-id <id> --json` |
| Read a text document | `doct-agent documents get --id <id> --text` (markdown) or `--json` (metadata); or `--workspace-id <id> --path '<path>'` |
| Create a text document | `doct-agent documents create --workspace-id <id> --title <t> --path <p> --kind text --content '# ...'` (published by default; add `--status draft` for a hidden draft; `--parent-id` to nest) |
| Replace full text body | `doct-agent documents replace-body --id <id> --file prepared.md` (or `--text` / `--stdin`) |
| Append to text body | `doct-agent collab edit --document-id <id> --append-markdown '...'` |
| Surgical text edit | `doct-agent collab anchored <replace\|insert-before\|insert-after\|delete> --document-id <id> --selected-text '...' [--text '...']` |
| Add a text-doc comment thread | `doct-agent collab comments add --document-id <id> --selected-text '...' --body '...'` |
| List / reply / resolve text-doc comments | `doct-agent collab comments <list\|reply\|resolve\|unresolve> --document-id <id>` |
| Register an HTML plan | `doct-agent plans register --base-url https://doct.nodaste.com --file thoughts/plans/<plan>.html --source-format html --allow-untemplated --json` |
| Register a Markdoc plan | `doct-agent plans register --base-url https://doct.nodaste.com --file thoughts/plans/<plan>.markdoc --source-format markdoc --json` |
| Update a registered plan | `doct-agent plans update --id <document-id> --workspace-id <workspace-id> --file thoughts/plans/<plan>.html --source-format html --expected-version <version> --json` |
| Show a registered plan | `doct-agent plans show --id <document-id> --json` |
| Watch/sync a plan source file | `doct-agent plans watch --id <document-id> --workspace-id <workspace-id> --file thoughts/plans/<plan>.html --json` |
| Start durable plan comment listener | `doct-agent plans listen --workspace-id <workspace-id> --document-id <document-id> --jsonl` |
| Inspect plan queue | `doct-agent plans queue list --workspace-id <workspace-id> --document-id <document-id> --json` |
| Drain / claim next plan item | `doct-agent plans agent next --workspace-id <workspace-id> --document-id <document-id> --no-wait --json`; use `--wait` only for one-shot listener/recovery flows |
| Reply / ack / resolve / release plan item | `doct-agent plans <reply\|ack\|resolve\|release> ... --thread-id <thread-id> --claim-id <claim-id> --json` |
| Plan lifecycle / board / readiness metadata | `doct-agent plans lifecycle --document-id <id> --workspace-id <id> --state active --json`; `doct-agent plans board list|set ...`; `doct-agent plans metadata --execution-ready true|false ...` |
| Title / status | `doct-agent documents update-metadata --id <id> --title <t> --status <s>` |
| Rename | `doct-agent documents rename --id <id> --workspace-id <id> --title <t>` |
| Move / reorder | `doct-agent documents move --id <id> --workspace-id <id> --new-parent-id <id>` |
| Delete | `doct-agent documents delete --id <id> --workspace-id <id>` |
| Read-only ops triage | `doct-agent triage <run\|logs\|db-query\|db-tables\|db-describe\|...>` |

### Text edit notes

- `replace-body` is the safe path for a full text-document rewrite.
- For anchored edits and comments, build `--selected-text` from the document's **visible prose**, not markdown syntax. Add prefix/suffix context when a quote is ambiguous.
- Bootstrap empty or near-empty documents with creation-time `--content` or `collab edit --append-markdown` until there is anchorable text to target.

## Coding plan defaults

If the user asks to **create, send, publish, copy, save, register, review, or monitor a coding/implementation plan in Doct**, prefer a browser-reviewable Doct plan artifact over a plain text document.

- Use `doct-agent plans register` for reviewer-facing HTML and Markdoc plans.
- Use HTML or Markdoc when the user wants browser comments, plan review, annotations, readiness feedback, or a durable listener.
- Use Markdown/text documents only when the user explicitly asks for Markdown/text/no comments, supplies an existing Markdown plan that should stay Markdown-only, or repo guidance forbids HTML/Markdoc plans.
- Do not use `doct-agent documents create`, `documents replace-body`, or `documents publish-plan` for a reviewer-facing implementation plan unless `doct-agent onboard` or the CLI explicitly directs a legacy fallback. Plain text docs are not the default plan review surface.
- If you accidentally create a text doc for a reviewer-facing coding plan, register a replacement HTML/Markdoc plan with `doct-agent plans register`, start/verify the plan comment listener, and report the replacement URL as canonical.

For Aaron-facing development plans, default to a browser-reviewable HTML or Markdoc plan registered in Doct even when the prompt only says "create a plan" or "publish a plan." Use Markdown/text only when he explicitly asks for that non-reviewable format or repo guidance requires it.

## Plan source formats

Resolve the plan source format from repo guidance, the user's explicit request, or the existing plan path:

- **Markdoc**: prefer `thoughts/plans/<slug>.markdoc` when repo guidance or Doct templates define Markdoc as the editable source. Keep Markdoc compact and template-compatible; preserve and follow any `sourceGuidance` returned by registration.
- **Handcrafted HTML**: use `thoughts/plans/<slug>.html` for repos whose active plan artifact is HTML, for legacy/raw HTML plans, or when a reviewer-facing plan is needed and no Markdoc template is defined. The file must be real semantic HTML, not Markdown renamed as HTML.
- **Markdown/text**: use `.md` only for explicit Markdown-only deliverables or non-reviewer-facing text documents. Publish with `documents create --kind text` or `documents replace-body`; do not promise browser plan-review comments on this surface.

Use lowercase, digits, and hyphens for generated slugs. In a repo, prefer `thoughts/plans/<slug>.<html|markdoc|md>` unless repo-local instructions specify another path. For standalone planning, a temporary handcrafted HTML source is acceptable when a browser-reviewable Doct plan is requested.

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

- `Progress` contains the phase checkboxes.
- The top table of contents links to every major plan section and each phase.
- Each phase has a stable wrapper ID, for example `id="phase-p1-contracts"`.
- Acceptance criteria and BDD scenarios have stable IDs, for example `id="ac-1"` and `id="bdd-retry-timeout"`.
- Add short context near diagrams and images so comments on visual elements are meaningful to the agent.

## Register reviewer-facing plans

From the repo that owns the plan, register with `doct-agent plans register`.

For HTML plans:

```bash
doct-agent plans register \
  --base-url https://doct.nodaste.com \
  --file thoughts/plans/<plan>.html \
  --source-format html \
  --allow-untemplated \
  --json
```

For Markdoc plans:

```bash
doct-agent plans register \
  --base-url https://doct.nodaste.com \
  --file thoughts/plans/<plan>.markdoc \
  --source-format markdoc \
  --json
```

Add `--title '<Plan Title>'`, `--workspace <workspace-slug-or-id>`, `--workspace-id <id>`, `--path '<path>'`, or `--parent-id <id>` only when repo guidance or the user specifies a destination. Otherwise use the CLI defaults. Use `--allow-untemplated` for handcrafted HTML plans. Do not use it for normal Markdoc template/config-backed plans unless the CLI or repo guidance says the plan is intentionally untemplated.

Parse the JSON and preserve at least:

- Doct document/plan id,
- workspace id,
- current source/version or expected-version value when returned,
- canonical Doct URL,
- `sourceGuidance` when returned,
- the full returned `listenerInstructions` object, including `startCommand`, `preferredCommand`, `drainCommand`, lifecycle/board commands, ack/resolve guidance, and processing-loop requirements.

Show the user the canonical Doct URL from the registration response. If a command returns a relative path, resolve it against `https://doct.nodaste.com` before sharing it. Do not share `localhost`, local `plan-review` URLs, or Tailscale local-service URLs for the default flow.

Registration creates or updates the Doct review artifact. The repo file remains the source artifact for implementation; Doct is the review/registration surface.

## Start the comment listener

A registered reviewer-facing plan is not ready for browser-review handoff until the comment listener is running, unless the user explicitly asked for registration-only work. Treat the returned `listenerInstructions` as the live contract because field names and preferred delivery commands can evolve.

After registration:

1. Run the returned `lifecycleCommand`, or equivalent `doct-agent plans lifecycle --state active`, before draining/listening.
2. Leave the plan in its registration/default board column, normally `backlog`, unless the user explicitly requested a board move. Registration and browser-review handoff do not mean implementation is underway.
3. Drain pending work with the returned `drainCommand` (`doct-agent plans agent next ... --no-wait --json`) until it returns `status: "empty"`.
4. Start the durable listener in the active agent harness background process so listener output is delivered to the agent. Prefer `listenerInstructions.startCommand` when present (`doct-agent plans listen ... --jsonl`); otherwise use the returned `preferredCommand`/`durableCommand`. Name the process with the plan/document id when the harness supports it.
5. Do not process claims inline inside the listener. When a listener event or `agent next --wait` result claims a browser comment, dispatch the claim payload and returned commands to a sub-agent or a clearly separate worker step, then keep or restart the listener.
6. Keep the listener running until the plan is complete, no longer active, or the user explicitly stops review. If the listener cannot be started, report that as a handoff blocker before telling the user to annotate the plan.

Agent background-process example:

```bash
doct-agent plans listen \
  --base-url https://doct.nodaste.com \
  --workspace-id <workspace-id> \
  --document-id <document-id> \
  --jsonl
```

Use the exact command returned by `listenerInstructions` when it differs from this example.

`plans watch` is only source sync/debug visibility and does not replace the comment listener.

## Publish Markdown/text plans

Use this path only when the user explicitly asks for Markdown/text/no comments or repo guidance forbids HTML/Markdoc for the workflow.

Create a Markdown/text plan document with a minimal body first:

```bash
doct-agent documents create \
  --base-url https://doct.nodaste.com \
  --workspace-id <workspace-id> \
  --title '<Plan Title>' \
  --path '<path>' \
  --kind text \
  --content '# <Plan Title>' \
  --json
```

Then prepare the Markdown file locally and replace the body:

```bash
doct-agent documents replace-body \
  --id <document-id> \
  --file thoughts/plans/<plan>.md \
  --json
```

Use `documents publish-plan` only as a legacy fallback when the CLI explicitly directs you there for old Markdown/text-plan flows. Current `doct-agent onboard` says `documents publish-plan` fails closed with replacement guidance for plan-review publishing.

Return the created/updated Doct URL, document id, workspace id, and status. State clearly that Markdown/text documents are not the reviewer-facing HTML/Markdoc plan-review surface.

## Update a registered plan

After editing a registered plan, push the updated source back through Doct:

```bash
doct-agent plans update \
  --base-url https://doct.nodaste.com \
  --id <document-id> \
  --workspace-id <workspace-id> \
  --file thoughts/plans/<plan>.<html|markdoc> \
  --source-format <html|markdoc> \
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
  --file thoughts/plans/<plan>.<html|markdoc> \
  --json
```

Use background processing for the watcher when it is needed. Do not block the conversation on it. `plans watch` is source-sync/debug infrastructure only; it is not the correctness-critical comment listener and does not replace the listener startup gate above.

## Monitor and process plan comments/actions

Use Doct plan listener and queue commands, not the legacy `plan-review agent next` flow.

The normal path is the durable listener started immediately after registration. Use queue inspection and one-shot claims for startup drain, recovery, or manual processing.

Inspect pending work:

```bash
doct-agent plans queue list \
  --base-url https://doct.nodaste.com \
  --workspace-id <workspace-id> \
  --document-id <document-id> \
  --json
```

Claim the next applicable item for this agent during drain/recovery:

```bash
doct-agent plans agent next \
  --base-url https://doct.nodaste.com \
  --workspace-id <workspace-id> \
  --document-id <document-id> \
  --no-wait \
  --json
```

For cross-document adapter workers, use `--all` only when that worker is intentionally responsible for all active plan comments/actions in the workspace.

A listener-delivered or manually claimed item should provide a thread id, claim id, reviewer context, action metadata, selected node/selector context, and returned ack/resolve/release commands. Process one claim at a time:

1. Read the full local plan file and, if needed, `doct-agent plans show --id <document-id> --json`.
2. Use the selected node ID, selector, heading path, quoted text, and reviewer body.
3. Classify the item as `READINESS_BLOCKER`, `PRODUCT_QUESTION`, `OPTIONAL_CLARITY`, `OUT_OF_SCOPE_FOLLOW_UP`, `DISAGREE_REPO_EVIDENCE`, `EXECUTION_READY_REQUEST`, or `BUILD_REQUEST`.
4. Make the smallest plan change that addresses in-scope feedback without widening scope.
5. Update Doct with `doct-agent plans update` after edits.
6. Add a visible reply when useful:
   ```bash
   doct-agent plans reply \
     --base-url https://doct.nodaste.com \
     --document-id <document-id> \
     --workspace-id <workspace-id> \
     --thread-id <thread-id> \
     --body "Updated the plan." \
     --json
   ```
7. Ack when the item has been incorporated or deliberately dispositioned:
   ```bash
   doct-agent plans ack \
     --base-url https://doct.nodaste.com \
     --workspace-id <workspace-id> \
     --thread-id <thread-id> \
     --claim-id <claim-id> \
     --summary "Integrated reviewer feedback on phase boundaries" \
     --json
   ```
8. Resolve only when the reviewer-visible issue is complete:
   ```bash
   doct-agent plans resolve \
     --base-url https://doct.nodaste.com \
     --workspace-id <workspace-id> \
     --thread-id <thread-id> \
     --claim-id <claim-id> \
     --summary "Plan now includes the missing verification gate" \
     --json
   ```

If you cannot act before the claim should be released:

```bash
doct-agent plans release \
  --base-url https://doct.nodaste.com \
  --workspace-id <workspace-id> \
  --thread-id <thread-id> \
  --claim-id <claim-id> \
  --reason "Cannot complete before handoff" \
  --json
```

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

Registration should leave the board assignment at the service default, normally `backlog`. Do not move a newly registered plan to `in_progress` as part of browser-review setup. Execution workflows such as `run-plan` own the transition to `in_progress` when implementation actually starts.

## Legacy local plan-review service

Use the old local `plan-review` CLI/service only when the user explicitly asks for the legacy local reviewer, a repo still mandates it, or you are migrating an existing local registration. In that case, follow the repo-local legacy instructions. Do not present local-service URLs as the default plan review surface.

## Decision rules

- One tool: `doct-agent`. Reads and discovery are safe to run freely.
- Production plan registration defaults to `https://doct.nodaste.com`; develop is opt-in.
- Confirm before create / replace-body / delete / move on documents you did not create, and before publishing into shared workspaces.
- `doct-agent triage` is read-only operational triage (DB checks and Railway logs) — use it to inspect state, not to mutate.
- For registered plans, listener startup is part of registration completion. Do not tell the user to annotate a plan until the returned listener command is running or you have reported a concrete listener-start blocker.
- For visual verification inside doct, use browser automation after approval.

## References

- `references/doct-agent-commands.md` — full per-command reference, flags, and worked examples.
- `references/plan-format-listener-repair-pattern.md` — repair path for wrong text-doc plan artifacts or missing listeners.
- `references/doct-plan-comment-dispatcher-pattern.md` — durable listener/worker pattern when comments remain pending.
- `references/coding-plan-archive-audit-pattern.md` — evidence and commands for archiving completed Coding Plans.
- `doct-agent onboard` — the canonical, always-current spec from the installed CLI.
