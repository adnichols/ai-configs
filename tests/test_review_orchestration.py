import argparse
import contextlib
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from scripts.benchmark_review_orchestration import compare, fixture_prompt, load_fixture, run_benchmark
from scripts.review_orchestration import (
    CommandResult,
    HerdrLeg,
    HerdrReviewAdapter,
    LegOutcome,
    LegRequest,
    OrchestrationResult,
    PromptSubmission,
    RawReviewResult,
    candidate_fingerprint,
    cleanup_request_file,
    cleanup_review_tabs,
    is_valid_herdr_agent_name,
    load_structured_result_file,
    main,
    orchestrate_reviews,
    result_record,
    run_request_file,
    short_herdr_agent_name,
    subprocess_command_runner,
    validate_herdr_agent_name,
    _extract_result_block,
    _load_run_request,
    _parse_result,
    _validate_result,
)


VERDICTS = (
    "FINDINGS_TO_RESOLVE",
    "CLEAN_FOR_PR",
    "BLOCKED_BY_QUESTION",
    "REVIEW_INCOMPLETE_RERUN_NEEDED",
)
PLAN_VERDICTS = (
    "PLAN_EXECUTION_READY",
    "PLAN_NEEDS_REVISION",
    "BLOCKED_BY_PRODUCT_QUESTION",
    "REVIEW_INCOMPLETE_RERUN_NEEDED",
)


class FakeAdapter:
    def __init__(self, plans, fingerprint="candidate-v1", mutate_on_wait=None):
        self.plans = plans
        self.fingerprint = fingerprint
        self.mutate_on_wait = mutate_on_wait
        self.operations = []
        self._lock = threading.Lock()
        self._submissions = {}
        self._wait_counts = {}
        self.cleaned = []

    def capture_fingerprint(self):
        with self._lock:
            self.operations.append(("fingerprint", self.fingerprint))
            return self.fingerprint

    def current_fingerprint(self):
        with self._lock:
            self.operations.append(("fingerprint_check", self.fingerprint))
            return self.fingerprint

    def prepare_leg(self, request, fingerprint):
        with self._lock:
            self.operations.append(("ready", request.name, fingerprint))
        return request.name

    def submit_prompt(self, handle, prompt, nonce, fingerprint):
        with self._lock:
            attempt = len(self._submissions.setdefault(handle, []))
            self._submissions[handle].append((prompt, nonce, fingerprint))
            self.operations.append(("submit", handle, attempt, fingerprint))
        rejected = self.plans[handle].get("reject", False) and attempt == 0
        stalled = self.plans[handle].get("stall", False) and attempt == 0
        return PromptSubmission(
            accepted=not (rejected or stalled),
            full_prompt_visible_unsubmitted=stalled,
            detail="rejected" if rejected else "",
        )

    def send_enter(self, handle):
        with self._lock:
            self.operations.append(("enter", handle))
        return True

    def prompt_accepted(self, handle):
        with self._lock:
            self.operations.append(("confirmation_started", handle))
        barrier = self.plans[handle].get("confirmation_barrier")
        if barrier is not None:
            barrier.wait(timeout=1.0)
        time.sleep(self.plans[handle].get("confirmation_delay", 0.0))
        accepted = not self.plans[handle].get("confirmation_fails", False)
        with self._lock:
            self.operations.append(("accepted" if accepted else "confirmation_failed", handle))
        return accepted

    def wait_for_result(self, handle, timeout_seconds):
        with self._lock:
            attempt = self._wait_counts.get(handle, 0)
            self._wait_counts[handle] = attempt + 1
            self.operations.append(("wait", handle, attempt))
            submission = self._submissions[handle][attempt]
        plan = self.plans[handle]
        time.sleep(plan.get("delay", 0.001))
        if self.mutate_on_wait == handle and attempt == 0:
            self.fingerprint = "candidate-v2"
        result = plan.get("results", ["clean"])[attempt]
        nonce = submission[1]
        fingerprint = submission[2]
        if result == "clean":
            output = bounded(nonce, "CLEAN_FOR_PR")
            return RawReviewResult("settled", output, fingerprint, first_action_observed=True)
        if result == "findings":
            output = bounded(nonce, "FINDINGS_TO_RESOLVE")
            return RawReviewResult("settled", output, fingerprint)
        if result == "plan-ready":
            output = bounded(nonce, "PLAN_EXECUTION_READY")
            return RawReviewResult("settled", output, fingerprint)
        if result == "plan-revision":
            output = bounded(nonce, "PLAN_NEEDS_REVISION")
            return RawReviewResult("settled", output, fingerprint)
        if result == "pass-scoped":
            output = bounded(nonce, "PASS_SCOPED")
            return RawReviewResult("settled", output, fingerprint)
        if result == "pass":
            output = bounded(nonce, "PASS")
            return RawReviewResult("settled", output, fingerprint, first_action_observed=True)
        if result == "incomplete":
            output = bounded(nonce, "REVIEW_INCOMPLETE_RERUN_NEEDED")
            return RawReviewResult("settled", output, fingerprint)
        if result == "bad-boundary":
            return RawReviewResult("settled", "VERDICT: CLEAN_FOR_PR", fingerprint)
        if result == "failed":
            return RawReviewResult("provider_error", "authentication failed", fingerprint)
        if result == "timeout":
            return RawReviewResult("timeout", "", fingerprint)
        raise AssertionError(result)

    def cleanup_leg_is_current(
        self,
        handle,
        result_nonce,
        result_digest,
        result_evidence_source="transcript",
        result_evidence_path=None,
        allowed_verdicts=(),
    ):
        with self._lock:
            self.operations.append(
                (
                    "cleanup_check",
                    handle,
                    result_nonce,
                    result_digest,
                    result_evidence_source,
                    result_evidence_path,
                    tuple(allowed_verdicts),
                )
            )
        return bool(result_nonce and result_digest)

    def cleanup_leg(self, handle):
        with self._lock:
            self.operations.append(("cleanup", handle))
            self.cleaned.append(handle)
        return True


def bounded(nonce, verdict):
    return (
        f"BEGIN_REVIEW_RESULT {nonce}\n"
        "1. Scope checked\n"
        f"VERDICT: {verdict}\n"
        f"END_REVIEW_RESULT {nonce}\n"
    )


def request(name, verdicts=VERDICTS, verdict_classes=None):
    return LegRequest(
        name=name,
        prompt=f"review {name}",
        narrowed_retry_prompt=f"narrow review {name}",
        allowed_verdicts=verdicts,
        timeout_seconds=1.0,
        verdict_classes=verdict_classes or {},
    )


class ReviewOrchestrationTests(unittest.TestCase):
    def test_known_transcript_presentation_prefixes_and_leading_whitespace_parse(self):
        nonce = "nonce-1414"
        examples = (
            (
                "Codex production-shaped transcript\n"
                "   • BEGIN_REVIEW_RESULT nonce-1414\n"
                "   • Scope checked: fixed candidate's P1 prompt submission and settlement.\n"
                "   • No unresolved in-scope findings.\n"
                "   • VERDICT: CLEAN_FOR_PR\n"
                "   • END_REVIEW_RESULT nonce-1414\n",
                "CLEAN_FOR_PR",
            ),
            (
                "Claude production-shaped transcript\n"
                " \t⏺ BEGIN_REVIEW_RESULT nonce-1414\n"
                "   ⏺ Scope reviewed: prompt submission and concurrent settlement.\n"
                "   ⏺ Finding 1 — P1, in-scope: delayed acceptance is misread.\n"
                "   ⏺ Finding 2 — P2, in-scope: fingerprint calls can overlap.\n"
                "   ⏺ VERDICT: FINDINGS_TO_RESOLVE\n"
                "   ⏺ END_REVIEW_RESULT nonce-1414\n",
                "FINDINGS_TO_RESOLVE",
            ),
        )
        for transcript, expected in examples:
            with self.subTest(expected=expected):
                verdict, failure, detail = _parse_result(
                    RawReviewResult("settled", transcript, "candidate-v1"),
                    nonce,
                    VERDICTS,
                )
                self.assertEqual(expected, verdict)
                self.assertIsNone(failure)
                self.assertEqual("", detail)

    def test_production_prefixed_blocks_preserve_exact_raw_spans(self):
        nonce = "nonce-1414"
        examples = (
            (
                "Codex preamble\n"
                "   • BEGIN_REVIEW_RESULT nonce-1414\r\n"
                "   • Scope checked\r\n"
                "   • VERDICT: CLEAN_FOR_PR\r\n"
                "   • END_REVIEW_RESULT nonce-1414\r\n"
                "Codex footer\n",
                "   • BEGIN_REVIEW_RESULT nonce-1414\r\n"
                "   • Scope checked\r\n"
                "   • VERDICT: CLEAN_FOR_PR\r\n"
                "   • END_REVIEW_RESULT nonce-1414\r\n",
            ),
            (
                "Claude preamble\n"
                " \t⏺ BEGIN_REVIEW_RESULT nonce-1414\n"
                "   ⏺ Scope checked\n"
                "   ⏺ VERDICT: CLEAN_FOR_PR\n"
                "   ⏺ END_REVIEW_RESULT nonce-1414\n"
                "Claude footer\n",
                " \t⏺ BEGIN_REVIEW_RESULT nonce-1414\n"
                "   ⏺ Scope checked\n"
                "   ⏺ VERDICT: CLEAN_FOR_PR\n"
                "   ⏺ END_REVIEW_RESULT nonce-1414\n",
            ),
        )
        for transcript, expected_span in examples:
            with self.subTest(transcript=transcript[:6]):
                block, failure, detail = _extract_result_block(transcript, nonce)
                self.assertIsNone(failure)
                self.assertEqual("", detail)
                self.assertIsNotNone(block)
                self.assertEqual(expected_span, block.raw_span)
                self.assertEqual(
                    "BEGIN_REVIEW_RESULT nonce-1414", block.normalized_lines[0]
                )
                self.assertEqual(
                    "END_REVIEW_RESULT nonce-1414", block.normalized_lines[-1]
                )

    def test_transcript_boundary_and_final_verdict_guardrails_remain_fail_closed(self):
        nonce = "nonce-1414"
        invalid = (
            "? BEGIN_REVIEW_RESULT nonce-1414\nreview\nVERDICT: CLEAN_FOR_PR\n? END_REVIEW_RESULT nonce-1414\n",
            "prefix prose BEGIN_REVIEW_RESULT nonce-1414\nreview\nVERDICT: CLEAN_FOR_PR\nEND_REVIEW_RESULT nonce-1414\n",
            "BEGIN_REVIEW_RESULT nonce-1414\nVERDICT: CLEAN_FOR_PR\nsubstantive text after verdict\nEND_REVIEW_RESULT nonce-1414\n",
            "BEGIN_REVIEW_RESULT nonce-1414\nVERDICT: CLEAN_FOR_PR\nEND_REVIEW_RESULT nonce-1414\n",
            "BEGIN_REVIEW_RESULT other-nonce\nreview\nVERDICT: CLEAN_FOR_PR\nEND_REVIEW_RESULT other-nonce\n",
        )
        for transcript in invalid:
            with self.subTest(transcript=transcript):
                verdict, failure, _ = _parse_result(
                    RawReviewResult("settled", transcript, "candidate-v1"),
                    nonce,
                    VERDICTS,
                )
                self.assertIsNone(verdict)
                self.assertEqual("unusable_output", failure)

    def test_wrap_broken_production_nonce_fences_parse(self):
        nonce = "2f29f0886990c29978747133f94ce4f5"
        hard_wrap = (
            f"• BEGIN_REVIEW_RESULT {nonce[:8]}\n"
            f"{nonce[8:]}\n"
            "• Scope checked hard wrap\n"
            "• No findings\n"
            "• VERDICT: CLEAN_FOR_PR\n"
            f"• END_REVIEW_RESULT {nonce[:8]}\n"
            f"{nonce[8:]}\n"
        )
        soft_like = (
            f"• BEGIN_REVIEW_RESULT {nonce[:20]}\n"
            f"{nonce[20:]}\n"
            "• Scope checked\n"
            "• VERDICT: CLEAN_FOR_PR\n"
            f"• END_REVIEW_RESULT {nonce[:18]}\n"
            f"{nonce[18:]}\n"
        )
        for transcript in (hard_wrap, soft_like):
            with self.subTest(transcript=transcript[:40]):
                verdict, failure, detail = _parse_result(
                    RawReviewResult("settled", transcript, "candidate-v1"),
                    nonce,
                    VERDICTS,
                )
                self.assertEqual("CLEAN_FOR_PR", verdict)
                self.assertIsNone(failure)
                self.assertEqual("", detail)

    def test_duplicate_nonce_blocks_accept_last_complete_block(self):
        nonce = "a8e85687c0ba93a378f4e893e4160823"
        first = (
            f"BEGIN_REVIEW_RESULT {nonce}\n"
            "first body should be ignored\n"
            "VERDICT: FINDINGS_TO_RESOLVE\n"
            f"END_REVIEW_RESULT {nonce}\n"
        )
        second = (
            f"• BEGIN_REVIEW_RESULT {nonce}\n"
            "• last body wins\n"
            "• VERDICT: CLEAN_FOR_PR\n"
            f"• END_REVIEW_RESULT {nonce}\n"
        )
        verdict, failure, detail = _parse_result(
            RawReviewResult("settled", first + second, "candidate-v1"),
            nonce,
            VERDICTS,
        )
        self.assertEqual("CLEAN_FOR_PR", verdict)
        self.assertIsNone(failure)
        self.assertEqual("", detail)
        block, block_failure, _ = _extract_result_block(first + second, nonce)
        self.assertIsNone(block_failure)
        self.assertIsNotNone(block)
        self.assertIn("last body wins", "\n".join(block.normalized_lines))
        self.assertNotIn("first body should be ignored", "\n".join(block.normalized_lines))

    def test_nested_and_unmatched_same_nonce_fences_remain_fail_closed(self):
        nonce = "a8e85687c0ba93a378f4e893e4160823"
        nested = (
            f"BEGIN_REVIEW_RESULT {nonce}\n"
            f"BEGIN_REVIEW_RESULT {nonce}\n"
            "body\n"
            "VERDICT: CLEAN_FOR_PR\n"
            f"END_REVIEW_RESULT {nonce}\n"
        )
        extra_end = (
            f"END_REVIEW_RESULT {nonce}\n"
            f"BEGIN_REVIEW_RESULT {nonce}\n"
            "body\n"
            "VERDICT: CLEAN_FOR_PR\n"
            f"END_REVIEW_RESULT {nonce}\n"
        )
        for transcript in (nested, extra_end):
            with self.subTest(transcript=transcript[:40]):
                verdict, failure, _ = _parse_result(
                    RawReviewResult("settled", transcript, "candidate-v1"),
                    nonce,
                    VERDICTS,
                )
                self.assertIsNone(verdict)
                self.assertEqual("unusable_output", failure)

    def test_structured_result_file_preferred_over_broken_transcript(self):
        nonce = "f" * 32
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "result.json"
            path.write_text(
                json.dumps(
                    {
                        "nonce": nonce,
                        "verdict": "CLEAN_FOR_PR",
                        "body": "structured body evidence",
                    }
                )
            )
            broken_transcript = "no usable fence here\n"
            verdict, failure, detail, block = _validate_result(
                RawReviewResult(
                    "settled",
                    broken_transcript,
                    "candidate-v1",
                    structured_result_path=str(path),
                ),
                nonce,
                VERDICTS,
            )
            self.assertEqual("CLEAN_FOR_PR", verdict)
            self.assertIsNone(failure)
            self.assertEqual("", detail)
            self.assertIsNotNone(block)
            self.assertIn("structured body evidence", "\n".join(block.normalized_lines))

            loaded, load_failure, _ = load_structured_result_file(path, nonce, VERDICTS)
            self.assertIsNone(load_failure)
            self.assertIsNotNone(loaded)

    def test_herdr_agent_name_rules_and_short_generator(self):
        self.assertTrue(is_valid_herdr_agent_name("rvw-cdx-abc123"))
        self.assertTrue(is_valid_herdr_agent_name("a" + ("x" * 31)))
        self.assertFalse(is_valid_herdr_agent_name("a" + ("x" * 32)))
        self.assertFalse(is_valid_herdr_agent_name("ReviewClaude"))
        self.assertFalse(is_valid_herdr_agent_name("1bad"))
        with self.assertRaises(ValueError):
            validate_herdr_agent_name("a" + ("x" * 32))
        with self.assertRaises(ValueError):
            validate_herdr_agent_name("ReviewClaude")
        generated = short_herdr_agent_name("codex", salt="deadbeef")
        self.assertTrue(is_valid_herdr_agent_name(generated))
        self.assertLessEqual(len(generated), 32)
        self.assertTrue(generated.startswith("rvw-codex-"))

    def test_result_digest_is_bound_to_exact_raw_result_block_bytes(self):
        raw_block = (
            "  • BEGIN_REVIEW_RESULT fixed-nonce\n"
            "  • substantive content\n"
            "  • VERDICT: CLEAN_FOR_PR\n"
            "  • END_REVIEW_RESULT fixed-nonce\n"
        )
        raw_transcript = "header with raw spacing  \n" + raw_block + "volatile footer\n"

        class RawTranscriptAdapter(FakeAdapter):
            def wait_for_result(self, handle, timeout_seconds):
                with self._lock:
                    attempt = self._wait_counts.get(handle, 0)
                    self._wait_counts[handle] = attempt + 1
                    self.operations.append(("wait", handle, attempt))
                return RawReviewResult("settled", raw_transcript, self.fingerprint)

        adapter = RawTranscriptAdapter({"codex": {}})
        with mock.patch("scripts.review_orchestration._nonce", return_value="fixed-nonce"):
            result = orchestrate_reviews(adapter, [request("codex")])

        self.assertEqual("CLEAN_FOR_PR", result.status)
        self.assertEqual(
            hashlib.sha256(raw_block.encode("utf-8", "surrogateescape")).hexdigest(),
            result.legs["codex"].result_digest,
        )

    def test_one_reviewer(self):
        adapter = FakeAdapter({"codex": {"results": ["clean"]}})
        result = orchestrate_reviews(adapter, [request("codex")])
        self.assertEqual("CLEAN_FOR_PR", result.status)
        self.assertTrue(result.all_prompts_submitted_before_first_wait)
        self.assertEqual("CLEAN_FOR_PR", result.legs["codex"].verdict)
        self.assertGreaterEqual(result.candidate_wall_time, 0)

    def test_two_successful_reviewers_submit_before_either_wait(self):
        adapter = FakeAdapter({
            "codex": {"delay": 0.02, "results": ["clean"]},
            "claude": {"delay": 0.02, "results": ["clean"]},
        })
        result = orchestrate_reviews(adapter, [request("codex"), request("claude")])
        self.assertEqual("CLEAN_FOR_PR", result.status)
        self.assertTrue(result.all_prompts_submitted_before_first_wait)
        operations = [op[0] for op in adapter.operations]
        self.assertLess(max(i for i, op in enumerate(operations) if op == "submit"), operations.index("wait"))
        self.assertLess(result.candidate_wall_time, 0.038)
        self.assertEqual(2, sum(leg.validation_complete for leg in result.legs.values()))

    def test_one_failed_reviewer_fails_closed(self):
        adapter = FakeAdapter({
            "codex": {"results": ["clean"]},
            "claude": {"results": ["failed"]},
        })
        result = orchestrate_reviews(adapter, [request("codex"), request("claude")])
        self.assertEqual("REVIEW_INFRASTRUCTURE_FAILURE", result.status)
        self.assertFalse(result.clean)
        self.assertEqual(1, adapter._wait_counts["claude"])

    def test_one_incomplete_reviewer_fails_closed_without_unusable_retry(self):
        adapter = FakeAdapter({
            "codex": {"results": ["clean"]},
            "claude": {"results": ["incomplete"]},
        })
        result = orchestrate_reviews(adapter, [request("codex"), request("claude")])
        self.assertEqual("REVIEW_INCOMPLETE_RERUN_NEEDED", result.status)
        self.assertEqual(1, adapter._wait_counts["claude"])

    def test_prompt_stall_recovers_only_proven_stalled_leg(self):
        adapter = FakeAdapter({
            "codex": {"stall": True, "results": ["clean"]},
            "claude": {"results": ["clean"]},
        })
        result = orchestrate_reviews(adapter, [request("codex"), request("claude")])
        self.assertEqual("CLEAN_FOR_PR", result.status)
        self.assertEqual([("enter", "codex")], [op for op in adapter.operations if op[0] == "enter"])

    def test_parallel_dispatches_second_prompt_before_delayed_recovery_confirmation_completes(self):
        adapter = FakeAdapter({
            "codex": {"stall": True, "confirmation_delay": 0.03, "results": ["clean"]},
            "claude": {"results": ["clean"]},
        })

        result = orchestrate_reviews(adapter, [request("codex"), request("claude")])

        self.assertEqual("CLEAN_FOR_PR", result.status)
        self.assertLess(
            adapter.operations.index(("submit", "claude", 0, "candidate-v1")),
            adapter.operations.index(("accepted", "codex")),
        )

    def test_parallel_pending_recovery_confirmations_do_not_serialize(self):
        barrier = threading.Barrier(2)
        adapter = FakeAdapter({
            "codex": {"stall": True, "confirmation_barrier": barrier, "confirmation_delay": 0.02},
            "claude": {"stall": True, "confirmation_barrier": barrier, "confirmation_delay": 0.02},
        })
        result = orchestrate_reviews(adapter, [request("codex"), request("claude")])

        self.assertEqual("CLEAN_FOR_PR", result.status)
        self.assertEqual(
            {"codex", "claude"},
            {op[1] for op in adapter.operations if op[0] == "confirmation_started"},
        )

    def test_parallel_accepts_every_prompt_before_first_result_wait(self):
        adapter = FakeAdapter({
            "codex": {"stall": True, "confirmation_delay": 0.01},
            "claude": {"stall": True, "confirmation_delay": 0.01},
        })

        result = orchestrate_reviews(adapter, [request("codex"), request("claude")])

        first_wait = next(i for i, op in enumerate(adapter.operations) if op[0] == "wait")
        accepted = [i for i, op in enumerate(adapter.operations) if op[0] == "accepted"]
        self.assertEqual("CLEAN_FOR_PR", result.status)
        self.assertEqual(2, len(accepted))
        self.assertLess(max(accepted), first_wait)

    def test_parallel_confirmation_failure_begins_zero_result_waits(self):
        adapter = FakeAdapter({
            "codex": {"stall": True, "confirmation_fails": True},
            "claude": {"stall": True},
        })

        result = orchestrate_reviews(adapter, [request("codex"), request("claude")])

        self.assertEqual("REVIEW_INFRASTRUCTURE_FAILURE", result.status)
        self.assertEqual({}, adapter._wait_counts)
        self.assertEqual("prompt_not_accepted", result.legs["codex"].failure_kind)
        self.assertEqual("prompt_batch_not_accepted", result.legs["claude"].failure_kind)

    def test_candidate_wall_time_includes_delayed_initial_submission(self):
        now = [0.0]

        class DelayedSubmitAdapter(FakeAdapter):
            def submit_prompt(self, handle, prompt, nonce, fingerprint):
                now[0] += 3.0
                return super().submit_prompt(handle, prompt, nonce, fingerprint)

            def wait_for_result(self, handle, timeout_seconds):
                with self._lock:
                    attempt = self._wait_counts.get(handle, 0)
                    self._wait_counts[handle] = attempt + 1
                    submission = self._submissions[handle][attempt]
                now[0] += 2.0
                return RawReviewResult(
                    "settled", bounded(submission[1], "CLEAN_FOR_PR"), submission[2]
                )

        result = orchestrate_reviews(
            DelayedSubmitAdapter({"codex": {}}),
            [request("codex")],
            clock=lambda: now[0],
        )

        self.assertEqual(5.0, result.candidate_wall_time)

    def test_partial_initial_prompt_rejection_begins_zero_waits_and_fails_closed(self):
        adapter = FakeAdapter({
            "codex": {"results": ["clean"]},
            "claude": {"reject": True, "results": ["clean"]},
        })
        result = orchestrate_reviews(adapter, [request("codex"), request("claude")])
        self.assertEqual("REVIEW_INFRASTRUCTURE_FAILURE", result.status)
        self.assertFalse(result.all_prompts_submitted_before_first_wait)
        self.assertEqual({}, adapter._wait_counts)
        self.assertEqual("prompt_not_accepted", result.legs["claude"].failure_kind)
        self.assertEqual("prompt_batch_not_accepted", result.legs["codex"].failure_kind)
        self.assertIn("prompt_batch_aborted", [event.kind for event in result.events])
        self.assertEqual([], adapter.cleaned)

    def test_fingerprint_mutation_rejects_both_results_as_stale(self):
        adapter = FakeAdapter(
            {
                "codex": {"delay": 0.01, "results": ["clean"]},
                "claude": {"delay": 0.02, "results": ["clean"]},
            },
            mutate_on_wait="codex",
        )
        result = orchestrate_reviews(adapter, [request("codex"), request("claude")])
        self.assertEqual("REVIEW_INFRASTRUCTURE_FAILURE", result.status)
        self.assertTrue(all(leg.failure_kind == "stale_fingerprint" for leg in result.legs.values()))

    def test_unusable_output_retries_only_affected_leg_once(self):
        adapter = FakeAdapter({
            "codex": {"results": ["bad-boundary", "clean"]},
            "claude": {"results": ["clean"]},
        })
        result = orchestrate_reviews(adapter, [request("codex"), request("claude")])
        self.assertEqual("CLEAN_FOR_PR", result.status)
        self.assertEqual(2, adapter._wait_counts["codex"])
        self.assertEqual(1, adapter._wait_counts["claude"])
        self.assertTrue(result.legs["codex"].retried_unusable_output)

    def test_narrowed_retry_records_the_retry_nonce(self):
        adapter = FakeAdapter({"codex": {"results": ["bad-boundary", "clean"]}})
        with mock.patch(
            "scripts.review_orchestration._nonce",
            side_effect=("initial-nonce", "retry-nonce"),
        ):
            result = orchestrate_reviews(adapter, [request("codex")])

        self.assertEqual("CLEAN_FOR_PR", result.status)
        self.assertEqual("retry-nonce", result.legs["codex"].result_nonce)
        self.assertNotEqual("initial-nonce", result.legs["codex"].result_nonce)
        self.assertEqual(
            "retry-nonce", result_record(result)["legs"]["codex"]["result_nonce"]
        )

    def test_unusable_output_exhausted_retry_fails_closed(self):
        adapter = FakeAdapter({"codex": {"results": ["bad-boundary", "bad-boundary"]}})
        result = orchestrate_reviews(adapter, [request("codex")])
        self.assertEqual("REVIEW_INFRASTRUCTURE_FAILURE", result.status)
        self.assertEqual(2, adapter._wait_counts["codex"])
        self.assertEqual("unusable_output", result.legs["codex"].failure_kind)

    def test_findings_aggregate_cannot_be_hidden_by_clean_sibling(self):
        adapter = FakeAdapter({
            "codex": {"results": ["clean"]},
            "claude": {"results": ["findings"]},
        })
        result = orchestrate_reviews(adapter, [request("codex"), request("claude")])
        self.assertEqual("FINDINGS_TO_RESOLVE", result.status)
        self.assertFalse(result.clean)

    def test_plan_ready_verdicts_are_a_clean_aggregate(self):
        adapter = FakeAdapter({
            "codex": {"results": ["plan-ready"]},
            "claude": {"results": ["plan-ready"]},
        })
        requests = [
            request("codex", PLAN_VERDICTS),
            request("claude", PLAN_VERDICTS),
        ]

        result = orchestrate_reviews(adapter, requests)

        self.assertEqual("PLAN_EXECUTION_READY", result.status)
        self.assertTrue(result.clean)
        self.assertEqual(
            {"pass"}, {outcome.verdict_class for outcome in result.legs.values()}
        )
        self.assertEqual(
            "pass", result_record(result)["legs"]["claude"]["verdict_class"]
        )

    def test_plan_revision_dominates_ready_sibling_without_infrastructure_failure(self):
        adapter = FakeAdapter({
            "codex": {"results": ["plan-ready"]},
            "claude": {"results": ["plan-revision"]},
        })
        requests = [
            request("codex", PLAN_VERDICTS),
            request("claude", PLAN_VERDICTS),
        ]

        result = orchestrate_reviews(adapter, requests)

        self.assertEqual("PLAN_NEEDS_REVISION", result.status)
        self.assertFalse(result.clean)

    def test_scoped_pass_verdicts_are_a_clean_aggregate(self):
        adapter = FakeAdapter({
            "codex": {"results": ["pass-scoped"]},
            "claude": {"results": ["pass-scoped"]},
        })
        scoped_verdicts = (
            "PASS_SCOPED",
            "FIX_IN_SCOPE_FINDINGS",
            "BLOCKED_BY_SCOPE_QUESTION",
            "REVIEW_INCOMPLETE_RERUN_NEEDED",
        )

        result = orchestrate_reviews(
            adapter,
            [request("codex", scoped_verdicts), request("claude", scoped_verdicts)],
        )

        self.assertEqual("PASS_SCOPED", result.status)
        self.assertTrue(result.clean)

    def test_pass_is_the_forward_clean_aggregate(self):
        adapter = FakeAdapter({
            "codex": {"results": ["pass"]},
            "claude": {"results": ["pass"]},
        })
        forward_verdicts = (
            "PASS",
            "FINDINGS_TO_RESOLVE",
            "BLOCKED_BY_QUESTION",
            "REVIEW_INCOMPLETE_RERUN_NEEDED",
        )

        result = orchestrate_reviews(
            adapter,
            [request("codex", forward_verdicts), request("claude", forward_verdicts)],
        )

        self.assertEqual("PASS", result.status)
        self.assertTrue(result.clean)
        self.assertEqual(
            {"pass"}, {outcome.verdict_class for outcome in result.legs.values()}
        )

    def test_direct_call_rejects_shared_verdict_reclassification_before_transport(self):
        adapter = FakeAdapter({"codex": {"results": ["findings"]}})
        bad_request = request(
            "codex",
            ("FINDINGS_TO_RESOLVE",),
            {"FINDINGS_TO_RESOLVE": "pass"},
        )

        with self.assertRaisesRegex(ValueError, "shared workflow verdicts cannot be reclassified"):
            orchestrate_reviews(adapter, [bad_request])

        self.assertEqual([], adapter.operations)

    def test_direct_call_rejects_unclassified_verdict_before_transport(self):
        adapter = FakeAdapter({"codex": {}})

        with self.assertRaisesRegex(ValueError, "require outcome classes before launch"):
            orchestrate_reviews(adapter, [request("codex", ("CUSTOM_READY",))])

        self.assertEqual([], adapter.operations)

    def test_custom_verdict_class_supports_new_workflow_tokens(self):
        custom = ("CUSTOM_READY", "CUSTOM_FINDINGS")
        classes = {"CUSTOM_READY": "pass", "CUSTOM_FINDINGS": "findings"}

        class CustomAdapter(FakeAdapter):
            def wait_for_result(self, handle, timeout_seconds):
                with self._lock:
                    attempt = self._wait_counts.get(handle, 0)
                    self._wait_counts[handle] = attempt + 1
                    submission = self._submissions[handle][attempt]
                return RawReviewResult(
                    "settled", bounded(submission[1], "CUSTOM_READY"), submission[2]
                )

        result = orchestrate_reviews(
            CustomAdapter({"codex": {}}),
            [request("codex", custom, classes)],
        )

        self.assertEqual("CUSTOM_READY", result.status)
        self.assertTrue(result.clean)

    def test_raw_result_preserves_legacy_fake_adapter_positional_detail(self):
        raw = RawReviewResult("provider_error", "", "candidate-v1", False, "legacy detail")
        self.assertEqual("legacy detail", raw.detail)
        self.assertIsNone(raw.first_action_observed_at)

    def test_recorder_uses_adapter_first_action_observation_timestamp(self):
        now = [0.0]

        class TimestampAdapter(FakeAdapter):
            def wait_for_result(self, handle, timeout_seconds):
                with self._lock:
                    attempt = self._wait_counts.get(handle, 0)
                    self._wait_counts[handle] = attempt + 1
                    submission = self._submissions[handle][attempt]
                now[0] = 7.0
                return RawReviewResult(
                    "settled",
                    bounded(submission[1], "CLEAN_FOR_PR"),
                    submission[2],
                    first_action_observed=True,
                    first_action_observed_at=2.0,
                )

        result = orchestrate_reviews(
            TimestampAdapter({"codex": {"results": ["clean"]}}),
            [request("codex")],
            clock=lambda: now[0],
        )
        first_action = next(event for event in result.events if event.kind == "first_action")
        settled = next(event for event in result.events if event.kind == "settled")
        self.assertEqual(2.0, first_action.timestamp)
        self.assertEqual(7.0, settled.timestamp)
        self.assertEqual(5.0, settled.timestamp - first_action.timestamp)

    def test_cleanup_requires_clean_result_and_written_artifact(self):
        adapter = FakeAdapter({"codex": {"results": ["clean"]}})
        result = orchestrate_reviews(adapter, [request("codex")])
        self.assertFalse(cleanup_review_tabs(adapter, result, artifact_written=False))
        self.assertEqual([], adapter.cleaned)
        result.legs["codex"].verdict = "FINDINGS_TO_RESOLVE"
        result.legs["codex"].verdict_class = "findings"
        self.assertFalse(cleanup_review_tabs(adapter, result, artifact_written=True))
        self.assertEqual([], adapter.cleaned)
        result.legs["codex"].verdict_class = "pass"
        self.assertFalse(cleanup_review_tabs(adapter, result, artifact_written=True))
        self.assertEqual([], adapter.cleaned)
        result.legs["codex"].verdict = "CUSTOM_UNKNOWN"
        self.assertFalse(cleanup_review_tabs(adapter, result, artifact_written=True))
        self.assertEqual([], adapter.cleaned)
        result.legs["codex"].verdict = "CLEAN_FOR_PR"
        result.legs["codex"].verdict_class = "pass"
        self.assertTrue(cleanup_review_tabs(adapter, result, artifact_written=True))
        self.assertEqual(["codex"], adapter.cleaned)
        self.assertIn("cleanup_complete", [event.kind for event in result.events])

    def test_direct_cleanup_supports_custom_pass_only_with_validated_request_profile(self):
        adapter = FakeAdapter({"codex": {}})
        custom_request = request(
            "codex",
            ("CUSTOM_READY", "CUSTOM_FINDINGS"),
            {"CUSTOM_READY": "pass", "CUSTOM_FINDINGS": "findings"},
        )
        outcome = LegOutcome(
            "codex",
            "codex",
            verdict="CUSTOM_READY",
            verdict_class="pass",
            validation_complete=True,
            result_nonce="nonce",
            result_digest="digest",
        )
        result = OrchestrationResult(
            status="CUSTOM_READY",
            fingerprint="candidate-v1",
            legs={"codex": outcome},
            events=[],
            candidate_wall_time=0.0,
            all_prompts_submitted_before_first_wait=True,
            mode="parallel",
            clean=True,
        )

        self.assertFalse(cleanup_review_tabs(adapter, result, artifact_written=True))
        disallowed_request = request(
            "codex",
            ("CUSTOM_FINDINGS",),
            {"CUSTOM_READY": "pass", "CUSTOM_FINDINGS": "findings"},
        )
        self.assertFalse(
            cleanup_review_tabs(
                adapter,
                result,
                artifact_written=True,
                requests={"codex": disallowed_request},
            )
        )
        self.assertTrue(
            cleanup_review_tabs(
                adapter,
                result,
                artifact_written=True,
                requests={"codex": custom_request},
            )
        )


class TemporaryGitRepository:
    def __enter__(self):
        self._temp = tempfile.TemporaryDirectory()
        self.path = Path(self._temp.name)
        subprocess.run(["git", "init", "-q"], cwd=self.path, check=True)
        subprocess.run(["git", "config", "user.email", "review@example.com"], cwd=self.path, check=True)
        subprocess.run(["git", "config", "user.name", "Review Test"], cwd=self.path, check=True)
        (self.path / "tracked.txt").write_text("base\n")
        subprocess.run(["git", "add", "tracked.txt"], cwd=self.path, check=True)
        subprocess.run(["git", "commit", "-qm", "base"], cwd=self.path, check=True)
        return self.path

    def __exit__(self, exc_type, exc, traceback):
        self._temp.cleanup()


class FakeHerdrRunner:
    def __init__(self):
        self.operations = []
        self.states = {"codex-target": "idle", "claude-target": "idle"}
        self.sequences = {"codex-target": 10, "claude-target": 20}
        self.tab_ids = {"codex-target": "tab-codex", "claude-target": "tab-claude"}
        self.prompts = {}
        self.nonces = {}
        self.closed_tabs = set()
        self.stall_target = None
        self.success_stall_target = None
        self.wait_intervals = {}
        self.transcript_overrides = {}
        self.structured_results = {}
        self.worktree_mutation_path = None
        self.verdicts = {
            "codex-target": "CLEAN_FOR_PR",
            "claude-target": "CLEAN_FOR_PR",
        }
        self.listed_tabs_override = None
        self.listed_tabs_payload = None
        self.wait_barrier = None
        self.active_git_commands = 0
        self.max_active_git_commands = 0
        self._lock = threading.Lock()

    def __call__(self, argv, cwd=None, timeout=None):
        if argv[0] == "git":
            with self._lock:
                self.active_git_commands += 1
                self.max_active_git_commands = max(
                    self.max_active_git_commands, self.active_git_commands
                )
            try:
                time.sleep(0.003)
                return subprocess_command_runner(argv, cwd, timeout)
            finally:
                with self._lock:
                    self.active_git_commands -= 1
        command = tuple(argv)
        with self._lock:
            self.operations.append(command)
        if command[:3] == ("herdr", "agent", "get"):
            return CommandResult(0, json.dumps({
                "id": command[3],
                "result": {"agent": {
                    "agent_status": self.states[command[3]],
                    "state_change_seq": self.sequences[command[3]],
                    "tab_id": self.tab_ids[command[3]],
                }},
            }))
        if command[:3] == ("herdr", "agent", "prompt"):
            target, prompt = command[3], command[4]
            self.prompts[target] = prompt
            match = re.search(r"Transaction nonce: ([0-9a-f]+)", prompt)
            self.nonces[target] = match.group(1)
            structured_match = re.search(
                r"Structured result file \(preferred when you can write files\): (.+)", prompt
            )
            if target in self.structured_results:
                Path(structured_match.group(1)).write_text(
                    json.dumps({
                        "nonce": self.nonces[target],
                        "verdict": self.structured_results[target]["verdict"],
                        "body": self.structured_results[target]["body"],
                    })
                )
            if self.worktree_mutation_path is not None:
                self.worktree_mutation_path.write_text("candidate changed\n")
            if target == self.stall_target:
                return CommandResult(1, "", "agent_prompt_stalled")
            if target != self.success_stall_target:
                self.states[target] = "working"
                self.sequences[target] += 1
            return CommandResult(0, json.dumps({"accepted": True}))
        if command[:3] == ("herdr", "agent", "send-keys"):
            target = command[3]
            self.states[target] = "working"
            self.sequences[target] += 1
            return CommandResult(0, "{}")
        if command[:3] == ("herdr", "agent", "wait"):
            target = command[3]
            started = time.monotonic()
            if self.wait_barrier is not None:
                self.wait_barrier.wait(timeout=1.0)
            time.sleep(0.03)
            ended = time.monotonic()
            with self._lock:
                self.wait_intervals[target] = (started, ended)
            self.states[target] = "idle"
            self.sequences[target] += 1
            return CommandResult(0, json.dumps({"state": "idle"}))
        if command[:3] == ("herdr", "agent", "read"):
            target = command[3]
            source = command[5]
            if source == "visible":
                return CommandResult(0, self.prompts[target])
            transcript = self.prompts[target] + "\n" + bounded(
                self.nonces[target], self.verdicts[target]
            )
            return CommandResult(0, self.transcript_overrides.get(target, transcript))
        if command[:3] == ("herdr", "tab", "close"):
            self.closed_tabs.add(command[3])
            return CommandResult(0, "{}")
        if command[:3] == ("herdr", "tab", "list"):
            if self.listed_tabs_payload is not None:
                return CommandResult(0, json.dumps(self.listed_tabs_payload))
            available = self.listed_tabs_override or ("tab-codex", "tab-claude")
            visible = [tab for tab in available if tab not in self.closed_tabs]
            return CommandResult(0, json.dumps({
                "id": "tab-list",
                "result": {"tabs": visible},
            }))
        raise AssertionError(command)


class SequenceClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


class SequenceHerdrRunner:
    def __init__(
        self,
        snapshots,
        transcript="review result",
        clock=None,
        wait_duration=0.0,
        visible_transcript=None,
    ):
        self.snapshots = list(snapshots)
        self.last_snapshot = self.snapshots[-1] if self.snapshots else None
        self.transcript = transcript
        self.visible_transcript = visible_transcript
        self.submitted_prompt = ""
        self.clock = clock
        self.wait_duration = wait_duration
        self.operations = []

    def __call__(self, argv, cwd=None, timeout=None):
        command = tuple(argv)
        self.operations.append(command)
        if command[:3] == ("herdr", "agent", "get"):
            snapshot = self.snapshots.pop(0) if self.snapshots else self.last_snapshot
            if isinstance(snapshot, CommandResult):
                return snapshot
            state, sequence = snapshot
            return CommandResult(0, json.dumps({
                "id": "agent-get",
                "result": {"agent": {
                    "agent_status": state,
                    "state_change_seq": sequence,
                }},
            }))
        if command[:3] == ("herdr", "agent", "prompt"):
            self.submitted_prompt = command[4]
            return CommandResult(0, json.dumps({"accepted": True}))
        if command[:3] == ("herdr", "agent", "send-keys"):
            return CommandResult(0, "{}")
        if command[:3] == ("herdr", "agent", "wait"):
            if self.clock is not None and self.wait_duration:
                self.clock.sleep(self.wait_duration)
            return CommandResult(0, json.dumps({"state": "idle"}))
        if command[:3] == ("herdr", "agent", "read"):
            if command[5] == "visible":
                if isinstance(self.visible_transcript, CommandResult):
                    return self.visible_transcript
                visible = (
                    self.submitted_prompt
                    if self.visible_transcript == "submitted"
                    else self.visible_transcript
                )
                return CommandResult(0, visible or "")
            return CommandResult(0, self.transcript)
        raise AssertionError(command)


def sequence_adapter(repo, runner, clock):
    leg = HerdrLeg(request("codex"), "codex-target", "tab-codex", "workspace-1")
    adapter = HerdrReviewAdapter(
        repo,
        {"codex": leg},
        runner=runner,
        clock=clock.monotonic,
        sleeper=clock.sleep,
        transition_poll_interval=1.0,
    )
    adapter.current_fingerprint = lambda: "candidate-v1"
    return adapter, leg


def write_run_request(
    root,
    worktree,
    names=("codex", "claude"),
    verdicts=VERDICTS,
    verdict_classes=None,
):
    reviewers = []
    for name in names:
        prompt = root / f"{name}.txt"
        retry = root / f"{name}-retry.txt"
        prompt.write_text(f"Review {name}")
        retry.write_text(f"Narrow review {name}")
        reviewers.append({
            "name": name,
            "target": f"{name}-target",
            "tab_id": f"tab-{name}",
            "workspace_id": "workspace-1",
            "prompt_file": str(prompt),
            "narrowed_retry_prompt_file": str(retry),
            "allowed_verdicts": list(verdicts),
            "timeout_seconds": 1,
        })
    request_path = root / "request.json"
    payload = {
        "worktree": str(worktree),
        "reviewers": reviewers,
    }
    if verdict_classes is not None:
        payload["verdict_classes"] = verdict_classes
    request_path.write_text(json.dumps(payload))
    return request_path


class ProductionAdapterTests(unittest.TestCase):
    def test_subprocess_runner_preserves_raw_line_endings(self):
        result = subprocess_command_runner([
            sys.executable,
            "-c",
            "import sys; sys.stdout.buffer.write(b'one\\r\\ntwo\\n')",
        ])
        self.assertEqual(0, result.returncode)
        self.assertEqual("one\r\ntwo\n", result.stdout)

    def test_request_load_rejects_unclassified_verdict_before_launch(self):
        with TemporaryGitRepository() as repo, tempfile.TemporaryDirectory() as temp:
            request_path = write_run_request(
                Path(temp), repo, names=("codex",), verdicts=("CUSTOM_READY",)
            )

            with self.assertRaisesRegex(ValueError, "require outcome classes before launch"):
                _load_run_request(request_path)

    def test_request_load_accepts_explicit_custom_verdict_classes(self):
        with TemporaryGitRepository() as repo, tempfile.TemporaryDirectory() as temp:
            request_path = write_run_request(
                Path(temp),
                repo,
                names=("codex",),
                verdicts=("CUSTOM_READY",),
                verdict_classes={"CUSTOM_READY": "pass"},
            )

            _, requests, _ = _load_run_request(request_path)

            self.assertEqual("pass", requests[0].verdict_classes["CUSTOM_READY"])

    def test_request_load_rejects_reclassification_of_shared_verdict(self):
        with TemporaryGitRepository() as repo, tempfile.TemporaryDirectory() as temp:
            request_path = write_run_request(
                Path(temp),
                repo,
                names=("codex",),
                verdicts=("PLAN_EXECUTION_READY",),
                verdict_classes={"PLAN_EXECUTION_READY": "findings"},
            )

            with self.assertRaisesRegex(ValueError, "cannot redefine shared workflow verdicts"):
                _load_run_request(request_path)

    def test_request_load_rejects_missing_empty_or_non_string_workspace_id(self):
        with TemporaryGitRepository() as repo, tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for workspace_id in (None, "", "   ", 7, False, []):
                request_path = write_run_request(root, repo, names=("codex",))
                payload = json.loads(request_path.read_text())
                if workspace_id is None:
                    payload["reviewers"][0].pop("workspace_id")
                else:
                    payload["reviewers"][0]["workspace_id"] = workspace_id
                request_path.write_text(json.dumps(payload))
                with self.subTest(workspace_id=workspace_id):
                    with self.assertRaisesRegex(ValueError, "workspace_id must be a non-empty string"):
                        _load_run_request(request_path)

    def test_run_command_fails_closed_when_workspace_id_is_missing_or_empty(self):
        with TemporaryGitRepository() as repo, tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for workspace_id in (None, ""):
                request_path = write_run_request(root, repo, names=("codex",))
                payload = json.loads(request_path.read_text())
                if workspace_id is None:
                    payload["reviewers"][0].pop("workspace_id")
                else:
                    payload["reviewers"][0]["workspace_id"] = workspace_id
                request_path.write_text(json.dumps(payload))
                stdout = io.StringIO()
                with self.subTest(workspace_id=workspace_id), contextlib.redirect_stdout(stdout):
                    code = main(["run", "--request", str(request_path)])
                    record = json.loads(stdout.getvalue())
                    self.assertEqual(2, code)
                    self.assertEqual("REVIEW_INFRASTRUCTURE_FAILURE", record["status"])
                    self.assertFalse(record["clean"])
                    self.assertIn("workspace_id", record["error"])

    def test_agent_get_actual_envelope_reports_working_idle_and_done(self):
        for state in ("working", "idle", "done"):
            response = CommandResult(0, json.dumps({
                "id": "agent-get",
                "result": {"agent": {"agent_status": state}},
            }))
            with self.subTest(state=state):
                self.assertEqual(state, HerdrReviewAdapter._state(response))

    def test_agent_get_malformed_payload_fails_closed_as_unknown(self):
        malformed = (
            CommandResult(0, "not-json"),
            CommandResult(0, json.dumps({"result": {"agent": {"agent_status": []}}})),
            CommandResult(0, json.dumps({"result": {"agent": {}}})),
        )
        for response in malformed:
            with self.subTest(payload=response.stdout):
                self.assertEqual("unknown", HerdrReviewAdapter._state(response))

    def test_agent_snapshot_parses_actual_nonnegative_integer_sequence_from_supported_envelopes(self):
        supported = (
            ({"agent": {"agent_status": "idle", "state_change_seq": 0}}, ("idle", 0)),
            (
                {"id": "agent-get", "result": {"agent": {
                    "agent_status": "done", "state_change_seq": 42,
                }}},
                ("done", 42),
            ),
        )
        for payload, expected in supported:
            with self.subTest(payload=payload):
                self.assertEqual(
                    expected,
                    HerdrReviewAdapter._agent_snapshot(CommandResult(0, json.dumps(payload))),
                )

    def test_agent_snapshot_rejects_missing_malformed_and_non_integer_sequence(self):
        malformed_sequences = (None, -1, 1.5, "1", True, [], {})
        for sequence in malformed_sequences:
            agent = {"agent_status": "idle"}
            if sequence is not None:
                agent["state_change_seq"] = sequence
            response = CommandResult(0, json.dumps({"result": {"agent": agent}}))
            with self.subTest(sequence=sequence):
                self.assertIsNone(HerdrReviewAdapter._agent_snapshot(response))

    def test_enter_recovery_attempt_resets_for_narrowed_retry_submission(self):
        with TemporaryGitRepository() as repo:
            clock = SequenceClock()
            runner = SequenceHerdrRunner([("idle", 10), ("idle", 10)])
            adapter, leg = sequence_adapter(repo, runner, clock)

            self.assertTrue(adapter.submit_prompt(leg, "review", "nonce-1", "candidate-v1").accepted)
            self.assertTrue(adapter.send_enter(leg))
            self.assertFalse(adapter.send_enter(leg))
            self.assertTrue(adapter.submit_prompt(leg, "narrow", "nonce-2", "candidate-v1").accepted)
            self.assertTrue(adapter.send_enter(leg))
            self.assertEqual(2, sum(
                command[:3] == ("herdr", "agent", "send-keys")
                for command in runner.operations
            ))

    def test_prompt_accepted_polls_until_delayed_send_enter_sequence_advance(self):
        with TemporaryGitRepository() as repo:
            clock = SequenceClock()
            runner = SequenceHerdrRunner([
                ("idle", 10),
                ("idle", 10),
                ("working", 11),
            ])
            adapter, leg = sequence_adapter(repo, runner, clock)
            self.assertTrue(adapter.submit_prompt(leg, "review", "nonce", "candidate-v1").accepted)
            self.assertTrue(adapter.send_enter(leg))

            self.assertTrue(adapter.prompt_accepted(leg))
            self.assertEqual(1.0, clock.now)
            self.assertEqual(1, sum(
                command[:3] == ("herdr", "agent", "prompt")
                for command in runner.operations
            ))
            self.assertEqual(1, sum(
                command[:3] == ("herdr", "agent", "send-keys")
                for command in runner.operations
            ))

    def test_wait_retains_send_enter_recovery_first_transition_timestamp(self):
        with TemporaryGitRepository() as repo:
            clock = SequenceClock()
            runner = SequenceHerdrRunner([
                ("idle", 10),
                ("idle", 10),
                ("working", 11),
                ("working", 11),
                ("idle", 12),
            ], clock=clock, wait_duration=4.0)
            adapter, leg = sequence_adapter(repo, runner, clock)
            self.assertTrue(adapter.submit_prompt(leg, "review", "nonce", "candidate-v1").accepted)
            self.assertTrue(adapter.send_enter(leg))
            self.assertTrue(adapter.prompt_accepted(leg))
            self.assertEqual(1.0, clock.now)

            clock.sleep(3.0)
            raw = adapter.wait_for_result(leg, 20.0)

            self.assertEqual("settled", raw.state)
            self.assertTrue(raw.first_action_observed)
            self.assertEqual(1.0, raw.first_action_observed_at)
            self.assertEqual(8.0, clock.now)
            self.assertEqual(7.0, clock.now - raw.first_action_observed_at)

    def test_prompt_accepted_rejects_unchanged_decreasing_and_malformed_sequences_without_resubmission(self):
        cases = (
            ([("idle", 10), ("idle", 10)], 1.0),
            ([("idle", 10), ("idle", 9)], 0.0),
            ([("idle", 10), CommandResult(0, json.dumps({"result": {"agent": {
                "agent_status": "idle", "state_change_seq": "11",
            }}}))], 0.0),
        )
        with TemporaryGitRepository() as repo:
            for snapshots, expected_time in cases:
                clock = SequenceClock()
                runner = SequenceHerdrRunner(snapshots)
                adapter, leg = sequence_adapter(repo, runner, clock)
                self.assertTrue(adapter.submit_prompt(leg, "review", "nonce", "candidate-v1").accepted)
                self.assertTrue(adapter.send_enter(leg))

                with self.subTest(snapshots=snapshots):
                    self.assertFalse(adapter.prompt_accepted(leg))
                    self.assertEqual(expected_time, clock.now)
                    self.assertEqual(1, sum(
                        command[:3] == ("herdr", "agent", "prompt")
                        for command in runner.operations
                    ))
                    self.assertEqual(1, sum(
                        command[:3] == ("herdr", "agent", "send-keys")
                        for command in runner.operations
                    ))

    def test_wait_observes_delayed_new_working_sequence_then_settled_result(self):
        with TemporaryGitRepository() as repo:
            clock = SequenceClock()
            runner = SequenceHerdrRunner([
                ("idle", 10),
                ("idle", 10),
                ("idle", 10),
                ("working", 11),
                ("idle", 12),
            ], clock=clock, wait_duration=4.0)
            adapter, leg = sequence_adapter(repo, runner, clock)
            submission = adapter.submit_prompt(leg, "review", "nonce", "candidate-v1")
            raw = adapter.wait_for_result(leg, 20.0)

            self.assertTrue(submission.accepted)
            self.assertEqual("settled", raw.state)
            self.assertTrue(raw.first_action_observed)
            self.assertEqual(2.0, raw.first_action_observed_at)
            self.assertEqual("review result", raw.output)
            self.assertEqual(6.0, clock.now)
            self.assertEqual(4.0, clock.now - raw.first_action_observed_at)
            self.assertTrue(any(command[:3] == ("herdr", "agent", "wait") for command in runner.operations))

    def test_wait_accepts_direct_new_settled_sequence_without_sampling_working(self):
        with TemporaryGitRepository() as repo:
            clock = SequenceClock()
            runner = SequenceHerdrRunner([("done", 7), ("idle", 8)])
            adapter, leg = sequence_adapter(repo, runner, clock)
            self.assertTrue(adapter.submit_prompt(leg, "review", "nonce", "candidate-v1").accepted)

            raw = adapter.wait_for_result(leg, 20.0)

            self.assertEqual("settled", raw.state)
            self.assertTrue(raw.first_action_observed)
            self.assertEqual(0.0, raw.first_action_observed_at)
            self.assertLessEqual(raw.first_action_observed_at, clock.now)
            self.assertFalse(any(command[:3] == ("herdr", "agent", "wait") for command in runner.operations))
            self.assertTrue(any(command[:3] == ("herdr", "agent", "read") for command in runner.operations))

    def test_successful_prompt_with_exact_visible_proof_gets_one_enter_and_accepts_later_transition(self):
        with TemporaryGitRepository() as repo:
            clock = SequenceClock()
            runner = SequenceHerdrRunner(
                [("idle", 10)] * 7 + [("working", 11), ("idle", 12)],
                transcript="review result",
                visible_transcript="submitted",
                clock=clock,
                wait_duration=4.0,
            )
            adapter, leg = sequence_adapter(repo, runner, clock)
            self.assertTrue(adapter.submit_prompt(leg, "review", "nonce", "candidate-v1").accepted)

            raw = adapter.wait_for_result(leg, 20.0)

            self.assertEqual("settled", raw.state)
            self.assertTrue(raw.first_action_observed)
            self.assertEqual(5.0, raw.first_action_observed_at)
            self.assertEqual(1, sum(
                command[:3] == ("herdr", "agent", "send-keys")
                for command in runner.operations
            ))
            self.assertTrue(any(
                command[:3] == ("herdr", "agent", "wait")
                for command in runner.operations
            ))

    def test_successful_prompt_stall_with_visible_mismatch_never_sends_enter(self):
        with TemporaryGitRepository() as repo:
            clock = SequenceClock()
            runner = SequenceHerdrRunner(
                [("idle", 3)], visible_transcript="a different visible prompt"
            )
            adapter, leg = sequence_adapter(repo, runner, clock)
            self.assertTrue(adapter.submit_prompt(leg, "review", "nonce", "candidate-v1").accepted)

            raw = adapter.wait_for_result(leg, 30.0)

            self.assertEqual("provider_error", raw.state)
            self.assertIn("did not end with the exact", raw.detail)
            self.assertEqual(5.0, clock.now)
            self.assertFalse(any(
                command[:3] == ("herdr", "agent", "send-keys")
                for command in runner.operations
            ))
            self.assertFalse(any(
                command[:3] == ("herdr", "agent", "wait")
                for command in runner.operations
            ))

    def test_second_non_transition_after_enter_never_sends_a_second_enter(self):
        with TemporaryGitRepository() as repo:
            clock = SequenceClock()
            runner = SequenceHerdrRunner(
                [("idle", 3)], visible_transcript="submitted"
            )
            adapter, leg = sequence_adapter(repo, runner, clock)
            self.assertTrue(adapter.submit_prompt(leg, "review", "nonce", "candidate-v1").accepted)

            raw = adapter.wait_for_result(leg, 20.0)

            self.assertEqual("provider_error", raw.state)
            self.assertIn("one permitted Enter recovery", raw.detail)
            self.assertEqual(10.0, clock.now)
            self.assertEqual(1, sum(
                command[:3] == ("herdr", "agent", "send-keys")
                for command in runner.operations
            ))
            self.assertEqual(1, sum(
                command[:3] == ("herdr", "agent", "read") and command[5] == "visible"
                for command in runner.operations
            ))

    def test_prompt_stall_is_transport_failure_without_unusable_output_retry(self):
        with TemporaryGitRepository() as repo:
            clock = SequenceClock()
            runner = SequenceHerdrRunner([("idle", 3)])
            adapter, _ = sequence_adapter(repo, runner, clock)
            adapter.capture_fingerprint = lambda: "candidate-v1"

            result = orchestrate_reviews(adapter, [request("codex")])

            self.assertEqual("REVIEW_INFRASTRUCTURE_FAILURE", result.status)
            self.assertEqual(
                "provider_or_transport_failure",
                result.legs["codex"].failure_kind,
            )
            self.assertFalse(result.legs["codex"].retried_unusable_output)
            self.assertEqual(1, sum(
                command[:3] == ("herdr", "agent", "prompt")
                for command in runner.operations
            ))
            self.assertEqual(1, sum(
                command[:3] == ("herdr", "agent", "read") and command[5] == "visible"
                for command in runner.operations
            ))
            self.assertFalse(any(
                command[:3] == ("herdr", "agent", "send-keys")
                for command in runner.operations
            ))

    def test_submit_and_wait_fail_closed_for_invalid_or_decreasing_sequences(self):
        invalid_baselines = (
            CommandResult(0, json.dumps({"result": {"agent": {"agent_status": "idle"}}})),
            CommandResult(0, json.dumps({"result": {"agent": {
                "agent_status": "idle", "state_change_seq": "4",
            }}})),
        )
        with TemporaryGitRepository() as repo:
            for baseline in invalid_baselines:
                clock = SequenceClock()
                runner = SequenceHerdrRunner([baseline])
                adapter, leg = sequence_adapter(repo, runner, clock)
                with self.subTest(baseline=baseline.stdout):
                    submission = adapter.submit_prompt(leg, "review", "nonce", "candidate-v1")
                    self.assertFalse(submission.accepted)
                    self.assertIn("pre-submit", submission.detail)
                    self.assertFalse(any(
                        command[:3] == ("herdr", "agent", "prompt")
                        for command in runner.operations
                    ))

            invalid_post_submit = (
                CommandResult(0, json.dumps({"result": {"agent": {"agent_status": "idle"}}})),
                CommandResult(0, json.dumps({"result": {"agent": {
                    "agent_status": "idle", "state_change_seq": 4.5,
                }}})),
                CommandResult(1, "", "agent unavailable"),
            )
            for invalid in invalid_post_submit:
                clock = SequenceClock()
                runner = SequenceHerdrRunner([("idle", 9), invalid])
                adapter, leg = sequence_adapter(repo, runner, clock)
                self.assertTrue(adapter.submit_prompt(leg, "review", "nonce", "candidate-v1").accepted)
                with self.subTest(post_submit=invalid.stdout or invalid.stderr):
                    raw = adapter.wait_for_result(leg, 20.0)
                    self.assertEqual("provider_error", raw.state)
                    self.assertIn("post-submit", raw.detail)
                    self.assertFalse(any(
                        command[:3] == ("herdr", "agent", "read")
                        for command in runner.operations
                    ))
                    self.assertFalse(any(
                        command[:3] == ("herdr", "agent", "send-keys")
                        for command in runner.operations
                    ))

            clock = SequenceClock()
            runner = SequenceHerdrRunner([("idle", 9), ("working", 8)])
            adapter, leg = sequence_adapter(repo, runner, clock)
            self.assertTrue(adapter.submit_prompt(leg, "review", "nonce", "candidate-v1").accepted)
            raw = adapter.wait_for_result(leg, 20.0)
            self.assertEqual("provider_error", raw.state)
            self.assertIn("decreased", raw.detail)
            self.assertFalse(any(command[:3] == ("herdr", "agent", "read") for command in runner.operations))
            self.assertFalse(any(
                command[:3] == ("herdr", "agent", "send-keys")
                for command in runner.operations
            ))

    def test_agent_tab_id_accepts_only_nonempty_supported_envelope_binding(self):
        supported = (
            ({"agent": {"tab_id": "tab-a"}}, "tab-a"),
            ({"result": {"agent": {"tab_id": "tab-b"}}}, "tab-b"),
        )
        for payload, expected in supported:
            with self.subTest(payload=payload):
                self.assertEqual(
                    expected,
                    HerdrReviewAdapter._agent_tab_id(
                        CommandResult(0, json.dumps(payload))
                    ),
                )
        malformed = (
            {"agent": {}},
            {"result": {"agent": {"tab_id": None}}},
            {"result": {"agent": {"tab_id": 7}}},
            {"result": {"agent": {"tab_id": ""}}},
            {"result": {"agent": {"tab_id": "   "}}},
            {"data": {"agent": {"tab_id": "tab-a"}}},
        )
        for payload in malformed:
            with self.subTest(payload=payload):
                self.assertIsNone(
                    HerdrReviewAdapter._agent_tab_id(
                        CommandResult(0, json.dumps(payload))
                    )
                )

    def test_workspace_tab_ids_accepts_only_supported_direct_and_result_envelopes(self):
        supported = (
            ({"tabs": ["tab-a", {"tab_id": "tab-b"}, {"id": "tab-c"}]}, {"tab-a", "tab-b", "tab-c"}),
            (
                {"id": "tab-list", "result": {"tabs": [{"id": "tab-a"}, "tab-b"]}},
                {"tab-a", "tab-b"},
            ),
        )
        for payload, expected in supported:
            with self.subTest(payload=payload):
                response = CommandResult(0, json.dumps(payload))
                self.assertEqual(expected, HerdrReviewAdapter._workspace_tab_ids(response))

    def test_workspace_tab_ids_rejects_unrelated_nested_lists_and_other_envelopes(self):
        unsupported = (
            {"error": "failed", "details": []},
            {"meta": {"page_tokens": []}},
            {"result": {"details": []}},
            {"data": {"tabs": []}},
            [{"id": "tab-a"}],
        )
        for payload in unsupported:
            with self.subTest(payload=payload):
                response = CommandResult(0, json.dumps(payload))
                self.assertIsNone(HerdrReviewAdapter._workspace_tab_ids(response))

    def test_workspace_tab_ids_rejects_malformed_tab_entries(self):
        malformed = (
            {"tabs": [7]},
            {"tabs": [""]},
            {"tabs": ["   "]},
            {"tabs": [{}]},
            {"tabs": [{"id": 7}]},
            {"result": {"tabs": [{"tab_id": None}]}},
            {"tabs": "tab-a"},
            {"result": {"tabs": {"id": "tab-a"}}},
        )
        for payload in malformed:
            with self.subTest(payload=payload):
                response = CommandResult(0, json.dumps(payload))
                self.assertIsNone(HerdrReviewAdapter._workspace_tab_ids(response))

    def test_codex_only_request_uses_the_same_runnable_adapter(self):
        with TemporaryGitRepository() as repo, tempfile.TemporaryDirectory() as temp:
            request_path = write_run_request(Path(temp), repo, names=("codex",))
            result, record = run_request_file(request_path, runner=FakeHerdrRunner())
            self.assertEqual("CLEAN_FOR_PR", result.status)
            self.assertEqual(["codex"], list(record["legs"]))
            self.assertTrue(record["all_prompts_submitted_before_first_wait"])

    def test_complete_fingerprint_tracks_safe_untracked_content_and_all_git_slices(self):
        with TemporaryGitRepository() as repo:
            first, components = candidate_fingerprint(repo)
            self.assertEqual(40, len(components["head"]))
            (repo / "new.txt").write_text("one\n")
            second, _ = candidate_fingerprint(repo)
            (repo / "new.txt").write_text("two\n")
            third, _ = candidate_fingerprint(repo)
            self.assertNotEqual(first, second)
            self.assertNotEqual(second, third)

            (repo / "tracked.txt").write_text("unstaged\n")
            unstaged, _ = candidate_fingerprint(repo)
            subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True)
            staged, _ = candidate_fingerprint(repo)
            self.assertNotEqual(third, unstaged)
            self.assertNotEqual(unstaged, staged)

    def test_fingerprint_never_reads_or_hashes_ignored_env_or_secret_paths(self):
        with TemporaryGitRepository() as repo:
            (repo / ".gitignore").write_text("ignored/\n")
            (repo / "service-secret.txt").write_text("tracked-first")
            subprocess.run(["git", "add", ".gitignore", "service-secret.txt"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "ignore and tracked secret"], cwd=repo, check=True)
            (repo / "ignored").mkdir()
            (repo / "ignored" / "data.txt").write_text("first")
            (repo / ".env.local").write_text("PASSWORD=first")
            (repo / "api-token.txt").write_text("first")
            (repo / "credentials.json").write_text("first")
            (repo / "secrets").mkdir()
            (repo / "secrets" / "machine.json").write_text("first")
            before, components = candidate_fingerprint(repo)
            self.assertEqual([], components["untracked_manifest"])

            (repo / "ignored" / "data.txt").write_text("second")
            (repo / ".env.local").write_text("PASSWORD=second")
            (repo / "api-token.txt").write_text("second")
            (repo / "credentials.json").write_text("second")
            (repo / "secrets" / "machine.json").write_text("second")
            (repo / "service-secret.txt").write_text("tracked-second")
            unstaged, _ = candidate_fingerprint(repo)
            subprocess.run(["git", "add", "service-secret.txt"], cwd=repo, check=True)
            staged, _ = candidate_fingerprint(repo)
            self.assertEqual(before, unstaged)
            self.assertEqual(before, staged)

    def test_legitimate_source_names_containing_sensitive_words_affect_every_git_slice(self):
        source_paths = (
            "src/api-token.ts",
            "src/auth_token.rs",
            "src/tokens/jwt.ts",
            "credential-provider.rs",
            "session-token-manager.ts",
            "client_secret_loader.go",
            "src/credentials/client.ts",
            "src/secret-loader.py",
            "src/token_store.java",
        )
        with TemporaryGitRepository() as repo:
            for relative in source_paths:
                path = repo / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                before, _ = candidate_fingerprint(repo)
                path.write_text("version one\n")
                untracked, components = candidate_fingerprint(repo)
                self.assertNotEqual(before, untracked, relative)
                self.assertIn(relative, [item["path"] for item in components["untracked_manifest"]])

                subprocess.run(["git", "add", relative], cwd=repo, check=True)
                staged_new, _ = candidate_fingerprint(repo)
                self.assertNotEqual(untracked, staged_new, relative)
                subprocess.run(["git", "commit", "-qm", f"add {relative}"], cwd=repo, check=True)
                tracked, _ = candidate_fingerprint(repo)
                self.assertNotEqual(staged_new, tracked, relative)

                path.write_text("version two\n")
                unstaged, _ = candidate_fingerprint(repo)
                self.assertNotEqual(tracked, unstaged, relative)
                subprocess.run(["git", "add", relative], cwd=repo, check=True)
                staged_modified, _ = candidate_fingerprint(repo)
                self.assertNotEqual(unstaged, staged_modified, relative)
                subprocess.run(["git", "commit", "-qm", f"update {relative}"], cwd=repo, check=True)

    def test_concurrent_current_fingerprint_calls_never_overlap(self):
        with TemporaryGitRepository() as repo:
            leg = HerdrLeg(request("codex"), "codex-target", "tab-codex", "workspace-1")
            adapter = HerdrReviewAdapter(
                repo, {"codex": leg}, runner=SequenceHerdrRunner([("idle", 1)])
            )
            active = 0
            maximum = 0
            calls = 0
            counter_lock = threading.Lock()
            start_barrier = threading.Barrier(3)

            def fingerprint(worktree, runner):
                nonlocal active, maximum, calls
                with counter_lock:
                    active += 1
                    maximum = max(maximum, active)
                    calls += 1
                time.sleep(0.02)
                with counter_lock:
                    active -= 1
                return "candidate-v1", {}

            def compute():
                start_barrier.wait(timeout=1.0)
                return adapter.current_fingerprint()

            with mock.patch("scripts.review_orchestration.candidate_fingerprint", side_effect=fingerprint):
                threads = [threading.Thread(target=compute) for _ in range(2)]
                for thread in threads:
                    thread.start()
                start_barrier.wait(timeout=1.0)
                for thread in threads:
                    thread.join(timeout=1.0)
                    self.assertFalse(thread.is_alive())

            self.assertEqual(2, calls)
            self.assertEqual(1, maximum)

    def test_concurrent_leg_settlement_serializes_fingerprints_without_serializing_waits(self):
        with TemporaryGitRepository() as repo, tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            request_path = write_run_request(root, repo)
            runner = FakeHerdrRunner()
            runner.wait_barrier = threading.Barrier(2)

            result, record = run_request_file(request_path, runner=runner)

            self.assertEqual("CLEAN_FOR_PR", result.status)
            self.assertTrue(record["all_prompts_submitted_before_first_wait"])
            codex_interval = runner.wait_intervals["codex-target"]
            claude_interval = runner.wait_intervals["claude-target"]
            self.assertLess(
                max(codex_interval[0], claude_interval[0]),
                min(codex_interval[1], claude_interval[1]),
            )
            self.assertEqual(1, runner.max_active_git_commands)

    def test_parallel_success_stall_recovery_follows_both_dispatches_and_keeps_sibling_wait_concurrent(self):
        class YieldingClock:
            def __init__(self):
                self.now = 0.0
                self.lock = threading.Lock()

            def monotonic(self):
                with self.lock:
                    return self.now

            def sleep(self, seconds):
                with self.lock:
                    self.now += seconds
                time.sleep(0.001)

        with TemporaryGitRepository() as repo:
            runner = FakeHerdrRunner()
            runner.success_stall_target = "claude-target"
            clock = YieldingClock()
            requests = [
                LegRequest(
                    name=name,
                    prompt=f"review {name}",
                    narrowed_retry_prompt=f"narrow review {name}",
                    allowed_verdicts=VERDICTS,
                    timeout_seconds=20.0,
                )
                for name in ("codex", "claude")
            ]
            legs = {
                request.name: HerdrLeg(
                    request,
                    f"{request.name}-target",
                    f"tab-{request.name}",
                    "workspace-1",
                )
                for request in requests
            }
            adapter = HerdrReviewAdapter(
                repo,
                legs,
                runner=runner,
                clock=clock.monotonic,
                sleeper=clock.sleep,
                transition_poll_interval=1.0,
            )

            result = orchestrate_reviews(adapter, requests, clock=clock.monotonic)

            self.assertEqual("CLEAN_FOR_PR", result.status)
            self.assertTrue(result.all_prompts_submitted_before_first_wait)
            prompt_indices = [
                index for index, command in enumerate(runner.operations)
                if command[:3] == ("herdr", "agent", "prompt")
            ]
            visible_index = next(
                index for index, command in enumerate(runner.operations)
                if command[:3] == ("herdr", "agent", "read")
                and command[3] == "claude-target"
                and command[5] == "visible"
            )
            sibling_wait_index = next(
                index for index, command in enumerate(runner.operations)
                if command[:3] == ("herdr", "agent", "wait")
                and command[3] == "codex-target"
            )
            enter_indices = [
                index for index, command in enumerate(runner.operations)
                if command[:3] == ("herdr", "agent", "send-keys")
            ]
            self.assertEqual(2, len(prompt_indices))
            self.assertLess(max(prompt_indices), visible_index)
            self.assertLess(sibling_wait_index, visible_index)
            self.assertEqual(1, len(enter_indices))
            codex_interval = runner.wait_intervals["codex-target"]
            claude_interval = runner.wait_intervals["claude-target"]
            self.assertLess(
                max(codex_interval[0], claude_interval[0]),
                min(codex_interval[1], claude_interval[1]),
            )

    def test_run_request_orders_prompts_before_concurrent_waits_and_proves_stall(self):
        with TemporaryGitRepository() as repo, tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            request_path = write_run_request(root, repo)
            runner = FakeHerdrRunner()
            runner.stall_target = "codex-target"
            result, record = run_request_file(request_path, runner=runner)

            self.assertEqual("CLEAN_FOR_PR", result.status)
            self.assertTrue(record["all_prompts_submitted_before_first_wait"])
            kinds = [(item[1], item[2]) for item in runner.operations if item[:3] in {
                ("herdr", "agent", "prompt"), ("herdr", "agent", "wait")
            }]
            first_wait = next(index for index, command in enumerate(kinds) if command[1] == "wait")
            self.assertEqual(["prompt", "prompt"], [command[1] for command in kinds[:first_wait]])
            codex_interval = runner.wait_intervals["codex-target"]
            claude_interval = runner.wait_intervals["claude-target"]
            self.assertLess(max(codex_interval[0], claude_interval[0]), min(codex_interval[1], claude_interval[1]))
            self.assertIn(("herdr", "agent", "send-keys", "codex-target", "Enter"), runner.operations)
            self.assertNotIn(("herdr", "agent", "send-keys", "claude-target", "Enter"), runner.operations)
            self.assertIn("prompt_stall_proven", [event["kind"] for event in record["events"]])
            json.dumps(record)

    def test_plan_review_aggregates_and_cleans_up_with_plan_verdicts(self):
        with TemporaryGitRepository() as repo, tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runner = FakeHerdrRunner()
            runner.verdicts = {
                "codex-target": "PLAN_EXECUTION_READY",
                "claude-target": "PLAN_EXECUTION_READY",
            }
            request_path = write_run_request(root, repo, verdicts=PLAN_VERDICTS)

            result, record = run_request_file(request_path, runner=runner)

            self.assertEqual("PLAN_EXECUTION_READY", result.status)
            self.assertTrue(result.clean)
            self.assertEqual(
                {"pass"},
                {leg["verdict_class"] for leg in record["legs"].values()},
            )
            receipt = root / "receipt.json"
            receipt.write_text(json.dumps(record))
            cleanup = cleanup_request_file(request_path, receipt, True, runner=runner)
            self.assertTrue(cleanup["cleanup_complete"])
            self.assertEqual({"tab-codex", "tab-claude"}, runner.closed_tabs)

    def test_structured_result_outside_worktree_preserves_fingerprint_and_cleanup(self):
        with TemporaryGitRepository() as repo, tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runner = FakeHerdrRunner()
            runner.structured_results = {
                "codex-target": {"verdict": "CLEAN_FOR_PR", "body": "codex sidecar"},
                "claude-target": {"verdict": "CLEAN_FOR_PR", "body": "claude sidecar"},
            }
            runner.transcript_overrides = {
                "codex-target": "broken transcript\n",
                "claude-target": "broken transcript\n",
            }
            request_path = write_run_request(root, repo)
            result, record = run_request_file(request_path, runner=runner)

            self.assertTrue(result.clean)
            self.assertEqual("CLEAN_FOR_PR", result.status)
            for leg in record["legs"].values():
                self.assertEqual("structured", leg["result_evidence_source"])
                self.assertTrue(leg["result_evidence_path"])
                self.assertNotIn(str(repo), leg["result_evidence_path"])

            receipt = root / "receipt.json"
            receipt.write_text(json.dumps(record))
            cleanup = cleanup_request_file(request_path, receipt, True, runner=runner)
            self.assertTrue(cleanup["cleanup_complete"])
            self.assertEqual({"tab-codex", "tab-claude"}, runner.closed_tabs)

    def test_structured_cleanup_rejects_tampered_sidecar(self):
        with TemporaryGitRepository() as repo, tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runner = FakeHerdrRunner()
            runner.structured_results = {
                "codex-target": {"verdict": "CLEAN_FOR_PR", "body": "codex sidecar"},
                "claude-target": {"verdict": "CLEAN_FOR_PR", "body": "claude sidecar"},
            }
            runner.transcript_overrides = {
                "codex-target": "broken transcript\n",
                "claude-target": "broken transcript\n",
            }
            request_path = write_run_request(root, repo)
            _, record = run_request_file(request_path, runner=runner)
            Path(record["legs"]["codex"]["result_evidence_path"]).write_text(
                json.dumps({
                    "nonce": record["legs"]["codex"]["result_nonce"],
                    "verdict": "CLEAN_FOR_PR",
                    "body": "tampered body",
                })
            )
            receipt = root / "receipt.json"
            receipt.write_text(json.dumps(record))
            cleanup = cleanup_request_file(request_path, receipt, True, runner=runner)
            self.assertFalse(cleanup["cleanup_complete"])
            self.assertEqual(set(), runner.closed_tabs)

    def test_non_transport_untracked_mutation_remains_stale(self):
        with TemporaryGitRepository() as repo, tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runner = FakeHerdrRunner()
            runner.worktree_mutation_path = repo / "candidate-change.txt"
            request_path = write_run_request(root, repo)
            result, _ = run_request_file(request_path, runner=runner)
            self.assertFalse(result.clean)
            self.assertEqual(
                {"stale_fingerprint"},
                {leg.failure_kind for leg in result.legs.values()},
            )

    def test_cleanup_requires_explicit_artifact_confirmation_and_clean_receipt(self):
        with TemporaryGitRepository() as repo, tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runner = FakeHerdrRunner()
            request_path = write_run_request(root, repo)
            result, record = run_request_file(request_path, runner=runner)
            self.assertTrue(result.clean)
            self.assertEqual(set(), runner.closed_tabs)
            receipt = root / "receipt.json"
            receipt.write_text(json.dumps(record))
            self.assertEqual(str(repo.resolve()), record["request_identity"]["worktree"])
            self.assertEqual(
                {"codex-target", "claude-target"},
                {leg["target"] for leg in record["request_identity"]["legs"]},
            )
            self.assertEqual(
                {"tab-codex", "tab-claude"},
                {leg["tab_id"] for leg in record["request_identity"]["legs"]},
            )

            with self.assertRaisesRegex(ValueError, "artifact-written"):
                cleanup_request_file(request_path, receipt, False, runner=runner)
            self.assertEqual(set(), runner.closed_tabs)

            for prompt_file in root.glob("*.txt"):
                prompt_file.unlink()
            cleanup = cleanup_request_file(request_path, receipt, True, runner=runner)
            self.assertTrue(cleanup["cleanup_complete"])
            self.assertEqual({"tab-codex", "tab-claude"}, runner.closed_tabs)

    def test_cleanup_ignores_dynamic_transcript_material_outside_accepted_blocks(self):
        with TemporaryGitRepository() as repo, tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runner = FakeHerdrRunner()
            request_path = write_run_request(root, repo)
            _, record = run_request_file(request_path, runner=runner)
            receipt = root / "receipt.json"
            receipt.write_text(json.dumps(record))

            for target in ("codex-target", "claude-target"):
                original = runner.prompts[target] + "\n" + bounded(
                    runner.nonces[target], "CLEAN_FOR_PR"
                )
                runner.transcript_overrides[target] = (
                    "new dynamic preamble\n" + original + "new dynamic footer\n"
                )

            cleanup = cleanup_request_file(request_path, receipt, True, runner=runner)
            self.assertTrue(cleanup["cleanup_complete"])
            self.assertEqual({"tab-codex", "tab-claude"}, runner.closed_tabs)

    def test_cleanup_blocks_raw_block_changes_and_invalid_nonce_boundaries(self):
        cases = {
            "content": lambda nonce: bounded(nonce, "CLEAN_FOR_PR").replace(
                "Scope checked", "Scope changed"
            ),
            "prefix": lambda nonce: "".join(
                "• " + line for line in bounded(nonce, "CLEAN_FOR_PR").splitlines(keepends=True)
            ),
            "line-ending": lambda nonce: bounded(nonce, "CLEAN_FOR_PR").replace("\n", "\r\n"),
            "missing": lambda nonce: "no result block\n",
            "truncated-fence": lambda nonce: (
                f"BEGIN_REVIEW_RESULT {nonce[:8]}\n"
                # Intentionally drop the remainder and end marker.
                "Scope checked\nVERDICT: CLEAN_FOR_PR\n"
            ),
            "wrong-nonce": lambda nonce: bounded("other-nonce", "CLEAN_FOR_PR"),
            "reversed": lambda nonce: (
                f"END_REVIEW_RESULT {nonce}\n"
                "Scope checked\n"
                "VERDICT: CLEAN_FOR_PR\n"
                f"BEGIN_REVIEW_RESULT {nonce}\n"
            ),
        }
        for name, changed_block in cases.items():
            with self.subTest(name=name), TemporaryGitRepository() as repo, tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                runner = FakeHerdrRunner()
                request_path = write_run_request(root, repo)
                _, record = run_request_file(request_path, runner=runner)
                receipt = root / "receipt.json"
                receipt.write_text(json.dumps(record))
                nonce = runner.nonces["codex-target"]
                runner.transcript_overrides["codex-target"] = changed_block(nonce)

                cleanup = cleanup_request_file(request_path, receipt, True, runner=runner)
                self.assertFalse(cleanup["cleanup_complete"])
                self.assertEqual(set(), runner.closed_tabs)
                checked_targets = {
                    command[3]
                    for command in runner.operations
                    if command[:3] == ("herdr", "agent", "read")
                    and command[5] == "recent-unwrapped"
                }
                self.assertEqual({"codex-target", "claude-target"}, checked_targets)
                self.assertFalse(any(
                    command[:3] == ("herdr", "tab", "close")
                    for command in runner.operations
                ))

    def test_cleanup_missing_or_tampered_nonce_digest_fails_before_close(self):
        cases = (
            ("missing-nonce", "result_nonce", None),
            ("missing-digest", "result_digest", None),
            ("tampered-nonce", "result_nonce", "different-nonce"),
            ("tampered-digest", "result_digest", "0" * 64),
        )
        for name, field, value in cases:
            with self.subTest(name=name), TemporaryGitRepository() as repo, tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                runner = FakeHerdrRunner()
                request_path = write_run_request(root, repo)
                _, record = run_request_file(request_path, runner=runner)
                tampered = json.loads(json.dumps(record))
                if value is None:
                    tampered["legs"]["codex"].pop(field)
                else:
                    tampered["legs"]["codex"][field] = value
                receipt = root / "receipt.json"
                receipt.write_text(json.dumps(tampered))

                if value is None:
                    with self.assertRaisesRegex(
                        ValueError, "clean verdict for every requested reviewer"
                    ):
                        cleanup_request_file(request_path, receipt, True, runner=runner)
                else:
                    cleanup = cleanup_request_file(
                        request_path, receipt, True, runner=runner
                    )
                    self.assertFalse(cleanup["cleanup_complete"])
                self.assertEqual(set(), runner.closed_tabs)
                self.assertFalse(any(
                    command[:3] == ("herdr", "tab", "close")
                    for command in runner.operations
                ))

    def test_cleanup_requires_exact_target_to_recorded_tab_binding_before_any_close(self):
        cases = (
            ("mismatch", "tab-other"),
            ("missing", None),
            ("malformed", 7),
        )
        for name, tab_id in cases:
            with self.subTest(name=name), TemporaryGitRepository() as repo, tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                runner = FakeHerdrRunner()
                request_path = write_run_request(root, repo)
                _, record = run_request_file(request_path, runner=runner)
                receipt = root / "receipt.json"
                receipt.write_text(json.dumps(record))
                runner.tab_ids["codex-target"] = tab_id

                cleanup = cleanup_request_file(request_path, receipt, True, runner=runner)

                self.assertFalse(cleanup["cleanup_complete"])
                self.assertEqual(set(), runner.closed_tabs)
                self.assertFalse(any(
                    command[:3] == ("herdr", "tab", "close")
                    for command in runner.operations
                ))

    def test_cleanup_succeeds_with_exact_target_tab_and_workspace_binding(self):
        with TemporaryGitRepository() as repo, tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runner = FakeHerdrRunner()
            request_path = write_run_request(root, repo)
            _, record = run_request_file(request_path, runner=runner)
            receipt = root / "receipt.json"
            receipt.write_text(json.dumps(record))

            cleanup = cleanup_request_file(request_path, receipt, True, runner=runner)

            self.assertTrue(cleanup["cleanup_complete"])
            self.assertEqual({"tab-codex", "tab-claude"}, runner.closed_tabs)

    def test_cleanup_validates_exact_workspace_membership_for_all_legs_before_any_close(self):
        with TemporaryGitRepository() as repo, tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runner = FakeHerdrRunner()
            request_path = write_run_request(root, repo)
            _, record = run_request_file(request_path, runner=runner)
            receipt = root / "receipt.json"
            receipt.write_text(json.dumps(record))

            runner.listed_tabs_override = ("tab-codex", "tab-claude-extra")
            cleanup = cleanup_request_file(request_path, receipt, True, runner=runner)
            self.assertFalse(cleanup["cleanup_complete"])
            self.assertEqual(set(), runner.closed_tabs)
            list_commands = [
                command for command in runner.operations
                if command[:3] == ("herdr", "tab", "list")
            ]
            self.assertGreaterEqual(len(list_commands), 2)
            self.assertTrue(all(command[-2:] == ("--workspace", "workspace-1") for command in list_commands))
            self.assertFalse(any(command[:3] == ("herdr", "tab", "close") for command in runner.operations))

    def test_cleanup_cannot_succeed_from_unrelated_nested_lists(self):
        unsupported = (
            {"error": "failed", "details": []},
            {"meta": {"page_tokens": []}},
            {"result": {"details": ["tab-codex", "tab-claude"]}},
        )
        for payload in unsupported:
            with self.subTest(payload=payload), TemporaryGitRepository() as repo, tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                runner = FakeHerdrRunner()
                request_path = write_run_request(root, repo)
                _, record = run_request_file(request_path, runner=runner)
                receipt = root / "receipt.json"
                receipt.write_text(json.dumps(record))
                runner.listed_tabs_payload = payload

                cleanup = cleanup_request_file(request_path, receipt, True, runner=runner)

                self.assertFalse(cleanup["cleanup_complete"])
                self.assertEqual(set(), runner.closed_tabs)
                self.assertFalse(any(
                    command[:3] == ("herdr", "tab", "close")
                    for command in runner.operations
                ))

    def test_cleanup_refuses_old_receipt_after_tab_reuse_without_closing_any_tab(self):
        with TemporaryGitRepository() as repo, tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runner = FakeHerdrRunner()
            request_path = write_run_request(root, repo)
            _, record = run_request_file(request_path, runner=runner)
            receipt = root / "receipt.json"
            receipt.write_text(json.dumps(record))

            runner.states["codex-target"] = "working"
            cleanup = cleanup_request_file(request_path, receipt, True, runner=runner)
            self.assertFalse(cleanup["cleanup_complete"])
            self.assertEqual(set(), runner.closed_tabs)

            runner.states["codex-target"] = "idle"
            runner.transcript_overrides["codex-target"] = "completed later review cycle"
            cleanup = cleanup_request_file(request_path, receipt, True, runner=runner)
            self.assertFalse(cleanup["cleanup_complete"])
            self.assertEqual(set(), runner.closed_tabs)

    def test_cleanup_rejects_request_or_receipt_binding_mismatches_before_closing_tabs(self):
        with TemporaryGitRepository() as repo, tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runner = FakeHerdrRunner()
            request_path = write_run_request(root, repo)
            _, record = run_request_file(request_path, runner=runner)
            receipt = root / "receipt.json"
            receipt.write_text(json.dumps(record))

            changed_request = json.loads(request_path.read_text())
            changed_request["reviewers"][0]["tab_id"] = "tab-from-other-request"
            request_path.write_text(json.dumps(changed_request))
            with self.assertRaisesRegex(ValueError, "exact review request identity"):
                cleanup_request_file(request_path, receipt, True, runner=runner)
            self.assertEqual(set(), runner.closed_tabs)

            request_path = write_run_request(root, repo)
            tampered = json.loads(receipt.read_text())
            tampered["request_identity"]["legs"][0]["target"] = "other-target"
            receipt.write_text(json.dumps(tampered))
            with self.assertRaisesRegex(ValueError, "exact review request identity"):
                cleanup_request_file(request_path, receipt, True, runner=runner)
            self.assertEqual(set(), runner.closed_tabs)

    def test_cleanup_rejects_non_clean_or_incomplete_per_leg_receipt(self):
        with TemporaryGitRepository() as repo, tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runner = FakeHerdrRunner()
            request_path = write_run_request(root, repo)
            _, record = run_request_file(request_path, runner=runner)
            receipt = root / "receipt.json"

            for field, value in (("verdict", "FINDINGS_TO_RESOLVE"), ("validation_complete", False)):
                tampered = json.loads(json.dumps(record))
                tampered["legs"]["codex"][field] = value
                receipt.write_text(json.dumps(tampered))
                with self.assertRaisesRegex(ValueError, "clean verdict for every requested reviewer"):
                    cleanup_request_file(request_path, receipt, True, runner=runner)
                self.assertEqual(set(), runner.closed_tabs)

    def test_main_emits_compact_json_and_writes_output(self):
        fake_result = OrchestrationResult(
            status="CLEAN_FOR_PR",
            fingerprint="abc",
            legs={},
            events=[],
            candidate_wall_time=0.1,
            all_prompts_submitted_before_first_wait=True,
            mode="parallel",
            clean=True,
        )
        record = result_record(fake_result)
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "result.json"
            stdout = io.StringIO()
            with mock.patch("scripts.review_orchestration.run_request_file", return_value=(fake_result, record)):
                with contextlib.redirect_stdout(stdout):
                    code = main(["run", "--request", "request.json", "--output", str(output)])
            self.assertEqual(0, code)
            self.assertEqual(record, json.loads(stdout.getvalue()))
            self.assertEqual(record, json.loads(output.read_text()))
            self.assertNotIn("\n  ", stdout.getvalue())


class BenchmarkFixtureTests(unittest.TestCase):
    fixture = Path(__file__).parent / "fixtures" / "heddle-dual-review"

    def copied_fixture(self, root):
        target = Path(root) / "fixture"
        shutil.copytree(self.fixture, target)
        return target

    def test_fixture_prompt_contains_bounded_coverage_and_verification_evidence(self):
        manifest = load_fixture(self.fixture)
        prompt = fixture_prompt(manifest, "codex")
        self.assertIn("src/app/services/session-context.ts", prompt)
        self.assertIn("contract parity", prompt)
        self.assertIn("npm test -- session-context: PASS", prompt)
        self.assertIn("untracked_manifest_sha256", prompt)
        self.assertIn("Do not execute tests", prompt)

    def test_fixture_rejects_missing_changed_file_coverage(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = self.copied_fixture(temp)
            verification = json.loads((fixture / "verification.json").read_text())
            verification["changed_files_covered"].pop()
            (fixture / "verification.json").write_text(json.dumps(verification))
            with self.assertRaisesRegex(SystemExit, "changed-file coverage"):
                load_fixture(fixture)

    def test_fixture_rejects_patch_manifest_changed_file_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = self.copied_fixture(temp)
            patch = (fixture / "candidate.patch").read_text().replace(
                "src-tauri/src/session_bridge.rs", "src-tauri/src/other_bridge.rs"
            )
            (fixture / "candidate.patch").write_text(patch)
            with self.assertRaisesRegex(SystemExit, "changed-file coverage"):
                load_fixture(fixture)

    def test_fixture_rejects_mismatched_failure_family_assignments(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = self.copied_fixture(temp)
            verification = json.loads((fixture / "verification.json").read_text())
            verification["failure_family_assignments"]["codex"].remove("contract parity")
            verification["failure_family_assignments"]["claude"].remove("contract parity")
            (fixture / "verification.json").write_text(json.dumps(verification))
            with self.assertRaisesRegex(SystemExit, "failure-family coverage"):
                load_fixture(fixture)

    def test_benchmark_reports_startup_not_applicable_and_cleanup_distribution(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "parallel.json"
            args = argparse.Namespace(
                fixture=str(self.fixture),
                mode="parallel",
                discard_warmup=0,
                samples=2,
                output=str(output),
            )

            self.assertEqual(0, run_benchmark(args))
            payload = json.loads(output.read_text())

            self.assertEqual("review-orchestration-benchmark-v2", payload["schema_version"])
            self.assertEqual("not_applicable", payload["startup"]["status"])
            self.assertIn("pre-created in-memory fixture reviewers", payload["startup"]["reason"])
            self.assertEqual(2, payload["complete_run_count"])
            self.assertEqual("complete", payload["coverage_status"])
            self.assertEqual(2, len(payload["cleanup"]["samples_seconds"]))
            self.assertEqual([True, True], payload["cleanup"]["per_run_success"])
            self.assertEqual(2, payload["cleanup"]["complete_run_count"])
            self.assertEqual(1.0, payload["cleanup"]["coverage"])
            self.assertEqual("complete", payload["cleanup"]["status"])
            for field in ("median_seconds", "p75_seconds", "p90_seconds"):
                self.assertGreaterEqual(payload["cleanup"][field], 0.0)

    def test_benchmark_run_fails_admission_when_cleanup_is_incomplete(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch(
            "scripts.benchmark_review_orchestration.cleanup_review_tabs",
            return_value=False,
        ):
            with self.assertRaisesRegex(SystemExit, "cleanup was incomplete"):
                run_benchmark(argparse.Namespace(
                    fixture=str(self.fixture),
                    mode="parallel",
                    discard_warmup=0,
                    samples=1,
                    output=str(Path(temp) / "parallel.json"),
                ))

    def test_benchmark_compare_rejects_incomplete_cleanup_admission(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            serial = root / "serial.json"
            parallel = root / "parallel.json"
            for mode, output in (("serial", serial), ("parallel", parallel)):
                self.assertEqual(0, run_benchmark(argparse.Namespace(
                    fixture=str(self.fixture),
                    mode=mode,
                    discard_warmup=0,
                    samples=1,
                    output=str(output),
                )))
            tampered = json.loads(parallel.read_text())
            tampered["cleanup"]["status"] = "incomplete"
            parallel.write_text(json.dumps(tampered))

            with self.assertRaisesRegex(SystemExit, "cleanup admission is incomplete"):
                compare(argparse.Namespace(
                    serial=str(serial),
                    parallel=str(parallel),
                    require_median_improvement=0.0,
                    require_coverage=1.0,
                ))

    def test_fixture_rejects_missing_or_mismatched_fingerprint_checks(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = self.copied_fixture(temp)
            verification = json.loads((fixture / "verification.json").read_text())
            verification["fingerprint_checks"]["components"].pop()
            (fixture / "verification.json").write_text(json.dumps(verification))
            with self.assertRaisesRegex(SystemExit, "fingerprint checks"):
                load_fixture(fixture)

        with tempfile.TemporaryDirectory() as temp:
            fixture = self.copied_fixture(temp)
            verification = json.loads((fixture / "verification.json").read_text())
            verification["fingerprint_checks"]["candidate_fingerprint"] = "sha256:tampered"
            (fixture / "verification.json").write_text(json.dumps(verification))
            with self.assertRaisesRegex(SystemExit, "candidate fingerprint"):
                load_fixture(fixture)


if __name__ == "__main__":
    unittest.main()
