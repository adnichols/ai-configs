#!/usr/bin/env python3
"""Start a WKS workstream owner: a Paseo worktree workspace and a top-level agent in it, both titled `WKS <name>`.

The orchestrator finds owners by that title (nod-fleet `wks_nudge.py`: a workspace whose name starts with `WKS `, and the
live agent at its cwd, top-level agents first), so the title, the worktree isolation and the missing parent are fixed here.

    start_wks.py --name NAME --source URL [--source URL]... [--checkout PATH] [--base main] [--note TEXT]
                 [--model ID] [--thinking ID] [--dry-run]

  1. Refuse, creating nothing, when a workspace titled `WKS <name>` exists on this host or on another host in
     ~/.config/orchestrate/hosts.json, or branch `wks/<slug>` exists in the checkout or on origin. A host that cannot be
     listed is named in `unchecked_hosts` instead.
  2. `git fetch origin <base>`. The owner's branch starts at origin/<base>.
  3. `paseo workspace create --isolation worktree --mode branch-off --new-branch wks/<slug> --worktree-slug wks-<slug>
     --base origin/<base> --path <checkout> --title "WKS <name>" --no-background --json`.
  4. `paseo run --no-wait --json --workspace <id> --title "WKS <name>" ...` with assets/owner-brief.md as the prompt and
     PASEO_AGENT_ID removed from its environment: run from inside an agent, `paseo run` makes the new agent that agent's
     subagent otherwise.
  5. `paseo inspect`: the requested provider, model, thinking and mode, the workspace's cwd, and no ParentAgentId.
  6. `paseo heartbeat create --cron "*/30 * * * *" --name "WKS <name> progress"` with assets/progress-heartbeat.md as the
     prompt and the owner's id in PASEO_AGENT_ID, which is how that command names the agent it prompts. Paseo skips a
     firing while the owner is in a turn, so the heartbeat reaches an idle owner only, and completes it when the owner is
     archived. Any failure or interruption in steps 3 to 6 archives the workspace titled `WKS <name>` (found by title
     when the create's outcome is unknown) and deletes the branch while it is still at the base commit.
  7. Pin the workspace to Paseo's sidebar with pin_workspace.mjs, run beside the installed paseo CLI. The pin is for
     the operator to find the owner; a pin that fails or is interrupted is reported in `pin_error`, and the start
     stands.

Prints one JSON object on stdout. Exit codes: 0 started (or the --dry-run plan), 1 usage, 2 refused (nothing created),
3 failed (what this run created was removed, except what `left` lists).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
BRIEF = SKILL_DIR / "assets" / "owner-brief.md"
HEARTBEAT = SKILL_DIR / "assets" / "progress-heartbeat.md"
HEARTBEAT_CRON = "*/30 * * * *"
PIN_SCRIPT = SKILL_DIR / "scripts" / "pin_workspace.mjs"
HOSTS_FILE = Path("~/.config/orchestrate/hosts.json")
# The configuration of the WKS owners running when this skill was written; --model and --thinking override.
PROVIDER, MODEL, THINKING, MODE = "omp", "anthropic/claude-opus-5-5", "high", "full"
CALLER_ENV = ("PASEO_AGENT_ID", "PASEO_AGENT_CWD")
REMOTE_TIMEOUT = 30


class Refused(Exception):
    """Nothing was created."""


class Failed(Exception):
    """Creation began; the caller rolls it back."""


class Parser(argparse.ArgumentParser):
    def error(self, message: str):
        self.print_usage(sys.stderr)
        print(json.dumps({"result": "usage", "error": message}, indent=2))
        sys.exit(1)


def interrupt(signum, frame):
    raise KeyboardInterrupt(signal.Signals(signum).name)


def run(cmd: list[str], env: dict[str, str] | None = None, timeout: int = 300) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=timeout)
    except FileNotFoundError:
        return subprocess.CompletedProcess(cmd, 127, "", f"{cmd[0]}: command not found")
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, 124, "", f"{' '.join(cmd[:3])}: timed out")


def tail(p: subprocess.CompletedProcess) -> str:
    return (p.stderr.strip() or p.stdout.strip())[-400:]


def git(checkout: Path, *args: str) -> subprocess.CompletedProcess:
    return run(["git", "-C", str(checkout), *args])


def parse_json(p: subprocess.CompletedProcess, what: str):
    try:
        return json.loads(p.stdout)
    except ValueError:
        raise Failed(f"{what} did not print JSON: {tail(p)}")


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:48].rstrip("-")


def main_checkout(path: Path) -> Path:
    p = git(path, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if p.returncode:
        raise Refused(f"{path} is not in a git checkout: {tail(p)}")
    common = Path(p.stdout.strip())
    if common.name != ".git":
        raise Refused(f"{path}: no main checkout owns git dir {common}")
    return common.parent


def fleet() -> tuple[str, dict[str, str]]:
    """This host's name in the orchestrate hosts file (matched by `hostnames`, else the short hostname) and the
    `--host` targets of the other hosts there."""
    me = socket.gethostname().lower().split(".")[0]
    try:
        hosts = json.loads(HOSTS_FILE.expanduser().read_text())["hosts"]
    except (OSError, ValueError, KeyError, TypeError):
        return me, {}
    name = next((h["name"] for h in hosts if me in [n.lower() for n in h.get("hostnames", [])]), me)
    return name, {h["name"]: h["target"] for h in hosts if h.get("target") and h.get("name") != name}


def list_workspaces(target: str | None = None) -> list[dict]:
    """Every workspace on this host's daemon (or `target`'s), background ones included. Raises Refused."""
    cmd = ["paseo", "workspace", "ls", "--json", "--background"] + (["--host", target] if target else [])
    p = run(cmd, timeout=REMOTE_TIMEOUT if target else 300)
    if p.returncode:
        raise Refused(f"{' '.join(cmd)} failed: {tail(p)}")
    try:
        return json.loads(p.stdout)
    except ValueError:
        raise Refused(f"{' '.join(cmd)} did not print JSON: {tail(p)}")


def titled(workspaces: list[dict], title: str) -> list[dict]:
    return [w for w in workspaces if (w.get("name") or "").strip().casefold() == title.casefold()]


def remote_titled(host: str, target: str, title: str) -> tuple[list[dict], str | None]:
    """Workspaces titled `title` on another host, and why that host could not be listed."""
    try:
        return [dict(w, host=host) for w in titled(list_workspaces(target), title)], None
    except Refused as e:
        return [], f"{host}: {e}"


def render(path: Path, fields: dict[str, str]) -> str:
    template = path.read_text()
    for key, value in fields.items():
        template = template.replace("{{" + key + "}}", value)
    left = re.findall(r"\{\{[A-Z_]+\}\}", template)
    if left:
        raise Refused(f"{path} has fields this script does not fill: {', '.join(sorted(set(left)))}")
    return template


def preflight(args: argparse.Namespace) -> dict:
    name = " ".join(args.name.split())
    slug = slugify(name)
    if not slug:
        raise Refused(f"--name {args.name!r} has no letters or digits to name a branch with")
    title, branch = f"WKS {name}", f"wks/{slug}"
    checkout = main_checkout(Path(args.checkout or os.getcwd()).expanduser())
    host, others = fleet()

    same = titled(list_workspaces(), title)
    unchecked = []
    with ThreadPoolExecutor() as pool:
        for found, error in pool.map(lambda item: remote_titled(*item, title), others.items()):
            same += found
            unchecked += [error] if error else []
    if same:
        w = same[0]
        raise Refused(f"workspace {w.get('workspaceId')} on {w.get('host', host)} is already titled {w.get('name')!r} "
                      f"({w.get('cwd')}); a workstream has one WKS workspace")

    if git(checkout, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}").returncode == 0:
        raise Refused(f"branch {branch} already exists in {checkout}")
    p = git(checkout, "fetch", "--quiet", "origin", args.base)
    if p.returncode:
        raise Refused(f"git fetch origin {args.base} failed in {checkout}: {tail(p)}")
    p = git(checkout, "ls-remote", "--exit-code", "--heads", "origin", branch)
    if p.returncode == 0:
        raise Refused(f"branch {branch} already exists on origin")
    if p.returncode != 2:
        raise Refused(f"git ls-remote origin failed in {checkout}: {tail(p)}")
    p = git(checkout, "rev-parse", "--verify", f"refs/remotes/origin/{args.base}^{{commit}}")
    if p.returncode:
        raise Refused(f"origin/{args.base} does not resolve in {checkout}: {tail(p)}")

    return {"name": name, "slug": slug, "title": title, "branch": branch, "checkout": str(checkout),
            "base": args.base, "base_sha": p.stdout.strip(), "host": host, "unchecked_hosts": unchecked}


def create_workspace(plan: dict) -> dict:
    p = run(["paseo", "workspace", "create", "--isolation", "worktree", "--mode", "branch-off",
             "--new-branch", plan["branch"], "--worktree-slug", f"wks-{plan['slug']}", "--base", f"origin/{plan['base']}",
             "--path", plan["checkout"], "--title", plan["title"], "--no-background", "--json"])
    if p.returncode:
        raise Failed(f"paseo workspace create failed: {tail(p)}")
    ws = parse_json(p, "paseo workspace create")
    if not ws.get("workspaceId") or not ws.get("cwd"):
        raise Failed(f"paseo workspace create printed no workspaceId or cwd: {p.stdout.strip()[:300]}")
    return ws


def start_owner(plan: dict, ws: dict, args: argparse.Namespace, brief: str) -> str:
    env = {k: v for k, v in os.environ.items() if k not in CALLER_ENV}
    p = run(["paseo", "run", "--no-wait", "--json", "--workspace", ws["workspaceId"], "--title", plan["title"],
             "--provider", PROVIDER, "--model", args.model, "--thinking", args.thinking, "--mode", MODE, brief], env=env)
    if p.returncode:
        raise Failed(f"paseo run failed: {tail(p)}")
    agent = parse_json(p, "paseo run").get("agentId")
    if not agent:
        raise Failed(f"paseo run printed no agentId: {p.stdout.strip()[:300]}")
    return agent


def verify(agent: str, ws: dict, args: argparse.Namespace) -> None:
    p = run(["paseo", "inspect", agent, "--json"])
    if p.returncode:
        raise Failed(f"paseo inspect {agent} failed: {tail(p)}")
    info = parse_json(p, "paseo inspect")
    want = {"Provider": PROVIDER, "Model": args.model, "Thinking": args.thinking, "Mode": MODE}
    problems = [f"{k} is {info.get(k)!r}, want {v!r}" for k, v in want.items() if info.get(k) != v]
    if (info.get("Cwd") or "").rstrip("/") != ws["cwd"].rstrip("/"):
        problems.append(f"Cwd is {info.get('Cwd')!r}, want {ws['cwd']!r}")
    if info.get("ParentAgentId"):
        problems.append(f"ParentAgentId is {info['ParentAgentId']}, want none: the owner must not be a subagent")
    if problems:
        raise Failed(f"agent {agent} is misplaced: {'; '.join(problems)}")


def add_heartbeat(plan: dict, agent: str, prompt: str) -> str:
    """Create the owner's progress heartbeat and return its id."""
    env = dict(os.environ, PASEO_AGENT_ID=agent)
    p = run(["paseo", "heartbeat", "create", "--json", "--cron", HEARTBEAT_CRON, "--name", f"{plan['title']} progress",
             prompt], env=env)
    if p.returncode:
        raise Failed(f"paseo heartbeat create failed: {tail(p)}")
    row = parse_json(p, "paseo heartbeat create")
    if not row.get("id"):
        raise Failed(f"paseo heartbeat create printed no id: {p.stdout.strip()[:300]}")
    # The row names the target as `agent:<first 7 of its id>`.
    if row.get("target") != f"agent:{agent[:7]}":
        gone = run(["paseo", "schedule", "delete", row["id"]])
        kept = f"; delete it with `paseo schedule delete {row['id']}`: {tail(gone)}" if gone.returncode else ""
        raise Failed(f"heartbeat {row['id']} targets {row.get('target')!r}, not the owner {agent}{kept}")
    return row["id"]


def paseo_node() -> tuple[list[str], dict[str, str]]:
    """The command that runs a Node script beside the installed paseo CLI, and the environment it adds, which names the
    CLI's dist directory in PASEO_CLI_DIST. Raises OSError for an install it does not recognize."""
    exe = shutil.which("paseo")
    if not exe:
        raise OSError("paseo is not on PATH")
    cli = Path(exe).resolve().parent.parent
    # npm global install: <prefix>/lib/node_modules/@getpaseo/cli/bin/paseo, a node script.
    if (cli / "dist" / "utils" / "client.js").is_file():
        return ["node"], {"PASEO_CLI_DIST": str(cli / "dist")}
    # Desktop app: Resources/bin/paseo runs the CLI from app.asar in the app's own executable (the Electron helper on
    # macOS, Paseo.bin or Paseo on Linux), as that launcher does.
    app = cli.parent
    runner = cli / "app.asar.unpacked" / "dist" / "daemon" / "node-entrypoint-runner.js"
    electron = [e for e in (app / "Frameworks" / "Paseo Helper.app" / "Contents" / "MacOS" / "Paseo Helper",
                            app / "Paseo.bin", app / "Paseo") if e.is_file()]
    if electron and runner.is_file():
        return ([str(electron[0]), "--disable-warning=DEP0040", str(runner), "node-script"],
                {"PASEO_CLI_DIST": str(cli / "app.asar" / "node_modules" / "@getpaseo" / "cli" / "dist"),
                 "ELECTRON_RUN_AS_NODE": "1", "PASEO_NODE_ENV": "production"})
    raise OSError(f"no paseo CLI dist found for {Path(exe).resolve()}")


def pin(ws: dict) -> str | None:
    """Pin the workspace to Paseo's sidebar. Returns why it could not, or None. Never raises: the owner has started,
    and an error or interrupt here must not lose the report of it."""
    try:
        prefix, extra = paseo_node()
        p = run([*prefix, str(PIN_SCRIPT), ws["workspaceId"]], env=dict(os.environ, **extra), timeout=REMOTE_TIMEOUT)
    except OSError as e:
        return str(e)
    except BaseException as e:
        return f"{type(e).__name__}: {e}" if str(e) else type(e).__name__
    if p.returncode:
        return tail(p) or f"exit {p.returncode}"
    return None


def roll_back(plan: dict, ws: dict | None) -> list[str]:
    """Archive the workspace this run created and delete its branch while it holds no commit past the base. Without
    `ws` (the create's outcome is unknown) the workspace is found by title: preflight found none, so any is this run's.
    Returns what is left."""
    branch, checkout = plan["branch"], Path(plan["checkout"])
    kept = f"branch {branch} in {checkout}: kept while its worktree may remain"
    if ws is None:
        try:
            found = titled(list_workspaces(), plan["title"])
            if not found:  # an interrupted create can still land in the daemon after the client is gone
                time.sleep(5)
                found = titled(list_workspaces(), plan["title"])
        except Refused as e:
            return [f"any workspace titled {plan['title']!r}: {e}", kept]
    else:
        found = [ws]
    left = []
    for w in found:
        p = run(["paseo", "workspace", "archive", w["workspaceId"]])
        if p.returncode:
            left.append(f"workspace {w['workspaceId']} ({w.get('cwd')}): paseo workspace archive failed: {tail(p)}")
    if left:
        return left + [kept]
    tip = git(checkout, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}").stdout.strip()
    if tip == plan["base_sha"]:
        p = git(checkout, "branch", "-D", branch)
        if p.returncode:
            left.append(f"branch {branch} in {checkout}: {tail(p)}")
    elif tip:
        left.append(f"branch {branch} in {checkout} is at {tip}, not the base {plan['base_sha']}; kept")
    return left


def main(argv: list[str] | None = None) -> int:
    ap = Parser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", required=True, help="the workstream's topic; the workspace and agent become `WKS <name>`")
    ap.add_argument("--source", action="append", required=True, help="a source document URL or path (repeatable)")
    ap.add_argument("--checkout", help="the repository's main checkout (default: the one holding the current directory)")
    ap.add_argument("--base", default="main", help="the branch the owner starts from and merges to (default: main)")
    ap.add_argument("--note", action="append", default=[], help="an operator instruction the documents lack (repeatable)")
    ap.add_argument("--model", default=MODEL, help=f"the owner's model (default: {MODEL})")
    ap.add_argument("--thinking", default=THINKING, help=f"the owner's thinking option (default: {THINKING})")
    ap.add_argument("--dry-run", action="store_true", help="check and print the plan and brief; create nothing")
    args = ap.parse_args(argv)

    def emit(code: int, **report) -> int:
        print(json.dumps(report, indent=2))
        return code

    try:
        plan = preflight(args)
        fields = {"NAME": plan["name"], "SOURCES": "\n".join(f"- {s}" for s in args.source),
                  "NOTES": " ".join(args.note) or "none", "HOST": plan["host"], "BRANCH": plan["branch"],
                  "BASE": plan["base"], "BASE_SHA": plan["base_sha"], "CHECKOUT": plan["checkout"]}
        preview = render(BRIEF, dict(fields, WORKSPACE="<new workspace>", WORKTREE="<new worktree>"))
        heartbeat_prompt = render(HEARTBEAT, {"NAME": plan["name"], "CRON": HEARTBEAT_CRON})
    except (Refused, OSError) as e:
        print(f"start_wks.py: refused: {e}", file=sys.stderr)
        return emit(2, result="refused", error=str(e))
    if args.dry_run:
        return emit(0, result="dry-run", **plan, model=args.model, thinking=args.thinking, brief=preview,
                    heartbeat_cron=HEARTBEAT_CRON, heartbeat_prompt=heartbeat_prompt)

    # From here a hangup or kill must still roll back, as an exception does.
    signal.signal(signal.SIGTERM, interrupt)
    signal.signal(signal.SIGHUP, interrupt)
    ws = agent = None
    try:
        ws = create_workspace(plan)
        brief = render(BRIEF, dict(fields, WORKSPACE=ws["workspaceId"], WORKTREE=ws["cwd"]))
        agent = start_owner(plan, ws, args, brief)
        verify(agent, ws, args)
        heartbeat = add_heartbeat(plan, agent, heartbeat_prompt)
    except BaseException as e:
        error = str(e) if isinstance(e, (Failed, Refused)) else f"{type(e).__name__}: {e}"
        left = roll_back(plan, ws)
        print(f"start_wks.py: failed: {error}", file=sys.stderr)
        return emit(3, result="failed", error=error, agent=agent, workspace=ws and ws["workspaceId"], left=left)

    pin_error = pin(ws)
    return emit(0, result="started", agent=agent, workspace=ws["workspaceId"], title=plan["title"], worktree=ws["cwd"],
                branch=plan["branch"], base=plan["base"], base_sha=plan["base_sha"], host=plan["host"],
                model=args.model, thinking=args.thinking, unchecked_hosts=plan["unchecked_hosts"],
                heartbeat=heartbeat, pinned=pin_error is None, pin_error=pin_error)


if __name__ == "__main__":
    sys.exit(main())
