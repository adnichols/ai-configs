#!/usr/bin/env python3
"""Publish one privacy-safe Pi analytics report for the completed Denver day."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

SCHEMA_VERSION = "pi-session-analytics/v1"
REPORT_TITLE_PREFIX = "pi-analytics/v1"
DEFAULT_TIMEZONE = "America/Denver"
DEFAULT_TIMEOUT_SECONDS = 30 * 60
VALID_STATES = {
    "not_run",
    "running",
    "succeeded",
    "analyzer_failed",
    "publish_failed",
    "report_conflict",
    "timed_out",
}
CATEGORIES = ("empty_stream", "timeout", "goaway", "http2", "auth", "config", "other")
RECORD_COUNTS = (
    "input_files",
    "lines_total",
    "malformed_lines",
    "parsed_records",
    "records_in_window",
    "message_records_in_window",
    "sessions",
    "assistant_terminal_attempts",
    "error_attempts",
)


class CollectorError(RuntimeError):
    """Base class for expected collector failures."""


class AnalyzerFailure(CollectorError):
    """The analyzer failed or returned an invalid report."""


class PublishFailure(CollectorError):
    """C-Core publication failed."""


class ReportConflict(CollectorError):
    """A same-title C-Core report has conflicting or ambiguous content."""


class CollectorTimeout(CollectorError):
    """The analyzer or publication exceeded the collector deadline."""


def default_config_path() -> Path:
    return Path.home() / ".hermes" / "config" / "pi-analytics-collector.json"


def default_status_path() -> Path:
    return Path.home() / ".hermes" / "state" / "pi-analytics" / "last-run.json"


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def completed_day(now: datetime, timezone_name: str = DEFAULT_TIMEZONE) -> tuple[date, datetime, datetime]:
    zone = ZoneInfo(timezone_name)
    local_now = now.astimezone(zone)
    report_date = local_now.date() - timedelta(days=1)
    start = datetime.combine(report_date, time.min, zone)
    end = datetime.combine(report_date + timedelta(days=1), time.min, zone)
    return report_date, start, end


def canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True) + "\n"


def _is_nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def validate_report(value: Any, expected_date: date, start: datetime, end: datetime) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        "schema_version", "reporting_window", "record_counts", "category_counts"
    }:
        raise AnalyzerFailure("analyzer output does not have the exact aggregate-only v1 shape")
    if value["schema_version"] != SCHEMA_VERSION:
        raise AnalyzerFailure("analyzer output has an unsupported schema version")

    window = value["reporting_window"]
    if not isinstance(window, dict) or set(window) != {"timezone", "local_date", "start", "end"}:
        raise AnalyzerFailure("analyzer output has an invalid reporting window")
    expected_window = {
        "timezone": DEFAULT_TIMEZONE,
        "local_date": expected_date.isoformat(),
        "start": start.isoformat(),
        "end": end.isoformat(),
    }
    if window != expected_window:
        raise AnalyzerFailure("analyzer output reporting window does not match the requested Denver day")

    record_counts = value["record_counts"]
    category_counts = value["category_counts"]
    if not isinstance(record_counts, dict) or tuple(record_counts.keys()) != RECORD_COUNTS:
        # Key order is part of canonical analyzer output, but accept parsed sorted-key order below.
        if not isinstance(record_counts, dict) or set(record_counts) != set(RECORD_COUNTS):
            raise AnalyzerFailure("analyzer output has invalid record-count fields")
    if not isinstance(category_counts, dict) or set(category_counts) != set(CATEGORIES):
        raise AnalyzerFailure("analyzer output has invalid category-count fields")
    if not all(_is_nonnegative_int(record_counts[name]) for name in RECORD_COUNTS):
        raise AnalyzerFailure("analyzer record counts must be non-negative integers")
    if not all(_is_nonnegative_int(category_counts[name]) for name in CATEGORIES):
        raise AnalyzerFailure("analyzer category counts must be non-negative integers")
    if record_counts["error_attempts"] != sum(category_counts.values()):
        raise AnalyzerFailure("analyzer error count does not equal category totals")
    if record_counts["sessions"] > record_counts["input_files"]:
        raise AnalyzerFailure("analyzer session count exceeds input-file count")
    return value


def parse_canonical_report(raw: str, expected_date: date, start: datetime, end: datetime) -> tuple[dict[str, Any], str]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AnalyzerFailure(f"analyzer output is not JSON: {exc}") from exc
    report = validate_report(value, expected_date, start, end)
    canonical = canonical_json(report)
    if raw != canonical:
        raise AnalyzerFailure("analyzer output is not canonical v1 JSON")
    return report, canonical


def load_config(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CollectorError(f"unable to read collector config {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CollectorError("collector config must be a JSON object")
    required = {"enabled", "host", "timezone", "input_roots", "ccore_space"}
    missing = sorted(required - set(value))
    if missing:
        raise CollectorError(f"collector config is missing fields: {', '.join(missing)}")
    if not isinstance(value["enabled"], bool):
        raise CollectorError("collector config enabled must be boolean")
    if (
        not isinstance(value["host"], str)
        or not value["host"]
        or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for character in value["host"])
    ):
        raise CollectorError("collector config host must use only letters, digits, dots, underscores, or hyphens")
    if value["timezone"] != DEFAULT_TIMEZONE:
        raise CollectorError(f"collector config timezone must be {DEFAULT_TIMEZONE}")
    roots = value["input_roots"]
    if not isinstance(roots, list) or not roots or not all(isinstance(root, str) and root for root in roots):
        raise CollectorError("collector config input_roots must be a non-empty string list")
    if value["ccore_space"] != "Private":
        raise CollectorError("collector config ccore_space must be Private")
    analyzer = value.get("analyzer_path")
    if not isinstance(analyzer, str) or not analyzer:
        raise CollectorError("collector config analyzer_path must name the authoritative P1 analyzer")
    ccore = value.get("ccore_binary", "ccore")
    if not isinstance(ccore, str) or not ccore:
        raise CollectorError("collector config ccore_binary must be a non-empty string")
    value["ccore_binary"] = ccore
    return value


def atomic_write_status(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_path, 0o600)
        os.replace(temp_path, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def read_status(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "host": None,
            "expected_date": None,
            "started_at": None,
            "finished_at": None,
            "state": "not_run",
        }
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CollectorError(f"unable to read collector status {path}: {exc}") from exc
    if not isinstance(value, dict) or value.get("state") not in VALID_STATES:
        raise CollectorError(f"collector status is invalid: {path}")
    return value


def _run(argv: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
    if timeout <= 0:
        raise CollectorTimeout("collector deadline expired")
    try:
        return subprocess.run(
            argv,
            shell=False,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise CollectorTimeout(f"command timed out: {argv[0]}") from exc
    except OSError as exc:
        raise PublishFailure(f"unable to execute {argv[0]}: {exc}") from exc


def _remaining(deadline: float) -> float:
    import time as _time

    return max(0.0, deadline - _time.monotonic())


def run_analyzer(config: dict[str, Any], start: datetime, end: datetime, deadline: float) -> str:
    argv = [
        sys.executable,
        str(Path(config["analyzer_path"]).expanduser()),
    ]
    for root in config["input_roots"]:
        argv.extend(["--input-root", str(Path(root).expanduser())])
    argv.extend(["--window-start", start.isoformat(), "--window-end", end.isoformat()])
    try:
        result = _run(argv, _remaining(deadline))
    except PublishFailure as exc:
        raise AnalyzerFailure(str(exc)) from exc
    if result.returncode != 0:
        raise AnalyzerFailure(f"analyzer exited {result.returncode}: {result.stderr.strip()}")
    return result.stdout


def _walk_documents(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        for key in ("documents", "items", "results", "data"):
            nested = value.get(key)
            if isinstance(nested, list):
                return [item for item in nested if isinstance(item, dict)]
    return []


def parse_document_list(output: str, title: str) -> list[str]:
    try:
        value = json.loads(output)
    except json.JSONDecodeError:
        matches = []
        for line in output.splitlines():
            if title not in line:
                continue
            fields = line.strip().split()
            if fields:
                matches.append(fields[0])
        return matches

    matches = []
    for item in _walk_documents(value):
        item_title = item.get("title") or item.get("name")
        item_id = item.get("id") or item.get("document_id") or item.get("documentId")
        if item_title == title and isinstance(item_id, str) and item_id:
            matches.append(item_id)
    return matches


def parse_document_content(output: str) -> str:
    try:
        value = json.loads(output)
    except json.JSONDecodeError:
        start = output.find("{")
        if start >= 0:
            candidate = output[start:].strip()
            return candidate + ("" if candidate.endswith("\n") else "\n")
        raise PublishFailure("ccore document output did not contain readable content")
    if not isinstance(value, dict):
        raise PublishFailure("ccore document output was not an object")
    direct_content = value.get("current_version_content") or value.get("currentVersionContent")
    if isinstance(direct_content, str):
        return direct_content + ("" if direct_content.endswith("\n") else "\n")
    candidates = [value]
    for key in ("document", "current_version", "currentVersion", "version", "data"):
        nested = value.get(key)
        if isinstance(nested, dict):
            candidates.append(nested)
    for candidate in candidates:
        content = candidate.get("content") or candidate.get("body")
        if isinstance(content, str):
            return content + ("" if content.endswith("\n") else "\n")
    raise PublishFailure("ccore document output did not contain content")


def _next_document_cursor(output: str) -> int | None:
    try:
        value = json.loads(output)
    except json.JSONDecodeError:
        return None
    if not isinstance(value, dict) or value.get("next_cursor") is None:
        return None
    cursor = value["next_cursor"]
    if isinstance(cursor, bool) or not isinstance(cursor, int) or cursor < 0:
        raise PublishFailure("ccore doc list returned an invalid cursor")
    return cursor


def list_title_matches(ccore: str, space: str, title: str, deadline: float) -> list[str]:
    matches: list[str] = []
    cursor = 0
    seen_cursors: set[int] = set()
    while cursor not in seen_cursors:
        seen_cursors.add(cursor)
        result = _run(
            [ccore, "doc", "list", space, "--limit", "500", "--cursor", str(cursor)],
            _remaining(deadline),
        )
        if result.returncode != 0:
            raise PublishFailure(f"ccore doc list failed: {result.stderr.strip()}")
        matches.extend(parse_document_list(result.stdout, title))
        next_cursor = _next_document_cursor(result.stdout)
        if next_cursor is None:
            return matches
        cursor = next_cursor
    raise PublishFailure("ccore doc list returned a repeating cursor")


def read_document(ccore: str, space: str, document_id: str, deadline: float) -> str:
    result = _run(
        [ccore, "doc", "show", document_id, "--space", space, "--include-content"],
        _remaining(deadline),
    )
    if result.returncode != 0:
        raise PublishFailure(f"ccore doc show failed: {result.stderr.strip()}")
    return parse_document_content(result.stdout)


def reconcile_existing(
    ccore: str,
    space: str,
    title: str,
    canonical: str,
    expected_date: date,
    start: datetime,
    end: datetime,
    deadline: float,
) -> bool:
    matches = list_title_matches(ccore, space, title, deadline)
    if not matches:
        return False
    if len(matches) != 1:
        raise ReportConflict(f"multiple C-Core documents have title {title}")
    content = read_document(ccore, space, matches[0], deadline)
    try:
        _, existing_canonical = parse_canonical_report(content, expected_date, start, end)
    except AnalyzerFailure as exc:
        raise ReportConflict(f"same-title C-Core document is not a valid canonical report: {exc}") from exc
    if existing_canonical != canonical:
        raise ReportConflict(f"same-title C-Core document has conflicting content: {title}")
    return True


def publish_report(
    config: dict[str, Any],
    title: str,
    canonical: str,
    expected_date: date,
    start: datetime,
    end: datetime,
    deadline: float,
) -> None:
    # Revalidate at the publication boundary so malformed or noncanonical data can
    # never become an argument to a C-Core mutation command.
    _, canonical = parse_canonical_report(canonical, expected_date, start, end)
    ccore = config["ccore_binary"]
    space = config["ccore_space"]
    if reconcile_existing(ccore, space, title, canonical, expected_date, start, end, deadline):
        return
    result = _run(
        [
            ccore,
            "doc",
            "new",
            space,
            title,
            canonical,
            "--kind",
            "note",
            "--content-type",
            "application/json",
        ],
        _remaining(deadline),
    )
    if result.returncode != 0:
        # An interrupted/racing create is safe to retry if the immutable report now exists.
        if reconcile_existing(ccore, space, title, canonical, expected_date, start, end, deadline):
            return
        raise PublishFailure(f"ccore doc new failed: {result.stderr.strip()}")


@contextmanager
def collector_lock(status_path: Path):
    """Serialize analyzer/publication runs on one host to prevent duplicate creates."""
    status_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = status_path.parent / ".pi-analytics-collector.lock"
    with lock_path.open("a+", encoding="utf-8") as lock:
        os.chmod(lock_path, 0o600)
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def run_collection(config_path: Path, status_path: Path, timeout_seconds: int) -> int:
    with collector_lock(status_path):
        return _run_collection_locked(config_path, status_path, timeout_seconds)


def _run_collection_locked(config_path: Path, status_path: Path, timeout_seconds: int) -> int:
    started_at = utc_timestamp()
    try:
        config = load_config(config_path)
    except CollectorError:
        report_date, _, _ = completed_day(datetime.now(timezone.utc), DEFAULT_TIMEZONE)
        final_status = {
            "host": None,
            "expected_date": report_date.isoformat(),
            "started_at": started_at,
            "finished_at": utc_timestamp(),
            "state": "publish_failed",
            "message": "collector configuration is invalid or unreadable",
        }
        atomic_write_status(status_path, final_status)
        print("pi analytics collector: publish_failed: collector configuration is invalid or unreadable", file=sys.stderr)
        return 1
    report_date, start, end = completed_day(datetime.now(timezone.utc), config["timezone"])
    base_status = {
        "host": config["host"],
        "expected_date": report_date.isoformat(),
        "started_at": started_at,
        "finished_at": None,
    }
    if not config["enabled"]:
        atomic_write_status(status_path, {**base_status, "finished_at": utc_timestamp(), "state": "not_run"})
        return 0

    atomic_write_status(status_path, {**base_status, "state": "running"})
    import time as _time

    deadline = _time.monotonic() + timeout_seconds
    state = "succeeded"
    message = None
    try:
        raw = run_analyzer(config, start, end, deadline)
        _, canonical = parse_canonical_report(raw, report_date, start, end)
        title = f"{REPORT_TITLE_PREFIX}/{config['host']}/{report_date.isoformat()}"
        publish_report(config, title, canonical, report_date, start, end, deadline)
    except CollectorTimeout as exc:
        state, message = "timed_out", str(exc)
    except AnalyzerFailure as exc:
        state, message = "analyzer_failed", str(exc)
    except ReportConflict as exc:
        state, message = "report_conflict", str(exc)
    except (PublishFailure, CollectorError) as exc:
        state, message = "publish_failed", str(exc)
    except Exception as exc:  # Defensive boundary: never strand status at running.
        state, message = "publish_failed", f"unexpected collector error: {exc}"

    final_status = {**base_status, "finished_at": utc_timestamp(), "state": state}
    if message:
        final_status["message"] = message
    atomic_write_status(status_path, final_status)
    if state != "succeeded":
        print(f"pi analytics collector: {state}: {message}", file=sys.stderr)
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=default_config_path())
    parser.add_argument("--status-file", type=Path, default=default_status_path())
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--status", action="store_true", help="read collector status without doing work")
    parser.add_argument("--json", action="store_true", help="emit machine-readable status JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.status:
        try:
            status = read_status(args.status_file.expanduser())
        except CollectorError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if args.json:
            sys.stdout.write(json.dumps(status, separators=(",", ":"), sort_keys=True) + "\n")
        else:
            print(status["state"])
        return 0
    if args.timeout_seconds <= 0:
        print("error: --timeout-seconds must be positive", file=sys.stderr)
        return 2
    if args.json:
        print("error: --json requires --status", file=sys.stderr)
        return 2
    try:
        return run_collection(args.config.expanduser(), args.status_file.expanduser(), args.timeout_seconds)
    except CollectorError as exc:
        print(f"pi analytics collector: publish_failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
