#!/usr/bin/env python3
"""Audit pi-vcc continuation session entries and strict transaction logs."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

PROTOCOL = "pi-vcc-continuation"
VERSION = 1
REQUEST_TYPE = "pi-vcc-continuation-request"
SNAPSHOT_TYPE = "pi-vcc-continuation-snapshot"
OUTCOME_TYPE = "pi-vcc-continuation-outcome"
SAFETY_READY_TYPE = "pi-vcc-continuation-safety-ready"
CONTINUATION_TYPES = {REQUEST_TYPE, SNAPSHOT_TYPE, OUTCOME_TYPE, SAFETY_READY_TYPE}
TERMINAL = {"settled", "superseded", "failed_loudly"}
ACTIVE = {"created", "waiting_tools", "submitted", "consumed", "progressed", "retrying"}
STATES = ACTIVE | TERMINAL
LOG_EVENTS = {"created", "waiting_tools", "submitted", "consumed", "progressed", "settled", "superseded", "retrying", "failed"}
LOG_KEYS = {
    "timestampEpoch", "event", "transactionId", "compactionId", "attemptId", "requestId",
    "originatingRequestId", "origin", "reason", "resumePolicy", "state", "outcome",
    "terminalReason", "retryCount", "retryLimit", "submissionCount", "elapsedMs", "deadlineAt",
    "pendingToolCount", "sessionEpoch", "inputEpoch", "agentEpoch", "turnEpoch", "messageEpoch",
    "settlementEpoch",
}
FORBIDDEN = {"preserve", "content", "message", "toolCallId", "pendingToolCallIds", "error", "stack", "password", "token", "secret"}
EPOCH_KEYS = ("sessionEpoch", "inputEpoch", "agentEpoch", "turnEpoch", "messageEpoch", "settlementEpoch")


def iter_jsonl(path: Path) -> Iterable[tuple[Path, int, dict[str, Any]]]:
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
                yield path, line_number, value


def is_nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def valid_epochs(value: Any) -> bool:
    return isinstance(value, dict) and set(value) == {"session", "input", "agent", "turn", "message", "settlement"} and all(
        is_nonnegative_int(item) for item in value.values()
    )


def valid_snapshot(value: Any, request: bool = False) -> bool:
    if not isinstance(value, dict):
        return False
    required = {
        "protocol", "version", "transactionId", "origin", "reason", "attemptId", "resumePolicy", "state",
        "createdAt", "deadlineAt", "pendingToolCount", "submissionCount", "retryCount", "retryLimit", "epochs",
    }
    optional = {"compactionId", "requestId", "originatingRequestId", "consumedEpochs", "lastAssistantResult", "terminalReason"}
    if not required <= set(value) or set(value) - required - optional:
        return False
    if value.get("protocol") != PROTOCOL or value.get("version") != VERSION:
        return False
    if not all(isinstance(value.get(key), str) and value[key] for key in ("transactionId", "origin", "reason", "attemptId", "resumePolicy", "state")):
        return False
    if value["state"] not in STATES or (request and value["state"] != "created"):
        return False
    if not all(is_nonnegative_int(value.get(key)) for key in ("createdAt", "deadlineAt", "pendingToolCount", "submissionCount", "retryCount", "retryLimit")):
        return False
    if value["deadlineAt"] < value["createdAt"] or not valid_epochs(value.get("epochs")):
        return False
    if value.get("consumedEpochs") is not None and not valid_epochs(value["consumedEpochs"]):
        return False
    if value["state"] in TERMINAL:
        return isinstance(value.get("terminalReason"), str) and bool(value["terminalReason"])
    return "terminalReason" not in value


def valid_wire(custom_type: str, data: Any) -> bool:
    if not isinstance(data, dict) or data.get("protocol") != PROTOCOL or data.get("version") != VERSION:
        return False
    if custom_type == REQUEST_TYPE:
        return (
            set(data) <= {"protocol", "version", "kind", "snapshot", "outcomeHint"}
            and {"protocol", "version", "kind", "snapshot"} <= set(data)
            and data.get("kind") == "request"
            and valid_snapshot(data.get("snapshot"), request=True)
            and (
                "outcomeHint" not in data
                or data.get("outcomeHint") in {"compacted", "no-safe-cut", "cancellation", "failure"}
            )
        )
    if custom_type == SNAPSHOT_TYPE:
        return set(data) == {"protocol", "version", "kind", "snapshot"} and data.get("kind") == "snapshot" and valid_snapshot(data.get("snapshot"))
    if custom_type == OUTCOME_TYPE:
        snapshot = data.get("snapshot")
        return (
            set(data) == {"protocol", "version", "kind", "transactionId", "terminalState", "terminalReason", "snapshot"}
            and data.get("kind") == "outcome"
            and valid_snapshot(snapshot)
            and data.get("terminalState") in TERMINAL
            and data.get("transactionId") == snapshot.get("transactionId")
            and data.get("terminalState") == snapshot.get("state")
            and data.get("terminalReason") == snapshot.get("terminalReason")
        )
    if custom_type == SAFETY_READY_TYPE:
        return (
            set(data) <= {"protocol", "version", "kind", "transactionId", "attemptId", "requestId"}
            and {"protocol", "version", "kind", "transactionId", "attemptId"} <= set(data)
            and data.get("kind") == "safety-ready"
            and all(isinstance(data.get(key), str) and data[key] for key in ("transactionId", "attemptId"))
        )
    return False


def audit(sessions: list[Path], logs: list[Path], require_terminal: bool) -> list[str]:
    findings: list[str] = []
    requests: dict[str, tuple[Path, int, dict[str, Any]]] = {}
    outcomes: dict[str, tuple[Path, int, dict[str, Any]]] = {}
    session_submissions: dict[str, list[int]] = defaultdict(list)
    session_consumptions: dict[str, list[int]] = defaultdict(list)
    last_session_snapshot: dict[str, dict[str, Any]] = {}
    log_submissions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    last_log_epochs: dict[str, tuple[int, ...]] = {}
    strict_log_candidates = 0

    for root in sessions:
        if not root.exists():
            findings.append(f"missing session path: {root}")
            continue
        for path, line_number, entry in iter_jsonl(root):
            if entry.get("type") == "message":
                message = entry.get("message")
                if isinstance(message, dict) and message.get("role") == "custom" and message.get("customType") == PROTOCOL:
                    details = message.get("details")
                    tx = details.get("transactionId") if isinstance(details, dict) else None
                    submission_count = details.get("submissionCount") if isinstance(details, dict) else None
                    if (
                        isinstance(tx, str)
                        and tx
                        and isinstance(submission_count, int)
                        and not isinstance(submission_count, bool)
                        and submission_count > 0
                    ):
                        session_consumptions[tx].append(submission_count)
                    else:
                        findings.append(f"{path}:{line_number}: malformed continuation consumption message")
                continue
            if entry.get("type") != "custom":
                continue
            custom_type = entry.get("customType")
            if custom_type not in CONTINUATION_TYPES:
                continue
            data = entry.get("data")
            if not valid_wire(str(custom_type), data):
                findings.append(f"{path}:{line_number}: malformed continuation record: {custom_type}")
                continue
            if custom_type == SAFETY_READY_TYPE:
                tx = data["transactionId"]
                if tx not in requests:
                    findings.append(f"{path}:{line_number}: safety-ready without prior request: {tx}")
                continue
            snapshot = data["snapshot"]
            tx = snapshot["transactionId"]
            if custom_type == REQUEST_TYPE:
                if tx in requests:
                    findings.append(f"{path}:{line_number}: duplicate continuation request: {tx}")
                else:
                    requests[tx] = (path, line_number, snapshot)
            elif custom_type == SNAPSHOT_TYPE:
                if tx not in requests:
                    findings.append(f"{path}:{line_number}: snapshot without prior request: {tx}")
                previous_snapshot = last_session_snapshot.get(tx)
                if previous_snapshot:
                    previous_epochs = tuple(previous_snapshot["epochs"][key] for key in ("session", "input", "agent", "turn", "message", "settlement"))
                    current_epochs = tuple(snapshot["epochs"][key] for key in ("session", "input", "agent", "turn", "message", "settlement"))
                    if any(current < old for current, old in zip(current_epochs, previous_epochs)):
                        findings.append(f"{path}:{line_number}: stale-session/lifecycle epoch regression: {tx}")
                    if snapshot["deadlineAt"] < previous_snapshot["deadlineAt"]:
                        findings.append(f"{path}:{line_number}: continuation deadline regressed: {tx}")
                last_session_snapshot[tx] = snapshot
                if snapshot["state"] == "submitted":
                    session_submissions[tx].append(snapshot["submissionCount"])
            elif custom_type == OUTCOME_TYPE:
                if tx not in requests:
                    findings.append(f"{path}:{line_number}: outcome without prior request: {tx}")
                if tx in outcomes:
                    findings.append(f"{path}:{line_number}: duplicate durable outcome: {tx}")
                else:
                    outcomes[tx] = (path, line_number, snapshot)

    for root in logs:
        if not root.exists():
            findings.append(f"missing log path: {root}")
            continue
        for path, line_number, record in iter_jsonl(root):
            event = record.get("event")
            tx = record.get("transactionId")
            # The shared pi-vcc log also contains ordinary diagnostics such as
            # compaction_failed/manual_compaction_complete. Any record with the
            # strict timestamp/transaction shape claims to be a continuation
            # transaction and must be audited even if no durable request
            # correlates it. Ordinary diagnostics omit that strict shape.
            strict_shape = isinstance(record.get("timestampEpoch"), int) and isinstance(tx, str) and bool(tx)
            if not strict_shape:
                continue
            strict_log_candidates += 1
            if sessions and tx not in requests:
                findings.append(f"{path}:{line_number}: continuation log without durable request: {tx}")
            keys = set(record)
            unknown = keys - LOG_KEYS
            forbidden = keys & FORBIDDEN
            if unknown:
                findings.append(f"{path}:{line_number}: unknown continuation log keys: {sorted(unknown)}")
            if forbidden:
                findings.append(f"{path}:{line_number}: privacy-forbidden continuation log keys: {sorted(forbidden)}")
            if event not in LOG_EVENTS or not isinstance(tx, str) or not tx:
                findings.append(f"{path}:{line_number}: malformed continuation log record")
                continue
            if not all(isinstance(record.get(key), int) and not isinstance(record[key], bool) and record[key] >= 0 for key in EPOCH_KEYS):
                findings.append(f"{path}:{line_number}: malformed continuation log epochs: {tx}")
                continue
            epochs = tuple(record[key] for key in EPOCH_KEYS)
            previous = last_log_epochs.get(tx)
            if previous and any(current < old for current, old in zip(epochs, previous)):
                findings.append(f"{path}:{line_number}: stale-session/lifecycle epoch regression: {tx}")
            last_log_epochs[tx] = epochs
            if event == "submitted":
                log_submissions[tx].append(record)
                request = requests.get(tx)
                if request and record["sessionEpoch"] < request[2]["epochs"]["session"]:
                    findings.append(f"{path}:{line_number}: stale-session send: {tx}")

    if logs and not sessions and strict_log_candidates == 0:
        findings.append("log-only audit requires at least one auditable continuation record")
    if require_terminal:
        for tx in sorted(set(requests) - set(outcomes)):
            findings.append(f"nonterminal durable session transaction: {tx}")
    for tx in sorted(set(outcomes) - set(requests)):
        findings.append(f"durable outcome without request: {tx}")
    for tx, counts in sorted(session_submissions.items()):
        if len(counts) != len(set(counts)):
            findings.append(f"duplicate active session submission: {tx}")
    for tx, records in sorted(log_submissions.items()):
        counts = [record.get("submissionCount") for record in records]
        if len(counts) != len(set(counts)):
            findings.append(f"duplicate active log submission: {tx}")
    for tx, consumptions in sorted(session_consumptions.items()):
        submissions = set(session_submissions.get(tx, []))
        permitted = max(submissions, default=0)
        if tx not in requests:
            findings.append(f"continuation consumption without durable request: {tx}")
        if len(consumptions) > permitted:
            findings.append(f"more continuation consumptions than submissions: {tx}")
        if any(ordinal not in submissions for ordinal in consumptions):
            findings.append(f"continuation consumption without matching submission ordinal: {tx}")
        if len(consumptions) != len(set(consumptions)):
            findings.append(f"duplicate continuation consumption submission ordinal: {tx}")
    return findings


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")


def self_test() -> list[str]:
    base_snapshot = {
        "protocol": PROTOCOL, "version": VERSION, "transactionId": "tx-good", "origin": "compact_context",
        "reason": "compacted", "attemptId": "attempt-good", "resumePolicy": "active", "state": "created",
        "createdAt": 100, "deadlineAt": 200, "pendingToolCount": 0, "submissionCount": 0,
        "retryCount": 0, "retryLimit": 1,
        "epochs": {"session": 1, "input": 0, "agent": 0, "turn": 0, "message": 0, "settlement": 0},
    }
    terminal = {**base_snapshot, "state": "settled", "terminalReason": "progressed_then_agent_settled", "submissionCount": 1}
    request = {"type": "custom", "customType": REQUEST_TYPE, "data": {"protocol": PROTOCOL, "version": VERSION, "kind": "request", "snapshot": base_snapshot}}
    outcome = {"type": "custom", "customType": OUTCOME_TYPE, "data": {"protocol": PROTOCOL, "version": VERSION, "kind": "outcome", "transactionId": "tx-good", "terminalState": "settled", "terminalReason": "progressed_then_agent_settled", "snapshot": terminal}}
    ordinary_log = {"timestamp": "2026-01-01", "event": "manual_compaction_complete", "cwd": "/tmp"}
    continuation_log = {
        "timestampEpoch": 150, "event": "submitted", "transactionId": "tx-good", "attemptId": "attempt-good",
        "origin": "compact_context", "reason": "compacted", "resumePolicy": "active", "state": "submitted",
        "retryCount": 0, "retryLimit": 1, "submissionCount": 1, "elapsedMs": 50, "deadlineAt": 200,
        "pendingToolCount": 0, "sessionEpoch": 1, "inputEpoch": 0, "agentEpoch": 0, "turnEpoch": 0,
        "messageEpoch": 0, "settlementEpoch": 0,
    }
    with tempfile.TemporaryDirectory(prefix="pi-vcc-audit-self-test-") as temp:
        root = Path(temp)
        sessions = root / "sessions.jsonl"
        logs = root / "logs.jsonl"
        write_jsonl(sessions, [request, outcome])
        write_jsonl(logs, [ordinary_log, continuation_log])
        if audit([sessions], [logs], True):
            return ["self-test valid fixture unexpectedly failed"]
        write_jsonl(sessions, [request])
        findings = audit([sessions], [logs], True)
        if not any("nonterminal durable session transaction" in finding for finding in findings):
            return ["self-test did not require durable session outcome"]
        malformed = {"type": "custom", "customType": REQUEST_TYPE, "data": {"kind": "request"}}
        write_jsonl(sessions, [malformed])
        findings = audit([sessions], [], False)
        if not any("malformed continuation record" in finding for finding in findings):
            return ["self-test did not detect malformed continuation record"]
        submitted = {**base_snapshot, "state": "submitted", "submissionCount": 1}
        snapshot = {"type": "custom", "customType": SNAPSHOT_TYPE, "data": {"protocol": PROTOCOL, "version": VERSION, "kind": "snapshot", "snapshot": submitted}}
        first_consumption = {
            "type": "message",
            "message": {"role": "custom", "customType": PROTOCOL, "content": "continue", "details": {"transactionId": "tx-good", "submissionCount": 1}},
        }
        write_jsonl(sessions, [request, snapshot, first_consumption, first_consumption, outcome])
        findings = audit([sessions], [logs], True)
        if not any("duplicate continuation consumption submission ordinal" in finding for finding in findings):
            return ["self-test did not detect repeated continuation submission ordinal"]
        if not any("more continuation consumptions than submissions" in finding for finding in findings):
            return ["self-test did not enforce one consumption per submission"]
        first_retry = {**submitted, "submissionCount": 2, "retryCount": 1}
        first_retry_snapshot = {"type": "custom", "customType": SNAPSHOT_TYPE, "data": {"protocol": PROTOCOL, "version": VERSION, "kind": "snapshot", "snapshot": first_retry}}
        second_consumption = {
            "type": "message",
            "message": {"role": "custom", "customType": PROTOCOL, "content": "continue", "details": {"transactionId": "tx-good", "submissionCount": 2}},
        }
        second_retry = {**submitted, "submissionCount": 3, "retryCount": 2, "retryLimit": 2}
        second_retry_snapshot = {"type": "custom", "customType": SNAPSHOT_TYPE, "data": {"protocol": PROTOCOL, "version": VERSION, "kind": "snapshot", "snapshot": second_retry}}
        third_consumption = {
            "type": "message",
            "message": {"role": "custom", "customType": PROTOCOL, "content": "continue", "details": {"transactionId": "tx-good", "submissionCount": 3}},
        }
        retry_terminal = {**terminal, "submissionCount": 3, "retryCount": 2, "retryLimit": 2}
        retry_outcome = {**outcome, "data": {**outcome["data"], "snapshot": retry_terminal}}
        write_jsonl(sessions, [request, snapshot, first_consumption, first_retry_snapshot, second_consumption, second_retry_snapshot, third_consumption, retry_outcome])
        if audit([sessions], [logs], True):
            return ["self-test rejected two legitimate retries with distinct submission ordinals"]
        write_jsonl(sessions, [request, outcome])
        malformed_uncorrelated_log = {
            "timestampEpoch": 160, "transactionId": "tx-malformed", "event": "submitted",
            "sessionEpoch": 1, "inputEpoch": 0, "agentEpoch": 0, "turnEpoch": 0,
            "messageEpoch": 0, "settlementEpoch": 0, "content": "private continuation payload",
        }
        write_jsonl(logs, [ordinary_log, continuation_log, malformed_uncorrelated_log])
        findings = audit([sessions], [logs], False)
        if not any("continuation log without durable request" in finding for finding in findings):
            return ["self-test sessions audit ignored an uncorrelated continuation record"]
        if not any("privacy-forbidden continuation log keys" in finding for finding in findings):
            return ["self-test sessions audit ignored privacy-invalid continuation fields"]
        write_jsonl(logs, [ordinary_log, {"timestampEpoch": 160, "transactionId": "uncorrelated", "event": "bogus"}])
        findings = audit([], [logs], False)
        if not any("malformed continuation log record" in finding for finding in findings):
            return ["self-test log-only audit ignored an uncorrelated malformed transaction record"]
        write_jsonl(logs, [ordinary_log])
        findings = audit([], [logs], False)
        if not any("requires at least one auditable continuation record" in finding for finding in findings):
            return ["self-test log-only audit falsely passed without a continuation record"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sessions", action="append", default=[], help="Session JSONL file or directory (repeatable)")
    parser.add_argument("--log", action="append", default=[], help="Mixed/shared JSONL log (repeatable)")
    parser.add_argument("--require-terminal", action="store_true", help="Require every persisted request to have a durable session outcome")
    parser.add_argument("--self-test", action="store_true", help="Run deterministic fixture tests")
    args = parser.parse_args()
    if args.self_test:
        findings = self_test()
    else:
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
