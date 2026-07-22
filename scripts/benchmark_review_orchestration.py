#!/usr/bin/env python3
"""Deterministic serial/parallel benchmark for review orchestration P1."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import statistics
import sys
import threading
import time
from pathlib import Path
from typing import Dict, List

# Permit direct execution from scripts/ without installing a package.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.review_orchestration import (  # noqa: E402
    LegRequest,
    PromptSubmission,
    RawReviewResult,
    cleanup_review_tabs,
    orchestrate_reviews,
)


ALLOWED_VERDICTS = (
    "FINDINGS_TO_RESOLVE",
    "CLEAN_FOR_PR",
    "BLOCKED_BY_QUESTION",
    "REVIEW_INCOMPLETE_RERUN_NEEDED",
)
REQUIRED_FINGERPRINT_CHECKS = (
    "head",
    "porcelain_sha256",
    "staged_diff_sha256",
    "unstaged_diff_sha256",
    "untracked_manifest_sha256",
)


class FixtureAdapter:
    def __init__(self, manifest: Dict[str, object]):
        self.manifest = manifest
        self.fingerprint = str(manifest["candidate_fingerprint"])
        self.reviewers = {
            str(item["name"]): item for item in manifest["reviewers"]  # type: ignore[index]
        }
        self.submissions: Dict[str, List[tuple]] = {}
        self._wait_counts: Dict[str, int] = {}
        self._lock = threading.Lock()

    def capture_fingerprint(self) -> str:
        return self.fingerprint

    def current_fingerprint(self) -> str:
        return self.fingerprint

    def prepare_leg(self, request: LegRequest, fingerprint: str):
        return request.name

    def submit_prompt(
        self, handle, prompt: str, nonce: str, fingerprint: str
    ) -> PromptSubmission:
        with self._lock:
            self.submissions.setdefault(handle, []).append((prompt, nonce, fingerprint))
        return PromptSubmission(accepted=True)

    def send_enter(self, handle) -> bool:
        return False

    def prompt_accepted(self, handle) -> bool:
        return False

    def wait_for_result(self, handle, timeout_seconds: float) -> RawReviewResult:
        with self._lock:
            attempt = self._wait_counts.get(handle, 0)
            self._wait_counts[handle] = attempt + 1
            _, nonce, fingerprint = self.submissions[handle][attempt]
        reviewer = self.reviewers[handle]
        time.sleep(float(reviewer["delay_seconds"]))
        verdict = str(reviewer["verdict"])
        output = (
            "BEGIN_REVIEW_RESULT {0}\n"
            "1. Scope checked\n"
            "2. Coverage complete\n"
            "VERDICT: {1}\n"
            "END_REVIEW_RESULT {0}\n"
        ).format(nonce, verdict)
        return RawReviewResult(
            state="settled",
            output=output,
            candidate_fingerprint=fingerprint,
            first_action_observed=True,
        )

    def cleanup_leg_is_current(
        self, handle, result_nonce: str, result_digest: str
    ) -> bool:
        return bool(result_nonce and result_digest)

    def cleanup_leg(self, handle) -> bool:
        return True


def fixture_hash(fixture: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted((p for p in fixture.rglob("*") if p.is_file()), key=lambda p: p.as_posix()):
        relative = path.relative_to(fixture).as_posix().encode("utf-8")
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def percentile(samples: List[float], fraction: float) -> float:
    ordered = sorted(samples)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _string_list(value: object, label: str) -> List[str]:
    if not isinstance(value, list) or not value or any(not isinstance(item, str) for item in value):
        raise SystemExit("{} must be a non-empty string list".format(label))
    return [str(item) for item in value]


def _patch_changed_files(patch: str) -> List[str]:
    changed: List[str] = []
    for line in patch.splitlines():
        match = re.match(r"^diff --git a/(.+) b/(.+)$", line)
        if match:
            old_path, new_path = match.groups()
            if old_path != new_path:
                raise SystemExit("benchmark patch renames are not supported: {} -> {}".format(old_path, new_path))
            changed.append(new_path)
    if not changed or len(changed) != len(set(changed)):
        raise SystemExit("candidate.patch must contain unique changed-file entries")
    return changed


def load_fixture(path: Path) -> Dict[str, object]:
    manifest_path = path / "manifest.json"
    patch_path = path / "candidate.patch"
    verification_path = path / "verification.json"
    for required in (manifest_path, patch_path, verification_path):
        if not required.is_file():
            raise SystemExit("fixture is missing {}: {}".format(required.name, path))

    manifest = json.loads(manifest_path.read_text())
    verification = json.loads(verification_path.read_text())
    if not isinstance(manifest, dict) or not isinstance(verification, dict):
        raise SystemExit("benchmark manifest and verification contract must be JSON objects")
    reviewers = manifest.get("reviewers")
    if not isinstance(reviewers, list) or len(reviewers) != 2:
        raise SystemExit("benchmark fixture must define exactly two reviewers")
    reviewer_names = [str(item.get("name")) for item in reviewers if isinstance(item, dict)]
    if len(reviewer_names) != 2 or len(set(reviewer_names)) != 2:
        raise SystemExit("benchmark fixture reviewer names must be unique")

    manifest_files = _string_list(manifest.get("changed_files"), "manifest.changed_files")
    patch_files = _patch_changed_files(patch_path.read_text())
    covered_files = _string_list(
        verification.get("changed_files_covered"), "verification.changed_files_covered"
    )
    if set(patch_files) != set(manifest_files) or set(covered_files) != set(manifest_files):
        raise SystemExit("candidate patch and verification changed-file coverage must match manifest.changed_files")

    if verification.get("schema_version") != "review-verification-v1":
        raise SystemExit("verification contract must use review-verification-v1")
    if verification.get("reviewers_must_not_execute_verification") is not True:
        raise SystemExit("verification contract must preserve static read-only reviewer execution")
    mechanical_evidence = _string_list(
        verification.get("mechanical_evidence"), "verification.mechanical_evidence"
    )
    required_families = _string_list(
        verification.get("required_failure_families"),
        "verification.required_failure_families",
    )
    assignments = verification.get("failure_family_assignments")
    if not isinstance(assignments, dict) or set(assignments) != set(reviewer_names):
        raise SystemExit("failure-family assignments must bind every fixture reviewer exactly")
    assigned: set[str] = set()
    for name in reviewer_names:
        assigned.update(_string_list(assignments[name], "failure families for {}".format(name)))
    if assigned != set(required_families):
        raise SystemExit("assigned failure-family coverage must match required_failure_families")

    fingerprint = verification.get("fingerprint_checks")
    if not isinstance(fingerprint, dict):
        raise SystemExit("verification fingerprint_checks must be an object")
    checks = _string_list(fingerprint.get("components"), "fingerprint_checks.components")
    if set(checks) != set(REQUIRED_FINGERPRINT_CHECKS):
        raise SystemExit("required fingerprint checks are missing or mismatched")
    if fingerprint.get("candidate_fingerprint") != manifest.get("candidate_fingerprint"):
        raise SystemExit("verification candidate fingerprint does not match manifest")

    manifest["_fixture_contract"] = {
        "patch_changed_files": patch_files,
        "changed_files_covered": covered_files,
        "mechanical_evidence": mechanical_evidence,
        "required_failure_families": required_families,
        "failure_family_assignments": assignments,
        "fingerprint_checks": fingerprint,
    }
    return manifest


def fixture_prompt(manifest: Dict[str, object], reviewer_name: str, narrowed: bool = False) -> str:
    contract = manifest["_fixture_contract"]
    assert isinstance(contract, dict)
    assignments = contract["failure_family_assignments"]
    assert isinstance(assignments, dict)
    lines = [
        "Deterministic bounded fixture review{}".format(" retry" if narrowed else ""),
        "Packet version: {}".format(manifest["packet_version"]),
        "Candidate fingerprint: {}".format(manifest["candidate_fingerprint"]),
        "Changed files: {}".format(", ".join(contract["changed_files_covered"])),
        "Assigned failure families: {}".format(", ".join(assignments[reviewer_name])),
        "Mechanical evidence: {}".format("; ".join(contract["mechanical_evidence"])),
        "Required fingerprint checks: {}".format(", ".join(contract["fingerprint_checks"]["components"])),
        "Do not execute tests, builds, linters, benchmarks, or other verification commands.",
    ]
    return "\n".join(lines)


def run_benchmark(args: argparse.Namespace) -> int:
    fixture = Path(args.fixture).resolve()
    manifest = load_fixture(fixture)
    measured: List[float] = []
    cleanup_measured: List[float] = []
    cleanup_success: List[bool] = []
    accepted_results = 0
    applicable_results = 0
    complete_runs = 0
    runs = args.discard_warmup + args.samples

    for index in range(runs):
        adapter = FixtureAdapter(manifest)
        requests = [
            LegRequest(
                name=str(reviewer["name"]),
                prompt=fixture_prompt(manifest, str(reviewer["name"])),
                narrowed_retry_prompt=fixture_prompt(
                    manifest, str(reviewer["name"]), narrowed=True
                ),
                allowed_verdicts=ALLOWED_VERDICTS,
                timeout_seconds=5.0,
            )
            for reviewer in manifest["reviewers"]  # type: ignore[index]
        ]
        result = orchestrate_reviews(adapter, requests, mode=args.mode)
        cleanup_started = time.monotonic()
        cleaned = cleanup_review_tabs(adapter, result, artifact_written=True)
        cleanup_elapsed = time.monotonic() - cleanup_started
        if not cleaned or not result.cleanup_complete:
            raise SystemExit("fixture run cleanup was incomplete")
        if index >= args.discard_warmup:
            measured.append(result.candidate_wall_time)
            cleanup_measured.append(cleanup_elapsed)
            cleanup_success.append(cleaned)
            applicable_results += len(requests)
            accepted_results += sum(
                leg.validation_complete for leg in result.legs.values()
            )
            if result.status != "CLEAN_FOR_PR":
                raise SystemExit("fixture run failed closed: {}".format(result.status))
            if args.mode == "parallel" and not result.all_prompts_submitted_before_first_wait:
                raise SystemExit("parallel run did not submit every prompt before first wait")
            complete_runs += 1

    coverage = accepted_results / applicable_results if applicable_results else 0.0
    cleanup_coverage = sum(cleanup_success) / len(cleanup_success) if cleanup_success else 0.0
    payload = {
        "schema_version": "review-orchestration-benchmark-v2",
        "fixture": str(fixture),
        "fixture_sha256": fixture_hash(fixture),
        "fixture_version": manifest["fixture_version"],
        "candidate_fingerprint": manifest["candidate_fingerprint"],
        "packet_version": manifest["packet_version"],
        "reviewer_profiles": {
            str(item["name"]): item["profile"] for item in manifest["reviewers"]  # type: ignore[index]
        },
        "mode": args.mode,
        "caches_enabled": False,
        "discarded_warmup": args.discard_warmup,
        "sample_count": args.samples,
        "samples_seconds": measured,
        "median_seconds": statistics.median(measured),
        "p75_seconds": percentile(measured, 0.75),
        "p90_seconds": percentile(measured, 0.90),
        "accepted_results": accepted_results,
        "applicable_results": applicable_results,
        "coverage": coverage,
        "coverage_status": "complete" if coverage == 1.0 else "incomplete",
        "complete_run_count": complete_runs,
        "startup": {
            "status": "not_applicable",
            "reason": "pre-created in-memory fixture reviewers; no reviewer tab startup occurs",
        },
        "cleanup": {
            "samples_seconds": cleanup_measured,
            "median_seconds": statistics.median(cleanup_measured),
            "p75_seconds": percentile(cleanup_measured, 0.75),
            "p90_seconds": percentile(cleanup_measured, 0.90),
            "per_run_success": cleanup_success,
            "complete_run_count": sum(cleanup_success),
            "coverage": cleanup_coverage,
            "status": "complete" if cleanup_coverage == 1.0 else "incomplete",
        },
        "fixture_admission": {
            "changed_file_coverage": 1.0,
            "assigned_failure_family_coverage": 1.0,
            "required_fingerprint_check_coverage": 1.0,
        },
        "host": {
            "hostname": platform.node(),
            "platform": platform.platform(),
            "python": platform.python_version(),
            "pid": os.getpid(),
        },
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    output.write_text(rendered)
    print(
        "{} median={:.6f}s p75={:.6f}s p90={:.6f}s coverage={:.3f} output={}".format(
            args.mode,
            payload["median_seconds"],
            payload["p75_seconds"],
            payload["p90_seconds"],
            coverage,
            output,
        )
    )
    return 0


def compare(args: argparse.Namespace) -> int:
    serial = json.loads(Path(args.serial).read_text())
    parallel = json.loads(Path(args.parallel).read_text())
    identity_fields = (
        "schema_version",
        "fixture_sha256",
        "fixture_version",
        "candidate_fingerprint",
        "packet_version",
        "reviewer_profiles",
        "fixture_admission",
    )
    for field in identity_fields:
        if serial.get(field) != parallel.get(field):
            raise SystemExit("benchmark identity mismatch for {}".format(field))
    if serial.get("mode") != "serial" or parallel.get("mode") != "parallel":
        raise SystemExit("compare requires serial and parallel benchmark outputs")
    for label, payload in (("serial", serial), ("parallel", parallel)):
        startup = payload.get("startup")
        cleanup = payload.get("cleanup")
        if not isinstance(startup, dict) or startup.get("status") != "not_applicable":
            raise SystemExit("{} benchmark startup applicability is invalid".format(label))
        if (
            not isinstance(cleanup, dict)
            or cleanup.get("status") != "complete"
            or float(cleanup.get("coverage", 0.0)) != 1.0
            or int(cleanup.get("complete_run_count", -1)) != int(payload.get("sample_count", 0))
            or int(payload.get("complete_run_count", -1)) != int(payload.get("sample_count", 0))
        ):
            raise SystemExit("{} benchmark cleanup admission is incomplete".format(label))
    admission = serial.get("fixture_admission")
    if not isinstance(admission, dict) or any(
        float(admission.get(field, 0.0)) != 1.0
        for field in (
            "changed_file_coverage",
            "assigned_failure_family_coverage",
            "required_fingerprint_check_coverage",
        )
    ):
        raise SystemExit("benchmark fixture admission coverage is incomplete")

    serial_median = float(serial["median_seconds"])
    parallel_median = float(parallel["median_seconds"])
    if serial_median <= 0:
        raise SystemExit("serial median must be positive")
    improvement = (serial_median - parallel_median) / serial_median
    coverage = min(float(serial["coverage"]), float(parallel["coverage"]))
    print(
        "median_improvement={:.3%} coverage={:.3f} serial={:.6f}s parallel={:.6f}s".format(
            improvement, coverage, serial_median, parallel_median
        )
    )
    if improvement < args.require_median_improvement:
        raise SystemExit(
            "median improvement {:.3%} is below required {:.3%}".format(
                improvement, args.require_median_improvement
            )
        )
    if coverage < args.require_coverage:
        raise SystemExit(
            "coverage {:.3f} is below required {:.3f}".format(
                coverage, args.require_coverage
            )
        )
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    subparsers = root.add_subparsers(dest="command")
    comparison = subparsers.add_parser("compare")
    comparison.add_argument("--serial", required=True)
    comparison.add_argument("--parallel", required=True)
    comparison.add_argument("--require-median-improvement", type=float, required=True)
    comparison.add_argument("--require-coverage", type=float, required=True)

    root.add_argument("--fixture")
    root.add_argument("--mode", choices=("serial", "parallel"))
    root.add_argument("--discard-warmup", type=int, default=1)
    root.add_argument("--samples", type=int, default=5)
    root.add_argument("--output")
    return root


def main() -> int:
    args = parser().parse_args()
    if args.command == "compare":
        return compare(args)
    for name in ("fixture", "mode", "output"):
        if getattr(args, name) is None:
            raise SystemExit("--{} is required".format(name.replace("_", "-")))
    if args.samples < 1 or args.discard_warmup < 0:
        raise SystemExit("samples must be positive and discard-warmup non-negative")
    return run_benchmark(args)


if __name__ == "__main__":
    raise SystemExit(main())
