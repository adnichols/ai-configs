#!/usr/bin/env python3
"""Pick the worker host with the most spare capacity for a new orchestrate worker.

Usage: pick_host.py --repo <repo-key> [--hosts <path>]

Hosts come from $ORCHESTRATE_HOSTS, else ~/.config/orchestrate/hosts.json. Each host is probed
with one shell command (cores, 5-minute load, available memory, swap used) plus `paseo ls -g
--json` (running agents, all trackers). The local host runs without ssh or `--host`.

Prints one JSON object. Exit 0: {"host", "local", "target", "checkout", "hosts"}.
Exit 3: no host can take a worker, {"host": null, "hosts": [...]}. Exit 2: config error.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import socket
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

DEFAULTS = {"max_workers": 12, "min_available_gb": 6, "max_swap_gb": 4, "max_load_per_core": 1.5, "per_worker_gb": 2}
GB = 1024**3
TIMEOUT = 20
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5"]

# Output: marker line, cores, 5-minute load line, then OS-specific memory/swap text.
PROBE = (
    "if [ -r /proc/meminfo ]; then echo @@linux; nproc; cat /proc/loadavg; cat /proc/meminfo; "
    "else echo @@darwin; sysctl -n hw.ncpu; sysctl -n vm.loadavg; vm_stat; sysctl vm.swapusage; fi"
)
SWAP_UNITS = {"K": 1024, "M": 1024**2, "G": GB, "T": 1024**4}


class ConfigError(Exception):
    pass


class ProbeError(Exception):
    pass


def run(argv: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True, timeout=TIMEOUT)


def local_name() -> str:
    return socket.gethostname().lower().split(".")[0]


def hosts_path(arg: str | None) -> Path:
    return Path(arg or os.environ.get("ORCHESTRATE_HOSTS") or "~/.config/orchestrate/hosts.json").expanduser()


def load_hosts(path: Path) -> list[dict]:
    try:
        data = json.loads(path.read_text())
    except OSError as exc:
        raise ConfigError(f"cannot read hosts file {path}: {exc.strerror or exc}")
    except json.JSONDecodeError as exc:
        raise ConfigError(f"malformed JSON in {path}: {exc}")
    hosts = data.get("hosts") if isinstance(data, dict) else None
    if not isinstance(hosts, list) or not hosts:
        raise ConfigError(f"{path}: 'hosts' must be a non-empty list")
    for index, host in enumerate(hosts):
        if not isinstance(host, dict):
            raise ConfigError(f"{path}: hosts[{index}] must be an object")
        for key in ("name", "target"):
            if not isinstance(host.get(key), str) or not host[key]:
                raise ConfigError(f"{path}: hosts[{index}] needs a string '{key}'")
        names = host.get("hostnames", [])
        if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
            raise ConfigError(f"{path}: host {host['name']}: 'hostnames' must be a list of strings")
        if not isinstance(host.get("checkouts", {}), dict):
            raise ConfigError(f"{path}: host {host['name']}: 'checkouts' must be an object")
        for key, default in DEFAULTS.items():
            value = host.get(key, default)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ConfigError(f"{path}: host {host['name']}: '{key}' must be a number")
    if len({h["name"] for h in hosts}) != len(hosts):
        raise ConfigError(f"{path}: host names must be unique")
    return hosts


def parse_linux(lines: list[str]) -> dict:
    meminfo = {}
    for line in lines[3:]:
        match = re.match(r"(\w+):\s+(\d+)", line)
        if match:
            meminfo[match.group(1)] = int(match.group(2)) * 1024
    return {
        "load5": float(lines[2].split()[1]),
        "available": meminfo["MemAvailable"],
        "swap_used": meminfo["SwapTotal"] - meminfo["SwapFree"],
    }


def parse_darwin(lines: list[str]) -> dict:
    text = "\n".join(lines[3:])
    page = re.search(r"page size of (\d+) bytes", text)
    pages = {
        kind: int(re.search(rf"Pages {kind}:\s+(\d+)", text).group(1))
        for kind in ("free", "inactive", "speculative", "purgeable")
    }
    swap = re.search(r"used = ([\d.]+)([KMGT])", text)
    return {
        "load5": float(lines[2].strip("{} \t").split()[1]),
        "available": sum(pages.values()) * int(page.group(1)),
        "swap_used": int(float(swap.group(1)) * SWAP_UNITS[swap.group(2)]),
    }


def parse_probe(output: str) -> dict:
    """Turn PROBE stdout into cores, load5, available_gb and swap_used_gb."""
    lines = [line for line in output.splitlines() if line.strip()]
    try:
        parse = {"@@linux": parse_linux, "@@darwin": parse_darwin}[lines[0].strip()]
        facts = parse(lines)
        return {
            "cores": int(lines[1]),
            "load5": facts["load5"],
            "available_gb": facts["available"] / GB,
            "swap_used_gb": facts["swap_used"] / GB,
        }
    except (KeyError, IndexError, ValueError, AttributeError):
        raise ProbeError("unparseable probe output")


def tail(text: str) -> str:
    lines = (text or "").strip().splitlines()
    return lines[-1] if lines else "no output"


def command(argv: list[str], what: str) -> str:
    try:
        result = run(argv)
    except subprocess.TimeoutExpired:
        raise ProbeError(f"{what} timed out after {TIMEOUT}s")
    except OSError as exc:
        raise ProbeError(f"{what}: {exc}")
    if result.returncode != 0:
        raise ProbeError(f"{what} exited {result.returncode}: {tail(result.stderr)}")
    return result.stdout


def probe_host(host: dict, local: bool) -> dict:
    """Return measured facts for one host, raising ProbeError when it cannot be measured."""
    alias = host["target"].removeprefix("ssh://")
    probe = ["sh", "-c", PROBE] if local else [*SSH, alias, PROBE]
    paseo = ["paseo", "ls", "-g", "--json"] + ([] if local else ["--host", host["target"]])
    facts = parse_probe(command(probe, "probe"))
    try:
        agents = json.loads(command(paseo, "paseo ls"))
        facts["running"] = sum(1 for a in agents if a.get("status") == "running")
    except (json.JSONDecodeError, AttributeError, TypeError):
        raise ProbeError("paseo ls: unparseable output")
    return facts


def evaluate(host: dict, repo: str, local: bool) -> dict:
    limit = {key: host.get(key, default) for key, default in DEFAULTS.items()}
    report = {
        "name": host["name"], "reachable": False, "running": None, "available_gb": None,
        "swap_used_gb": None, "load5": None, "cores": None, "free_slots": 0, "eligible": False, "reason": "",
    }
    try:
        facts = probe_host(host, local)
    except ProbeError as exc:
        report["reason"] = f"unreachable: {exc}"
        return report
    report.update(
        reachable=True, running=facts["running"], available_gb=round(facts["available_gb"], 2),
        swap_used_gb=round(facts["swap_used_gb"], 2), load5=facts["load5"], cores=facts["cores"],
    )
    need_gb = limit["min_available_gb"] + limit["per_worker_gb"]
    max_load = limit["max_load_per_core"] * facts["cores"]
    memory_slots = math.floor((facts["available_gb"] - limit["min_available_gb"]) / limit["per_worker_gb"])
    report["free_slots"] = max(0, min(limit["max_workers"] - facts["running"], memory_slots))
    if repo not in host.get("checkouts", {}):
        report["reason"] = f"no checkout for {repo}"
    elif facts["running"] >= limit["max_workers"]:
        report["reason"] = f"at max_workers {limit['max_workers']}"
    elif facts["available_gb"] < need_gb:
        report["reason"] = f"available {facts['available_gb']:.1f} GB < {need_gb:.1f} GB"
    # Linux leaves pages in swap long after pressure ends, so swap counts only
    # while memory is also short.
    elif facts["swap_used_gb"] > limit["max_swap_gb"] and facts["available_gb"] < 2 * need_gb:
        report["reason"] = f"swap {facts['swap_used_gb']:.1f} GB > {limit['max_swap_gb']:g} GB with {facts['available_gb']:.1f} GB available"
    elif facts["load5"] > max_load:
        report["reason"] = f"load {facts['load5']:.1f} > {max_load:.1f}"
    else:
        report["eligible"] = True
        report["reason"] = "ok"
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", required=True, help="repo key in each host's checkouts")
    parser.add_argument("--hosts", help="hosts file (default: $ORCHESTRATE_HOSTS or ~/.config/orchestrate/hosts.json)")
    args = parser.parse_args(argv)
    try:
        hosts = load_hosts(hosts_path(args.hosts))
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        return 2
    me = local_name()
    flags = [me in [n.lower() for n in host.get("hostnames", [])] for host in hosts]
    with ThreadPoolExecutor(max_workers=len(hosts)) as pool:
        reports = list(pool.map(lambda pair: evaluate(pair[0], args.repo, pair[1]), zip(hosts, flags)))
    eligible = [i for i, report in enumerate(reports) if report["eligible"]]
    if not eligible:
        print(json.dumps({"host": None, "hosts": reports}))
        return 3
    best = max(eligible, key=lambda i: (reports[i]["free_slots"], -i))
    host = hosts[best]
    print(json.dumps({
        "host": host["name"], "local": flags[best], "target": host["target"],
        "checkout": host["checkouts"][args.repo], "hosts": reports,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
