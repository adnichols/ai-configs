#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

WORKDIR = Path("/Users/anichols/Obsidian")
RUNNER = WORKDIR / ".agents" / "scripts" / "gm_deterministic.py"


def main() -> int:
    report_date = os.environ.get("GM_DATE") or date.today().isoformat()
    dry_run = os.environ.get("GM_DRY_RUN") == "1"
    cmd = ["python3", str(RUNNER), "--date", report_date]
    cmd.append("--dry-run" if dry_run else "--publish")
    env = os.environ.copy()
    env.setdefault("GM_JOB_ID", "039f96dcecfc")
    env.setdefault("GM_JOB_NAME", "Daily Good Morning HTML Plan + Todoist Review")
    proc = subprocess.run(cmd, cwd=WORKDIR, capture_output=True, text=True, timeout=600, env=env)
    if proc.returncode != 0:
        print("Daily GM deterministic runner failed.")
        if proc.stdout.strip():
            print("STDOUT:")
            print(proc.stdout.strip())
        if proc.stderr.strip():
            print("STDERR:")
            print(proc.stderr.strip())
        return proc.returncode
    try:
        manifest = json.loads(proc.stdout)
    except json.JSONDecodeError:
        print("Daily GM deterministic runner returned non-JSON output.")
        print(proc.stdout[-4000:])
        return 1
    phase_errors = [s for s in manifest.get("phase_statuses", []) if s.get("status") != "ok"]
    publish = manifest.get("publish") or {}
    if not manifest.get("ok") or phase_errors:
        print(f"Daily GM completed with phase errors for {report_date}.")
        for item in phase_errors:
            print(f"- {item.get('name')}: {item.get('error')}")
        print(f"Artifact: {manifest.get('html_path')}")
        return 1
    review_url = publish.get("review_url")
    if dry_run:
        print(f"Daily GM dry-run OK for {report_date}: {manifest.get('html_path')}")
        return 0
    if review_url:
        print(f"Good morning report is ready: {review_url}")
    else:
        print(f"Good morning report completed, but no review URL was returned. Artifact: {manifest.get('html_path')}")
    task = publish.get("todoist_task") or {}
    if task.get("ok"):
        if task.get("deduped"):
            print(f"Todoist review task already exists: {task.get('id') or task.get('stdout', '').strip()}")
        else:
            print("Todoist review task created.")
    else:
        print(f"Todoist review task was not verified: {task.get('stderr') or task.get('stdout') or task}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
