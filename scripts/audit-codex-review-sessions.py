#!/usr/bin/env python3
"""Privacy-preserving audit of Codex controller state and Pi completion delivery."""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

TERMINAL = {"succeeded", "failed", "timed_out", "cancelled", "interrupted"}
PROFILE_TOKENS = {
    "pre-pr-implementation": {"FINDINGS_TO_RESOLVE", "CLEAN_FOR_PR", "BLOCKED_BY_QUESTION", "REVIEW_INCOMPLETE_RERUN_NEEDED"},
    "generic-implementation": {"FINDINGS_TO_RESOLVE", "CLEAN_FOR_PR", "BLOCKED_BY_QUESTION", "REVIEW_INCOMPLETE_RERUN_NEEDED"},
    "run-plan-pm": {"PASS_SCOPED", "PASS_WITH_DOCUMENTED_OUT_OF_SCOPE_FOLLOW_UPS", "FIX_IN_SCOPE_FINDINGS", "BLOCKED_BY_SCOPE_QUESTION", "REVIEW_INCOMPLETE_RERUN_NEEDED"},
    "reviewed-html-plan": {"PLAN_EXECUTION_READY", "PLAN_NEEDS_REVISION", "BLOCKED_BY_PRODUCT_QUESTION", "REVIEW_INCOMPLETE_RERUN_NEEDED"},
    "generic-plan": {"PLAN_EXECUTION_READY", "PLAN_NEEDS_REVISION", "BLOCKED_BY_QUESTION", "REVIEW_INCOMPLETE_RERUN_NEEDED"},
}
REACHED_CODEX_CLASSIFICATIONS = {
    "CODEX_REVIEW_SUCCEEDED", "CODEX_REVIEW_ARTIFACT_MISSING", "CODEX_REVIEW_ARTIFACT_INVALID",
    "CODEX_REVIEW_ARTIFACT_POST_PUBLISH_INVALID", "CODEX_REVIEW_CODEX_EXIT_NONZERO",
    "CODEX_REVIEW_CODEX_SIGNAL", "CODEX_REVIEW_INNER_TIMEOUT", "CODEX_REVIEW_OUTER_TIMEOUT",
}


def structured_thread_ids(file: Path) -> set[str]:
    """Extract only structured thread identifiers; discard all event bodies."""
    result: set[str] = set()
    try:
        lines = file.open(errors="replace")
    except OSError:
        return result
    with lines:
        for line in lines:
            if "thread.started" not in line:
                continue
            try:
                row = json.loads(line)
            except (json.JSONDecodeError, AttributeError):
                continue
            if row.get("type") != "thread.started":
                continue
            value = row.get("thread_id")
            if not isinstance(value, str):
                thread = row.get("thread")
                value = thread.get("id") if isinstance(thread, dict) else row.get("id")
            if isinstance(value, str) and value:
                result.add(value)
    return result


def codex_session_index(root: Path) -> Counter[str]:
    files_by_thread: Counter[str] = Counter()
    if not root.is_dir():
        return files_by_thread
    for file in root.rglob("*.jsonl"):
        ids = structured_thread_ids(file)
        for thread_id in ids:
            files_by_thread[thread_id] += 1
        if not ids:
            name = file.name
            for candidate in re.findall(r"[0-9a-fA-F]{8,}(?:-[0-9a-fA-F-]{4,})?", name):
                files_by_thread[candidate] += 1
    return files_by_thread


def completion_counts(sessions_root: Path) -> Counter[str]:
    """Read only custom-message metadata; never retain prompt or output bodies."""
    counts: Counter[str] = Counter()
    if not sessions_root.is_dir():
        return counts
    for file in sessions_root.rglob("*.jsonl"):
        try:
            lines = file.open(errors="replace")
        except OSError:
            continue
        with lines:
            for line in lines:
                if "codex-review-completion" not in line:
                    continue
                try:
                    row = json.loads(line)
                except (json.JSONDecodeError, AttributeError):
                    continue
                message = row if row.get("type") == "custom_message" else row.get("message", {})
                if not isinstance(message, dict) or message.get("customType") != "codex-review-completion" or (row.get("type") != "custom_message" and message.get("role") != "custom"):
                    continue
                details = message.get("details")
                if isinstance(details, dict) and isinstance(details.get("deliveryId"), str):
                    counts[details["deliveryId"]] += 1
    return counts


def notification_eligible(data: dict) -> bool:
    return data.get("status") in TERMINAL and not (
        data.get("status") == "cancelled" and data.get("cancellationReason") == "session_shutdown"
    )


def audit(root: Path, require_terminal: bool = False, sessions_root: Path | None = None, codex_sessions_root: Path | None = None, job_ids: set[str] | None = None):
    errors = []
    seen = {}
    count = 0
    deliveries = completion_counts(sessions_root or (root / "sessions"))
    codex_sessions = codex_session_index(codex_sessions_root or (root / "codex-sessions"))
    states = sorted((root / "jobs").glob("*.state.json")) if (root / "jobs").is_dir() else sorted(root.glob("*.state.json"))
    for file in states:
        try:
            data = json.loads(file.read_text())
        except Exception as error:
            errors.append(f"{file}: malformed state: {error}")
            continue
        job = data.get("jobId")
        if job_ids and job not in job_ids:
            continue
        count += 1
        status = data.get("status")
        classification = data.get("classification")
        if job in seen:
            errors.append(f"{file}: duplicate jobId {job} (also {seen[job]})")
        seen[job] = file
        if require_terminal and status not in TERMINAL:
            errors.append(f"{file}: non-terminal status {status!r}")
        if status in TERMINAL and not classification:
            errors.append(f"{file}: terminal job lacks classification")
        delivery_id = data.get("deliveryId")
        if notification_eligible(data):
            found = deliveries.get(delivery_id, 0) if isinstance(delivery_id, str) else 0
            if found != 1:
                errors.append(f"{file}: eligible completion delivery count is {found}, expected 1")
            if data.get("deliveryState") != "delivered":
                errors.append(f"{file}: eligible terminal job deliveryState is not delivered")
        elif isinstance(delivery_id, str) and deliveries.get(delivery_id, 0):
            errors.append(f"{file}: notification-ineligible completion was delivered {deliveries[delivery_id]} time(s)")
        if status in TERMINAL and data.get("action") == "start":
            stdout = Path(data.get("stdoutLog", ""))
            thread_ids = structured_thread_ids(stdout)
            expects_thread = classification in REACHED_CODEX_CLASSIFICATIONS
            if len(thread_ids) > 1:
                errors.append(f"{file}: stdout contains multiple thread.started identifiers")
            elif not thread_ids and expects_thread:
                errors.append(f"{file}: terminal review reached Codex but stdout lacks thread.started identifier")
            elif thread_ids:
                thread_id = next(iter(thread_ids))
                corresponding = codex_sessions.get(thread_id, 0)
                if corresponding != 1:
                    errors.append(f"{file}: Codex session count for structured thread identifier is {corresponding}, expected 1")
        if status != "succeeded":
            continue
        if data.get("action") == "smoke":
            expected_tokens = None
        else:
            profile = data.get("verdictProfile")
            expected_tokens = PROFILE_TOKENS.get(profile)
            if expected_tokens is None:
                errors.append(f"{file}: succeeded review has unknown verdictProfile {profile!r}")
                continue
        output = Path(data.get("output", ""))
        if not output.exists():
            verdict = data.get("verdict")
            if data.get("action") != "smoke" and verdict not in expected_tokens:
                errors.append(f"{file}: succeeded job has neither retained output nor a profile-valid recorded verdict")
            continue
        try:
            text = output.read_text().replace("\r\n", "\n").replace("\r", "\n")
        except Exception as error:
            errors.append(f"{file}: retained succeeded output unreadable: {error}")
            continue
        nonempty = [line.rstrip(" \t") for line in text.split("\n") if line.rstrip(" \t")]
        if data.get("action") == "smoke":
            ok = nonempty == ["CODEX_REVIEW_SMOKE_READY"]
        else:
            match = re.fullmatch(r"VERDICT: ([A-Z0-9_]+)", nonempty[-1]) if nonempty else None
            ok = bool(match and match.group(1) in expected_tokens and data.get("verdict") in (None, match.group(1)))
        if not ok:
            errors.append(f"{file}: succeeded artifact ends without a verdict valid for the selected profile")
    if job_ids:
        for missing in sorted(job_ids - set(seen)):
            errors.append(f"requested jobId {missing} has no controller state")
    return count, errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-terminal", action="store_true")
    parser.add_argument("--sessions-root", type=Path, default=Path.home() / ".pi/agent/sessions")
    parser.add_argument("--codex-sessions-root", type=Path, default=Path.home() / ".codex/sessions")
    parser.add_argument("--job-id", action="append", dest="job_ids", help="audit only the named managed job (repeatable)")
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    count, errors = audit(args.root, args.require_terminal, args.sessions_root, args.codex_sessions_root, set(args.job_ids or []))
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"PASS: audited {count} Codex review jobs; terminal state, profile verdict, completion delivery, and Codex sessions agree")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
