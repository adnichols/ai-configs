import json
import os
import shutil
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skills" / "orchestrate" / "scripts"))
import listener

HOSTS = {"hosts": [
    {"name": "mbp", "target": "ssh://mbp", "hostnames": ["aarons-macbook-pro"]},
    {"name": "devor", "target": "ssh://dever", "hostnames": ["devor"]},
]}


def agent(aid, status, name="worker"):
    return {"id": aid, "shortId": aid[:4], "name": name, "status": status, "cwd": "/x"}


class FakePaseo:
    """Stands in for listener.run: `agents[target]` is a list of agents or an Exception."""

    def __init__(self):
        self.agents = {}
        self.sends = []
        self.ls_cmds = []
        self.fail_send = False

    def __call__(self, cmd, timeout=60):
        if cmd[:2] == ["paseo", "ls"]:
            self.ls_cmds.append(cmd)
            result = self.agents[cmd[cmd.index("--host") + 1]]
            if isinstance(result, Exception):
                raise result
            return json.loads(json.dumps(result))
        if cmd[:3] == ["paseo", "send", "--no-wait"]:
            if self.fail_send:
                raise RuntimeError("paseo send exit 1: boom")
            self.sends.append((cmd[3], cmd[4]))
            return ""
        raise AssertionError(f"unexpected command {cmd}")


class RemoteRelayTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.root = self.tmp / "trk-slug"
        self.root.mkdir()
        (self.root / "dashboard.json").write_text(json.dumps({"plan_id": "doc", "space_id": "sp"}))
        self.hosts_file = self.tmp / "hosts.json"
        self.hosts_file.write_text(json.dumps(HOSTS))
        self.fake = FakePaseo()
        self.fake.agents = {"ssh://mbp": [], "ssh://dever": []}
        self.hostname = "aarons-macbook-pro.local"
        for patcher in (
            unittest.mock.patch.dict(os.environ, {"ORCHESTRATE_HOSTS": str(self.hosts_file)}),
            unittest.mock.patch.object(listener, "run", self.fake),
            unittest.mock.patch.object(listener.socket, "gethostname", lambda: self.hostname),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def listener(self):
        return listener.Listener(self.root, "orch-id", "me", 30)

    def stored(self):
        return json.loads((self.root / "listener.json").read_text())

    def test_seeding_sends_nothing(self):
        self.fake.agents["ssh://dever"] = [agent("a1", "idle"), agent("a2", "running"), agent("a3", "error")]
        lst = self.listener()
        self.assertEqual(lst.poll_remote(), [])
        self.assertEqual(self.fake.sends, [])
        self.assertEqual(self.stored()["remote_agents"], {"devor": {"a1": "idle", "a2": "running", "a3": "error"}})

    def test_lists_by_tracker_label_on_remote_host_only(self):
        self.listener().poll_remote()
        self.assertEqual(self.fake.ls_cmds, [[
            "paseo", "ls", "-g", "--json", "--label", "tracker=trk-slug", "--host", "ssh://dever"]])

    def test_running_to_idle_sends_once_with_contract_text(self):
        self.fake.agents["ssh://dever"] = [agent("a1", "running", "Fix login")]
        lst = self.listener()
        lst.poll_remote()
        self.fake.agents["ssh://dever"] = [agent("a1", "idle", "Fix login")]
        lst.poll_remote()
        self.assertEqual(self.fake.sends, [(
            "orch-id",
            "WORKER_TURN_ENDED host=devor agent=a1 status=idle name=Fix login. "
            "Read its WORKER_STATUS: paseo logs --host ssh://dever a1")])
        lst.poll_remote()
        self.assertEqual(len(self.fake.sends), 1)

    def test_initializing_to_error_and_closed_relay(self):
        self.fake.agents["ssh://dever"] = [agent("a1", "initializing"), agent("a2", "running")]
        lst = self.listener()
        lst.poll_remote()
        self.fake.agents["ssh://dever"] = [agent("a1", "error"), agent("a2", "closed")]
        lst.poll_remote()
        self.assertEqual([m.split()[3] for _, m in self.fake.sends], ["status=error", "status=closed"])

    def test_idle_to_running_to_idle_relays_second_ending(self):
        self.fake.agents["ssh://dever"] = [agent("a1", "idle")]
        lst = self.listener()
        lst.poll_remote()
        self.fake.agents["ssh://dever"] = [agent("a1", "running")]
        lst.poll_remote()
        self.assertEqual(self.fake.sends, [])
        self.fake.agents["ssh://dever"] = [agent("a1", "idle")]
        lst.poll_remote()
        self.assertEqual(len(self.fake.sends), 1)

    def test_failed_send_is_retried_next_poll(self):
        self.fake.agents["ssh://dever"] = [agent("a1", "running")]
        lst = self.listener()
        lst.poll_remote()
        self.fake.agents["ssh://dever"] = [agent("a1", "idle")]
        self.fake.fail_send = True
        errors = lst.poll_remote()
        self.assertEqual(len(errors), 1)
        self.assertIn("devor", errors[0])
        self.assertEqual(self.stored()["remote_agents"]["devor"]["a1"], "running")
        self.fake.fail_send = False
        self.assertEqual(lst.poll_remote(), [])
        self.assertEqual(len(self.fake.sends), 1)
        self.assertEqual(self.stored()["remote_agents"]["devor"]["a1"], "idle")

    def test_new_already_idle_agent_after_seeding_is_relayed(self):
        lst = self.listener()
        lst.poll_remote()
        self.fake.agents["ssh://dever"] = [agent("a9", "idle"), agent("a8", "running")]
        lst.poll_remote()
        self.assertEqual(len(self.fake.sends), 1)
        self.assertIn("agent=a9 status=idle", self.fake.sends[0][1])
        lst.poll_remote()
        self.assertEqual(len(self.fake.sends), 1)

    def test_unreachable_host_records_error_and_other_host_still_processed(self):
        self.hostname = "somewhere-else"
        self.fake.agents["ssh://mbp"] = [agent("m1", "running")]
        self.fake.agents["ssh://dever"] = [agent("d1", "running")]
        lst = self.listener()
        lst.poll = lambda: None
        lst.tick()
        self.fake.agents["ssh://mbp"] = RuntimeError("paseo ls exit 1: ssh: connection refused")
        self.fake.agents["ssh://dever"] = [agent("d1", "idle")]
        lst.tick()
        state = self.stored()
        self.assertIn("host mbp", state["last_error"])
        self.assertIn("connection refused", state["last_error"])
        self.assertEqual([m.split()[1] for _, m in self.fake.sends], ["host=devor"])
        self.assertEqual(state["remote_agents"]["mbp"], {"m1": "running"})
        self.fake.agents["ssh://mbp"] = [agent("m1", "idle")]
        lst.tick()
        self.assertIsNone(self.stored()["last_error"])
        self.assertEqual(len(self.fake.sends), 2)

    def test_unreachable_first_poll_does_not_seed_host(self):
        self.fake.agents["ssh://dever"] = RuntimeError("down")
        lst = self.listener()
        self.assertEqual(len(lst.poll_remote()), 1)
        self.assertNotIn("devor", lst.state.get("remote_agents", {}))

    def test_no_hosts_file_disables_feature(self):
        self.hosts_file.unlink()
        lst = self.listener()
        self.assertEqual(lst.poll_remote(), [])
        self.assertEqual(self.fake.ls_cmds, [])
        self.assertEqual(self.fake.sends, [])

    def test_local_host_is_skipped(self):
        self.hostname = "Devor"
        self.fake.agents["ssh://mbp"] = [agent("m1", "running")]
        lst = self.listener()
        lst.poll_remote()
        self.assertEqual([c[c.index("--host") + 1] for c in self.fake.ls_cmds], ["ssh://mbp"])
        self.assertEqual(list(lst.state["remote_agents"]), ["mbp"])

    def test_state_survives_restart_and_downtime_transition_is_relayed(self):
        self.fake.agents["ssh://dever"] = [agent("a1", "running")]
        self.listener().poll_remote()
        self.fake.agents["ssh://dever"] = [agent("a1", "idle")]  # ended while the listener was down
        restarted = self.listener()
        self.assertEqual(restarted.poll_remote(), [])
        self.assertEqual(len(self.fake.sends), 1)
        again = self.listener()
        again.poll_remote()
        self.assertEqual(len(self.fake.sends), 1)


if __name__ == "__main__":
    unittest.main()
