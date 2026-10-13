# Hosts file

`$ORCHESTRATE_HOSTS`, else `~/.config/orchestrate/hosts.json`, identical on
every machine. No file: every worker runs on the orchestrator's machine.

```json
{ "hosts": [
  { "name": "mbp", "target": "ssh://mbp", "hostnames": ["aarons-macbook-pro"],
    "max_workers": 16, "min_available_gb": 4, "max_swap_gb": 4, "max_load_per_core": 2.0, "per_worker_gb": 2,
    "checkouts": { "ccore2": "/Users/anichols/code/ccore2" } },
  { "name": "dever", "target": "ssh://dever", "hostnames": ["dever"],
    "max_workers": 12, "min_available_gb": 6, "max_swap_gb": 4, "max_load_per_core": 1.5, "per_worker_gb": 2,
    "checkouts": { "ccore2": "/home/anichols/code/ccore2" } } ] }
```

- `name`: host name in ledger and item files. `target`: the `paseo --host`
  value; ssh alias = target without `ssh://`, as seen from the orchestrator's
  machine (Mac → `dever`, Dever → `mbp`).
- `hostnames`: lowercase short hostnames. A host is **local** when the
  orchestrator's lowercase short `socket.gethostname()` (no `.local` or
  domain) is listed; local hosts use no ssh or `--host` and drive workers with
  the Paseo MCP tools.
- `checkouts`: repo key → checkout path on that host (`pick_host.py` returns
  it as `checkout`).
- Limits (optional; defaults): `max_workers` 12, `min_available_gb` 6,
  `max_swap_gb` 4, `max_load_per_core` 1.5, `per_worker_gb` 2. `pick_host.py`
  probes running agents, available memory, swap, and load; a host is eligible
  only within limits with room for one more worker (`reason` says why not).
  Swap counts only while available memory < 2 × (`min_available_gb` +
  `per_worker_gb`), because Linux keeps pages in swap long after pressure
  ends. `mbp` runs only agents, so its limits are looser. Tune limits in the
  file, never per tracker.
- The Paseo MCP tools reach only the local daemon. Each host runs its own
  daemon; remote workers are launched, messaged, inspected, and cleaned with
  the `paseo` CLI and `--host <target>`, and send no native finish
  notification (SKILL.md § Worker notifications).
- One-time setup per host, not per item: ai-configs skills in
  `~/.agents/skills`, `gh` and `ava` authenticated, lab-manager credentials,
  the `omp` Paseo profile. A remote worker reporting a missing tool or
  credential: fix that host once and record it.
- Labs are shared cloud labs; host admission is not lab capacity. The
  per-lab-system cap (SKILL.md § Handoff) counts workers on all hosts.
- Ledger line at tracker start, one entry per host, defaults filled in:
  `Hosts: <name> (local|remote) max <N> workers, avail >= <G> GB, swap <= <S>
  GB, load <= <L>/core; ...`.
