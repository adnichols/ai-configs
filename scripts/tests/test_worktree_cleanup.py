"""Behavior tests for skills/worktree-cleanup/scripts/worktree_cleanup.py.

Each test builds a real bare origin, a clone and a linked worktree, and puts fake
gh/paseo/pnpm/wrangler on PATH (see fixtures/worktree_cleanup_fakes.py). Git runs for real.
"""

import hashlib
import importlib.util
import json
import os
import shutil
import sys
import subprocess
import tempfile
import threading
import types
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills" / "worktree-cleanup" / "scripts" / "worktree_cleanup.py"
FAKES = Path(__file__).resolve().parent / "fixtures" / "worktree_cleanup_fakes.py"
ACCOUNT = "e6d3e575b97001f8ad1a7e98e497afa5"
PR_URL = "https://github.com/acme/widgets/pull/7"


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True).stdout.strip()


class AccountApi(ThreadingHTTPServer):
    """The slice of the Cloudflare REST API the script reads, from the fake account state: the Labs account's worker list and its R2 bucket lists per jurisdiction, paged by cursor."""

    def __init__(self, fake_state: Path):
        self.paths: list[str] = []

        class Handler(BaseHTTPRequestHandler):
            def reply(handler, status, body=None, headers=None):
                handler.send_response(status)
                for name, value in (headers or {}).items():
                    handler.send_header(name, value)
                handler.end_headers()
                if body is not None:
                    handler.wfile.write(json.dumps(body).encode())

            def do_GET(handler):
                self.paths.append(handler.path)
                state = json.loads(fake_state.read_text())
                url = urllib.parse.urlsplit(handler.path)
                query = urllib.parse.parse_qs(url.query)
                if handler.headers.get("Authorization") != "Bearer fake-token":
                    return handler.reply(403, {"success": False, "errors": [{"code": 10000, "message": "Authentication error"}]})
                if state.get("api_down"):
                    return handler.reply(500)
                if state.get("api_redirect"):
                    return handler.reply(302, headers={"Location": "/leak"})
                for suffix, raw in state.get("api_raw", {}).items():
                    if url.path.endswith(suffix):
                        return handler.reply(200, raw)
                if url.path == f"/accounts/{ACCOUNT}/d1/database":
                    return handler.reply(200, {"success": True, "result": [{"name": d, "uuid": "x"} for d in state["d1"]], "result_info": {"total_count": len(state["d1"])}})
                if url.path == f"/accounts/{ACCOUNT}/workers/scripts":
                    return handler.reply(200, {"success": True, "result": [{"id": w} for w in state["workers"]]})
                if url.path == f"/accounts/{ACCOUNT}/r2/buckets":
                    jurisdiction = handler.headers.get("cf-r2-jurisdiction")
                    eu = jurisdiction is not None
                    names = state[f"r2_{jurisdiction}"] if jurisdiction else state["r2"]
                    size = state.get("r2_page_size", 1000)
                    start = int(query.get("cursor", ["0"])[0])
                    info = {"total_count": len(names) if eu else state.get("r2_total", len(names))}
                    if start + size < len(names):
                        info["cursor"] = str(start + size)
                    return handler.reply(200, {"success": True, "result": {"buckets": [{"name": b} for b in names[start : start + size]]}, "result_info": info})
                handler.reply(404, {"success": False, "errors": []})

            def log_message(handler, *args):
                pass

        super().__init__(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.serve_forever, daemon=True).start()

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.server_address[1]}"


class Fixture:
    def __init__(self, tmp: Path):
        self.tmp = tmp
        self.origin = tmp / "origin.git"
        self.main = tmp / "main"
        self.wt = tmp / "wt"
        self.bin = tmp / "bin"
        self.state_dir = tmp / "state"
        self.fake_state = tmp / "fake.json"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(self.origin)], check=True)
        subprocess.run(["git", "clone", "-q", str(self.origin), str(self.main)], check=True, capture_output=True)
        git(self.main, "config", "user.email", "t@example.com")
        git(self.main, "config", "user.name", "t")
        (self.main / "README").write_text("hi\n")
        (self.main / ".gitignore").write_text(".ccore/\nartifacts/\n")
        git(self.main, "add", ".")
        git(self.main, "commit", "-qm", "init")
        git(self.main, "push", "-q", "origin", "main")
        git(self.main, "worktree", "add", "-q", "-b", "feat", str(self.wt))
        (self.wt / "change.txt").write_text("work\n")
        git(self.wt, "add", ".")
        git(self.wt, "commit", "-qm", "work")
        git(self.wt, "push", "-q", "origin", "feat")
        self.head = git(self.wt, "rev-parse", "HEAD")
        self.wt = self.wt.resolve()
        self.bin.mkdir()
        self.api: AccountApi | None = None
        self.api_base: str | None = None
        for tool in ("gh", "paseo", "pnpm", "wrangler"):
            shim = self.bin / tool
            shim.write_text(f'#!/bin/sh\nexec python3 "{FAKES}" {tool} "$@"\n')
            shim.chmod(0o755)
        self.fake_state.write_text(
            json.dumps(
                {
                    "calls": [],
                    "origin": str(self.origin),
                    "prs": [{"number": 7, "url": PR_URL, "state": "MERGED", "headRefName": "feat", "baseRefName": "main", "headRefOid": self.head, "headRepositoryOwner": {"login": "acme"}, "headRepository": {"name": "widgets"}}],
                    "workspaces": [{"workspaceId": "wks_1", "cwd": str(self.wt), "repo": str(self.main)}],
                    "agents": [],
                    "lab_claim": None,
                    "lab_state": "provisioned",
                    "deprovisions": True,
                    "workers": [],
                    "d1": [],
                    "r2": [],
                    "r2_eu": [],
                    "r2_us": [],
                }
            )
        )
        self.api = AccountApi(self.fake_state)

    def close(self):
        self.api.shutdown()
        self.api.server_close()

    def fake(self, **updates):
        state = json.loads(self.fake_state.read_text())
        state.update(updates)
        self.fake_state.write_text(json.dumps(state))

    def calls(self):
        return json.loads(self.fake_state.read_text())["calls"]

    def claim(self):
        (self.wt / ".ccore").mkdir()
        (self.wt / ".ccore" / "lab-claim.json").write_text(json.dumps({"lab": "lab007", "claim_id": "c-1", "credential": "secret"}))
        self.fake(lab_claim={"claim_id": "c-1", "lab": "lab007", "status": "active", "pull_requests": [PR_URL]})

    def demo(self, run="proto-20261005-ab12cd34", **overrides):
        entry = {"run": run, "worker": run, "d1": f"{run}-feedback", "account": ACCOUNT, "url": f"https://{run}.demos.keramos.tech", "worktree": str(self.wt), "branch": "feat"}
        entry.update(overrides)
        directory = self.wt / "artifacts" / "verified-build" / "r1"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "demos.json").write_text(json.dumps({"demos": [entry]}))
        self.fake(workers=[run], d1=[f"{run}-feedback"])

    def run(self, *args, cwd=None):
        env = {**os.environ, "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}", "FAKE_STATE": str(self.fake_state), "WORKTREE_CLEANUP_STATE_DIR": str(self.state_dir), "PASEO_HOME": str(self.tmp / "paseo"), "XDG_STATE_HOME": str(self.tmp / "xdg"), "CLOUDFLARE_API_BASE": self.api_base or self.api.base}
        env.pop("PASEO_AGENT_ID", None)
        env.pop("CLOUDFLARE_API_TOKEN", None)
        p = subprocess.run([str(SCRIPT), *args], cwd=cwd or self.main, env=env, capture_output=True, text=True)
        try:
            report = json.loads(p.stdout)
        except ValueError:
            self.fail_output = p.stdout + p.stderr
            raise AssertionError(f"no JSON report (exit {p.returncode}): {p.stdout}{p.stderr}")
        self.last_stderr = p.stderr
        return p.returncode, report

    def step(self, report, step_id):
        return next(s for s in report["steps"] if s["id"] == step_id)

    def remote_has_branch(self):
        return bool(git(self.origin, "branch", "--list", "feat"))


class WorktreeCleanupTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.f = Fixture(Path(self._tmp.name).resolve())
        self.addCleanup(self.f.close)

    def test_full_cleanup_in_fixed_order_then_rerun_is_a_noop(self):
        self.f.claim()
        self.f.demo()
        code, report = self.f.run("--workspace", "wks_1")
        self.assertEqual((code, report["status"]), (0, "complete"), report)
        self.assertEqual([s["id"] for s in report["steps"]], ["preflight", "lab", "demos", "workspace", "remote_branch"])
        self.assertEqual(self.f.calls(), ["release", "delete worker proto-20261005-ab12cd34", "delete d1 proto-20261005-ab12cd34-feedback", "archive wks_1"])
        self.assertFalse(self.f.wt.exists())
        self.assertFalse(self.f.remote_has_branch())
        self.assertTrue(any(p["kind"] == "d1-export" and Path(p["path"]).exists() for p in report["preserved"]))
        self.assertEqual(git(self.f.main, "branch", "--list", "feat").strip(), "feat")

        code, again = self.f.run("--workspace", "wks_1")
        self.assertEqual((code, again["status"]), (0, "complete"), again)
        self.assertEqual([s["status"] for s in again["steps"]], ["skipped", "already_done", "already_done", "already_done", "already_done"])
        self.assertEqual(len(self.f.calls()), 4)

    def test_dirty_worktree_is_refused_and_nothing_is_touched(self):
        self.f.claim()
        (self.f.wt / "scratch.txt").write_text("uncommitted\n")
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual((code, report["status"]), (2, "refused"))
        self.assertIn("uncommitted", report["error"])
        self.assertEqual(self.f.calls(), [])
        self.assertTrue((self.f.wt / ".ccore" / "lab-claim.json").exists())
        self.assertTrue(self.f.remote_has_branch())

    def test_gitignored_claim_and_artifacts_do_not_count_as_dirty(self):
        self.f.claim()
        self.f.demo()
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual(code, 0, report)

    def test_unmerged_pr_is_refused(self):
        prs = json.loads(self.f.fake_state.read_text())["prs"]
        prs[0]["state"] = "OPEN"
        self.f.fake(prs=prs)
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual((code, report["status"]), (2, "refused"))
        self.assertIn("still open", report["error"])
        self.assertTrue(self.f.wt.exists())

    def test_commits_beyond_the_merged_pr_head_are_refused(self):
        (self.f.wt / "later.txt").write_text("after merge\n")
        git(self.f.wt, "add", ".")
        git(self.f.wt, "commit", "-qm", "after merge")
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual(code, 2)
        self.assertIn("not contained in the head of a merged PR", report["error"])

    def test_abandon_preserves_work_then_removes_everything(self):
        prs = json.loads(self.f.fake_state.read_text())["prs"]
        prs[0]["state"] = "OPEN"
        self.f.fake(prs=prs)
        (self.f.wt / "wip.txt").write_text("keep me\n")
        code, report = self.f.run("--path", str(self.f.wt), "--abandon", "operator dropped it")
        self.assertEqual(report["mode"], "abandon")
        self.assertEqual(report["abandon_reason"], "operator dropped it")
        snapshot = Path(report["preserved"][0]["path"])
        self.assertTrue((snapshot / "untracked.tar.gz").exists())
        self.assertIn("wip.txt", (snapshot / "status.txt").read_text())
        self.assertFalse(self.f.wt.exists())

    def test_failed_release_keeps_claim_and_worktree_then_a_rerun_finishes(self):
        self.f.claim()
        self.f.fake(release_fails=True)
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual((code, report["status"]), (3, "failed"))
        self.assertEqual([s["id"] for s in report["steps"]], ["preflight", "lab"])
        self.assertTrue((self.f.wt / ".ccore" / "lab-claim.json").exists())
        self.assertTrue(self.f.wt.exists())
        self.assertTrue(self.f.remote_has_branch())

        self.f.fake(release_fails=False)
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual(code, 0, report)
        self.assertFalse(self.f.wt.exists())

    STALE_ERROR = "lab release failed: claim_credential_invalid: the claim credential is no longer valid"

    def stale_claim_files(self):
        return sorted((self.f.tmp / "xdg" / "stale-lab-claims").glob("*.json"))

    def test_release_rejected_as_credential_invalid_while_another_claim_holds_the_lab_moves_the_stale_file_aside_and_finishes(self):
        self.f.claim()
        self.f.demo()
        original = (self.f.wt / ".ccore" / "lab-claim.json").read_text()
        self.f.fake(release_error=self.STALE_ERROR, lab_claim={"claim_id": "c-2", "lab": "lab007", "status": "active", "pull_requests": []})
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual((code, report["status"]), (0, "complete"), report)
        lab = self.f.step(report, "lab")
        self.assertEqual(lab["status"], "done")
        self.assertIn("stale claim file moved aside", lab["note"])
        self.assertIn("c-1", lab["note"])
        self.assertIn("c-2", lab["note"])
        (moved,) = self.stale_claim_files()
        self.assertEqual(moved.name, "wt-c-1.json")
        self.assertEqual(moved.read_text(), original)
        self.assertEqual(self.f.calls(), ["release", "delete worker proto-20261005-ab12cd34", "delete d1 proto-20261005-ab12cd34-feedback", "archive wks_1"])
        self.assertFalse(self.f.wt.exists())
        self.assertFalse(self.f.remote_has_branch())

        code, again = self.f.run("--path", str(self.f.wt))
        self.assertEqual((code, again["status"]), (0, "complete"), again)
        self.assertEqual(self.f.step(again, "lab")["status"], "already_done")
        self.assertEqual(len(self.stale_claim_files()), 1)

    def test_release_rejected_as_credential_invalid_when_the_manager_has_no_claim_or_a_released_one_is_also_stale(self):
        for held in (None, {"claim_id": "c-1", "lab": "lab007", "status": "released", "released_at": "2026-10-13T00:00:00Z"}):
            with self.subTest(held=held):
                self.setUp()
                self.f.claim()
                self.f.fake(release_error=self.STALE_ERROR, lab_claim=held)
                code, report = self.f.run("--path", str(self.f.wt))
                self.assertEqual((code, report["status"]), (0, "complete"), report)
                self.assertEqual(self.f.step(report, "lab")["status"], "done")
                self.assertEqual([p.name for p in self.stale_claim_files()], ["wt-c-1.json"])

    def test_unproven_inspect_answers_fail_closed_and_keep_the_claim_file(self):
        good = {"claim_id": "c-2", "lab": "lab007", "status": "active"}
        answers = {
            "empty object": {},
            "missing claim key": {"name": "lab007", "state": "provisioned"},
            "claim false": {"name": "lab007", "claim": False},
            "claim empty object": {"name": "lab007", "claim": {}},
            "outer name mismatch": {"name": "lab008", "claim": dict(good, lab="lab008")},
            "missing outer name": {"claim": good},
            "nested lab mismatch": {"name": "lab007", "claim": dict(good, lab="lab008")},
            "unknown status": {"name": "lab007", "claim": dict(good, status="pending")},
            "same claim id, weird released_at": {"name": "lab007", "claim": {"claim_id": "c-1", "lab": "lab007", "status": "active", "released_at": "2026-10-13T00:00:00Z"}},
            "non-string claim id": {"name": "lab007", "claim": dict(good, claim_id=2)},
        }
        for label, answer in answers.items():
            with self.subTest(label):
                self.setUp()
                self.f.claim()
                self.f.fake(release_error=self.STALE_ERROR, inspect_answer=answer)
                code, report = self.f.run("--path", str(self.f.wt))
                self.assertEqual((code, report["status"]), (3, "failed"), report)
                self.assertIn("claim file kept", report["error"])
                self.assertTrue((self.f.wt / ".ccore" / "lab-claim.json").exists())
                self.assertEqual(self.stale_claim_files(), [])

    def test_repeated_same_name_same_claim_id_archives_in_one_second_never_overwrite(self):
        spec = importlib.util.spec_from_file_location("worktree_cleanup_under_test", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        self.addCleanup(sys.modules.pop, spec.name, None)
        spec.loader.exec_module(module)
        root = Path(self._tmp.name)
        worktree = root / "wt-archive"
        (worktree / ".ccore").mkdir(parents=True)
        stub = types.SimpleNamespace(snap=types.SimpleNamespace(path=str(worktree)))
        bodies = []
        with mock.patch.dict(os.environ, {"XDG_STATE_HOME": str(root / "xdg-archive")}), mock.patch.object(module.time, "time", return_value=1_800_000_000.0):
            for n in range(3):
                body = json.dumps({"lab": "lab007", "claim_id": "c-1", "credential": f"secret-{n}"})
                bodies.append(body)
                (worktree / ".ccore" / "lab-claim.json").write_text(body)
                dest = module.Cleanup.move_stale_claim_aside(stub, {"claim_id": "c-1", "lab": "lab007"})
                self.assertFalse((worktree / ".ccore" / "lab-claim.json").exists())
                self.assertEqual(dest.read_text(), body)
            kept = list((root / "xdg-archive" / "stale-lab-claims").glob("*.json"))
        self.assertEqual(sorted(p.read_text() for p in kept), sorted(bodies))

    def test_release_rejected_as_credential_invalid_for_the_live_holder_still_fails_and_keeps_everything(self):
        self.f.claim()
        self.f.fake(release_error=self.STALE_ERROR)
        for _ in range(2):
            code, report = self.f.run("--path", str(self.f.wt))
            self.assertEqual((code, report["status"]), (3, "failed"), report)
            self.assertIn("claim file kept", report["error"])
            self.assertTrue((self.f.wt / ".ccore" / "lab-claim.json").exists())
            self.assertEqual(self.stale_claim_files(), [])
            self.assertTrue(self.f.wt.exists())
            self.assertTrue(self.f.remote_has_branch())

    def test_release_rejected_as_credential_invalid_with_an_unreachable_manager_still_fails_and_keeps_everything(self):
        self.f.claim()
        self.f.fake(release_error=self.STALE_ERROR, inspect_fails_after_release=True, lab_claim={"claim_id": "c-2", "lab": "lab007", "status": "active"})
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual((code, report["status"]), (3, "failed"), report)
        self.assertIn("claim file kept", report["error"])
        self.assertTrue((self.f.wt / ".ccore" / "lab-claim.json").exists())
        self.assertEqual(self.stale_claim_files(), [])
        self.assertTrue(self.f.wt.exists())
        self.assertTrue(self.f.remote_has_branch())

    def test_other_release_failures_never_take_the_stale_path_even_when_another_claim_holds_the_lab(self):
        self.f.claim()
        self.f.fake(release_fails=True, lab_claim={"claim_id": "c-2", "lab": "lab007", "status": "active"})
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual((code, report["status"]), (3, "failed"), report)
        self.assertTrue((self.f.wt / ".ccore" / "lab-claim.json").exists())
        self.assertEqual(self.stale_claim_files(), [])

    def test_running_inside_the_target_defers_archive_and_branch_deletion_and_gives_a_resume_command(self):
        code, report = self.f.run(cwd=self.f.wt)
        self.assertEqual((code, report["status"]), (4, "deferred"))
        self.assertTrue(self.f.wt.exists())
        self.assertTrue(self.f.remote_has_branch())
        (item,) = report["remaining"]
        self.assertEqual(item["owner"], "orchestrator")
        self.assertEqual(item["command"], report["resume"])

        code, report = self.f.run("--workspace", "wks_1", cwd=self.f.main)
        self.assertEqual((code, report["status"]), (0, "complete"), report)
        self.assertFalse(self.f.wt.exists())
        self.assertFalse(self.f.remote_has_branch())

    def test_abandon_started_inside_the_target_resumes_with_abandon(self):
        (self.f.wt / "wip.txt").write_text("keep me\n")
        code, report = self.f.run("--abandon", "dropped", cwd=self.f.wt)
        self.assertEqual(code, 4, report)
        self.assertTrue(self.f.remote_has_branch())
        self.assertIn("--abandon dropped", report["resume"])
        resume = report["resume"].split()[1:]
        code, report = self.f.run(*resume, cwd=self.f.main)
        self.assertEqual(code, 0, report)
        self.assertFalse(self.f.wt.exists())

    def test_release_the_manager_still_holds_stops_everything_and_never_proceeds_on_rerun(self):
        self.f.claim()
        self.f.fake(release_noop=True)
        for _ in range(2):
            code, report = self.f.run("--path", str(self.f.wt))
            self.assertEqual((code, report["status"]), (3, "failed"), report)
            self.assertIn("still holds", report["error"])
            self.assertTrue(self.f.wt.exists())
            self.assertTrue(self.f.remote_has_branch())

    def test_unverifiable_release_stops_and_a_rerun_verifies_before_removing(self):
        self.f.claim()
        self.f.fake(inspect_fails_after_release=True)
        for _ in range(2):
            code, report = self.f.run("--path", str(self.f.wt))
            self.assertEqual((code, report["status"]), (3, "failed"), report)
            self.assertIn("cannot confirm", report["error"])
            self.assertTrue(self.f.wt.exists())
            self.assertTrue(self.f.remote_has_branch())
        self.assertEqual(self.f.calls(), ["release"])

        self.f.fake(inspect_fails_after_release=False)
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual(code, 0, report)
        self.assertEqual(self.f.calls(), ["release", "archive wks_1"])
        self.assertFalse(self.f.wt.exists())

    def test_unconfirmed_release_blocks_demos_and_branch_even_after_the_worktree_is_gone(self):
        self.f.claim()
        self.f.demo()
        self.f.fake(inspect_fails_after_release=True)
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual(code, 3, report)
        git(self.f.main, "worktree", "remove", "--force", str(self.f.wt))
        self.f.fake(workspaces=[])
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual((code, report["status"]), (3, "failed"), report)
        self.assertEqual([c for c in self.f.calls() if "delete" in c], [])
        self.assertTrue(self.f.remote_has_branch())

        self.f.fake(inspect_fails_after_release=False)
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual(code, 0, report)
        self.assertFalse(self.f.remote_has_branch())

    def test_merged_pr_of_an_earlier_head_does_not_authorize_deleting_a_newer_remote_head(self):
        self.f.fake(release_fails=True)
        self.f.claim()
        code, _ = self.f.run("--path", str(self.f.wt))
        self.assertEqual(code, 3)
        (self.f.wt / "newer.txt").write_text("pushed after the merged head\n")
        git(self.f.wt, "add", ".")
        git(self.f.wt, "commit", "-qm", "newer")
        git(self.f.wt, "push", "-q", "origin", "feat")
        self.f.fake(release_fails=False)
        code, report = self.f.run("--path", str(self.f.wt), "--abandon", "dropped")
        self.assertEqual(code, 4, report)
        self.assertTrue(self.f.remote_has_branch())

    def test_branch_is_kept_while_an_open_pr_is_based_on_it(self):
        prs = json.loads(self.f.fake_state.read_text())["prs"]
        prs.append({"number": 9, "url": "https://github.com/acme/widgets/pull/9", "state": "OPEN", "headRefName": "child", "baseRefName": "feat", "headRefOid": "0" * 40, "headRepositoryOwner": {"login": "acme"}})
        self.f.fake(prs=prs)
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual(code, 4, report)
        self.assertTrue(self.f.remote_has_branch())
        self.assertIn("#9", report["remaining"][0]["reason"])

    def test_open_pr_at_the_same_head_is_refused_even_when_another_pr_merged(self):
        prs = json.loads(self.f.fake_state.read_text())["prs"]
        prs.append({**prs[0], "number": 8, "url": "https://github.com/acme/widgets/pull/8", "state": "OPEN", "baseRefName": "release"})
        self.f.fake(prs=prs)
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual(code, 2, report)
        self.assertIn("still open", report["error"])
        self.assertTrue(self.f.remote_has_branch())

    def land_as_stack_member(self):
        """Origin's branch gains 'Merge main' after the worker's head, and the PR merges at that commit."""
        f = self.f
        (f.main / "other.txt").write_text("landed on main\n")
        git(f.main, "add", ".")
        git(f.main, "commit", "-qm", "main moves")
        git(f.main, "push", "-q", "origin", "main")
        member = f.tmp / "member"
        subprocess.run(["git", "clone", "-q", "-b", "feat", str(f.origin), str(member)], check=True, capture_output=True)
        git(member, "config", "user.email", "t@example.com")
        git(member, "config", "user.name", "t")
        git(member, "merge", "-q", "--no-ff", "-m", "Merge main into feat for stack landing", "origin/main")
        git(member, "push", "-q", "origin", "feat")
        merged_head = git(member, "rev-parse", "HEAD")
        prs = json.loads(f.fake_state.read_text())["prs"]
        prs[0]["headRefOid"] = merged_head
        f.fake(prs=prs)
        return merged_head

    def test_stack_landed_item_cleans_without_abandon_when_the_pr_merged_at_a_head_containing_the_worker_head(self):
        merged_head = self.land_as_stack_member()
        self.assertNotEqual(merged_head, self.f.head)
        code, report = self.f.run("--workspace", "wks_1")
        self.assertEqual((code, report["status"], report["mode"]), (0, "complete", "normal"), report)
        self.assertFalse(self.f.wt.exists())
        self.assertFalse(self.f.remote_has_branch())

    def test_stack_landed_branch_whose_tip_moved_past_the_merged_pr_head_is_kept(self):
        self.land_as_stack_member()
        member = self.f.tmp / "member"
        (member / "late.txt").write_text("pushed after the merge\n")
        git(member, "add", ".")
        git(member, "commit", "-qm", "late")
        git(member, "push", "-q", "origin", "feat")
        code, report = self.f.run("--workspace", "wks_1")
        self.assertEqual(code, 4, report)
        self.assertEqual(self.f.step(report, "remote_branch")["status"], "deferred")
        self.assertTrue(self.f.remote_has_branch())

    def test_branch_is_deleted_when_its_tip_is_the_head_of_any_merged_pr_that_contains_the_worker_head(self):
        self.land_as_stack_member()
        member = self.f.tmp / "member"
        git(member, "merge", "-q", "--no-ff", "-m", "Merge main again", "origin/main")
        (member / "again.txt").write_text("second merge-main\n")
        git(member, "add", ".")
        git(member, "commit", "-qm", "second")
        git(member, "push", "-q", "origin", "feat")
        prs = json.loads(self.f.fake_state.read_text())["prs"]
        prs.append({**prs[0], "number": 11, "url": "https://github.com/acme/widgets/pull/11", "headRefOid": self.f.head})
        prs[0]["headRefOid"] = git(member, "rev-parse", "HEAD")
        self.f.fake(prs=prs)
        code, report = self.f.run("--workspace", "wks_1")
        self.assertEqual((code, report["status"]), (0, "complete"), report)
        self.assertFalse(self.f.remote_has_branch())

    def test_merged_pr_from_another_repository_of_the_same_owner_does_not_authorize_cleanup(self):
        self.land_as_stack_member()
        prs = json.loads(self.f.fake_state.read_text())["prs"]
        prs[0]["headRepository"] = {"name": "widgets-fork"}
        self.f.fake(prs=prs)
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual(code, 2, report)
        self.assertTrue(self.f.wt.exists())

    def test_merged_pr_head_that_does_not_contain_the_worker_head_is_refused(self):
        self.land_as_stack_member()
        (self.f.wt / "unpushed.txt").write_text("never reached the PR\n")
        git(self.f.wt, "add", ".")
        git(self.f.wt, "commit", "-qm", "unpushed")
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual(code, 2, report)
        self.assertIn("not contained in", report["error"])
        self.assertTrue(self.f.remote_has_branch())

    def test_abandon_never_deletes_a_remote_branch_holding_unmerged_work(self):
        prs = json.loads(self.f.fake_state.read_text())["prs"]
        prs[0]["state"] = "OPEN"
        self.f.fake(prs=prs)
        code, report = self.f.run("--path", str(self.f.wt), "--abandon", "dropped")
        self.assertEqual(code, 4, report)
        self.assertTrue(self.f.remote_has_branch())
        self.assertFalse(self.f.wt.exists())

    def test_accounting_only_release_leaves_the_deprovision_to_the_operator(self):
        self.f.claim()
        self.f.fake(deprovisions=False)
        code, report = self.f.run("--workspace", "wks_1")
        self.assertEqual((code, report["status"]), (4, "deferred"))
        (item,) = report["remaining"]
        self.assertEqual(item["owner"], "operator")
        self.assertIn("deprovision lab007", item["command"])
        self.assertFalse(self.f.wt.exists())

    def test_manifest_written_by_another_worktree_is_never_deleted(self):
        self.f.demo(worktree=str(self.f.tmp / "elsewhere"))
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual(code, 4, report)
        self.assertEqual([c for c in self.f.calls() if "delete" in c], [])
        self.assertIn("different worktree", report["remaining"][0]["reason"])

    def test_published_url_without_a_manifest_is_reported_not_guessed(self):
        directory = self.f.wt / "artifacts" / "verified-build" / "r1"
        directory.mkdir(parents=True)
        (directory / "run.md").write_text("demo: https://old-proto-20260101-deadbeef.demos.keramos.tech\n")
        self.f.fake(workers=["old-proto-20260101-deadbeef"])
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual(code, 4, report)
        self.assertIn("old-proto-20260101-deadbeef", report["remaining"][0]["reason"])

    RUN = "proto-20261005-ab12cd34"

    def unresolved_demo(self, run=RUN, **account):
        """A published demo whose manifest entry fails the worker-name check, with `account` as what the Labs account holds."""
        self.f.demo(run, worker="renamed-worker")
        self.f.fake(**{"workers": [], "d1": [], "r2": [], **account})

    def unresolved_runs(self):
        code, record = self.f.run("--show-record", str(self.f.wt))
        self.assertEqual(code, 0, record)
        return [u["run"] for u in record["unresolved_demos"]]

    def test_unresolved_demo_clears_on_the_next_run_once_its_resources_are_gone(self):
        self.unresolved_demo(workers=[f"{self.RUN}-builder-lab001"])
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual((code, report["status"]), (4, "deferred"), report)
        self.assertIn(f"worker {self.RUN}-builder-lab001", report["remaining"][0]["reason"])
        self.assertEqual(self.unresolved_runs(), [self.RUN])
        self.f.fake(workers=[])
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual((code, report["status"]), (0, "complete"), report)
        self.assertEqual(self.f.step(report, "demos")["status"], "done")
        self.assertEqual(self.f.step(report, "demos")["cleared"], [self.RUN])
        self.assertEqual(self.unresolved_runs(), [])
        self.assertEqual([c for c in self.f.calls() if "delete" in c], [])

    def test_unresolved_demo_stays_deferred_while_any_worker_d1_or_r2_name_matches(self):
        self.unresolved_demo(workers=[f"{self.RUN}-builder-lab001"])
        self.f.run("--path", str(self.f.wt))
        for account, present in (
            ({"workers": [self.RUN]}, f"worker {self.RUN}"),
            ({"workers": [], "d1": [f"{self.RUN}-feedback"]}, f"D1 database {self.RUN}-feedback"),
            ({"d1": [], "r2": [f"{self.RUN}-packs-lab017"]}, f"R2 bucket {self.RUN}-packs-lab017"),
            ({"r2": [], "workers": ["renamed-worker"]}, "worker renamed-worker"),
        ):
            with self.subTest(present=present):
                self.f.fake(**account)
                code, report = self.f.run("--path", str(self.f.wt))
                self.assertEqual((code, report["status"]), (4, "deferred"), report)
                self.assertIn(present, report["remaining"][0]["reason"])
                self.assertEqual(self.unresolved_runs(), [self.RUN])
        self.assertEqual([c for c in self.f.calls() if "delete" in c], [])

    def test_names_that_only_share_the_run_name_as_text_do_not_hold_a_demo(self):
        self.unresolved_demo(workers=[f"{self.RUN}0", f"other-{self.RUN}"], d1=[f"{self.RUN[:-1]}-feedback"], r2=[f"x{self.RUN}"])
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual((code, report["status"]), (0, "complete"), report)

    def test_published_url_without_a_manifest_clears_once_the_account_holds_nothing_for_it(self):
        directory = self.f.wt / "artifacts" / "verified-build" / "r1"
        directory.mkdir(parents=True)
        (directory / "run.md").write_text("demo: https://old-proto-20260101-deadbeef.demos.keramos.tech\n")
        self.f.fake(workers=["old-proto-20260101-deadbeef"])
        self.assertEqual(self.f.run("--path", str(self.f.wt))[0], 4)
        self.f.fake(workers=[])
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual((code, report["status"]), (0, "complete"), report)

    def test_unresolved_demo_with_a_malformed_run_name_is_never_cleared(self):
        self.unresolved_demo(run="Bad_Run")
        for _ in range(2):
            code, report = self.f.run("--path", str(self.f.wt))
            self.assertEqual((code, report["status"]), (4, "deferred"), report)
            self.assertIn("malformed", report["remaining"][0]["reason"])

    def test_unresolved_demo_is_kept_when_the_account_cannot_be_listed(self):
        self.unresolved_demo()
        self.f.fake(api_down=True)
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual(code, 3, report)
        self.assertIn("worker", report["error"])
        self.assertEqual(self.unresolved_runs(), [self.RUN])

    def test_unresolved_demo_is_kept_when_the_bucket_list_is_cut_short(self):
        self.unresolved_demo()
        self.f.fake(r2_total=21)
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual(code, 3, report)
        self.assertIn("R2 buckets", report["error"])
        self.assertEqual(self.unresolved_runs(), [self.RUN])

    def test_a_matching_bucket_on_a_later_page_or_in_another_jurisdiction_holds_the_demo(self):
        self.unresolved_demo(r2=["unrelated-a", f"{self.RUN}-packs"], r2_page_size=1, r2_total=1)
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual((code, report["status"]), (4, "deferred"), report)
        self.assertIn(f"R2 bucket {self.RUN}-packs", report["remaining"][0]["reason"])
        self.f.fake(r2=[], r2_total=0, r2_eu=[f"{self.RUN}-packs"])
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual((code, report["status"]), (4, "deferred"), report)
        self.f.fake(r2_eu=[], r2_us=[f"{self.RUN}-packs"])
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual((code, report["status"]), (4, "deferred"), report)
        self.f.fake(r2_us=[])
        self.assertEqual(self.f.run("--path", str(self.f.wt))[0], 0)

    def test_a_malformed_successful_listing_is_not_read_as_an_empty_account(self):
        self.unresolved_demo()
        buckets = {"success": True, "result": {"buckets": []}}
        cases = [
            ("r2/buckets", buckets),
            ("r2/buckets", {**buckets, "result_info": {"total_count": 0, "cursor": ""}}),
            ("r2/buckets", {**buckets, "result_info": {"total_count": -1}}),
            ("r2/buckets", {**buckets, "result_info": {"total_count": False}}),
            ("r2/buckets", {"success": True, "result": {}}),
            ("workers/scripts", {"success": True, "result": [{"id": 7}]}),
            ("workers/scripts", ["not", "an", "object"]),
            ("workers/scripts", {"success": True, "result": [], "result_info": {"cursor": "next"}}),
            ("workers/scripts", {"success": True, "result": [], "result_info": {"total_count": -1}}),
            ("workers/scripts", {"success": True, "result": [], "result_info": ["malformed"]}),
            ("d1/database", {"success": True, "result": [], "result_info": {"total_count": 5}}),
            ("d1/database", {"success": True, "result": []}),
            ("d1/database", {"success": True, "result": {}, "result_info": {"total_count": 0}}),
            ("d1/database", {"success": True, "result": [{"uuid": "x"}], "result_info": {"total_count": 1}}),
            ("workers/scripts", {"success": False, "errors": [{"code": 1, "message": "no"}]}),
        ]
        for suffix, raw in cases:
            with self.subTest(suffix=suffix, raw=raw):
                self.f.fake(api_raw={suffix: raw})
                code, report = self.f.run("--path", str(self.f.wt))
                self.assertEqual(code, 3, report)
                self.assertEqual(self.unresolved_runs(), [self.RUN])

    def test_a_branch_change_in_the_same_worktree_keeps_an_unresolved_demo(self):
        self.f.claim()
        self.unresolved_demo(workers=[self.RUN])
        self.f.fake(release_fails=True)
        self.assertEqual(self.f.run("--path", str(self.f.wt))[0], 3)
        subprocess.run(["git", "-C", str(self.f.wt), "switch", "-q", "-c", "renamed-branch"], check=True)
        shutil.rmtree(self.f.wt / "artifacts")
        self.f.fake(release_fails=False)
        code, report = self.f.run("--path", str(self.f.wt), "--abandon", "branch dropped")
        self.assertEqual((code, report["status"]), (4, "deferred"), report)
        self.assertIn(self.RUN, report["remaining"][0]["reason"])

    def run_with_a_valid_and_an_invalid_entry_for_one_run(self, invalid_first):
        directory = self.f.wt / "artifacts" / "verified-build" / "r1"
        directory.mkdir(parents=True)
        valid = {"run": self.RUN, "worker": self.RUN, "d1": None, "account": ACCOUNT, "url": f"https://{self.RUN}.demos.keramos.tech", "worktree": str(self.f.wt), "branch": "feat"}
        invalid = {**valid, "worktree": "/somewhere/else"}
        (directory / "demos.json").write_text(json.dumps({"demos": [invalid, valid] if invalid_first else [valid, invalid]}))
        self.f.fake(workers=[self.RUN], d1=[], r2=[])
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual((code, report["status"]), (4, "deferred"), report)
        self.assertEqual([c for c in self.f.calls() if c.startswith("delete")], [])

    def test_an_invalid_entry_before_a_valid_one_for_the_same_run_deletes_nothing(self):
        self.run_with_a_valid_and_an_invalid_entry_for_one_run(invalid_first=True)

    def test_an_invalid_entry_after_a_valid_one_for_the_same_run_deletes_nothing(self):
        self.run_with_a_valid_and_an_invalid_entry_for_one_run(invalid_first=False)

    def conflicted_legacy_record(self, live):
        """A record that holds one run both as a deletable demo and as unresolved, as the base version could write, with its manifest gone."""
        if live:
            self.f.claim()
        self.unresolved_demo(workers=[self.RUN])
        if live:
            self.f.fake(release_fails=True)
            self.assertEqual(self.f.run("--path", str(self.f.wt))[0], 3)
            shutil.rmtree(self.f.wt / "artifacts")
            self.f.fake(release_fails=False)
        else:
            self.assertEqual(self.f.run("--path", str(self.f.wt))[0], 4)
        record = next(self.f.state_dir.glob("*.json"))
        data = json.loads(record.read_text())
        data["demos"] = [{"run": self.RUN, "worker": self.RUN, "d1": None}]
        record.write_text(json.dumps(data))
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual((code, report["status"]), (4, "deferred"), report)
        self.assertEqual([c for c in self.f.calls() if c.startswith("delete")], [])

    def test_a_record_holding_a_run_as_demo_and_as_unresolved_deletes_nothing_in_a_live_worktree(self):
        self.conflicted_legacy_record(live=True)

    def test_a_record_holding_a_run_as_demo_and_as_unresolved_deletes_nothing_once_the_worktree_is_gone(self):
        self.conflicted_legacy_record(live=False)

    def test_a_manifest_that_turns_a_recorded_valid_demo_unresolved_deletes_nothing(self):
        self.f.claim()
        self.f.demo()
        self.f.fake(release_fails=True)
        self.assertEqual(self.f.run("--path", str(self.f.wt))[0], 3)
        manifest = self.f.wt / "artifacts" / "verified-build" / "r1" / "demos.json"
        data = json.loads(manifest.read_text())
        data["demos"][0]["worktree"] = "/somewhere/else"
        manifest.write_text(json.dumps(data))
        self.f.fake(release_fails=False)
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual((code, report["status"]), (4, "deferred"), report)
        self.assertEqual([c for c in self.f.calls() if c.startswith("delete")], [])

    def test_the_account_token_is_never_sent_to_a_plain_http_host_that_is_not_loopback(self):
        self.unresolved_demo()
        self.f.api_base = "http://api.example.invalid/client/v4"
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual(code, 3, report)
        self.assertIn("not an https endpoint", report["error"])
        self.assertEqual(self.f.api.paths, [])

    def test_a_legacy_record_with_a_stringified_non_string_run_is_never_cleared(self):
        self.unresolved_demo(workers=[self.RUN])
        self.assertEqual(self.f.run("--path", str(self.f.wt))[0], 4)
        record = next(self.f.state_dir.glob("*.json"))
        data = json.loads(record.read_text())
        data["unresolved_demos"] = [{"run": "123", "reason": "run name missing or malformed", "manifest": data["unresolved_demos"][0]["manifest"]}]
        record.write_text(json.dumps(data))
        self.f.fake(workers=[], d1=[], r2=[])
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual((code, report["status"]), (4, "deferred"), report)

    def test_a_replacement_worktree_does_not_inherit_the_demos_of_the_one_it_replaced(self):
        self.f.claim()
        self.unresolved_demo(workers=[self.RUN])
        self.f.fake(release_fails=True)
        self.assertEqual(self.f.run("--path", str(self.f.wt))[0], 3)
        record = next(self.f.state_dir.glob("*.json"))
        data = json.loads(record.read_text())
        data["token"] = "token-of-the-removed-worktree"
        record.write_text(json.dumps(data))
        shutil.rmtree(self.f.wt / "artifacts")
        self.f.fake(release_fails=False)
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual((code, report["status"]), (0, "complete"), report)
        self.assertEqual([c for c in self.f.calls() if c.startswith("delete")], [])

    def test_demo_removed_cannot_be_combined_with_abandon(self):
        p = subprocess.run([str(SCRIPT), "--path", str(self.f.wt), "--abandon", "dropped", "--demo-removed", self.RUN], capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)
        self.assertIn("cannot be combined with --abandon", p.stderr)

    def test_a_redirect_from_the_api_is_not_followed_with_the_token(self):
        self.unresolved_demo()
        self.f.fake(api_redirect=True)
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual(code, 3, report)
        self.assertNotIn("/leak", self.f.api.paths)

    def test_a_run_name_that_is_not_a_string_is_never_cleared(self):
        self.f.demo(123, worker="x-run")
        self.f.fake(workers=[], d1=[])
        for _ in range(2):
            code, report = self.f.run("--path", str(self.f.wt))
            self.assertEqual((code, report["status"]), (4, "deferred"), report)
            self.assertIn("malformed", report["remaining"][0]["reason"])

    def test_every_name_a_run_declared_holds_it_across_entries_of_the_same_run(self):
        directory = self.f.wt / "artifacts" / "verified-build" / "r1"
        directory.mkdir(parents=True)
        entries = [{"run": self.RUN, "worker": name, "d1": None, "account": ACCOUNT, "url": f"https://{self.RUN}.demos.keramos.tech", "worktree": str(self.f.wt), "branch": "feat"} for name in ("renamed-a", "renamed-b")]
        (directory / "demos.json").write_text(json.dumps({"demos": entries}))
        self.f.fake(workers=["renamed-b"])
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual((code, report["status"]), (4, "deferred"), report)
        self.assertEqual(len(report["remaining"]), 1)
        self.assertIn("worker renamed-b", report["remaining"][0]["reason"])
        self.assertEqual(self.unresolved_runs(), [self.RUN])

    def test_a_record_from_before_declared_names_were_kept_is_checked_by_run_name(self):
        self.unresolved_demo(workers=[f"{self.RUN}-builder-lab001"])
        self.assertEqual(self.f.run("--path", str(self.f.wt))[0], 4)
        record = next(self.f.state_dir.glob("*.json"))
        data = json.loads(record.read_text())
        for u in data["unresolved_demos"]:
            del u["names"]
        record.write_text(json.dumps(data))
        self.assertEqual(self.f.run("--path", str(self.f.wt))[0], 4)
        self.f.fake(workers=[])
        self.assertEqual(self.f.run("--path", str(self.f.wt))[0], 0)

    def test_a_rerun_in_a_live_worktree_keeps_an_unresolved_demo_whose_manifest_is_gone(self):
        self.f.claim()
        self.unresolved_demo(workers=[self.RUN])
        self.f.fake(release_fails=True)
        self.assertEqual(self.f.run("--path", str(self.f.wt))[0], 3)
        shutil.rmtree(self.f.wt / "artifacts")
        self.f.fake(release_fails=False)
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual((code, report["status"]), (4, "deferred"), report)
        self.assertIn(self.RUN, report["remaining"][0]["reason"])

    def test_demo_removed_names_several_runs_and_refuses_on_any_of_them(self):
        other = "old-proto-20260101-deadbeef"
        directory = self.f.wt / "artifacts" / "verified-build" / "r2"
        directory.mkdir(parents=True)
        (directory / "run.md").write_text(f"demo: https://{other}.demos.keramos.tech\n")
        self.unresolved_demo(workers=[f"{other}-writer"])
        code, report = self.f.run("--path", str(self.f.wt), "--demo-removed", self.RUN, "--demo-removed", other)
        self.assertEqual((code, report["code"]), (2, "REFUSE-DEMO-PRESENT"), report)
        self.assertIn(other, report["error"])
        self.assertNotIn(self.RUN, report["error"])
        self.f.fake(workers=[])
        code, report = self.f.run("--path", str(self.f.wt), "--demo-removed", self.RUN, "--demo-removed", other)
        self.assertEqual((code, report["status"]), (0, "complete"), report)

    def test_show_record_takes_no_demo_removed(self):
        p = subprocess.run([str(SCRIPT), "--show-record", str(self.f.wt), "--demo-removed", self.RUN], capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)
        self.assertIn("takes no other option", p.stderr)

    def test_a_demo_found_again_by_every_run_is_recorded_once(self):
        self.f.claim()
        self.unresolved_demo(workers=[self.RUN])
        self.f.fake(release_fails=True)
        for _ in range(2):
            self.assertEqual(self.f.run("--path", str(self.f.wt))[0], 3)
        self.assertEqual(self.unresolved_runs(), [self.RUN])

    def test_demo_removed_is_refused_while_a_matching_worker_d1_or_r2_name_exists(self):
        self.f.claim()
        self.unresolved_demo()
        for account in ({"workers": [f"{self.RUN}-writer-lab017"]}, {"workers": [], "d1": [f"{self.RUN}-feedback"]}, {"d1": [], "r2": [f"{self.RUN}-packs"]}):
            with self.subTest(account=account):
                self.f.fake(**account)
                code, report = self.f.run("--path", str(self.f.wt), "--demo-removed", self.RUN)
                self.assertEqual((code, report["status"], report["code"]), (2, "refused", "REFUSE-DEMO-PRESENT"), report)
                self.assertEqual([step["id"] for step in report["steps"]], ["preflight"])
                self.assertEqual(self.f.calls(), [])
                self.assertTrue(self.f.wt.exists() and self.f.remote_has_branch())
        self.f.fake(r2=[])
        code, report = self.f.run("--path", str(self.f.wt), "--demo-removed", self.RUN)
        self.assertEqual((code, report["status"]), (0, "complete"), report)
        self.assertFalse(self.f.wt.exists())
        self.assertEqual(self.unresolved_runs(), [])

    def test_demo_removed_refuses_a_run_the_record_does_not_hold_as_unresolved(self):
        self.unresolved_demo()
        code, report = self.f.run("--path", str(self.f.wt), "--demo-removed", "no-such-demo")
        self.assertEqual((code, report["code"]), (2, "REFUSE-NO-SUCH-DEMO"), report)
        self.assertTrue(self.f.wt.exists())

    def test_remote_branch_with_unchecked_commits_is_kept(self):
        other = self.f.tmp / "other"
        subprocess.run(["git", "clone", "-q", "-b", "feat", str(self.f.origin), str(other)], check=True, capture_output=True)
        git(other, "config", "user.email", "t@example.com")
        git(other, "config", "user.name", "t")
        (other / "extra.txt").write_text("pushed after merge\n")
        git(other, "add", ".")
        git(other, "commit", "-qm", "late")
        git(other, "push", "-q", "origin", "feat")
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual(code, 4, report)
        self.assertTrue(self.f.remote_has_branch())
        self.assertEqual(self.f.step(report, "remote_branch")["status"], "deferred")

    def test_running_agent_in_the_worktree_is_refused(self):
        self.f.fake(agents=[{"id": "a-1", "shortId": "a1", "status": "running", "cwd": str(self.f.wt)}])
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual(code, 2)
        self.assertIn("still running", report["error"])

    def test_plain_worktree_without_paseo_is_removed_with_git(self):
        self.f.fake(workspaces=[])
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual(code, 0, report)
        self.assertEqual(self.f.step(report, "workspace")["note"], "git worktree remove")
        self.assertFalse(self.f.wt.exists())

    def test_main_checkout_and_unknown_paths_are_refused(self):
        code, report = self.f.run("--path", str(self.f.main))
        self.assertEqual((code, report["status"]), (2, "refused"))
        self.assertIn("main checkout", report["error"])
        code, report = self.f.run("--path", str(self.f.tmp / "never-existed"))
        self.assertEqual(code, 2)
        self.assertIn("nothing to resume", report["error"])
        self.assertEqual(report["code"], "REFUSE-GONE-NO-RECORD")
        self.assertIn("REFUSE-GONE-NO-RECORD", self.f.last_stderr)

    def record_then_remove_worktree(self):
        """Run inside the target so preflight saves the record and the archive is deferred, then drop the worktree."""
        code, report = self.f.run(cwd=self.f.wt)
        self.assertEqual(code, 4, report)
        git(self.f.main, "worktree", "remove", "--force", str(self.f.wt))

    def test_workspace_with_the_recorded_id_but_a_different_cwd_is_not_archived(self):
        self.record_then_remove_worktree()
        elsewhere = self.f.tmp / "someone-elses-worktree"
        self.f.fake(workspaces=[{"workspaceId": "wks_1", "cwd": str(elsewhere), "repo": str(self.f.main)}])
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual((code, report["status"]), (0, "complete"), report)
        self.assertEqual(self.f.step(report, "workspace")["status"], "already_done")
        self.assertNotIn("archive wks_1", self.f.calls())
        self.assertEqual([w["workspaceId"] for w in json.loads(self.f.fake_state.read_text())["workspaces"]], ["wks_1"])

    def test_workspace_with_the_recorded_id_and_the_recorded_cwd_is_archived(self):
        self.record_then_remove_worktree()
        self.f.fake(workspaces=[{"workspaceId": "wks_1", "cwd": str(self.f.wt), "repo": str(self.f.main)}], archive_keeps_dir=True)
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual((code, report["status"]), (0, "complete"), report)
        self.assertEqual(self.f.step(report, "workspace")["status"], "done")
        self.assertIn("archive wks_1", self.f.calls())

    def test_every_refusal_carries_a_stable_code(self):
        (self.f.wt / "scratch.txt").write_text("uncommitted\n")
        cases = [
            (("--path", str(self.f.wt)), "REFUSE-PREFLIGHT"),
            (("--path", str(self.f.main)), "REFUSE-MAIN-CHECKOUT"),
            (("--path", str(self.f.tmp / "plain")), "REFUSE-GONE-NO-RECORD"),
            (("--workspace", "wks_nope"), "REFUSE-UNKNOWN-WORKSPACE"),
        ]
        for args, expected in cases:
            code, report = self.f.run(*args)
            self.assertEqual((code, report["status"], report["code"]), (2, "refused", expected), report)

    def test_a_completed_run_has_no_refusal_code(self):
        code, report = self.f.run("--workspace", "wks_1")
        self.assertEqual((code, report["code"]), (0, None), report)

    def test_show_record_prints_the_record_by_path_or_workspace_id(self):
        self.record_then_remove_worktree()
        self.f.fake(workspaces=[])
        by_path_code, by_path = self.f.run("--show-record", str(self.f.wt))
        by_id_code, by_id = self.f.run("--show-record", "wks_1")
        self.assertEqual((by_path_code, by_id_code), (0, 0))
        self.assertEqual(by_path, by_id)
        self.assertEqual((by_path["workspace_id"], by_path["path"], by_path["branch"], by_path["head"]), ("wks_1", str(self.f.wt), "feat", self.f.head))

    def test_show_record_by_a_workspace_id_held_by_two_records_is_refused_but_a_path_still_works(self):
        self.record_then_remove_worktree()
        code, record = self.f.run("--show-record", str(self.f.wt))
        other = str(self.f.tmp / "other-worktree")
        key = hashlib.sha256(other.encode()).hexdigest()[:16]
        (self.f.state_dir / f"{key}.json").write_text(json.dumps({**record, "path": other}))
        code, report = self.f.run("--show-record", "wks_1")
        self.assertEqual((code, report["code"]), (2, "REFUSE-AMBIGUOUS-RECORD"), report)
        code, report = self.f.run("--show-record", str(self.f.wt))
        self.assertEqual((code, report["path"]), (0, str(self.f.wt)), report)

    def test_show_record_without_a_record_is_refused_and_changes_nothing(self):
        code, report = self.f.run("--show-record", "wks_1")
        self.assertEqual((code, report["status"], report["code"]), (2, "refused", "REFUSE-NO-RECORD"), report)
        self.assertIn("REFUSE-NO-RECORD:", self.f.last_stderr)
        code, report = self.f.run("--show-record", str(self.f.wt))
        self.assertEqual((code, report["code"]), (2, "REFUSE-NO-RECORD"), report)
        self.assertEqual(self.f.calls(), [])
        self.assertTrue(self.f.wt.exists())

    def test_workspace_that_misses_falls_back_to_the_record_found_by_path(self):
        self.record_then_remove_worktree()
        self.f.fake(workspaces=[])
        code, report = self.f.run("--workspace", "wks_renamed")
        self.assertEqual((code, report["code"]), (2, "REFUSE-UNKNOWN-WORKSPACE"), report)
        code, report = self.f.run("--workspace", "wks_renamed", "--path", str(self.f.wt))
        self.assertEqual((code, report["status"]), (0, "complete"), report)
        self.assertFalse(self.f.remote_has_branch())

    def test_workspace_and_path_that_name_different_worktrees_are_refused(self):
        code, report = self.f.run("--workspace", "wks_1", "--path", str(self.f.main))
        self.assertEqual((code, report["code"]), (2, "REFUSE-TARGET-CONFLICT"), report)
        self.assertTrue(self.f.wt.exists())

    def test_workspace_that_misses_without_a_record_at_the_path_is_refused_and_nothing_changes(self):
        code, report = self.f.run("--workspace", "wks_typo", "--path", str(self.f.wt))
        self.assertEqual((code, report["code"]), (2, "REFUSE-UNKNOWN-WORKSPACE"), report)
        self.assertEqual(self.f.calls(), [])
        self.assertTrue(self.f.wt.exists())
        self.assertTrue(self.f.remote_has_branch())

    def test_resume_command_after_the_workspace_id_is_reused_for_another_path_is_refused(self):
        code, report = self.f.run(cwd=self.f.wt)
        self.assertEqual(code, 4, report)
        elsewhere = self.f.tmp / "someone-elses-worktree"
        self.f.fake(workspaces=[{"workspaceId": "wks_1", "cwd": str(elsewhere), "repo": str(self.f.main)}])
        code, report = self.f.run(*report["resume"].split()[1:], cwd=self.f.main)
        self.assertEqual((code, report["code"]), (2, "REFUSE-TARGET-CONFLICT"), report)
        self.assertEqual(self.f.calls(), [])
        self.assertTrue(self.f.wt.exists())

    def test_a_subdirectory_of_the_worktree_we_run_in_still_defers_the_archive(self):
        (self.f.wt / "sub").mkdir()
        code, report = self.f.run("--path", str(self.f.wt / "sub"), cwd=self.f.wt)
        self.assertEqual((code, report["status"], report["mode"]), (4, "deferred", "self"), report)
        self.assertTrue(self.f.wt.exists())
        self.assertEqual(self.f.calls(), [])

    def test_resume_command_after_the_workspace_id_is_reused_for_an_ancestor_directory_is_refused(self):
        code, report = self.f.run(cwd=self.f.wt)
        self.assertEqual(code, 4, report)
        self.f.fake(workspaces=[{"workspaceId": "wks_1", "cwd": str(self.f.tmp), "repo": str(self.f.main)}])
        code, report = self.f.run(*report["resume"].split()[1:], cwd=self.f.main)
        self.assertEqual((code, report["code"]), (2, "REFUSE-TARGET-CONFLICT"), report)
        self.assertEqual(self.f.calls(), [])
        self.assertTrue(self.f.wt.exists())

    def test_unknown_workspace_id_with_a_path_now_owned_by_another_workspace_is_refused(self):
        code, report = self.f.run(cwd=self.f.wt)
        self.assertEqual(code, 4, report)
        self.f.fake(workspaces=[{"workspaceId": "wks_new", "cwd": str(self.f.wt), "repo": str(self.f.main)}])
        code, report = self.f.run("--workspace", "wks_typo", "--path", str(self.f.wt), cwd=self.f.main)
        self.assertEqual((code, report["code"]), (2, "REFUSE-TARGET-CONFLICT"), report)
        self.assertEqual(self.f.calls(), [])
        self.assertTrue(self.f.wt.exists())

    def test_unknown_workspace_id_with_a_new_workspace_rooted_in_a_subdirectory_is_refused_before_any_release(self):
        code, report = self.f.run(cwd=self.f.wt)
        self.assertEqual(code, 4, report)
        self.f.claim()
        (self.f.wt / "sub").mkdir()
        self.f.fake(workspaces=[{"workspaceId": "wks_new", "cwd": str(self.f.wt / "sub"), "repo": str(self.f.main)}])
        code, report = self.f.run("--workspace", "wks_typo", "--path", str(self.f.wt), cwd=self.f.main)
        self.assertEqual((code, report["code"]), (2, "REFUSE-TARGET-CONFLICT"), report)
        self.assertFalse(report.get("resume"), report)
        self.assertEqual(self.f.calls(), [])
        self.assertTrue((self.f.wt / ".ccore" / "lab-claim.json").exists())

    def test_resume_command_after_another_workspace_took_over_the_path_is_refused_and_removes_nothing(self):
        code, report = self.f.run(cwd=self.f.wt)
        self.assertEqual(code, 4, report)
        self.f.fake(workspaces=[{"workspaceId": "wks_new", "cwd": str(self.f.wt), "repo": str(self.f.main)}])
        code, report = self.f.run(*report["resume"].split()[1:], cwd=self.f.main)
        self.assertEqual((code, report["code"]), (2, "REFUSE-TARGET-CONFLICT"), report)
        self.assertEqual(self.f.calls(), [])
        self.assertTrue(self.f.wt.exists())
        self.assertTrue(self.f.remote_has_branch())

    def test_a_paseo_outage_is_not_read_as_the_workspace_being_gone(self):
        code, report = self.f.run(cwd=self.f.wt)
        self.assertEqual(code, 4, report)
        self.f.fake(paseo_down=True)
        code, report = self.f.run(*report["resume"].split()[1:], cwd=self.f.main)
        self.assertEqual((code, report["code"]), (2, "REFUSE-PASEO-UNAVAILABLE"), report)
        self.assertEqual(self.f.calls(), [])
        self.assertTrue(self.f.wt.exists())
        self.assertTrue(self.f.remote_has_branch())

    def test_a_workspace_that_takes_over_the_path_after_resolution_is_not_removed_with_git(self):
        code, report = self.f.run(cwd=self.f.wt)
        self.assertEqual(code, 4, report)
        recorded = {"workspaceId": "wks_1", "cwd": str(self.f.wt), "repo": str(self.f.main)}
        moved = {**recorded, "cwd": str(self.f.tmp / "elsewhere")}
        taker = {"workspaceId": "wks_other", "cwd": str(self.f.wt), "repo": str(self.f.main)}
        self.f.fake(ls_script=[[recorded], [moved, taker]])
        code, report = self.f.run(*report["resume"].split()[1:], cwd=self.f.main)
        self.assertEqual((code, report["status"]), (4, "deferred"), report)
        self.assertEqual(self.f.step(report, "workspace")["note"], "path used by another workspace")
        self.assertTrue(self.f.wt.exists())
        self.assertTrue(self.f.remote_has_branch())

    def test_a_paseo_outage_after_resolution_fails_the_workspace_step_instead_of_removing_with_git(self):
        code, report = self.f.run(cwd=self.f.wt)
        self.assertEqual(code, 4, report)
        self.f.fake(ls_script=[[], [], [], None])
        code, report = self.f.run("--workspace", "wks_gone", "--path", str(self.f.wt), cwd=self.f.main)
        self.assertEqual((code, report["status"]), (3, "failed"), report)
        self.assertEqual(self.f.step(report, "workspace")["status"], "failed")
        self.assertTrue(self.f.wt.exists())
        self.assertTrue(self.f.remote_has_branch())
        self.assertIn("--workspace wks_1", report["resume"])
        code, report = self.f.run(*report["resume"].split()[1:], cwd=self.f.main)
        self.assertEqual((code, report["code"]), (2, "REFUSE-PASEO-UNAVAILABLE"), report)
        self.assertTrue(self.f.wt.exists())
        self.assertTrue(self.f.remote_has_branch())

    def test_a_fallback_never_adopts_an_owner_that_appears_in_one_listing(self):
        code, report = self.f.run(cwd=self.f.wt)
        self.assertEqual(code, 4, report)
        new = {"workspaceId": "wks_new", "cwd": str(self.f.wt), "repo": str(self.f.main)}
        self.f.fake(ls_script=[[], [new], []])
        code, report = self.f.run("--workspace", "wks_typo", "--path", str(self.f.wt), cwd=self.f.main)
        self.assertEqual((code, report["code"]), (2, "REFUSE-TARGET-CONFLICT"), report)
        self.assertFalse(report.get("resume"), report)
        self.assertEqual(self.f.calls(), [])
        self.assertTrue(self.f.wt.exists())
        self.assertTrue(self.f.remote_has_branch())

    def test_a_fallback_never_cleans_a_different_worktree_that_now_holds_the_path(self):
        self.record_then_remove_worktree()
        git(self.f.main, "worktree", "add", "-b", "replacement", str(self.f.wt))
        code, report = self.f.run("--workspace", "wks_typo", "--path", str(self.f.wt), cwd=self.f.main)
        self.assertEqual((code, report["code"]), (2, "REFUSE-TARGET-CONFLICT"), report)
        self.assertFalse(report.get("resume"), report)
        self.assertEqual(self.f.calls(), [])
        self.assertTrue(self.f.wt.exists())
        self.assertTrue(self.f.remote_has_branch())

    def test_a_fallback_never_cleans_a_replacement_worktree_on_the_same_branch_and_path(self):
        self.record_then_remove_worktree()
        code, record = self.f.run("--show-record", str(self.f.wt))
        self.assertEqual(code, 0, record)
        git(self.f.main, "worktree", "add", str(self.f.wt), record["branch"])
        self.f.claim()
        code, report = self.f.run("--workspace", "wks_typo", "--path", str(self.f.wt), cwd=self.f.main)
        self.assertEqual((code, report["code"]), (2, "REFUSE-TARGET-CONFLICT"), report)
        self.assertFalse(report.get("resume"), report)
        self.assertEqual(self.f.calls(), [])
        self.assertTrue((self.f.wt / ".ccore" / "lab-claim.json").exists())
        self.assertTrue(self.f.remote_has_branch())

    def test_a_fallback_never_cleans_another_branch_checked_out_in_the_recorded_worktree(self):
        code, report = self.f.run(cwd=self.f.wt)
        self.assertEqual(code, 4, report)
        git(self.f.wt, "switch", "-c", "other-work")
        self.f.claim()
        code, report = self.f.run("--workspace", "wks_typo", "--path", str(self.f.wt), cwd=self.f.main)
        self.assertEqual((code, report["code"]), (2, "REFUSE-TARGET-CONFLICT"), report)
        self.assertFalse(report.get("resume"), report)
        self.assertEqual(self.f.calls(), [])
        self.assertTrue((self.f.wt / ".ccore" / "lab-claim.json").exists())
        self.assertTrue(self.f.remote_has_branch())

    def test_a_fallback_for_a_removed_nested_worktree_never_resolves_to_the_enclosing_one(self):
        code, report = self.f.run(cwd=self.f.wt)
        self.assertEqual(code, 4, report)
        code, record = self.f.run("--show-record", str(self.f.wt))
        self.assertEqual(code, 0, record)
        nested = self.f.wt / "nested"
        nested.mkdir()
        nested_real = str(nested.resolve())
        key = hashlib.sha256(nested_real.encode()).hexdigest()[:16]
        (self.f.state_dir / f"{key}.json").write_text(json.dumps({**record, "path": nested_real, "workspace_id": "wks_nested"}))
        self.f.claim()
        self.f.fake(workspaces=[])
        code, report = self.f.run("--workspace", "wks_typo", "--path", str(nested), cwd=self.f.main)
        self.assertEqual((code, report["code"]), (2, "REFUSE-TARGET-CONFLICT"), report)
        self.assertFalse(report.get("resume"), report)
        self.assertEqual(self.f.calls(), [])
        self.assertTrue((self.f.wt / ".ccore" / "lab-claim.json").exists())
        self.assertTrue(self.f.remote_has_branch())

    def test_a_listed_workspace_with_a_recorded_nested_path_never_resolves_to_the_enclosing_worktree(self):
        code, report = self.f.run(cwd=self.f.wt)
        self.assertEqual(code, 4, report)
        code, record = self.f.run("--show-record", str(self.f.wt))
        self.assertEqual(code, 0, record)
        nested = self.f.wt / "nested"
        nested.mkdir()
        nested_real = str(nested.resolve())
        key = hashlib.sha256(nested_real.encode()).hexdigest()[:16]
        (self.f.state_dir / f"{key}.json").write_text(json.dumps({**record, "path": nested_real, "workspace_id": "wks_1"}))
        self.f.claim()
        code, report = self.f.run("--workspace", "wks_1", "--path", str(nested), cwd=self.f.main)
        self.assertEqual((code, report["code"]), (2, "REFUSE-TARGET-CONFLICT"), report)
        self.assertFalse(report.get("resume"), report)
        self.assertEqual(self.f.calls(), [])
        self.assertTrue((self.f.wt / ".ccore" / "lab-claim.json").exists())
        self.assertTrue(self.f.remote_has_branch())

    def test_the_resume_command_quotes_an_unmatched_workspace_argument(self):
        self.f.fake(workspaces=[])
        code, report = self.f.run(cwd=self.f.wt)
        self.assertEqual(code, 4, report)
        self.f.fake(ls_script=[[], [], [], None])
        code, report = self.f.run("--workspace", "wks gone;echo injected;#", "--path", str(self.f.wt), cwd=self.f.main)
        self.assertEqual((code, report["status"]), (3, "failed"), report)
        self.assertIn("--workspace 'wks gone;echo injected;#' --path", report["resume"])

    def test_a_fallback_to_a_record_without_a_workspace_keeps_requiring_paseo_on_resume(self):
        self.f.fake(workspaces=[])
        code, report = self.f.run(cwd=self.f.wt)
        self.assertEqual(code, 4, report)
        self.f.fake(ls_script=[[], [], [], None])
        code, report = self.f.run("--workspace", "wks_gone", "--path", str(self.f.wt), cwd=self.f.main)
        self.assertEqual((code, report["status"]), (3, "failed"), report)
        self.assertIn("--workspace wks_gone", report["resume"])
        code, report = self.f.run(*report["resume"].split()[1:], cwd=self.f.main)
        self.assertEqual((code, report["code"]), (2, "REFUSE-PASEO-UNAVAILABLE"), report)
        self.assertTrue(self.f.wt.exists())
        self.assertTrue(self.f.remote_has_branch())

    def test_a_workspace_rooted_in_a_subdirectory_keeps_the_worktree_from_being_removed(self):
        code, report = self.f.run(cwd=self.f.wt)
        self.assertEqual(code, 4, report)
        (self.f.wt / "sub").mkdir()
        self.f.fake(workspaces=[{"workspaceId": "wks_1", "cwd": str(self.f.wt / "sub"), "repo": str(self.f.main)}])
        code, report = self.f.run("--workspace", "wks_1", cwd=self.f.main)
        self.assertEqual((code, report["status"]), (4, "deferred"), report)
        self.assertEqual(self.f.step(report, "workspace")["note"], "path used by another workspace")
        self.assertEqual(self.f.calls(), [])
        self.assertTrue(self.f.wt.exists())
        self.assertTrue(self.f.remote_has_branch())

    def test_resume_command_for_a_workspace_rooted_in_a_subdirectory_reaches_the_deferral_not_a_false_conflict(self):
        (self.f.wt / "sub").mkdir()
        self.f.fake(workspaces=[{"workspaceId": "wks_1", "cwd": str(self.f.wt / "sub"), "repo": str(self.f.main)}])
        code, report = self.f.run("--workspace", "wks_1", cwd=self.f.wt)
        self.assertEqual(code, 4, report)
        code, report = self.f.run(*report["resume"].split()[1:], cwd=self.f.main)
        self.assertEqual((code, report["status"]), (4, "deferred"), report)
        self.assertEqual(self.f.step(report, "workspace")["note"], "path used by another workspace")
        self.assertTrue(self.f.wt.exists())


if __name__ == "__main__":
    unittest.main()
