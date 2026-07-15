#!/usr/bin/env python3
"""Audit pi-vcc continuation sessions and metadata-only transaction logs."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

PROTOCOL = "pi-vcc-continuation"
VERSIONS = {1, 2}
REQUEST_TYPE = "pi-vcc-continuation-request"
SNAPSHOT_TYPE = "pi-vcc-continuation-snapshot"
OUTCOME_TYPE = "pi-vcc-continuation-outcome"
SAFETY_READY_TYPE = "pi-vcc-continuation-safety-ready"
CONTINUATION_TYPES = {REQUEST_TYPE, SNAPSHOT_TYPE, OUTCOME_TYPE, SAFETY_READY_TYPE}
TERMINAL = {"settled", "superseded", "failed_loudly"}
ACTIVE = {"created", "waiting_tools", "submitted", "consumed", "progressed", "stalled", "retrying"}
STATES = ACTIVE | TERMINAL
ORIGINS = {"package-command", "compact_context", "hard-backstop", "host-threshold", "host-overflow"}
REASONS = {"compacted", "no-safe-cut", "cancelled", "failed"}
RESUME_POLICIES = {"active", "terminal", "auto"}
ATTEMPT_OUTCOMES = {"compacted", "no-safe-cut", "cancellation", "failure"}
ASSISTANT_RESULTS = {"progress", "error", "aborted"}
TERMINAL_REASONS = {
    "progressed_then_agent_settled", "real_user_input", "independent_input", "session_replaced",
    "explicitly_stopped", "deadline_expired", "retry_limit_exhausted", "host_unavailable",
    "invalid_persistence", "reload_rehydrate_failed", "unrecoverable_error",
}
LOG_EVENTS = {"created", "waiting_tools", "submitted", "consumed", "progressed", "stalled", "settled", "superseded", "retrying", "failed"}
LOG_KEYS = {
    "timestampEpoch", "event", "transactionId", "compactionId", "attemptId", "requestId",
    "originatingRequestId", "origin", "reason", "resumePolicy", "state", "outcome",
    "terminalReason", "retryCount", "retryLimit", "submissionCount", "elapsedMs", "deadlineAt",
    "pendingToolCount", "sessionEpoch", "inputEpoch", "agentEpoch", "turnEpoch", "messageEpoch",
    "settlementEpoch", "phaseEpoch", "queuedAt", "activatedAt", "submittedAt",
    "acceptanceDeadlineAt", "acceptedAt", "lastProgressAt", "progressDeadlineAt",
    "toolStallDeadlineAt", "nextRetryAt", "runtimeId",
}
FORBIDDEN = {"preserve", "content", "message", "toolCallId", "pendingToolCallIds", "error", "stack", "password", "token", "secret"}
EPOCH_KEYS = ("sessionEpoch", "inputEpoch", "agentEpoch", "turnEpoch", "messageEpoch", "settlementEpoch")
V2_TIMING_KEYS = {
    "queuedAt", "activatedAt", "submittedAt", "acceptanceDeadlineAt", "acceptedAt",
    "lastProgressAt", "progressDeadlineAt", "toolStallDeadlineAt", "nextRetryAt",
}


def parse_since(value: str | None, now: float | None = None) -> float | None:
    if value is None:
        return None
    current = now if now is not None else datetime.now(tz=timezone.utc).timestamp()
    match = re.fullmatch(r"(\d+)([smhdw])", value.strip().lower())
    if match:
        multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
        return current - int(match.group(1)) * multipliers[match.group(2)]
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    except ValueError as exc:
        raise ValueError(f"invalid --since value: {value}") from exc


def entry_epoch_seconds(entry: dict[str, Any], path: Path) -> float:
    raw = entry.get("timestamp", entry.get("timestampEpoch"))
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return raw / 1000 if raw > 10_000_000_000 else float(raw)
    if isinstance(raw, str):
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.timestamp()
        except ValueError:
            pass
    try:
        return path.stat().st_mtime
    except OSError:
        return 0


def iter_jsonl(path: Path, findings: list[str]) -> Iterable[tuple[Path, int, dict[str, Any]]]:
    if path.is_dir():
        for child in sorted(path.rglob("*.jsonl")):
            yield from iter_jsonl(child, findings)
        return
    try:
        handle = path.open("r", encoding="utf-8", errors="replace")
    except OSError as exc:
        findings.append(f"{path}: unreadable JSONL: {exc}")
        return
    with handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                findings.append(f"{path}:{line_number}: malformed JSONL line: {exc.msg}")
                continue
            if isinstance(value, dict):
                yield path, line_number, value
            else:
                findings.append(f"{path}:{line_number}: JSONL value is not an object")


def is_nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def is_timestamp(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0 and value != float("inf")


def exact_keys(value: dict[str, Any], required: set[str], optional: set[str] | None = None) -> bool:
    allowed = required | (optional or set())
    return required <= set(value) and set(value) <= allowed


def valid_optional_nonempty_string(value: dict[str, Any], key: str) -> bool:
    return key not in value or (isinstance(value[key], str) and bool(value[key]))


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
    optional = {
        "compactionId", "requestId", "originatingRequestId", "consumedEpochs", "lastAssistantResult",
        "terminalReason", "phaseEpoch", "stalledWarningIssued", *V2_TIMING_KEYS,
    }
    if not exact_keys(value, required, optional):
        return False
    if value.get("protocol") != PROTOCOL or value.get("version") not in VERSIONS:
        return False
    if not isinstance(value.get("transactionId"), str) or not value["transactionId"] or not isinstance(value.get("attemptId"), str) or not value["attemptId"]:
        return False
    if value.get("origin") not in ORIGINS or value.get("reason") not in REASONS or value.get("resumePolicy") not in RESUME_POLICIES or value.get("state") not in STATES:
        return False
    if request and value["state"] != "created":
        return False
    if not is_timestamp(value.get("createdAt")) or not is_timestamp(value.get("deadlineAt")):
        return False
    if not all(is_nonnegative_int(value.get(key)) for key in ("pendingToolCount", "submissionCount", "retryCount", "retryLimit")):
        return False
    if not valid_epochs(value.get("epochs")):
        return False
    if value.get("version") == 2 and (not is_nonnegative_int(value.get("phaseEpoch")) or not is_timestamp(value.get("queuedAt"))):
        return False
    if any(key in value and not is_timestamp(value[key]) for key in V2_TIMING_KEYS):
        return False
    if not all(valid_optional_nonempty_string(value, key) for key in ("compactionId", "requestId", "originatingRequestId")):
        return False
    if "consumedEpochs" in value and not valid_epochs(value["consumedEpochs"]):
        return False
    if "lastAssistantResult" in value and value["lastAssistantResult"] not in ASSISTANT_RESULTS:
        return False
    if value["state"] in TERMINAL:
        return value.get("terminalReason") in TERMINAL_REASONS
    return "terminalReason" not in value


def valid_wire(custom_type: str, data: Any) -> bool:
    if not isinstance(data, dict) or data.get("protocol") != PROTOCOL or data.get("version") not in VERSIONS:
        return False
    if custom_type == REQUEST_TYPE:
        required = {"protocol", "version", "kind", "snapshot"}
        if not exact_keys(data, required, {"outcomeHint"}):
            return False
        return (
            data.get("kind") == "request" and valid_snapshot(data.get("snapshot"), request=True) and
            ("outcomeHint" not in data or data["outcomeHint"] in ATTEMPT_OUTCOMES)
        )
    if custom_type == SNAPSHOT_TYPE:
        return exact_keys(data, {"protocol", "version", "kind", "snapshot"}) and data.get("kind") == "snapshot" and valid_snapshot(data.get("snapshot"))
    if custom_type == OUTCOME_TYPE:
        required = {"protocol", "version", "kind", "transactionId", "terminalState", "terminalReason", "snapshot"}
        if not exact_keys(data, required):
            return False
        snapshot = data.get("snapshot")
        return (
            data.get("kind") == "outcome" and isinstance(data.get("transactionId"), str) and bool(data["transactionId"]) and
            valid_snapshot(snapshot) and data.get("terminalState") in TERMINAL and
            data.get("terminalReason") in TERMINAL_REASONS and
            data.get("transactionId") == snapshot.get("transactionId") and
            data.get("terminalState") == snapshot.get("state") and
            data.get("terminalReason") == snapshot.get("terminalReason")
        )
    if custom_type == SAFETY_READY_TYPE:
        required = {"protocol", "version", "kind", "transactionId", "attemptId"}
        return (
            exact_keys(data, required, {"requestId"}) and data.get("kind") == "safety-ready" and
            all(isinstance(data.get(key), str) and data[key] for key in ("transactionId", "attemptId")) and
            valid_optional_nonempty_string(data, "requestId")
        )
    return False


def valid_continuation_message_details(value: Any) -> bool:
    required = {"protocol", "version", "transactionId", "attemptId", "submissionCount"}
    optional = {"compactionId", "requestId", "originatingRequestId"}
    return (
        isinstance(value, dict) and exact_keys(value, required, optional) and
        value.get("protocol") == PROTOCOL and value.get("version") in VERSIONS and
        all(isinstance(value.get(key), str) and value[key] for key in ("transactionId", "attemptId")) and
        is_nonnegative_int(value.get("submissionCount")) and value["submissionCount"] > 0 and
        all(valid_optional_nonempty_string(value, key) for key in optional)
    )


def matching_continuation_details(snapshot: dict[str, Any], details: dict[str, Any]) -> bool:
    if snapshot.get("protocol") != PROTOCOL or snapshot.get("version") not in VERSIONS:
        return False
    if not valid_continuation_message_details(details):
        return False
    return (
        details["transactionId"] == snapshot.get("transactionId") and
        details["attemptId"] == snapshot.get("attemptId") and
        details["submissionCount"] == snapshot.get("submissionCount") and
        all(details.get(key) == snapshot.get(key) for key in ("compactionId", "requestId", "originatingRequestId"))
    )


def continuation_message_details(entry: dict[str, Any]) -> dict[str, Any] | None:
    if entry.get("type") == "custom_message" and entry.get("customType") == PROTOCOL:
        details = entry.get("details")
        if details is None and isinstance(entry.get("data"), dict):
            details = entry["data"].get("details")
        return details if isinstance(details, dict) else None
    if entry.get("type") == "message":
        message = entry.get("message")
        if isinstance(message, dict) and message.get("role") == "custom" and message.get("customType") == PROTOCOL:
            details = message.get("details")
            return details if isinstance(details, dict) else None
    return None


def audit(sessions: list[Path], logs: list[Path], require_terminal: bool, since: float | None = None) -> list[str]:
    findings: list[str] = []
    requests: dict[str, tuple[Path, int, dict[str, Any]]] = {}
    outcomes: dict[str, tuple[Path, int, dict[str, Any]]] = {}
    session_submissions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    session_snapshots: dict[str, list[dict[str, Any]]] = defaultdict(list)
    durable_acceptances: dict[str, list[dict[str, Any]]] = defaultdict(list)
    last_session_snapshot: dict[str, dict[str, Any]] = {}
    log_submissions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    last_log_epochs: dict[str, tuple[int, ...]] = {}
    seen_entry_ids: set[str] = set()
    strict_log_candidates = 0

    for root in sessions:
        if not root.exists():
            findings.append(f"missing session path: {root}")
            continue
        for path, line_number, entry in iter_jsonl(root, findings):
            if since is not None and entry_epoch_seconds(entry, path) < since:
                continue
            entry_id = entry.get("id")
            if isinstance(entry_id, str) and entry_id:
                if entry_id in seen_entry_ids:
                    continue
                seen_entry_ids.add(entry_id)

            details = continuation_message_details(entry)
            if details is not None:
                if valid_continuation_message_details(details):
                    durable_acceptances[details["transactionId"]].append(details)
                else:
                    findings.append(f"{path}:{line_number}: malformed continuation custom_message")
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
                previous = last_session_snapshot.get(tx)
                if previous:
                    old_epochs = tuple(previous["epochs"][key] for key in ("session", "input", "agent", "turn", "message", "settlement"))
                    new_epochs = tuple(snapshot["epochs"][key] for key in ("session", "input", "agent", "turn", "message", "settlement"))
                    if any(current < old for current, old in zip(new_epochs, old_epochs)):
                        findings.append(f"{path}:{line_number}: stale-session/lifecycle epoch regression: {tx}")
                    if snapshot.get("phaseEpoch", 0) < previous.get("phaseEpoch", 0):
                        findings.append(f"{path}:{line_number}: continuation phase epoch regressed: {tx}")
                last_session_snapshot[tx] = snapshot
                session_snapshots[tx].append(snapshot)
                if snapshot["state"] == "submitted":
                    session_submissions[tx].append(snapshot)
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
        for path, line_number, record in iter_jsonl(root, findings):
            if since is not None and entry_epoch_seconds(record, path) < since:
                continue
            event = record.get("event")
            tx = record.get("transactionId")
            strict_shape = isinstance(record.get("timestampEpoch"), int) and isinstance(tx, str) and bool(tx)
            if not strict_shape:
                continue
            strict_log_candidates += 1
            if sessions and tx not in requests:
                findings.append(f"{path}:{line_number}: continuation log without durable request: {tx}")
            unknown = set(record) - LOG_KEYS
            forbidden = set(record) & FORBIDDEN
            if unknown:
                findings.append(f"{path}:{line_number}: unknown continuation log keys: {sorted(unknown)}")
            if forbidden:
                findings.append(f"{path}:{line_number}: privacy-forbidden continuation log keys: {sorted(forbidden)}")
            if event not in LOG_EVENTS:
                findings.append(f"{path}:{line_number}: malformed continuation log record")
                continue
            if not all(is_nonnegative_int(record.get(key)) for key in EPOCH_KEYS):
                findings.append(f"{path}:{line_number}: malformed continuation log epochs: {tx}")
                continue
            epochs = tuple(record[key] for key in EPOCH_KEYS)
            previous = last_log_epochs.get(tx)
            if previous and any(current < old for current, old in zip(epochs, previous)):
                findings.append(f"{path}:{line_number}: stale-session/lifecycle epoch regression: {tx}")
            last_log_epochs[tx] = epochs
            if event == "submitted":
                log_submissions[tx].append(record)

    if logs and not sessions and strict_log_candidates == 0:
        findings.append("log-only audit requires at least one auditable continuation record")
    if require_terminal:
        for tx in sorted(set(requests) - set(outcomes)):
            findings.append(f"nonterminal durable session transaction: {tx}")
    for tx, snapshots in sorted(session_submissions.items()):
        counts = [snapshot["submissionCount"] for snapshot in snapshots]
        if len(counts) != len(set(counts)):
            findings.append(f"duplicate active session submission: {tx}")
    for tx, records in sorted(log_submissions.items()):
        counts = [record.get("submissionCount") for record in records]
        if len(counts) != len(set(counts)):
            findings.append(f"duplicate active log submission: {tx}")
    runtime_acceptances: dict[str, dict[int, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for tx, details_list in sorted(durable_acceptances.items()):
        submissions = session_submissions.get(tx, [])
        if tx not in requests:
            findings.append(f"continuation custom_message without durable request: {tx}")
        for details in details_list:
            if any(matching_continuation_details(snapshot, details) for snapshot in submissions):
                runtime_acceptances[tx][details["submissionCount"]].append(details)
            else:
                findings.append(f"continuation custom_message without runtime-matching submission identity: {tx}")
        # Runtime matching intentionally dual-reads V1/V2 details. Protocol
        # version therefore cannot split exact-one identity for the same
        # transaction attempt, request correlation, and submission ordinal.
        identities = [(
            details["transactionId"], details["attemptId"], details["submissionCount"],
            details.get("compactionId"), details.get("requestId"), details.get("originatingRequestId"),
        ) for details in details_list]
        if len(identities) != len(set(identities)):
            findings.append(f"duplicate continuation custom_message submission identity: {tx}")

    for tx in sorted(set(session_snapshots) | set(runtime_acceptances)):
        accepted_ordinals = {
            snapshot["submissionCount"]
            for snapshot in session_snapshots.get(tx, [])
            if snapshot["submissionCount"] > 0 and (
                "acceptedAt" in snapshot or snapshot["state"] in {"consumed", "progressed", "stalled"}
            )
        } | set(runtime_acceptances.get(tx, {}))
        for ordinal in sorted(accepted_ordinals):
            count = len(runtime_acceptances.get(tx, {}).get(ordinal, []))
            if count != 1:
                findings.append(
                    f"accepted continuation submission ordinal requires exactly one runtime-matching durable delivery: {tx} ordinal={ordinal} (found {count})"
                )

    for tx, (_path, _line_number, outcome) in sorted(outcomes.items()):
        if outcome["state"] != "settled":
            continue
        final_ordinal = outcome["submissionCount"]
        final_count = len(runtime_acceptances.get(tx, {}).get(final_ordinal, []))
        if final_count != 1:
            findings.append(
                f"settled continuation successful ordinal requires exactly one runtime-matching durable delivery: {tx} ordinal={final_ordinal} (found {final_count})"
            )
        accepted_ordinals = sorted(runtime_acceptances.get(tx, {}))
        for ordinal in accepted_ordinals:
            if ordinal == final_ordinal:
                continue
            explained_failure = any(
                snapshot["submissionCount"] == ordinal and
                snapshot.get("acceptedAt") is not None and
                snapshot.get("lastAssistantResult") in {"error", "aborted"}
                for snapshot in session_snapshots.get(tx, [])
            )
            if ordinal > final_ordinal or not explained_failure:
                findings.append(
                    f"settled continuation has unexplained accepted retry ordinal: {tx} ordinal={ordinal} final={final_ordinal}"
                )
    return findings


def write_jsonl(path: Path, records: Iterable[dict[str, Any] | str]) -> None:
    lines = [record if isinstance(record, str) else json.dumps(record) for record in records]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def self_test() -> list[str]:
    epochs = {"session": 1, "input": 0, "agent": 0, "turn": 0, "message": 0, "settlement": 0}
    base = {
        "protocol": PROTOCOL, "version": 2, "transactionId": "tx-good", "origin": "compact_context",
        "reason": "compacted", "compactionId": "compact-good", "attemptId": "attempt-good",
        "requestId": "request-good", "originatingRequestId": "origin-good", "resumePolicy": "active", "state": "created",
        "createdAt": 100, "queuedAt": 100, "deadlineAt": 15_100, "phaseEpoch": 0,
        "pendingToolCount": 0, "submissionCount": 0, "retryCount": 0, "retryLimit": 2, "epochs": epochs,
    }
    submitted = {**base, "state": "submitted", "submittedAt": 110, "acceptanceDeadlineAt": 15_110, "submissionCount": 1, "phaseEpoch": 1}
    terminal = {**submitted, "state": "settled", "acceptedAt": 120, "acceptanceDeadlineAt": None, "terminalReason": "progressed_then_agent_settled", "phaseEpoch": 4}
    terminal = {key: value for key, value in terminal.items() if value is not None}
    request = {"id": "request-id", "timestamp": 1_900_000_000, "type": "custom", "customType": REQUEST_TYPE, "data": {"protocol": PROTOCOL, "version": 2, "kind": "request", "snapshot": base}}
    snapshot = {"id": "snapshot-id", "timestamp": 1_900_000_001, "type": "custom", "customType": SNAPSHOT_TYPE, "data": {"protocol": PROTOCOL, "version": 2, "kind": "snapshot", "snapshot": submitted}}
    acceptance = {"id": "accept-id", "timestamp": 1_900_000_002, "type": "custom_message", "customType": PROTOCOL, "details": {"protocol": PROTOCOL, "version": 1, "transactionId": "tx-good", "attemptId": "attempt-good", "submissionCount": 1, "compactionId": "compact-good", "requestId": "request-good", "originatingRequestId": "origin-good"}}
    outcome = {"id": "outcome-id", "timestamp": 1_900_000_003, "type": "custom", "customType": OUTCOME_TYPE, "data": {"protocol": PROTOCOL, "version": 2, "kind": "outcome", "transactionId": "tx-good", "terminalState": "settled", "terminalReason": "progressed_then_agent_settled", "snapshot": terminal}}
    log = {
        "timestampEpoch": 1_900_000_001, "event": "submitted", "transactionId": "tx-good", "attemptId": "attempt-good",
        "origin": "compact_context", "reason": "compacted", "resumePolicy": "active", "state": "submitted",
        "retryCount": 0, "retryLimit": 2, "submissionCount": 1, "elapsedMs": 10, "deadlineAt": 15_110,
        "pendingToolCount": 0, "sessionEpoch": 1, "inputEpoch": 0, "agentEpoch": 0, "turnEpoch": 0,
        "messageEpoch": 0, "settlementEpoch": 0,
    }

    request_wire = request["data"]
    snapshot_wire = snapshot["data"]
    outcome_wire = outcome["data"]
    safety_wire = {
        "protocol": PROTOCOL, "version": 2, "kind": "safety-ready",
        "transactionId": "tx-good", "attemptId": "attempt-good", "requestId": "request-good",
    }
    message_details = acceptance["details"]
    valid_families = (
        (REQUEST_TYPE, request_wire),
        (SNAPSHOT_TYPE, snapshot_wire),
        (OUTCOME_TYPE, outcome_wire),
        (SAFETY_READY_TYPE, safety_wire),
    )
    if any(not valid_wire(custom_type, wire) for custom_type, wire in valid_families):
        return ["self-test rejected a valid continuation wire record family"]
    if not valid_continuation_message_details(message_details):
        return ["self-test rejected valid continuation message details"]
    for custom_type, wire in valid_families:
        if valid_wire(custom_type, {**wire, "privacyExpansion": "must-not-pass"}):
            return [f"self-test allowed extra field on {custom_type}"]
    if valid_continuation_message_details({**message_details, "privacyExpansion": "must-not-pass"}):
        return ["self-test allowed extra field on continuation message details"]
    if valid_snapshot({**submitted, "privacyExpansion": "must-not-pass"}):
        return ["self-test allowed extra field on continuation snapshot"]
    if valid_wire(REQUEST_TYPE, {**request_wire, "initiator": "compact_context"}):
        return ["self-test allowed non-wire initiator expansion on continuation request"]
    if valid_wire(OUTCOME_TYPE, {**outcome_wire, "actions": ["continue"]}):
        return ["self-test allowed terminal actions expansion on continuation outcome"]

    invalid_snapshot_enums = {
        "origin": "other-origin",
        "reason": "other-reason",
        "resumePolicy": "later",
        "state": "other-state",
        "lastAssistantResult": "other-result",
    }
    for field, invalid in invalid_snapshot_enums.items():
        candidate = {**submitted, field: invalid}
        if valid_snapshot(candidate):
            return [f"self-test allowed invalid snapshot enum: {field}"]
    invalid_terminal_reason = {**terminal, "terminalReason": "other-terminal-reason"}
    if valid_snapshot(invalid_terminal_reason):
        return ["self-test allowed invalid snapshot terminalReason"]
    if valid_wire(REQUEST_TYPE, {**request_wire, "outcomeHint": "other-outcome"}):
        return ["self-test allowed invalid request outcomeHint"]
    if valid_wire(OUTCOME_TYPE, {**outcome_wire, "terminalState": "other-terminal-state"}):
        return ["self-test allowed invalid outcome terminalState"]
    if valid_wire(OUTCOME_TYPE, {**outcome_wire, "terminalReason": "other-terminal-reason"}):
        return ["self-test allowed invalid outcome terminalReason"]

    with tempfile.TemporaryDirectory(prefix="pi-vcc-audit-self-test-") as temp:
        root = Path(temp)
        branch_a = root / "branch-a.jsonl"
        branch_b = root / "branch-b.jsonl"
        logs = root / "logs.jsonl"
        write_jsonl(branch_a, [request, snapshot, acceptance, outcome])
        write_jsonl(branch_b, [request, "{malformed}{concatenated}", {**acceptance, "id": "old-filtered", "timestamp": 10}, outcome])
        write_jsonl(logs, [log])
        findings = audit([root], [logs], True, since=1_800_000_000)
        if not any("malformed JSONL line" in finding for finding in findings):
            return ["self-test did not report malformed concatenated line"]
        non_malformed = [finding for finding in findings if "malformed JSONL line" not in finding]
        if non_malformed:
            return [f"self-test valid branch-copy fixture failed: {non_malformed}"]

        write_jsonl(branch_a, [request, snapshot, acceptance])
        write_jsonl(branch_b, [])
        findings = audit([root], [], True, since=1_800_000_000)
        if not any("nonterminal durable session transaction" in finding for finding in findings):
            return ["self-test did not require a terminal outcome"]

        write_jsonl(branch_a, [request, snapshot, {**acceptance, "id": "accept-2"}, {**acceptance, "id": "accept-3"}, outcome])
        findings = audit([branch_a], [], True)
        if not any("duplicate continuation custom_message submission identity" in finding for finding in findings):
            return ["self-test did not detect duplicate durable acceptance"]

        write_jsonl(branch_a, [request, snapshot, outcome])
        findings = audit([branch_a], [], True)
        if not any("successful ordinal requires exactly one runtime-matching durable delivery" in finding and "found 0" in finding for finding in findings):
            return ["self-test allowed a settled transaction with zero durable deliveries"]

        retry_submitted = {
            **submitted,
            "submittedAt": 130,
            "acceptanceDeadlineAt": 15_130,
            "submissionCount": 2,
            "retryCount": 1,
            "phaseEpoch": 5,
        }
        retry_snapshot = {
            "id": "retry-snapshot-id", "timestamp": 1_900_000_003, "type": "custom",
            "customType": SNAPSHOT_TYPE,
            "data": {"protocol": PROTOCOL, "version": 2, "kind": "snapshot", "snapshot": retry_submitted},
        }
        retry_acceptance = {
            **acceptance,
            "id": "retry-accept-id",
            "timestamp": 1_900_000_004,
            "details": {**acceptance["details"], "submissionCount": 2},
        }
        retry_terminal = {
            **retry_submitted,
            "state": "settled",
            "acceptedAt": 140,
            "terminalReason": "progressed_then_agent_settled",
            "phaseEpoch": 8,
        }
        retry_terminal.pop("acceptanceDeadlineAt", None)
        retry_outcome = {
            **outcome,
            "id": "retry-outcome-id",
            "timestamp": 1_900_000_005,
            "data": {
                "protocol": PROTOCOL, "version": 2, "kind": "outcome", "transactionId": "tx-good",
                "terminalState": "settled", "terminalReason": "progressed_then_agent_settled", "snapshot": retry_terminal,
            },
        }
        failed_first = {
            **submitted,
            "state": "consumed",
            "acceptedAt": 120,
            "lastAssistantResult": "aborted",
            "phaseEpoch": 3,
        }
        failed_first.pop("acceptanceDeadlineAt", None)
        failed_first_snapshot = {
            "id": "failed-first-snapshot-id", "timestamp": 1_900_000_002.5, "type": "custom",
            "customType": SNAPSHOT_TYPE,
            "data": {"protocol": PROTOCOL, "version": 2, "kind": "snapshot", "snapshot": failed_first},
        }
        write_jsonl(branch_a, [request, snapshot, acceptance, failed_first_snapshot, retry_snapshot, retry_acceptance, retry_outcome])
        findings = audit([branch_a], [], True)
        if findings:
            return [f"self-test rejected explained abort/error retry acceptances: {findings}"]

        write_jsonl(branch_a, [request, snapshot, acceptance, retry_snapshot, retry_acceptance, retry_outcome])
        findings = audit([branch_a], [], True)
        if not any("unexplained accepted retry ordinal" in finding for finding in findings):
            return ["self-test allowed an unexplained accepted earlier retry ordinal"]

        missing_first_acceptance = {
            **failed_first_snapshot,
            "id": "missing-first-acceptance-snapshot-id",
        }
        write_jsonl(branch_a, [request, snapshot, missing_first_acceptance, retry_snapshot, retry_acceptance, retry_outcome])
        findings = audit([branch_a], [], True)
        if not any("accepted continuation submission ordinal requires exactly one" in finding and "ordinal=1" in finding and "found 0" in finding for finding in findings):
            return ["self-test allowed an accepted retry ordinal with missing durable delivery"]

        duplicate_final = {**retry_acceptance, "id": "retry-accept-id-duplicate"}
        write_jsonl(branch_a, [request, snapshot, acceptance, failed_first_snapshot, retry_snapshot, retry_acceptance, duplicate_final, retry_outcome])
        findings = audit([branch_a], [], True)
        if not any("ordinal=2" in finding and "found 2" in finding for finding in findings):
            return ["self-test allowed duplicate durable delivery for the successful final ordinal"]

        cross_version_duplicate = {
            **acceptance,
            "id": "accept-v2-duplicate",
            "details": {**acceptance["details"], "version": 2},
        }
        write_jsonl(branch_a, [request, snapshot, acceptance, cross_version_duplicate, outcome])
        findings = audit([branch_a], [], True)
        if not any("duplicate continuation custom_message submission identity" in finding for finding in findings):
            return ["self-test allowed V1/V2 details to split one runtime-equivalent acceptance identity"]

        mismatched_attempt = {
            **acceptance,
            "id": "accept-wrong-attempt",
            "details": {**acceptance["details"], "attemptId": "attempt-other"},
        }
        write_jsonl(branch_a, [request, snapshot, mismatched_attempt, outcome])
        findings = audit([branch_a], [], True)
        if not any("without runtime-matching submission identity" in finding for finding in findings):
            return ["self-test accepted matching transaction/submission with a different attempt"]

        mismatched_identity = {
            **acceptance,
            "id": "accept-wrong-identity",
            "details": {**acceptance["details"], "requestId": "request-other"},
        }
        write_jsonl(branch_a, [request, snapshot, mismatched_identity, outcome])
        findings = audit([branch_a], [], True)
        if not any("without runtime-matching submission identity" in finding for finding in findings):
            return ["self-test accepted matching transaction/submission with different request identity"]

        if parse_since("24h", now=100_000) != 13_600:
            return ["self-test relative --since parsing failed"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sessions", action="append", default=[], help="Session JSONL file or directory (repeatable)")
    parser.add_argument("--log", action="append", default=[], help="Mixed/shared JSONL log (repeatable)")
    parser.add_argument("--require-terminal", action="store_true", help="Require every persisted request to have a durable session outcome")
    parser.add_argument("--since", help="Bound the audit to a relative window such as 24h/7d or an ISO-8601 timestamp")
    parser.add_argument("--self-test", action="store_true", help="Run deterministic fixture tests")
    args = parser.parse_args()
    if args.self_test:
        findings = self_test()
    else:
        if not args.sessions and not args.log:
            parser.error("at least one --sessions or --log path is required")
        try:
            findings = audit(
                [Path(item) for item in args.sessions],
                [Path(item) for item in args.log],
                args.require_terminal,
                parse_since(args.since),
            )
        except ValueError as exc:
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
