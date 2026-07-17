import importlib.util
import argparse
import os
import pathlib
import signal
import sys
import tempfile
import unittest
from unittest import mock


SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


identity = load_module("process_identity", "process_identity.py")
supervisor = load_module("review_supervisor", "review_supervisor.py")


def record(pid, pgid, sid=100, start=None, state="R"):
    return identity.ProcessRecord(pid, 100, pgid, sid, state, start or f"start:{pid}", True, False)


class FakeAdapter:
    platform = "fake"

    def __init__(self, records):
        self.records = {value.pid: value for value in records}

    def boot_identity(self):
        return "fake-boot"

    def snapshot(self, pid):
        return self.records.get(pid)

    def list_processes(self):
        return sorted(self.records.values(), key=lambda value: value.pid)

    def stop(self, pid):
        value = self.records.get(pid)
        if value is not None:
            self.records[pid] = record(value.pid, value.pgid, value.sid, value.startIdentity, "T")

    def resume(self, pid):
        value = self.records.get(pid)
        if value is not None:
            self.records[pid] = record(value.pid, value.pgid, value.sid, value.startIdentity, "R")

    def kill(self, pid):
        self.records.pop(pid, None)


class ReviewSupervisorTest(unittest.TestCase):
    def arguments(self, directory):
        return argparse.Namespace(
            parent_pid=101, parent_start_identity="parent", parent_boot_id="fake-boot",
            owner_pid=102, owner_start_identity="owner", owner_boot_id="fake-boot",
            ready_file=f"{directory}/ready", failed_file=f"{directory}/failed",
            identity_file=f"{directory}/identity", result_file=f"{directory}/result",
            nonce="nonce", login_shell="/bin/sh", work_dir=directory,
            timeout_seconds=10, command=["exec"],
        )

    def test_parent_death_signal_is_handled_before_codex_launch(self):
        current = os.getpid()
        adapter = FakeAdapter([
            record(101, 101, sid=101, start="parent"),
            record(102, 102, sid=102, start="owner"),
            record(current, current, sid=current, start="supervisor"),
        ])
        with tempfile.TemporaryDirectory() as directory:
            arguments = argparse.Namespace(
                parent_pid=101,
                parent_start_identity="parent",
                parent_boot_id="fake-boot",
                owner_pid=102,
                owner_start_identity="owner",
                owner_boot_id="fake-boot",
                ready_file=f"{directory}/ready",
                failed_file=f"{directory}/failed",
                identity_file=f"{directory}/identity",
                result_file=f"{directory}/result",
                nonce="nonce",
                login_shell="/bin/sh",
                work_dir=directory,
                timeout_seconds=10,
                command=["exec"],
            )

            def deliver_parent_death_signal():
                os.kill(current, signal.SIGTERM)

            with mock.patch.object(identity, "adapter_for_platform", return_value=adapter), mock.patch.object(
                supervisor.os, "setsid"
            ), mock.patch.object(
                supervisor, "optional_linux_parent_death_signal", side_effect=deliver_parent_death_signal
            ), mock.patch.object(
                supervisor, "cleanup_private_session"
            ) as cleanup, mock.patch.object(
                supervisor.subprocess, "Popen"
            ) as popen:
                with self.assertRaisesRegex(supervisor.SupervisorError, "stop signal during initialization"):
                    supervisor.supervise(arguments)

            cleanup.assert_called_once()
            popen.assert_not_called()

    def test_group_signals_require_a_live_stopped_identity_anchor(self):
        anchor = record(201, 200, state="T")
        adapter = FakeAdapter([anchor])
        with mock.patch.object(supervisor.os, "killpg") as killpg:
            adapter.records.clear()
            self.assertFalse(supervisor.signal_anchored_group(adapter, anchor, signal.SIGTERM))
            adapter.records[201] = record(201, 200, start="reused", state="T")
            self.assertFalse(supervisor.signal_anchored_group(adapter, anchor, signal.SIGTERM))
            adapter.records[201] = record(201, 300, start=anchor.startIdentity, state="T")
            self.assertFalse(supervisor.signal_anchored_group(adapter, anchor, signal.SIGTERM))
            killpg.assert_not_called()

    def test_post_launch_publication_failure_cleans_private_session(self):
        current = os.getpid()
        child = mock.Mock(pid=103)
        adapter = FakeAdapter([
            record(101, 101, sid=101, start="parent"),
            record(102, 102, sid=102, start="owner"),
            record(current, current, sid=current, start="supervisor"),
            record(103, 103, sid=current, start="child"),
        ])
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            identity, "adapter_for_platform", return_value=adapter
        ), mock.patch.object(supervisor.os, "setsid"), mock.patch.object(
            supervisor, "optional_linux_parent_death_signal"
        ), mock.patch.object(supervisor, "atomic_json"), mock.patch.object(
            supervisor, "atomic_text", side_effect=OSError("ready publication failed")
        ), mock.patch.object(supervisor, "cleanup_private_session") as cleanup, mock.patch.object(
            supervisor.subprocess, "Popen", return_value=child
        ):
            with self.assertRaisesRegex(OSError, "ready publication failed"):
                supervisor.supervise(self.arguments(directory))
        cleanup.assert_called_once_with(adapter, adapter.snapshot(current))

    def test_group_stop_is_anchored_by_a_per_process_freeze(self):
        adapter = FakeAdapter([record(201, 200)])
        events = []

        def kill(pid, signum):
            events.append(("pid", pid, signum))
            if signum == signal.SIGSTOP:
                adapter.stop(pid)

        def killpg(pgid, signum):
            events.append(("group", pgid, signum))

        with mock.patch.object(supervisor.os, "kill", side_effect=kill), mock.patch.object(
            supervisor.os, "killpg", side_effect=killpg
        ):
            anchor = supervisor.freeze_group(adapter, 100, 200, 100)

        self.assertIsNotNone(anchor)
        self.assertEqual(events, [("pid", 201, signal.SIGSTOP), ("group", 200, signal.SIGSTOP)])

    def test_cleanup_handles_same_leader_group_descendants_without_signalling_supervisor(self):
        leader = record(100, 100)
        adapter = FakeAdapter([leader, record(101, 100), record(201, 200)])
        process_signals = []
        group_signals = []

        def kill(pid, signum):
            self.assertNotEqual(pid, leader.pid)
            process_signals.append((pid, signum))
            if signum == signal.SIGSTOP:
                adapter.stop(pid)
            elif signum == signal.SIGCONT:
                adapter.resume(pid)
            elif signum == signal.SIGKILL:
                adapter.kill(pid)

        def killpg(pgid, signum):
            self.assertNotEqual(pgid, leader.pgid)
            group_signals.append((pgid, signum))
            members = [value.pid for value in adapter.list_processes() if value.pgid == pgid]
            for pid in members:
                if signum == signal.SIGSTOP:
                    adapter.stop(pid)
                elif signum == signal.SIGCONT:
                    adapter.resume(pid)
                elif signum == signal.SIGKILL:
                    adapter.kill(pid)

        with mock.patch.object(supervisor.os, "kill", side_effect=kill), mock.patch.object(
            supervisor.os, "killpg", side_effect=killpg
        ), mock.patch.object(supervisor.time, "sleep"), mock.patch.object(
            supervisor, "TERM_GRACE_SECONDS", 0
        ):
            supervisor.cleanup_private_session(adapter, leader)

        self.assertEqual(adapter.list_processes(), [leader])
        self.assertIn((101, signal.SIGSTOP), process_signals)
        self.assertIn((101, signal.SIGTERM), process_signals)
        self.assertIn((101, signal.SIGKILL), process_signals)
        self.assertIn((200, signal.SIGSTOP), group_signals)
        self.assertIn((200, signal.SIGTERM), group_signals)
        self.assertIn((200, signal.SIGKILL), group_signals)


if __name__ == "__main__":
    unittest.main()
