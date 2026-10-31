"""Fake `paseo` for test_start_wks.py. State lives in the JSON file $START_WKS_FAKE_STATE.

It models the CLI behavior start_wks.py depends on:
- `workspace create` makes a real git worktree for `--isolation worktree`; a workspace created from inside an agent
  ($PASEO_AGENT_ID set) inherits background unless `--no-background` is passed.
- `workspace ls` hides background workspaces unless `--background` is passed, as the orchestrator's sweep sees them;
  `--host <target>` lists `remote[<target>]`, and a target missing there cannot be reached.
- `workspace archive` removes the worktree and its agents and leaves the branch.
- `run` makes the new agent the subagent of $PASEO_AGENT_ID when that is set.

One-shot faults: `create_fails` (the workspace is created, then the command fails), `commit_on_run` (the new agent
commits before inspect), `force` (overrides fields of the next agent, to model a misplaced launch).
"""

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

STATE = Path(os.environ["START_WKS_FAKE_STATE"])


def opt(args, name):
    return args[args.index(name) + 1] if name in args else None


def main(argv):
    state = json.loads(STATE.read_text())
    state["calls"].append(argv)
    out, code = None, 0
    if argv[:2] == ["workspace", "ls"]:
        target = opt(argv, "--host")
        if target and target not in state["remote"]:
            STATE.write_text(json.dumps(state))
            print(f"ssh: connect to host {target}: Connection refused", file=sys.stderr)
            return 1
        listed = state["remote"][target] if target else state["workspaces"]
        out = [w for w in listed if "--background" in argv or not w["background"]]
    elif argv[:2] == ["workspace", "create"]:
        path, isolation = opt(argv, "--path"), opt(argv, "--isolation") or "local"
        cwd = path
        if isolation == "worktree":
            cwd = str(Path(state["worktrees"]) / opt(argv, "--worktree-slug"))
            subprocess.run(["git", "-C", path, "worktree", "add", "-q", "-b", opt(argv, "--new-branch"), cwd,
                            opt(argv, "--base")], check=True, capture_output=True)
        background = "--no-background" not in argv and ("--background" in argv or "PASEO_AGENT_ID" in os.environ)
        out = {"workspaceId": f"wks_{uuid.uuid4().hex[:16]}", "project": "repo", "name": opt(argv, "--title"),
               "isolation": isolation, "cwd": cwd, "background": background, "checkout": path}
        state["workspaces"].append(out)
        if state.pop("create_fails", False):
            out, code = None, 1
    elif argv[:2] == ["workspace", "archive"]:
        ws = next(w for w in state["workspaces"] if w["workspaceId"] == argv[2])
        if ws["isolation"] == "worktree":
            subprocess.run(["git", "-C", ws["checkout"], "worktree", "remove", "--force", ws["cwd"]], check=True,
                           capture_output=True)
        state["workspaces"].remove(ws)
        state["agents"] = [a for a in state["agents"] if a["Cwd"] != ws["cwd"]]
        out = {"workspaceId": ws["workspaceId"], "status": "archived"}
    elif argv[0] == "run":
        ws = next(w for w in state["workspaces"] if w["workspaceId"] == opt(argv, "--workspace"))
        agent = {"Id": str(uuid.uuid4()), "Name": opt(argv, "--title"), "Provider": opt(argv, "--provider"),
                 "Model": opt(argv, "--model"), "Thinking": opt(argv, "--thinking"), "Mode": opt(argv, "--mode"),
                 "Cwd": ws["cwd"], "Status": "running", "ParentAgentId": os.environ.get("PASEO_AGENT_ID"), "Prompt": argv[-1]}
        agent.update(state.pop("force", {}))
        if state.pop("commit_on_run", False):
            subprocess.run(["git", "-C", ws["cwd"], "commit", "-q", "--allow-empty", "-m", "owner work"], check=True)
        state["agents"].append(agent)
        out = {"agentId": agent["Id"], "status": "running", "provider": agent["Provider"], "cwd": agent["Cwd"], "title": agent["Name"]}
    elif argv[0] == "inspect":
        out = next(a for a in state["agents"] if a["Id"] == argv[1])
    else:
        print(f"fake paseo: unsupported {argv}", file=sys.stderr)
        return 2
    STATE.write_text(json.dumps(state))
    if code:
        print("Error: request timed out", file=sys.stderr)
    else:
        print(json.dumps(out))
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
