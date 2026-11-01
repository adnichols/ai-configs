"""Behavior tests for skills/workstream-owner/scripts/start_wks.py.

Each test builds a real bare origin and its main checkout, and puts the fake paseo of fixtures/start_wks_fakes.py on PATH,
installed as npm installs the real CLI (bin/paseo beside dist/), with fixtures/start_wks_fake_client.mjs as its daemon
client. Git and node run for real. The script runs as an agent would run it: with PASEO_AGENT_ID set.
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills" / "workstream-owner" / "scripts" / "start_wks.py"
FAKES = Path(__file__).resolve().parent / "fixtures" / "start_wks_fakes.py"
FAKE_CLIENT = Path(__file__).resolve().parent / "fixtures" / "start_wks_fake_client.mjs"
DOC = "https://nodaste.hub.avalandra.com/d/27bff766"
CALLER = "e7558b3c-0d83-44db-841d-55733165fc30"


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True).stdout.strip()


class StartWksTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.origin, self.checkout, self.bin = self.tmp / "origin.git", self.tmp / "repo", self.tmp / "bin"
        self.env = dict(os.environ, HOME=str(self.tmp), GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
                        GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com",
                        START_WKS_FAKE_STATE=str(self.tmp / "fake.json"), PASEO_AGENT_ID=CALLER)
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(self.origin)], check=True)
        subprocess.run(["git", "clone", "-q", str(self.origin), str(self.checkout)], check=True, capture_output=True)
        (self.checkout / "README").write_text("hi\n")
        subprocess.run(["git", "-C", str(self.checkout), "add", "."], check=True, env=self.env)
        subprocess.run(["git", "-C", str(self.checkout), "commit", "-qm", "init"], check=True, env=self.env)
        git(self.checkout, "push", "-q", "origin", "main")
        self.base = git(self.checkout, "rev-parse", "HEAD")
        cli = self.tmp / "lib" / "node_modules" / "@getpaseo" / "cli"
        (cli / "bin").mkdir(parents=True)
        (cli / "dist" / "utils").mkdir(parents=True)
        (cli / "package.json").write_text('{"type": "module"}\n')
        shim = cli / "bin" / "paseo"
        shim.write_text(f'#!/bin/sh\nexec python3 "{FAKES}" "$@"\n')
        shim.chmod(0o755)
        (cli / "dist" / "utils" / "client.js").write_text(f'export {{ connectToDaemon }} from "{FAKE_CLIENT.as_uri()}";\n')
        (cli / "dist" / "utils" / "daemon-target.js").write_text(f'export {{ selectDaemonTarget }} from "{FAKE_CLIENT.as_uri()}";\n')
        self.bin.mkdir()
        (self.bin / "paseo").symlink_to(shim)
        self.env["PATH"] = f"{self.bin}:{os.environ['PATH']}"
        self.write_state(calls=[], workspaces=[], agents=[], heartbeats=[], remote={}, worktrees=str(self.tmp / "worktrees"))

    def tearDown(self):
        subprocess.run(["rm", "-rf", str(self.tmp)], check=True)

    def write_state(self, **state):
        (self.tmp / "fake.json").write_text(json.dumps(state))

    def state(self):
        return json.loads((self.tmp / "fake.json").read_text())

    def update_state(self, **updates):
        self.write_state(**dict(self.state(), **updates))

    def write_hosts(self, *names):
        hosts = [{"name": n, "target": f"ssh://{n}", "hostnames": [f"{n}.invalid"]} for n in names]
        path = self.tmp / ".config" / "orchestrate" / "hosts.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"hosts": hosts}))

    def start(self, *extra, name="Ava  format"):
        p = subprocess.run(["python3", str(SCRIPT), "--name", name, "--source", DOC, "--checkout", str(self.checkout), *extra],
                           capture_output=True, text=True, env=self.env, cwd=self.tmp)
        return p.returncode, json.loads(p.stdout)

    def orchestrator_view(self):
        """What the orchestrator's sweep lists: `paseo workspace ls --json`, without --background."""
        p = subprocess.run(["paseo", "workspace", "ls", "--json"], capture_output=True, text=True, env=self.env, check=True)
        return json.loads(p.stdout)

    def local_branch(self, branch="wks/ava-format"):
        return subprocess.run(["git", "-C", str(self.checkout), "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"],
                              capture_output=True, text=True).stdout.strip()

    def created_workspaces(self):
        return [c for c in self.state()["calls"] if c[:2] == ["workspace", "create"]]

    def assert_nothing_remains(self):
        self.assertEqual((self.state()["workspaces"], self.state()["agents"]), ([], []))
        self.assertEqual([h for h in self.state()["heartbeats"] if h["status"] == "active"], [])
        self.assertEqual(self.local_branch(), "")

    def test_starts_a_top_level_owner_the_orchestrator_can_see(self):
        code, report = self.start("--note", "Ship behind the toggle.")

        self.assertEqual(code, 0, report)
        [ws] = self.orchestrator_view()
        [agent] = self.state()["agents"]
        self.assertEqual((ws["name"], ws["isolation"]), ("WKS Ava format", "worktree"))
        self.assertEqual(git(ws["cwd"], "rev-parse", "--abbrev-ref", "HEAD"), "wks/ava-format")
        self.assertEqual(git(ws["cwd"], "rev-parse", "HEAD"), self.base)
        self.assertEqual(agent["Name"], "WKS Ava format")
        self.assertIsNone(agent["ParentAgentId"], "launched from inside an agent, the owner must still be top-level")
        self.assertEqual(agent["Cwd"], ws["cwd"])
        for text in (DOC, "Ship behind the toggle.", "skill://workstream-owner", ws["workspaceId"], self.base):
            self.assertIn(text, agent["Prompt"])
        self.assertEqual((report["agent"], report["workspace"], report["base_sha"]), (agent["Id"], ws["workspaceId"], self.base))
        self.assertEqual((report["pinned"], self.state().get("pins")), (True, [ws["workspaceId"]]))
        [heartbeat] = self.state()["heartbeats"]
        self.assertEqual(heartbeat["agentId"], agent["Id"], "the heartbeat must prompt the owner, not the agent that ran the script")
        self.assertEqual((heartbeat["name"], heartbeat["cron"], heartbeat["status"], report["heartbeat"]),
                         ("WKS Ava format progress", "*/30 * * * *", "active", heartbeat["id"]))
        self.assertIn('Progress check for the WKS workstream "Ava format"', heartbeat["prompt"])
        self.assertNotIn(DOC, heartbeat["prompt"], "the heartbeat's prompt is its own, not the owner's brief")

    def test_a_heartbeat_the_daemon_rejects_rolls_the_start_back(self):
        self.update_state(heartbeat_fails=True)

        code, report = self.start()

        self.assertEqual(code, 3)
        self.assertIn("heartbeat", report["error"])
        self.assertEqual(report["left"], [])
        self.assert_nothing_remains()

    def test_a_heartbeat_that_lands_on_another_agent_is_deleted_and_the_start_rolled_back(self):
        self.update_state(heartbeat_target=CALLER)

        code, report = self.start()

        self.assertEqual(code, 3)
        self.assertIn("not the owner", report["error"])
        self.assertEqual(self.state()["heartbeats"], [])
        self.assert_nothing_remains()

    def test_a_failed_pin_still_leaves_the_owner_started_and_says_why(self):
        self.update_state(pin_fails=True)

        code, report = self.start()

        self.assertEqual(code, 0, report)
        self.assertEqual(report["pinned"], False)
        self.assertIn("setWorkspacePinned rejected", report["pin_error"])
        [ws] = self.orchestrator_view()
        [agent] = self.state()["agents"]
        self.assertEqual((report["workspace"], report["agent"]), (ws["workspaceId"], agent["Id"]))

    def test_a_paseo_install_without_the_daemon_client_still_starts_the_owner_unpinned(self):
        (self.tmp / "lib" / "node_modules" / "@getpaseo" / "cli" / "dist" / "utils" / "client.js").unlink()

        code, report = self.start()

        self.assertEqual(code, 0, report)
        self.assertEqual(report["pinned"], False)
        self.assertIn("no paseo CLI dist found", report["pin_error"])
        self.assertEqual([w["workspaceId"] for w in self.orchestrator_view()], [report["workspace"]])

    def test_dry_run_creates_nothing(self):
        code, report = self.start("--dry-run")

        self.assertEqual((code, report["result"]), (0, "dry-run"))
        self.assertIn(DOC, report["brief"])
        self.assertEqual(report["heartbeat_cron"], "*/30 * * * *")
        self.assertIn('Progress check for the WKS workstream "Ava format"', report["heartbeat_prompt"])
        self.assertEqual(self.created_workspaces(), [])
        self.assert_nothing_remains()

    def test_bad_arguments_exit_1_with_the_error(self):
        p = subprocess.run(["python3", str(SCRIPT), "--name", "x"], capture_output=True, text=True, env=self.env)

        self.assertEqual(p.returncode, 1)
        self.assertIn("--source", json.loads(p.stdout)["error"])

    def test_refuses_a_second_workspace_with_the_same_wks_title(self):
        self.update_state(workspaces=[{"workspaceId": "wks_old", "name": " WKS ava FORMAT ", "isolation": "worktree",
                                       "cwd": str(self.tmp / "old"), "background": True}])

        code, report = self.start()

        self.assertEqual(code, 2)
        self.assertIn("wks_old", report["error"])
        self.assertEqual(self.created_workspaces(), [])

    def test_refuses_a_wks_workspace_with_the_same_title_on_another_host(self):
        self.write_hosts("farhost")
        self.update_state(remote={"ssh://farhost": [{"workspaceId": "wks_farhost", "name": "WKS Ava format",
                                                   "isolation": "worktree", "cwd": "/home/x", "background": False}]})

        code, report = self.start()

        self.assertEqual(code, 2)
        self.assertIn("wks_farhost on farhost", report["error"])
        self.assertEqual(self.created_workspaces(), [])

    def test_an_unreachable_host_does_not_block_the_start_and_is_reported(self):
        self.write_hosts("downhost")

        code, report = self.start()

        self.assertEqual(code, 0, report)
        [unchecked] = report["unchecked_hosts"]
        self.assertTrue(unchecked.startswith("downhost: "), unchecked)

    def test_refuses_a_branch_that_already_exists_in_the_checkout(self):
        git(self.checkout, "branch", "wks/ava-format")

        code, report = self.start()

        self.assertEqual(code, 2)
        self.assertIn("wks/ava-format", report["error"])
        self.assertEqual(self.created_workspaces(), [])

    def test_refuses_a_branch_that_already_exists_on_origin(self):
        git(self.checkout, "push", "-q", "origin", "main:refs/heads/wks/ava-format")

        code, report = self.start()

        self.assertEqual(code, 2)
        self.assertIn("wks/ava-format", report["error"])
        self.assertEqual(self.created_workspaces(), [])

    def test_a_create_that_fails_after_creating_is_rolled_back(self):
        self.update_state(create_fails=True)

        code, report = self.start()

        self.assertEqual(code, 3)
        self.assertEqual(report["left"], [])
        self.assert_nothing_remains()

    def test_a_misplaced_owner_is_removed_and_a_rerun_starts_cleanly(self):
        self.update_state(force={"Model": "anthropic/claude-sonnet-5-5"})

        code, report = self.start()

        self.assertEqual(code, 3)
        self.assertIn("claude-sonnet-5-5", report["error"])
        self.assertEqual(report["left"], [])
        self.assert_nothing_remains()

        code, report = self.start()

        self.assertEqual(code, 0, report)
        self.assertEqual(len(self.state()["agents"]), 1)

    def test_rollback_keeps_a_branch_that_holds_commits(self):
        self.update_state(force={"ParentAgentId": CALLER}, commit_on_run=True)

        code, report = self.start()

        self.assertEqual(code, 3)
        self.assertEqual(self.state()["workspaces"], [])
        tip = self.local_branch()
        self.assertNotIn(tip, ("", self.base))
        [left] = report["left"]
        self.assertIn(tip, left)


if __name__ == "__main__":
    unittest.main()
