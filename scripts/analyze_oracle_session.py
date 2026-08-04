#!/usr/bin/env python3
"""Validate Oracle Agent calls in a Pi session JSONL against the launch contract."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


FORBIDDEN_KEYS_IF_SET = {
    "isolation": {"worktree"},
}
# Any explicit false inherit_context on an oracle call is a caller violation.
DISPOSITION_RE = re.compile(
    r"\b(accepted|accepts|partially-accepted|partially accepted|partially accepts|rejected|rejects|escalated|escalates)\b"
    r".{0,80}\b(oracle|recommendation|advisory)\b|"
    r"\b(oracle|recommendation|advisory)\b.{0,80}\b(accepted|accepts|partially-accepted|partially accepted|partially accepts|rejected|rejects|escalated|escalates)\b|"
    r"\b(advisory disposition|oracle disposition)\b.{0,40}\b(accepted|partially-accepted|rejected|escalated)\b",
    re.I | re.S,
)


def iter_agent_calls(session_path: Path):
    for line_no, line in enumerate(session_path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        line = line.strip()
        if not line or "subagent_type" not in line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        content = obj.get("content")
        msg = obj.get("message")
        if isinstance(msg, dict):
            content = msg.get("content", content)
        blocks = content if isinstance(content, list) else []
        for block in blocks:
            if not isinstance(block, dict):
                continue
            if block.get("type") not in (
                "toolCall",
                "tool_use",
                "functionCall",
                "tool_call",
                "function_call",
            ):
                continue
            name = block.get("name") or block.get("toolName") or ""
            if str(name) not in ("Agent", "agent"):
                continue
            args = block.get("arguments") or block.get("input") or block.get("args") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            if not isinstance(args, dict):
                continue
            yield line_no, args, obj.get("timestamp")


def session_text_blob(session_path: Path) -> str:
    parts = []
    for line in session_path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        content = obj.get("content")
        msg = obj.get("message")
        if isinstance(msg, dict):
            content = msg.get("content", content)
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and isinstance(block.get("text"), str):
                    parts.append(block["text"])
                elif isinstance(block, str):
                    parts.append(block)
    return "\n".join(parts)


def analyze(session_path: Path, require_disposition: bool = True) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    oracle_calls = []
    clean_calls = []
    for line_no, args, ts in iter_agent_calls(session_path):
        sat = str(args.get("subagent_type") or args.get("subagentType") or "")
        if sat.lower() != "oracle":
            continue
        prompt = args.get("prompt") or ""
        if not isinstance(prompt, str):
            prompt = str(prompt)
        call = {
            "line": line_no,
            "timestamp": ts,
            "description": args.get("description"),
            "prompt_len": len(prompt),
            "inherit_context": args.get("inherit_context"),
            "isolation": args.get("isolation"),
            "model": args.get("model"),
            "thinking": args.get("thinking"),
            "has_question_mark": "?" in prompt,
            "has_recommendation": bool(
                re.search(
                    r"\b(current recommendation|my recommendation|driving agent.?s (?:current )?recommendation|leaning)\b",
                    prompt,
                    re.I,
                )
            ),
            "has_options": bool(re.search(r"\boptions?\b|\bA\)|\bB\)|versus|\bvs\.?\b", prompt, re.I)),
            "has_constraints": bool(
                re.search(r"\b(constraint|inherited|must not|do not|locked|established)\b", prompt, re.I)
            ),
            "asks_readonly": bool(re.search(r"read-?only|do not edit", prompt, re.I)),
        }
        oracle_calls.append(call)

        call_errors = []
        # Caller must omit these on a successful launch. A rejected first attempt
        # may still appear; require at least one clean call overall.
        if "isolation" in args and args.get("isolation") not in (None, "", "none"):
            call_errors.append(
                "line %s: oracle call set isolation=%r (must omit; never worktree)"
                % (line_no, args.get("isolation"))
            )
        if "inherit_context" in args and args.get("inherit_context") is False:
            call_errors.append(
                "line %s: oracle call set inherit_context=false (must omit so persona true applies)"
                % line_no
            )
        model = args.get("model")
        if model not in (None, ""):
            model_s = str(model)
            if model_s not in ("openai-codex/gpt-5.6-sol", "gpt-5.6-sol") and not model_s.endswith(
                "/gpt-5.6-sol"
            ):
                call_errors.append("line %s: oracle call overrode model=%r" % (line_no, model))
        if args.get("thinking") not in (None, "", "high"):
            call_errors.append(
                "line %s: oracle call overrode thinking=%r (omit or high only)"
                % (line_no, args.get("thinking"))
            )
        if not call["has_question_mark"]:
            call_errors.append("line %s: oracle packet missing narrow question ('?')" % line_no)
        if not call["has_recommendation"]:
            warnings.append("line %s: oracle packet missing driving-agent recommendation" % line_no)
        if not call["has_options"]:
            warnings.append("line %s: oracle packet may be missing credible options" % line_no)
        if not call["has_constraints"]:
            warnings.append("line %s: oracle packet may be missing constraints/inherited decisions" % line_no)

        # Packet quality is hard; launch-arg overrides are soft when the install
        # strip-guard + persona-first transport still run Oracle correctly.
        hard = [e for e in call_errors if "missing narrow question" in e or "overrode model" in e]
        soft = [e for e in call_errors if e not in hard]
        warnings.extend(soft)
        if hard:
            errors.extend(hard)
        elif call["has_question_mark"]:
            clean_calls.append(call)
        else:
            warnings.extend(call_errors)

    if not oracle_calls:
        errors.append("no Agent call with subagent_type=oracle found")
    elif not clean_calls:
        errors.append(
            "oracle was called but no launch had a usable decision packet "
            "(need one narrow question '?')"
        )

    blob = session_text_blob(session_path)
    has_disposition = bool(DISPOSITION_RE.search(blob))
    if require_disposition and oracle_calls and not has_disposition:
        errors.append(
            "oracle was called but session text lacks an accepted/rejected/escalated disposition"
        )

    # Operator prompt should not have forced the call for proactive e2e.
    if re.search(r"\b(use oracle|/consult:oracle|call the oracle)\b", blob, re.I):
        # Only flag if it appears in a user role heavily — soft warning.
        warnings.append("session text mentions explicit oracle prompting; proactive purity may be reduced")

    status = "pass" if not errors else "fail"
    return {
        "schemaVersion": 1,
        "status": status,
        "session": str(session_path),
        "oracleCallCount": len(oracle_calls),
        "oracleCalls": oracle_calls,
        "hasDisposition": has_disposition,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session", type=Path, help="Path to Pi session .jsonl")
    parser.add_argument("--allow-missing-disposition", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if not args.session.is_file():
        payload = {
            "schemaVersion": 1,
            "status": "fail",
            "errors": ["session file not found: %s" % args.session],
            "warnings": [],
            "oracleCallCount": 0,
            "oracleCalls": [],
        }
    else:
        payload = analyze(args.session, require_disposition=not args.allow_missing_disposition)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("Oracle session analysis: %s" % payload["status"])
        print("oracle_calls=%s disposition=%s" % (payload.get("oracleCallCount"), payload.get("hasDisposition")))
        for err in payload.get("errors") or []:
            print("ERROR: %s" % err)
        for warn in payload.get("warnings") or []:
            print("WARN: %s" % warn)
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
