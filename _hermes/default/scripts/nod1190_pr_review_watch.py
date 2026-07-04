#!/usr/bin/env python3
"""Quiet watcher for NOD-1190 PR review readiness.

Prints only actionable changes so Hermes cron can deliver alerts without spam.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ISSUE = "NOD-1190"
REPO = "Nodaste-Lab/doct"
REPO_DIR = "/Users/anichols/code/doct"
TEAM = "NOD"
PROJECT = "2a70aa04-0606-436e-ac5f-b7859677ee08"
STATE_PATH = Path.home() / ".hermes" / "state" / "nod1190_pr_review_watch.json"
REVIEW_WAIT_SECONDS = 30 * 60

BUDGET_RE = re.compile(
    r"(codex|openai|review).{0,80}(budget|quota|limit|credit|usage)|"
    r"(out of budget|usage limit|rate limit|insufficient credits)",
    re.IGNORECASE | re.DOTALL,
)
CODEX_RE = re.compile(r"codex|openai", re.IGNORECASE)


def now() -> datetime:
    return datetime.now(timezone.utc)


def run(cmd: list[str], cwd: str = REPO_DIR, timeout: int = 60) -> tuple[int, str, str]:
    env = os.environ.copy()
    env.setdefault("NO_COLOR", "1")
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def run_json(cmd: list[str], cwd: str = REPO_DIR, timeout: int = 60) -> Any | None:
    code, out, err = run(cmd, cwd=cwd, timeout=timeout)
    if code != 0:
        raise RuntimeError(f"command failed ({code}): {' '.join(cmd)}\nSTDOUT:{out}\nSTDERR:{err}")
    if not out:
        return None
    return json.loads(out)


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"prs": {}, "alerts": {}}
    try:
        return json.loads(STATE_PATH.read_text())
    except Exception:
        return {"prs": {}, "alerts": {}}


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True))
    tmp.replace(STATE_PATH)


def alert_once(state: dict[str, Any], key: str, message: str, alerts: list[str]) -> None:
    sent = state.setdefault("alerts", {})
    if sent.get(key):
        return
    sent[key] = now().isoformat()
    alerts.append(message)


def get_issue_row() -> dict[str, Any] | None:
    data = run_json([
        "ltui", "--format", "json", "--limit", "10",
        "issues", "list",
        "--team", TEAM,
        "--project", PROJECT,
        "--search", ISSUE,
    ])
    rows = (data or {}).get("rows", [])
    for row in rows:
        if row.get("identifier") == ISSUE:
            return row
    return None


def search_prs() -> list[dict[str, Any]]:
    seen: dict[int, dict[str, Any]] = {}
    for query in (ISSUE, "1190"):
        data = run_json([
            "gh", "pr", "list",
            "--repo", REPO,
            "--state", "open",
            "--search", query,
            "--json", "number,title,url,headRefName,headRefOid,isDraft,reviewDecision,mergeStateStatus,updatedAt,author,labels",
        ], timeout=90)
        for pr in data or []:
            text = " ".join(str(pr.get(k, "")) for k in ("title", "headRefName", "url"))
            if ISSUE in text or "1190" in text:
                seen[int(pr["number"])] = pr
    return list(seen.values())


def pr_details(number: int) -> dict[str, Any]:
    return run_json([
        "gh", "pr", "view", str(number),
        "--repo", REPO,
        "--json", "number,title,url,body,headRefOid,comments,reviews,statusCheckRollup,reviewDecision,mergeStateStatus,updatedAt,author,isDraft",
    ], timeout=90) or {}


def text_items(details: dict[str, Any]) -> list[tuple[str, str, str]]:
    items: list[tuple[str, str, str]] = []
    for c in details.get("comments") or []:
        author = ((c.get("author") or {}).get("login") or "")
        items.append(("comment", author, c.get("body") or ""))
    for r in details.get("reviews") or []:
        author = ((r.get("author") or {}).get("login") or "")
        body = r.get("body") or ""
        state = r.get("state") or ""
        items.append((f"review:{state}", author, body))
    return items


def has_codex_signal(details: dict[str, Any]) -> bool:
    for kind, author, body in text_items(details):
        if CODEX_RE.search(author) or CODEX_RE.search(body) or CODEX_RE.search(kind):
            return True
    return False


def codex_budget_hits(details: dict[str, Any]) -> list[str]:
    hits: list[str] = []
    for kind, author, body in text_items(details):
        haystack = f"{kind}\n{author}\n{body}"
        if BUDGET_RE.search(haystack):
            snippet = " ".join(body.split())[:280]
            hits.append(f"{kind} by {author or 'unknown'}: {snippet}")
    return hits


def failing_checks(details: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for check in details.get("statusCheckRollup") or []:
        name = check.get("name") or check.get("context") or check.get("workflowName") or "check"
        conclusion = (check.get("conclusion") or check.get("state") or check.get("status") or "").upper()
        if conclusion in {"FAILURE", "FAILED", "ERROR", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED"}:
            failures.append(f"{name}: {conclusion}")
    return failures


def main() -> int:
    state = load_state()
    alerts: list[str] = []

    try:
        issue = get_issue_row()
        if not issue:
            alert_once(state, f"{ISSUE}:missing", f"⚠️ {ISSUE} was not found in Linear project Doc Thingy during PR monitoring.", alerts)
        else:
            labels = {x.strip().lower() for x in str(issue.get("labels") or "").split(",") if x.strip()}
            if "autobuild" not in labels:
                alert_once(state, f"{ISSUE}:missing-autobuild", f"⚠️ {ISSUE} is missing the `autobuild` label, so the shared Autobuild PR nudge monitor may not act on it.", alerts)
            state.setdefault("issue", {})["last_seen"] = {
                "state": issue.get("state"),
                "labels": issue.get("labels"),
                "updatedAt": issue.get("updatedAt"),
                "checkedAt": now().isoformat(),
            }

        prs = search_prs()
        state_prs = state.setdefault("prs", {})
        open_numbers = {str(pr["number"]) for pr in prs}
        state["last_open_prs"] = sorted(open_numbers)

        for pr in prs:
            number = int(pr["number"])
            key = str(number)
            details = pr_details(number)
            head = details.get("headRefOid") or pr.get("headRefOid") or "unknown"
            url = details.get("url") or pr.get("url")
            title = details.get("title") or pr.get("title")
            existing = state_prs.get(key, {})
            head_state = existing.get("heads", {}).get(head, {})
            first_seen = head_state.get("first_seen")
            if not first_seen:
                first_seen = now().isoformat()
                state_prs.setdefault(key, {}).setdefault("heads", {})[head] = {"first_seen": first_seen}
                alerts.append(
                    f"🔎 {ISSUE} PR detected: #{number} — {title}\n{url}\n"
                    f"Review decision: {details.get('reviewDecision') or 'unknown'}; merge state: {details.get('mergeStateStatus') or 'unknown'}."
                )

            budget_hits = codex_budget_hits(details)
            if budget_hits:
                alert_once(
                    state,
                    f"pr-{number}:{head}:codex-budget",
                    f"⚠️ Codex may be unavailable/out of budget on {ISSUE} PR #{number}. Fallback review likely needed.\n{url}\n" + "\n".join(f"- {h}" for h in budget_hits[:3]),
                    alerts,
                )

            if not has_codex_signal(details):
                try:
                    age = (now() - datetime.fromisoformat(first_seen)).total_seconds()
                except Exception:
                    age = 0
                if age >= REVIEW_WAIT_SECONDS:
                    alert_once(
                        state,
                        f"pr-{number}:{head}:codex-missing-30m",
                        f"⚠️ {ISSUE} PR #{number} has had no detectable Codex review signal for 30+ minutes. Consider Hermes/gh-based review fallback.\n{url}",
                        alerts,
                    )

            decision = details.get("reviewDecision") or ""
            if decision == "CHANGES_REQUESTED":
                alert_once(
                    state,
                    f"pr-{number}:{head}:changes-requested",
                    f"🔁 {ISSUE} PR #{number} has CHANGES_REQUESTED and should be watched for Rework/follow-up.\n{url}",
                    alerts,
                )

            failures = failing_checks(details)
            if failures:
                alert_once(
                    state,
                    f"pr-{number}:{head}:checks-failing:{'|'.join(failures[:5])}",
                    f"❌ {ISSUE} PR #{number} has failing checks.\n{url}\n" + "\n".join(f"- {f}" for f in failures[:8]),
                    alerts,
                )

            state_prs.setdefault(key, {})["last_seen"] = {
                "head": head,
                "url": url,
                "title": title,
                "reviewDecision": details.get("reviewDecision"),
                "mergeStateStatus": details.get("mergeStateStatus"),
                "hasCodexSignal": has_codex_signal(details),
                "checkedAt": now().isoformat(),
            }

        # If PRs close, keep state but report once for visibility.
        for key, rec in list(state_prs.items()):
            if key not in open_numbers and rec.get("last_seen") and not rec.get("closed_reported"):
                rec["closed_reported"] = now().isoformat()
                last = rec.get("last_seen") or {}
                alerts.append(f"✅ {ISSUE} PR #{key} is no longer open. Last seen: {last.get('url', '')}")

        state["last_check"] = now().isoformat()
        save_state(state)

        if os.environ.get("REPORT_STATUS") == "1":
            print(json.dumps({"issue": issue, "open_prs": prs, "state_path": str(STATE_PATH)}, indent=2))
        elif alerts:
            print("\n\n".join(alerts))
        return 0
    except Exception as exc:
        # Non-zero makes cron alert if the watchdog itself breaks.
        print(f"NOD-1190 PR review watch failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
