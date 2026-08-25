#!/usr/bin/env python3
"""Make repo-owned review/oracle personas explicitly disable worktree isolation.

Also retarget Agent-tool prose so callers stop advertising isolation: worktree
for oracle/reviewer/planner launches.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

PACKAGE = Path("npm/node_modules/@tintinweb/pi-subagents")
AGENT_FIRST_ISOLATION = "agentConfig?.isolation ?? params.isolation"
CALLER_FIRST_ISOLATION = "params.isolation ?? agentConfig?.isolation"
ALREADY_AUTHORITATIVE = {
    "src/types.ts": (
        'IsolationMode = "worktree" | "none"',
        'IsolationMode = "worktree" | "off"',
    ),
    "dist/types.d.ts": (
        'IsolationMode = "worktree" | "none"',
        'IsolationMode = "worktree" | "off"',
    ),
    "src/custom-agents.ts": (
        'fm.isolation === "worktree" || fm.isolation === "none"',
        'val === "off" || val === "none"',
    ),
    "dist/custom-agents.js": (
        'fm.isolation === "worktree" || fm.isolation === "none"',
        'val === "off" || val === "none"',
    ),
}
REPLACEMENTS = {
    "src/types.ts": (
        'export type IsolationMode = "worktree";',
        'export type IsolationMode = "worktree" | "none";',
    ),
    "dist/types.d.ts": (
        'export type IsolationMode = "worktree";',
        'export type IsolationMode = "worktree" | "none";',
    ),
    "src/custom-agents.ts": (
        'isolation: fm.isolation === "worktree" ? "worktree" : undefined,',
        'isolation: fm.isolation === "worktree" || fm.isolation === "none" ? fm.isolation : undefined,',
    ),
    "dist/custom-agents.js": (
        'isolation: fm.isolation === "worktree" ? "worktree" : undefined,',
        'isolation: fm.isolation === "worktree" || fm.isolation === "none" ? fm.isolation : undefined,',
    ),
}

# Tool-description guidance that trains callers away from worktree isolation on
# isolation:none personas (oracle/reviewer/planner).
LIVE_CHECKOUT_GUARD_MARKER = "ai-configs live-checkout agent guard"

GET_AGENT_CONFIG = "const customConfig = getAgentConfig(subagentType);"
SRC_GUARD_INSERT = """const customConfig = getAgentConfig(subagentType);

      // ai-configs live-checkout agent guard
      // Strip caller overrides that fight isolation:none / inherited-context personas.
      // Do not hard-error: models otherwise retry-loop with the same bad args.
      if (subagentType === "oracle" || subagentType === "reviewer" || subagentType === "planner") {
        if (params.isolation === "worktree") {
          delete (params as { isolation?: unknown }).isolation;
        }
      }
      if (subagentType === "oracle" && params.inherit_context === false) {
        delete (params as { inherit_context?: unknown }).inherit_context;
      }
      if (subagentType === "oracle" && params.thinking && params.thinking !== "high") {
        delete (params as { thinking?: unknown }).thinking;
      }
"""
DIST_GUARD_INSERT = """const customConfig = getAgentConfig(subagentType);
            // ai-configs live-checkout agent guard
            // Strip caller overrides that fight isolation:none / inherited-context personas.
            // Do not hard-error: models otherwise retry-loop with the same bad args.
            if (subagentType === "oracle" || subagentType === "reviewer" || subagentType === "planner") {
                if (params.isolation === "worktree") {
                    delete params.isolation;
                }
            }
            if (subagentType === "oracle" && params.inherit_context === false) {
                delete params.inherit_context;
            }
            if (subagentType === "oracle" && params.thinking && params.thinking !== "high") {
                delete params.thinking;
            }
"""

DESCRIPTION_REPLACEMENTS = {
    'isolation: "worktree" runs the agent in an isolated git worktree; changes land on a branch.': (
        'isolation: omit for oracle/reviewer/planner (persona isolation: none / live checkout). '
        'Only use isolation: "worktree" for mutable implementation agents that need a throwaway tree.'
    ),
    (
        'Use isolation: "worktree" to run the agent in an isolated git worktree '
        "(safe parallel file modifications). The worktree is automatically cleaned up if the agent "
        "makes no changes; otherwise the path and branch are returned in the result."
    ): (
        "Never set isolation for oracle, reviewer, or planner — their frontmatter pins isolation: none "
        "on the live checkout; omit the property entirely. Only use isolation: \"worktree\" for mutable "
        "implementation agents that need a throwaway tree (cleaned up if unchanged; otherwise branch is returned)."
    ),
    (
        'Use inherit_context if the agent needs the parent conversation history.'
    ): (
        "Omit inherit_context for oracle (persona pins inherited/forked parent context). "
        "Only set inherit_context for other agents when they truly need parent history."
    ),
    (
        'Set to "worktree" to run the agent in a temporary git worktree (isolated copy of the repo). '
        "Changes are saved to a branch on completion."
    ): (
        'Omit for oracle/reviewer/planner (live checkout). Set to "worktree" only for mutable '
        "implementation agents that need a temporary git worktree; changes save to a branch on completion."
    ),
}


def apply_description_patches(source: str) -> tuple[str, int]:
    updated = source
    count = 0
    for old, new in DESCRIPTION_REPLACEMENTS.items():
        if new in updated:
            continue
        if old not in updated:
            continue
        updated = updated.replace(old, new)
        count += 1
    return updated, count

def has_agent_first_isolation(source: str) -> bool:
    return AGENT_FIRST_ISOLATION in source and CALLER_FIRST_ISOLATION not in source


def already_authoritative(relative: str, source: str) -> bool:
    return any(marker in source for marker in ALREADY_AUTHORITATIVE[relative])



def main() -> int:
    agent_dir = Path(
        os.environ.get("PI_CODING_AGENT_DIR", Path.home() / ".pi" / "agent")
    ).expanduser()
    package = agent_dir / PACKAGE
    if not package.is_dir():
        print(
            f"pi-subagents patch refused: required package not found at {package}",
            file=sys.stderr,
        )
        return 1

    for relative in ("src/invocation-config.ts", "dist/invocation-config.js"):
        target = package / relative
        if not target.is_file() or not has_agent_first_isolation(
            target.read_text(encoding="utf-8")
        ):
            print(
                f"pi-subagents patch refused: agent-config isolation precedence missing in {target}",
                file=sys.stderr,
            )
            return 1

    updates = []
    for relative, (old, new) in REPLACEMENTS.items():
        target = package / relative
        if not target.is_file():
            print(f"pi-subagents patch refused: missing {target}", file=sys.stderr)
            return 1
        source = target.read_text(encoding="utf-8")
        if new in source or already_authoritative(relative, source):
            continue
        if old not in source:
            print(
                f"pi-subagents patch refused: expected upstream text not found in {target}",
                file=sys.stderr,
            )
            return 1
        updates.append((target, source.replace(old, new, 1)))


    description_targets = []
    for relative in ("src/index.ts", "dist/index.js"):
        target = package / relative
        if not target.is_file():
            print(f"pi-subagents patch refused: missing {target}", file=sys.stderr)
            return 1
        source = target.read_text(encoding="utf-8")
        patched, count = apply_description_patches(source)

        if LIVE_CHECKOUT_GUARD_MARKER not in patched:
            replacement = (
                SRC_GUARD_INSERT if relative.startswith("src/") else DIST_GUARD_INSERT
            )
            if GET_AGENT_CONFIG not in patched:
                print(
                    f"pi-subagents patch refused: live-checkout guard anchor missing in {target}",
                    file=sys.stderr,
                )
                return 1
            patched = patched.replace(GET_AGENT_CONFIG, replacement, 1)
            count += 1


        if count:
            description_targets.append((target, patched, count))
        elif not any(new in source for new in DESCRIPTION_REPLACEMENTS.values()) and LIVE_CHECKOUT_GUARD_MARKER not in source:
            compact_new = DESCRIPTION_REPLACEMENTS[
                'isolation: "worktree" runs the agent in an isolated git worktree; changes land on a branch.'
            ]
            compact_old = 'isolation: "worktree" runs the agent in an isolated git worktree; changes land on a branch.'
            if compact_new not in source and compact_old not in source:
                print(
                    f"pi-subagents patch refused: Agent tool isolation guidance not found in {target}",
                    file=sys.stderr,
                )
                return 1

    for target, replacement in updates:
        target.write_text(replacement, encoding="utf-8")
    for target, replacement, count in description_targets:
        target.write_text(replacement, encoding="utf-8")

    if updates or description_targets:
        desc_n = sum(c for _, _, c in description_targets)
        print(
            "patched pi-subagents isolation: none support"
            + (f" and {desc_n} Agent-tool guidance/guard rewrite(s)" if desc_n else "")
        )
    else:
        print("pi-subagents authoritative isolation: none and Agent-tool guidance already present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
