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
| Initialize a plan source | HTML plans are handcrafted (no `plans init` source scaffolding); author the semantic HTML directly |
| Register an HTML plan | `doct-agent plans register --base-url https://doct.nodaste.com --file thoughts/plans/<plan>.html --source-format html --allow-untemplated --title '<Plan Title>' --json` |
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

## Publish Markdown/text plans

Use this path only when the user explicitly asks for Markdown/text/no comments or repo guidance forbids HTML for the workflow.

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

Return the created/updated Doct URL, document id, workspace id, and status. State clearly that Markdown/text documents are not the reviewer-facing HTML plan-review surface.

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
