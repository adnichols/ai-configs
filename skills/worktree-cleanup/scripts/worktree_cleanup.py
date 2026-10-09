#!/usr/bin/env python3
"""Tear down a finished worktree in a fixed, resumable order.

Order: preflight, lab release, demos, workspace, remote branch. Anything that
needs the worktree's files (the lab claim credential, the demo manifest) runs
before the step that removes them. The script prints one JSON report on stdout
and progress on stderr.

Exit codes: 0 complete, 1 usage, 2 refused (nothing changed), 3 a step failed
(later steps did not run; the same command is safe to repeat), 4 finished what
this process may do but `remaining` lists work for someone else.
"""

from __future__ import annotations

import argparse
import fcntl
import glob
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

LABS_ACCOUNT_ID = "e6d3e575b97001f8ad1a7e98e497afa5"
LAB_CLI = ["pnpm", "--filter", "@ccore/lab-manager", "run", "lab", "--"]
CLAIM_FILE = ".ccore/lab-claim.json"
DEMO_MANIFESTS = "artifacts/verified-build/*/demos.json"
DEMO_NOTES = "artifacts/verified-build/**/*.md"
DEMO_URL = re.compile(r"https://([a-z0-9][a-z0-9-]*)\.demos\.keramos\.tech")
ABSENT_WORKER = ("10007", "10090", "does not exist")
PR_FIELDS = "number,state,headRefOid,url,headRepositoryOwner"


class Refused(Exception):
    """Preflight found a reason to change nothing."""


class StepFailed(Exception):
    """A step did not finish; later steps must not run."""


@dataclass
class Proc:
    code: int
    out: str
    err: str

    @property
    def ok(self) -> bool:
        return self.code == 0

    @property
    def tail(self) -> str:
        return (self.err.strip() or self.out.strip())[-600:]


def sh(cmd: list[str], cwd: str | None = None, env: dict[str, str] | None = None) -> Proc:
    try:
        p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=900)
    except FileNotFoundError:
        return Proc(127, "", f"{cmd[0]}: command not found")
    except subprocess.TimeoutExpired:
        return Proc(124, "", f"{' '.join(cmd)}: timed out")
    return Proc(p.returncode, p.stdout, p.stderr)


def parse_json(text: str):
    """Decode the first JSON value that starts a line (pnpm prints a `$ ...` banner first)."""
    offset = 0
    for line in text.splitlines(keepends=True):
        if line.startswith(("{", "[")):
            return json.JSONDecoder().raw_decode(text[offset:])[0]
        offset += len(line)
    raise ValueError("no JSON in output")


def real(path: str) -> str:
    return os.path.realpath(os.path.expanduser(path))


def inside(child: str, parent: str) -> bool:
    return child == parent or child.startswith(parent.rstrip(os.sep) + os.sep)


def say(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def state_dir() -> Path:
    override = os.environ.get("WORKTREE_CLEANUP_STATE_DIR")
    base = Path(override) if override else Path(os.environ.get("XDG_STATE_HOME", "~/.local/state")).expanduser() / "worktree-cleanup"
    base.mkdir(parents=True, exist_ok=True)
    return base


def key_for(path: str) -> str:
    return hashlib.sha256(path.encode()).hexdigest()[:16]


@dataclass
class Snapshot:
    """Identity captured while the worktree still exists, so a re-run can finish after it is gone."""

    path: str
    repo: str
    default_branch: str
    branch: str | None
    head: str
    common_dir: str
    workspace_id: str | None = None
    pr: dict | None = None
    claims: list[dict] = field(default_factory=list)
    demos: list[dict] = field(default_factory=list)
    unresolved_demos: list[dict] = field(default_factory=list)
    abandon: str | None = None

    @property
    def file(self) -> Path:
        return state_dir() / f"{key_for(self.path)}.json"

    def save(self) -> None:
        tmp = self.file.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2) + "\n")
        tmp.replace(self.file)

    @staticmethod
    def load(path: str) -> Snapshot | None:
        file = state_dir() / f"{key_for(path)}.json"
        return Snapshot(**json.loads(file.read_text())) if file.exists() else None

    @staticmethod
    def find_by_workspace(workspace_id: str) -> Snapshot | None:
        for file in state_dir().glob("*.json"):
            data = json.loads(file.read_text())
            if data.get("workspace_id") == workspace_id:
                return Snapshot(**data)
        return None


class Cleanup:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.steps: list[dict] = []
        self.remaining: list[dict] = []
        self.preserved: list[dict] = []
        self.snap: Snapshot
        self.exists = False
        self.self_mode = False
        self.archive_pending = False

    # ---- reporting -------------------------------------------------------

    def record(self, step: str, status: str, **detail) -> None:
        self.steps.append({"id": step, "status": status, **detail})
        say(f"[{step}] {status}" + (f": {detail['note']}" if "note" in detail else ""))

    def defer(self, owner: str, reason: str, command: str | None = None) -> None:
        self.remaining.append({"owner": owner, "reason": reason, "command": command})

    def resume_command(self) -> str:
        script = os.path.abspath(__file__)
        target = f"--workspace {self.snap.workspace_id}" if self.snap.workspace_id else f"--path {shlex.quote(self.snap.path)}"
        abandon = f" --abandon {shlex.quote(self.snap.abandon)}" if self.snap.abandon else ""
        return f"{script} {target}{abandon}"

    def report(self, status: str, exit_code: int, error: str | None = None) -> dict:
        snap = getattr(self, "snap", None)
        return {
            "schema": 1,
            "status": status,
            "error": error,
            "target": snap and {
                "path": snap.path,
                "repo": snap.repo,
                "branch": snap.branch,
                "head": snap.head,
                "workspace_id": snap.workspace_id,
                "pr": snap.pr and snap.pr.get("url"),
            },
            "mode": "abandon" if snap and snap.abandon else ("self" if self.self_mode else "normal"),
            "abandon_reason": snap.abandon if snap else None,
            "steps": self.steps,
            "preserved": self.preserved,
            "remaining": self.remaining,
            "resume": self.resume_command() if snap else None,
            "exit": exit_code,
        }

    # ---- target ----------------------------------------------------------

    def workspaces(self, required: type[Exception] | None) -> list[dict]:
        """Active Paseo workspaces. `required` names the error to raise when the daemon is unusable."""
        p = sh(["paseo", "workspace", "ls", "--json"])
        if p.ok:
            data = json.loads(p.out or "[]")
            return data if isinstance(data, list) else data.get("workspaces", [])
        if required:
            raise required("paseo is not installed" if p.code == 127 else f"paseo workspace ls failed: {p.tail}")
        return []

    def resolve(self) -> None:
        a = self.args
        path: str | None = None
        workspace_id = a.workspace
        if a.path:
            path = real(a.path)
        elif workspace_id:
            match = next((w for w in self.workspaces(None) if w.get("workspaceId") == workspace_id), None)
            snap = Snapshot.find_by_workspace(workspace_id)
            path = real(match["cwd"]) if match else (snap.path if snap else None)
            if path is None:
                raise Refused(f"unknown workspace {workspace_id}: not listed by paseo and no cleanup record")
        else:
            top = sh(["git", "rev-parse", "--show-toplevel"])
            if not top.ok:
                raise SystemExit("usage: run inside a worktree, or pass --path or --workspace")
            path = real(top.out.strip())
        self.self_mode = inside(real(os.getcwd()), path)
        self.exists = os.path.isdir(path)
        if self.exists:
            self.snap = self.snapshot_live(path, workspace_id)
        else:
            snap = Snapshot.load(path)
            if snap is None:
                raise Refused(f"{path} is gone and has no cleanup record; nothing to resume")
            self.snap = snap

    def snapshot_live(self, path: str, workspace_id: str | None) -> Snapshot:
        git = lambda *a: sh(["git", "-C", path, *a])
        top = git("rev-parse", "--show-toplevel")
        if not top.ok:
            raise Refused(f"{path} is not a git worktree: {top.tail}")
        path = real(top.out.strip())
        git_dir = git("rev-parse", "--path-format=absolute", "--git-dir").out.strip()
        common = git("rev-parse", "--path-format=absolute", "--git-common-dir").out.strip()
        if real(git_dir) == real(common):
            raise Refused(f"{path} is the main checkout, not a linked worktree")
        listing = sh(["git", "--git-dir", common, "worktree", "list", "--porcelain"]).out
        for block in listing.split("\n\n"):
            lines = block.splitlines()
            if lines and real(lines[0].removeprefix("worktree ")) == path and any(l.startswith("locked") for l in lines):
                raise Refused(f"{path} is locked; unlock it deliberately first")
        head = git("rev-parse", "HEAD").out.strip()
        branch = git("symbolic-ref", "-q", "--short", "HEAD").out.strip() or None
        meta = sh(["gh", "repo", "view", "--json", "nameWithOwner,defaultBranchRef"], cwd=path)
        if not meta.ok:
            raise Refused(f"cannot resolve the GitHub repository: {meta.tail}")
        info = json.loads(meta.out)
        if workspace_id is None:
            managed = inside(path, real(os.path.join(os.environ.get("PASEO_HOME", "~/.paseo"), "worktrees")))
            match = next((w for w in self.workspaces(Refused if managed else None) if w.get("cwd") and real(w["cwd"]) == path), None)
            workspace_id = match["workspaceId"] if match else None
        snap = Snapshot(
            path=path,
            repo=info["nameWithOwner"],
            default_branch=info["defaultBranchRef"]["name"],
            branch=branch,
            head=head,
            common_dir=real(common),
            workspace_id=workspace_id,
            abandon=self.args.abandon,
        )
        previous = Snapshot.load(path)
        if previous and (previous.repo, previous.branch) == (snap.repo, snap.branch):
            snap.claims = previous.claims
        return snap

    # ---- preflight -------------------------------------------------------

    def read_claim(self) -> dict | None:
        file = Path(self.snap.path) / CLAIM_FILE
        if not file.exists():
            return None
        try:
            data = json.loads(file.read_text())
            return {"claim_id": str(data["claim_id"]), "lab": str(data["lab"])}
        except (ValueError, KeyError):
            raise Refused(f"{file} is malformed; release your own orphaned claim through the lab-manager's agent release path (see the ccore2 lab-manager skill)")

    def git(self, *args: str) -> Proc:
        return sh(["git", "-C", self.snap.path, *args])

    def lab(self, *args: str, cwd: str | None = None) -> Proc:
        return sh([*LAB_CLI, *args], cwd=cwd or self.snap.path)

    def lab_cwd(self) -> str | None:
        """A checkout that can run the lab CLI: the worktree, else the repo's main checkout."""
        if self.exists:
            return self.snap.path
        main = Path(self.snap.common_dir).parent
        return str(main) if (main / ".git").is_dir() else None

    def pr_state(self, ref: str) -> str | None:
        p = sh(["gh", "pr", "view", ref, "--repo", self.snap.repo, "--json", "state", "-q", ".state"])
        return p.out.strip() if p.ok else None

    def preflight(self) -> None:
        snap = self.snap
        if not self.exists:
            self.record("preflight", "skipped", note="worktree is gone; resuming from the cleanup record")
            return
        git = self.git
        relaxable: list[str] = []
        hard: list[str] = []

        if snap.branch is None:
            relaxable.append("HEAD is detached, so there is no branch whose PR can prove the work landed")
        elif snap.branch == snap.default_branch:
            hard.append(f"{snap.branch} is the default branch")

        dirty = [l for l in git("status", "--porcelain").out.splitlines() if l]
        if dirty:
            relaxable.append(f"{len(dirty)} uncommitted path(s), e.g. {dirty[0][3:]}")

        if snap.branch and snap.branch != snap.default_branch:
            prs = sh(["gh", "pr", "list", "--repo", snap.repo, "--head", snap.branch, "--state", "all", "--limit", "30", "--json", PR_FIELDS])
            if not prs.ok:
                hard.append(f"cannot list PRs: {prs.tail}")
            else:
                owner = snap.repo.split("/")[0].lower()
                mine = [p for p in json.loads(prs.out) if (p.get("headRepositoryOwner") or {}).get("login", "").lower() == owner]
                exact = [p for p in mine if p["headRefOid"] == snap.head]
                opened = [p for p in exact if p["state"] == "OPEN"]
                merged = [p for p in exact if p["state"] == "MERGED"]
                if opened:
                    relaxable.append(f"PR #{opened[0]['number']} from {snap.branch} at this head is still open")
                elif merged:
                    snap.pr = merged[0]
                elif exact:
                    relaxable.append(f"PR #{exact[0]['number']} was closed without merging")
                elif mine:
                    relaxable.append(f"HEAD {snap.head[:9]} is not the head of a merged PR for {snap.branch}; push it and merge the PR")
                else:
                    relaxable.append(f"no PR exists for {snap.branch}; commits may be unpushed")

        claim = self.read_claim()
        if claim:
            inspected = self.lab("inspect", claim["lab"])
            if not inspected.ok:
                hard.append(f"cannot inspect lab {claim['lab']} (is the lab CLI installed in this worktree?): {inspected.tail}")
            else:
                held = (parse_json(inspected.out).get("claim") or {})
                for url in held.get("pull_requests") or []:
                    if url != (snap.pr or {}).get("url") and self.pr_state(url) != "MERGED":
                        relaxable.append(f"lab claim lists {url}, which is not merged")

        me = os.environ.get("PASEO_AGENT_ID")
        agents = sh(["paseo", "ls", "-g", "--json"])
        if agents.ok:
            for ag in json.loads(agents.out or "[]"):
                if ag.get("status") == "running" and ag.get("id") != me and ag.get("cwd") and inside(real(ag["cwd"]), snap.path):
                    hard.append(f"agent {ag.get('shortId') or ag.get('id')} is still running in this worktree")

        if hard or (relaxable and not snap.abandon):
            problems = hard + relaxable
            hint = "" if hard or snap.abandon else " Pass --abandon <reason> when the work is abandoned or concluded without a merge; keep the lab while a PR using it is open or a prototype review is pending."
            raise Refused("; ".join(problems) + "." + hint)
        if relaxable:
            self.preserve_abandoned(relaxable)
        self.collect(claim)
        snap.save()
        self.record("preflight", "done", note="abandoned: " + snap.abandon if snap.abandon else "merged and clean", discarded=relaxable)

    def preserve_abandoned(self, discarded: list[str]) -> None:
        snap = self.snap
        out = Path(tempfile.mkdtemp(prefix=f"abandon-{key_for(snap.path)}-", dir=state_dir()))
        git = self.git
        (out / "reason.txt").write_text(f"{snap.abandon}\n" + "\n".join(discarded) + "\n")
        (out / "status.txt").write_text(git("status", "--porcelain").out)
        (out / "tracked.patch").write_text(git("diff", "HEAD", "--binary").out)
        untracked = [f for f in git("ls-files", "-o", "--exclude-standard", "-z").out.split("\0") if f]
        if untracked:
            with tarfile.open(out / "untracked.tar.gz", "w:gz") as tar:
                for name in untracked:
                    tar.add(os.path.join(snap.path, name), arcname=name)
        bundle = git("bundle", "create", str(out / "unpushed.bundle"), "HEAD", "--not", "--remotes")
        if not bundle.ok and "empty bundle" not in (bundle.err + bundle.out).lower():
            raise Refused(f"could not preserve unpushed commits before abandoning: {bundle.tail}")
        self.preserved = [{"kind": "abandon-snapshot", "path": str(out)}]

    def collect(self, claim: dict | None) -> None:
        """Record what only the worktree knows: the claim identity (never its credential) and demo identities."""
        snap = self.snap
        if claim and not any(c["claim_id"] == claim["claim_id"] for c in snap.claims):
            snap.claims.append({**claim, "released": False})
        known = {d["run"] for d in snap.demos}
        seen_runs: set[str] = set()
        for manifest in sorted(glob.glob(os.path.join(snap.path, DEMO_MANIFESTS))):
            for entry in json.loads(Path(manifest).read_text()).get("demos", []):
                run = str(entry.get("run", ""))
                seen_runs.add(run)
                reason = self.demo_problem(entry)
                if reason:
                    snap.unresolved_demos.append({"run": run, "reason": reason, "manifest": manifest})
                elif run not in known:
                    snap.demos.append({"run": run, "worker": entry["worker"], "d1": entry.get("d1")})
        for note in glob.glob(os.path.join(snap.path, DEMO_NOTES), recursive=True):
            for run in DEMO_URL.findall(Path(note).read_text(errors="replace")):
                if run not in seen_runs and not any(u["run"] == run for u in snap.unresolved_demos):
                    snap.unresolved_demos.append({"run": run, "reason": "published URL has no entry in a demos.json manifest", "manifest": note})
                    seen_runs.add(run)

    def demo_problem(self, e: dict) -> str | None:
        run = e.get("run")
        if not isinstance(run, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", run):
            return "run name missing or malformed"
        if e.get("account") != LABS_ACCOUNT_ID:
            return "account is not the Nodaste Labs account"
        if e.get("worker") != run or e.get("d1") not in (None, f"{run}-feedback"):
            return "worker must equal the run name and the D1 database must be <run>-feedback"
        if e.get("url") != f"https://{run}.demos.keramos.tech":
            return "url does not match the run name"
        if not e.get("worktree") or real(str(e["worktree"])) != self.snap.path or e.get("branch") != self.snap.branch:
            return "manifest was written by a different worktree or branch"
        return None

    # ---- lab -------------------------------------------------------------

    def confirm_released(self, claim: dict) -> str | None:
        """Ask the manager whether the claim is still held. Only a clean answer marks it released."""
        cwd = self.lab_cwd()
        if cwd is None:
            raise StepFailed(f"cannot confirm the release of claim {claim['claim_id']} on {claim['lab']}: no checkout is left to run the lab CLI from")
        check = self.lab("inspect", claim["lab"], cwd=cwd)
        if not check.ok:
            raise StepFailed(f"cannot confirm the release of claim {claim['claim_id']} on {claim['lab']}; run again once the manager is reachable: {check.tail}")
        now = parse_json(check.out)
        held = now.get("claim") or {}
        if held.get("claim_id") == claim["claim_id"] and not held.get("released_at") and held.get("status") != "released":
            raise StepFailed(f"manager still holds claim {claim['claim_id']} on {claim['lab']}; nothing was removed")
        for c in self.snap.claims:
            if c["claim_id"] == claim["claim_id"]:
                c["released"] = True
        self.snap.save()
        return now.get("state")

    def step_lab(self) -> None:
        snap = self.snap
        claim = self.read_claim() if self.exists else None
        receipt = None
        if claim:
            say(f"releasing lab claim {claim['claim_id']} on {claim['lab']}")
            rel = self.lab("release")
            if not rel.ok:
                raise StepFailed(f"lab release failed, claim file kept: {rel.tail}")
            if (Path(snap.path) / CLAIM_FILE).exists():
                raise StepFailed("lab release exited 0 but the claim file is still present")
            receipt = next((r for r in parse_json(rel.out).get("released", []) if r.get("claim_id") == claim["claim_id"]), None)
        confirmed: list[dict] = []
        states: dict[str, str | None] = {}
        for c in [c for c in snap.claims if not c["released"]]:
            states[c["claim_id"]] = self.confirm_released(c)
            confirmed.append({"claim_id": c["claim_id"], "lab": c["lab"]})
        if claim and receipt and receipt.get("deprovisioning") is False and states.get(claim["claim_id"]) == "provisioned":
            self.defer(
                "operator",
                f"claim released as accounting only; lab {claim['lab']} is still provisioned (agents do not run lab deprovision)",
                f"pnpm --filter @ccore/lab-manager run lab -- deprovision {claim['lab']} --wait",
            )
        if confirmed:
            self.record("lab", "done", claims=confirmed, lab_states=states, deprovisioning=receipt and receipt.get("deprovisioning"))
        elif snap.claims:
            self.record("lab", "already_done", claims=[{"claim_id": c["claim_id"], "lab": c["lab"]} for c in snap.claims])
        else:
            self.record("lab", "skipped", note="no lab claim")

    # ---- demos -----------------------------------------------------------

    def wrangler(self, *args: str) -> Proc:
        cmd = ["wrangler"] if shutil.which("wrangler") else ["npx", "--yes", "wrangler"]
        env = {**os.environ, "CLOUDFLARE_ACCOUNT_ID": LABS_ACCOUNT_ID}
        return sh([*cmd, *args], cwd=str(state_dir()), env=env)

    def worker_exists(self, name: str) -> bool:
        p = self.wrangler("deployments", "list", "--name", name)
        if p.ok:
            return True
        if any(code in p.out + p.err for code in ABSENT_WORKER):
            return False
        raise StepFailed(f"cannot tell whether worker {name} exists: {p.tail}")

    def d1_names(self) -> set[str]:
        p = self.wrangler("d1", "list", "--json")
        if not p.ok:
            raise StepFailed(f"wrangler d1 list failed: {p.tail}")
        return {d["name"] for d in parse_json(p.out)}

    def step_demos(self) -> None:
        snap = self.snap
        removed: list[str] = []
        for d in snap.demos:
            if self.worker_exists(d["worker"]):
                say(f"deleting demo worker {d['worker']}")
                p = self.wrangler("delete", "--name", d["worker"], "--force")
                if not p.ok or self.worker_exists(d["worker"]):
                    raise StepFailed(f"could not delete demo worker {d['worker']}: {p.tail}")
                removed.append(d["worker"])
            if d["d1"] and d["d1"] in self.d1_names():
                export = state_dir() / f"{d['d1']}.sql"
                p = self.wrangler("d1", "export", d["d1"], "--remote", "--output", str(export))
                if not p.ok:
                    raise StepFailed(f"could not export {d['d1']} before deleting it: {p.tail}")
                self.preserved.append({"kind": "d1-export", "path": str(export)})
                p = self.wrangler("d1", "delete", d["d1"], "-y")
                if not p.ok or d["d1"] in self.d1_names():
                    raise StepFailed(f"could not delete D1 database {d['d1']}: {p.tail}")
                removed.append(d["d1"])
        for u in snap.unresolved_demos:
            self.defer("operator", f"demo {u['run']} not removed: {u['reason']} ({u['manifest']})", None)
        if snap.unresolved_demos:
            self.record("demos", "deferred", removed=removed, unresolved=snap.unresolved_demos)
        elif removed:
            self.record("demos", "done", removed=removed)
        else:
            self.record("demos", "already_done" if snap.demos else "skipped", note="nothing left to remove" if snap.demos else "no demos recorded")

    # ---- workspace -------------------------------------------------------

    def step_workspace(self) -> None:
        snap = self.snap
        if self.exists and self.self_mode:
            self.defer("orchestrator", "this process runs inside the worktree; archiving it would end the session", self.resume_command())
            self.record("workspace", "deferred", note="running inside the target")
            self.archive_pending = True
            return
        if self.exists and not self.args.abandon and self.git("status", "--porcelain").out.strip():
            raise StepFailed("worktree became dirty after preflight; not removing it")
        workspace_id = snap.workspace_id
        if workspace_id and any(w.get("workspaceId") == workspace_id for w in self.workspaces(StepFailed)):
            p = sh(["paseo", "workspace", "archive", workspace_id])
            if not p.ok:
                raise StepFailed(f"paseo workspace archive failed: {p.tail}")
            for _ in range(20):
                if not os.path.isdir(snap.path):
                    break
                time.sleep(0.5)
            if os.path.isdir(snap.path):
                self.defer("orchestrator", "workspace archived but the worktree is still on disk; another workspace may reference it", None)
                self.record("workspace", "deferred", workspace_id=snap.workspace_id, note="path remains after archive")
                self.archive_pending = True
                return
            self.record("workspace", "done", workspace_id=workspace_id)
        elif os.path.isdir(snap.path):
            args = ["git", "--git-dir", snap.common_dir, "worktree", "remove"]
            if self.args.abandon:
                args.append("--force")
            p = sh([*args, snap.path])
            if not p.ok:
                raise StepFailed(f"git worktree remove failed: {p.tail}")
            self.record("workspace", "done", note="git worktree remove")
        else:
            self.record("workspace", "already_done", workspace_id=snap.workspace_id)

    # ---- remote branch ---------------------------------------------------

    def remote_tip(self) -> str | None:
        p = sh(["git", "--git-dir", self.snap.common_dir, "ls-remote", "origin", f"refs/heads/{self.snap.branch}"])
        if not p.ok:
            raise StepFailed(f"git ls-remote failed: {p.tail}")
        return p.out.split()[0] if p.out.strip() else None

    def step_branch(self) -> None:
        snap = self.snap
        if self.archive_pending:
            self.record("remote_branch", "deferred", note="runs after the workspace archive")
            return
        if not snap.branch:
            self.record("remote_branch", "skipped", note="detached HEAD")
            return
        if snap.branch == snap.default_branch:
            raise StepFailed(f"refusing to delete the default branch {snap.branch}")
        tip = self.remote_tip()
        if tip is None:
            self.record("remote_branch", "already_done", branch=snap.branch)
            return
        if tip != snap.head:
            self.defer("operator", f"origin/{snap.branch} is at {tip[:9]}, not the recorded head {snap.head[:9]}; it has commits this cleanup did not check", None)
            self.record("remote_branch", "deferred", branch=snap.branch, remote_tip=tip)
            return
        if not (snap.pr and snap.pr.get("state") == "MERGED"):
            self.defer("operator", f"origin/{snap.branch} kept: it holds work that never merged and the bundle only covers unpushed commits", None)
            self.record("remote_branch", "deferred", branch=snap.branch, note="unmerged work")
            return
        owner = snap.repo.split("/")[0].lower()
        blocking: list[dict] = []
        for side in ("--base", "--head"):
            found = sh(["gh", "pr", "list", "--repo", snap.repo, "--state", "open", side, snap.branch, "--limit", "1000", "--json", "number,headRepositoryOwner"])
            if not found.ok:
                raise StepFailed(f"cannot list open PRs {side} {snap.branch}: {found.tail}")
            blocking += [p for p in json.loads(found.out) if side == "--base" or (p.get("headRepositoryOwner") or {}).get("login", "").lower() == owner]
        if blocking:
            self.defer("operator", f"open PR(s) #{', #'.join(str(p['number']) for p in blocking)} depend on {snap.branch}; deleting it would close or retarget them", None)
            self.record("remote_branch", "deferred", branch=snap.branch, open_prs=[p["number"] for p in blocking])
            return
        p = sh(["git", "--git-dir", snap.common_dir, "push", f"--force-with-lease=refs/heads/{snap.branch}:{tip}", "origin", "--delete", snap.branch])
        if not p.ok or self.remote_tip() is not None:
            raise StepFailed(f"could not delete origin/{snap.branch}: {p.tail}")
        self.record("remote_branch", "done", branch=snap.branch)

    # ---- driver ----------------------------------------------------------

    def run(self) -> tuple[dict, int]:
        try:
            self.resolve()
        except Refused as e:
            return self.report("refused", 2, str(e)), 2
        lock = open(state_dir() / f"{key_for(self.snap.path)}.lock", "w")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return self.report("failed", 3, "another cleanup of this worktree is running"), 3
        current = "preflight"
        try:
            self.preflight()
            for current, step in (("lab", self.step_lab), ("demos", self.step_demos), ("workspace", self.step_workspace), ("remote_branch", self.step_branch)):
                step()
        except Refused as e:
            return self.report("refused", 2, str(e)), 2
        except (StepFailed, ValueError, KeyError, OSError) as e:
            self.record(current, "failed", error=str(e) or type(e).__name__)
            return self.report("failed", 3, str(e) or type(e).__name__), 3
        code = 4 if self.remaining else 0
        return self.report("deferred" if self.remaining else "complete", code), code


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    target = ap.add_mutually_exclusive_group()
    target.add_argument("--path", help="worktree path (default: the worktree containing the current directory)")
    target.add_argument("--workspace", help="Paseo workspace id")
    ap.add_argument("--abandon", metavar="REASON", help="work abandoned or concluded without a merge: discard unmerged or uncommitted work (a snapshot is preserved) and release the lab; never to get past an open PR or a pending prototype review")
    args = ap.parse_args(argv)
    if args.abandon is not None and not args.abandon.strip():
        ap.error("--abandon needs a reason")
    report, code = Cleanup(args).run()
    print(json.dumps(report, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
