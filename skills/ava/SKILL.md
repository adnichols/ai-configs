---
name: ava
description: Use the ava CLI to create, publish, read, edit, review, and administer documents and Spaces in Avalandra.
---

# Ava CLI

Use the installed `ava` CLI directly in the current environment.

Start with only the checks needed to establish the target:

```bash
ava auth status --json
ava space list --json
```

Use `ava onboard`, `ava capabilities --json`, or targeted `--help` only when the requested operation is not covered here or a command fails.

## Command discovery

For commands not covered below, inspect `ava --help --json`, select the command whose summary matches the requested action, then inspect `ava <command> --help --json`. Follow its positional `args` in order and use only its declared flags.

- Pass `--organization` and `--space` when the request names those scopes and the command accepts them.
- If help lists `--idempotency-key`, every logical mutation needs one stable key.
- If help lists `--expected-revision` and the operation changes an existing resource, pass the revision returned by the preceding read or mutation.
- For JSON requests, `--data` accepts inline JSON and `--file` accepts a JSON file. Do not pass a raw content file to a JSON request.
- For a JSON mutation with no fields, pass `--data '{}'`; do not omit the request body.
- `document replace-body --file` accepts raw Markdown. `blob put --file` accepts raw bytes.
- `ava update` and `ava upgrade` are aliases. Preserve the verb the user requested when either is valid.

Command-table details that are easy to miss:

- `space show`, `space history`, `space revise`, `space archive`, `space restore`, and `space delete` take the target through `--space`.
- A POST can be read-only and still require `--idempotency-key`. Follow help for `catalog validate`, `transaction validate`, and `view run`.
- `view run` takes the view ID as its positional argument; it does not accept `--resource-id`.
- Entity actions, entity lifecycle changes, and profile activation changes require `--expected-revision`.

## Resolve the Space

Use the exact `space_id` returned by `ava space list --json`, such as `spc_...`. Organization-scoped document commands require the Space ID; do not substitute a display handle.

## Meaning of publish

- `save`, `upload`, or `create`: create the document and verify its saved draft.
- `publish`: after saving content, run `ava document submit` and verify `standing: published`.
- `canonical`: use `ava document promote` only when the user explicitly requests canonical approval.

Do not describe a draft as published.

## Text documents

Creating metadata and saving Markdown are separate commits with separate idempotency keys:

```bash
ava document create \
  --space "$space_id" \
  --idempotency-key "$create_key" \
  --data '{"title":"Document title","kind":"text"}' \
  --json

ava document replace-body "$document_id" \
  --space "$space_id" \
  --idempotency-key "$body_key" \
  --file document.md \
  --json

ava document get "$document_id" --space "$space_id" --json
```

Use `--file -` for stdin. Compare the returned `body` with the intended Markdown. For a live-state check, require `ava document get ... --live --json` to report `unsnapshotted: false`.

To publish after the body commit:

```bash
ava document submit "$document_id" \
  --space "$space_id" \
  --expected-revision "$body_revision_id" \
  --idempotency-key "$submit_key" \
  --data '{}' \
  --json

ava document status "$document_id" --space "$space_id" --json
```

Require the final status to report `standing: published`, `lifecycle: active`, and the submit revision.

## HTML documents

Register HTML through the plan pipeline. `document register --file plan.html` is wrong because `--file` expects a JSON request for this command. Encode the raw HTML as the `source` field. With `jq`:

```bash
payload="$(jq -n --arg title "$title" --rawfile source plan.html \
  '{title:$title,source:$source,source_format:"html"}')"

ava document register \
  --space "$space_id" \
  --idempotency-key "$register_key" \
  --data "$payload" \
  --json
```

The response calls the document ID `plan_id`. Verify the registered draft:

```bash
ava document render "$plan_id" --space "$space_id" --json
ava document status "$plan_id" --space "$space_id" --json
```

Require the rendered HTML to contain the requested content and inspect `warnings`. The CLI does not expose the stored canonical HTML source, so do not claim byte-for-byte source verification.

To publish:

```bash
ava document submit "$plan_id" \
  --space "$space_id" \
  --expected-revision "$register_revision_id" \
  --idempotency-key "$submit_key" \
  --data '{}' \
  --json

ava document status "$plan_id" --space "$space_id" --json
ava document render "$plan_id" --space "$space_id" --json
```

Require `standing: published`, `lifecycle: active`, the submit revision, the expected rendered content, and understood or empty warnings.

## Collaboration and administration

- Create a text comment with `ava document text-comment create`, including a uniquely matching `quote` and any useful `prefix` or `suffix`; list threads with `ava document text-comment list`.
- Use `ava document comment create`, `list`, and `reply` for HTML comments.
- Adding a human to a Space is a two-step authority split: an Organization admin invites or finds the user, then a Space admin grants membership by principal ID.
- An agent enrollment code is redeemed with `ava agent redeem`; inspect the result with `ava auth status` and `ava whoami`.

## Mutation rules

Use one stable idempotency key per logical mutation. Reuse the same key only when retrying the same command with identical content. If the payload changes after a validation failure, use a new key.

Use `--expected-revision` for submit, HTML edit, and canonical promotion. Stop on an unexpected conflict and reread current status before deciding whether to retry.

Return the Space ID, document ID, latest revision ID, standing, lifecycle, and verification result. Report every failed mutation that may have created state.
