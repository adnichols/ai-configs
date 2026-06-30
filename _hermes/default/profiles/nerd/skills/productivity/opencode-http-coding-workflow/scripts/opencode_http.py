#!/usr/bin/env python3
"""Small stdlib OpenCode HTTP API helper for Hermes workflows.

Default server: http://localhost:63333
Override with OPENCODE_SERVER.

The helper intentionally avoids /config dumps and prints compact JSON/text suitable for
Hermes tool outputs.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import string
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

DEFAULT_BASE = "http://localhost:63333"


def base_url() -> str:
    return os.environ.get("OPENCODE_SERVER", DEFAULT_BASE).rstrip("/")


def request(method: str, path: str, *, query: dict[str, Any] | None = None, body: Any = None, timeout: int = 30) -> Any:
    url = base_url() + path
    if query:
        clean = {k: v for k, v in query.items() if v is not None}
        if clean:
            url += "?" + urllib.parse.urlencode(clean, doseq=True)

    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            ctype = resp.headers.get("Content-Type", "")
            if "application/json" in ctype:
                return json.loads(raw) if raw else None
            return raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        raise SystemExit(f"HTTP {e.code} {method} {url}: {raw[:2000]}") from e
    except urllib.error.URLError as e:
        raise SystemExit(f"Connection failed for {method} {url}: {e}") from e


def request_result(method: str, path: str, *, query: dict[str, Any] | None = None, body: Any = None, timeout: int = 30) -> tuple[bool, int | None, Any]:
    """Like request(), but return HTTP errors to the caller for recoverable APIs.

    Some experimental OpenCode workspace endpoints have been observed to return
    HTTP 500 after successfully creating the workspace because a follow-up global
    event timed out. Workspace creation uses this helper so callers can verify by
    listing workspaces instead of incorrectly treating the attempt as definitely
    failed.
    """
    url = base_url() + path
    if query:
        clean = {k: v for k, v in query.items() if v is not None}
        if clean:
            url += "?" + urllib.parse.urlencode(clean, doseq=True)

    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            if "application/json" in resp.headers.get("Content-Type", ""):
                return True, resp.status, json.loads(raw) if raw else None
            return True, resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            value: Any = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            value = raw
        return False, e.code, value
    except urllib.error.URLError as e:
        raise SystemExit(f"Connection failed for {method} {url}: {e}") from e


def print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False))


def generated_workspace_id() -> str:
    """Return an OpenCode-compatible workspace id.

    The HTTP API requires the client to submit an id beginning with ``wrk``.
    This is not the user-facing workspace name; OpenCode still generates the
    display name, branch, and directory for worktree workspaces.
    """
    alphabet = string.ascii_letters + string.digits
    return "wrk_" + "".join(secrets.choice(alphabet) for _ in range(24))


def repo_query(args: argparse.Namespace) -> dict[str, Any]:
    return {"directory": getattr(args, "repo", None), "workspace": getattr(args, "workspace", None)}


def cmd_health(args: argparse.Namespace) -> None:
    print_json(request("GET", "/global/health", timeout=args.timeout))


def cmd_sessions(args: argparse.Namespace) -> None:
    query = repo_query(args)
    query.update({"limit": args.limit, "search": args.search, "archived": args.archived})
    sessions = request("GET", "/session", query=query, timeout=args.timeout)
    if args.raw:
        print_json(sessions)
        return
    rows = []
    for s in sessions[: args.limit if args.limit else len(sessions)]:
        rows.append({
            "id": s.get("id"),
            "title": s.get("title"),
            "agent": s.get("agent"),
            "directory": s.get("directory"),
            "updated": (s.get("time") or {}).get("updated"),
            "summary": s.get("summary"),
        })
    print_json(rows)


def cmd_create(args: argparse.Namespace) -> None:
    body: dict[str, Any] = {"title": args.title}
    if args.agent:
        body["agent"] = args.agent
    if args.model:
        # Accept provider/model or just model; OpenCode tolerates model strings in many contexts.
        if "/" in args.model:
            provider, model = args.model.split("/", 1)
            body["model"] = {"providerID": provider, "modelID": model}
        else:
            body["model"] = args.model
    if args.parent:
        body["parentID"] = args.parent
    session = request("POST", "/session", query=repo_query(args), body=body, timeout=args.timeout)
    print_json(session)


def cmd_messages(args: argparse.Namespace) -> None:
    query = repo_query(args)
    query.update({"limit": args.limit, "before": args.before})
    messages = request("GET", f"/session/{args.session}/message", query=query, timeout=args.timeout)
    if args.raw:
        print_json(messages)
        return
    compact = []
    for msg in messages:
        info = msg.get("info", {})
        text_parts = []
        tool_parts = []
        for part in msg.get("parts", []):
            ptype = part.get("type")
            if ptype == "text":
                text_parts.append(part.get("text", ""))
            elif ptype not in {"step-start", "step-finish"}:
                tool_parts.append({k: part.get(k) for k in ("type", "id", "tool", "state") if k in part})
        compact.append({
            "id": info.get("id"),
            "role": info.get("role"),
            "agent": info.get("agent"),
            "finish": info.get("finish"),
            "created": (info.get("time") or {}).get("created"),
            "completed": (info.get("time") or {}).get("completed"),
            "text": "\n".join(text_parts),
            "other_parts": tool_parts,
        })
    print_json(compact)


def cmd_prompt(args: argparse.Namespace) -> None:
    if args.text == "-":
        text = sys.stdin.read()
    else:
        text = args.text
    body: dict[str, Any] = {"parts": [{"type": "text", "text": text}]}
    if args.agent:
        body["agent"] = args.agent
    if args.model:
        body["model"] = args.model
    if args.variant:
        body["variant"] = args.variant
    if args.no_reply:
        body["noReply"] = True
    result = request("POST", f"/session/{args.session}/message", query=repo_query(args), body=body, timeout=args.timeout)
    print_json(result)


def cmd_wait(args: argparse.Namespace) -> None:
    """Poll messages until the latest assistant message appears completed or timeout expires."""
    deadline = time.time() + args.seconds
    last = None
    while time.time() < deadline:
        messages = request("GET", f"/session/{args.session}/message", query=repo_query(args), timeout=args.timeout)
        assistants = [m for m in messages if (m.get("info") or {}).get("role") == "assistant"]
        if assistants:
            latest = assistants[-1]
            info = latest.get("info") or {}
            last = latest
            if info.get("time", {}).get("completed") or info.get("finish"):
                print_json(latest if args.raw else {
                    "id": info.get("id"),
                    "finish": info.get("finish"),
                    "completed": info.get("time", {}).get("completed"),
                    "text": "\n".join(p.get("text", "") for p in latest.get("parts", []) if p.get("type") == "text"),
                })
                return
        time.sleep(args.interval)
    if last is not None:
        print_json({"timeout": True, "last_assistant_id": (last.get("info") or {}).get("id")})
    else:
        print_json({"timeout": True, "last_assistant_id": None})
    raise SystemExit(124)


def cmd_workspace_adapters(args: argparse.Namespace) -> None:
    print_json(request("GET", "/experimental/workspace/adapter", query=repo_query(args), timeout=args.timeout))


def cmd_workspace_list(args: argparse.Namespace) -> None:
    print_json(request("GET", "/experimental/workspace", query=repo_query(args), timeout=args.timeout))


def cmd_workspace_status(args: argparse.Namespace) -> None:
    print_json(request("GET", "/experimental/workspace/status", query=repo_query(args), timeout=args.timeout))


def cmd_workspace_create(args: argparse.Namespace) -> None:
    workspace_id = args.id or generated_workspace_id()
    if not workspace_id.startswith("wrk"):
        raise SystemExit("ERROR workspace id must start with 'wrk' (OpenCode API requirement)")
    extra = json.loads(args.extra_json) if args.extra_json else {}
    body: dict[str, Any] = {"id": workspace_id, "type": args.type, "extra": extra}
    if args.branch:
        body["branch"] = args.branch
    ok, status, value = request_result("POST", "/experimental/workspace", query=repo_query(args), body=body, timeout=args.timeout)
    if ok:
        print_json(value)
        return

    # Experimental OpenCode 1.14.x may create the worktree, then return 500
    # while waiting for a global event. Recover by listing and matching the id.
    workspaces = request("GET", "/experimental/workspace", query=repo_query(args), timeout=args.timeout)
    for workspace in workspaces:
        if workspace.get("id") == workspace_id:
            workspace["_warning"] = f"create returned HTTP {status}; verified workspace exists by id"
            workspace["_create_error"] = value
            print_json(workspace)
            return
    print_json({"ok": False, "status": status, "error": value})
    raise SystemExit(1)


def cmd_workspace_delete(args: argparse.Namespace) -> None:
    encoded = urllib.parse.quote(args.id, safe="")
    print_json(request("DELETE", f"/experimental/workspace/{encoded}", query=repo_query(args), timeout=args.timeout))


def cmd_worktree_list(args: argparse.Namespace) -> None:
    print_json(request("GET", "/experimental/worktree", query=repo_query(args), timeout=args.timeout))


def cmd_worktree_create(args: argparse.Namespace) -> None:
    print_json(request("POST", "/experimental/worktree", query=repo_query(args), body={}, timeout=args.timeout))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="OpenCode HTTP helper")
    p.add_argument("--timeout", type=int, default=30)
    sub = p.add_subparsers(dest="cmd", required=True)

    h = sub.add_parser("health")
    h.set_defaults(func=cmd_health)

    s = sub.add_parser("sessions")
    s.add_argument("--repo")
    s.add_argument("--workspace")
    s.add_argument("--limit", type=int, default=10)
    s.add_argument("--search")
    s.add_argument("--archived")
    s.add_argument("--raw", action="store_true")
    s.set_defaults(func=cmd_sessions)

    c = sub.add_parser("create")
    c.add_argument("--repo")
    c.add_argument("--workspace")
    c.add_argument("--title", required=True)
    c.add_argument("--agent", default="build")
    c.add_argument("--model")
    c.add_argument("--parent")
    c.set_defaults(func=cmd_create)

    m = sub.add_parser("messages")
    m.add_argument("--repo")
    m.add_argument("--workspace")
    m.add_argument("--session", required=True)
    m.add_argument("--limit", type=int, default=20)
    m.add_argument("--before")
    m.add_argument("--raw", action="store_true")
    m.set_defaults(func=cmd_messages)

    pr = sub.add_parser("prompt")
    pr.add_argument("--repo")
    pr.add_argument("--workspace")
    pr.add_argument("--session", required=True)
    pr.add_argument("--agent")
    pr.add_argument("--model")
    pr.add_argument("--variant")
    pr.add_argument("--no-reply", action="store_true", help="Append user message without requesting assistant reply, if supported")
    pr.add_argument("--text", required=True, help="Prompt text, or '-' to read stdin")
    pr.set_defaults(func=cmd_prompt)

    w = sub.add_parser("wait")
    w.add_argument("--repo")
    w.add_argument("--workspace")
    w.add_argument("--session", required=True)
    w.add_argument("--seconds", type=int, default=300)
    w.add_argument("--interval", type=float, default=5.0)
    w.add_argument("--raw", action="store_true")
    w.set_defaults(func=cmd_wait)

    wa = sub.add_parser("workspace-adapters", help="List experimental OpenCode workspace adapters")
    wa.add_argument("--repo", required=True)
    wa.add_argument("--workspace")
    wa.set_defaults(func=cmd_workspace_adapters)

    wl = sub.add_parser("workspace-list", help="List experimental OpenCode workspaces for a repo")
    wl.add_argument("--repo", required=True)
    wl.add_argument("--workspace")
    wl.set_defaults(func=cmd_workspace_list)

    ws = sub.add_parser("workspace-status", help="List experimental OpenCode workspace status for a repo")
    ws.add_argument("--repo", required=True)
    ws.add_argument("--workspace")
    ws.set_defaults(func=cmd_workspace_status)

    wc = sub.add_parser("workspace-create", help="Create an experimental OpenCode workspace via HTTP API")
    wc.add_argument("--repo", required=True, help="Primary repo checkout; do not pass an already-created worktree here")
    wc.add_argument("--workspace")
    wc.add_argument("--id", help="Optional client id; must start with 'wrk'. If omitted, helper generates an OpenCode-compatible id. This is not the display name.")
    wc.add_argument("--type", default="worktree")
    wc.add_argument("--branch", help="Optional requested branch. OpenCode usually generates opencode/<name>; verify and check out the issue branch inside the returned directory if needed.")
    wc.add_argument("--extra-json", help="JSON object passed as workspace extra metadata")
    wc.set_defaults(func=cmd_workspace_create)

    wd = sub.add_parser("workspace-delete", help="Delete an experimental OpenCode workspace by id")
    wd.add_argument("--repo", required=True)
    wd.add_argument("--workspace")
    wd.add_argument("--id", required=True)
    wd.set_defaults(func=cmd_workspace_delete)

    twl = sub.add_parser("worktree-list", help="List OpenCode-created worktree directories for a repo")
    twl.add_argument("--repo", required=True)
    twl.add_argument("--workspace")
    twl.set_defaults(func=cmd_worktree_list)

    twc = sub.add_parser("worktree-create", help="Create an OpenCode worktree via legacy experimental endpoint")
    twc.add_argument("--repo", required=True)
    twc.add_argument("--workspace")
    twc.set_defaults(func=cmd_worktree_create)

    return p


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
