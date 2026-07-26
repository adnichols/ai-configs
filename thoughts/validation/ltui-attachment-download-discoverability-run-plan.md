# ltui attachment download discoverability — run ledger

## Scope and run state

- **Plan:** `thoughts/plans/ltui-attachment-download-discoverability.html`
- **User-authorized outcome:** implement the reviewed plan through separate standalone `ltui` and `ai-configs` pull requests. Live customer-file retrieval remains a post-merge, operator-authorized check.
- **Target branches:** `origin/main` for both repositories. `ai-configs` stays on `main` under its repository policy; determine the standalone `ltui` branch and PR workflow before committing.
- **Initial state:** `ai-configs` has only the plan source as an untracked file owned by this run. `/Users/anichols/code/ltui` is clean at `8a35156ddd46d43be9ed575fd6c740df2399dc7a`, matching `origin/main`.
- **Doct:** document `4205aa4e-cfd8-4580-ad7d-2b1ba35346fa`, workspace `759bfae3-44f1-4ce5-9bff-9077d9933a21`, execution-ready and active. Move to `in_progress` before source edits.

## Integration-integrity record

| Contract | Source of truth / producer | Consumers / inventory | Coverage and proof | Reconciliation |
| --- | --- | --- | --- | --- |
| Exact private-upload authorization boundary | Linear file-storage authentication guidance and `ltui/src/commands/issues.ts` request builder | `downloadToDir`, attachment-row classification, `--download-dir` output, tests, docs | Exact `URL.origin === "https://uploads.linear.app"`; HTTP, lookalikes, and `:444` reject authorization; authenticated requests prove `redirect: "error"`. | Reconciled — focused request-builder and fetch-seam tests passed. |
| Additive attachment row fields | `IssueAssetRow` and attachment row assembly in `ltui/src/commands/issues.ts` | Table/TSV/JSON formatters, `--fields`, issue-view probe, CLI regression tests, README, `skills/linear`, two Hermes source skills, command reference, architecture doc | Actual Commander JSON tests cover description/private, comment-private, mixed external-image/comment-private, and external rows; parser help and stale-reference checks passed. | Reconciled. |
| Generated download command | Commander registration in `ltui/src/commands/issues.ts` | Per-row JSON/table fields; generic issue-view fields; standalone README and agent/Hermes documentation | Comment rows assert `--scan-comments`; generic private command omits `--only-images`; mixed-attachment test proves an existing external image does not suppress comment-private discovery. | Reconciled. |
| Managed distribution | `install.sh` and `_hermes/default` plus `scripts/hermes_config_sync.py` | managed ltui checkout/binary and live Hermes source | Hermes dry-run/apply/export/verify succeeded; source manifest was refreshed after restoring exported scheduler runtime state. Tool refresh and live smoke are post-merge obligations. | Reconciled for source and Hermes skill synchronization. |

## Review and verification ledger

| Stage | Result | Notes |
| --- | --- | --- |
| Plan review | Clean | Doct reviewer completed; exact-origin and test-install corrections incorporated. |
| Implementation review cycle 1 | Finding fixed | Reviewer found comment-private uploads were skipped when an image attachment already existed. Added a mixed external-image/comment-private regression and narrowed comment-probe exit conditions. |
| Targeted rereview | Clean | Same active-harness reviewer returned `FIX_VERIFIED`. |
| Implementation PM review | Complete | Driving-agent review confirmed the change is limited to attachment discovery, output cues, credential boundary, docs, and managed Hermes sources. |
| Pre-PR reviewer gate | Complete | Satisfied by the bounded review plus targeted rereview. |
| Final verification | Passed | `npm ci && npm test`: 59 tests passed; parser/docs stale-flag checks and Hermes source verification passed. |
| Base freshness / PR feedback | Complete | Both branches were fetched and based on current `origin/main` before commit. Opened [Nodaste-Lab/ltui#2](https://github.com/Nodaste-Lab/ltui/pull/2) and [adnichols/ai-configs#50](https://github.com/adnichols/ai-configs/pull/50); initial snapshots had no comments or reviews. |

## Non-blocking post-merge obligations

1. Release/merge standalone ltui and refresh the managed tool with `bash ./install.sh --tools` (or a pinned `LTUI_REF` for pre-merge validation).
2. With authorized access to a non-sensitive issue, run one live `--download-dir` smoke check and retain only safe diagnostics: `downloadPath`, `downloadStatus`, and sanitized `downloadError` if it fails.
