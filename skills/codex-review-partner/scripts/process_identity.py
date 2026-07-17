#!/usr/bin/env python3
"""Kernel-backed Linux and Darwin process identity snapshots.

The JSON protocol is intentionally small and versioned so the shell launcher,
Python supervisor, and Pi extension share one PID-reuse-safe authority.
"""

from __future__ import annotations

import argparse
import ctypes
import ctypes.util
import errno
import json
import os
import pathlib
import platform as platform_module
import sys
from dataclasses import asdict, dataclass
from typing import Iterable, Protocol


PROTOCOL_VERSION = 2
ADAPTER_VERSION = 1


class ProcessIdentityError(RuntimeError):
    """A supported process identity could not be proved."""


class UnsupportedPlatformError(ProcessIdentityError):
    """The current operating system has no maintained adapter."""


class ProcessAccessDeniedError(ProcessIdentityError):
    """Darwin denied inspection of an unrelated system process."""


@dataclass(frozen=True)
class ProcessRecord:
    pid: int
    ppid: int
    pgid: int
    sid: int
    state: str
    startIdentity: str
    alive: bool
    zombie: bool


class PlatformAdapter(Protocol):
    platform: str

    def boot_identity(self) -> str: ...

    def snapshot(self, pid: int) -> ProcessRecord | None: ...

    def list_processes(self) -> list[ProcessRecord]: ...


def _positive_pid(value: int | str) -> int:
    try:
        pid = int(value)
    except (TypeError, ValueError) as error:
        raise ProcessIdentityError(f"pid must be a positive integer: {value!r}") from error
    if pid <= 0:
        raise ProcessIdentityError(f"pid must be a positive integer: {value!r}")
    return pid


class LinuxAdapter:
    platform = "linux"

    def __init__(self, proc_root: pathlib.Path | str = "/proc") -> None:
        self.proc_root = pathlib.Path(proc_root)

    def boot_identity(self) -> str:
        path = self.proc_root / "sys/kernel/random/boot_id"
        try:
            value = path.read_text(encoding="utf-8").strip()
        except OSError as error:
            raise ProcessIdentityError(f"linux boot identity unavailable at {path}: {error}") from error
        if not value:
            raise ProcessIdentityError(f"linux boot identity is empty at {path}")
        return f"linux:{value}"

    def snapshot(self, pid: int) -> ProcessRecord | None:
        pid = _positive_pid(pid)
        path = self.proc_root / str(pid) / "stat"
        try:
            raw = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        except OSError as error:
            raise ProcessIdentityError(f"linux process identity unavailable for pid {pid}: {error}") from error
        close = raw.rfind(")")
        if close < 2:
            raise ProcessIdentityError(f"malformed linux process stat for pid {pid}: missing command boundary")
        fields = raw[close + 2 :].split()
        if len(fields) <= 19:
            raise ProcessIdentityError(f"malformed linux process stat for pid {pid}: expected at least 20 tail fields")
        try:
            state = fields[0]
            ppid = int(fields[1])
            pgid = int(fields[2])
            sid = int(fields[3])
            start = fields[19]
        except (ValueError, IndexError) as error:
            raise ProcessIdentityError(f"malformed linux process stat for pid {pid}: {error}") from error
        zombie = state == "Z"
        return ProcessRecord(pid, ppid, pgid, sid, state, f"linux-jiffies:{start}", not zombie, zombie)

    def list_processes(self) -> list[ProcessRecord]:
        try:
            names = list(self.proc_root.iterdir())
        except OSError as error:
            raise ProcessIdentityError(f"linux process enumeration unavailable at {self.proc_root}: {error}") from error
        records: list[ProcessRecord] = []
        for entry in names:
            if not entry.name.isdigit():
                continue
            try:
                record = self.snapshot(int(entry.name))
            except ProcessIdentityError:
                try:
                    entry.stat()
                except FileNotFoundError:
                    continue
                raise
            if record is not None:
                records.append(record)
        return sorted(records, key=lambda record: record.pid)


class ProcBsdInfo(ctypes.Structure):
    _fields_ = [
        ("pbi_flags", ctypes.c_uint32),
        ("pbi_status", ctypes.c_uint32),
        ("pbi_xstatus", ctypes.c_uint32),
        ("pbi_pid", ctypes.c_uint32),
        ("pbi_ppid", ctypes.c_uint32),
        ("pbi_uid", ctypes.c_uint32),
        ("pbi_gid", ctypes.c_uint32),
        ("pbi_ruid", ctypes.c_uint32),
        ("pbi_rgid", ctypes.c_uint32),
        ("pbi_svuid", ctypes.c_uint32),
        ("pbi_svgid", ctypes.c_uint32),
        ("rfu_1", ctypes.c_uint32),
        ("pbi_comm", ctypes.c_char * 16),
        ("pbi_name", ctypes.c_char * 32),
        ("pbi_nfiles", ctypes.c_uint32),
        ("pbi_pgid", ctypes.c_uint32),
        ("pbi_pjobc", ctypes.c_uint32),
        ("e_tdev", ctypes.c_uint32),
        ("e_tpgid", ctypes.c_uint32),
        ("pbi_nice", ctypes.c_int32),
        ("pbi_start_tvsec", ctypes.c_uint64),
        ("pbi_start_tvusec", ctypes.c_uint64),
    ]


class Timeval(ctypes.Structure):
    _fields_ = [("tv_sec", ctypes.c_long), ("tv_usec", ctypes.c_int)]


class DarwinAdapter:
    platform = "darwin"
    PROC_PIDTBSDINFO = 3
    SZOMB = 5

    def __init__(self, libproc: ctypes.CDLL | None = None, libc: ctypes.CDLL | None = None) -> None:
        try:
            self.libproc = libproc or ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True)
            self.libc = libc or ctypes.CDLL(ctypes.util.find_library("c") or None, use_errno=True)
        except OSError as error:
            raise ProcessIdentityError(f"darwin libproc capability unavailable: {error}") from error
        try:
            self.libproc.proc_pidinfo.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64, ctypes.c_void_p, ctypes.c_int]
            self.libproc.proc_pidinfo.restype = ctypes.c_int
            self.libproc.proc_listallpids.argtypes = [ctypes.c_void_p, ctypes.c_int]
            self.libproc.proc_listallpids.restype = ctypes.c_int
            self.libc.sysctlbyname.argtypes = [ctypes.c_char_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t), ctypes.c_void_p, ctypes.c_size_t]
            self.libc.sysctlbyname.restype = ctypes.c_int
        except AttributeError as error:
            raise ProcessIdentityError(f"darwin process capability missing required symbol: {error}") from error

    def boot_identity(self) -> str:
        value = Timeval()
        size = ctypes.c_size_t(ctypes.sizeof(value))
        result = self.libc.sysctlbyname(b"kern.boottime", ctypes.byref(value), ctypes.byref(size), None, 0)
        if result != 0 or size.value < ctypes.sizeof(Timeval):
            error = ctypes.get_errno()
            detail = os.strerror(error) if error else f"short result ({size.value} bytes)"
            raise ProcessIdentityError(f"darwin kernel boot time unavailable: {detail}")
        return f"darwin-boottime:{int(value.tv_sec)}:{int(value.tv_usec)}"

    def snapshot(self, pid: int) -> ProcessRecord | None:
        pid = _positive_pid(pid)
        info = ProcBsdInfo()
        size = ctypes.sizeof(info)
        received = self.libproc.proc_pidinfo(pid, self.PROC_PIDTBSDINFO, 0, ctypes.byref(info), size)
        if received == 0:
            error = ctypes.get_errno()
            if error in (0, 3):  # ESRCH may be lost by older libproc builds.
                return None
            if error == errno.EPERM:  # Normal for unrelated protected processes.
                raise ProcessAccessDeniedError(f"darwin process identity denied for pid {pid}: {os.strerror(error)}")
            raise ProcessIdentityError(f"darwin process identity unavailable for pid {pid}: {os.strerror(error)}")
        if received != size:
            raise ProcessIdentityError(f"darwin proc_pidinfo returned {received} bytes for pid {pid}; expected {size}")
        if int(info.pbi_pid) != pid:
            raise ProcessIdentityError(f"darwin proc_pidinfo pid mismatch: requested {pid}, received {int(info.pbi_pid)}")
        try:
            sid = os.getsid(pid)
        except ProcessLookupError:
            return None
        except PermissionError as error:
            raise ProcessAccessDeniedError(f"darwin session identity denied for pid {pid}: {error}") from error
        except OSError as error:
            raise ProcessIdentityError(f"darwin session identity unavailable for pid {pid}: {error}") from error
        status = int(info.pbi_status)
        zombie = status == self.SZOMB
        state = "Z" if zombie else {1: "I", 2: "R", 3: "S", 4: "T"}.get(status, f"U{status}")
        start = f"darwin-usec:{int(info.pbi_start_tvsec)}:{int(info.pbi_start_tvusec):06d}"
        return ProcessRecord(pid, int(info.pbi_ppid), int(info.pbi_pgid), sid, state, start, not zombie, zombie)

    def _pids(self) -> list[int]:
        requested = self.libproc.proc_listallpids(None, 0)
        if requested <= 0:
            error = ctypes.get_errno()
            raise ProcessIdentityError(f"darwin process enumeration unavailable: {os.strerror(error) if error else 'empty result'}")
        for _ in range(3):
            capacity = requested + 64
            buffer = (ctypes.c_int32 * capacity)()
            received = self.libproc.proc_listallpids(buffer, ctypes.sizeof(buffer))
            if received < 0:
                error = ctypes.get_errno()
                raise ProcessIdentityError(f"darwin process enumeration failed: {os.strerror(error)}")
            if received < capacity:
                return sorted({int(buffer[index]) for index in range(received) if int(buffer[index]) > 0})
            requested = capacity * 2
        raise ProcessIdentityError("darwin process enumeration did not stabilize")

    def list_processes(self) -> list[ProcessRecord]:
        records: list[ProcessRecord] = []
        for pid in self._pids():
            try:
                record = self.snapshot(pid)
            except ProcessAccessDeniedError:
                # Darwin denies proc_pidinfo for unrelated system processes
                # (for example pid 1) during every normal enumeration.
                continue
            if record is not None:
                records.append(record)
        return records


def adapter_for_platform(platform_name: str | None = None) -> PlatformAdapter:
    selected = (platform_name or os.environ.get("CODEX_REVIEW_PLATFORM_OVERRIDE") or sys.platform).lower()
    if selected.startswith("linux"):
        return LinuxAdapter(os.environ.get("CODEX_REVIEW_PROC_ROOT", "/proc"))
    if selected == "darwin":
        return DarwinAdapter()
    raise UnsupportedPlatformError(
        f"unsupported process identity platform {selected!r}; supported platforms are linux and darwin"
    )


def _payload(adapter: PlatformAdapter, processes: Iterable[ProcessRecord], **extra: object) -> dict[str, object]:
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "adapterVersion": ADAPTER_VERSION,
        "platform": adapter.platform,
        "bootId": adapter.boot_identity(),
        "processes": [asdict(record) for record in processes],
        **extra,
    }


def snapshot_payload(pid: int, adapter: PlatformAdapter | None = None) -> dict[str, object]:
    adapter = adapter or adapter_for_platform()
    record = adapter.snapshot(_positive_pid(pid))
    return _payload(adapter, [] if record is None else [record], requestedPid=pid, process=None if record is None else asdict(record))


def list_payload(*, sid: int | None = None, pgid: int | None = None, adapter: PlatformAdapter | None = None) -> dict[str, object]:
    adapter = adapter or adapter_for_platform()
    records = adapter.list_processes()
    if sid is not None:
        sid = _positive_pid(sid)
        records = [record for record in records if record.sid == sid]
    if pgid is not None:
        pgid = _positive_pid(pgid)
        records = [record for record in records if record.pgid == pgid]
    return _payload(adapter, records, requestedSid=sid, requestedPgid=pgid)


def preflight_payload(adapter: PlatformAdapter | None = None) -> dict[str, object]:
    adapter = adapter or adapter_for_platform()
    current = adapter.snapshot(os.getpid())
    if current is None:
        raise ProcessIdentityError(f"{adapter.platform} preflight could not snapshot its own process")
    return _payload(adapter, [current], ok=True, process=asdict(current))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    snapshot = subparsers.add_parser("snapshot")
    snapshot.add_argument("--pid", required=True, type=int)
    listing = subparsers.add_parser("list")
    selector = listing.add_mutually_exclusive_group()
    selector.add_argument("--sid", type=int)
    selector.add_argument("--pgid", type=int)
    subparsers.add_parser("preflight")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        if arguments.command == "snapshot":
            payload = snapshot_payload(arguments.pid)
        elif arguments.command == "list":
            payload = list_payload(sid=arguments.sid, pgid=arguments.pgid)
        else:
            payload = preflight_payload()
    except ProcessIdentityError as error:
        print(
            json.dumps(
                {
                    "protocolVersion": PROTOCOL_VERSION,
                    "adapterVersion": ADAPTER_VERSION,
                    "platform": os.environ.get("CODEX_REVIEW_PLATFORM_OVERRIDE") or sys.platform,
                    "error": type(error).__name__,
                    "message": str(error),
                    "host": platform_module.platform(),
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
