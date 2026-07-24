#!/usr/bin/env python3
"""Patch pi-service-tier for CLIProxyAPI's OpenAI Responses route."""

from __future__ import annotations

import os
import sys
from pathlib import Path

OLD = '''  const definition = SERVICE_TIER_PROVIDER_DEFINITIONS[model.provider];
  return model.api === definition.api ? model.provider : undefined;'''
NEW = '''  const definition = SERVICE_TIER_PROVIDER_DEFINITIONS[model.provider];
  // CLIProxyAPI serves Codex GPT models through the standard Responses route,
  // not ChatGPT's separate /codex/responses endpoint.
  const usesCLIProxyAPIResponses =
    model.provider === "openai-codex" && model.api === "openai-responses";
  return model.api === definition.api || usesCLIProxyAPIResponses
    ? model.provider
    : undefined;'''
MARKER = "const usesCLIProxyAPIResponses ="


def package_path(agent_dir: Path) -> Path:
    return agent_dir / "npm" / "node_modules" / "pi-service-tier" / "shared.ts"


def main() -> int:
    agent_dir = Path(
        os.environ.get("PI_CODING_AGENT_DIR", Path.home() / ".pi" / "agent")
    ).expanduser()
    target = package_path(agent_dir)
    if not target.is_file():
        print(f"pi-service-tier patch skipped: package not found at {target}")
        return 0

    source = target.read_text(encoding="utf-8")
    if MARKER in source:
        print(f"pi-service-tier CLIProxyAPI compatibility already present: {target}")
        return 0
    if OLD not in source:
        print(
            f"pi-service-tier patch refused: expected upstream block not found in {target}",
            file=sys.stderr,
        )
        return 1

    target.write_text(source.replace(OLD, NEW, 1), encoding="utf-8")
    print(f"patched pi-service-tier for CLIProxyAPI: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
