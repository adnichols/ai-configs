#!/usr/bin/env python3
"""Collect a read-only Nodaste stand-up packet and render a first-pass Y/T/B draft."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

HOSTS = {"this-host": None, "dever": "dever", "macbook-pro": "mbp"}
DOCT_WORKSPACES = {
    "shared": "6dbf05f0-fc4b-41f4-b927-5799ec7be0bb",
    "personal": "759bfae3-44f1-4ce5-9bff-9077d9933a21",
}
WORK_RE = re.compile(r"nodaste|heddle|ccore|c-core|doct|herdr|weft|navi|monsoon|mycelios|tinker|find studio", re.I)
EXCLUDE_RE = re.compile(r"\bjack\b|coach|coaching|workday|\bwd\b|personal|therapy|doctor", re.I)


def run(argv: list[str], host: str | None = None, timeout: int = 45) -> dict:
    remote = 'export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"; ' + shlex.join(argv)
    cmd = argv if host is None else ["ssh", "-o", "ConnectTimeout=6", host, remote]
    try:
        p = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
        return {"ok": p.returncode == 0, "stdout": p.stdout, "stderr": p.stderr, "code": p.returncode}
    except Exception as exc:
        return {"ok": False, "stdout": "", "stderr": str(exc), "code": -1}


def parsed(result: dict) -> object | None:
    if not result["ok"]:
        return None
    try:
        return json.loads(result["stdout"])
    except json.JSONDecodeError:
        return None


def collect(day: dt.date) -> dict:
    next_day = day + dt.timedelta(days=1)
    packet: dict = {"date": str(day), "generated_at": dt.datetime.now().astimezone().isoformat(), "hosts": {}, "warnings": []}
    git_cmd = ["sh", "-lc", f'''for r in "$HOME"/code/* "$HOME"/.herdr/worktrees/*/*; do git -C "$r" rev-parse --is-inside-work-tree >/dev/null 2>&1 || continue; git -C "$r" log --all --since="{day} 00:00" --until="{next_day} 00:00" --author='Aaron\\|anichols\\|adnichols' --format='%H%x09%ad%x09%s' --date=iso-local 2>/dev/null | while IFS= read -r line; do printf '%s\\t%s\\n' "$line" "$r"; done; done | sort -u''']
    for label, host in HOSTS.items():
        workspaces = run(["herdr", "workspace", "list"], host)
        agents = run(["herdr", "agent", "list"], host)
        commits = run(git_cmd, host, 90)
        packet["hosts"][label] = {"workspaces": parsed(workspaces), "agents": parsed(agents), "commits": commits["stdout"].splitlines() if commits["ok"] else []}
        for name, result in (("workspaces", workspaces), ("agents", agents), ("commits", commits)):
            if not result["ok"]:
                packet["warnings"].append(f"{label} {name}: {result['stderr'].strip()}")
    packet["doct"] = {}
    for label, workspace_id in DOCT_WORKSPACES.items():
        result = run(["doct-agent", "plans", "board", "list", "--base-url", "https://doct.nodaste.com", "--workspace-id", workspace_id, "--json"])
        packet["doct"][label] = parsed(result)
        if not result["ok"]:
            packet["warnings"].append(f"Doct {label}: {result['stderr'].strip()}")
    slack = run(["agent-slack", "message", "list", "C09C9V4BBR8", "--workspace", "nodaste", "--limit", "80", "--max-body-chars", "5000"])
    packet["standup_channel"] = parsed(slack)
    if not slack["ok"]:
        packet["warnings"].append(f"Slack: {slack['stderr'].strip()}")
    granola = run(["granola", "meeting", "list", "--since", str(day), "--until", str(day), "-o", "json"])
    meetings = parsed(granola)
    if isinstance(meetings, list):
        packet["granola"] = [m for m in meetings if WORK_RE.search(json.dumps(m)) and not EXCLUDE_RE.search(json.dumps(m))]
    else:
        packet["granola"] = []
        packet["warnings"].append(f"Granola unavailable: {granola['stderr'].strip() or granola['stdout'].strip()}")
    prs = run(["gh", "pr", "list", "-R", "Nodaste-Lab/heddle", "--state", "merged", "--search", f"merged:{day}", "--limit", "100", "--json", "number,title,mergedAt,url,author"])
    packet["merged_prs"] = parsed(prs) or []
    if not prs["ok"]:
        packet["warnings"].append(f"GitHub PRs: {prs['stderr'].strip()}")
    return packet


def completed_outcomes(prs: list[dict]) -> list[str]:
    titles = " ".join(p.get("title", "") for p in prs).lower()
    outcomes = []
    if any(x in titles for x in ("release", "deployment", "publishing")):
        outcomes.append("Changed releases so we can roll the Hub and signed desktop updates through Dev, Staging, and Production one environment at a time. The release tooling now distinguishes a failed deployment from a failed health check and blocks an unsigned or incorrectly versioned production update.")
    if any(x in titles for x in ("cust hub", "fresh heddle")):
        outcomes.append("Changed new Heddle and CCore sign-ins to use the dedicated Customer Hub by default, while preserving an existing customer's selected Hub during reauthentication. This prevents a new or returning customer from being silently routed to the wrong backend environment.")
    if "private-space" in titles:
        outcomes.append("Fixed a case where two private workspaces from different accounts or customer Hubs could share the same remote identifier. They are now stored separately, preventing one context's keys, membership, or sync position from being attached to another.")
    if "canonical identity" in titles:
        outcomes.append("Established one verified person identity per account and used it consistently for assignments, “Mine” filters, Signals, daily briefs, and decision reviews. This replaces guesses based on display names that could misattribute work or route it to the wrong person.")
    if any(x in titles for x in ("upgrade rehydrate", "adv-8")):
        outcomes.append("Ran a real upgrade from Heddle 0.2.42 with historical customer data and verified that the current version restores that data through CCore and Heddle. Recoverable content gaps are repaired automatically, while permission problems remain visible instead of being reported as a successful recovery.")
    return outcomes


def plan_outcome(title: str) -> str | None:
    title = title.lower()
    if "auth root readiness" in title:
        return "Finish the startup fix for cases where Heddle shows a signed-in account but CCore is not actually ready to use it after an upgrade or restart. The final step is to release it and verify the recovery path on a real upgraded installation."
    if "test suite performance" in title:
        return "Reduce release delays caused by multiple reviewers rerunning the same large test suites on one machine. Reviews will inspect the change, while one controlled verification run owns the expensive build and test work."
    if "truthful auth" in title:
        return "Separate sign-in failures, missing account access, unavailable customer Hubs, and missing workspaces instead of presenting them all as a generic error. Each case should tell the person what failed and whether to sign in again, choose another account, retry, or contact support."
    if "palette authority" in title:
        return "Replace Doct's remaining one-off theme colors with the shared Weft palette. This keeps light and dark modes consistent and lets future color changes be made once rather than repaired separately across screens."
    if "process-test lifecycle" in title:
        return "Stop automated Heddle tests from leaving helper services running after a test ends. Those orphaned processes have caused later tests to fail or the overall release check to hang for hours."
    return None


def render(packet: dict) -> str:
    prs = [p for p in packet["merged_prs"] if (p.get("author") or {}).get("login") in {"adnichols", "aaronnodaste"}]
    active, blocked = [], []
    cutoff = dt.datetime.fromisoformat(packet["generated_at"]) - dt.timedelta(days=2)
    for host, data in packet["hosts"].items():
        agents = ((data.get("agents") or {}).get("result") or {}).get("agents", [])
        for a in agents:
            state = a.get("agent_status")
            project = Path(a.get('cwd', '')).name or a.get('cwd', '')
            item = f"{host}: {project} ({state})"
            if state == "working" and project not in {"anichols", "~"}: active.append(item)
            if state == "blocked": blocked.append(item)
    plans = []
    for board in packet["doct"].values():
        for card in (board or {}).get("cards", []):
            updated = dt.datetime.fromisoformat(card["updatedAt"].replace("Z", "+00:00")).astimezone()
            if card.get("columnKey") == "in_progress" and updated >= cutoff:
                plans.append(card["title"])
    lines = ["Y:", ""]
    lines += [f"- {outcome}" for outcome in completed_outcomes(prs)] or ["- No completed customer or team outcomes were confidently identified; review the evidence packet."]
    for meeting in packet.get("granola", []):
        lines.append(f"- Nodaste-related call: {meeting.get('title') or meeting.get('name') or 'meeting'}")
    lines += ["", "T:", ""]
    lines += [f"- {x}" for x in dict.fromkeys(filter(None, (plan_outcome(x) for x in plans)))]
    if not plans and not active:
        lines.append("- No current work was confidently identified.")
    lines += ["", "B:", ""]
    lines += [f"- {x}" for x in blocked] or ["- No clear blockers detected."]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Work date to summarize (default: yesterday)")
    parser.add_argument("--output", type=Path, help="Write the evidence packet as JSON")
    args = parser.parse_args()
    day = dt.date.fromisoformat(args.date) if args.date else dt.date.today() - dt.timedelta(days=1)
    packet = collect(day)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(packet, indent=2) + "\n")
    print(render(packet))
    if packet["warnings"]:
        print(f"Collector note: {len(packet['warnings'])} source warning(s); inspect the JSON packet.", file=sys.stderr)


if __name__ == "__main__":
    main()
