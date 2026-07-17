import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts/process_identity.py"
SPEC = importlib.util.spec_from_file_location("process_identity", SCRIPT)
assert SPEC and SPEC.loader
identity = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = identity
SPEC.loader.exec_module(identity)


class FakeAdapter:
    platform = "fake"

    def boot_identity(self):
        return "fake-boot:1"

    def snapshot(self, pid):
        if pid == 99:
            return None
        return identity.ProcessRecord(pid, 1, pid, pid, "R", f"fake:{pid}", True, False)

    def list_processes(self):
        return [
            identity.ProcessRecord(10, 1, 10, 10, "R", "fake:10", True, False),
            identity.ProcessRecord(11, 10, 11, 10, "Z", "fake:11", False, True),
            identity.ProcessRecord(20, 1, 20, 20, "S", "fake:20", True, False),
        ]


class ProcessIdentityTest(unittest.TestCase):
    def test_snapshot_and_list_protocol_are_strict_and_versioned(self):
        snapshot = identity.snapshot_payload(10, FakeAdapter())
        self.assertEqual(snapshot["protocolVersion"], 2)
        self.assertEqual(snapshot["adapterVersion"], 1)
        self.assertEqual(snapshot["platform"], "fake")
        self.assertEqual(snapshot["process"]["sid"], 10)
        self.assertEqual(snapshot["process"]["startIdentity"], "fake:10")
        listing = identity.list_payload(sid=10, adapter=FakeAdapter())
        self.assertEqual([row["pid"] for row in listing["processes"]], [10, 11])
        self.assertTrue(listing["processes"][1]["zombie"])

    def test_dead_and_malformed_pids(self):
        self.assertIsNone(identity.snapshot_payload(99, FakeAdapter())["process"])
        for value in (0, -1, "nope"):
            with self.subTest(value=value), self.assertRaises(identity.ProcessIdentityError):
                identity._positive_pid(value)

    def test_linux_fixture_parses_parent_group_session_start_and_zombie(self):
        with tempfile.TemporaryDirectory() as temporary:
            proc = pathlib.Path(temporary)
            (proc / "sys/kernel/random").mkdir(parents=True)
            (proc / "sys/kernel/random/boot_id").write_text("fixture-boot\n")
            (proc / "321").mkdir()
            # Fields after comm: state, ppid, pgrp, session, then enough
            # placeholders to reach Linux stat starttime at tail index 19.
            tail = ["Z", "12", "300", "299", *(["0"] * 15), "987654", "0"]
            (proc / "321/stat").write_text(f"321 (name with ) parenthesis) {' '.join(tail)}\n")
            adapter = identity.LinuxAdapter(proc)
            record = adapter.snapshot(321)
            self.assertIsNotNone(record)
            self.assertEqual((record.ppid, record.pgid, record.sid), (12, 300, 299))
            self.assertEqual(record.startIdentity, "linux-jiffies:987654")
            self.assertTrue(record.zombie)
            self.assertEqual(adapter.boot_identity(), "linux:fixture-boot")

    def test_unknown_platform_fails_explicitly(self):
        with self.assertRaisesRegex(identity.UnsupportedPlatformError, "supported platforms are linux and darwin"):
            identity.adapter_for_platform("win32")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "preflight"],
            env={**os.environ, "CODEX_REVIEW_PLATFORM_OVERRIDE": "win32"},
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 2)
        error = json.loads(result.stderr)
        self.assertEqual(error["platform"], "win32")
        self.assertIn("unsupported", error["message"])

    def test_real_host_self_parent_group_session_and_enumeration(self):
        adapter = identity.adapter_for_platform()
        current = adapter.snapshot(os.getpid())
        parent = adapter.snapshot(os.getppid())
        self.assertIsNotNone(current)
        self.assertIsNotNone(parent)
        self.assertEqual(current.ppid, os.getppid())
        self.assertEqual(current.pgid, os.getpgid(0))
        self.assertEqual(current.sid, os.getsid(0))
        self.assertTrue(current.startIdentity)
        self.assertTrue(adapter.boot_identity())
        members = identity.list_payload(sid=current.sid, adapter=adapter)["processes"]
        self.assertIn(os.getpid(), {row["pid"] for row in members})

    @unittest.skipUnless(sys.platform == "darwin", "Darwin libproc integration")
    def test_darwin_libproc_returns_complete_struct(self):
        adapter = identity.DarwinAdapter()
        current = adapter.snapshot(os.getpid())
        self.assertEqual(current.startIdentity.split(":", 1)[0], "darwin-usec")
        self.assertEqual(adapter.platform, "darwin")

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux /proc integration")
    def test_linux_proc_returns_precise_start_and_boot_identity(self):
        adapter = identity.LinuxAdapter()
        current = adapter.snapshot(os.getpid())
        self.assertRegex(current.startIdentity, r"^linux-jiffies:\d+$")
        self.assertRegex(adapter.boot_identity(), r"^linux:.+")


if __name__ == "__main__":
    unittest.main()
