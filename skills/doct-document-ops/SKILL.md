---
name: doct-document-ops
description: Interact with doct through the doct-agent CLI. Use when asked to open a doct URL, list doct workspaces or documents, view/create/edit doct documents, update metadata, rename/move/delete, add or inspect comments, create/register/update/monitor HTML, Markdoc, or Markdown coding plans in Doct, publish plans for browser review, or run read-only doct DB/log triage. For reviewer-facing plans, automatically activate the plan, process already-routed queue items, and start the returned durable comment listener without waiting for a separate request. Keep pre-execution listener ownership until execution moves the plan to `in_progress` (or an explicitly configured equivalent), restarting it when necessary; supervise it using the current host's real wake mechanism and state any limitation truthfully. Use text-document publishing only when Markdown/text is explicitly requested.
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
| Initialize a plan source | `doct-agent plans init --output thoughts/plans/<plan>.markdoc [--template <template>] [--plan-config <file>] --json` |
| Register an HTML plan | `doct-agent plans register --base-url https://doct.nodaste.com --file thoughts/plans/<plan>.html --source-format html --allow-untemplated --json` |
| Register a Markdoc plan | `doct-agent plans register --base-url https://doct.nodaste.com --file thoughts/plans/<plan>.markdoc --source-format markdoc --json` |
| Update a registered plan | `doct-agent plans update --id <document-id> --workspace-id <workspace-id> --file thoughts/plans/<plan>.html --source-format html --expected-version <version> --json` |
| Show a registered plan | `doct-agent plans show --id <document-id> --json` |
| Watch/sync a plan source file | `doct-agent plans watch --id <document-id> --workspace-id <workspace-id> --file thoughts/plans/<plan>.html --json` |
| Start durable plan comment listener | `doct-agent plans listen --workspace-id <workspace-id> --document-id <document-id> --jsonl` |
| Inspect plan queue | `doct-agent plans queue list --workspace-id <workspace-id> --document-id <document-id> --json` |
| Drain / claim next plan item | `doct-agent plans agent next --workspace-id <workspace-id> --document-id <document-id> --no-wait --json`; reserve `--wait` for explicit diagnostics or one-shot recovery only |
| Reply / ack / resolve / release plan item | `doct-agent plans <reply\|ack\|resolve\|release> ... --thread-id <thread-id> --claim-id <claim-id> --json` |
| Plan notes / columns / lifecycle / board / readiness | `doct-agent plans notes ...`; `doct-agent plans columns ...`; `doct-agent plans lifecycle --document-id <id> --workspace-id <id> --state active --json`; `doct-agent plans board list|set ...`; `doct-agent plans metadata --execution-ready true|false ...` |
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
- the returned `listenerInstructions` object, especially `listenerCommand` (`doct-agent plans listen ... --jsonl`) and any source/version metadata returned for local tracking.

Show the user the canonical Doct URL from the registration response. If a command returns a relative path, resolve it against `https://doct.nodaste.com` before sharing it. Do not share `localhost`, local `plan-review` URLs, or Tailscale local-service URLs for the default flow.

Registration creates or updates the Doct review artifact. The repo file remains the source artifact for implementation; Doct is the review/registration surface.

## Start and supervise the comment worker automatically

A registered reviewer-facing plan is not ready for browser-review handoff until existing routed work has been processed and the durable comment listener is both running and observable by the supervising agent. Do this automatically after registration or a monitoring handoff; do not wait for the user to separately ask you to start the listener. The exceptions are an explicit registration-only request or a host that cannot provide a safe wake path, which must be reported precisely.

Treat the returned `listenerInstructions.listenerCommand` as the live command contract. The CLI listener claims/dequeues routed items and emits one JSONL `plan_comment_dispatch` per claim; it does not edit the plan or acknowledge/resolve the claim for you.

After registration:

1. Run `doct-agent plans lifecycle --state active` before draining/listening when lifecycle is not already active.
2. Leave the plan in its registration/default board column, normally `backlog`, unless the user explicitly requested a board move. Registration and browser-review handoff do not mean implementation is underway.
3. Drain existing routed work with `doct-agent plans agent next ... --no-wait --json`. If the response contains a claim, process that claim immediately, then call `agent next --no-wait` again. Stop only on the CLI's empty envelope. Never use a blind shell loop that discards claimed JSON; a claim that is dequeued but not handled remains leased and can be hidden until redelivery.
4. Start the exact returned `listenerInstructions.listenerCommand` (`doct-agent plans listen ... --jsonl`) using the host-specific supervision path below. This durable listener uses bounded request timeouts and retries transient 408/429/5xx responses.
5. Verify both halves before browser handoff: the process is alive, and every emitted `plan_comment_dispatch` can re-activate or remain connected to the agent that will handle it. A running PID alone is insufficient.
6. When the listener emits a dispatch, treat that event as the already-claimed work item. Process exactly that claim, then reply/ack/resolve/release with the returned identifiers and commands. Do not call `agent next` to re-claim the same event. Keep the listener running for later work.
7. A routed work item is created by the browser's agent action or by `doct-agent plans comments add --submit-action agent ...`. Ordinary conversation comments use `submitAction: "conversation"`, return `queueState: "none"`, and intentionally do not wake the listener.
8. If a claim cannot be completed before its lease expires, release it with a reason. Do not let a listener silently accumulate claimed-but-unhandled work.

### Host supervision matrix

- **Codex desktop/app:** Start the listener with a persistent `exec_command`/terminal session and capture its session id. Keep the plan-review task active; wait for output with `write_stdin` (or the equivalent terminal poll), process each dispatch immediately, and periodically inspect `doct-agent plans board list` for this document's assignment. Do not return a final handoff while Codex owns pre-execution monitoring. If a native recurring automation or thread-wake tool is available and the requested monitoring scope authorizes it, that may carry the same watchdog responsibility without holding the interactive turn open. A background exec process alone does **not** prove that Codex will start a new turn after the current task returns.
- **Pi:** Start the listener through `process` with `alertOnFailure: true`, `alertOnKill: true`, and `logWatches: [{"pattern":"\\\"type\\\":\\\"plan_comment_dispatch\\\"","stream":"stdout","repeat":true}]`. The repeating watch wakes Pi for every dispatch; the failure/kill alerts create recovery turns.
- **Other wake-capable harnesses:** Use their durable background-process primitive plus a repeating stdout match for `"type":"plan_comment_dispatch"`, and alerts for listener exit/failure.
- **Terminal-only agents (including Claude Code sessions without a wake hook):** A detached PID or `nohup` is not autonomous supervision. Keep the interactive task attached and polling, install an explicitly authorized scheduler/worker, or report `LISTENER_WAKE_UNAVAILABLE`.

### Pre-execution ownership and stop condition

The agent that publishes or opens the plan for browser review owns the pre-execution listener until one of these observable conditions occurs:

1. An execution workflow moves the exact document to the visible `in_progress` board column, or repo/service configuration explicitly identifies an equivalent execution-start column.
2. The plan lifecycle is no longer `active`, the document is deleted/archived, or the listener exits because target validation is no longer valid.
3. The user explicitly cancels monitoring or requested registration-only work.

For Codex, treat this as an ongoing-task terminal condition:

1. Keep the listener exec session attached and poll it for dispatches.
2. Periodically run `doct-agent plans board list --workspace-id <workspace-id> --json` and locate the exact document card; do not infer execution from a local progress checkbox.
3. If the listener exits before an ownership boundary, inspect lifecycle/auth/board state and restart the exact registration-provided command automatically when the plan is still active and pre-execution.
4. When `in_progress` is observed, finish or release any current claim, drain the exact document queue once, interrupt the pre-execution listener cleanly, and report that listener ownership passed to the execution workflow.
5. When a Codex task is resumed after interruption, inspect board state, lifecycle, queue, and listener health first; restart monitoring automatically if the plan is still active and not yet `in_progress`.

If the listener command itself cannot start or fails lifecycle/auth/scope validation, report `LISTENER_START_BLOCKED`. If the user requires the Codex task to return before execution begins and no native automation/thread-wake path exists, report `LISTENER_WAKE_UNAVAILABLE` rather than pretending a detached listener is sufficient. Queue inspection and manual claims are recovery paths, not evidence of durable supervision.

Durable listener example:

```bash
doct-agent plans listen \
  --base-url https://doct.nodaste.com \
  --workspace-id <workspace-id> \
  --document-id <document-id> \
  --jsonl
```

Use the exact `listenerInstructions.listenerCommand` returned by registration when it differs from this example.

`plans agent next --wait --json` is a one-shot diagnostic/recovery path only. It depends on the HTTP request staying open until the server-side wait deadline and is more vulnerable to platform/proxy timeouts than `plans listen --jsonl`. `plans watch` is only source sync/debug visibility and does not replace the comment listener.

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

The normal path is automatic startup drain followed by the durable listener immediately after registration. Use queue inspection and one-shot claims for startup drain, recovery, or manual processing; do not wait for a second user prompt before performing the startup drain.

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

A listener-delivered or manually claimed item should provide a thread id, claim id, reviewer context, action metadata, selected node/selector context, and returned ack/resolve/release commands. A listener event is already claimed; a manual drain response is the claim. Process one claim at a time:

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
- For registered plans, startup drain and listener startup happen automatically as part of registration completion. Keep pre-execution ownership until the plan enters `in_progress`, its lifecycle ends, or the user cancels. Do not wait for a separate request, and do not tell the user to annotate a plan until supervision is verified or you have reported `LISTENER_START_BLOCKED` / `LISTENER_WAKE_UNAVAILABLE` accurately.
- For visual verification inside doct, use browser automation after approval.

## References

- `references/doct-agent-commands.md` — full per-command reference, flags, and worked examples.
- `references/plan-format-listener-repair-pattern.md` — repair path for wrong text-doc plan artifacts or missing listeners.
- `references/doct-plan-comment-dispatcher-pattern.md` — durable listener/worker pattern when comments remain pending.
- `references/coding-plan-archive-audit-pattern.md` — evidence and commands for archiving completed Coding Plans.
- `doct-agent onboard` — the canonical, always-current spec from the installed CLI.
