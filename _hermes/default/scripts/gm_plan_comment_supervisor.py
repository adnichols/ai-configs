#!/usr/bin/env python3
"""Quiet supervisor for owned Good Morning Doct plan listeners.

No stdout unless something is genuinely wrong. Intended for no_agent cron.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import time
from typing import Any

BASE_URL = "https://doct.nodaste.com"
STATE_DIR = pathlib.Path.home() / ".hermes" / "state" / "gm-plan-maintainer"
REGISTRY = STATE_DIR / "active-plans.json"
PID_DIR = STATE_DIR / "pids"
LOG_DIR = STATE_DIR / "logs"
LISTENER = pathlib.Path.home() / ".hermes" / "scripts" / "gm_plan_comment_listener.py"
OBSIDIAN = pathlib.Path.home() / "Obsidian"


def log(msg: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with (LOG_DIR / "supervisor.log").open("a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S%z')} {msg}\n")


def load_registry() -> dict[str, Any]:
    if not REGISTRY.exists():
        return {"active_plans": []}
    try:
        return json.loads(REGISTRY.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"GM listener supervisor: cannot parse registry {REGISTRY}: {exc}")
        return {"active_plans": []}


def save_registry(reg: dict[str, Any]) -> None:
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    tmp = REGISTRY.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(reg, indent=2) + "\n", encoding="utf-8")
    tmp.replace(REGISTRY)


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except Exception:
        return False


def entry_document_id(item: dict[str, Any]) -> str:
    return str(item.get("document_id") or item.get("plan_id") or "")


def cmdline_contains(pid: int, document_id: str) -> bool:
    try:
        cp = subprocess.run(["ps", "-p", str(pid), "-o", "command="], text=True, capture_output=True, timeout=5)
        return cp.returncode == 0 and "gm_plan_comment_listener.py" in cp.stdout and document_id in cp.stdout
    except Exception:
        return False


def listener_running(document_id: str) -> bool:
    pid_file = PID_DIR / f"{document_id}.pid"
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text(encoding="utf-8").strip())
            if pid_alive(pid) and cmdline_contains(pid, document_id):
                return True
        except Exception:
            pass
        try:
            pid_file.unlink()
        except Exception:
            pass
    try:
        cp = subprocess.run(["pgrep", "-f", f"gm_plan_comment_listener.py {document_id}"], text=True, capture_output=True, timeout=5)
        return cp.returncode == 0 and bool(cp.stdout.strip())
    except Exception:
        return False


def document_lifecycle(document_id: str) -> str:
    cp = subprocess.run([
        "doct-agent", "plans", "show",
        "--base-url", BASE_URL,
        "--id", document_id,
        "--json",
    ], cwd=str(OBSIDIAN), text=True, capture_output=True, timeout=30)
    if cp.returncode != 0:
        log(f"show failed for {document_id}: {cp.stderr.strip() or cp.stdout.strip()}")
        return "unknown"
    try:
        data = json.loads(cp.stdout)
        plan = data.get("plan") if isinstance(data.get("plan"), dict) else {}
        doc = data.get("document") if isinstance(data.get("document"), dict) else {}
        return str(plan.get("lifecycleState") or doc.get("status") or data.get("lifecycleState") or "active")
    except Exception as exc:
        log(f"show parse failed for {document_id}: {exc}")
        return "active"


def start_listener(document_id: str, workspace_id: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    out = (LOG_DIR / f"{document_id}.supervised.out").open("ab")
    err = (LOG_DIR / f"{document_id}.supervised.err").open("ab")
    subprocess.Popen(
        [sys.executable, str(LISTENER), document_id, workspace_id],
        cwd=str(OBSIDIAN),
        stdout=out,
        stderr=err,
        start_new_session=True,
        close_fds=True,
    )
    log(f"started Doct listener for document={document_id} workspace={workspace_id}")


def main() -> int:
    if not LISTENER.exists():
        print(f"GM listener supervisor: missing listener script {LISTENER}")
        return 1
    reg = load_registry()
    changed = False
    active = []
    for item in reg.get("active_plans", []):
        if item.get("status", "active") != "active":
            active.append(item)
            continue
        if item.get("routine") != "good_morning":
            # Ownership guard: never supervise unrelated plans.
            active.append(item)
            continue
        document_id = entry_document_id(item)
        workspace_id = str(item.get("workspace_id") or "")
        if not document_id or not workspace_id:
            log(f"skipping legacy/non-Doct GM registry item without document_id/workspace_id: {item}")
            active.append(item)
            continue
        lifecycle = document_lifecycle(document_id).lower()
        if lifecycle == "archived":
            item["status"] = "archived"
            item["archived_at"] = time.strftime('%Y-%m-%dT%H:%M:%S%z')
            changed = True
            active.append(item)
            continue
        if not listener_running(document_id):
            start_listener(document_id, workspace_id)
        active.append(item)
    reg["active_plans"] = active
    if changed:
        save_registry(reg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
