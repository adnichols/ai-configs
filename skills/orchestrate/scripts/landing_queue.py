#!/usr/bin/env python3
"""Report where each PR in a tracker's landing queue stands and what the driver does next.

    landing_queue.py <tracker-dir> [--repo DIR] [--remote origin] [--base main] [--json]

Reads `## Landing queue` in <tracker-dir>/ledger.md: an ordered list, one entry per line,
`1. #<pr> <ID> validated <sha> — <LANDING|ON_DECK|WAITING> <note>`, or the single line `Empty.`.
Fetches the base and each `pull/<n>/head` into refs/landing-queue/ (fork-safe), then reports per entry:
head versus validated sha, PR state, conflict files, and overlap files (changed on the base since the
merge-base and also changed by the PR). Verdicts:
  position 1   MERGE (merge now at the validated head), UPDATE (conflict, overlap or strict branch policy),
               REVALIDATE (head moved), BLOCKED (closed, draft, or GitHub and git disagree on a conflict)
  position 2   ON_DECK, with a preview of its conflicts and overlap as if position 1 had merged as-is
  later        WAIT; MOVED when the head differs from the validated sha
Nothing in the working tree or branches changes; only refs/landing-queue/* and loose git objects are written.

Exit codes: 0 reported, 2 bad ledger or arguments, 3 git or gh failed.
"""
import argparse, json, os, re, subprocess, sys
from pathlib import Path

ENTRY = re.compile(r"^(\d+)\. #(\d+) (\S+) validated ([0-9a-f]{7,40})\b\s*(?:[—–-]\s*)?(?:(LANDING|ON_DECK|WAITING)\b\s*)?(.*)$")
IDENT = {f"GIT_{w}_{k}": v for w in ("AUTHOR", "COMMITTER") for k, v in (("NAME", "landing-queue"), ("EMAIL", "landing-queue@localhost"))}


class Fail(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code = code


def parse(tracker):
    ledger = Path(tracker) / "ledger.md"
    if not ledger.is_file():
        raise Fail(2, f"no ledger at {ledger}")
    m = re.search(r"^## Landing queue\n(.*?)(?=^## |\Z)", ledger.read_text(), re.S | re.M)
    if not m:
        raise Fail(2, f"{ledger} has no `## Landing queue` section")
    lines = [l.strip() for l in m.group(1).splitlines() if l.strip()]
    if lines == ["Empty."]:
        return []
    out = []
    for n, line in enumerate(lines, 1):
        e = ENTRY.match(line)
        if not e or int(e.group(1)) != n:
            raise Fail(2, f"landing queue line {n} is not `{n}. #<pr> <ID> validated <sha> — <LANDING|ON_DECK|WAITING> <note>`: {line!r}")
        out.append({"position": n, "pr": int(e.group(2)), "id": e.group(3), "validated": e.group(4), "note": e.group(6)})
    if not out:
        raise Fail(2, "`## Landing queue` is empty; write `Empty.` when nothing is queued")
    return out


def run(cmd, cwd, ok=(0,), env=None):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env={**os.environ, **(env or {})})
    if p.returncode not in ok:
        raise Fail(3, f"`{' '.join(cmd[:4])}` failed (exit {p.returncode}): {(p.stderr or p.stdout).strip()[:300]}")
    return p


def git(repo, *args, ok=(0,), env=None):
    return run(["git", "-C", repo, *args], None, ok, env)


def names(repo, a, b):
    return set(git(repo, "diff", "--name-only", a, b).stdout.split())


def analyze(repo, base, head):
    """Conflict and overlap files for merging `head` into `base` (both are commits)."""
    p = git(repo, "merge-tree", "--write-tree", "--name-only", base, head, ok=(0, 1))
    conflicts = sorted(set(p.stdout.split("\n\n")[0].splitlines()[1:])) if p.returncode == 1 else []
    mb = git(repo, "merge-base", base, head).stdout.strip()
    return {"conflicts": conflicts, "overlap": sorted((names(repo, mb, base) & names(repo, mb, head)) - set(conflicts))}


def strict_policy(repo, base):
    p = subprocess.run(["gh", "api", f"repos/{{owner}}/{{repo}}/branches/{base}/protection"], cwd=repo, capture_output=True, text=True)
    if p.returncode == 0:
        return bool((json.loads(p.stdout).get("required_status_checks") or {}).get("strict"))
    return False if "HTTP 404" in p.stderr else None


def collect(entries, repo, remote, base):
    refs = [f"+refs/heads/{base}:refs/landing-queue/base"] + [f"+pull/{e['pr']}/head:refs/landing-queue/pr{e['pr']}" for e in entries]
    git(repo, "fetch", "--quiet", "--no-tags", "--no-write-fetch-head", remote, *refs)
    base_sha = git(repo, "rev-parse", "refs/landing-queue/base").stdout.strip()
    for e in entries:
        view = json.loads(run(["gh", "pr", "view", str(e["pr"]), "--json", "state,isDraft,mergeable,headRefOid"], repo).stdout)
        e.update(head=git(repo, "rev-parse", f"refs/landing-queue/pr{e['pr']}").stdout.strip(), state=view["state"],
                 draft=view["isDraft"], mergeable=view["mergeable"])
        if e["head"] != view["headRefOid"]:
            raise Fail(3, f"#{e['pr']}: fetched head {e['head'][:9]} differs from GitHub's {view['headRefOid'][:9]}; rerun")
        e["moved"] = not e["head"].startswith(e["validated"])
        e.update(analyze(repo, base_sha, e["head"]))
    return base_sha


def judge(entries, repo, base_sha, strict):
    first = entries[0]
    flags = lambda e: [f for f, on in (("MOVED", e["moved"]), ("DRAFT", e["draft"]), ("CLOSED", e["state"] != "OPEN")) if on]
    for e in entries:
        e["flags"] = flags(e)
    reasons = []
    if first["state"] != "OPEN" or first["draft"]:
        first["verdict"], reasons = "BLOCKED", ["PR is a draft" if first["state"] == "OPEN" else f"PR is {first['state'].lower()}"]
    elif first["mergeable"] == "CONFLICTING" and not first["conflicts"]:
        first["verdict"], reasons = "BLOCKED", ["GitHub reports CONFLICTING but a local merge is clean; check the PR"]
    elif first["moved"]:
        first["verdict"], reasons = "REVALIDATE", [f"head {first['head'][:9]} is not the validated {first['validated']}"]
    elif first["conflicts"] or first["overlap"]:
        first["verdict"] = "UPDATE"
        reasons = (["conflicts with the base"] if first["conflicts"] else []) + (["base changed files this PR also changes"] if first["overlap"] else [])
    elif strict:
        first["verdict"], reasons = "UPDATE", ["repository requires up-to-date branch"]
    else:
        first["verdict"] = "MERGE"
    first["reasons"] = reasons
    if len(entries) > 1:
        second, target, against = entries[1], base_sha, "base"
        if first["verdict"] in ("MERGE", "UPDATE") and not first["conflicts"]:
            tree = git(repo, "merge-tree", "--write-tree", base_sha, first["head"]).stdout.split()[0]
            target = git(repo, "commit-tree", tree, "-p", base_sha, "-p", first["head"], "-m", "landing-queue preview", env=IDENT).stdout.strip()
            against = f"base + #{first['pr']} merged as-is"
        second.update(verdict="ON_DECK", reasons=[], preview={"against": against, **analyze(repo, target, second["head"])})
    for e in entries[2:]:
        e.update(verdict="WAIT", reasons=[])


def files(paths, limit=8):
    return (", ".join(paths[:limit]) + (f", ... {len(paths) - limit} more (see --json)" if len(paths) > limit else "")) or "none"


def show(e):
    flag = f" [{' '.join(e['flags'])}]" if e["flags"] else ""
    out = [f"{e['position']}. #{e['pr']} {e['id']}  {e['verdict']}{flag}",
           f"   head {e['head'][:9]} (validated {e['validated']}), {e['state']}{', draft' if e['draft'] else ''}, GitHub mergeable: {e['mergeable']}",
           f"   conflicts: {files(e['conflicts'])}", f"   overlap: {files(e['overlap'])}"]
    out += [f"   why: {r}" for r in e["reasons"]]
    if "preview" in e:
        p = e["preview"]
        out += [f"   prep preview against {p['against']}:", f"     conflicts: {files(p['conflicts'])}", f"     overlap: {files(p['overlap'])}"]
    if e["verdict"] == "MERGE":
        out.append(f"   next: gh pr merge {e['pr']} --squash --match-head-commit {e['head']}")
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
        entries = parse(a.tracker_dir)
        if not entries:
            print("[]" if a.json else "Landing queue is empty.")
            return 0
        base_sha = collect(entries, a.repo, a.remote, a.base)
        strict = strict_policy(a.repo, a.base)
        judge(entries, a.repo, base_sha, strict)
    except Fail as f:
        print(f"landing_queue: {f}", file=sys.stderr)
        return f.code
    if a.json:
        print(json.dumps(entries, indent=2))
    else:
        print(f"base {a.base} @ {base_sha[:9]}; branch policy requires up-to-date: {'unknown' if strict is None else 'yes' if strict else 'no'}\n")
        print("\n\n".join(show(e) for e in entries))
    return 0


if __name__ == "__main__":
    sys.exit(main())
