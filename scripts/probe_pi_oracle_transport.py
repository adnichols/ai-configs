#!/usr/bin/env python3
"""Resolve installed Oracle launch profile without invoking a model.

Fails closed when persona frontmatter or transport precedence would drop
inherited context or allow caller worktree isolation to win.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

EXPECTED_MODEL = "openai-codex/gpt-5.6-sol"
EXPECTED_REASONING = "high"
EXPECTED_THINKING = "high"


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"---\n(.*?)\n---(?:\n|$)", text, re.S)
    if not match:
        raise ValueError("missing frontmatter: %s" % path)
    values: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def transport_precedence(package: Path) -> str:
    precedence_files = (
        package / "src/invocation-config.ts",
        package / "dist/invocation-config.js",
    )
    agent_first = "agentConfig?.isolation ?? params.isolation"
    caller_first = "params.isolation ?? agentConfig?.isolation"
    inherit_agent_first = "inheritContext: agentConfig?.inheritContext ?? params.inherit_context"
    found = []
    inherit_ok = False
    for path in precedence_files:
        if not path.is_file():
            raise ValueError("required transport file missing: %s" % path)
        text = path.read_text(encoding="utf-8")
        if agent_first in text:
            found.append("agent")
        elif caller_first in text:
            found.append("caller")
        else:
            raise ValueError("unrecognized isolation precedence in %s" % path)
        if inherit_agent_first in text:
            inherit_ok = True
    if len(set(found)) != 1:
        raise ValueError("source/dist isolation precedence disagree")
    if not inherit_ok:
        raise ValueError("inheritContext does not prefer agentConfig over caller params")
    return found[0]


def resolve(args: argparse.Namespace) -> dict:
    agent_dir = Path(args.agent_dir).expanduser().resolve()
    agent_source_dir = (
        Path(args.agent_source_dir).expanduser().resolve()
        if args.agent_source_dir
        else agent_dir / "agents"
    )
    package = agent_dir / "npm/node_modules/@tintinweb/pi-subagents"
    errors: list[str] = []
    try:
        precedence = transport_precedence(package)
    except ValueError as exc:
        return {
            "schemaVersion": 1,
            "status": "fail",
            "reason": str(exc),
            "profile": {},
        }

    metadata = frontmatter(agent_source_dir / "oracle.md")
    persona_isolation = metadata.get("isolation")
    persona_inherit = metadata.get("inherit_context")
    persona_thinking = metadata.get("thinking")
    persona_default_context = metadata.get("defaultContext")
    model = metadata.get("model")
    reasoning = metadata.get("reasoningEffort")

    # Simulate a buggy caller that still sets worktree + inherit false.
    caller_isolation = args.caller_isolation
    caller_inherit = args.caller_inherit_context
    if precedence == "agent":
        effective_isolation = persona_isolation or caller_isolation
        isolation_source = "persona" if persona_isolation else "caller"
        if persona_inherit in ("true", "false"):
            effective_inherit = persona_inherit == "true"
            inherit_source = "persona"
        else:
            effective_inherit = bool(caller_inherit)
            inherit_source = "caller"
    else:
        effective_isolation = caller_isolation or persona_isolation
        isolation_source = "caller" if caller_isolation else "persona"
        if caller_inherit is not None:
            effective_inherit = bool(caller_inherit)
            inherit_source = "caller"
        else:
            effective_inherit = persona_inherit == "true"
            inherit_source = "persona"

    if persona_isolation != "none":
        errors.append("oracle persona isolation is %r; expected 'none'" % persona_isolation)
    if persona_inherit != "true":
        errors.append("oracle persona inherit_context is %r; expected 'true'" % persona_inherit)
    if persona_thinking != EXPECTED_THINKING:
        errors.append("oracle thinking is %r; expected %r" % (persona_thinking, EXPECTED_THINKING))
    if persona_default_context != "fork":
        errors.append("oracle defaultContext is %r; expected 'fork'" % persona_default_context)
    if model != EXPECTED_MODEL or reasoning != EXPECTED_REASONING:
        errors.append(
            "oracle profile is %r/%r; expected %r/%r"
            % (model, reasoning, EXPECTED_MODEL, EXPECTED_REASONING)
        )
    if effective_isolation != "none":
        errors.append(
            "effective isolation is %r from %s (caller tried %r)"
            % (effective_isolation, isolation_source, caller_isolation)
        )
    if not effective_inherit:
        errors.append(
            "effective inheritContext is false from %s (caller tried %r)"
            % (inherit_source, caller_inherit)
        )
    if precedence == "caller" and caller_isolation == "worktree":
        errors.append("caller isolation overrides persona because transport is caller-first")

    return {
        "schemaVersion": 1,
        "status": "fail" if errors else "pass",
        "reason": "; ".join(errors) if errors else None,
        "agentDir": str(agent_dir),
        "agentSourceDir": str(agent_source_dir),
        "transportPrecedence": "%s-first" % precedence,
        "profile": {
            "personaIsolation": persona_isolation,
            "personaInheritContext": persona_inherit,
            "personaThinking": persona_thinking,
            "personaDefaultContext": persona_default_context,
            "callerIsolation": caller_isolation,
            "callerInheritContext": caller_inherit,
            "effectiveIsolation": effective_isolation,
            "isolationSource": isolation_source,
            "effectiveInheritContext": effective_inherit,
            "inheritSource": inherit_source,
            "model": model,
            "reasoningEffort": reasoning,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-dir", default=str(Path.home() / ".pi/agent"))
    parser.add_argument("--agent-source-dir")
    parser.add_argument("--caller-isolation", choices=("none", "worktree"), default="worktree")
    parser.add_argument(
        "--caller-inherit-context",
        choices=("true", "false"),
        default="false",
        help="Simulated buggy caller override (default false).",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.caller_inherit_context == "true":
        args.caller_inherit_context = True
    elif args.caller_inherit_context == "false":
        args.caller_inherit_context = False
    try:
        payload = resolve(args)
    except (OSError, ValueError) as exc:
        payload = {"schemaVersion": 1, "status": "fail", "reason": str(exc), "profile": {}}
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("Pi oracle transport: %s" % payload["status"])
        if payload.get("reason"):
            print("Reason: %s" % payload["reason"])
        profile = payload.get("profile") or {}
        if profile:
            print(
                "oracle: isolation=%s inherit=%s model=%s reasoning=%s thinking=%s"
                % (
                    profile.get("effectiveIsolation"),
                    profile.get("effectiveInheritContext"),
                    profile.get("model"),
                    profile.get("reasoningEffort"),
                    profile.get("personaThinking"),
                )
            )
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
