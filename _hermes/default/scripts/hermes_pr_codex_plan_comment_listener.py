#!/usr/bin/env python3
"""Quiet Doct plan comment listener for Hermes Codex PR Watcher plan.

Cron/no_agent contract: print nothing when no new actionable comments exist.
Print one Discord-ready alert when new pending/claimed queue items appear.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_URL = "https://doct.nodaste.com"
WORKSPACE_ID = "6dbf05f0-fc4b-41f4-b927-5799ec7be0bb"
DOCUMENT_ID = "25cbf31c-6af9-4d5c-97a0-a155f8bba997"
PLAN_URL = "https://doct.nodaste.com/d/workspace_6dbf05f0-fc4b-41f4-b927-5799ec7be0bb/docs/25cbf31c-6af9-4d5c-97a0-a155f8bba997"
STATE_PATH = Path.home() / ".hermes" / "state" / "hermes-pr-codex-plan-comment-listener.json"


def run_json(cmd: list[str]) -> dict:
    proc = subprocess.run(cmd, text=True, capture_output=True, timeout=45)
    if proc.returncode != 0:
        print(
            "Doct plan comment listener error\n"
            f"Plan: {PLAN_URL}\n"
            f"Command failed: {' '.join(cmd[:4])} ...\n"
            f"stderr: {proc.stderr.strip()[:800]}"
        )
        sys.exit(0)
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as exc:
        print(
            "Doct plan comment listener error\n"
            f"Plan: {PLAN_URL}\n"
            f"Could not parse JSON: {exc}\n"
            f"Output prefix: {(proc.stdout or '')[:800]}"
        )
        sys.exit(0)


def item_key(item: dict) -> str:
    for key in ("threadId", "rootCommentId", "id", "claimId"):
        if item.get(key):
            return str(item[key])
    return json.dumps(item, sort_keys=True)[:200]


def main() -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    state = {}
    if STATE_PATH.exists():
        try:
            state = json.loads(STATE_PATH.read_text())
        except Exception:
            state = {}
    seen = set(state.get("seen_item_keys", []))

    data = run_json([
        "doct-agent", "plans", "queue", "list",
        "--base-url", BASE_URL,
        "--workspace-id", WORKSPACE_ID,
        "--document-id", DOCUMENT_ID,
        "--json",
    ])
    items = data.get("items") or []
    actionable = []
    for item in items:
        queue_state = (item.get("queueState") or item.get("state") or "").lower()
        thread_state = (item.get("threadState") or "").lower()
        claim_status = (item.get("claimStatus") or "").lower()
        if queue_state in {"resolved", "closed", "done"} or thread_state in {"resolved", "closed"}:
            continue
        if claim_status in {"resolved", "acked"}:
            continue
        actionable.append(item)

    new_items = [item for item in actionable if item_key(item) not in seen]
    if not new_items:
        state.update({
            "last_checked_at": datetime.now(timezone.utc).isoformat(),
            "last_actionable_count": len(actionable),
            "document_id": DOCUMENT_ID,
            "workspace_id": WORKSPACE_ID,
            "plan_url": PLAN_URL,
        })
        STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
        return

    for item in new_items:
        seen.add(item_key(item))
    state.update({
        "last_checked_at": datetime.now(timezone.utc).isoformat(),
        "last_actionable_count": len(actionable),
        "seen_item_keys": sorted(seen),
        "document_id": DOCUMENT_ID,
        "workspace_id": WORKSPACE_ID,
        "plan_url": PLAN_URL,
    })
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")

    lines = [
        "New Doct plan comment/action detected",
        f"Plan: Hermes Codex PR Watcher Plan",
        f"URL: {PLAN_URL}",
        f"Document: {DOCUMENT_ID}",
        f"New item count: {len(new_items)}",
    ]
    for item in new_items[:5]:
        bits = []
        for key in ("threadId", "rootCommentId", "queueState", "claimStatus", "createdAt", "targetScope"):
            if item.get(key) is not None:
                bits.append(f"{key}={item[key]}")
        if bits:
            lines.append("- " + "; ".join(bits))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
