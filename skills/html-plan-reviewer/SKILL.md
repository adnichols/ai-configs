---
name: html-plan-reviewer
description: Create, register, update, and monitor HTML development plans in Doct using `doct-agent plans` against `https://doct.nodaste.com`. Use this skill whenever the user asks to create an HTML plan, publish/register a plan for browser review, use the plan review workflow, monitor plan comments/actions, process reviewer annotations, or wire an agent workflow to registered plan comments. After registration, start the returned durable Doct listener unless explicitly doing registration-only work. Prefer this Doct-backed flow over the legacy local `plan-review` service unless the user explicitly asks for that legacy service.
---

# HTML Plan Reviewer Workflow

Use this skill to turn agent-authored HTML plans into reviewable Doct plan artifacts, register them through `doct-agent`, start the returned queue-backed listener, and process reviewer comments/actions until they are acknowledged or resolved.

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

## Create an HTML plan

When asked to create a plan for browser review:

1. Load this skill before writing, registering, linking, or monitoring any `thoughts/plans/*.html` artifact.
2. Load repo planning guidance, especially root `AGENTS.md`, product-intent docs, and any repo-local planning overrides.
3. Write the plan under `thoughts/plans/<slug>.html` unless repo-local instructions or the user supplied another active plan path.
4. Use a real HTML document, not Markdown renamed as HTML.
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

From the repo that owns the plan, register with `doct-agent plans register`:

```bash
doct-agent plans register \
  --base-url https://doct.nodaste.com \
  --file thoughts/plans/<plan>.html \
  --source-format html \
  --allow-untemplated \
  --json
```

Add `--title '<Plan Title>'`, `--workspace <workspace-slug-or-id>`, `--workspace-id <id>`, `--path '<path>'`, or `--parent-id <id>` only when repo guidance or the user specifies a destination. Otherwise use the CLI defaults. Use `--allow-untemplated` for the handcrafted HTML plans this workflow normally produces; omit it only when using a Doct plan template/config that the CLI recognizes.

Parse the JSON and preserve the returned identifiers in the handoff or working notes. Field names may evolve, so inspect the payload, but capture at least:

- Doct document/plan id,
- workspace id,
- current source/version or expected-version value when returned,
- canonical Doct URL,
- the full returned `listenerInstructions` object, including `startCommand`, `preferredCommand`, `drainCommand`, lifecycle/board commands, ack/resolve guidance, and processing-loop requirements.

Show the user the canonical Doct URL from the registration response. If a command returns a relative path, resolve it against `https://doct.nodaste.com` before sharing it. Do not share `localhost`, local `plan-review` URLs, or Tailscale local-service URLs for the default flow.

Registration creates or updates the Doct review artifact. The repo file remains the source artifact for implementation; Doct is the review/registration surface.

### Immediately start the returned listener

A registered plan is not ready for browser review handoff until the comment listener is running, unless the user explicitly asked for registration only. The `plans register` JSON returns `listenerInstructions`; treat those instructions as the live contract, because field names and preferred delivery commands can evolve.

After registration:

1. Run the returned `lifecycleCommand`, or equivalent `doct-agent plans lifecycle --state active`, before draining/listening.
2. Leave the plan in its registration/default board column, normally `backlog`, unless the user explicitly requested a board move. Registration and browser-review handoff do not mean implementation is underway.
3. Drain pending work with the returned `drainCommand` (`doct-agent plans agent next ... --no-wait --json`) until it returns `status: "empty"`.
4. Start the durable listener with the harness background-process tool. Prefer `listenerInstructions.startCommand` when present (`doct-agent plans listen ... --jsonl`); otherwise use the returned `preferredCommand`/`durableCommand`. Name the process with the plan/document id and add a log watch for `plan_comment_dispatch` when the harness supports it.
5. Do not process claims inline inside the listener. When a listener event or `agent next --wait` result claims a browser comment, dispatch the claim payload and returned commands to a sub-agent or a clearly separate worker step, then keep or restart the listener.
6. Keep the listener running until the plan is complete, no longer active, or the user explicitly stops review. If the listener cannot be started, report that as a handoff blocker before telling the user to annotate the plan.

Pi `process` example:

```bash
doct-agent plans listen \
  --base-url https://doct.nodaste.com \
  --workspace-id <workspace-id> \
  --document-id <document-id> \
  --jsonl
```

Use the exact command returned by `listenerInstructions` when it differs from this example.

## Update an already registered plan

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

For continuous source sync while a reviewer is actively annotating a local source file, use the Doct watcher with the Pi `process` tool:

```bash
doct-agent plans watch \
  --base-url https://doct.nodaste.com \
  --id <document-id> \
  --workspace-id <workspace-id> \
  --file thoughts/plans/<plan>.html \
  --json
```

Use background processing for the watcher; do not block the conversation on it. `plans watch` is source-sync/debug infrastructure only. It is not the correctness-critical comment listener and does not replace the listener startup gate above.

## Monitor and process comments/actions

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

## Quick command sequence

```bash
# 1. Confirm endpoint/auth
doct-agent auth status --all --json
doct-agent context --base-url https://doct.nodaste.com --json

# 2. Register the HTML plan in Doct
doct-agent plans register --base-url https://doct.nodaste.com --file thoughts/plans/<plan>.html --source-format html --allow-untemplated --json

# 3. Activate, drain, and start the returned listener before handoff
doct-agent plans lifecycle --base-url https://doct.nodaste.com --workspace-id <workspace-id> --document-id <document-id> --state active --json
doct-agent plans agent next --base-url https://doct.nodaste.com --workspace-id <workspace-id> --document-id <document-id> --no-wait --json
doct-agent plans listen --base-url https://doct.nodaste.com --workspace-id <workspace-id> --document-id <document-id> --jsonl

# 4. After edits, update the registered plan
doct-agent plans update --base-url https://doct.nodaste.com --id <document-id> --workspace-id <workspace-id> --file thoughts/plans/<plan>.html --source-format html --expected-version <version> --json

# 5. Inspect and claim reviewer work during recovery/manual processing
doct-agent plans queue list --base-url https://doct.nodaste.com --workspace-id <workspace-id> --document-id <document-id> --json
doct-agent plans agent next --base-url https://doct.nodaste.com --workspace-id <workspace-id> --document-id <document-id> --no-wait --json

# 6. Reply, ack, and resolve the returned thread/claim
doct-agent plans reply --base-url https://doct.nodaste.com --document-id <document-id> --workspace-id <workspace-id> --thread-id <thread-id> --body "Updated the plan." --json
doct-agent plans ack --base-url https://doct.nodaste.com --workspace-id <workspace-id> --thread-id <thread-id> --claim-id <claim-id> --summary "Handled" --json
doct-agent plans resolve --base-url https://doct.nodaste.com --workspace-id <workspace-id> --thread-id <thread-id> --claim-id <claim-id> --summary "Resolved" --json
```
