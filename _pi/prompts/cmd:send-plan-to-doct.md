---
description: Publish a coding plan to doct under the personal Coding Plans document
argument-hint: "[plan file path or short description]"
---

# Send Coding Plan to Doct

Publish a coding plan into doct as a **child document** under the root document **Coding Plans** in the user's **personal** workspace.

Request: $ARGUMENTS

## Required behavior

- Prefer the `doct-document-ops` skill if it is available.
- If `$ARGUMENTS` looks like a local file path, read that file **fully** before publishing.
- If the user pasted the plan inline, preserve the markdown exactly.
- Default destination unless the user explicitly overrides it:
  - workspace: personal
  - parent title: `Coding Plans`
  - kind: `text`
  - placement: child document under `Coding Plans`

## Publish flow

All doct operations go through the `doct-agent` CLI. Do not use `doct-cli`, raw REST, or helper scripts.

1. Verify doct auth:

```bash
doct-agent auth status
```

2. Publish the plan:

```bash
doct-agent documents publish-plan --file "$ARGUMENTS" --json
```

`publish-plan` resolves the personal workspace, ensures the `Coding Plans` parent document exists, and creates the plan as a new `text` child document. The title defaults to the first H1 in the file; override with `--title`.

If the plan is not already in a file, write the markdown to a temp file first and pass it with `--file`:

```bash
doct-agent documents publish-plan --file /tmp/plan.md --title "Plan Title" --json
```

3. Return to the user:
- created doct title
- document id
- doct URL

## Notes

- `publish-plan` auto-creates the root `Coding Plans` document if it does not already exist.
- New plans are created as child documents, not appended into the parent body.
- If auth is missing, run `doct-agent auth login --base-url https://doct.nodaste.com` first (paste the owner-approved enrollment code, or use `doct-agent auth import-pat --base-url <url> --token <doct_pat_v1_...>`).
- Override the destination only when asked, with `--parent-title` / `--workspace`.
