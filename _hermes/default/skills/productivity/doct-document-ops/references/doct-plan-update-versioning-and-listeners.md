# Doct plan update versioning and listener payload notes

Concise operational notes captured while moving Good Morning report publishing from legacy local plan-review to Doct plans.

## Version fields

Doct plan/document payloads can expose multiple version-ish fields:

- `document.version`: integer revision used by `doct-agent plans update --expected-version`.
- `htmlVersionId`: UUID-like render/content version. Useful for identity/debugging, but not accepted by `--expected-version`.
- `documentVersionId`: UUID-like document version id. Also not the integer expected by `--expected-version`.
- `plan.listenerInstructions.htmlVersionId`: nested UUID-like HTML version returned for listener/update context.

When updating a Doct plan document, prefer:

```bash
doct-agent plans show \
  --base-url https://doct.nodaste.com \
  --id <document-id> \
  --json

# Use the integer document.version value from the show/update payload.
doct-agent plans update \
  --base-url https://doct.nodaste.com \
  --id <document-id> \
  --workspace-id <workspace-id> \
  --file <path> \
  --source-format html \
  --expected-version <document.version> \
  --json
```

Use `--force` only for intentional overwrite recovery after confirming the target document/workspace and source file.

## Listener normalization

Registration/show payloads may put the canonical review URL and listener inputs under nested `plan.listenerInstructions` rather than top-level `reviewUrl` / `workspaceId` / `documentId` fields. Normalizers should inspect both top-level fields and nested `listenerInstructions` before declaring registration incomplete.

## Idle waits

`doct-agent plans agent next --wait --json` can exit non-zero with a timeout message when no routed agent comment arrives. In a durable supervisor that is quiet-by-default, treat that exact timeout as idle/no-work rather than a reportable error. Ordinary conversation comments are not routed claims; use browser agent actions or `plans comments add --submit-action agent` when testing listener wake behavior.

Current production Doct disables `doct-agent plans agent next --wait --timeout 300` because upstream proxy timeouts can terminate the request before a claim returns. For durable browser-review monitoring, use the CLI-provided listener command:

```bash
doct-agent plans listen \
  --base-url https://doct.nodaste.com \
  --workspace-id <workspace-id> \
  --document-id <document-id> \
  --jsonl \
  --lease-seconds 900
```

Run it as a tracked long-lived background process and verify that the process remains running. Use `plans agent next --wait --timeout 60` only for short diagnostics. Treat old registration payloads that return only `plans listen` as authoritative rather than rewriting them to a 300-second one-shot wait.
