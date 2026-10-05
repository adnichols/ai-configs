"""Behavior tests for skills/worktree-cleanup/scripts/worktree_cleanup.py.

Each test builds a real bare origin, a clone and a linked worktree, and puts fake
gh/paseo/pnpm/wrangler on PATH (see fixtures/worktree_cleanup_fakes.py). Git runs for real.
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills" / "worktree-cleanup" / "scripts" / "worktree_cleanup.py"
FAKES = Path(__file__).resolve().parent / "fixtures" / "worktree_cleanup_fakes.py"
ACCOUNT = "e6d3e575b97001f8ad1a7e98e497afa5"
PR_URL = "https://github.com/acme/widgets/pull/7"


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True).stdout.strip()


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
        for tool in ("gh", "paseo", "pnpm", "wrangler"):
            shim = self.bin / tool
            shim.write_text(f'#!/bin/sh\nexec python3 "{FAKES}" {tool} "$@"\n')
            shim.chmod(0o755)
        self.fake_state.write_text(
            json.dumps(
                {
                    "calls": [],
                    "prs": [{"number": 7, "url": PR_URL, "state": "MERGED", "headRefName": "feat", "baseRefName": "main", "headRefOid": self.head, "headRepositoryOwner": {"login": "acme"}}],
                    "workspaces": [{"workspaceId": "wks_1", "cwd": str(self.wt), "repo": str(self.main)}],
                    "agents": [],
                    "lab_claim": None,
                    "lab_state": "provisioned",
                    "deprovisions": True,
                    "workers": [],
                    "d1": [],
                }
            )
        )

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
        env = {**os.environ, "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}", "FAKE_STATE": str(self.fake_state), "WORKTREE_CLEANUP_STATE_DIR": str(self.state_dir), "PASEO_HOME": str(self.tmp / "paseo")}
        env.pop("PASEO_AGENT_ID", None)
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
        self.assertIn("not the head of a merged PR", report["error"])

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
        code, report = self.f.run("--path", str(self.f.wt))
        self.assertEqual(code, 4, report)
        self.assertIn("old-proto-20260101-deadbeef", report["remaining"][0]["reason"])

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


if __name__ == "__main__":
    unittest.main()
