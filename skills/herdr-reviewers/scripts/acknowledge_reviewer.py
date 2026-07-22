#!/usr/bin/env python3
"""Mark a consumed Herdr reviewer result seen without leaving focus changed."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any


def run_json(herdr: str, *args: str) -> dict[str, Any]:
    completed = subprocess.run(
        [herdr, *args], check=True, capture_output=True, text=True
    )
    payload = json.loads(completed.stdout)
    result = payload.get("result")
    if not isinstance(result, dict):
        raise RuntimeError(f"unexpected Herdr response for {' '.join(args)}")
    return result


def focused_tab(herdr: str) -> str:
    workspaces = run_json(herdr, "workspace", "list").get("workspaces", [])
    focused_workspaces = [item for item in workspaces if item.get("focused") is True]
    if len(focused_workspaces) != 1:
        raise RuntimeError("Herdr must have exactly one focused workspace")
    workspace_id = focused_workspaces[0].get("workspace_id")
    tabs = run_json(herdr, "tab", "list", "--workspace", workspace_id).get("tabs", [])
    focused_tabs = [item for item in tabs if item.get("focused") is True]
    if len(focused_tabs) != 1:
        raise RuntimeError("Herdr must have exactly one focused tab")
    return str(focused_tabs[0]["tab_id"])


def agent_status(herdr: str, target: str) -> str:
    agent = run_json(herdr, "agent", "get", target).get("agent", {})
    return str(agent.get("agent_status", "unknown"))


def acknowledge(herdr: str, target: str) -> str:
    status = agent_status(herdr, target)
    if status == "idle":
        return "already_seen"
    if status != "done":
        raise RuntimeError(f"reviewer must be done before acknowledgment; got {status}")

    restore_tab = focused_tab(herdr)
    focus_error: Exception | None = None
    try:
        run_json(herdr, "agent", "focus", target)
    except Exception as exc:  # restore focus even after a partial focus failure
        focus_error = exc

    restore_error: Exception | None = None
    try:
        run_json(herdr, "tab", "focus", restore_tab)
    except Exception as exc:
        restore_error = exc

    if focus_error is not None:
        raise RuntimeError(f"failed to acknowledge reviewer: {focus_error}")
    if restore_error is not None:
        raise RuntimeError(f"reviewer acknowledged but focus restore failed: {restore_error}")
    if agent_status(herdr, target) != "idle":
        raise RuntimeError("reviewer did not become idle after acknowledgment")
    return "acknowledged"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", help="reviewer agent name or pane ID")
    parser.add_argument("--herdr-bin", default="herdr")
    args = parser.parse_args()
    try:
        outcome = acknowledge(args.herdr_bin, args.target)
    except (RuntimeError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"acknowledgment failed: {exc}", file=sys.stderr)
        return 1
    print(outcome)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
