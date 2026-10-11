#!/usr/bin/env python3
"""Re-check every non-terminal row of a tracker and say what the driver does next.

    reconcile.py <tracker-dir> [--now ISO] [--bound name=DURATION ...] [--no-live] [--no-net] [--json]

Reads <tracker-dir>/ledger.md (the `## Status` table, columns matched by header name) and each row's
item file (items/<ID>-*.md, or issues/<ID>-*.md in older trackers) for its `## Timeline` (or `## Log`).
For every row whose state is not terminal it prints the state, the gate, the time since the last
timeline entry, and a verdict. Nothing is written and nothing is launched.

A row states its launch gate in its `Waiting on` cell: `gate: WI-05, WI-07, https://github.com/o/r/pull/9`.
A gate token is an item ID in the same ledger (cleared when that row is MERGED, CLEANED, DONE or CLOSED)
or a GitHub PR URL (cleared when the PR is merged). A deliberate hold reads `park: <reason>`.
Operator waits are recognised by a state of NEEDS_OPERATOR or PROTOTYPE_REVIEW, or by `operator` in the cell.

Verdicts (the driver's action; * = counted in the exit status)
  LAUNCH*   READY, QUEUED or BACKLOG with no open gate and no park: run Handoff step 0 and launch now, or
            record in the item timeline why it cannot (host or lab capacity) and tell the operator.
  CHASE*    a worker or one of its review subagents is past its time bound, idle, or gone.
  STALE*    a row waiting on a gate, research, a block or a park has not moved for the stale bound.
  ASK*      a row waiting on the operator is older than the operator bound: remind them, or tell them why not.
  LAND*     VALIDATED with no operator wait: advance it through the landing queue.
  CLEANUP*  MERGED but not CLEANED: run cleanup per item.
  CHECK*    the script cannot judge the row (unknown state, unknown gate target, unparsable gate).
  WAIT, WAIT_OPERATOR, PARKED, OK   nothing to do yet.

Time bounds (defaults; override with a `Reconcile: worker=60m review=30m stale=24h operator=24h` line in the
ledger header, or `--bound`): worker 60m (a worker idle or silent that long), review 30m (a running review
subagent), stale 24h (a waiting row without a timeline entry), operator 24h (an unanswered ask).
Live checks shell out to `paseo inspect` and `paseo ls` (read-only) and `gh pr view`; `--no-live` and
`--no-net` skip them, and a failure degrades the row to its timeline age.

Exit codes: 0 nothing to act on, 10 at least one starred verdict, 2 bad ledger or arguments.
"""
import argparse, json, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ledger import header, issue_rows, natural

BOUNDS = {"worker": timedelta(minutes=60), "review": timedelta(minutes=30),
          "stale": timedelta(hours=24), "operator": timedelta(hours=24)}
UNITS = {"m": 60, "h": 3600, "d": 86400}

PRELAUNCH = {"READY", "QUEUED", "BACKLOG"}
RESEARCH = {"INTAKE", "RESEARCHING", "NEEDS_INFO"}
WORKER = {"HANDED_OFF", "BUILDING", "REWORK", "IN_PROGRESS", "VALIDATING", "FAILED_VALIDATION", "CLOSING"}
OPERATOR = {"PROTOTYPE_REVIEW", "NEEDS_OPERATOR", "NOT_REPRODUCED", "EXPECTED_BEHAVIOR"}
MERGEWAIT = {"VALIDATED", "READY_TO_MERGE"}
TERMINAL = {"CLEANED", "CLOSED", "DONE", "DEFERRED", "DUPLICATE", "WONT_FIX", "SUPERSEDED", "CONCLUDED"}
CLEARS_A_GATE = {"MERGED", "CLEANED", "DONE", "CLOSED"}
ACTIONABLE = {"LAUNCH", "CHASE", "STALE", "ASK", "LAND", "CLEANUP", "CHECK"}

STAMP = re.compile(r"(\d{4})-(\d{2})-(\d{2})(?:[T ]\s*~?(\d{2}):(\d{2}))?\s*(Z|[+-]\d{2}:\d{2})?")
ENTRY = re.compile(r"^- (\d{4}-\d{2}-\d{2}.*)$")
ITEM_ID = re.compile(r"\b[A-Z]{2,}-\d+\b")
PR_URL = re.compile(r"https://github\.com/[^/\s]+/[^/\s]+/pull/\d+")
UUID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")
MERGED_AT = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}Z")


class Fail(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code = code


def parse_time(s):
    """First timestamp in `s` as an aware datetime (no zone means UTC); None when there is none."""
    m = STAMP.match(s.strip())
    if not m:
        return None
    y, mo, d, hh, mm, tz = m.groups()
    zone = timezone.utc if tz in (None, "Z") else timezone(timedelta(hours=int(tz[:3]), minutes=int(tz[0] + tz[4:])))
    return datetime(int(y), int(mo), int(d), int(hh or 0), int(mm or 0), tzinfo=zone).astimezone(timezone.utc)


def parse_duration(s):
    m = re.fullmatch(r"(\d+(?:\.\d+)?)([mhd])", s.strip())
    if not m:
        raise Fail(2, f"bad duration {s!r}; use a number and m, h or d (for example 90m, 24h)")
    return timedelta(seconds=float(m.group(1)) * UNITS[m.group(2)])


def read_bounds(ledger, overrides):
    bounds = dict(BOUNDS)
    pairs = re.findall(r"(\w+)=(\S+)", header(ledger, "Reconcile")) + [o.partition("=")[::2] for o in overrides]
    for name, value in pairs:
        if name not in bounds:
            raise Fail(2, f"unknown time bound {name!r}; known: {', '.join(bounds)}")
        bounds[name] = parse_duration(value)
    return bounds


def item_file(tracker, row_id):
    for sub in ("items", "issues"):
        for p in sorted((tracker / sub).glob(f"{row_id}-*.md")):
            return p
    return None


def last_movement(path):
    """Newest timestamp in the item's Timeline (or Log), else the item file's mtime, else None. Returns (time, source)."""
    stamps = []
    if path:
        text = path.read_text()
        m = re.search(r"^## (?:Timeline|Log)\n(.*?)(?=^## |\Z)", text, re.S | re.M)
        stamps = [t for l in (m.group(1).splitlines() if m else []) if (e := ENTRY.match(l)) and (t := parse_time(e.group(1)))]
        if stamps:
            return max(stamps), "timeline"
        return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc), "file mtime"
    return None, "no item file"


def state_word(state):
    m = re.match(r"[A-Z_]+", state.upper().strip())
    return m.group(0) if m else ""


def gate_tokens(waiting):
    m = re.search(r"\bgate:\s*([^;|]*)", waiting, re.I)
    if not m:
        return None
    return PR_URL.findall(m.group(1)) + ITEM_ID.findall(PR_URL.sub("", m.group(1)))


def pr_merged(url):
    p = subprocess.run(["gh", "pr", "view", url, "--json", "state"], capture_output=True, text=True)
    if p.returncode != 0:
        return None
    return json.loads(p.stdout)["state"] == "MERGED"


def eval_gate(tokens, by_id, net):
    """(open tokens, unknown tokens, newest cleared time). A closed-unmerged PR counts as unknown: a person decides."""
    open_, unknown, cleared = [], [], None
    for t in tokens:
        if t.startswith("https://"):
            merged = pr_merged(t) if net else None
            if merged is None:
                unknown.append(t)
            elif not merged:
                open_.append(t)
            continue
        row = by_id.get(t)
        if row is None:
            unknown.append(t)
        elif state_word(row.get("state", "")) in CLEARS_A_GATE:
            m = MERGED_AT.match(row.get("merged", ""))
            at = parse_time(m.group(0)) if m else None
            cleared = max(filter(None, (cleared, at)), default=cleared)
        else:
            open_.append(t)
    return open_, unknown, cleared


def human(delta):
    s = int(delta.total_seconds())
    if s < 0:
        return "0m"
    d, rem = divmod(s, 86400)
    h, rem = divmod(rem, 3600)
    return f"{d}d{h}h" if d else f"{h}h{rem // 60:02d}m" if h else f"{rem // 60}m"


# ---- live workers ----------------------------------------------------------

def host_targets():
    """host name -> `--host` target ('' for the local host); empty when there is no usable hosts file."""
    try:
        from pick_host import hosts_path, load_hosts, local_name
        hosts = load_hosts(hosts_path(None))
        me = local_name()
    except Exception:
        return {}
    return {h["name"]: ("" if me in [n.lower() for n in h.get("hostnames", [])] else h["target"]) for h in hosts}


def paseo(args, target):
    cmd = ["paseo", *args, *(["--host", target] if target else []), "--json"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None, "paseo unavailable"
    try:
        out = json.loads(p.stdout)
    except json.JSONDecodeError:
        return None, "paseo output unreadable"
    if p.returncode != 0:
        return None, (out.get("error", {}).get("message", "paseo failed") if isinstance(out, dict) else "paseo failed")
    return out, ""


def inspect(agent, target):
    out, err = paseo(["inspect", agent], target)
    if out is None:
        return {"found": False if "not found" in err.lower() else None, "error": err}
    return {"found": True, "status": out.get("Status"), "updated": parse_time(out.get("UpdatedAt", "")),
            "created": parse_time(out.get("CreatedAt", "")), "parent": out.get("ParentAgentId")}


def probe_workers(rows, now):
    """Per row ID: {'live': inspect result or None, 'reviews': [(name, age)]} for each row with a worker agent id."""
    targets = host_targets()
    jobs = {}
    for r in rows:
        agent = UUID.search(r.get("workspace / agent", ""))
        host = re.match(r"\s*([\w-]+)\s*[:·]", r.get("workspace / agent", ""))
        if agent and state_word(r.get("state", "")) in WORKER:
            jobs[r["id"]] = (agent.group(0), targets.get(host.group(1), "") if host else "")
    result = {i: {"live": None, "reviews": []} for i in jobs}
    with ThreadPoolExecutor(8) as pool:
        for i, live in zip(jobs, pool.map(lambda j: inspect(*j), jobs.values())):
            result[i]["live"] = live
        owner = {agent: i for i, (agent, _) in jobs.items()}
        for target in {t for _, t in jobs.values()}:
            listing, _ = paseo(["ls", "-g"], target)
            reviews = [a for a in listing or [] if a.get("status") == "running" and re.search(r"review", a.get("name", ""), re.I)]
            for a, info in zip(reviews, pool.map(lambda a, t=target: inspect(a["id"], t), reviews)):
                if info.get("found") and info["parent"] in owner and info["created"]:
                    result[owner[info["parent"]]]["reviews"].append((a["name"], now - info["created"]))
    return result


# ---- verdicts --------------------------------------------------------------

def judge(row, by_id, now, bounds, net, probe):
    """One row's verdict dict. `probe` is the live-check result for the row, or None."""
    state, waiting = state_word(row.get("state", "")), row.get("waiting on", "")
    out = {"id": row["id"], "state": row.get("state", ""), "title": row.get("title", ""), "gate": "none"}
    path = item_file(row["_tracker"], row["id"])
    moved, source = last_movement(path)
    age = now - moved if moved else None
    out.update(last_movement=moved.strftime("%Y-%m-%d %H:%MZ") if moved else None, age=human(age) if age else "unknown", age_source=source, _age=age)

    def verdict(v, why):
        out.update(verdict=v, why=why)
        return out

    over = lambda name: age is not None and age > bounds[name]
    tokens = gate_tokens(waiting)
    if tokens is not None:
        out["gate"] = ", ".join(tokens) or "unparsable"
    park = re.search(r"\bpark(?:ed)?:\s*(.*)", waiting, re.I)
    operator = state in OPERATOR or (re.search(r"\boperator\b", waiting, re.I) and state not in PRELAUNCH | WORKER)

    if state in TERMINAL:
        return None
    if state == "MERGED":
        return verdict("CLEANUP", "merged; run cleanup per item")
    if state in PRELAUNCH | RESEARCH | {"BLOCKED"} and tokens is not None:
        if not tokens:
            return verdict("CHECK", "`gate:` names no item ID or PR URL")
        open_, unknown, cleared = eval_gate(tokens, by_id, net)
        out["gate_cleared_at"] = cleared.strftime("%Y-%m-%d %H:%MZ") if cleared else None
        if unknown:
            return verdict("CHECK", f"cannot judge gate: {', '.join(unknown)} (not in this ledger, or PR state unavailable)")
        if open_:
            out["gate"] = f"waiting on {', '.join(open_)}"
            return verdict("STALE" if over("stale") else "WAIT", f"gate open: {', '.join(open_)}" + (f"; no movement for {out['age']}" if over("stale") else ""))
        out["gate"] = f"cleared ({', '.join(tokens)})"
    if state in PRELAUNCH:
        if park:
            return verdict("STALE" if over("stale") else "PARKED", f"parked: {park.group(1).strip() or 'no reason given'}")
        since = f" since {out['gate_cleared_at']}" if out.get("gate_cleared_at") else ""
        return verdict("LAUNCH", f"nothing gates it{since}; launch it, or record why not")
    if state in WORKER:
        return judge_worker(out, now, bounds, probe, verdict)
    if state in OPERATOR or operator:
        return verdict("ASK" if over("operator") else "WAIT_OPERATOR", f"waiting on the operator for {out['age']}")
    if state in MERGEWAIT:
        return verdict("LAND", "validated and no operator wait: advance the landing queue")
    if state in RESEARCH | {"BLOCKED"}:
        return verdict("STALE" if over("stale") else "WAIT", f"{state.lower()} with no movement for {out['age']}")
    return verdict("CHECK", f"unknown state {row.get('state', '')!r}")


def judge_worker(out, now, bounds, probe, verdict):
    live = (probe or {}).get("live")
    long_reviews = [(n, a) for n, a in (probe or {}).get("reviews", []) if a > bounds["review"]]
    if long_reviews:
        names = ", ".join(f"{n} running {human(a)}" for n, a in long_reviews)
        return verdict("CHASE", f"review subagent past {human(bounds['review'])}: {names}")
    if live and live.get("found") is False:
        return verdict("CHASE", "worker agent not found on its host")
    if live and live.get("found"):
        if live["status"] in ("closed", "error"):
            return verdict("CHASE", f"worker agent is {live['status']}")
        since = live["updated"]
        out["live"] = f"{live['status']}, updated {since.strftime('%Y-%m-%d %H:%MZ') if since else 'unknown'}"
        if since and now - since > bounds["worker"]:
            return verdict("CHASE", f"worker {live['status']} with no activity for {human(now - since)}")
        return verdict("OK", f"worker {live['status']}")
    if out["_age"] is not None and out["_age"] > bounds["worker"]:
        return verdict("CHASE", f"no timeline entry for {out['age']} and no live check")
    return verdict("OK", "worker active; live check unavailable" if probe else "worker active (live check off)")


def reconcile(tracker, now=None, bounds_override=(), live=True, net=True):
    tracker = Path(tracker).expanduser().resolve()
    ledger_path = tracker / "ledger.md"
    if not ledger_path.is_file():
        raise Fail(2, f"no ledger at {ledger_path}")
    text = ledger_path.read_text()
    rows = [r for r in issue_rows(text) if r.get("id")]
    if not rows:
        raise Fail(2, f"{ledger_path} has no `## Status` table rows")
    now = now or datetime.now(timezone.utc)
    bounds = read_bounds(text, bounds_override)
    by_id = {r["id"]: r for r in rows}
    for r in rows:
        r["_tracker"] = tracker
    concluded = header(text, "Mode").upper().startswith("CONCLUDED")
    probes = probe_workers(rows, now) if live and not concluded else {}
    results = []
    for r in sorted(rows, key=lambda r: natural(r["id"])):
        v = judge(r, by_id, now, bounds, net, probes.get(r["id"]))
        if v:
            results.append(v)
    return results, bounds


def summary(tracker, results):
    counts = {v: sum(1 for r in results if r["verdict"] == v) for v in ("LAUNCH", "CHASE", "STALE", "ASK", "LAND", "CLEANUP", "CHECK")}
    actions = sum(counts.values())
    return f"RECONCILE {Path(tracker).name}: {len(results)} open rows; " + " ".join(f"{k.lower()}={n}" for k, n in counts.items()) + f"; actions={actions}", actions


def show(results):
    cols = ("ID", "STATE", "GATE", "LAST MOVEMENT", "AGE", "VERDICT")
    rows = [(r["id"], r["state"][:28], r["gate"][:40], r["last_movement"] or "none", r["age"], r["verdict"]) for r in results]
    width = [max(len(str(x)) for x in col) for col in zip(cols, *rows)]
    line = lambda cells: "  ".join(str(c).ljust(w) for c, w in zip(cells, width)).rstrip()
    out = [line(cols)] + [line(r) for r in rows] + [""]
    out += [f"{r['id']}  {r['verdict']}: {r['why']}" + (f" [{r['live']}]" if r.get("live") else "") for r in results if r["verdict"] in ACTIONABLE | {"PARKED"}]
    return "\n".join(out)


def public(r):
    return {k: v for k, v in r.items() if not k.startswith("_")}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("tracker_dir")
    ap.add_argument("--now", help="evaluate as of this time (ISO, UTC unless a zone is given); default: the current time")
    ap.add_argument("--bound", action="append", default=[], metavar="NAME=DURATION", help="override a time bound, for example worker=45m")
    ap.add_argument("--no-live", action="store_true", help="skip `paseo` worker and review checks")
    ap.add_argument("--no-net", action="store_true", help="skip `gh` PR gate checks (such gates become CHECK)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        now = parse_time(a.now) if a.now else None
        if a.now and not now:
            raise Fail(2, f"cannot read --now {a.now!r}")
        results, bounds = reconcile(a.tracker_dir, now, a.bound, not a.no_live, not a.no_net)
    except Fail as f:
        print(f"reconcile: {f}", file=sys.stderr)
        return f.code
    line, actions = summary(a.tracker_dir, results)
    if a.json:
        print(json.dumps({"summary": line, "actions": actions, "rows": [public(r) for r in results]}, indent=2))
    else:
        print(show(results) if results else "No open rows.")
        print("\n" + line)
    return 10 if actions else 0


if __name__ == "__main__":
    sys.exit(main())
