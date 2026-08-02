---
description: Register a coding plan in Doct and start the returned listener for reviewer-facing plans
argument-hint: "[plan file path or short description]"
---

# Send Coding Plan to Doct

Register or publish a coding plan in Doct for: `$ARGUMENTS`

## Required behavior

- Prefer the `doct-document-ops` skill if it is available.
- All doct operations go through the `doct-agent` CLI. Do not use `doct-cli`, raw REST, local `plan-review`, or helper scripts.
- If `$ARGUMENTS` looks like a local file path, read that file **fully** before sending it.
- If the plan is HTML or Markdoc, use `doct-agent plans register` against `https://doct.nodaste.com` by default.
- If the user explicitly wants a legacy text/Markdown child document instead of plan review, only then use the document flow the installed `doct-agent onboard` currently supports.

## Plan registration flow

1. Verify doct auth/context:

```bash
doct-agent auth status --all --json
doct-agent context --base-url https://doct.nodaste.com --json
```

2. Register reviewer-facing HTML plans:

```bash
doct-agent plans register \
  --base-url https://doct.nodaste.com \
  --file "$ARGUMENTS" \
  --source-format html \
  --allow-untemplated \
  --title '<Plan Title>' \
  --json
```

For Markdoc plans, use `--source-format markdoc` and omit `--allow-untemplated` unless the CLI/template guidance says otherwise. `--title` is required and must match the plan content title (HTML `<title>`+`<h1>`, or Markdoc frontmatter `title:`).

3. Parse the registration JSON and preserve:
- canonical Doct URL (`reviewUrl` or `documentUrl` resolved against `https://doct.nodaste.com`)
- document/plan id
- workspace id
- current version ids
- `sourceGuidance`
- full `listenerInstructions`

4. Follow the returned `listenerInstructions` before handoff:
- run the lifecycle command / set the plan active
- leave the plan in its registration/default board column for browser-review handoff
- drain with `agent next --no-wait` until `status: "empty"`
- start `listenerInstructions.listenerCommand` (`doct-agent plans listen ... --jsonl`) in the harness background-process tool; do not use `agent next --wait` as the default listener

5. Return to the user only after the listener is running, or report the listener-start blocker:
- plan title
- document/plan id
- workspace id
- canonical Doct review URL
- listener process/status

## Notes

- `documents publish-plan` is legacy and current doct-agent onboarding says it fails closed with replacement guidance for plan-review publishing. Do not use it for reviewer-facing HTML/Markdoc plans.
- The durable listener is part of registration completion. Do not ask the user to annotate the plan until it is running.
- If auth is missing, run `doct-agent auth login --base-url https://doct.nodaste.com` first with an owner-approved enrollment code, or use `doct-agent auth import-pat --base-url <url> --token <doct_pat_v1_...>` when explicitly provided.
