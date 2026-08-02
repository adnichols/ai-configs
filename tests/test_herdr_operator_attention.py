#!/usr/bin/env python3

import hashlib
import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "skills/herdr/scripts/herdr-operator-attention"


class OperatorAttentionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.state = self.root / "state"
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.log = self.root / "herdr.log"
        fake = self.bin / "herdr"
        fake.write_text(
            "#!/usr/bin/env bash\n"
            "printf '%s\\n' \"$*\" >>\"$FAKE_HERDR_LOG\"\n"
            "exit \"${FAKE_HERDR_EXIT:-0}\"\n"
        )
        fake.chmod(0o755)
        self.env = {
            **os.environ,
            "HERDR_OPERATOR_WAIT_DIR": str(self.state),
            "FAKE_HERDR_LOG": str(self.log),
            "PATH": f"{self.bin}:{os.environ.get('PATH', '')}",
        }

    def tearDown(self):
        self.temp.cleanup()

    def invoke(self, *args, env=None):
        return subprocess.run(
            [str(HELPER), *args],
            env=env or self.env,
            text=True,
            capture_output=True,
        )

    def marker(self, pane):
        return self.state / f"{hashlib.sha256(pane.encode()).hexdigest()}.json"

    def log_lines(self):
        return self.log.read_text().splitlines() if self.log.exists() else []

    def test_set_status_idempotence_change_and_clear(self):
        pane = "workspace/pane:α"
        first = self.invoke("set", "--pane", pane, "--message", "Type password", "--kind", "password")
        self.assertEqual(first.returncode, 0, first.stderr)
        marker = self.marker(pane)
        self.assertTrue(marker.is_file())
        value = json.loads(marker.read_text())
        self.assertEqual(value["paneId"], pane)
        self.assertEqual(value["message"], "Type password")
        self.assertEqual(value["kind"], "password")
        self.assertTrue(value["notifyOnSet"])
        self.assertTrue(value["setAt"].endswith("Z"))
        self.assertEqual(
            self.log_lines(),
            [
                f"pane report-agent {pane} --source workflow:operator-attention --agent operator-wait --state blocked --message Type password",
                "notification show Operator action required --body Type password --sound request",
            ],
        )

        status = self.invoke("status", "--pane", pane)
        self.assertEqual(status.returncode, 0)
        self.assertTrue(json.loads(status.stdout)["active"])

        again = self.invoke("set", "--pane", pane, "--message", "Type password", "--kind", "password")
        self.assertEqual(again.returncode, 0)
        self.assertEqual(sum("report-agent" in line for line in self.log_lines()), 2)
        self.assertEqual(sum("notification show" in line for line in self.log_lines()), 1)

        changed = self.invoke("set", "--pane", pane, "--message", "Approve release", "--kind", "approval")
        self.assertEqual(changed.returncode, 0)
        self.assertEqual(sum("notification show" in line for line in self.log_lines()), 2)

        cleared = self.invoke("clear", "--pane", pane)
        self.assertEqual(cleared.returncode, 0, cleared.stderr)
        self.assertFalse(marker.exists())
        inactive = json.loads(self.invoke("status", "--pane", pane).stdout)
        self.assertEqual(inactive, {"active": False})
        self.assertIn(
            f"pane release-agent {pane} --source workflow:operator-attention --agent operator-wait",
            self.log_lines(),
        )
        self.assertEqual(self.invoke("clear", "--pane", pane).returncode, 0)

    def test_no_notify_and_pane_env_default(self):
        env = {**self.env, "HERDR_PANE_ID": "env-pane"}
        result = self.invoke("set", "--message", "quiet", "--no-notify", env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(any("notification show" in line for line in self.log_lines()))
        self.assertFalse(json.loads(self.marker("env-pane").read_text())["notifyOnSet"])

    def test_missing_or_failing_herdr_is_best_effort(self):
        no_herdr = {**self.env, "PATH": "/usr/bin:/bin"}
        result = self.invoke("set", "--pane", "p1", "--message", "marker only", env=no_herdr)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.marker("p1").exists())
        self.assertEqual(self.invoke("clear", "--pane", "p1", env=no_herdr).returncode, 0)

        failing = {**self.env, "FAKE_HERDR_EXIT": "9"}
        result = self.invoke("set", "--pane", "p2", "--message", "socket down", env=failing)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.marker("p2").exists())

    def test_usage_errors_are_nonzero(self):
        for args in [(), ("wat",), ("set", "--pane", "p"), ("clear",), ("status",)]:
            result = self.invoke(*args, env={k: v for k, v in self.env.items() if k != "HERDR_PANE_ID"})
            self.assertNotEqual(result.returncode, 0, args)

    def test_marker_write_failure_is_nonzero_and_names_path(self):
        bad_parent = self.root / "not-a-directory"
        bad_parent.write_text("x")
        env = {**self.env, "HERDR_OPERATOR_WAIT_DIR": str(bad_parent)}
        result = self.invoke("set", "--pane", "p", "--message", "fail", env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(bad_parent), result.stderr)

    def test_active_marker_delete_failure_is_nonzero(self):
        pane = "delete-pane"
        self.assertEqual(self.invoke("set", "--pane", pane, "--message", "active").returncode, 0)
        marker = self.marker(pane)
        # Replacing the marker file with a non-empty directory reliably makes unlink fail,
        # while preserving an active marker path for the direct clear contract.
        marker.unlink()
        marker.mkdir()
        (marker / "child").write_text("x")
        result = self.invoke("clear", "--pane", pane)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(marker), result.stderr)


if __name__ == "__main__":
    unittest.main()
