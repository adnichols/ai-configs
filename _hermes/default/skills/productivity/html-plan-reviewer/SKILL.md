---
name: html-plan-reviewer
description: Create, register, update, and monitor Aaron-facing HTML or Markdoc development plans in Doct using `doct-agent plans` against `https://doct.nodaste.com`. Use whenever Aaron asks to create/post/publish a plan, even if he does not say HTML; register the plan, start/verify the comment listener, and process reviewer annotations. Prefer this Doct-backed flow over text docs or the legacy local `plan-review` service unless explicitly overridden.
---

# HTML Plan Reviewer Workflow

Use this skill to turn agent-authored HTML or Markdoc plans into reviewable Doct plan artifacts, register them through `doct-agent`, and process reviewer comments/actions until they are acknowledged or resolved.

## Default backend

The default plan-review backend is **Doct production**:

```bash
https://doct.nodaste.com
```

Use `doct-agent` for every plan registration, update, comment, queue, board, or lifecycle operation. Do **not** use the legacy local `plan-review` CLI/service unless the user explicitly asks for a local/legacy plan-reviewer flow.

Before mutating anything, confirm auth and endpoint:

```bash
doct-agent auth status --all --json
doct-agent context --base-url https://doct.nodaste.com --json
```

If production is authenticated but not default, either pass `--base-url https://doct.nodaste.com` on every command or set it explicitly:

```bash
doct-agent auth default --base-url https://doct.nodaste.com
```

If not authenticated, follow `doct-document-ops`: ask the doct owner for a selected-agent enrollment code, then run:

```bash
doct-agent auth login --base-url https://doct.nodaste.com
```

## Create an HTML or Markdoc plan

When Aaron asks to create/post/publish a plan, treat it as a request for a browser-reviewable, commentable Doct plan by default even if he does not explicitly say “HTML”. Do not publish a Markdown/text Doct document for an Aaron-facing implementation plan unless he explicitly asks for that non-reviewable format.

1. Load this skill before writing, registering, linking, updating, or monitoring any implementation/development plan for Aaron, including `thoughts/plans/*.html` or `thoughts/plans/*.markdoc` artifacts.
2. Load repo planning guidance, especially root `AGENTS.md`, product-intent docs, and any repo-local planning overrides.
3. Prefer `thoughts/plans/<slug>.markdoc` when repo guidance defines Markdoc as the editable source. Use `thoughts/plans/<slug>.html` for handcrafted HTML plans, legacy/raw HTML plans, or when repo guidance is absent/ambiguous. For standalone/non-repo planning, write a temporary handcrafted HTML source and still register it through Doct.
4. Do not create Markdown-only plans for reviewer-facing work unless the user explicitly asks for Markdown. Markdoc is the compact source format; HTML is the rendered/review surface for handcrafted or generated artifacts.
5. Use a dark-mode default theme: explicit dark background, light foreground, readable muted text, accessible accent/link colors, and `color-scheme: dark`.
6. Use a full-width single-column reviewer layout. Put a concise table of contents near the top after the title/status summary and before the main plan sections. Format the ToC as responsive columns; do not reserve a permanent left sidebar.
7. Add stable `id` attributes to sections, phases, acceptance criteria, BDD scenarios, diagrams, figures, mockups, and likely comment targets. Doct comments on HTML plans are node/selector based, so stable IDs are part of the review contract.
8. Prefer semantic HTML: `section`, `article`, `figure`, `figcaption`, headings, lists, tables, and code blocks.
9. Keep plan-authored scripts, event handlers, forms, and active embeds out of the artifact; Doct owns review interactivity.
10. Keep images as relative repo assets when possible, with useful `alt`, `width`, and `height` attributes.

Reviewer-friendly structure:

- `Progress` contains the phase checkboxes.
- The top table of contents links to every major plan section and each phase.
- Each phase has a stable wrapper ID, for example `id="phase-p1-contracts"`.
- Acceptance criteria and BDD scenarios have stable IDs, for example `id="ac-1"` and `id="bdd-retry-timeout"`.
- Add short context near diagrams and images so comments on visual elements are meaningful to the agent.

## Register a plan in Doct

From the repo that owns the plan, register with `doct-agent plans register`. For Markdoc source:

```bash
doct-agent plans register \
  --base-url https://doct.nodaste.com \
  --file thoughts/plans/<plan>.markdoc \
  --source-format markdoc \
  --json
```

For handcrafted or legacy HTML source:

```bash
doct-agent plans register \
  --base-url https://doct.nodaste.com \
  --file thoughts/plans/<plan>.html \
  --source-format html \
  --allow-untemplated \
  --json
```

Add `--title '<Plan Title>'`, `--workspace <workspace-slug-or-id>`, `--workspace-id <id>`, `--path '<path>'`, or `--parent-id <id>` only when repo guidance or the user specifies a destination. Otherwise use the CLI defaults. Use `--allow-untemplated` for handcrafted HTML plans. Do not use it for normal Markdoc template/config-backed plans unless the CLI or repo guidance says the plan is intentionally untemplated.

Parse the JSON and preserve the returned identifiers in the handoff or working notes. Field names may evolve, so inspect the payload, but capture at least:

- Doct document/plan id,
- workspace id,
- current source/version or expected-version value when returned,
- canonical Doct URL,
- any returned watch, agent, or reviewer instructions.

Show the user the canonical Doct URL from the registration response. If a command returns a relative path, resolve it against `https://doct.nodaste.com` before sharing it. Do not share `localhost`, local `plan-review` URLs, or Tailscale local-service URLs for the default flow.

Registration creates or updates the Doct review artifact. The repo file remains the source artifact for implementation; Doct is the review/registration surface.

Do **not** use `doct-agent documents create`, `documents replace-body`, or any plain text-document flow for Aaron-facing implementation plans. Text documents are not the plan review surface Aaron expects and may not support the comment/annotation workflow he needs. If you accidentally create a text document for a plan, replace it by registering an HTML/Markdoc plan through `doct-agent plans register` and report the replacement URL.

## Start the comment listener / queue watcher

After every new or updated Aaron-facing plan registration, start or verify a comment listener before final response. “Listener” means an active Doct plan queue watcher/maintainer for that specific document, not merely sharing the URL.

Minimum required post-registration sequence:

1. Validate that the artifact is the HTML/Markdoc plan-review surface, not a text doc:
   ```bash
   doct-agent plans show \
     --base-url https://doct.nodaste.com \
     --id <document-id> \
     --json
   ```
   Treat success plus returned render/anchor fields such as `anchorTargets`, `renderedHtml`, `documentVersionId`, or `htmlVersionId` as the evidence that browser comments can target the plan. `doct-agent documents get` alone is not sufficient evidence.
2. Inspect pending work once:
   ```bash
   doct-agent plans queue list \
     --base-url https://doct.nodaste.com \
     --workspace-id <workspace-id> \
     --document-id <document-id> \
     --json
   ```
3. If pending comments/actions exist, claim and process them one at a time with `doct-agent plans agent next`, update the plan, reply, ack, and resolve before returning to the user.
4. If the plan is being handed to Aaron for browser comments, create or verify a durable queue-backed watcher for this document. In Hermes, prefer a self-contained recurring cron/listener that polls `doct-agent plans queue list` for the exact `<workspace-id>/<document-id>`, stays quiet when no work exists, and stops only when the plan is archived or Aaron asks to stop listening. **Do not implement a notification-only listener that marks queue items seen.** A valid listener must claim/process/reply/ack/resolve, or dispatch a bounded worker/sub-agent that does so. If the script only prints "new comment detected" and records `seen_item_keys`, it is not taking action. For Discord-delivered cron/listeners, never pass worker stdout through directly: suppress raw HTML, CSS, unified diffs, command transcripts, and plan markup from chat-facing output; store full transcripts in local logs and print only a concise Markdown/plain-text status summary.
5. If a prior wrong `documents create` text doc was shared, delete it or clearly supersede it so there is one canonical review URL. Verify the old URL no longer resolves or is no longer presented.
6. Report listener status in the final response: watcher/cron id or process id when available, plus the document id it owns. If listener setup fails, say it failed and why; do not imply comments are being watched.

`doct-agent plans watch` is a source-sync watcher for keeping a local source file and Doct registration aligned. It is useful during active editing, but by itself it is not sufficient as the comment listener unless paired with queue polling/claim processing.

Session-specific correction details and the required `ai-configs` sync sequence are captured in `references/aaron-plan-default-and-ai-configs-2026-06-30.md`; consult it when repairing plan-format/listener failures or when skill edits must persist beyond the current Hermes profile.

A condensed operational checklist for replacing a bad text-doc plan with a real Doct HTML/Markdoc plan and listener is in `references/plan-format-listener-repair-pattern.md`.

When a listener exists but comments remain pending or Aaron says it is not taking action, use `references/doct-plan-comment-dispatcher-pattern.md`. It documents the durable pattern: script-only quiet polling, lock state, bounded Hermes worker dispatch, and mandatory claim/edit/reply/ack/resolve instead of notification-only `seen_item_keys` behavior.

## Update an already registered plan

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

For continuous sync while a reviewer is actively annotating a local source file, use the Doct watcher with the Pi `process` tool:

```bash
doct-agent plans watch \
  --base-url https://doct.nodaste.com \
  --id <document-id> \
  --workspace-id <workspace-id> \
  --file thoughts/plans/<plan>.<html|markdoc> \
  --json
```

Use background processing for the watcher; do not block the conversation on it.

## Monitor and process comments/actions

Use Doct plan queue commands, not the legacy `plan-review agent next` flow.

Inspect pending work:

```bash
doct-agent plans queue list \
  --base-url https://doct.nodaste.com \
  --workspace-id <workspace-id> \
  --document-id <document-id> \
  --json
```

Claim the next applicable item for this agent:

```bash
doct-agent plans agent next \
  --base-url https://doct.nodaste.com \
  --workspace-id <workspace-id> \
  --document-id <document-id> \
  --json
```

For cross-document adapter workers, use `--all` only when that worker is intentionally responsible for all active plan comments/actions in the workspace.

A claimed item should provide a thread id, claim id, reviewer context, action metadata, and selected node/selector context. Process one claim at a time:

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

Use Doct state/board commands for registered plan status:

```bash
doct-agent plans lifecycle \
  --base-url https://doct.nodaste.com \
  --document-id <document-id> \
  --workspace-id <workspace-id> \
  --state active \
  --json

doct-agent plans board list \
  --base-url https://doct.nodaste.com \
  --workspace-id <workspace-id> \
  --json

doct-agent plans board set \
  --base-url https://doct.nodaste.com \
  --document-id <document-id> \
  --workspace-id <workspace-id> \
  --column in_progress \
  --json
```

Only set a board column that exists in the workspace. If the intended status column is absent or ambiguous, stop with an actionable status-sync blocker rather than guessing.

### Auditing and archiving completed coding plans

When Aaron asks to review Coding Plans and archive completed/PR-backed work in Doct, use the board and document tree together; neither source alone is sufficient.

1. Identify the personal workspace with `doct-agent workspaces list --base-url https://doct.nodaste.com --json`, then read both `doct-agent plans board list --workspace-id <personal>` and `doct-agent documents list --workspace-id <personal>`.
2. Locate the `Coding Plans` folder and its `Archived` child from document readback, preserving the actual `parentId`/folder id. The Archived document may have a generated path such as `coding-plans/archived-<id>.md`; use `documents move --new-parent-id <archived-id>`, not path string inference.
3. Treat a plan as safe to archive only when there is concrete evidence: registered PR metadata, a matching GitHub PR that is open or merged, checked-off/completion notes in the plan body, or it is already on Done and clearly belongs in Archived. Search GitHub by Linear key, branch, and title when PR metadata is absent. Do not archive browser-review drafts or executionReady=false plans without independent completion evidence.
4. For each confident plan, apply all three state changes and verify readback:
   - `doct-agent plans board set --column done`
   - `doct-agent plans lifecycle --state archived`
   - `doct-agent documents move --new-parent-id <archived-folder-id>`
5. Normalize already-archived/done cards whose lifecycle still says `active` by setting lifecycle to `archived`; Doct board column, folder placement, and lifecycle metadata can drift independently.
6. Watch for duplicate plan documents with the same title/path. If one is hidden/not_visible but has the same plan id or Linear key as a merged/open PR plan, archive the duplicate too only when the evidence clearly ties it to the same completed work.

Session-specific detail and examples: `references/coding-plan-archive-audit-pattern.md`.

## Legacy local plan-review service

Use the old local `plan-review` CLI/service only when the user explicitly asks for the legacy local reviewer, a repo still mandates it, or you are migrating an existing local registration. In that case, follow the repo-local legacy instructions. Do not present local-service URLs as the default plan review surface.

## Quick command sequence

```bash
# 1. Confirm endpoint/auth
doct-agent auth status --all --json
doct-agent context --base-url https://doct.nodaste.com --json

# 2. Register the Markdoc plan in Doct when available; otherwise register handcrafted HTML
doct-agent plans register --base-url https://doct.nodaste.com --file thoughts/plans/<plan>.markdoc --source-format markdoc --json
doct-agent plans register --base-url https://doct.nodaste.com --file thoughts/plans/<plan>.html --source-format html --allow-untemplated --json

# 3. After edits, update the registered plan
doct-agent plans update --base-url https://doct.nodaste.com --id <document-id> --workspace-id <workspace-id> --file thoughts/plans/<plan>.<html|markdoc> --source-format <html|markdoc> --expected-version <version> --json

# 4. Inspect and claim reviewer work
doct-agent plans queue list --base-url https://doct.nodaste.com --workspace-id <workspace-id> --document-id <document-id> --json
doct-agent plans agent next --base-url https://doct.nodaste.com --workspace-id <workspace-id> --document-id <document-id> --json

# 5. Reply, ack, and resolve the returned thread/claim
doct-agent plans reply --base-url https://doct.nodaste.com --document-id <document-id> --workspace-id <workspace-id> --thread-id <thread-id> --body "Updated the plan." --json
doct-agent plans ack --base-url https://doct.nodaste.com --workspace-id <workspace-id> --thread-id <thread-id> --claim-id <claim-id> --summary "Handled" --json
doct-agent plans resolve --base-url https://doct.nodaste.com --workspace-id <workspace-id> --thread-id <thread-id> --claim-id <claim-id> --summary "Resolved" --json
```
