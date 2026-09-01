#!/usr/bin/env python3
"""Run the synthesized Oracle proactive-trigger scenario under Pi print mode.

The operator prompt never mentions Oracle. Success requires:
1. at least one Agent call with subagent_type=oracle
2. correct launch contract (no inherit_context=false, no isolation=worktree,
   no model/thinking override away from Sol high)
3. packet contains a narrow '?' question
4. session records an accept/reject/escalate disposition
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "scripts/fixtures/oracle-proactive-trigger"
ANALYZE = ROOT / "scripts/analyze_oracle_session.py"
PROBE = ROOT / "scripts/probe_pi_oracle_transport.py"


def run(cmd, **kwargs):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run(cmd, text=True, **kwargs)


def prepare_work(work: Path) -> None:
    if work.exists():
        shutil.rmtree(work)
    shutil.copytree(FIXTURE, work)
    # Drop docs that are not part of the agent-facing tree prompt surface.
    for name in ("README.md",):
        p = work / name
        if p.exists():
            p.unlink()
    run(["git", "init"], cwd=work, check=True, capture_output=True)
    run(["git", "add", "-A"], cwd=work, check=True, capture_output=True)
    run(
        ["git", "-c", "user.email=oracle-e2e@example.com", "-c", "user.name=oracle-e2e", "commit", "-m", "fixture"],
        cwd=work,
        check=True,
        capture_output=True,
    )


def latest_session(session_dir: Path, since: float) -> Path | None:
    candidates = []
    for path in session_dir.rglob("*.jsonl"):
        try:
            st = path.stat()
        except FileNotFoundError:
            continue
        if st.st_mtime >= since - 1:
            candidates.append((st.st_mtime, path))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, help="Optional persistent work dir")
    parser.add_argument("--session-dir", type=Path, help="Optional Pi session dir")
    parser.add_argument("--model", default="openai-codex/gpt-5.6-terra")
    parser.add_argument("--thinking", default="medium")
    parser.add_argument("--timeout-sec", type=int, default=900)
    parser.add_argument("--skip-live", action="store_true", help="Only run transport probe + dry checks")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    probe = run(
        [sys.executable, str(PROBE), "--agent-source-dir", str(ROOT / "_pi/agents"), "--json"],
        cwd=ROOT,
        capture_output=True,
    )
    probe_payload = {}
    try:
        probe_payload = json.loads(probe.stdout or "{}")
    except json.JSONDecodeError:
        probe_payload = {"status": "fail", "reason": probe.stdout or probe.stderr}
    if probe.returncode != 0 or probe_payload.get("status") != "pass":
        # Fall back to installed agent dir if source-only lacks transport package.
        probe2 = run([sys.executable, str(PROBE), "--json"], cwd=ROOT, capture_output=True)
        try:
            probe_payload = json.loads(probe2.stdout or "{}")
        except json.JSONDecodeError:
            probe_payload = {"status": "fail", "reason": probe2.stdout or probe2.stderr}
        if probe2.returncode != 0:
            out = {
                "status": "fail",
                "stage": "probe",
                "probe": probe_payload,
                "stderr": (probe.stderr or "") + (probe2.stderr or ""),
            }
            print(json.dumps(out, indent=2) if args.json else out)
            return 1

    if args.skip_live:
        payload = {
            "status": "pass",
            "stage": "probe-only",
            "probe": probe_payload,
            "note": "Live Pi run skipped (--skip-live).",
        }
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0

    tmp_root = Path(tempfile.mkdtemp(prefix="oracle-proactive-e2e-"))
    work = args.work_dir or (tmp_root / "work")
    session_dir = args.session_dir or (tmp_root / "sessions")
    session_dir.mkdir(parents=True, exist_ok=True)
    prepare_work(work)

    prompt = (FIXTURE / "OPERATOR_PROMPT.md").read_text(encoding="utf-8")
    # Explicitly forbid naming Oracle in the operator text already; reinforce
    # autonomy without mentioning the subagent.
    append_bits = [
        "Project-local AGENTS.md in the checkout is authoritative for this fixture.",
        "Host Pi agents from the installed agent directory are available.",
    ]

    env = os.environ.copy()
    env["PI_SKIP_VERSION_CHECK"] = "1"
    started = time.time()
    cmd = [
        "pi",
        "--print",
        "--mode",
        "json",
        "--approve",
        "--session-dir",
        str(session_dir),
        "--provider",
        "openai-codex",
        "--model",
        args.model,
        "--thinking",
        args.thinking,
        "--append-system-prompt",
        append_bits[0],
        "--append-system-prompt",
        append_bits[1],
        "--skill",
        str(ROOT / "skills/oracle-consultation"),
        # Keep tools needed for Agent + inspection; avoid unrelated extensions noise.
        prompt,
    ]
    result = run(
        cmd,
        cwd=work,
        env=env,
        capture_output=True,
        timeout=args.timeout_sec,
    )
    session = latest_session(session_dir, started)
    analysis = None
    if session and session.is_file():
        analyzed = run(
            [sys.executable, str(ANALYZE), str(session), "--json"],
            cwd=ROOT,
            capture_output=True,
        )
        try:
            analysis = json.loads(analyzed.stdout or "{}")
        except json.JSONDecodeError:
            analysis = {
                "status": "fail",
                "errors": ["analyzer returned non-JSON"],
                "raw": analyzed.stdout,
                "stderr": analyzed.stderr,
            }
    else:
        analysis = {"status": "fail", "errors": ["no session jsonl produced"], "oracleCallCount": 0}

    disposition_path = work / "thoughts/decisions/cleanup-ownership-disposition.md"
    oracle_ran = False
    if session and session.is_file():
        blob = session.read_text(encoding="utf-8", errors="replace")
        # A successful Oracle spawn produces advisory response sections, not only a
        # rejected/stripped launch attempt.
        has_call = '"subagent_type": "oracle"' in blob or '"subagent_type":"oracle"' in blob
        has_response = any(
            marker in blob
            for marker in (
                "Inherited decisions",
                "**Recommendation**",
                "### Recommendation",
                "## Recommendation",
                "Oracle recommendation",
            )
        )
        rejected_only = (
            "Do not set isolation for oracle" in blob
            and not has_response
        )
        oracle_ran = bool(has_call and has_response and not rejected_only)

    payload = {
        "status": "pass"
        if (
            result.returncode == 0
            and analysis.get("status") == "pass"
            and disposition_path.is_file()
            and oracle_ran
        )
        else "fail",
        "stage": "live",
        "probe": probe_payload,
        "piReturncode": result.returncode,
        "session": str(session) if session else None,
        "analysis": analysis,
        "oracleActuallyRan": oracle_ran,
        "dispositionFile": str(disposition_path) if disposition_path.is_file() else None,
        "workDir": str(work),
        "sessionDir": str(session_dir),
        "stdoutTail": (result.stdout or "")[-4000:],
        "stderrTail": (result.stderr or "")[-2000:],
    }
    if not disposition_path.is_file():
        payload.setdefault("errors", []).append("missing disposition file after run")
        payload["status"] = "fail"
    if not oracle_ran:
        payload.setdefault("errors", []).append(
            "oracle Agent call did not produce a usable advisory response"
        )
        payload["status"] = "fail"
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("E2E oracle proactive trigger: %s" % payload["status"])
        print("session=%s" % payload.get("session"))
        print("analysis=%s oracle_calls=%s" % (
            (analysis or {}).get("status"),
            (analysis or {}).get("oracleCallCount"),
        ))
        for err in (analysis or {}).get("errors") or []:
            print("ERROR:", err)
        if payload["status"] != "pass":
            print("stderr tail:\n", payload.get("stderrTail") or "")
    # Keep tmp on failure for inspection when using default temp root.
    if payload["status"] == "pass" and args.work_dir is None:
        shutil.rmtree(tmp_root, ignore_errors=True)
    else:
        print("artifacts retained under", tmp_root if args.work_dir is None else work)
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.TimeoutExpired as exc:
        print("E2E timed out:", exc, file=sys.stderr)
        raise SystemExit(2)
