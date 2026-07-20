# Pi Session Analytics Report Schema v1

## Purpose

`pi-session-analytics/v1` is the deterministic, aggregate-only output contract of `scripts/pi_session_analytics.py`. It is designed for offline analysis of explicitly named Pi session roots without emitting session text or raw structured errors.

## Command contract

The analyzer requires one or more explicit input roots and an explicit completed `America/Denver` calendar-day window:

```bash
python3 scripts/pi_session_analytics.py \
  --input-root /explicit/pi/session/root \
  --window-start 2026-07-19T00:00:00-06:00 \
  --window-end 2026-07-20T00:00:00-06:00
```

- `--input-root` is required and repeatable. Each value must be a directory. Duplicate or overlapping roots do not double-count the same resolved `*.jsonl` file.
- `--window-start` is inclusive and `--window-end` is exclusive.
- Both window arguments must be offset-aware ISO 8601 timestamps representing consecutive local midnights in `America/Denver`. The duration may be 23, 24, or 25 hours across daylight-saving transitions.
- Files are discovered recursively and processed line by line. The analyzer does not read a default or implicit live-session location.
- The report is written to standard output. Input and window errors are written to standard error and return exit status 2.

## Allowed input paths

For each parsed JSON object, the analyzer may access only:

- top-level `type`
- top-level `timestamp`
- for `type == "message"` only:
  - `message.role`
  - `message.provider`
  - `message.model`
  - `message.api`
  - `message.stopReason`
  - `message.errorMessage`

The provider, model, and API fields are accepted as part of the current Pi record shape but are not emitted in v1.

The analyzer must never access or emit `message.content`, prompts, source, paths, credentials, tool arguments or results, thinking, transcript prose, or arbitrary additional fields. It never emits the structured `errorMessage`; it emits only its mapped category count.

## Attempt and session semantics

- An **attempt** is a `message` record inside the reporting window whose role is exactly `assistant` and whose `stopReason` is a non-empty string.
- A **failure** is an attempt whose `stopReason` is exactly `error`.
- `record_counts.input_files` counts JSONL files containing at least one parsed record in the reporting window. Files containing only later or earlier dates, and later records appended to a continuing session file, do not change a completed day's report identity.
- A **session** is one input JSONL file containing at least one attempt in the reporting window.
- A file with only user messages or nonterminal assistant messages may contribute one `input_files` count but zero sessions; a file with only out-of-window records contributes neither.
- Malformed JSON lines and parsed records with a missing, invalid, or offset-naive timestamp are skipped. Because they have no trustworthy timestamp, v1 does not assign them to a completed day: `malformed_lines` remains the reserved value `0`, while `lines_total` and `parsed_records` count only parsed records whose timestamps fall in the reporting window. This keeps a completed report immutable when a continuing session file receives later appends.

## Error categories

Matching is case-insensitive and occurs only in `message.errorMessage`, in the precedence shown below.

| Category | Fixed tokens |
|---|---|
| `empty_stream` | `empty_stream` |
| `timeout` | `timeout`, `timed out` |
| `goaway` | `goaway` |
| `http2` | `http2`, `http/2` |
| `auth` | `authentication failed`, `authentication failure`, `authentication error`, `authentication required`, `authorization failed`, `authorization failure`, `authorization error`, `unauthorized`, `unauthorised`, `access denied`, `account disabled`, `account locked`, `account suspended`, `account failure`, `account error`, `invalid token`, `token invalid`, `expired token`, `token expired`, `token failure`, `token error`, `token rejected`, `missing token`, `invalid api key`, `api key invalid`, `expired api key`, `missing api key` |
| `config` | `configuration`, `misconfigured`, `unsupported model`, `unsupported-model`, `unsupported_model`, `model not supported`, `invalid provider`, `invalid-provider`, `invalid_provider`, `provider not supported` |
| `other` | every other structured error, including a missing or non-string `errorMessage` |

All seven category keys are always present, including when their counts are zero.

## Required report shape

```json
{
  "schema_version": "pi-session-analytics/v1",
  "reporting_window": {
    "timezone": "America/Denver",
    "local_date": "YYYY-MM-DD",
    "start": "YYYY-MM-DDT00:00:00-07:00",
    "end": "YYYY-MM-DDT00:00:00-06:00"
  },
  "record_counts": {
    "input_files": 0,
    "lines_total": 0,
    "malformed_lines": 0,
    "parsed_records": 0,
    "records_in_window": 0,
    "message_records_in_window": 0,
    "sessions": 0,
    "assistant_terminal_attempts": 0,
    "error_attempts": 0
  },
  "category_counts": {
    "empty_stream": 0,
    "timeout": 0,
    "goaway": 0,
    "http2": 0,
    "auth": 0,
    "config": 0,
    "other": 0
  }
}
```

### Field rules

- `schema_version`: exact string `pi-session-analytics/v1`.
- `reporting_window.timezone`: exact string `America/Denver`.
- `reporting_window.local_date`: Denver date selected by the validated start boundary.
- `reporting_window.start` and `.end`: canonical Denver-local ISO 8601 boundaries with numeric UTC offsets.
- Every value under `record_counts` and `category_counts`: a non-negative JSON integer.
- `error_attempts` equals the sum of all values in `category_counts`.
- `sessions` is less than or equal to `input_files`.

## Canonical JSON serialization

The command emits exactly one JSON object followed by one LF newline. Serialization uses:

- UTF-8-compatible ASCII escapes (`ensure_ascii=true`)
- lexicographically sorted object keys at every level
- no insignificant whitespace (`separators=(",", ":")`)
- JSON integers for every count
- no timestamps other than the reporting-window boundaries

Equivalent input-root orderings and duplicate roots therefore produce byte-identical output when they resolve to the same files and records.

## Sanitized baseline

`thoughts/retro/pi-session-analytics-sanitized-baseline-v1.json` is generated only from `scripts/tests/fixtures/pi-session-analytics/comprehensive/`. The fixtures preserve the current structured event shape but use synthetic timestamps and sanitized values. Privacy sentinels in forbidden fields prove those fields do not reach the report. The baseline contains no live-session record or raw excerpt.
