#!/usr/bin/env python3
"""Fail-closed orchestration for independent read-only review legs.

The pure state machine remains transport-injected.  The runnable ``run``
command supplies a standard-library Herdr CLI adapter for reviewer targets and
coordinator-owned tabs that have already been created and started visibly.
It never launches reviewers or uses a hidden terminal transport.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import stat
import subprocess
import tempfile
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Dict, List, Mapping, Optional, Protocol, Sequence, Tuple


# `PASS` is the only green verdict emitted going forward. The legacy green
# tokens below are permanently read as green so historical records and
# in-flight reviewers stay valid.
CLEAN = "PASS"
INFRASTRUCTURE_FAILURE = "REVIEW_INFRASTRUCTURE_FAILURE"
PROFILE_MISMATCH = "REVIEW_ORCHESTRATOR_PROFILE_MISMATCH"
PASS_CLASS = "pass"
FINDINGS_CLASS = "findings"
BLOCKED_CLASS = "blocked"
INCOMPLETE_CLASS = "incomplete"
_VERDICT_CLASSES = {
    "PASS": PASS_CLASS,
    "CLEAN_FOR_PR": PASS_CLASS,
    "CLEAN": PASS_CLASS,
    "PASS_SCOPED": PASS_CLASS,
    "PASS_WITH_DOCUMENTED_OUT_OF_SCOPE_FOLLOW_UPS": PASS_CLASS,
    "PLAN_EXECUTION_READY": PASS_CLASS,
    "FINDINGS_TO_RESOLVE": FINDINGS_CLASS,
    "FIX_IN_SCOPE_FINDINGS": FINDINGS_CLASS,
    "PLAN_NEEDS_REVISION": FINDINGS_CLASS,
    "BLOCKED_BY_QUESTION": BLOCKED_CLASS,
    "BLOCKED_BY_SCOPE_QUESTION": BLOCKED_CLASS,
    "BLOCKED_BY_PRODUCT_QUESTION": BLOCKED_CLASS,
    "REVIEW_INCOMPLETE_RERUN_NEEDED": INCOMPLETE_CLASS,
}
_ALLOWED_VERDICT_CLASSES = frozenset(
    {PASS_CLASS, FINDINGS_CLASS, BLOCKED_CLASS, INCOMPLETE_CLASS}
)
_TRANSCRIPT_PRESENTATION_PREFIXES = ("• ", "⏺ ")
_HERDR_AGENT_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")
_BEGIN_RESULT_PREFIX = "BEGIN_REVIEW_RESULT "
_END_RESULT_PREFIX = "END_REVIEW_RESULT "


@dataclass(frozen=True)
class LegRequest:
    name: str
    prompt: str
    narrowed_retry_prompt: str
    allowed_verdicts: Sequence[str]
    timeout_seconds: float
    verdict_classes: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class PromptSubmission:
    accepted: bool
    full_prompt_visible_unsubmitted: bool = False
    detail: str = ""


@dataclass(frozen=True)
class RawReviewResult:
    state: str
    output: str
    candidate_fingerprint: str
    first_action_observed: bool = False
    detail: str = ""
    first_action_observed_at: Optional[float] = None
    structured_result_path: Optional[str] = None


class ReviewAdapter(Protocol):
    """Transport boundary implemented by Herdr production code or a fake."""

    def capture_fingerprint(self) -> str:
        ...

    def current_fingerprint(self) -> str:
        ...

    def prepare_leg(self, request: LegRequest, fingerprint: str):
        ...

    def submit_prompt(
        self, handle, prompt: str, nonce: str, fingerprint: str
    ) -> PromptSubmission:
        ...

    def send_enter(self, handle) -> bool:
        ...

    def prompt_accepted(self, handle) -> bool:
        ...

    def wait_for_result(self, handle, timeout_seconds: float) -> RawReviewResult:
        ...

    def cleanup_leg_is_current(
        self,
        handle,
        result_nonce: str,
        result_digest: str,
        result_evidence_source: str,
        result_evidence_path: Optional[str],
        allowed_verdicts: Sequence[str],
    ) -> bool:
        ...

    def cleanup_leg(self, handle) -> bool:
        ...


@dataclass(frozen=True)
class ReviewEvent:
    kind: str
    timestamp: float
    leg: Optional[str] = None
    detail: str = ""


@dataclass
class LegOutcome:
    name: str
    handle: object
    verdict: Optional[str] = None
    verdict_class: Optional[str] = None
    validation_complete: bool = False
    failure_kind: Optional[str] = None
    detail: str = ""
    elapsed_time: float = 0.0
    retried_unusable_output: bool = False
    prompt_accepted_at: Optional[float] = None
    settled_at: Optional[float] = None
    result_accepted_at: Optional[float] = None
    result_nonce: Optional[str] = None
    result_digest: Optional[str] = None
    result_evidence_source: str = "transcript"
    result_evidence_path: Optional[str] = None


@dataclass
class OrchestrationResult:
    status: str
    fingerprint: str
    legs: Dict[str, LegOutcome]
    events: List[ReviewEvent]
    candidate_wall_time: float
    all_prompts_submitted_before_first_wait: bool
    mode: str
    clean: bool = False
    cleanup_complete: bool = False


class _EventRecorder:
    def __init__(self, clock: Callable[[], float]):
        self._clock = clock
        self._events: List[ReviewEvent] = []
        self._lock = threading.Lock()

    def add(
        self,
        kind: str,
        leg: Optional[str] = None,
        detail: str = "",
        timestamp: Optional[float] = None,
    ) -> float:
        observed_at = self._clock() if timestamp is None else timestamp
        with self._lock:
            self._events.append(ReviewEvent(kind, observed_at, leg, detail))
        return observed_at

    def snapshot(self) -> List[ReviewEvent]:
        with self._lock:
            return sorted(self._events, key=lambda event: event.timestamp)


def _nonce() -> str:
    return secrets.token_hex(16)


def _current_fingerprint(adapter: ReviewAdapter) -> str:
    method = getattr(adapter, "current_fingerprint", None)
    if method is not None:
        return method()
    # Compatibility for a minimal adapter; production adapters should expose the
    # non-recording current_fingerprint operation explicitly.
    return adapter.capture_fingerprint()


def _classify_verdict(request: LegRequest, verdict: Optional[str]) -> Optional[str]:
    if verdict is None:
        return None
    if verdict in _VERDICT_CLASSES:
        return _VERDICT_CLASSES[verdict]
    return request.verdict_classes.get(verdict)


def _validate_verdict_profile(request: LegRequest) -> None:
    if not request.allowed_verdicts or request.timeout_seconds <= 0:
        raise ValueError("reviewer verdicts and timeout must be non-empty/positive")
    if any(value not in _ALLOWED_VERDICT_CLASSES for value in request.verdict_classes.values()):
        raise ValueError("verdict class values must be pass/findings/blocked/incomplete")
    if any(
        token in _VERDICT_CLASSES and _VERDICT_CLASSES[token] != verdict_class
        for token, verdict_class in request.verdict_classes.items()
    ):
        raise ValueError("shared workflow verdicts cannot be reclassified")
    unclassified = [
        verdict for verdict in request.allowed_verdicts
        if _classify_verdict(request, verdict) not in _ALLOWED_VERDICT_CLASSES
    ]
    if unclassified:
        raise ValueError(
            "allowed verdicts require outcome classes before launch: "
            + ", ".join(unclassified)
        )


@dataclass(frozen=True)
class _PromptDispatch:
    nonce: str
    accepted: bool
    pending_confirmation: bool
    accepted_at: Optional[float]
    started_at: float


def _dispatch_prompt(
    adapter: ReviewAdapter,
    request: LegRequest,
    handle,
    prompt: str,
    fingerprint: str,
    recorder: _EventRecorder,
    retry: bool,
    clock: Callable[[], float],
    defer_stall_confirmation: bool = False,
) -> _PromptDispatch:
    nonce = _nonce()
    # Candidate timing starts at the transport boundary, before submission can
    # block, rather than after Herdr reports acceptance.
    started_at = clock()
    submission = adapter.submit_prompt(handle, prompt, nonce, fingerprint)
    if submission.accepted:
        accepted_at = recorder.add(
            "prompt_accepted", request.name, "retry" if retry else "initial"
        )
        return _PromptDispatch(nonce, True, False, accepted_at, started_at)
    if not submission.full_prompt_visible_unsubmitted:
        return _PromptDispatch(nonce, False, False, None, started_at)

    recorder.add("prompt_stall_proven", request.name, "retry" if retry else "initial")
    if not adapter.send_enter(handle):
        return _PromptDispatch(nonce, False, False, None, started_at)
    if defer_stall_confirmation:
        recorder.add("prompt_confirmation_pending", request.name, "enter")
        return _PromptDispatch(nonce, False, True, None, started_at)
    if adapter.prompt_accepted(handle):
        accepted_at = recorder.add(
            "prompt_accepted", request.name, "retry-enter" if retry else "enter"
        )
        return _PromptDispatch(nonce, True, False, accepted_at, started_at)
    return _PromptDispatch(nonce, False, False, None, started_at)


def _submit(
    adapter: ReviewAdapter,
    request: LegRequest,
    handle,
    prompt: str,
    fingerprint: str,
    recorder: _EventRecorder,
    retry: bool,
    clock: Callable[[], float],
) -> Tuple[bool, str, Optional[float], float]:
    dispatched = _dispatch_prompt(
        adapter,
        request,
        handle,
        prompt,
        fingerprint,
        recorder,
        retry,
        clock,
    )
    return (
        dispatched.accepted,
        dispatched.nonce,
        dispatched.accepted_at,
        dispatched.started_at,
    )


def _normalize_transcript_line(line: str) -> str:
    """Remove only transport presentation added at the start of a line."""

    normalized = line.lstrip()
    for prefix in _TRANSCRIPT_PRESENTATION_PREFIXES:
        if normalized.startswith(prefix):
            return normalized[len(prefix) :]
    return normalized


def is_valid_herdr_agent_name(name: str) -> bool:
    """Herdr accepts 1-32 char names: lowercase letter start, [a-z0-9_-] only."""

    return bool(isinstance(name, str) and _HERDR_AGENT_NAME_RE.fullmatch(name))


def validate_herdr_agent_name(name: str, *, label: str = "agent name") -> str:
    if not is_valid_herdr_agent_name(name):
        raise ValueError(
            "{} must match Herdr's 1-32 char rule "
            "(lowercase letter start, then [a-z0-9_-]): {!r}".format(label, name)
        )
    return name


def short_herdr_agent_name(kind: str, salt: Optional[str] = None) -> str:
    """Build a short, Herdr-safe reviewer target name."""

    kind_token = re.sub(r"[^a-z0-9]+", "", (kind or "rvw").lower()) or "rvw"
    kind_token = kind_token[:8]
    token = (salt or secrets.token_hex(3)).lower()
    token = re.sub(r"[^a-z0-9]+", "", token) or secrets.token_hex(3)
    name = "rvw-{}-{}".format(kind_token, token[:12])
    return validate_herdr_agent_name(name[:32])


@dataclass(frozen=True)
class ExtractedReviewBlock:
    """A normalized result block paired with its exact accepted bytes."""

    normalized_lines: Tuple[str, ...]
    raw_span: str
    evidence_source: str = "transcript"
    evidence_path: Optional[str] = None


def _marker_targets(nonce: str) -> Tuple[str, str]:
    return (
        "{}{}".format(_BEGIN_RESULT_PREFIX, nonce),
        "{}{}".format(_END_RESULT_PREFIX, nonce),
    )


def _coalesce_wrapped_marker_lines(
    normalized_lines: Sequence[str],
    raw_lines: Sequence[str],
    nonce: str,
) -> Tuple[List[str], List[str]]:
    """Rejoin hard/soft-broken BEGIN/END fence lines for a known nonce.

    Terminal soft-wraps are usually repaired by Herdr ``recent-unwrapped``.
    Models and TUIs still emit real newlines mid-fence; those survive unwrap
    and must be joined here before exact marker matching.
    """

    begin, end = _marker_targets(nonce)
    markers = (begin, end)
    out_norm: List[str] = []
    out_raw: List[str] = []
    index = 0
    total = len(normalized_lines)
    while index < total:
        norm = normalized_lines[index]
        raw = raw_lines[index]
        if norm and any(marker.startswith(norm) and marker != norm for marker in markers):
            cursor = index + 1
            while cursor < total:
                nxt = normalized_lines[cursor]
                if nxt == "":
                    break
                candidate = norm + nxt
                if any(
                    marker == candidate or marker.startswith(candidate)
                    for marker in markers
                ):
                    norm = candidate
                    raw = raw + raw_lines[cursor]
                    cursor += 1
                    if norm in markers:
                        break
                    continue
                break
            out_norm.append(norm)
            out_raw.append(raw)
            index = cursor
            continue
        out_norm.append(norm)
        out_raw.append(raw)
        index += 1
    return out_norm, out_raw


def _extract_result_block(
    output: str, nonce: str
) -> Tuple[Optional[ExtractedReviewBlock], Optional[str], str]:
    """Find a nonce block, wrap-safe, last complete block wins.

    Preserves the accepted raw transcript span (including any hard wraps) so
    cleanup digests remain exact byte matches against the live pane.
    """

    if not nonce or any(ch.isspace() for ch in nonce):
        return None, "unusable_output", "invalid review nonce"

    begin, end = _marker_targets(nonce)
    raw_lines = output.splitlines(keepends=True)
    normalized_lines = [
        _normalize_transcript_line(line.rstrip("\r\n")) for line in raw_lines
    ]
    normalized_lines, raw_lines = _coalesce_wrapped_marker_lines(
        normalized_lines, raw_lines, nonce
    )
    # A valid duplicate is a sequence of fully closed blocks. Nested, unmatched,
    # or extra boundaries stay fail-closed: only then is choosing the last block
    # safe from accepting a partially overwritten/stale transcript.
    completed: List[Tuple[int, int]] = []
    open_begin: Optional[int] = None
    for index, line in enumerate(normalized_lines):
        if line == begin:
            if open_begin is not None:
                return None, "unusable_output", "nested or unmatched nonce boundary"
            open_begin = index
        elif line == end:
            if open_begin is None or index <= open_begin + 1:
                return None, "unusable_output", "nested or unmatched nonce boundary"
            completed.append((open_begin, index))
            open_begin = None
    if open_begin is not None or not completed:
        return None, "unusable_output", "missing or duplicate nonce boundary"

    begin_index, end_index = completed[-1]
    return (
        ExtractedReviewBlock(
            normalized_lines=tuple(normalized_lines[begin_index : end_index + 1]),
            raw_span="".join(raw_lines[begin_index : end_index + 1]),
        ),
        None,
        "",
    )


def _structured_result_block(
    payload: Mapping[str, Any], nonce: str, allowed_verdicts: Sequence[str]
) -> Tuple[Optional[ExtractedReviewBlock], Optional[str], str]:
    """Build a canonical block from a reviewer/coordinator result file."""

    if str(payload.get("nonce", "")) != nonce:
        return None, "unusable_output", "structured result nonce mismatch"
    verdict = payload.get("verdict")
    if not isinstance(verdict, str) or verdict not in allowed_verdicts:
        return None, "unusable_output", "structured result has invalid workflow verdict"
    body = payload.get("body", payload.get("review", ""))
    if isinstance(body, list):
        body_text = "\n".join(str(part) for part in body).strip()
    else:
        body_text = str(body or "").strip()
    if not body_text:
        return None, "unusable_output", "structured result body is empty"
    canonical = (
        "{}{}\n".format(_BEGIN_RESULT_PREFIX, nonce)
        + body_text
        + "\n"
        + "VERDICT: {}\n".format(verdict)
        + "{}{}\n".format(_END_RESULT_PREFIX, nonce)
    )
    block, failure_kind, detail = _extract_result_block(canonical, nonce)
    if block is None:
        return None, failure_kind, detail or "structured result could not be normalized"
    return block, None, ""


def load_structured_result_file(
    path: Path, nonce: str, allowed_verdicts: Sequence[str]
) -> Tuple[Optional[ExtractedReviewBlock], Optional[str], str]:
    try:
        payload = json.loads(path.read_text())
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return None, "unusable_output", "structured result unreadable: {}".format(error)
    if not isinstance(payload, dict):
        return None, "unusable_output", "structured result must be a JSON object"
    block, failure_kind, detail = _structured_result_block(payload, nonce, allowed_verdicts)
    if block is None:
        return None, failure_kind, detail
    return (
        ExtractedReviewBlock(
            normalized_lines=block.normalized_lines,
            raw_span=block.raw_span,
            evidence_source="structured",
            evidence_path=str(path.resolve()),
        ),
        None,
        "",
    )


def _verdict_from_block(
    block: ExtractedReviewBlock, allowed_verdicts: Sequence[str]
) -> Tuple[Optional[str], Optional[str], str]:
    body = [line for line in block.normalized_lines[1:-1] if line]
    if len(body) < 2:
        return None, "unusable_output", "empty review result"
    verdict_line = body[-1]
    if not verdict_line.startswith("VERDICT: "):
        return (
            None,
            "unusable_output",
            "verdict is not the final non-empty result line",
        )
    verdict = verdict_line[len("VERDICT: ") :]
    if verdict not in allowed_verdicts:
        return None, "unusable_output", "invalid workflow verdict"
    return verdict, None, ""


def _validate_result(
    raw: RawReviewResult,
    nonce: str,
    allowed_verdicts: Sequence[str],
) -> Tuple[Optional[str], Optional[str], str, Optional[ExtractedReviewBlock]]:
    if raw.state == "timeout":
        return None, "timeout", raw.detail or "reviewer timed out", None
    if raw.state != "settled":
        return (
            None,
            "provider_or_transport_failure",
            raw.detail or raw.output or raw.state,
            None,
        )

    if raw.structured_result_path:
        structured_path = Path(raw.structured_result_path)
        if structured_path.is_file():
            block, failure_kind, detail = load_structured_result_file(
                structured_path, nonce, allowed_verdicts
            )
            if block is not None:
                verdict, failure_kind, detail = _verdict_from_block(block, allowed_verdicts)
                if failure_kind is None:
                    return verdict, None, "", block
            # Fall through to transcript when the side-channel file is unusable so
            # wrap-safe pane capture can still accept a valid fence.

    block, failure_kind, detail = _extract_result_block(raw.output, nonce)
    if block is None:
        return None, failure_kind, detail, None
    verdict, failure_kind, detail = _verdict_from_block(block, allowed_verdicts)
    if failure_kind is not None:
        return None, failure_kind, detail, None
    return verdict, None, "", block


def _parse_result(
    raw: RawReviewResult,
    nonce: str,
    allowed_verdicts: Sequence[str],
) -> Tuple[Optional[str], Optional[str], str]:
    verdict, failure_kind, detail, _ = _validate_result(raw, nonce, allowed_verdicts)
    return verdict, failure_kind, detail


def _wait_and_validate(
    adapter: ReviewAdapter,
    request: LegRequest,
    outcome: LegOutcome,
    fingerprint: str,
    nonce: str,
    recorder: _EventRecorder,
    clock: Callable[[], float],
) -> LegOutcome:
    raw = adapter.wait_for_result(outcome.handle, request.timeout_seconds)
    accepted_nonce = nonce
    if raw.first_action_observed:
        recorder.add(
            "first_action",
            request.name,
            timestamp=raw.first_action_observed_at,
        )
    outcome.settled_at = recorder.add("settled", request.name, raw.state)
    verdict, failure_kind, detail, accepted_block = _validate_result(
        raw, nonce, request.allowed_verdicts
    )

    if raw.candidate_fingerprint != fingerprint:
        failure_kind = "stale_fingerprint"
        detail = "review result belongs to a different candidate fingerprint"
        verdict = None

    if failure_kind == "unusable_output":
        if _current_fingerprint(adapter) != fingerprint:
            failure_kind = "stale_fingerprint"
            detail = "candidate changed before narrowed unusable-output retry"
        else:
            outcome.retried_unusable_output = True
            accepted, retry_nonce, _, _ = _submit(
                adapter,
                request,
                outcome.handle,
                request.narrowed_retry_prompt,
                fingerprint,
                recorder,
                retry=True,
                clock=clock,
            )
            if not accepted:
                failure_kind = "prompt_not_accepted"
                detail = "narrowed retry prompt was not accepted"
            else:
                retry_raw = adapter.wait_for_result(outcome.handle, request.timeout_seconds)
                accepted_nonce = retry_nonce
                if retry_raw.first_action_observed:
                    recorder.add(
                        "first_action",
                        request.name,
                        "retry",
                        timestamp=retry_raw.first_action_observed_at,
                    )
                outcome.settled_at = recorder.add("settled", request.name, "retry:" + retry_raw.state)
                verdict, failure_kind, detail, accepted_block = _validate_result(
                    retry_raw, retry_nonce, request.allowed_verdicts
                )
                if retry_raw.candidate_fingerprint != fingerprint:
                    verdict = None
                    failure_kind = "stale_fingerprint"
                    detail = "narrowed retry belongs to a different candidate fingerprint"

    outcome.elapsed_time = max(0.0, clock() - (outcome.prompt_accepted_at or clock()))
    if failure_kind is not None:
        outcome.failure_kind = failure_kind
        outcome.detail = detail
        recorder.add("validation_complete", request.name, "rejected:" + failure_kind)
        return outcome

    if accepted_block is None:
        outcome.failure_kind = "unusable_output"
        outcome.detail = "validated result block is missing"
        recorder.add("validation_complete", request.name, "rejected:unusable_output")
        return outcome
    outcome.verdict = verdict
    outcome.verdict_class = _classify_verdict(request, verdict)
    outcome.validation_complete = True
    outcome.result_nonce = accepted_nonce
    outcome.result_digest = _digest(
        accepted_block.raw_span.encode("utf-8", "surrogateescape")
    )
    outcome.result_evidence_source = accepted_block.evidence_source
    outcome.result_evidence_path = accepted_block.evidence_path
    outcome.result_accepted_at = recorder.add("result_accepted", request.name, verdict or "")
    recorder.add("validation_complete", request.name, "accepted")
    return outcome


def _aggregate(legs: Dict[str, LegOutcome]) -> Tuple[str, bool]:
    if any(not leg.validation_complete for leg in legs.values()):
        return INFRASTRUCTURE_FAILURE, False
    if any(leg.verdict_class not in _ALLOWED_VERDICT_CLASSES for leg in legs.values()):
        return PROFILE_MISMATCH, False

    for verdict_class in (INCOMPLETE_CLASS, BLOCKED_CLASS, FINDINGS_CLASS):
        matching = [
            leg for _, leg in sorted(legs.items()) if leg.verdict_class == verdict_class
        ]
        if matching:
            return matching[0].verdict or PROFILE_MISMATCH, False

    passing = [leg for _, leg in sorted(legs.items()) if leg.verdict_class == PASS_CLASS]
    if len(passing) == len(legs):
        return passing[0].verdict or PROFILE_MISMATCH, True
    return PROFILE_MISMATCH, False


def orchestrate_reviews(
    adapter: ReviewAdapter,
    requests: Sequence[LegRequest],
    mode: str = "parallel",
    clock: Callable[[], float] = time.monotonic,
) -> OrchestrationResult:
    """Prepare, submit, settle, validate, and fail-closed aggregate review legs.

    ``parallel`` is the production protocol. ``serial`` exists only to produce
    a controlled benchmark baseline from the identical transport/validation
    state machine.
    """

    if not requests:
        raise ValueError("at least one applicable reviewer is required")
    if mode not in ("parallel", "serial"):
        raise ValueError("mode must be 'parallel' or 'serial'")
    names = [request.name for request in requests]
    if len(names) != len(set(names)):
        raise ValueError("reviewer names must be unique")
    for request in requests:
        _validate_verdict_profile(request)

    recorder = _EventRecorder(clock)
    fingerprint = adapter.capture_fingerprint()
    recorder.add("candidate_fingerprint_captured", detail=fingerprint)

    outcomes: Dict[str, LegOutcome] = {}
    handles = {}
    for request in requests:
        handle = adapter.prepare_leg(request, fingerprint)
        handles[request.name] = handle
        outcomes[request.name] = LegOutcome(request.name, handle)
        recorder.add("tab_ready", request.name)

    first_submission_at: Optional[float] = None
    first_wait_started = False
    all_submitted_before_wait = True

    def submit_initial_serial(request: LegRequest) -> Optional[str]:
        nonlocal first_submission_at, all_submitted_before_wait
        if first_wait_started:
            all_submitted_before_wait = False
        accepted, nonce, accepted_at, started_at = _submit(
            adapter,
            request,
            handles[request.name],
            request.prompt,
            fingerprint,
            recorder,
            retry=False,
            clock=clock,
        )
        if first_submission_at is None:
            first_submission_at = started_at
        outcomes[request.name].prompt_accepted_at = accepted_at
        if not accepted:
            outcomes[request.name].failure_kind = "prompt_not_accepted"
            outcomes[request.name].detail = "initial prompt was not accepted"
            recorder.add("validation_complete", request.name, "rejected:prompt_not_accepted")
            all_submitted_before_wait = False
            return None
        return nonce

    if mode == "parallel":
        dispatches: Dict[str, _PromptDispatch] = {}
        for request in requests:
            if first_wait_started:
                all_submitted_before_wait = False
            dispatched = _dispatch_prompt(
                adapter,
                request,
                handles[request.name],
                request.prompt,
                fingerprint,
                recorder,
                retry=False,
                clock=clock,
                defer_stall_confirmation=True,
            )
            dispatches[request.name] = dispatched
            if first_submission_at is None:
                first_submission_at = dispatched.started_at
            outcomes[request.name].prompt_accepted_at = dispatched.accepted_at

        pending = [
            request for request in requests
            if dispatches[request.name].pending_confirmation
        ]
        confirmation_results: Dict[str, bool] = {}
        if pending:
            with ThreadPoolExecutor(max_workers=len(pending)) as executor:
                futures = {
                    request.name: executor.submit(
                        adapter.prompt_accepted, handles[request.name]
                    )
                    for request in pending
                }
                for request in pending:
                    confirmed = futures[request.name].result()
                    confirmation_results[request.name] = confirmed
                    if confirmed:
                        outcomes[request.name].prompt_accepted_at = recorder.add(
                            "prompt_accepted", request.name, "enter"
                        )

        nonces: Dict[str, Optional[str]] = {}
        for request in requests:
            dispatched = dispatches[request.name]
            accepted = dispatched.accepted or confirmation_results.get(request.name, False)
            nonces[request.name] = dispatched.nonce if accepted else None
            if not accepted:
                outcomes[request.name].failure_kind = "prompt_not_accepted"
                outcomes[request.name].detail = "initial prompt was not accepted"
                recorder.add(
                    "validation_complete", request.name, "rejected:prompt_not_accepted"
                )
                all_submitted_before_wait = False

        if any(nonce is None for nonce in nonces.values()):
            recorder.add("prompt_batch_aborted", detail="one or more initial prompts were not accepted")
            for request in requests:
                outcome = outcomes[request.name]
                if outcome.failure_kind is None:
                    outcome.failure_kind = "prompt_batch_not_accepted"
                    outcome.detail = "a sibling initial prompt was not accepted; no waits began"
                    recorder.add(
                        "validation_complete", request.name, "rejected:prompt_batch_not_accepted"
                    )
        else:
            first_wait_started = True
            recorder.add("first_wait_started", detail=str(len(requests)))
            with ThreadPoolExecutor(max_workers=len(requests)) as executor:
                futures = {
                    request.name: executor.submit(
                        _wait_and_validate,
                        adapter,
                        request,
                        outcomes[request.name],
                        fingerprint,
                        nonces[request.name],
                        recorder,
                        clock,
                    )
                    for request in requests
                }
                for name, future in futures.items():
                    outcomes[name] = future.result()
    else:
        for request in requests:
            nonce = submit_initial_serial(request)
            if nonce is None:
                continue
            first_wait_started = True
            recorder.add("first_wait_started", request.name)
            outcomes[request.name] = _wait_and_validate(
                adapter,
                request,
                outcomes[request.name],
                fingerprint,
                nonce,
                recorder,
                clock,
            )

    current_fingerprint = _current_fingerprint(adapter)
    if current_fingerprint != fingerprint:
        for outcome in outcomes.values():
            outcome.verdict = None
            outcome.verdict_class = None
            outcome.validation_complete = False
            outcome.failure_kind = "stale_fingerprint"
            outcome.detail = "candidate fingerprint changed while reviews were running"
            recorder.add("validation_complete", outcome.name, "rejected:stale_fingerprint")

    completed_at = clock()
    wall_start = completed_at if first_submission_at is None else first_submission_at
    wall_time = max(0.0, completed_at - wall_start)
    status, clean = _aggregate(outcomes)
    recorder.add("aggregate_complete", detail=status)
    return OrchestrationResult(
        status=status,
        fingerprint=fingerprint,
        legs=outcomes,
        events=recorder.snapshot(),
        candidate_wall_time=wall_time,
        all_prompts_submitted_before_first_wait=(
            all_submitted_before_wait
            and (mode == "parallel" or len(requests) == 1)
            and all(outcome.prompt_accepted_at is not None for outcome in outcomes.values())
        ),
        mode=mode,
        clean=clean,
    )


def cleanup_review_tabs(
    adapter: ReviewAdapter,
    result: OrchestrationResult,
    artifact_written: bool,
    preserve: bool = False,
    clock: Callable[[], float] = time.monotonic,
    requests: Optional[Mapping[str, LegRequest]] = None,
) -> bool:
    """Close only coordinator-owned tabs after a clean artifact is durable.

    Non-clean or invalid results intentionally preserve visible tabs for
    inspection. A cleanup failure never changes the accepted review verdict.
    """

    def outcome_is_pass(outcome: LegOutcome) -> bool:
        request = requests.get(outcome.name) if requests is not None else None
        if request is not None:
            try:
                _validate_verdict_profile(request)
            except ValueError:
                return False
            if outcome.verdict not in request.allowed_verdicts:
                return False
            verdict_class = _classify_verdict(request, outcome.verdict)
        else:
            verdict_class = _VERDICT_CLASSES.get(outcome.verdict or "")
        return outcome.verdict_class == PASS_CLASS and verdict_class == PASS_CLASS

    if (
        preserve
        or not result.clean
        or not artifact_written
        or not result.legs
        or any(
            not outcome.validation_complete or not outcome_is_pass(outcome)
            for outcome in result.legs.values()
        )
    ):
        return False
    current_check = getattr(adapter, "cleanup_leg_is_current", None)
    preflight_results = []
    if current_check is not None:
        for outcome in result.legs.values():
            if not outcome.result_nonce or not outcome.result_digest:
                preflight_results.append(False)
                continue
            # The extended evidence contract belongs to the production Herdr
            # adapter. Existing benchmark/test adapters remain transcript-only.
            if isinstance(adapter, HerdrReviewAdapter):
                request = requests.get(outcome.name) if requests is not None else None
                preflight_results.append(
                    current_check(
                        outcome.handle,
                        outcome.result_nonce,
                        outcome.result_digest,
                        outcome.result_evidence_source,
                        outcome.result_evidence_path,
                        request.allowed_verdicts if request is not None else (outcome.verdict or "",),
                    )
                )
            else:
                preflight_results.append(
                    current_check(outcome.handle, outcome.result_nonce, outcome.result_digest)
                )
    if current_check is None or not all(preflight_results):
        result.events.append(
            ReviewEvent(
                "cleanup_incomplete",
                clock(),
                detail="one or more tabs no longer match the accepted review cycle",
            )
        )
        result.events.sort(key=lambda event: event.timestamp)
        return False

    complete = True
    for outcome in result.legs.values():
        if not adapter.cleanup_leg(outcome.handle):
            complete = False
    result.cleanup_complete = complete
    result.events.append(
        ReviewEvent(
            "cleanup_complete" if complete else "cleanup_incomplete",
            clock(),
            detail="all coordinator-owned tabs" if complete else "one or more tabs preserved",
        )
    )
    result.events.sort(key=lambda event: event.timestamp)
    return complete


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


class CommandRunner(Protocol):
    def __call__(
        self, argv: Sequence[str], cwd: Optional[Path] = None, timeout: Optional[float] = None
    ) -> CommandResult:
        ...


def subprocess_command_runner(
    argv: Sequence[str], cwd: Optional[Path] = None, timeout: Optional[float] = None
) -> CommandResult:
    """Run an argument-array command without a shell."""

    try:
        completed = subprocess.run(
            list(argv),
            cwd=str(cwd) if cwd is not None else None,
            text=False,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        stdout = (
            error.stdout.decode("utf-8", "surrogateescape")
            if isinstance(error.stdout, bytes)
            else error.stdout or ""
        )
        stderr = (
            error.stderr.decode("utf-8", "surrogateescape")
            if isinstance(error.stderr, bytes)
            else error.stderr or "command timed out"
        )
        return CommandResult(124, stdout, stderr)
    except OSError as error:
        return CommandResult(127, "", str(error))
    return CommandResult(
        completed.returncode,
        completed.stdout.decode("utf-8", "surrogateescape"),
        completed.stderr.decode("utf-8", "surrogateescape"),
    )


_SECRET_STORE_DIRECTORIES = frozenset((".secrets", "secrets"))
_EXACT_SECRET_FILES = frozenset((
    "credentials.json", "id_dsa", "id_ecdsa", "id_ed25519", "id_rsa",
))
_CRYPTOGRAPHIC_SECRET_EXTENSIONS = frozenset((
    ".cer", ".crt", ".der", ".key", ".p12", ".pem", ".pfx",
))
_DATA_SECRET_EXTENSIONS = frozenset((".json", ".txt", ".yaml", ".yml"))
_DATA_SECRET_STEM_WORDS = frozenset(("credential", "credentials", "secret", "secrets", "token", "tokens"))
_DATA_SECRET_WORD_SPLIT = re.compile(r"[^a-z0-9]+")
_GIT_SENSITIVE_EXCLUSIONS = (
    ":(top,icase,glob,exclude).env*",
    ":(top,icase,glob,exclude)**/.env*",
)


def _is_sensitive_path(path: str) -> bool:
    """Exclude only explicit secret-store, environment, key, and data-secret paths."""

    normalized = path.replace("\\", "/").strip("/")
    if not normalized:
        return False
    parts = PurePosixPath(normalized).parts
    lowered_parts = tuple(component.lower() for component in parts)
    if any(component.startswith(".env") for component in lowered_parts):
        return True
    if any(component in _SECRET_STORE_DIRECTORIES for component in lowered_parts[:-1]):
        return True

    filename = lowered_parts[-1]
    if filename in _EXACT_SECRET_FILES:
        return True
    suffix = PurePosixPath(filename).suffix
    if suffix in _CRYPTOGRAPHIC_SECRET_EXTENSIONS:
        return True
    if suffix not in _DATA_SECRET_EXTENSIONS:
        return False
    stem = filename[: -len(suffix)]
    words = [word for word in _DATA_SECRET_WORD_SPLIT.split(stem) if word]
    return bool(words and words[-1] in _DATA_SECRET_STEM_WORDS)


def _run_checked(
    runner: CommandRunner, argv: Sequence[str], cwd: Path, purpose: str
) -> bytes:
    result = runner(argv, cwd, None)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError("{} failed: {}".format(purpose, detail or result.returncode))
    return result.stdout.encode("utf-8", "surrogateescape")


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _filtered_porcelain(raw: bytes) -> bytes:
    records = raw.split(b"\0")
    kept: List[bytes] = []
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        status_code = record[:2]
        path_bytes = record[3:] if len(record) >= 3 else b""
        paths = [path_bytes.decode("utf-8", "surrogateescape")]
        extra: Optional[bytes] = None
        if b"R" in status_code or b"C" in status_code:
            if index < len(records):
                extra = records[index]
                index += 1
                paths.append(extra.decode("utf-8", "surrogateescape"))
        if any(_is_sensitive_path(path) for path in paths):
            continue
        kept.append(record)
        if extra is not None:
            kept.append(extra)
    return b"\0".join(kept) + (b"\0" if kept else b"")


def _safe_changed_paths(runner: CommandRunner, worktree: Path, staged: bool) -> List[str]:
    argv = ["git", "diff"]
    if staged:
        argv.append("--cached")
    argv.extend(["--name-only", "-z", "--no-ext-diff", "--no-renames", "--"])
    argv.extend(_GIT_SENSITIVE_EXCLUSIONS)
    raw = _run_checked(runner, argv, worktree, "git changed-path inventory")
    paths = [item.decode("utf-8", "surrogateescape") for item in raw.split(b"\0") if item]
    return sorted({path for path in paths if not _is_sensitive_path(path)}, key=os.fsencode)


def _diff_digest(runner: CommandRunner, worktree: Path, staged: bool) -> str:
    paths = _safe_changed_paths(runner, worktree, staged)
    if not paths:
        return _digest(b"")
    argv = ["git", "diff"]
    if staged:
        argv.append("--cached")
    argv.extend(["--no-ext-diff", "--no-renames", "--binary", "--"])
    argv.extend(paths)
    return _digest(_run_checked(runner, argv, worktree, "git diff"))


def _untracked_manifest(runner: CommandRunner, worktree: Path) -> Tuple[str, List[Mapping[str, str]]]:
    raw = _run_checked(
        runner,
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        worktree,
        "git untracked inventory",
    )
    paths = sorted(
        (
            item.decode("utf-8", "surrogateescape")
            for item in raw.split(b"\0")
            if item and not _is_sensitive_path(item.decode("utf-8", "surrogateescape"))
        ),
        key=os.fsencode,
    )
    manifest: List[Mapping[str, str]] = []
    encoded = bytearray()
    root = worktree.resolve()
    for relative in paths:
        candidate = worktree / relative
        # Defend before lstat/readlink/read against an injected traversal path.
        if os.path.commonpath((str(root), str(candidate.absolute()))) != str(root):
            raise RuntimeError("untracked path escapes worktree: {}".format(relative))
        # lstat/readlink never follows a symlink outside the worktree.
        metadata = candidate.lstat()
        mode = stat.S_IMODE(metadata.st_mode)
        if stat.S_ISLNK(metadata.st_mode):
            kind = "symlink"
            content_hash = _digest(os.fsencode(os.readlink(candidate)))
        elif stat.S_ISREG(metadata.st_mode):
            kind = "file"
            content_hash = _digest(candidate.read_bytes())
        else:
            kind = "other"
            content_hash = _digest(b"")
        entry = {
            "path": relative,
            "type": kind,
            "mode": "{:04o}".format(mode),
            "content_sha256": content_hash,
        }
        manifest.append(entry)
        rendered = json.dumps(entry, sort_keys=True, separators=(",", ":")).encode("utf-8")
        encoded.extend(len(rendered).to_bytes(8, "big"))
        encoded.extend(rendered)
    return _digest(bytes(encoded)), manifest


def candidate_fingerprint(
    worktree: Path, runner: CommandRunner = subprocess_command_runner
) -> Tuple[str, Mapping[str, Any]]:
    """Compute the complete, secret-excluding Git candidate fingerprint."""

    worktree = worktree.resolve()
    head = _run_checked(runner, ["git", "rev-parse", "HEAD"], worktree, "git HEAD").strip().decode()
    porcelain = _run_checked(
        runner,
        ["git", "status", "--porcelain=v1", "-z", "-uall", "--ignored=no", "--", *_GIT_SENSITIVE_EXCLUSIONS],
        worktree,
        "git status",
    )
    manifest_digest, manifest = _untracked_manifest(runner, worktree)
    components: Mapping[str, Any] = {
        "head": head,
        "porcelain_sha256": _digest(_filtered_porcelain(porcelain)),
        "staged_diff_sha256": _diff_digest(runner, worktree, staged=True),
        "unstaged_diff_sha256": _diff_digest(runner, worktree, staged=False),
        "untracked_manifest_sha256": manifest_digest,
        "untracked_manifest": manifest,
    }
    canonical = json.dumps(components, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _digest(canonical), components


@dataclass(frozen=True)
class HerdrLeg:
    request: LegRequest
    target: str
    tab_id: str
    workspace_id: str


class HerdrReviewAdapter:
    """Production adapter for already-running, visible Herdr reviewer targets."""

    def __init__(
        self,
        worktree: Path,
        legs: Mapping[str, HerdrLeg],
        runner: CommandRunner = subprocess_command_runner,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
        transition_poll_interval: float = 0.05,
    ):
        if transition_poll_interval <= 0:
            raise ValueError("transition_poll_interval must be positive")
        self.worktree = worktree.resolve()
        self.legs = dict(legs)
        self.runner = runner
        self.clock = clock
        self.sleeper = sleeper
        self.transition_poll_interval = transition_poll_interval
        self._launch_fingerprint = ""
        self._submitted: Dict[str, Tuple[str, str]] = {}
        self._pre_submit_sequences: Dict[str, int] = {}
        self._first_action_observed_at: Dict[str, float] = {}
        self._enter_recovery_attempted: Dict[str, bool] = {}
        self._result_files: Dict[str, Path] = {}
        self._fingerprint_lock = threading.Lock()

    def _result_dir(self) -> Path:
        # Result files must never live in the candidate checkout: the complete
        # fingerprint intentionally includes every untracked path there.
        path = Path(tempfile.gettempdir()) / "ai-configs-review-transport"
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            path.chmod(0o700)
        except OSError:
            pass
        return path.resolve()

    def _is_result_path(self, path: Path) -> bool:
        try:
            return path.resolve().parent == self._result_dir()
        except OSError:
            return False

    def _result_path_for(self, leg_name: str, nonce: str) -> Path:
        safe_leg = re.sub(r"[^a-z0-9_-]+", "-", leg_name.lower()).strip("-") or "leg"
        return self._result_dir() / "{}-{}.json".format(safe_leg[:24], nonce)

    def _command(self, argv: Sequence[str], timeout: Optional[float] = None) -> CommandResult:
        return self.runner(argv, self.worktree, timeout)

    @staticmethod
    def _payload(result: CommandResult) -> Any:
        text = result.stdout.strip()
        if not text:
            return {}
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"text": text}

    @classmethod
    def _state(cls, result: CommandResult) -> str:
        payload = cls._payload(result)

        def find(value: Any, keys: Sequence[str]) -> Optional[str]:
            if isinstance(value, dict):
                for key in keys:
                    found = value.get(key)
                    if isinstance(found, str):
                        return found.lower()
                for nested in value.values():
                    found = find(nested, keys)
                    if found:
                        return found
            elif isinstance(value, list):
                for nested in value:
                    found = find(nested, keys)
                    if found:
                        return found
            return None

        return find(payload, ("state", "agent_state", "agent_status")) or find(payload, ("status",)) or "unknown"

    @classmethod
    def _agent_snapshot(cls, result: CommandResult) -> Optional[Tuple[str, int]]:
        """Parse state and sequence only from supported ``agent get`` envelopes."""

        if result.returncode != 0:
            return None
        payload = cls._payload(result)
        if not isinstance(payload, dict):
            return None
        agent: Any = payload.get("agent")
        if agent is None and isinstance(payload.get("result"), dict):
            agent = payload["result"].get("agent")
        if not isinstance(agent, dict):
            return None
        state = agent.get("agent_status", agent.get("state"))
        sequence = agent.get("state_change_seq")
        if not isinstance(state, str) or state.lower() not in ("idle", "done", "blocked", "working"):
            return None
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
            return None
        return state.lower(), sequence

    @classmethod
    def _agent_tab_id(cls, result: CommandResult) -> Optional[str]:
        """Parse a non-empty tab binding from supported ``agent get`` envelopes."""

        if result.returncode != 0:
            return None
        payload = cls._payload(result)
        if not isinstance(payload, dict):
            return None
        agent: Any = payload.get("agent")
        if agent is None and isinstance(payload.get("result"), dict):
            agent = payload["result"].get("agent")
        if not isinstance(agent, dict):
            return None
        tab_id = agent.get("tab_id")
        if not isinstance(tab_id, str) or not tab_id.strip():
            return None
        return tab_id

    @classmethod
    def _workspace_tab_ids(cls, result: CommandResult) -> Optional[set[str]]:
        """Return exact tab IDs from a scoped Herdr tab-list response."""

        if result.returncode != 0:
            return None
        payload = cls._payload(result)

        tabs: Optional[List[Any]] = None
        if isinstance(payload, dict):
            if "tabs" in payload:
                direct_tabs = payload.get("tabs")
                if isinstance(direct_tabs, list):
                    tabs = direct_tabs
            elif isinstance(payload.get("result"), dict):
                result_tabs = payload["result"].get("tabs")
                if isinstance(result_tabs, list):
                    tabs = result_tabs
        if tabs is None:
            return None
        tab_ids: set[str] = set()
        for tab in tabs:
            if isinstance(tab, str) and tab.strip():
                tab_ids.add(tab)
                continue
            if isinstance(tab, dict):
                tab_id = tab.get("tab_id", tab.get("id"))
                if isinstance(tab_id, str) and tab_id.strip():
                    tab_ids.add(tab_id)
                    continue
            return None
        return tab_ids

    def _workspace_contains_tab(self, workspace_id: str, tab_id: str) -> Optional[bool]:
        listed = self._command(["herdr", "tab", "list", "--workspace", workspace_id])
        tab_ids = self._workspace_tab_ids(listed)
        return None if tab_ids is None else tab_id in tab_ids

    def preflight(self) -> None:
        for leg in self.legs.values():
            result = self._command(["herdr", "agent", "get", leg.target])
            if result.returncode != 0:
                raise RuntimeError("reviewer target is unavailable: {}".format(leg.target))
            if self._state(result) == "working":
                raise RuntimeError("reviewer target is already working: {}".format(leg.target))

    def capture_fingerprint(self) -> str:
        with self._fingerprint_lock:
            self._launch_fingerprint, _ = candidate_fingerprint(self.worktree, self.runner)
            return self._launch_fingerprint

    def current_fingerprint(self) -> str:
        with self._fingerprint_lock:
            fingerprint, _ = candidate_fingerprint(self.worktree, self.runner)
            return fingerprint

    def prepare_leg(self, request: LegRequest, fingerprint: str) -> HerdrLeg:
        leg = self.legs[request.name]
        result = self._command(["herdr", "agent", "get", leg.target])
        if result.returncode != 0:
            raise RuntimeError("reviewer target is unavailable: {}".format(leg.target))
        if self._state(result) == "working":
            raise RuntimeError("reviewer target is already working: {}".format(leg.target))
        return leg

    def _render_prompt(
        self,
        leg: HerdrLeg,
        prompt: str,
        nonce: str,
        fingerprint: str,
        result_path: Path,
    ) -> str:
        allowed = ", ".join(leg.request.allowed_verdicts)
        return (
            prompt.rstrip()
            + "\n\nREVIEW TRANSACTION (required):\n"
            + "Candidate fingerprint: {}\n".format(fingerprint)
            + "Transaction nonce: {}\n".format(nonce)
            + "Allowed verdicts: {}\n".format(allowed)
            + "Structured result file (preferred when you can write files): {}\n".format(
                result_path
            )
            + "Write one JSON object to that path with keys nonce, verdict, and body "
              "(body = non-empty review text). Also print a nonce-delimited transcript block.\n"
            + "Return a nonce-delimited block with non-empty review content. Start with the token "
              "BEGIN_REVIEW_RESULT, one space, and the transaction nonce on one logical line "
              "(do not insert newlines inside the marker or nonce). End with the token "
              "END_REVIEW_RESULT, one space, and the same nonce on one logical line. "
              "Make VERDICT: <allowed-token> the final non-empty line inside that block.\n"
        )

    def submit_prompt(
        self, handle: HerdrLeg, prompt: str, nonce: str, fingerprint: str
    ) -> PromptSubmission:
        self._first_action_observed_at.pop(handle.request.name, None)
        self._enter_recovery_attempted[handle.request.name] = False
        result_path = self._result_path_for(handle.request.name, nonce)
        if result_path.exists():
            try:
                result_path.unlink()
            except OSError:
                pass
        self._result_files[handle.request.name] = result_path
        rendered = self._render_prompt(handle, prompt, nonce, fingerprint, result_path)
        state = self._command(["herdr", "agent", "get", handle.target])
        snapshot = self._agent_snapshot(state)
        if snapshot is None:
            detail = (state.stderr or state.stdout).strip()
            return PromptSubmission(
                False,
                detail="invalid pre-submit agent state_change_seq" + (": " + detail if detail else ""),
            )
        current_state, baseline_sequence = snapshot
        if current_state == "working":
            return PromptSubmission(False, detail="reviewer target is already working")
        self._submitted[handle.request.name] = (rendered, fingerprint)
        self._pre_submit_sequences[handle.request.name] = baseline_sequence
        result = self._command(["herdr", "agent", "prompt", handle.target, rendered])
        combined = (result.stdout + "\n" + result.stderr).lower()
        if result.returncode == 0 and "agent_prompt_stalled" not in combined:
            return PromptSubmission(True, detail="herdr accepted prompt")
        if "agent_prompt_stalled" in combined:
            visible = self._command(
                ["herdr", "agent", "read", handle.target, "--source", "visible", "--lines", "400", "--format", "text"]
            )
            proof = visible.returncode == 0 and rendered in visible.stdout
            return PromptSubmission(False, proof, "agent_prompt_stalled")
        return PromptSubmission(False, detail=(result.stderr or result.stdout).strip())

    def send_enter(self, handle: HerdrLeg) -> bool:
        name = handle.request.name
        if self._enter_recovery_attempted.get(name, False):
            return False
        # Record the attempt before transport so a failed or ambiguous send can
        # never cause a second Enter for the same prompt submission.
        self._enter_recovery_attempted[name] = True
        result = self._command(["herdr", "agent", "send-keys", handle.target, "Enter"])
        return result.returncode == 0

    def _recover_successful_but_unsubmitted_prompt(
        self,
        handle: HerdrLeg,
        baseline: int,
        reviewer_deadline: float,
    ) -> Tuple[Optional[Tuple[str, int]], Optional[str]]:
        name = handle.request.name
        if self._enter_recovery_attempted.get(name, False):
            return None, "prompt transition stalled after the one permitted Enter recovery"

        submitted = self._submitted.get(name)
        if submitted is None:
            return None, "prompt transition stalled without a current rendered prompt"
        rendered, _ = submitted
        visible = self._command(
            [
                "herdr", "agent", "read", handle.target,
                "--source", "visible", "--lines", "400", "--format", "text",
            ]
        )
        if visible.returncode != 0:
            detail = (visible.stderr or visible.stdout).strip()
            return None, (
                "prompt transition stalled and visible transcript inspection failed"
                + (": " + detail if detail else "")
            )
        visible_text = visible.stdout.rstrip("\r\n")
        rendered_text = rendered.rstrip("\r\n")
        if not visible_text or not visible_text.endswith(rendered_text):
            return None, (
                "prompt transition stalled but the visible transcript did not end with the exact "
                "current rendered prompt; Enter recovery was not attempted"
            )

        remaining = reviewer_deadline - self.clock()
        if remaining <= 0:
            return None, (
                "prompt transition stalled with exact visible proof, but the reviewer timeout "
                "expired before Enter recovery"
            )
        if not self.send_enter(handle):
            return None, "exact visible prompt was proven, but the one permitted Enter send failed"

        remaining = reviewer_deadline - self.clock()
        if remaining <= 0:
            return None, "reviewer timeout expired immediately after Enter recovery"
        snapshot, error = self._poll_for_sequence_advance(handle, baseline, remaining)
        if snapshot is None:
            return None, (
                "prompt did not transition after the one permitted Enter recovery: "
                + (error or "unknown transition failure")
            )
        return snapshot, None

    def _poll_for_sequence_advance(
        self,
        handle: HerdrLeg,
        baseline: int,
        timeout_seconds: float,
    ) -> Tuple[Optional[Tuple[str, int]], Optional[str]]:
        transition_window = min(5.0, timeout_seconds)
        deadline = self.clock() + transition_window
        while True:
            state_result = self._command(["herdr", "agent", "get", handle.target])
            snapshot = self._agent_snapshot(state_result)
            if snapshot is None:
                detail = (state_result.stderr or state_result.stdout).strip()
                return None, (
                    "invalid post-submit agent state/state_change_seq"
                    + (": " + detail if detail else "")
                )
            _, sequence = snapshot
            if sequence < baseline:
                return None, "post-submit state_change_seq decreased from {} to {}".format(
                    baseline, sequence
                )
            if sequence > baseline:
                return snapshot, None
            now = self.clock()
            if now >= deadline:
                return None, (
                    "prompt stalled: state_change_seq did not advance beyond {} within {:.3f}s".format(
                        baseline, transition_window
                    )
                )
            self.sleeper(min(self.transition_poll_interval, deadline - now))

    def prompt_accepted(self, handle: HerdrLeg) -> bool:
        baseline = self._pre_submit_sequences.get(handle.request.name)
        if baseline is None:
            return False
        snapshot, _ = self._poll_for_sequence_advance(
            handle, baseline, handle.request.timeout_seconds
        )
        if snapshot is None:
            return False
        self._first_action_observed_at[handle.request.name] = self.clock()
        return True

    def _transport_failure(
        self,
        detail: str,
        state: str = "provider_error",
        first_action_observed_at: Optional[float] = None,
    ) -> RawReviewResult:
        return RawReviewResult(
            state,
            "",
            self.current_fingerprint(),
            first_action_observed=first_action_observed_at is not None,
            first_action_observed_at=first_action_observed_at,
            detail=detail,
        )

    def wait_for_result(self, handle: HerdrLeg, timeout_seconds: float) -> RawReviewResult:
        baseline = self._pre_submit_sequences.get(handle.request.name)
        if baseline is None:
            return self._transport_failure("missing pre-submit state_change_seq baseline")

        started = self.clock()
        reviewer_deadline = started + timeout_seconds
        snapshot, transition_error = self._poll_for_sequence_advance(
            handle, baseline, timeout_seconds
        )
        if snapshot is None and transition_error and transition_error.startswith("prompt stalled:"):
            snapshot, transition_error = self._recover_successful_but_unsubmitted_prompt(
                handle, baseline, reviewer_deadline
            )
        if snapshot is None:
            return self._transport_failure(transition_error or "prompt transition failed")
        observed_state, observed_sequence = snapshot
        first_action_observed_at = self._first_action_observed_at.pop(
            handle.request.name, None
        )
        if first_action_observed_at is None:
            first_action_observed_at = self.clock()

        if observed_state == "working":
            remaining = reviewer_deadline - self.clock()
            if remaining <= 0:
                return self._transport_failure(
                    "reviewer timeout expired after prompt transition",
                    state="timeout",
                    first_action_observed_at=first_action_observed_at,
                )
            timeout_ms = max(1, int(remaining * 1000))
            waited = self._command(
                [
                    "herdr", "agent", "wait", handle.target,
                    "--until", "idle", "--until", "done", "--until", "blocked",
                    "--timeout", str(timeout_ms),
                ],
                remaining + 5.0,
            )
            combined = (waited.stdout + "\n" + waited.stderr).lower()
            if waited.returncode != 0:
                state = "timeout" if "timeout" in combined or waited.returncode == 124 else "provider_error"
                return self._transport_failure(
                    (waited.stderr or waited.stdout).strip() or "Herdr wait failed",
                    state=state,
                    first_action_observed_at=first_action_observed_at,
                )
            state_result = self._command(["herdr", "agent", "get", handle.target])
            snapshot = self._agent_snapshot(state_result)
            if snapshot is None:
                detail = (state_result.stderr or state_result.stdout).strip()
                return self._transport_failure(
                    "invalid settled agent state/state_change_seq"
                    + (": " + detail if detail else ""),
                    first_action_observed_at=first_action_observed_at,
                )
            observed_state, sequence = snapshot
            if observed_sequence is None or sequence < observed_sequence:
                return self._transport_failure(
                    "settled state_change_seq decreased from {} to {}".format(
                        observed_sequence, sequence
                    ),
                    first_action_observed_at=first_action_observed_at,
                )

        if observed_state not in ("idle", "done", "blocked"):
            return self._transport_failure(
                "unexpected post-submit Herdr state: {}".format(observed_state),
                first_action_observed_at=first_action_observed_at,
            )
        transcript = self._command(
            ["herdr", "agent", "read", handle.target, "--source", "recent-unwrapped", "--lines", "400", "--format", "text"]
        )
        structured = self._result_files.get(handle.request.name)
        structured_path = str(structured) if structured is not None else None
        if transcript.returncode != 0:
            return RawReviewResult(
                "provider_error",
                transcript.stdout,
                self.current_fingerprint(),
                first_action_observed=True,
                first_action_observed_at=first_action_observed_at,
                detail=(transcript.stderr or transcript.stdout).strip(),
                structured_result_path=structured_path,
            )
        return RawReviewResult(
            "settled",
            transcript.stdout,
            self.current_fingerprint(),
            first_action_observed=True,
            first_action_observed_at=first_action_observed_at,
            structured_result_path=structured_path,
        )

    def cleanup_leg_is_current(
        self,
        handle: HerdrLeg,
        result_nonce: str,
        result_digest: str,
        result_evidence_source: str,
        result_evidence_path: Optional[str],
        allowed_verdicts: Sequence[str],
    ) -> bool:
        state_result = self._command(["herdr", "agent", "get", handle.target])
        if state_result.returncode != 0 or self._state(state_result) not in ("idle", "done", "blocked"):
            return False
        if self._agent_tab_id(state_result) != handle.tab_id:
            return False
        if self._workspace_contains_tab(handle.workspace_id, handle.tab_id) is not True:
            return False
        if not result_nonce or not result_digest:
            return False
        if result_evidence_source == "structured":
            if not result_evidence_path:
                return False
            path = Path(result_evidence_path)
            if not self._is_result_path(path):
                return False
            block, failure_kind, _ = load_structured_result_file(
                path, result_nonce, allowed_verdicts
            )
        elif result_evidence_source == "transcript":
            transcript = self._command(
                ["herdr", "agent", "read", handle.target, "--source", "recent-unwrapped", "--lines", "400", "--format", "text"]
            )
            if transcript.returncode != 0:
                return False
            block, failure_kind, _ = _extract_result_block(transcript.stdout, result_nonce)
        else:
            return False
        if failure_kind is not None or block is None:
            return False
        current_digest = _digest(block.raw_span.encode("utf-8", "surrogateescape"))
        return current_digest == result_digest

    def cleanup_leg(self, handle: HerdrLeg) -> bool:
        result = self._command(["herdr", "tab", "close", handle.tab_id])
        if result.returncode != 0:
            return False
        return self._workspace_contains_tab(handle.workspace_id, handle.tab_id) is False


def _load_run_request(
    path: Path, read_prompts: bool = True
) -> Tuple[HerdrReviewAdapter, List[LegRequest], Mapping[str, Any]]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError("request must be a JSON object")
    worktree = Path(str(payload["worktree"])).expanduser().resolve()
    reviewers = payload.get("reviewers")
    if not isinstance(reviewers, list) or not reviewers:
        raise ValueError("request.reviewers must contain at least one reviewer")
    raw_verdict_classes = payload.get("verdict_classes", {})
    if not isinstance(raw_verdict_classes, dict):
        raise ValueError("request.verdict_classes must be an object when provided")
    verdict_classes = {str(key): str(value) for key, value in raw_verdict_classes.items()}
    if any(value not in _ALLOWED_VERDICT_CLASSES for value in verdict_classes.values()):
        raise ValueError("request.verdict_classes values must be pass/findings/blocked/incomplete")
    if any(
        token in _VERDICT_CLASSES and _VERDICT_CLASSES[token] != verdict_class
        for token, verdict_class in verdict_classes.items()
    ):
        raise ValueError("request.verdict_classes cannot redefine shared workflow verdicts")

    requests: List[LegRequest] = []
    legs: Dict[str, HerdrLeg] = {}
    for item in reviewers:
        if not isinstance(item, dict):
            raise ValueError("each reviewer must be an object")
        name = str(item["name"])
        prompt_path = Path(str(item["prompt_file"])).expanduser()
        retry_path = Path(str(item["narrowed_retry_prompt_file"])).expanduser()
        request = LegRequest(
            name=name,
            prompt=prompt_path.read_text() if read_prompts else "",
            narrowed_retry_prompt=retry_path.read_text() if read_prompts else "",
            allowed_verdicts=tuple(str(value) for value in item["allowed_verdicts"]),
            timeout_seconds=float(item["timeout_seconds"]),
            verdict_classes=verdict_classes,
        )
        _validate_verdict_profile(request)
        workspace_id = item.get("workspace_id")
        if not isinstance(workspace_id, str) or not workspace_id.strip():
            raise ValueError("each reviewer.workspace_id must be a non-empty string")
        # A target may be either a short agent name or an opaque Herdr pane ID.
        # Name generation/validation is provided for launchers; this adapter
        # controls reviewers that are already running and must preserve pane IDs.
        target = str(item["target"])
        if not target.strip():
            raise ValueError("each reviewer.target must be a non-empty string")
        leg = HerdrLeg(
            request=request,
            target=target,
            tab_id=str(item["tab_id"]),
            workspace_id=workspace_id.strip(),
        )
        requests.append(request)
        legs[name] = leg
    if len(legs) != len(requests):
        raise ValueError("reviewer names must be unique")
    return HerdrReviewAdapter(worktree, legs), requests, payload


def _request_identity(
    adapter: HerdrReviewAdapter, payload: Mapping[str, Any]
) -> Mapping[str, Any]:
    reviewers = payload.get("reviewers")
    if not isinstance(reviewers, list):
        raise ValueError("request.reviewers must be a list")
    raw_by_name = {
        str(item["name"]): item for item in reviewers if isinstance(item, dict)
    }
    legs = []
    for name in sorted(adapter.legs):
        leg = adapter.legs[name]
        raw = raw_by_name[name]
        legs.append(
            {
                "name": name,
                "target": leg.target,
                "tab_id": leg.tab_id,
                "workspace_id": leg.workspace_id,
                "prompt_file": str(Path(str(raw["prompt_file"])).expanduser().resolve()),
                "narrowed_retry_prompt_file": str(
                    Path(str(raw["narrowed_retry_prompt_file"])).expanduser().resolve()
                ),
                "allowed_verdicts": list(leg.request.allowed_verdicts),
                "timeout_seconds": leg.request.timeout_seconds,
            }
        )
    binding = {
        "schema_version": "review-orchestration-request-v1",
        "worktree": str(adapter.worktree),
        "legs": legs,
    }
    if "verdict_classes" in payload:
        binding["verdict_classes"] = {
            str(key): str(value)
            for key, value in sorted(payload["verdict_classes"].items())
        }
    canonical = json.dumps(binding, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {**binding, "sha256": _digest(canonical)}


def result_record(
    result: OrchestrationResult,
    request_identity: Optional[Mapping[str, Any]] = None,
) -> Mapping[str, Any]:
    record: Dict[str, Any] = {
        "schema_version": "review-orchestration-result-v3",
        "status": result.status,
        "clean": result.clean,
        "fingerprint": result.fingerprint,
        "mode": result.mode,
        "all_prompts_submitted_before_first_wait": result.all_prompts_submitted_before_first_wait,
        "cleanup_complete": result.cleanup_complete,
        "timing": {
            "candidate_wall_seconds": result.candidate_wall_time,
            "legs": {name: outcome.elapsed_time for name, outcome in result.legs.items()},
        },
        "legs": {
            name: {
                "verdict": outcome.verdict,
                "verdict_class": outcome.verdict_class,
                "validation_complete": outcome.validation_complete,
                "failure_kind": outcome.failure_kind,
                "detail": outcome.detail,
                "retried_unusable_output": outcome.retried_unusable_output,
                "result_nonce": outcome.result_nonce,
                "result_digest": outcome.result_digest,
                "result_evidence_source": outcome.result_evidence_source,
                "result_evidence_path": outcome.result_evidence_path,
            }
            for name, outcome in result.legs.items()
        },
        "events": [
            {"kind": event.kind, "timestamp": event.timestamp, "leg": event.leg, "detail": event.detail}
            for event in result.events
        ],
    }
    if request_identity is not None:
        record["request_identity"] = request_identity
    return record


def run_request_file(
    request_path: Path,
    runner: CommandRunner = subprocess_command_runner,
) -> Tuple[OrchestrationResult, Mapping[str, Any]]:
    adapter, requests, payload = _load_run_request(request_path)
    adapter.runner = runner
    adapter.preflight()
    identity = _request_identity(adapter, payload)
    result = orchestrate_reviews(adapter, requests, mode="parallel")
    # Review artifacts are coordinator-owned and can only be written after this
    # result returns. Cleanup is therefore a separate, explicit command.
    return result, result_record(result, identity)


def cleanup_request_file(
    request_path: Path,
    receipt_path: Path,
    artifact_written: bool,
    runner: CommandRunner = subprocess_command_runner,
) -> Mapping[str, Any]:
    adapter, requests, payload = _load_run_request(request_path, read_prompts=False)
    adapter.runner = runner
    receipt = json.loads(receipt_path.read_text())
    if artifact_written is not True:
        raise ValueError("cleanup requires explicit --artifact-written confirmation")
    if (
        receipt.get("schema_version") != "review-orchestration-result-v3"
        or receipt.get("clean") is not True
    ):
        raise ValueError("cleanup receipt is not a clean validated review result")
    expected_identity = _request_identity(adapter, payload)
    if receipt.get("request_identity") != expected_identity:
        raise ValueError("cleanup receipt does not match the exact review request identity")
    fingerprint = str(receipt.get("fingerprint", ""))
    if not fingerprint:
        raise ValueError("cleanup receipt is missing its validated fingerprint")
    receipt_legs = receipt.get("legs")
    requested_names = {request.name for request in requests}
    if not isinstance(receipt_legs, dict) or set(receipt_legs) != requested_names:
        raise ValueError("cleanup receipt does not contain every requested reviewer")
    for request in requests:
        leg = receipt_legs.get(request.name)
        verdict = leg.get("verdict") if isinstance(leg, dict) else None
        if (
            not isinstance(leg, dict)
            or leg.get("validation_complete") is not True
            or verdict not in request.allowed_verdicts
            or _classify_verdict(request, verdict) != PASS_CLASS
            or leg.get("verdict_class", PASS_CLASS) != PASS_CLASS
            or not isinstance(leg.get("result_nonce"), str)
            or not leg["result_nonce"]
            or not isinstance(leg.get("result_digest"), str)
            or not leg["result_digest"]
            or leg.get("result_evidence_source", "transcript") not in ("transcript", "structured")
            or (
                leg.get("result_evidence_source", "transcript") == "structured"
                and (not isinstance(leg.get("result_evidence_path"), str) or not leg["result_evidence_path"])
            )
        ):
            raise ValueError(
                "cleanup receipt does not contain a clean verdict for every requested reviewer (pass-class required)"
            )
    outcomes = {
        request.name: LegOutcome(
            request.name,
            adapter.legs[request.name],
            verdict=receipt_legs[request.name]["verdict"],
            verdict_class=PASS_CLASS,
            validation_complete=True,
            result_nonce=receipt_legs[request.name]["result_nonce"],
            result_digest=receipt_legs[request.name]["result_digest"],
            result_evidence_source=receipt_legs[request.name].get("result_evidence_source", "transcript"),
            result_evidence_path=receipt_legs[request.name].get("result_evidence_path"),
        )
        for request in requests
    }
    expected_status, expected_clean = _aggregate(outcomes)
    if not expected_clean or receipt.get("status") != expected_status:
        raise ValueError("cleanup receipt aggregate status does not match its pass-class verdicts")
    result = OrchestrationResult(
        status=expected_status,
        fingerprint=fingerprint,
        legs=outcomes,
        events=[],
        candidate_wall_time=float(receipt.get("timing", {}).get("candidate_wall_seconds", 0.0)),
        all_prompts_submitted_before_first_wait=bool(receipt.get("all_prompts_submitted_before_first_wait")),
        mode="parallel",
        clean=True,
    )
    complete = cleanup_review_tabs(
        adapter,
        result,
        artifact_written=True,
        requests={request.name: request for request in requests},
    )
    return {
        "schema_version": "review-orchestration-cleanup-v1",
        "status": "CLEANUP_COMPLETE" if complete else "CLEANUP_INCOMPLETE",
        "cleanup_complete": complete,
        "fingerprint": fingerprint,
        "tab_ids": [adapter.legs[request.name].tab_id for request in requests],
        "events": [{"kind": "cleanup_complete" if complete else "cleanup_incomplete", "timestamp": time.monotonic()}],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run", help="run reviews on already-started visible Herdr targets")
    run.add_argument("--request", required=True, type=Path, help="JSON request file")
    run.add_argument("--output", type=Path, help="write the compact JSON receipt to this path")
    cleanup = subparsers.add_parser("cleanup", help="close recorded tabs after a durable clean artifact")
    cleanup.add_argument("--request", required=True, type=Path)
    cleanup.add_argument("--receipt", required=True, type=Path)
    cleanup.add_argument("--artifact-written", action="store_true")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "cleanup":
            record = cleanup_request_file(args.request, args.receipt, args.artifact_written)
            sys.stdout.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
            return 0 if record["cleanup_complete"] else 2
        result, record = run_request_file(args.request)
        rendered = json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered)
        sys.stdout.write(rendered)
        return 0 if result.clean else 2
    except (KeyError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError) as error:
        record = {
            "schema_version": "review-orchestration-result-v3",
            "status": INFRASTRUCTURE_FAILURE,
            "clean": False,
            "error": str(error),
        }
        sys.stdout.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
