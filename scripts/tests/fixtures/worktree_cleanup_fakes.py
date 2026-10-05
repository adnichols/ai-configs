#!/usr/bin/env python3
"""Stand-ins for gh, paseo, pnpm (lab CLI) and wrangler, driven by a JSON file at $FAKE_STATE.

Invoked as `worktree_cleanup_fakes.py <tool> args...` by shims that test_worktree_cleanup.py
writes to a temporary bin directory.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

STATE = Path(os.environ["FAKE_STATE"])


def load():
    return json.loads(STATE.read_text())


def save(state):
    STATE.write_text(json.dumps(state))


def out(value):
    print(json.dumps(value))


def fail(message, code=1) -> NoReturn:
    print(message, file=sys.stderr)
    sys.exit(code)


def flag(args, name):
    return args[args.index(name) + 1] if name in args else None


def gh(state, args):
    if args[:2] == ["repo", "view"]:
        return out({"nameWithOwner": "acme/widgets", "defaultBranchRef": {"name": "main"}})
    if args[:2] == ["pr", "list"]:
        head, base, listed = flag(args, "--head"), flag(args, "--base"), flag(args, "--state")
        prs = [p for p in state["prs"] if (head is None or p["headRefName"] == head) and (base is None or p["baseRefName"] == base)]
        if listed == "open":
            prs = [p for p in prs if p["state"] == "OPEN"]
        return out(prs)
    if args[:2] == ["pr", "view"]:
        match = [p for p in state["prs"] if p["url"] == args[2]]
        if not match:
            fail("no pull requests found")
        return print(match[0]["state"])
    fail(f"fake gh: unsupported {args}")


def paseo(state, args):
    if args[:2] == ["workspace", "ls"]:
        return out(state["workspaces"])
    if args[0] == "ls":
        return out(state["agents"])
    if args[:2] == ["workspace", "archive"]:
        ws = next((w for w in state["workspaces"] if w["workspaceId"] == args[2]), None)
        if ws is None:
            fail("workspace not found")
        state["workspaces"].remove(ws)
        if not state.get("archive_keeps_dir"):
            subprocess.run(["git", "-C", ws["repo"], "worktree", "remove", "--force", ws["cwd"]], check=True, capture_output=True)
        state["calls"].append(f"archive {args[2]}")
        return
    fail(f"fake paseo: unsupported {args}")


def pnpm(state, args):
    lab = args[args.index("--") + 1 :]
    cwd = Path.cwd()
    claim_file = cwd / ".ccore" / "lab-claim.json"
    print("$ node --experimental-strip-types scripts/lab.ts -- " + " ".join(lab))
    if lab[0] == "inspect":
        if state.get("inspect_fails_after_release") and state.get("released_once"):
            fail("manager unreachable")
        claim = state["lab_claim"]
        return out({"name": lab[1], "state": state["lab_state"], "claim": claim})
    if lab[0] == "release":
        state["calls"].append("release")
        state["released_once"] = True
        if state.get("release_fails"):
            fail("manager unreachable")
        claim = json.loads(claim_file.read_text())
        claim_file.unlink()
        released = []
        if state["lab_claim"] and state["lab_claim"]["status"] == "active" and not state.get("release_noop"):
            state["lab_claim"]["status"] = "released"
            released = [{"claim_id": claim["claim_id"], "lab": claim["lab"], "deprovisioning": state["deprovisions"]}]
            if state["deprovisions"]:
                state["lab_state"] = "deprovisioning"
        return out({"released": released})
    fail(f"fake lab: unsupported {lab}")


def wrangler(state, args):
    if state.get("account") != "e6d3e575b97001f8ad1a7e98e497afa5":
        fail("wrong account")
    if args[:2] == ["deployments", "list"]:
        if flag(args, "--name") not in state["workers"]:
            fail("This Worker does not exist on your account. [code: 10007]")
        return
    if args[0] == "delete":
        state["workers"].remove(flag(args, "--name"))
        state["calls"].append(f"delete worker {flag(args, '--name')}")
        return
    if args[:2] == ["d1", "list"]:
        return out([{"name": n} for n in state["d1"]])
    if args[:2] == ["d1", "export"]:
        Path(args[args.index("--output") + 1]).write_text("-- export\n")
        return
    if args[:2] == ["d1", "delete"]:
        state["d1"].remove(args[2])
        state["calls"].append(f"delete d1 {args[2]}")
        return
    fail(f"fake wrangler: unsupported {args}")


if __name__ == "__main__":
    state = load()
    state["account"] = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    tool = {"gh": gh, "paseo": paseo, "pnpm": pnpm, "wrangler": wrangler}[sys.argv[1]]
    tool(state, sys.argv[2:])
    state.pop("account")
    save(state)
