#!/usr/bin/env python3
"""Create a privacy-safe aggregate report from Pi session JSONL files."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

SCHEMA_VERSION = "pi-session-analytics/v1"
DENVER = ZoneInfo("America/Denver")
CATEGORIES = ("empty_stream", "timeout", "goaway", "http2", "auth", "config", "other")
AUTH_TOKENS = (
    "authentication failed",
    "authentication failure",
    "authentication error",
    "authentication required",
    "authorization failed",
    "authorization failure",
    "authorization error",
    "unauthorized",
    "unauthorised",
    "access denied",
    "account disabled",
    "account locked",
    "account suspended",
    "account failure",
    "account error",
    "invalid token",
    "token invalid",
    "expired token",
    "token expired",
    "token failure",
    "token error",
    "token rejected",
    "missing token",
    "invalid api key",
    "api key invalid",
    "expired api key",
    "missing api key",
)
CONFIG_TOKENS = (
    "configuration",
    "misconfigured",
    "unsupported model",
    "unsupported-model",
    "unsupported_model",
    "model not supported",
    "invalid provider",
    "invalid-provider",
    "invalid_provider",
    "provider not supported",
)


class AnalyticsError(ValueError):
    """Raised when analyzer inputs do not satisfy the v1 contract."""


@dataclass(frozen=True)
class ReportingWindow:
    local_date: date
    start: datetime
    end: datetime


@dataclass(frozen=True)
class AllowedRecord:
    record_type: Any
    timestamp: Any
    role: Any = None
    provider: Any = None
    model: Any = None
    api: Any = None
    stop_reason: Any = None
    error_message: Any = None


def parse_timestamp(value: str, argument_name: str) -> datetime:
    if not isinstance(value, str):
        raise AnalyticsError(f"{argument_name} must be an ISO 8601 timestamp")
    normalized = value[:-1] + "+00:00" if value.endswith(("Z", "z")) else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise AnalyticsError(f"{argument_name} must be an ISO 8601 timestamp: {error}") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise AnalyticsError(f"{argument_name} must include a UTC offset")
    return parsed


def reporting_window(start_text: str, end_text: str) -> ReportingWindow:
    start = parse_timestamp(start_text, "--window-start").astimezone(DENVER)
    end = parse_timestamp(end_text, "--window-end").astimezone(DENVER)
    expected_start = datetime.combine(start.date(), time.min, DENVER)
    expected_end = datetime.combine(start.date() + timedelta(days=1), time.min, DENVER)
    if start != expected_start or end != expected_end:
        raise AnalyticsError(
            "reporting window must be exactly one America/Denver calendar day "
            "from local midnight (inclusive) to the next local midnight (exclusive)"
        )
    return ReportingWindow(start.date(), start, end)


def extract_allowed_record(value: Any) -> AllowedRecord | None:
    """Copy only the contract's allowlisted structured paths from a parsed record."""
    if not isinstance(value, dict):
        return None
    record_type = value.get("type")
    timestamp = value.get("timestamp")
    if record_type != "message":
        return AllowedRecord(record_type=record_type, timestamp=timestamp)
    message = value.get("message")
    if not isinstance(message, dict):
        return AllowedRecord(record_type=record_type, timestamp=timestamp)
    return AllowedRecord(
        record_type=record_type,
        timestamp=timestamp,
        role=message.get("role"),
        provider=message.get("provider"),
        model=message.get("model"),
        api=message.get("api"),
        stop_reason=message.get("stopReason"),
        error_message=message.get("errorMessage"),
    )


def classify_error(error_message: Any) -> str:
    text = error_message.casefold() if isinstance(error_message, str) else ""
    if "empty_stream" in text:
        return "empty_stream"
    if "timeout" in text or "timed out" in text:
        return "timeout"
    if "goaway" in text:
        return "goaway"
    if "http2" in text or "http/2" in text:
        return "http2"
    if any(token in text for token in AUTH_TOKENS):
        return "auth"
    if any(token in text for token in CONFIG_TOKENS):
        return "config"
    return "other"


def input_files(input_roots: Iterable[Path]) -> list[Path]:
    files: set[Path] = set()
    for root in input_roots:
        resolved_root = root.expanduser().resolve()
        if not resolved_root.is_dir():
            raise AnalyticsError("an input root is not a directory")
        for path in resolved_root.rglob("*.jsonl"):
            if not path.is_file():
                continue
            resolved_path = path.resolve()
            if not resolved_path.is_relative_to(resolved_root):
                raise AnalyticsError("an input root contains a JSONL file outside its resolved boundary")
            files.add(resolved_path)
    return sorted(files, key=lambda path: str(path))


def analyze(input_roots: Iterable[Path], window: ReportingWindow) -> dict[str, Any]:
    files = input_files(input_roots)
    counts: Counter[str] = Counter()
    categories: Counter[str] = Counter()
    sessions = 0
    window_start = window.start.astimezone(timezone.utc)
    window_end = window.end.astimezone(timezone.utc)

    for path in files:
        file_counts: Counter[str] = Counter()
        file_categories: Counter[str] = Counter()
        file_has_window_record = False
        file_has_attempt = False
        try:
            lines = path.open("r", encoding="utf-8", errors="replace")
        except OSError as error:
            raise AnalyticsError(f"cannot open an input JSONL file: {error.strerror or error}") from error
        with lines:
            for line in lines:
                try:
                    parsed = json.loads(line)
                except (json.JSONDecodeError, UnicodeError):
                    # A malformed line has no trustworthy timestamp, so assigning it
                    # to a completed day would let later appends change that day's
                    # immutable report. V1 therefore excludes it from window counts.
                    continue
                record = extract_allowed_record(parsed)
                if record is None or not isinstance(record.timestamp, str):
                    continue
                try:
                    timestamp = parse_timestamp(record.timestamp, "record timestamp").astimezone(timezone.utc)
                except AnalyticsError:
                    continue
                if not window_start <= timestamp < window_end:
                    continue
                file_counts["lines_total"] += 1
                file_counts["parsed_records"] += 1
                file_counts["records_in_window"] += 1
                file_has_window_record = True
                if record.record_type != "message":
                    continue
                file_counts["message_records_in_window"] += 1
                if record.role != "assistant" or not isinstance(record.stop_reason, str) or not record.stop_reason:
                    continue
                file_counts["assistant_terminal_attempts"] += 1
                file_has_attempt = True
                if record.stop_reason == "error":
                    file_counts["error_attempts"] += 1
                    file_categories[classify_error(record.error_message)] += 1
        if file_has_window_record:
            counts.update(file_counts)
            counts["input_files"] += 1
            categories.update(file_categories)
        if file_has_attempt:
            sessions += 1

    record_counts = {
        "input_files": counts["input_files"],
        "lines_total": counts["lines_total"],
        "malformed_lines": counts["malformed_lines"],
        "parsed_records": counts["parsed_records"],
        "records_in_window": counts["records_in_window"],
        "message_records_in_window": counts["message_records_in_window"],
        "sessions": sessions,
        "assistant_terminal_attempts": counts["assistant_terminal_attempts"],
        "error_attempts": counts["error_attempts"],
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "reporting_window": {
            "timezone": "America/Denver",
            "local_date": window.local_date.isoformat(),
            "start": window.start.isoformat(),
            "end": window.end.isoformat(),
        },
        "record_counts": record_counts,
        "category_counts": {category: categories[category] for category in CATEGORIES},
    }


def canonical_json(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=True, separators=(",", ":"), sort_keys=True) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Stream explicit Pi JSONL roots into a deterministic aggregate-only v1 report."
    )
    parser.add_argument(
        "--input-root",
        action="append",
        required=True,
        type=Path,
        help="Pi session directory to scan recursively (required; repeatable)",
    )
    parser.add_argument(
        "--window-start",
        required=True,
        help="inclusive ISO 8601 instant for America/Denver local midnight",
    )
    parser.add_argument(
        "--window-end",
        required=True,
        help="exclusive ISO 8601 instant for the following America/Denver local midnight",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        window = reporting_window(args.window_start, args.window_end)
        report = analyze(args.input_root, window)
    except AnalyticsError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    sys.stdout.write(canonical_json(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
