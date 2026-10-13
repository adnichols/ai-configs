#!/usr/bin/env python3
"""Report where each PR in a tracker's landing queue stands and what the driver does next.

    landing_queue.py <tracker-dir> [--repo DIR] [--remote origin] [--base main] [--json]

Reads `## Landing queue` in <tracker-dir>/ledger.md: an ordered list, one entry per line,
`1. #<pr> <ID> validated <sha> — <note>`, or the single line `Empty.`. The optional ledger header line
`Generated paths: <glob>, <glob>` lists fnmatch globs (`*` crosses `/`) for files every PR regenerates;
overlap there never forces an update or a wait (a conflict there still does).
Fetches the base and each `pull/<n>/head` into refs/landing-queue/ (fork-safe) and judges every entry
against the current base. Each PR already carries a receipt run on its head merged with main; the
script decides whether that receipt still covers the tree a merge would produce:
  MERGE       open, head = validated, no conflict, main has not changed this PR's files since the PR's
              last main merge, and no earlier landing entry shares its files; merge now
  UPDATE      conflicts, main changed files this PR changes, or the branch policy requires up-to-date
  WAIT        shares changed files with an earlier MERGE, UPDATE or WAIT entry; lands after it
  REVALIDATE  head moved from the validated sha
  BLOCKED     closed, draft, or GitHub reports a conflict a local merge does not have
Also reads <tracker-dir>/gates.jsonl, the main gate runs the driver records (other kinds are ignored):
  {"kind":"main","sha":"<sha>","result":"RUNNING|CLEAN|FAILED","log":"<path>"}
The main gate never blocks a merge; the script reports the base's status, whether a run is due, and the
deploy candidate (the newest CLEAN main record).
Nothing in the working tree or branches changes; only refs/landing-queue/* are written.

Exit codes: 0 reported, 2 bad ledger, gate records or arguments, 3 git or gh failed.
"""
import argparse, json, os, re, subprocess, sys
from fnmatch import fnmatch
from pathlib import Path

ENTRY = re.compile(r"^(\d+)\. #(\d+) (\S+) validated ([0-9a-f]{7,40})\b\s*(?:[—–-]\s*)?(?:(?:LANDING|ON_DECK|WAITING)\b\s*)?(.*)$")
LANDING = ("MERGE", "UPDATE", "WAIT")


class Fail(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code = code


def parse(tracker):
    ledger = Path(tracker) / "ledger.md"
    if not ledger.is_file():
        raise Fail(2, f"no ledger at {ledger}")
    text = ledger.read_text()
    g = re.search(r"^Generated paths:(.*)$", text, re.M)
    generated = [p.strip() for p in g.group(1).split(",") if p.strip()] if g else []
    m = re.search(r"^## Landing queue\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    if not m:
        raise Fail(2, f"{ledger} has no `## Landing queue` section")
    lines = [l.strip() for l in m.group(1).splitlines() if l.strip()]
    if lines == ["Empty."]:
        return [], generated
    out = []
    for n, line in enumerate(lines, 1):
        e = ENTRY.match(line)
        if not e or int(e.group(1)) != n:
            raise Fail(2, f"landing queue line {n} is not `{n}. #<pr> <ID> validated <sha> — <note>`: {line!r}")
        out.append({"position": n, "pr": int(e.group(2)), "id": e.group(3), "validated": e.group(4), "note": e.group(5)})
    if not out:
        raise Fail(2, "`## Landing queue` is empty; write `Empty.` when nothing is queued")
    return out, generated


def run(cmd, cwd, ok=(0,)):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=os.environ)
    if p.returncode not in ok:
        raise Fail(3, f"`{' '.join(cmd[:4])}` failed (exit {p.returncode}): {(p.stderr or p.stdout).strip()[:300]}")
    return p


def git(repo, *args, ok=(0,)):
    return run(["git", "-C", repo, *args], None, ok)


def names(repo, a, b):
    return set(git(repo, "diff", "--name-only", a, b).stdout.split())


def analyze(repo, base, head, generated):
    """Conflicts, the PR's own changes, and overlap (base changes since the merge-base that the PR also changes)."""
    p = git(repo, "merge-tree", "--write-tree", "--name-only", base, head, ok=(0, 1))
    conflicts = sorted(set(p.stdout.split("\n\n")[0].splitlines()[1:])) if p.returncode == 1 else []
    mb = git(repo, "merge-base", base, head).stdout.strip()
    keep = lambda paths: {f for f in paths if not any(fnmatch(f, g) for g in generated)}
    changes = keep(names(repo, mb, head))
    return {"conflicts": conflicts, "changes": sorted(changes), "overlap": sorted((keep(names(repo, mb, base)) & changes) - set(conflicts))}


def strict_policy(repo, base):
    p = subprocess.run(["gh", "api", f"repos/{{owner}}/{{repo}}/branches/{base}/protection"], cwd=repo, capture_output=True, text=True)
    if p.returncode == 0:
        return bool((json.loads(p.stdout).get("required_status_checks") or {}).get("strict"))
    return False if "HTTP 404" in p.stderr else None


def fetch(entries, repo, remote, base):
    refs = [f"+refs/heads/{base}:refs/landing-queue/base"] + [f"+pull/{e['pr']}/head:refs/landing-queue/pr{e['pr']}" for e in entries]
    git(repo, "fetch", "--quiet", "--no-tags", "--no-write-fetch-head", remote, *refs)
    return git(repo, "rev-parse", "refs/landing-queue/base").stdout.strip()


def collect(entries, repo, base_sha, generated):
    for e in entries:
        view = json.loads(run(["gh", "pr", "view", str(e["pr"]), "--json", "state,isDraft,mergeable,headRefOid"], repo).stdout)
        e.update(head=git(repo, "rev-parse", f"refs/landing-queue/pr{e['pr']}").stdout.strip(), state=view["state"],
                 draft=view["isDraft"], mergeable=view["mergeable"])
        if e["head"] != view["headRefOid"]:
            raise Fail(3, f"#{e['pr']}: fetched head {e['head'][:9]} differs from GitHub's {view['headRefOid'][:9]}; rerun")
        e["moved"] = not e["head"].startswith(e["validated"])
        e.update(analyze(repo, base_sha, e["head"], generated))


def read_gates(tracker):
    path = Path(tracker) / "gates.jsonl"
    if not path.is_file():
        return []
    out = []
    for n, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            g = json.loads(line)
        except ValueError:
            raise Fail(2, f"{path} line {n} is not JSON")
        if not isinstance(g, dict) or g.get("kind") != "main":
            continue
        if g.get("result") not in ("RUNNING", "CLEAN", "FAILED") or len(str(g.get("sha", ""))) < 7:
            raise Fail(2, f"{path} line {n} is not a main gate record (kind main, sha, result RUNNING|CLEAN|FAILED, log)")
        if g["result"] != "RUNNING" and not g.get("log"):
            raise Fail(2, f"{path} line {n}: a finished main gate record needs a log path")
        out.append(g)
    return out


def same_sha(a, b):
    a, b = str(a), str(b)
    return len(a) >= 7 and len(b) >= 7 and (a.startswith(b) or b.startswith(a))


def main_status(gates, base_sha):
    """The base's own record, any run in progress, and the deploy candidate."""
    latest = {}
    for g in gates:
        latest[g["sha"]] = g
    here = next((g for s, g in latest.items() if same_sha(s, base_sha)), None)
    running = next((g for g in latest.values() if g["result"] == "RUNNING"), None)
    clean = [g for g in gates if g["result"] == "CLEAN" and latest[g["sha"]] is g]
    return {"base": base_sha, "record": here, "running": running, "candidate": clean[-1] if clean else None,
            "due": here is None and running is None}


def judge(entries, base_sha, strict):
    ahead = []
    for e in entries:
        e["flags"] = [f for f, on in (("MOVED", e["moved"]), ("DRAFT", e["draft"]), ("CLOSED", e["state"] != "OPEN")) if on]
        if e["state"] != "OPEN" or e["draft"]:
            e["verdict"], reasons = "BLOCKED", ["PR is a draft" if e["state"] == "OPEN" else f"PR is {e['state'].lower()}"]
        elif e["mergeable"] == "CONFLICTING" and not e["conflicts"]:
            e["verdict"], reasons = "BLOCKED", ["GitHub reports CONFLICTING but a local merge is clean; check the PR"]
        elif e["moved"]:
            e["verdict"], reasons = "REVALIDATE", [f"head {e['head'][:9]} is not the validated {e['validated']}"]
        else:
            blockers = [a for a in ahead if set(a["changes"]) & set(e["changes"])]
            if blockers:
                shared = sorted(set(blockers[0]["changes"]) & set(e["changes"]))
                e["verdict"], reasons = "WAIT", [f"shares {files(shared, 3)} with #{blockers[0]['pr']} ahead in the queue; lands after it"]
            elif e["conflicts"]:
                e["verdict"], reasons = "UPDATE", ["conflicts with the base"]
            elif e["overlap"]:
                e["verdict"], reasons = "UPDATE", [f"main changed {files(e['overlap'], 3)} since this PR's last main merge"]
            elif strict:
                e["verdict"], reasons = "UPDATE", ["repository requires up-to-date branch"]
            else:
                e["verdict"], reasons = "MERGE", []
        e["reasons"], e["base"] = reasons, base_sha
        if e["verdict"] in LANDING:
            ahead.append(e)


def files(paths, limit=8):
    return (", ".join(paths[:limit]) + (f", ... {len(paths) - limit} more (see --json)" if len(paths) > limit else "")) or "none"


def show(e):
    flag = f" [{' '.join(e['flags'])}]" if e["flags"] else ""
    out = [f"{e['position']}. #{e['pr']} {e['id']}  {e['verdict']}{flag}",
           f"   head {e['head'][:9]} (validated {e['validated']}), {e['state']}{', draft' if e['draft'] else ''}, GitHub mergeable: {e['mergeable']}",
           f"   conflicts: {files(e['conflicts'])}", f"   overlap: {files(e['overlap'])}"]
    out += [f"   why: {r}" for r in e["reasons"]]
    if e["verdict"] == "MERGE":
        out.append(f"   next: gh pr merge {e['pr']} --squash --match-head-commit {e['head']}, then rerun this script")
    if e["verdict"] == "UPDATE":
        out.append("   next: tell the worker to merge main once (merge commit), resolve, rerun its receipt, push, and report VALIDATED")
    return "\n".join(out)


def show_main(m):
    rec, cand, run_ = m["record"], m["candidate"], m["running"]
    here = f"{rec['result']}" + (f" (log {rec['log']})" if rec.get("log") else "") if rec else "no record"
    out = [f"main gate @ {m['base'][:9]}: {here}"]
    if run_ and not (rec and rec is run_):
        out.append(f"main gate running on {run_['sha'][:9]}")
    out.append(f"deploy candidate (Last CLEAN main): {cand['sha'][:9]} (log {cand['log']})" if cand else "deploy candidate (Last CLEAN main): none")
    if m["due"]:
        out.append(f"next: start the full gate on main {m['base'][:9]} in the landing worktree (non-blocking) and append "
                   f"{json.dumps({'kind': 'main', 'sha': m['base'], 'result': 'RUNNING'})}")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("tracker_dir")
    ap.add_argument("--repo", default=".", help="local clone of the target repository")
    ap.add_argument("--remote", default="origin")
    ap.add_argument("--base", default="main")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    try:
        entries, generated = parse(a.tracker_dir)
        gates = read_gates(a.tracker_dir)
        base_sha = fetch(entries, a.repo, a.remote, a.base)
        collect(entries, a.repo, base_sha, generated)
        strict = strict_policy(a.repo, a.base) if entries else None
        judge(entries, base_sha, strict)
        status = main_status(gates, base_sha)
    except Fail as f:
        print(f"landing_queue: {f}", file=sys.stderr)
        return f.code
    if a.json:
        print(json.dumps({"base": base_sha, "main_gate": status, "entries": entries}, indent=2))
        return 0
    print(f"base {a.base} @ {base_sha[:9]}; branch policy requires up-to-date: {'unknown' if strict is None else 'yes' if strict else 'no'}")
    print(show_main(status) + "\n")
    print("\n\n".join(show(e) for e in entries) if entries else "Landing queue is empty.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
