---
name: html-plan-reviewer
description: Create, publish, and monitor HTML development plans with the local `plan-review` service. Use this skill whenever the user asks to create an HTML plan, publish/register a plan for browser review, use the HTML plan editor/reviewer, monitor plan comments, process reviewer annotations, or wire an agent workflow to plan-reviewer comments. Also use it when working with plans under `thoughts/plans/*.html` that should be served at `http://mbp.braid-python.ts.net:4317/` or another plan-reviewer URL.
---

# HTML Plan Reviewer Workflow

Use this skill to turn agent-authored HTML plans into reviewable browser artifacts, publish them to the local `plan-review` daemon, and monitor reviewer comments until they are acknowledged or resolved.

## Service assumptions

The tool is the Homebrew-installed `plan-review` CLI from the standalone `Nodaste-Lab/plan-reviewer` repository. `ai-configs` only owns this workflow skill; it no longer vendors the daemon, CLI, or Homebrew formula.

This skill is the source of truth for service mechanics: CLI commands, canonical URLs, registration metadata, source sync, queue-backed comment claiming, acking, and resolving. It is not the structural plan schema source. Use `planning-workflow` for plan structure and `reviewed-html-plan` for execution-readiness doctrine; this service records and routes readiness metadata but should not duplicate repo-specific validators or Heddle-specific contract rules.

If the daemon supports profile or contract enforcement, treat it as warning-first and repo-declared unless the target repo explicitly requires stricter behavior. Do not describe hard fail runtime enforcement here without matching service support and repo-local approval.

Default service URL on this host:

```bash
http://mbp.braid-python.ts.net:4317
```

Use that full Tailscale MagicDNS URL in all user-facing plan links. Shortnames such as `mbp`, `localhost`, and `127.0.0.1` are allowed only for private health checks or curl diagnostics, never for URLs shared with the user or browser-review handoff.

Local health check:

```bash
curl -fsS http://127.0.0.1:4317/health
```

If the service is not running, start it:

```bash
brew services start plan-reviewer
```

If it is not installed, install from the standalone `plan-reviewer` tap. If this machine previously installed the old `local/ai-configs/plan-reviewer` formula, remove that local tap install first so Homebrew does not keep launching the stale cellar service:

```bash
brew services stop plan-reviewer || true
brew uninstall local/ai-configs/plan-reviewer || brew uninstall plan-reviewer || true
brew untap local/ai-configs || true
```

Then install from the standalone tap:

```bash
brew tap Nodaste-Lab/plan-reviewer https://github.com/Nodaste-Lab/plan-reviewer.git
brew install Nodaste-Lab/plan-reviewer/plan-reviewer
brew services start plan-reviewer
```

Source and development docs live at `https://github.com/Nodaste-Lab/plan-reviewer`.

The MVP is intentionally unauthenticated. Treat `0.0.0.0:4317` as trusted-network only.

## Create an HTML plan

When asked to create a plan for this reviewer:

1. Load this skill before writing or serving any `thoughts/plans/*.html` artifact, even if a repo-local planning skill is also loaded.
2. Load the repo's planning guidance, especially `AGENTS.md` and any planning workflow skill that applies.
3. Write the plan under `thoughts/plans/<slug>.html` unless repo-local instructions say otherwise.
4. Use an HTML document, not Markdown renamed as HTML.
5. Mandatory visual baseline: use a dark-mode default theme with an explicit dark background, light foreground, readable muted text, accessible accent/link colors, and `color-scheme: dark`. Do not create light-mode HTML plans unless the user explicitly asks for a light-mode artifact.
6. Mandatory URL baseline: every plan URL shown to the user, opened in the browser, posted to Linear, or recorded in handoff must use the full Tailscale MagicDNS name, not a shortname, `localhost`, or `127.0.0.1`. On this host the canonical base is `http://mbp.braid-python.ts.net:4317/`; if using a temporary alternate port, keep the hostname and change only the port, e.g. `http://mbp.braid-python.ts.net:4318/...`.
7. Add stable `id` attributes to sections, phases, acceptance criteria, diagrams, figures, mockups, and other likely comment targets.
8. Prefer semantic HTML: `section`, `article`, `figure`, `figcaption`, headings, lists, tables, and code blocks.
9. Keep plan-authored scripts, event handlers, forms, and active embeds out of the artifact; the reviewer shell owns interactivity.
10. Keep images as relative repo assets when possible, with useful `alt`, `width`, and `height` attributes.

Important reviewer-friendly structure:

- `## Progress` or equivalent should contain the phase checkboxes.
- Each phase should have a stable wrapper ID, for example `id="phase-p1-contracts"`.
- Acceptance criteria and BDD scenarios should have stable IDs, for example `id="ac-1"` and `id="bdd-retry-timeout"`.
- Add short context near diagrams and images so comments on visual elements are meaningful to the agent.

## Publish/register a plan

From the repo that owns the plan, register with explicit execution-readiness metadata:

```bash
plan-review register thoughts/plans/<plan>.html --repo auto --branch auto --commit auto --execution-ready false
```

For machine-readable output:

```bash
plan-review register thoughts/plans/<plan>.html --repo auto --branch auto --commit auto --execution-ready false --json
```

`--execution-ready` is required by the service. Use `false` for initial browser-review registration and any pre-AI-review plan. Use `true` only after the required agent plan-review gates agree by substance that the plan is execution-ready; then re-register with `--execution-ready true --json` so the service metadata is truthful.

By default, registration live-links the local source file. The repo file is authoritative; service blobs are derived cache/history. After this succeeds, editing the HTML file should automatically sync the latest render into the already-open review page. Use `--snapshot` only when the user explicitly wants a detached historical review.

The command prints:

- `Plan ID`
- `Index URL`
- `Review URL`
- `Source sync`
- `Watch command`
- `Agent Instructions`

For JSON output, parse `planId`, `reviewUrl`, `indexUrl`, `sourceSync`, `publicationMetadata`, and `agentInstructions`. The service may return relative URLs such as `/p/<planId>`; convert them to the canonical full Tailscale URL before showing them to a user, opening a browser, or writing a handoff.

Open the review URL for browser annotation, or open the index:

```bash
plan-review index
open http://mbp.braid-python.ts.net:4317/
```

Registration normally upserts the same plan thread. Use `--new-thread` only when the user explicitly wants a fresh review thread instead of updating the existing plan.

## Monitor for comments

Registration JSON includes `agentInstructions`; treat those instructions as authoritative for the current service version. The correctness-critical listener is the queue-backed `plan-review agent next` flow, not `plan-review watch`.

Always do this immediately after registering a browser-review plan unless the user explicitly says not to monitor comments:

1. Drain already-pending comments until the command returns `"status":"empty"`:
   ```bash
   plan-review agent next <planId> --url http://mbp.braid-python.ts.net:4317 --no-wait --json
   ```
2. Start one waiting listener before continuing other work:
   ```bash
   plan-review agent next <planId> --url http://mbp.braid-python.ts.net:4317 --wait --json
   ```
3. When that listener exits successfully with a claimed comment, process and ack that exact claim before starting another listener.

`agent next --wait` atomically claims one pending `browser.comment.v1`, prints `commentId`, `claimId`, thread/conversation context, and ack/resolve guidance, then exits. Do not blindly loop successful claim commands or pre-claim multiple comments. Restart the listener only after the claimed comment has been processed and acknowledged.

### Pi monitor pattern

Use the Pi `process` tool for the waiting listener so the main conversation can continue:

```bash
plan-review agent next <planId> --url http://mbp.braid-python.ts.net:4317 --wait --json
```

Set success alerts on the background process. A successful exit means a comment was claimed and must be processed/acked; after acking it, start a fresh listener. A failure before a claim can normally be restarted because queue state and claim leases remain authoritative.

### Codex monitor pattern

Codex should start `agent next --wait` in a PTY session, not `watch`, when the user wants live monitoring:

```bash
plan-review agent next <planId> --url http://mbp.braid-python.ts.net:4317 --wait --json
```

Use `yield_time_ms: 1000` so the tool returns a `session_id`. When the command exits with a claim payload, process/ack it, then start the next `agent next --wait` command. Before sending a final answer, stop the listener or move monitoring to a durable handoff.

If monitoring needs to outlive the agent turn, use the durable command returned in `agentInstructions`, with the canonical service URL added when required by the payload.

### Debug-only watch stream

`plan-review watch` is useful for low-latency diagnostics, but it is not the correctness-critical delivery path. Use it only as an optional debug stream:

```bash
plan-review watch <planId> --url http://mbp.braid-python.ts.net:4317 --mode queue --format browser-comment --json
```

Fallback polling/queue snapshot:

```bash
plan-review queue list --url http://mbp.braid-python.ts.net:4317 --plan-id <planId> --json
```

For adapter workers that intentionally claim across active documents, use the service-supported all-plan form instead of pre-enumerating plans:

```bash
plan-review agent next --all --adapter <adapter> --url http://mbp.braid-python.ts.net:4317 --wait --json
```

## Process comment queue

Comments are at-least-once. The safe agent loop is claim -> inspect/apply -> optionally append a visible reply -> ack -> optionally resolve. `ack` and `resolve` are lifecycle metadata; use `reply` when the reviewer should see an agent response in the thread.

Prefer the `commentId`, `claimId`, and ack guidance returned by `plan-review agent next`. Manual queue commands remain useful for recovery or inspection.

Claim one pending comment manually:

```bash
plan-review queue claim <planId> --url http://mbp.braid-python.ts.net:4317 --one --json
```

Claim multiple comments manually only when you are prepared to process each claim before its lease expires:

```bash
plan-review queue claim <planId> --url http://mbp.braid-python.ts.net:4317 --limit 5 --json
```

Acknowledge after incorporating or explicitly deciding on the comment:

```bash
plan-review ack <commentId> \
  --url http://mbp.braid-python.ts.net:4317 \
  --claim <claimId> \
  --note "Updated the plan" \
  --summary "Integrated reviewer feedback on phase boundaries" \
  --changed-files thoughts/plans/<plan>.html \
  --json
```

Append a visible agent reply when useful for reviewer-facing conversation history:

```bash
plan-review reply <commentId> \
  --url http://mbp.braid-python.ts.net:4317 \
  --claim <claimId> \
  --body "Updated the document." \
  --json
```

Resolve when the reviewer-visible issue is complete:

```bash
plan-review resolve <commentId> \
  --url http://mbp.braid-python.ts.net:4317 \
  --note "Done" \
  --summary "Plan now includes the missing verification gate" \
  --changed-files thoughts/plans/<plan>.html \
  --json
```

If you cannot act on a claimed comment before the lease expires, release it with the active claim ID:

```bash
plan-review release <commentId> --url http://mbp.braid-python.ts.net:4317 --claim <claimId> --reason "Cannot complete before lease expiry" --json
```

Direct `ack` without a matching active claim can return `409 claim_required`; claim first unless you already have the claim ID from the event payload.

## Responding to reviewer annotations

For each comment:

1. Read the full plan file before editing.
2. Use the annotation context: selected DOM node, heading path, quoted text, image anchor, and reviewer note.
3. Decide whether the comment is a blocker, clarification, or optional suggestion.
4. Make the smallest plan change that addresses the comment without widening scope.
5. If `Source sync: active` was reported, save the file and let the service sync/reload the browser view; otherwise re-register manually.
6. Append a visible `plan-review reply` when the reviewer needs to see the response in the browser thread.
7. Ack with a concise summary and changed files.
8. Resolve only when the comment is fully addressed, not merely seen.

If the plan was registered with `--snapshot`, or if source sync reports a failure, re-register manually after edits, preserving truthful execution-readiness metadata:

```bash
plan-review register thoughts/plans/<plan>.html --repo auto --branch auto --commit auto --execution-ready false --json
```

Keep append-only decision/deviation logs intact when regenerating a plan. Do not delete reviewer-relevant history unless the user explicitly asks.

## Quick command sequence

```bash
# 1. Verify service
curl -fsS http://127.0.0.1:4317/health

# 2. Register plan with required readiness metadata
plan-review register thoughts/plans/<plan>.html --repo auto --branch auto --commit auto --execution-ready false --json

# 3. Share/open the canonical review UI
open http://mbp.braid-python.ts.net:4317/p/<planId>

# 4. Drain pending comments, then start the primary listener
plan-review agent next <planId> --url http://mbp.braid-python.ts.net:4317 --no-wait --json
plan-review agent next <planId> --url http://mbp.braid-python.ts.net:4317 --wait --json

# 5. Process the returned claim, optionally reply visibly, then ack/resolve
plan-review reply <commentId> --url http://mbp.braid-python.ts.net:4317 --claim <claimId> --body "Updated the document." --json
plan-review ack <commentId> --url http://mbp.braid-python.ts.net:4317 --claim <claimId> --note "Handled" --summary "Updated the plan" --changed-files thoughts/plans/<plan>.html --json
plan-review resolve <commentId> --url http://mbp.braid-python.ts.net:4317 --note "Resolved" --summary "Reviewer feedback addressed" --changed-files thoughts/plans/<plan>.html --json
```
