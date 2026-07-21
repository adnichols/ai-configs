#!/usr/bin/env python3
"""Restricted Good Morning Pi analytics disposition worker.

This process has one authority: validate a claimed Doct analytics-card action,
record its local display disposition, and close or release that exact claim. It
never invokes Hermes or any external work system.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
from typing import Any, Callable

BASE_URL = "https://doct.nodaste.com"
CARD_RE = re.compile(r"pi-analytics-card-([0-9a-f]{64})\Z")
COMMAND_RE = re.compile(r"pi-action (accept|investigate|defer|dismiss)\Z")
STATE_SCHEMA = "pi-analytics-actions/v1"
DEFAULT_REGISTRY = pathlib.Path.home() / ".hermes" / "state" / "gm-plan-maintainer" / "active-plans.json"
DEFAULT_LEDGER = pathlib.Path.home() / ".hermes" / "state" / "pi-analytics" / "actions.json"
DEFAULT_CONFIG = pathlib.Path.home() / ".hermes" / "config" / "pi-analytics-actions.json"
Runner = Callable[..., subprocess.CompletedProcess[str]]


class ClaimRejected(Exception):
    """The claimed analytics action is not authorized or current."""


class LedgerFailure(Exception):
    """The decision ledger could not be safely updated."""


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _claim_item(claim: dict[str, Any]) -> dict[str, Any]:
    item = _dict(claim.get("item"))
    if item:
        return item
    return _dict(_dict(claim.get("conversationPayload")).get("item"))


def _claim_thread(claim: dict[str, Any]) -> dict[str, Any]:
    thread = _dict(claim.get("thread"))
    if thread:
        return thread
    return _dict(_dict(claim.get("conversationPayload")).get("thread"))


def anchor_node_id(claim: dict[str, Any]) -> str:
    return str(_dict(_claim_thread(claim).get("anchor")).get("nodeId") or "")


def _submit_actions(claim: dict[str, Any]) -> list[str]:
    thread_routing = _dict(_claim_thread(claim).get("routingMetadata"))
    item_routing = _dict(_claim_item(claim).get("routingMetadata"))
    return [
        str(value) for value in (
            thread_routing.get("submitAction"), item_routing.get("submitAction")
        ) if value is not None
    ]


def submit_action(claim: dict[str, Any]) -> str:
    values = _submit_actions(claim)
    return values[0] if values and len(set(values)) == 1 else ""


def is_analytics_anchor(claim: dict[str, Any]) -> bool:
    """Recognize the reserved prefix so malformed analytics claims stay restricted."""
    return anchor_node_id(claim).startswith("pi-analytics-card-")


def claim_parts(claim: dict[str, Any]) -> tuple[str, str, str, str]:
    nested = _dict(claim.get("claim"))
    item = _claim_item(claim)
    item_claim = _dict(item.get("claim"))
    thread = _claim_thread(claim)
    document_id = str(
        claim.get("documentId")
        or nested.get("documentId")
        or item.get("documentId")
        or thread.get("documentId")
        or ""
    )
    workspace_id = str(
        claim.get("workspaceId")
        or nested.get("workspaceId")
        or item.get("workspaceId")
        or thread.get("workspaceId")
        or ""
    )
    thread_id = str(
        claim.get("threadId")
        or nested.get("threadId")
        or item.get("threadId")
        or thread.get("threadId")
        or ""
    )
    claim_id = str(claim.get("claimId") or nested.get("id") or item_claim.get("id") or "")
    return document_id, workspace_id, thread_id, claim_id


def _last_comment(claim: dict[str, Any]) -> dict[str, Any]:
    comments = _claim_thread(claim).get("comments")
    if not isinstance(comments, list) or not comments or not isinstance(comments[-1], dict):
        raise ClaimRejected("analytics action has no current user comment")
    return comments[-1]


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ClaimRejected(f"analytics action has invalid {label}")
    return value


def _sha256(value: Any, label: str) -> str:
    text = str(value or "")
    if not re.fullmatch(r"[0-9a-f]{64}", text):
        raise ClaimRejected(f"analytics action has invalid {label}")
    return text


def _load_json(path: pathlib.Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ClaimRejected(f"analytics {label} is unavailable") from exc
    if not isinstance(value, dict):
        raise ClaimRejected(f"analytics {label} is invalid")
    return value


def _active_registry_entry(registry: dict[str, Any], document_id: str) -> dict[str, Any]:
    plans = registry.get("active_plans")
    if not isinstance(plans, list):
        raise ClaimRejected("analytics card registry is invalid")
    matches = [
        item for item in plans
        if isinstance(item, dict)
        and str(item.get("document_id") or item.get("plan_id") or "") == document_id
        and item.get("status", "active") == "active"
        and item.get("routine") == "good_morning"
    ]
    if len(matches) != 1:
        raise ClaimRejected("analytics action is not for the current Good Morning document")
    return matches[0]


def validate_claim(
    claim: dict[str, Any], *, registry_path: pathlib.Path, aaron_user_id: str
) -> dict[str, Any]:
    if not aaron_user_id:
        raise ClaimRejected("analytics action author configuration is unavailable")
    routed_actions = _submit_actions(claim)
    if not routed_actions or any(value != "agent" for value in routed_actions):
        raise ClaimRejected("analytics card actions require the routed Agent action")

    card_id = anchor_node_id(claim)
    match = CARD_RE.fullmatch(card_id)
    if match is None:
        raise ClaimRejected("analytics action has an invalid card anchor")
    anchored_signal = match.group(1)
    selector = str(_dict(_claim_thread(claim).get("anchor")).get("selector") or "")
    allowed_selectors = {f"#{card_id}", f'[data-plan-node-id="{card_id}"]'}
    if selector not in allowed_selectors:
        raise ClaimRejected("analytics action has an invalid card selector")

    comment = _last_comment(claim)
    if comment.get("authorType") != "user" or str(comment.get("authorUserId") or "") != aaron_user_id:
        raise ClaimRejected("analytics action author is not authorized")
    body = str(comment.get("body") or "").strip()
    command = COMMAND_RE.fullmatch(body)
    if command is None:
        raise ClaimRejected("analytics card command is invalid")
    action = command.group(1)

    document_id, workspace_id, thread_id, claim_id = claim_parts(claim)
    if not all((document_id, workspace_id, thread_id, claim_id)):
        raise ClaimRejected("analytics claim identity is incomplete")
    item = _claim_item(claim)
    thread = _claim_thread(claim)
    nested = _dict(claim.get("claim"))
    item_claim = _dict(item.get("claim"))
    identity_candidates = {
        "document": [claim.get("documentId"), nested.get("documentId"), item.get("documentId"), item_claim.get("documentId"), thread.get("documentId")],
        "workspace": [claim.get("workspaceId"), nested.get("workspaceId"), item.get("workspaceId"), item_claim.get("workspaceId"), thread.get("workspaceId")],
        "thread": [claim.get("threadId"), nested.get("threadId"), item.get("threadId"), item_claim.get("threadId"), thread.get("threadId")],
    }
    for label, values in identity_candidates.items():
        present = {str(value) for value in values if value not in (None, "")}
        if len(present) != 1:
            raise ClaimRejected(f"analytics claim {label} identity is inconsistent")
    claim_version_raw = item.get("documentVersion")
    claim_version = (
        _positive_int(claim_version_raw, "document version")
        if claim_version_raw is not None
        else None
    )
    generated_hash = _sha256(item.get("generatedHtmlHash"), "generated HTML hash")
    source_hash = _sha256(item.get("sourceHash"), "source hash")
    source = _dict(claim.get("source"))
    top_generated_hash = _sha256(source.get("generatedHtmlHash"), "source generated HTML hash")
    top_source_hash = _sha256(source.get("sourceHash"), "source document hash")
    if len({generated_hash, source_hash, top_generated_hash, top_source_hash}) != 1:
        raise ClaimRejected("analytics action document hashes disagree")

    entry = _active_registry_entry(_load_json(registry_path, "card registry"), document_id)
    registry_workspace = str(entry.get("workspace_id") or "")
    if not registry_workspace or workspace_id != registry_workspace:
        raise ClaimRejected("analytics action workspace is not current")
    registry_version = _positive_int(entry.get("document_version"), "registry document version")
    registry_hash = _sha256(entry.get("html_sha256"), "registry HTML hash")
    if claim_version is not None and claim_version != registry_version:
        raise ClaimRejected("analytics action document version is stale")
    if generated_hash != registry_hash:
        raise ClaimRejected("analytics action document hash is stale")

    cards = entry.get("pi_analytics_cards")
    if not isinstance(cards, list):
        raise ClaimRejected("analytics card registry is invalid")
    matching_cards = [card for card in cards if isinstance(card, dict) and card.get("card_id") == card_id]
    if len(matching_cards) != 1:
        raise ClaimRejected("analytics card is not current")
    card = matching_cards[0]
    signal = _sha256(card.get("signal_key"), "signal key")
    evidence = _sha256(card.get("evidence_snapshot_id"), "evidence snapshot")
    if signal != anchored_signal:
        raise ClaimRejected("analytics card signal identity is invalid")

    claim_signal_raw = item.get("signalKey")
    claim_evidence_raw = item.get("evidenceSnapshotId")
    if claim_signal_raw is not None and _sha256(claim_signal_raw, "claim signal key") != signal:
        raise ClaimRejected("analytics claim signal is stale")
    if (
        claim_evidence_raw is not None
        and _sha256(claim_evidence_raw, "claim evidence snapshot") != evidence
    ):
        raise ClaimRejected("analytics claim evidence is stale")

    return {
        "action": action,
        "document_id": document_id,
        "document_version": registry_version,
        "card_id": card_id,
        "signal_key": signal,
        "evidence_snapshot_id": evidence,
        "workspace_id": workspace_id,
        "thread_id": thread_id,
        "claim_id": claim_id,
    }


def _empty_ledger() -> dict[str, Any]:
    return {"schema": STATE_SCHEMA, "deliveries": {}, "signals": {}}


def _read_ledger(path: pathlib.Path) -> dict[str, Any]:
    if not path.exists():
        return _empty_ledger()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LedgerFailure("analytics decision state is unreadable") from exc
    if (
        not isinstance(value, dict)
        or value.get("schema") != STATE_SCHEMA
        or not isinstance(value.get("deliveries"), dict)
        or not isinstance(value.get("signals"), dict)
    ):
        raise LedgerFailure("analytics decision state is invalid")
    return value


def _atomic_write(path: pathlib.Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_path = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = pathlib.Path(raw_path)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=True, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temp_path.unlink(missing_ok=True)


def delivery_key(decision: dict[str, Any]) -> str:
    value = "\0".join((
        decision["document_id"],
        str(decision["document_version"]),
        decision["card_id"],
        decision["evidence_snapshot_id"],
    ))
    return hashlib.sha256(f"pi-delivery-v1\0{value}".encode()).hexdigest()


def record_decision(
    path: pathlib.Path, decision: dict[str, Any], *, now: dt.datetime | None = None
) -> tuple[bool, dict[str, Any]]:
    decided_at = now or dt.datetime.now(dt.timezone.utc)
    if decided_at.tzinfo is None:
        raise LedgerFailure("analytics decision time must be timezone-aware")
    decided_at = decided_at.astimezone(dt.timezone.utc)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    with lock_path.open("a+", encoding="utf-8") as lock:
        os.chmod(lock_path, 0o600)
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        ledger = _read_ledger(path)
        key = delivery_key(decision)
        existing = ledger["deliveries"].get(key)
        if existing is not None:
            if not isinstance(existing, dict) or existing.get("action") not in {
                "accept", "investigate", "defer", "dismiss"
            }:
                raise LedgerFailure("analytics delivery identity conflicts with invalid decision state")
            return False, existing

        stamp = decided_at.isoformat().replace("+00:00", "Z")
        record = {
            "action": decision["action"],
            "card_id": decision["card_id"],
            "closure": {},
            "decided_at": stamp,
            "document_id": decision["document_id"],
            "document_version": decision["document_version"],
            "evidence_snapshot_id": decision["evidence_snapshot_id"],
            "signal_key": decision["signal_key"],
        }
        state = {"action": decision["action"], "decided_at": stamp}
        if decision["action"] in {"accept", "investigate"}:
            state["visible_until"] = (decided_at + dt.timedelta(days=7)).isoformat().replace("+00:00", "Z")
        elif decision["action"] == "defer":
            state["suppress_until"] = (decided_at + dt.timedelta(days=7)).isoformat().replace("+00:00", "Z")
        else:
            state["dismissed_active"] = True
        ledger["deliveries"][key] = record
        ledger["signals"][decision["signal_key"]] = state
        _atomic_write(path, ledger)
        return True, record


def _run_doct(argv: list[str], *, runner: Runner) -> subprocess.CompletedProcess[str]:
    try:
        proc = runner(argv, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Doct claim command timed out") from exc
    if proc.returncode != 0:
        raise RuntimeError("Doct claim command failed")
    return proc


def require_current_document_version(
    document_id: str, expected_version: int, *, runner: Runner
) -> None:
    proc = _run_doct(
        [
            "doct-agent", "documents", "get", "--base-url", BASE_URL,
            "--id", document_id, "--json",
        ],
        runner=runner,
    )
    try:
        value = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ClaimRejected("analytics document version could not be verified") from exc
    actual = value.get("version") if isinstance(value, dict) else None
    if isinstance(actual, bool) or not isinstance(actual, int) or actual != expected_version:
        raise ClaimRejected("analytics action document version is stale")


def _mark_closure_step(
    path: pathlib.Path, decision: dict[str, Any], record: dict[str, Any], step: str
) -> None:
    lock_path = path.with_suffix(path.suffix + ".lock")
    with lock_path.open("a+", encoding="utf-8") as lock:
        os.chmod(lock_path, 0o600)
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        ledger = _read_ledger(path)
        key = delivery_key(decision)
        persisted = ledger["deliveries"].get(key)
        if not isinstance(persisted, dict):
            raise LedgerFailure("analytics delivery disappeared before claim closure")
        closure = persisted.get("closure")
        if not isinstance(closure, dict):
            closure = {}
        closure[step] = True
        persisted["closure"] = closure
        _atomic_write(path, ledger)
        record["closure"] = dict(closure)


def finish_claim(
    decision: dict[str, Any], *, ledger_path: pathlib.Path, record: dict[str, Any],
    duplicate: bool, runner: Runner = subprocess.run,
) -> None:
    common = ["--base-url", BASE_URL, "--workspace-id", decision["workspace_id"], "--thread-id", decision["thread_id"]]
    label = decision["action"]
    body = f"Recorded Pi analytics disposition: {label}. No external work was created."
    summary = f"Pi analytics disposition {'already recorded' if duplicate else 'recorded'}: {label}"
    commands = {
        "reply": [
            "doct-agent", "plans", "reply", *common,
            "--document-id", decision["document_id"], "--body", body, "--json",
        ],
        "ack": [
            "doct-agent", "plans", "ack", *common,
            "--claim-id", decision["claim_id"], "--summary", summary, "--json",
        ],
        "resolve": [
            "doct-agent", "plans", "resolve", *common,
            "--claim-id", decision["claim_id"], "--summary", summary, "--json",
        ],
    }
    closure = record.get("closure") if isinstance(record.get("closure"), dict) else {}
    for step in ("reply", "ack", "resolve"):
        if closure.get(step) is True:
            continue
        _run_doct(commands[step], runner=runner)
        _mark_closure_step(ledger_path, decision, record, step)
        closure = record["closure"]


def reject_claim(
    claim: dict[str, Any], reason: str, *, registry_path: pathlib.Path,
    runner: Runner = subprocess.run,
) -> None:
    document_id, workspace_id, thread_id, claim_id = claim_parts(claim)
    if not all((document_id, workspace_id, thread_id, claim_id)):
        return
    try:
        entry = _active_registry_entry(_load_json(registry_path, "card registry"), document_id)
    except (ClaimRejected, LedgerFailure):
        return
    if str(entry.get("workspace_id") or "") != workspace_id:
        return
    common = ["--base-url", BASE_URL, "--workspace-id", workspace_id, "--thread-id", thread_id]
    body = f"Pi analytics action rejected: {reason}. No analytics state or external work changed."
    try:
        _run_doct([
            "doct-agent", "plans", "reply", *common,
            "--document-id", document_id, "--body", body, "--json",
        ], runner=runner)
        summary = "Rejected restricted Pi analytics action"
        _run_doct([
            "doct-agent", "plans", "ack", *common,
            "--claim-id", claim_id, "--summary", summary, "--json",
        ], runner=runner)
        _run_doct([
            "doct-agent", "plans", "resolve", *common,
            "--claim-id", claim_id, "--summary", summary, "--json",
        ], runner=runner)
    except RuntimeError:
        release_claim(claim, "restricted analytics rejection could not be completed", runner=runner)


def release_claim(claim: dict[str, Any], reason: str, *, runner: Runner = subprocess.run) -> None:
    _, workspace_id, thread_id, claim_id = claim_parts(claim)
    if not all((workspace_id, thread_id, claim_id)):
        return
    try:
        _run_doct([
            "doct-agent", "plans", "release", "--base-url", BASE_URL,
            "--workspace-id", workspace_id, "--thread-id", thread_id,
            "--claim-id", claim_id, "--reason", reason, "--json",
        ], runner=runner)
    except RuntimeError:
        pass


def process_claim(
    claim: dict[str, Any], *, registry_path: pathlib.Path, ledger_path: pathlib.Path,
    aaron_user_id: str, runner: Runner = subprocess.run, now: dt.datetime | None = None,
) -> int:
    try:
        decision = validate_claim(claim, registry_path=registry_path, aaron_user_id=aaron_user_id)
        require_current_document_version(
            decision["document_id"], decision["document_version"], runner=runner
        )
    except (ClaimRejected, RuntimeError) as exc:
        reject_claim(claim, str(exc), registry_path=registry_path, runner=runner)
        return 2
    try:
        created, recorded = record_decision(ledger_path, decision, now=now)
        if not created:
            decision = {**decision, "action": recorded["action"]}
    except LedgerFailure:
        release_claim(claim, "analytics decision state write failed; safe retry required", runner=runner)
        return 1
    try:
        finish_claim(
            decision, ledger_path=ledger_path, record=recorded,
            duplicate=not created, runner=runner,
        )
    except RuntimeError:
        release_claim(claim, "analytics decision recorded; claim close requires retry", runner=runner)
        return 1
    return 0


def configured_aaron_user_id(path: pathlib.Path) -> str:
    environment_value = os.environ.get("GM_PI_ANALYTICS_AARON_DOCT_USER_ID", "").strip()
    if environment_value:
        return environment_value
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    user_id = value.get("aaron_doct_user_id") if isinstance(value, dict) else None
    return user_id.strip() if isinstance(user_id, str) else ""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record one restricted Good Morning Pi analytics card action")
    parser.add_argument("--claim-file", required=True, type=pathlib.Path)
    parser.add_argument("--registry", type=pathlib.Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--ledger", type=pathlib.Path, default=DEFAULT_LEDGER)
    parser.add_argument("--config", type=pathlib.Path, default=DEFAULT_CONFIG)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    aaron_user_id = configured_aaron_user_id(args.config)
    try:
        try:
            claim = json.loads(args.claim_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return 2
    finally:
        args.claim_file.unlink(missing_ok=True)
    if not isinstance(claim, dict):
        return 2
    return process_claim(
        claim,
        registry_path=args.registry,
        ledger_path=args.ledger,
        aaron_user_id=aaron_user_id,
    )


if __name__ == "__main__":
    raise SystemExit(main())
