"""Behavior tests for orchestrate's pick_host.py. Commands are faked; no ssh, paseo, or network."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skills" / "orchestrate" / "scripts"))
import pick_host

GB_KB = 1024 * 1024


def linux_probe(cores=16, load5=0.52, available_gb=32, swap_used_gb=2):
    return f"""@@linux
{cores}
0.60 {load5} 0.59 3/1234 56789
MemTotal:       65536000 kB
MemFree:         1048576 kB
MemAvailable:   {int(available_gb * GB_KB)} kB
Buffers:          204800 kB
SwapTotal:       {7 * GB_KB} kB
SwapFree:        {int((7 - swap_used_gb) * GB_KB)} kB
"""


MACOS_PROBE = """@@darwin
16
{ 1.85 2.10 2.30 }
Mach Virtual Memory Statistics: (page size of 16384 bytes)
Pages free:                               10000.
Pages active:                            900000.
Pages inactive:                          200000.
Pages speculative:                         5000.
Pages throttled:                              0.
Pages wired down:                        150000.
Pages purgeable:                          10000.
Pages stored in compressor:              300000.
vm.swapusage: total = 2048.00M  used = 1024.50M  free = 1023.50M  (encrypted)
"""


def agents(running, idle=1):
    rows = [{"id": f"r{i}", "status": "running"} for i in range(running)]
    return rows + [{"id": f"i{i}", "status": "idle"} for i in range(idle)] + [{"id": "c", "status": "closed"}]


class World:
    """Fake machines keyed by ssh alias; 'local' is the machine without ssh/--host."""

    def __init__(self):
        self.machines = {}
        self.calls = []

    def add(self, key, probe, running=0, fail=None):
        self.machines[key] = {"probe": probe, "agents": agents(running), "fail": fail}

    def __call__(self, argv):
        self.calls.append(argv)
        if argv[0] == "ssh":
            key = argv[-2]
        elif argv[0] == "sh":
            key = "local"
        else:
            key = "local" if "--host" not in argv else argv[argv.index("--host") + 1].removeprefix("ssh://")
        machine = self.machines[key]
        if machine["fail"]:
            return subprocess.CompletedProcess(argv, 255, "", machine["fail"])
        out = machine["probe"] if argv[0] in ("ssh", "sh") else json.dumps(machine["agents"])
        return subprocess.CompletedProcess(argv, 0, out, "")


def hosts_config(**overrides):
    mbp = {"name": "mbp", "target": "ssh://mbp", "hostnames": ["aarons-macbook-pro"], "max_workers": 16,
           "min_available_gb": 4, "max_swap_gb": 4, "max_load_per_core": 2.0, "per_worker_gb": 2,
           "checkouts": {"ccore2": "/Users/anichols/code/ccore2"}}
    devor = {"name": "devor", "target": "ssh://dever", "hostnames": ["devor"], "max_workers": 12,
             "min_available_gb": 6, "max_swap_gb": 4, "max_load_per_core": 1.5, "per_worker_gb": 2,
             "checkouts": {"ccore2": "/home/anichols/code/ccore2"}}
    mbp.update(overrides.get("mbp", {}))
    devor.update(overrides.get("devor", {}))
    return {"hosts": [mbp, devor]}


@pytest.fixture
def world(monkeypatch):
    fake = World()
    monkeypatch.setattr(pick_host, "run", fake)
    monkeypatch.setattr(pick_host, "local_name", lambda: "elsewhere")
    return fake


@pytest.fixture
def pick(tmp_path, capsys):
    def go(config=None, repo="ccore2", raw=None):
        path = tmp_path / "hosts.json"
        path.write_text(raw if raw is not None else json.dumps(config or hosts_config()))
        code = pick_host.main(["--repo", repo, "--hosts", str(path)])
        captured = capsys.readouterr()
        return code, (json.loads(captured.out) if captured.out else None), captured.err

    return go


def report(result, name):
    return next(r for r in result["hosts"] if r["name"] == name)


def healthy(world, mbp_running=0, devor_running=0, mbp_gb=32, devor_gb=32):
    world.add("mbp", linux_probe(available_gb=mbp_gb), mbp_running)
    world.add("dever", linux_probe(available_gb=devor_gb), devor_running)


# --- selection ---

def test_picks_host_with_more_free_slots(world, pick):
    healthy(world, mbp_running=10, devor_running=2)
    code, result, _ = pick()
    assert code == 0
    assert result["host"] == "devor"
    assert result["local"] is False
    assert result["target"] == "ssh://dever"
    assert result["checkout"] == "/home/anichols/code/ccore2"
    assert report(result, "mbp")["free_slots"] == 6
    assert report(result, "devor")["free_slots"] == 10


def test_free_slots_limited_by_memory_not_just_max_workers(world, pick):
    healthy(world, mbp_gb=10, devor_gb=32)  # mbp: (10-4)/2 = 3 slots; devor: min(12, 13) = 12
    code, result, _ = pick()
    assert report(result, "mbp")["free_slots"] == 3
    assert report(result, "devor")["free_slots"] == 12
    assert result["host"] == "devor"


def test_tie_keeps_file_order(world, pick):
    world.add("mbp", linux_probe(available_gb=16), 0)    # min(16, 6) = 6
    world.add("dever", linux_probe(available_gb=18), 0)  # min(12, 6) = 6
    code, result, _ = pick()
    assert report(result, "mbp")["free_slots"] == report(result, "devor")["free_slots"] == 6
    assert result["host"] == "mbp"


def test_counts_all_running_agents_not_idle_or_closed(world, pick):
    healthy(world, mbp_running=3, devor_running=0)
    code, result, _ = pick()
    assert report(result, "mbp")["running"] == 3
    assert report(result, "devor")["running"] == 0


# --- rejection reasons ---

def test_rejects_host_at_max_workers(world, pick):
    healthy(world, devor_running=12)
    code, result, _ = pick()
    assert result["host"] == "mbp"
    entry = report(result, "devor")
    assert (entry["eligible"], entry["reason"], entry["free_slots"]) == (False, "at max_workers 12", 0)


def test_rejects_low_memory_with_headroom_for_one_worker(world, pick):
    healthy(world, devor_gb=7.9)  # needs min 6 + per_worker 2 = 8.0
    code, result, _ = pick()
    assert report(result, "devor")["eligible"] is False
    assert report(result, "devor")["reason"] == "available 7.9 GB < 8.0 GB"


def test_accepts_memory_exactly_at_threshold(world, pick):
    healthy(world, devor_gb=8.0)
    code, result, _ = pick(hosts_config(mbp={"max_workers": 0}))
    assert code == 0 and result["host"] == "devor"
    assert report(result, "devor")["free_slots"] == 1


def test_rejects_swap_over_limit_when_memory_is_short(world, pick):
    world.add("mbp", linux_probe(), 0)
    world.add("dever", linux_probe(swap_used_gb=5.2, available_gb=12), 0)
    code, result, _ = pick()
    assert report(result, "devor")["reason"] == "swap 5.2 GB > 4 GB with 12.0 GB available"
    assert result["host"] == "mbp"


def test_ignores_leftover_swap_when_memory_is_plentiful(world, pick):
    world.add("mbp", linux_probe(available_gb=5), 0)
    world.add("dever", linux_probe(swap_used_gb=6.9, available_gb=31), 0)
    code, result, _ = pick()
    assert report(result, "devor")["reason"] == "ok"
    assert result["host"] == "devor"


def test_rejects_high_load(world, pick):
    world.add("mbp", linux_probe(), 0)
    world.add("dever", linux_probe(load5=40.1), 0)
    code, result, _ = pick()
    assert report(result, "devor")["reason"] == "load 40.1 > 24.0"
    assert result["host"] == "mbp"


def test_unreachable_host_reports_stderr_tail(world, pick):
    world.add("mbp", linux_probe(), 0)
    world.add("dever", "", fail="ssh: connect to host dever port 22: Operation timed out\n")
    code, result, _ = pick()
    entry = report(result, "devor")
    assert entry["reachable"] is False and entry["eligible"] is False
    assert entry["reason"].startswith("unreachable: ")
    assert "Operation timed out" in entry["reason"]
    assert result["host"] == "mbp"


def test_timeout_is_unreachable(world, pick, monkeypatch):
    healthy(world)

    def slow(argv):
        raise subprocess.TimeoutExpired(argv, 20)

    monkeypatch.setattr(pick_host, "run", slow)
    code, result, _ = pick()
    assert code == 3
    assert all(r["reason"].startswith("unreachable: ") for r in result["hosts"])


def test_host_without_checkout_for_repo_is_ineligible(world, pick):
    healthy(world)
    config = hosts_config()
    config["hosts"][0]["checkouts"] = {"other": "/x"}
    code, result, _ = pick(config)
    assert report(result, "mbp")["eligible"] is False
    assert report(result, "mbp")["reason"] == "no checkout for ccore2"
    assert result["host"] == "devor"


def test_exit_3_when_no_host_can_take_a_worker(world, pick):
    healthy(world, mbp_running=16, devor_running=12)
    code, result, _ = pick()
    assert code == 3
    assert result["host"] is None
    assert [r["reason"] for r in result["hosts"]] == ["at max_workers 16", "at max_workers 12"]


def test_threshold_defaults_apply_when_fields_omitted(world, pick):
    healthy(world, mbp_running=12)
    config = {"hosts": [{"name": "mbp", "target": "ssh://mbp", "hostnames": [], "checkouts": {"ccore2": "/c"}}]}
    code, result, _ = pick(config)
    assert code == 3
    assert report(result, "mbp")["reason"] == "at max_workers 12"


# --- local detection ---

def test_local_host_runs_without_ssh_or_host_flag(world, pick, monkeypatch):
    monkeypatch.setattr(pick_host, "local_name", lambda: "aarons-macbook-pro")
    world.add("local", linux_probe(), running=0)
    world.add("dever", linux_probe(available_gb=8), 11)
    code, result, _ = pick()
    assert code == 0
    assert result["host"] == "mbp" and result["local"] is True
    mbp_calls = [c for c in world.calls if "dever" not in c and "ssh://dever" not in c]
    assert mbp_calls and all(c[0] in ("sh", "paseo") for c in mbp_calls)
    assert all("--host" not in c for c in mbp_calls)
    assert sum(c[0] == "ssh" for c in world.calls) == 1


def test_hostname_match_ignores_case_and_domain(monkeypatch):
    monkeypatch.setattr(pick_host.socket, "gethostname", lambda: "Aarons-MacBook-Pro.local")
    assert pick_host.local_name() == "aarons-macbook-pro"


def test_remote_host_uses_ssh_alias_and_host_flag(world, pick):
    healthy(world)
    pick()
    ssh_calls = [c for c in world.calls if c[0] == "ssh"]
    assert {c[-2] for c in ssh_calls} == {"mbp", "dever"}
    assert all("BatchMode=yes" in c for c in ssh_calls)
    paseo_hosts = {c[c.index("--host") + 1] for c in world.calls if c[0] == "paseo"}
    assert paseo_hosts == {"ssh://mbp", "ssh://dever"}
    assert all(c[:4] == ["paseo", "ls", "-g", "--json"] for c in world.calls if c[0] == "paseo")


# --- probe parsing ---

def test_parse_linux_probe():
    facts = pick_host.parse_probe(linux_probe(cores=16, load5=3.25, available_gb=32, swap_used_gb=2))
    assert facts["cores"] == 16
    assert facts["load5"] == 3.25
    assert facts["available_gb"] == pytest.approx(32)
    assert facts["swap_used_gb"] == pytest.approx(2)


def test_parse_macos_probe():
    facts = pick_host.parse_probe(MACOS_PROBE)
    assert facts["cores"] == 16
    assert facts["load5"] == 2.10
    # (10000 free + 200000 inactive + 5000 speculative + 10000 purgeable) * 16384
    assert facts["available_gb"] == pytest.approx(225000 * 16384 / 1024**3)
    assert facts["swap_used_gb"] == pytest.approx(1024.5 / 1024)


def test_parse_macos_swap_in_gigabytes():
    text = MACOS_PROBE.replace("used = 1024.50M", "used = 3.25G")
    assert pick_host.parse_probe(text)["swap_used_gb"] == pytest.approx(3.25)


def test_parse_macos_uses_page_size_from_header():
    text = MACOS_PROBE.replace("page size of 16384", "page size of 4096")
    assert pick_host.parse_probe(text)["available_gb"] == pytest.approx(225000 * 4096 / 1024**3)


def test_garbage_probe_output_makes_host_unreachable(world, pick):
    world.add("mbp", linux_probe(), 0)
    world.add("dever", "command not found\n", 0)
    code, result, _ = pick()
    assert report(result, "devor")["reason"] == "unreachable: unparseable probe output"


def test_macos_host_end_to_end_through_report(world, pick, monkeypatch):
    monkeypatch.setattr(pick_host, "local_name", lambda: "aarons-macbook-pro")
    world.add("local", MACOS_PROBE, 0)
    world.add("dever", linux_probe(), 12)
    code, result, _ = pick()
    entry = report(result, "mbp")
    assert entry["cores"] == 16 and entry["load5"] == 2.10
    assert entry["available_gb"] == pytest.approx(3.43, abs=0.01)
    assert entry["reason"] == "available 3.4 GB < 6.0 GB"
    assert code == 3


# --- config errors ---

def test_malformed_json_exits_2(world, pick):
    code, result, err = pick(raw="{ not json")
    assert code == 2 and result is None
    assert "malformed JSON" in err


def test_missing_hosts_file_exits_2(world, tmp_path, capsys):
    code = pick_host.main(["--repo", "ccore2", "--hosts", str(tmp_path / "nope.json")])
    assert code == 2
    assert "cannot read hosts file" in capsys.readouterr().err


@pytest.mark.parametrize("raw", ['{"hosts": []}', '{}', '[]', '{"hosts": [{"name": "x"}]}'])
def test_invalid_hosts_structure_exits_2(world, pick, raw):
    code, result, err = pick(raw=raw)
    assert code == 2 and err


def test_orchestrate_hosts_env_selects_file(world, tmp_path, monkeypatch, capsys):
    path = tmp_path / "env-hosts.json"
    path.write_text(json.dumps(hosts_config()))
    monkeypatch.setenv("ORCHESTRATE_HOSTS", str(path))
    healthy(world)
    assert pick_host.main(["--repo", "ccore2"]) == 0
    assert json.loads(capsys.readouterr().out)["host"] in ("mbp", "devor")
