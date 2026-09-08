#!/usr/bin/env python3
"""Portable private-session supervisor for managed Codex reviews."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import signal
import subprocess
import sys
import tempfile
import time

import process_identity


MONITOR_INTERVAL_SECONDS = 0.05
STABILIZATION_ATTEMPTS = 40
TERM_GRACE_SECONDS = 2.0


class SupervisorError(RuntimeError):
    pass


def atomic_text(path: str, text: str, mode: int = 0o600) -> None:
    target = os.path.abspath(path)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{os.path.basename(target)}.", dir=os.path.dirname(target))
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor = -1
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        os.chmod(target, mode)
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def atomic_json(path: str, value: object) -> None:
    atomic_text(path, json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")


def publish_result(path: str, value: dict[str, object]) -> None:
    test_mode = os.environ.get("CODEX_REVIEW_TEST_SUPERVISOR_RESULT")
    if test_mode == "missing":
        raise SupervisorError("injected missing supervisor result")
    if test_mode == "malformed":
        atomic_text(path, "{not-json\n")
        return
    if test_mode == "cleanup-false":
        value = {**value, "cleanupVerified": False}
    if test_mode == "inconsistent":
        value = {**value, "codexExitCode": 9}
    if test_mode == "missing-signal":
        value = {key: item for key, item in value.items() if key != "codexSignal"}
    if test_mode == "invalid-signal-reason":
        value = {**value, "reason": "signal:garbage", "codexExitCode": 143, "codexSignal": 15}
    atomic_json(path, value)


def identity_matches(adapter: process_identity.PlatformAdapter, pid: int, start: str, boot: str) -> bool:
    if adapter.boot_identity() != boot:
        return False
    record = adapter.snapshot(pid)
    return record is not None and record.alive and record.startIdentity == start


def optional_linux_parent_death_signal() -> None:
    if sys.platform.startswith("linux"):
        try:
            libc = ctypes.CDLL(None, use_errno=True)
            prctl = libc.prctl
            prctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong]
            prctl.restype = ctypes.c_int
            # PR_SET_PDEATHSIG is an optimization only. Portable identity
            # monitoring below remains authoritative on every platform.
            prctl(1, signal.SIGTERM, 0, 0, 0)
        except (AttributeError, OSError):
            pass


def send_group(pgid: int, signum: int) -> bool:
    try:
        os.killpg(pgid, signum)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return False


def live_session(adapter: process_identity.PlatformAdapter, sid: int, own_pid: int) -> list[process_identity.ProcessRecord]:
    return [record for record in adapter.list_processes() if record.sid == sid and record.pid != own_pid and record.alive]


def same_process(actual: process_identity.ProcessRecord | None, expected: process_identity.ProcessRecord) -> bool:
    return (
        actual is not None
        and actual.alive
        and actual.pid == expected.pid
        and actual.startIdentity == expected.startIdentity
        and actual.pgid == expected.pgid
        and actual.sid == expected.sid
    )


def process_is_stopped(record: process_identity.ProcessRecord) -> bool:
    return record.state.upper().startswith("T")


def freeze_process(
    adapter: process_identity.PlatformAdapter,
    expected: process_identity.ProcessRecord,
    own_pid: int,
) -> process_identity.ProcessRecord | None:
    """Stop one identity-validated process without ever targeting the supervisor."""

    if expected.pid == own_pid:
        raise SupervisorError("refusing to stop the private supervisor")
    current = adapter.snapshot(expected.pid)
    if current is None:
        return None
    if not same_process(current, expected):
        raise SupervisorError(f"process identity changed before freezing pid {expected.pid}")
    try:
        os.kill(expected.pid, signal.SIGSTOP)
    except ProcessLookupError:
        return None
    except PermissionError as error:
        raise SupervisorError(f"could not freeze private session pid {expected.pid}") from error
    for _ in range(STABILIZATION_ATTEMPTS):
        current = adapter.snapshot(expected.pid)
        if current is None:
            return None
        if not same_process(current, expected):
            raise SupervisorError(f"process identity changed while freezing pid {expected.pid}")
        if process_is_stopped(current):
            return current
        time.sleep(MONITOR_INTERVAL_SECONDS)
    raise SupervisorError(f"private session pid {expected.pid} did not stop")


def signal_frozen_process(
    adapter: process_identity.PlatformAdapter,
    expected: process_identity.ProcessRecord,
    own_pid: int,
    signum: int,
) -> bool:
    if expected.pid == own_pid:
        raise SupervisorError("refusing to signal the private supervisor")
    current = adapter.snapshot(expected.pid)
    if current is None:
        return True
    if not same_process(current, expected) or not process_is_stopped(current):
        return False
    try:
        os.kill(expected.pid, signum)
        return True
    except ProcessLookupError:
        return True
    except PermissionError:
        return False


def signal_anchored_group(
    adapter: process_identity.PlatformAdapter,
    anchor: process_identity.ProcessRecord,
    signum: int,
) -> bool:
    """Signal a group only while a stopped, revalidated member pins its PGID."""

    current = adapter.snapshot(anchor.pid)
    if not same_process(current, anchor) or not process_is_stopped(current):
        return False
    return send_group(anchor.pgid, signum)


def freeze_group(
    adapter: process_identity.PlatformAdapter,
    sid: int,
    pgid: int,
    own_pid: int,
) -> process_identity.ProcessRecord | None:
    candidates = [
        record
        for record in live_session(adapter, sid, own_pid)
        if record.pgid == pgid
    ]
    for candidate in candidates:
        anchor = freeze_process(adapter, candidate, own_pid)
        if anchor is None:
            continue
        if not signal_anchored_group(adapter, anchor, signal.SIGSTOP):
            raise SupervisorError(f"could not freeze anchored private session process group {pgid}")
        current = adapter.snapshot(anchor.pid)
        if not same_process(current, anchor) or not process_is_stopped(current):
            raise SupervisorError(f"private session process group {pgid} lost its freeze anchor")
        return current
    if any(record.pgid == pgid for record in live_session(adapter, sid, own_pid)):
        raise SupervisorError(f"could not establish a freeze anchor for private session process group {pgid}")
    return None


def resume_frozen(
    adapter: process_identity.PlatformAdapter,
    anchors: dict[int, process_identity.ProcessRecord],
    frozen_processes: dict[int, process_identity.ProcessRecord],
    own_pid: int,
) -> None:
    for anchor in anchors.values():
        signal_anchored_group(adapter, anchor, signal.SIGCONT)
    for record in frozen_processes.values():
        signal_frozen_process(adapter, record, own_pid, signal.SIGCONT)


def stable_private_session(
    adapter: process_identity.PlatformAdapter,
    leader: process_identity.ProcessRecord,
) -> tuple[
    dict[int, dict[int, str]],
    dict[int, process_identity.ProcessRecord],
    dict[int, process_identity.ProcessRecord],
]:
    """Freeze every non-supervisor group and require two equal snapshots."""

    anchors: dict[int, process_identity.ProcessRecord] = {}
    frozen_processes: dict[int, process_identity.ProcessRecord] = {}
    previous: tuple[tuple[int, int, str], ...] | None = None
    stable_count = 0
    evidence: dict[int, dict[int, str]] = {}
    for _ in range(STABILIZATION_ATTEMPTS):
        current_leader = adapter.snapshot(leader.pid)
        if not same_process(current_leader, leader):
            raise SupervisorError("private session leader identity changed during cleanup")
        members = live_session(adapter, leader.sid, leader.pid)
        for member in members:
            if member.pgid == leader.pgid:
                current = frozen_processes.get(member.pid)
                if current is None or not same_process(adapter.snapshot(member.pid), current) or not process_is_stopped(adapter.snapshot(member.pid) or member):
                    frozen = freeze_process(adapter, member, leader.pid)
                    if frozen is not None:
                        frozen_processes[member.pid] = frozen
        groups = {member.pgid for member in members if member.pgid != leader.pgid}
        for pgid in sorted(groups):
            anchor = anchors.get(pgid)
            current_anchor = adapter.snapshot(anchor.pid) if anchor is not None else None
            if anchor is None or not same_process(current_anchor, anchor) or not process_is_stopped(current_anchor):
                anchor = freeze_group(adapter, leader.sid, pgid, leader.pid)
                if anchor is not None:
                    anchors[pgid] = anchor
        # Re-enumerate after freezing newly discovered groups. Membership is
        # authoritative by SID, so reparenting cannot escape this boundary.
        members = live_session(adapter, leader.sid, leader.pid)
        snapshot = tuple(sorted((member.pid, member.pgid, member.startIdentity) for member in members))
        evidence = {}
        for member in members:
            evidence.setdefault(member.pgid, {})[member.pid] = member.startIdentity
        all_frozen = all(
            (
                member.pid in frozen_processes
                and same_process(adapter.snapshot(member.pid), frozen_processes[member.pid])
                and process_is_stopped(adapter.snapshot(member.pid) or member)
            )
            if member.pgid == leader.pgid
            else (
                member.pgid in anchors
                and same_process(adapter.snapshot(anchors[member.pgid].pid), anchors[member.pgid])
                and process_is_stopped(adapter.snapshot(anchors[member.pgid].pid) or member)
            )
            for member in members
        )
        if snapshot == previous and all_frozen:
            stable_count += 1
            if stable_count >= 2:
                return evidence, anchors, frozen_processes
        else:
            stable_count = 0
        previous = snapshot
        time.sleep(MONITOR_INTERVAL_SECONDS)
    resume_frozen(adapter, anchors, frozen_processes, leader.pid)
    raise SupervisorError("private session membership did not stabilize")


def evidence_still_matches(
    adapter: process_identity.PlatformAdapter,
    sid: int,
    evidence: dict[int, dict[int, str]],
) -> bool:
    current = {record.pid: record for record in adapter.list_processes() if record.sid == sid and record.alive}
    for pgid, members in evidence.items():
        for pid, start in members.items():
            record = current.get(pid)
            if record is not None and (record.startIdentity != start or record.pgid != pgid):
                return False
    return True


def cleanup_private_session(adapter: process_identity.PlatformAdapter, leader: process_identity.ProcessRecord) -> None:
    evidence, anchors, frozen_processes = stable_private_session(adapter, leader)
    groups = sorted(pgid for pgid in evidence if pgid != leader.pgid)
    if not evidence_still_matches(adapter, leader.sid, evidence):
        raise SupervisorError("private session identity changed before TERM")
    for pgid in groups:
        anchor = anchors.get(pgid)
        current_anchor = adapter.snapshot(anchor.pid) if anchor is not None else None
        if anchor is None or not same_process(current_anchor, anchor) or not process_is_stopped(current_anchor):
            anchor = freeze_group(adapter, leader.sid, pgid, leader.pid)
        if anchor is None:
            continue
        if not signal_anchored_group(adapter, anchor, signal.SIGTERM):
            raise SupervisorError(f"could not TERM private session process group {pgid}")
        current_anchor = adapter.snapshot(anchor.pid)
        if not same_process(current_anchor, anchor) or not process_is_stopped(current_anchor):
            anchor = freeze_group(adapter, leader.sid, pgid, leader.pid)
        if anchor is not None and not signal_anchored_group(adapter, anchor, signal.SIGCONT):
            raise SupervisorError(f"could not resume TERM-signalled private session process group {pgid}")
    for record in sorted(frozen_processes.values(), key=lambda value: value.pid):
        if not signal_frozen_process(adapter, record, leader.pid, signal.SIGTERM):
            raise SupervisorError(f"could not TERM private session pid {record.pid}")
        if not signal_frozen_process(adapter, record, leader.pid, signal.SIGCONT):
            raise SupervisorError(f"could not resume TERM-signalled private session pid {record.pid}")
    deadline = time.monotonic() + TERM_GRACE_SECONDS
    while time.monotonic() < deadline and live_session(adapter, leader.sid, leader.pid):
        time.sleep(MONITOR_INTERVAL_SECONDS)
    survivors = live_session(adapter, leader.sid, leader.pid)
    survivor_groups = sorted({record.pgid for record in survivors if record.pgid != leader.pgid})
    for pgid in survivor_groups:
        anchor = freeze_group(adapter, leader.sid, pgid, leader.pid)
        if anchor is not None and not signal_anchored_group(adapter, anchor, signal.SIGKILL):
            raise SupervisorError(f"could not KILL private session process group {pgid}")
    for record in [value for value in survivors if value.pgid == leader.pgid]:
        frozen = freeze_process(adapter, record, leader.pid)
        if frozen is not None and not signal_frozen_process(adapter, frozen, leader.pid, signal.SIGKILL):
            raise SupervisorError(f"could not KILL private session pid {record.pid}")
    deadline = time.monotonic() + TERM_GRACE_SECONDS
    while time.monotonic() < deadline and live_session(adapter, leader.sid, leader.pid):
        time.sleep(MONITOR_INTERVAL_SECONDS)
    survivors = live_session(adapter, leader.sid, leader.pid)
    if survivors:
        raise SupervisorError(f"private session cleanup left live pids: {[record.pid for record in survivors]}")
    current_leader = adapter.snapshot(leader.pid)
    if not same_process(current_leader, leader):
        raise SupervisorError("private supervisor identity changed during cleanup")
    remaining = [record for record in adapter.list_processes() if record.sid == leader.sid and record.alive]
    if len(remaining) != 1 or not same_process(remaining[0], leader):
        raise SupervisorError(f"private session was not empty except for supervisor pid {leader.pid}")


def process_result(child: subprocess.Popen[bytes]) -> tuple[int, int | None]:
    result = child.returncode
    if result is None:
        return 1, None
    if result < 0:
        return 128 + (-result), -result
    return result, None


def preflight() -> int:
    if not hasattr(os, "setsid"):
        raise SupervisorError(f"platform {sys.platform} does not provide os.setsid()")
    adapter = process_identity.adapter_for_platform()
    process_identity.preflight_payload(adapter)
    probe = subprocess.run(
        [sys.executable, "-c", "import os; os.setsid(); assert os.getsid(0)==os.getpid()"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    if probe.returncode != 0:
        raise SupervisorError(f"platform {adapter.platform} private-session preflight failed: {probe.stderr.strip()}")
    print(json.dumps({"protocolVersion": 2, "adapterVersion": process_identity.ADAPTER_VERSION, "platform": adapter.platform, "ok": True}, sort_keys=True))
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--preflight", action="store_true")
    result.add_argument("--parent-pid", type=int)
    result.add_argument("--parent-start-identity")
    result.add_argument("--parent-boot-id")
    result.add_argument("--owner-pid", type=int)
    result.add_argument("--owner-start-identity")
    result.add_argument("--owner-boot-id")
    result.add_argument("--ready-file")
    result.add_argument("--failed-file")
    result.add_argument("--identity-file")
    result.add_argument("--result-file")
    result.add_argument("--nonce")
    result.add_argument("--login-shell")
    result.add_argument("--work-dir")
    result.add_argument("--timeout-seconds", type=int)
    result.add_argument("command", nargs=argparse.REMAINDER)
    return result


def supervise(arguments: argparse.Namespace) -> int:
    required = [
        "parent_pid", "parent_start_identity", "parent_boot_id", "owner_pid", "owner_start_identity", "owner_boot_id",
        "ready_file", "failed_file", "identity_file", "result_file", "nonce", "login_shell", "work_dir", "timeout_seconds",
    ]
    missing = [name.replace("_", "-") for name in required if getattr(arguments, name) in (None, "")]
    if missing:
        raise SupervisorError(f"missing required supervisor arguments: {', '.join(missing)}")
    if arguments.timeout_seconds <= 0:
        raise SupervisorError("timeout-seconds must be positive")
    command = list(arguments.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise SupervisorError("missing Codex command arguments")

    adapter = process_identity.adapter_for_platform()
    if not identity_matches(adapter, arguments.parent_pid, arguments.parent_start_identity, arguments.parent_boot_id):
        raise SupervisorError("review launcher parent identity was stale before supervisor initialization")
    if not identity_matches(adapter, arguments.owner_pid, arguments.owner_start_identity, arguments.owner_boot_id):
        raise SupervisorError("Pi owner identity was stale before supervisor initialization")

    stop_reason: str | None = None

    def request_stop(signum: int, _frame: object) -> None:
        nonlocal stop_reason
        stop_reason = f"signal:{signum}"

    os.setsid()
    for signum in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        signal.signal(signum, request_stop)
    optional_linux_parent_death_signal()
    leader = adapter.snapshot(os.getpid())
    if leader is None or leader.pid != leader.pgid or leader.pid != leader.sid:
        raise SupervisorError(f"private supervisor identity mismatch: {leader}")
    if stop_reason:
        cleanup_private_session(adapter, leader)
        raise SupervisorError("review supervisor received a stop signal during initialization")
    evidence = {
        "protocolVersion": 2,
        "adapterVersion": process_identity.ADAPTER_VERSION,
        "platform": adapter.platform,
        "bootId": adapter.boot_identity(),
        "nonce": arguments.nonce,
        "phase": "initializing",
        "leaderPid": leader.pid,
        "leaderPgid": leader.pgid,
        "leaderSid": leader.sid,
        "leaderStartIdentity": leader.startIdentity,
    }
    atomic_json(arguments.identity_file, evidence)

    hook = os.environ.get("CODEX_REVIEW_TEST_BEFORE_IDENTITY_MARKER")
    if hook:
        atomic_text(hook, f"{os.getpid()}\n")
        allow = os.environ.get("CODEX_REVIEW_TEST_ALLOW_IDENTITY_PUBLICATION", f"{hook}.allow")
        while not os.path.exists(allow):
            if not identity_matches(adapter, arguments.parent_pid, arguments.parent_start_identity, arguments.parent_boot_id):
                cleanup_private_session(adapter, leader)
                raise SupervisorError("review launcher parent exited before readiness publication")
            time.sleep(0.01)

    if stop_reason:
        cleanup_private_session(adapter, leader)
        raise SupervisorError("review supervisor received a stop signal before Codex launch")
    if not identity_matches(adapter, arguments.parent_pid, arguments.parent_start_identity, arguments.parent_boot_id):
        raise SupervisorError("review launcher parent exited before Codex launch")
    if not identity_matches(adapter, arguments.owner_pid, arguments.owner_start_identity, arguments.owner_boot_id):
        raise SupervisorError("Pi owner exited before Codex launch")

    environment = os.environ.copy()
    environment["CODEX_REVIEW_PARTNER_ACTIVE"] = "1"
    os.chdir(arguments.work_dir)
    child = subprocess.Popen(
        [arguments.login_shell, "-l", "-c", 'exec codex "$@"', "codex", *command],
        env=environment,
        preexec_fn=os.setpgrp,
    )
    cleanup_verified = False
    try:
        child_identity = adapter.snapshot(child.pid)
        if child_identity is None or child_identity.sid != leader.sid:
            child.kill()
            child.wait()
            raise SupervisorError("Codex child did not join the private supervisor session")
        evidence.update(
            phase="ready",
            codexPid=child_identity.pid,
            codexPgid=child_identity.pgid,
            codexStartIdentity=child_identity.startIdentity,
        )
        atomic_json(arguments.identity_file, evidence)
        atomic_text(arguments.ready_file, "ready\n")

        deadline = time.monotonic() + arguments.timeout_seconds
        while child.poll() is None:
            if stop_reason:
                break
            if time.monotonic() >= deadline:
                stop_reason = "timeout"
                break
            if not identity_matches(adapter, arguments.parent_pid, arguments.parent_start_identity, arguments.parent_boot_id):
                stop_reason = "launcher-lost"
                break
            if not identity_matches(adapter, arguments.owner_pid, arguments.owner_start_identity, arguments.owner_boot_id):
                stop_reason = "owner-lost"
                break
            time.sleep(MONITOR_INTERVAL_SECONDS)

        if stop_reason is None:
            child.wait()
            cleanup_private_session(adapter, leader)
            cleanup_verified = True
            exit_code, child_signal = process_result(child)
            publish_result(arguments.result_file, {"reason": "completed", "codexExitCode": exit_code, "codexSignal": child_signal, "timeout": False, "cleanupVerified": True})
            return exit_code

        cleanup_private_session(adapter, leader)
        cleanup_verified = True
        try:
            child.wait(timeout=TERM_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            pass
        if stop_reason == "timeout":
            publish_result(arguments.result_file, {"reason": stop_reason, "codexExitCode": 137, "codexSignal": 9, "timeout": True, "cleanupVerified": True})
            return 124
        if stop_reason.startswith("signal:"):
            stop_signal = int(stop_reason.split(":", 1)[1])
            stop_exit = 128 + stop_signal
            publish_result(arguments.result_file, {"reason": stop_reason, "codexExitCode": stop_exit, "codexSignal": stop_signal, "timeout": False, "cleanupVerified": True})
            return stop_exit
        publish_result(arguments.result_file, {"reason": stop_reason, "codexExitCode": 143, "codexSignal": 15, "timeout": False, "cleanupVerified": True})
        return 125
    except BaseException:
        if not cleanup_verified:
            cleanup_private_session(adapter, leader)
        raise


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        if arguments.preflight:
            return preflight()
        return supervise(arguments)
    except BaseException as error:
        if not arguments.preflight and arguments.failed_file:
            try:
                atomic_text(arguments.failed_file, f"{type(error).__name__}: {error}\n")
            except BaseException:
                pass
        print(f"Codex supervisor failed on platform {sys.platform}: {type(error).__name__}: {error}", file=sys.stderr, flush=True)
        return 127


if __name__ == "__main__":
    raise SystemExit(main())
