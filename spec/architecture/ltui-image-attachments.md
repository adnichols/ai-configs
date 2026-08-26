# ltui Image Attachments System

**Last Updated:** 2026-07-26
**Status:** ✅ Implemented

## Overview

`ltui` now includes a first-class issue-asset surface for Linear issues. The implementation adds `ltui issues attachments <issue>` for deterministic attachment discovery and optional local downloads, and extends `ltui issues view <issue>` with explicit attachment/image guidance fields so agents can discover screenshots without guessing.

The shipped behavior covers both native Linear link attachments and `uploads.linear.app` URLs discovered in issue descriptions and comments.

## CLI Contracts

### `ltui issues attachments <identifier>`

Implemented in the standalone `ltui` repository at `src/commands/issues.ts`.

Supported options:
- `--only-images`
- `--download-dir <dir>`
- `--overwrite`
- `--no-linear-attachments`
- `--no-upload-urls`
- `--scan-comments`
- `--max-comments <n>` (default: `50`, used with `--scan-comments`)

List output is deterministic:
- rows are sorted by `createdAt` descending, then `id` ascending
- optional text fields normalize to empty strings
- retrieval cues are always present: `downloadAccess`, `downloadCommand`
- download result fields are always present: `downloadPath`, `downloadStatus`, `downloadError`

`downloadAccess` is `ltui_authenticated` only for the exact private upload origin `https://uploads.linear.app`; every other HTTP(S) URL is `direct_url`. For authenticated rows, `downloadCommand` is a deterministic command that re-discovers the issue asset and downloads it through ltui.

For `--format json`, paginated list output is emitted as a JSON envelope:

```json
{
  "meta": {
    "cursorNext": "",
    "cursorPrev": "",
    "count": 1
  },
  "rows": [
    {
      "id": "..."
    }
  ]
}
```

### `ltui issues view <identifier>`

Issue detail output now emits:
- `ATTACHMENTS_PRESENT`
- `IMAGE_ATTACHMENTS_PRESENT`
- `IMAGE_ATTACHMENTS_FETCH_CMD`
- `IMAGE_ATTACHMENTS_DOWNLOAD_CMD`
- `ATTACHMENTS_DOWNLOAD_CMD` and `ATTACHMENTS_DOWNLOAD_GUIDANCE` when a private upload is found

JSON output mirrors these fields as `attachmentsDownloadCmd` and `attachmentsDownloadGuidance`. The generic private-file command intentionally omits `--only-images`, so customer ZIPs and other non-image evidence remain downloadable. It includes `--scan-comments` only when the matching private upload came from a comment.

The image probe pages through issue attachments until an image is found or the attachment connection is exhausted, and also checks `uploads.linear.app` references in the issue description and comments.

## Data Flow

1. Resolve the Linear issue by key or ID.
2. Build asset rows from:
   - `issue.attachments()`
   - `uploads.linear.app` URLs extracted from the description
   - `uploads.linear.app` URLs extracted from comments
3. Classify image-like assets by content type first, then by URL extension fallback.
4. Classify each URL as `ltui_authenticated` only when its normalized `URL.origin` is `https://uploads.linear.app`; otherwise classify it as `direct_url`.
5. Render deterministic list output with pagination metadata and retrieval cues.
6. When download mode is enabled, stream each asset to disk and annotate the output row with final download status.

## Behaviors

- Agents can detect screenshots from `ltui issues view` without parsing prose.
- Agents can fetch attachment metadata independently with a stable command surface.
- Agents can limit results to image-like assets with `--only-images`.
- Agents can optionally download assets locally into a caller-controlled directory.
- Download attempts do not suppress row output; failures are surfaced in-row and through process exit code.

## Constraints

- Downloads are opt-in and occur only when `--download-dir` is supplied.
- Only `http` and `https` URLs are fetched.
- Comment upload URLs are discovered only with `--scan-comments`; this keeps ordinary attachment listing cheaper.
- `--only-images` intentionally excludes archives and other non-image evidence.
- JSON list output uses a JSON envelope for paginated list commands.
- Attachment discovery includes uploads embedded in markdown, not only first-party Linear attachment nodes.

## Configuration

Implemented defaults in standalone `ltui/src/commands/issues.ts`:
- download timeout: `10 * 60_000` ms
- maximum download size: `512 * 1024 * 1024` bytes

## Security

- Download directories must not be symlinks.
- Existing symlink targets are refused during overwrite/write selection.
- Filenames are sanitized before writing.
- Large downloads are capped with a byte-limit transform.
- Only the exact origin `https://uploads.linear.app` receives a GraphQL-compatible `Authorization` header: raw `lin_api_...` personal keys, `Bearer` only for OAuth tokens. HTTP, lookalike hosts, and alternate ports receive no Linear credential. `public-file-urls-expire-in` does not sign `attachment.url`.
- Authenticated downloads set `redirect: "error"`, so credentials cannot follow a redirect to another origin.
- Downloaded files should be treated as untrusted input by downstream tooling.

## Testing

Verified in the standalone `ltui` repository with:
- `npm ci`
- `npm run build`
- `npm test`

Relevant coverage includes:
- `src/__tests__/cli-args.test.ts`
- `src/__tests__/cli-regression.test.ts`
- `src/__tests__/attachment-download-request.test.ts`
- `src/__tests__/output.test.ts`
- `src/test-utils/mockLinearClient.ts`

The regression suite covers attachment command help, comment-scan opt-in, private/comment/external retrieval cues, issue-detail guidance fields, exact-origin authentication, no credential leakage to HTTP/lookalike/alternate-port URLs, and fail-closed authenticated redirects.

## Integration Points

- `skills/linear/SKILL.md`
- `skills/linear/references/ltui-command-reference.md`
- `_hermes/default/skills/productivity/linear/SKILL.md`
- `_hermes/default/profiles/nerd/skills/productivity/linear/SKILL.md`
- standalone `ltui/src/commands/issues.ts`
- standalone `ltui/src/format.ts`

## Implementation Notes

- This implementation changed JSON pagination behavior from plaintext cursor headers to a JSON envelope for paginated JSON list output.
- The final implementation exceeded the original plan in one useful way by including upload URLs discovered in issue descriptions and comments, not only `issue.attachments()` rows.
- The original working plan was `thoughts/plans/ltui-image-attachments-plan.md` and is preserved in git history after graduation cleanup.
