#!/usr/bin/env python3
"""Audit pi-vcc continuation session entries and strict transaction logs."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

TERMINAL = {"settled", "superseded", "failed_loudly"}
ACTIVE = {"created", "waiting_tools", "submitted", "consumed", "progressed", "retrying"}
LOG_EVENTS = {"created", "waiting_tools", "submitted", "consumed", "progressed", "settled", "superseded", "retrying", "failed"}
LOG_KEYS = {
    "timestampEpoch", "event", "transactionId", "compactionId", "attemptId", "requestId",
    "originatingRequestId", "origin", "reason", "resumePolicy", "state", "outcome",
    "terminalReason", "retryCount", "retryLimit", "submissionCount", "elapsedMs", "deadlineAt",
    "pendingToolCount", "sessionEpoch", "inputEpoch", "agentEpoch", "turnEpoch", "messageEpoch",
    "settlementEpoch",
}
FORBIDDEN = {"preserve", "content", "message", "toolCallId", "pendingToolCallIds", "error", "stack", "password", "token", "secret"}


def iter_jsonl(path: Path) -> Iterable[tuple[int, dict[str, Any]]]:
    if path.is_dir():
        for child in sorted(path.rglob("*.jsonl")):
            yield from iter_jsonl(child)
        return
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            if isinstance(value, dict):
                yield line_number, value


def audit(sessions: list[Path], logs: list[Path], require_terminal: bool) -> list[str]:
    findings: list[str] = []
    requests: set[str] = set()
    outcomes: dict[str, str] = {}
    submissions: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for path in sessions:
        if not path.exists():
            findings.append(f"missing session path: {path}")
            continue
        for line_number, entry in iter_jsonl(path):
            if entry.get("type") != "custom":
                continue
            custom_type = entry.get("customType")
            data = entry.get("data")
            if not isinstance(data, dict):
                continue
            snapshot = data.get("snapshot")
            if not isinstance(snapshot, dict):
                continue
            tx = snapshot.get("transactionId")
            if not isinstance(tx, str):
                continue
            if custom_type == "pi-vcc-continuation-request":
                requests.add(tx)
            elif custom_type == "pi-vcc-continuation-outcome":
                state = snapshot.get("state")
                if state not in TERMINAL:
                    findings.append(f"{path}:{line_number}: invalid terminal outcome for {tx}: {state}")
                elif tx in outcomes and outcomes[tx] != state:
                    findings.append(f"{path}:{line_number}: conflicting outcomes for {tx}")
                outcomes[tx] = str(state)

    for path in logs:
        if not path.exists():
            findings.append(f"missing log path: {path}")
            continue
        for line_number, record in iter_jsonl(path):
            keys = set(record)
            unknown = keys - LOG_KEYS
            forbidden = {key for key in keys if key in FORBIDDEN}
            if unknown:
                findings.append(f"{path}:{line_number}: unknown log keys: {sorted(unknown)}")
            if forbidden:
                findings.append(f"{path}:{line_number}: privacy-forbidden log keys: {sorted(forbidden)}")
            event = record.get("event")
            tx = record.get("transactionId")
            if event not in LOG_EVENTS or not isinstance(tx, str):
                findings.append(f"{path}:{line_number}: invalid continuation log record")
                continue
            if event == "submitted":
                submissions[tx].append(record)
            if record.get("state") in TERMINAL:
                outcomes.setdefault(tx, str(record.get("state")))
            if event == "submitted" and record.get("terminalReason") == "session_replaced":
                findings.append(f"{path}:{line_number}: stale-session send for {tx}")

    if require_terminal:
        for tx in sorted(requests - set(outcomes)):
            findings.append(f"nonterminal transaction: {tx}")
    for tx, records in sorted(submissions.items()):
        counts = [record.get("submissionCount") for record in records]
        if len(counts) != len(set(counts)):
            findings.append(f"duplicate active submission record: {tx}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sessions", action="append", default=[], help="Session JSONL file or directory (repeatable)")
    parser.add_argument("--log", action="append", default=[], help="Strict continuation JSONL log (repeatable)")
    parser.add_argument("--require-terminal", action="store_true", help="Require every persisted request to have a terminal outcome")
    args = parser.parse_args()
    if not args.sessions and not args.log:
        parser.error("at least one --sessions or --log path is required")
    try:
        findings = audit([Path(item) for item in args.sessions], [Path(item) for item in args.log], args.require_terminal)
    except (OSError, ValueError) as exc:
        print(f"audit error: {exc}", file=sys.stderr)
        return 2
    if findings:
        for finding in findings:
            print(f"FINDING: {finding}")
        print(f"pi-vcc continuation audit: FAIL ({len(findings)} findings)")
        return 1
    print("pi-vcc continuation audit: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
