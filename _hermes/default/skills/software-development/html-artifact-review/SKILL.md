---
name: html-artifact-review
description: Evaluate, design, or extend Doct-backed HTML/Markdoc artifact review workflows where agents publish HTML documents/plans, users comment on DOM/text/image selections, and agents inspect queues, reply, ack, resolve, and update artifacts. Prefer Doct/doct-agent over the legacy local plan-review service unless explicitly requested.
version: 2.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [html, artifacts, review, comments, agents, hermes, doct, markdoc]
    related_skills: [doct-document-ops, doct-agent-cli]
---

# HTML Artifact Review

Use this skill when the user asks whether Hermes or another agent system can host HTML artifacts for browser review, receive DOM/text/image-anchored comments, subscribe to those comments, reply inline, or update documents through the review surface.

## Default backend

Use **Doct production** and the `doct-agent` CLI by default:

```bash
https://doct.nodaste.com
doct-agent auth status --all --json
doct-agent context --base-url https://doct.nodaste.com --json
```

Do not use the legacy local `plan-review` daemon, loopback URLs, or Tailscale local-service URLs unless Aaron explicitly asks for the legacy local reviewer or a repo mandates it.

## Core pattern

A robust agent-review surface has five layers:

1. **Artifact publication** — the agent writes a source artifact and registers it in Doct with a stable canonical URL.
2. **Safe render shell** — Doct owns review interactivity; artifact-authored scripts/forms are not trusted by default.
3. **Precise anchors** — comments capture stable DOM IDs/selectors, text ranges, image anchors, heading paths, and reviewer context.
4. **Durable queue** — comments/actions are server-side work items with claim, reply, ack, release, resolve, lifecycle, and board/status surfaces.
5. **Agent update loop** — the agent claims one item, updates the source artifact, pushes the update to Doct, replies visibly when useful, then acks/resolves.

## Current commands

For reviewer-facing HTML plans or plan-like HTML documents, load `doct-document-ops` and use:

```bash
doct-agent plans register --base-url https://doct.nodaste.com --file thoughts/plans/<plan>.html --source-format html --allow-untemplated --json
doct-agent plans register --base-url https://doct.nodaste.com --file thoughts/plans/<plan>.markdoc --source-format markdoc --json
doct-agent plans update --base-url https://doct.nodaste.com --id <document-id> --workspace-id <workspace-id> --file <source> --source-format <html|markdoc> --expected-version <version> --json
doct-agent plans queue list --base-url https://doct.nodaste.com --workspace-id <workspace-id> --document-id <document-id> --json
doct-agent plans agent next --base-url https://doct.nodaste.com --workspace-id <workspace-id> --document-id <document-id> --json
doct-agent plans reply --base-url https://doct.nodaste.com --document-id <document-id> --workspace-id <workspace-id> --thread-id <thread-id> --body "Updated the document." --json
doct-agent plans ack --base-url https://doct.nodaste.com --workspace-id <workspace-id> --thread-id <thread-id> --claim-id <claim-id> --summary "Handled" --json
doct-agent plans resolve --base-url https://doct.nodaste.com --workspace-id <workspace-id> --thread-id <thread-id> --claim-id <claim-id> --summary "Resolved" --json
```

For ordinary Doct text documents, load `doct-agent-cli` / `doct-document-ops` and use `documents create`, `documents replace-body`, `collab anchored`, and `collab comments` commands rather than registering them as coding plans.

## HTML / Markdoc authoring rules

- Prefer repo-local `thoughts/plans/<slug>.markdoc` when the repo defines a Markdoc plan source; the generated/reviewed HTML is not the editable source.
- For handcrafted HTML, use semantic HTML with stable `id` attributes on likely comment targets.
- Use a dark-mode, full-width single-column reviewer layout unless the user asks otherwise.
- Put a concise table of contents near the top for plan-like artifacts.
- Keep active scripts, event handlers, forms, and untrusted embeds out of review artifacts.
- Share only canonical Doct URLs from `https://doct.nodaste.com`.

## Pitfalls

- Do not describe “hosting HTML” as the hard part. The valuable substrate is anchored feedback plus reliable agent delivery and source updates.
- Do not use `documents publish-plan` for current HTML/Markdoc planning; current onboarding says it fails closed with replacement guidance.
- Do not claim a plan/document is updated in Doct until `doct-agent plans update` or the relevant Doct document command returns successfully.
- Do not process multiple claimed comments in parallel unless the worker is explicitly designed for that queue scope.
- Do not fork a local plan-review workflow when Doct already provides the required registration, queue, reply, ack, resolve, lifecycle, and board surfaces.
