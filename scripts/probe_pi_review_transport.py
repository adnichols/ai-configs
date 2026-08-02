#!/usr/bin/env python3
"""Resolve installed planner/reviewer launch profiles without invoking a model."""

import argparse
import json
import re
import sys
from pathlib import Path

PROFILES = ("planner", "reviewer")
EXPECTED = {
    "planner": ("openai-codex/gpt-5.6-sol", "medium"),
    "reviewer": ("openai-codex/gpt-5.6-terra", "medium"),
}


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    match = re.match(r"---\n(.*?)\n---(?:\n|$)", text, re.S)
    if not match:
        raise ValueError("missing frontmatter: %s" % path)
    values = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def resolve(args):
    agent_dir = Path(args.agent_dir).expanduser().resolve()
    target = Path(args.target_checkout).expanduser().resolve() if args.target_checkout else Path.cwd().resolve()
    package = agent_dir / "npm/node_modules/@tintinweb/pi-subagents"
    precedence_files = (package / "src/invocation-config.ts", package / "dist/invocation-config.js")
    agent_first = "isolation: agentConfig?.isolation ?? params.isolation,"
    caller_first = "isolation: params.isolation ?? agentConfig?.isolation,"
    precedence = []
    for path in precedence_files:
        if not path.is_file():
            raise ValueError("required transport file missing: %s" % path)
        text = path.read_text(encoding="utf-8")
        if agent_first in text:
            precedence.append("agent")
        elif caller_first in text:
            precedence.append("caller")
        else:
            raise ValueError("unrecognized isolation precedence in %s" % path)
    if len(set(precedence)) != 1:
        raise ValueError("source/dist isolation precedence disagree")
    profiles = {}
    errors = []
    agent_source_dir = Path(args.agent_source_dir).expanduser().resolve() if args.agent_source_dir else agent_dir / "agents"
    for name in PROFILES:
        metadata = frontmatter(agent_source_dir / (name + ".md"))
        persona_isolation = metadata.get("isolation")
        if precedence[0] == "agent":
            effective = persona_isolation or args.caller_isolation
            source = "persona" if persona_isolation else "caller"
        else:
            effective = args.caller_isolation or persona_isolation
            source = "caller" if args.caller_isolation else "persona"
        model = metadata.get("model")
        reasoning = metadata.get("reasoningEffort")
        expected_model, expected_reasoning = EXPECTED[name]
        if effective != "none":
            errors.append("%s effective isolation is %r from %s" % (name, effective, source))
        if model != expected_model or reasoning != expected_reasoning:
            errors.append("%s profile is %r/%r; expected %r/%r" % (name, model, reasoning, expected_model, expected_reasoning))
        profiles[name] = {
            "personaIsolation": persona_isolation,
            "callerIsolation": args.caller_isolation,
            "effectiveIsolation": effective,
            "isolationSource": source,
            "model": model,
            "reasoningEffort": reasoning,
        }
    if args.target_checkout and not target.is_dir():
        errors.append("target checkout is not a directory: %s" % target)
    if precedence[0] == "caller" and args.caller_isolation:
        errors.append("caller isolation overrides persona because installed transport uses caller-first precedence")
    return {
        "schemaVersion": 1,
        "status": "fail" if errors else "pass",
        "reason": "; ".join(errors) if errors else None,
        "agentDir": str(agent_dir),
        "agentSourceDir": str(agent_source_dir),
        "targetCheckout": str(target),
        "transportPrecedence": "%s-first" % precedence[0],
        "profiles": profiles,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-dir", default=str(Path.home() / ".pi/agent"))
    parser.add_argument("--target-checkout")
    parser.add_argument("--agent-source-dir")
    parser.add_argument("--caller-isolation", choices=("none", "worktree"))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        payload = resolve(args)
    except (OSError, ValueError) as exc:
        payload = {"schemaVersion": 1, "status": "fail", "reason": str(exc), "profiles": {}}
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("Pi review transport: %s" % payload["status"])
        if payload.get("reason"):
            print("Reason: %s" % payload["reason"])
        for name, profile in payload.get("profiles", {}).items():
            print("%s: isolation=%s model=%s reasoning=%s" % (name, profile["effectiveIsolation"], profile["model"], profile["reasoningEffort"]))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
