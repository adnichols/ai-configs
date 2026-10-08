#!/usr/bin/env python3
"""Fill the ledger Status table's Merged and Deployed columns.

usage: deploy_status.py <tracker-dir> --repo <checkout> [--target <name>=<commit> ...]

Merged: every done row whose PR column holds GitHub PR URLs and whose Merged cell is empty gets
the latest merge time and that merge commit from `gh pr view`, as `2026-10-08 19:42Z 562a1a890`.

Deployed: with --target, every merged row whose PRs belong to the --repo checkout's repository,
and is not already deployed everywhere, gets how many targets run a commit that contains its
merge commit, plus the check time. Read each target's deployed commit from the repository's
read-only status command (ccore2: `pnpm rollout`, the platform Worker's source commit per hub).
This script never deploys anything.

Missing Merged and Deployed columns are added. Republish the dashboard afterwards.
"""
import argparse, json, re, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dashboard import MERGED_AT, group_of  # noqa: E402

PR_URL = re.compile(r"https://github\.com/[^/\s]+/([^/\s]+)/pull/\d+")


def run(*cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def joined(c):
    return "| " + " | ".join(c) + " |"


def merge_of(urls):
    """(`YYYY-MM-DD HH:MMZ sha`, sha) for the newest merged PR among urls, or None if none merged."""
    best = None
    for url in urls:
        p = run("gh", "pr", "view", url, "--json", "mergedAt,mergeCommit")
        if p.returncode:
            raise SystemExit(f"gh pr view {url} failed: {p.stderr.strip()}")
        d = json.loads(p.stdout)
        if d.get("mergedAt") and (best is None or d["mergedAt"] > best[0]):
            best = (d["mergedAt"], d["mergeCommit"]["oid"][:9])
    if best is None:
        return None
    at = datetime.strptime(best[0], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%MZ")
    return f"{at} {best[1]}"


def deployed_cell(sha, targets, repo, checked):
    """`yes, all N`, `no, 0 of N`, or `partly, K of N; not yet: <names>`. A target whose deployed
    commit is not in the checkout's history counts as not deployed and is marked `(unknown commit)`."""
    hit, missing = 0, []
    for name, commit in targets:
        code = run("git", "merge-base", "--is-ancestor", sha, commit, cwd=repo).returncode
        if code == 0:
            hit += 1
        else:
            missing.append(name if code == 1 else f"{name} (unknown commit)")
    total = len(targets)
    unknown = [m for m in missing if m.endswith("(unknown commit)")]
    if hit == total:
        state = f"yes, all {total}"
    elif hit == 0:
        state = f"no, 0 of {total}" + (f"; {', '.join(unknown)}" if unknown else "")
    else:
        state = f"partly, {hit} of {total}; not yet: {', '.join(missing)}"
    return f"{state} (checked {checked})"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("tracker")
    ap.add_argument("--repo", required=True, help="checkout of the repository whose merges are checked")
    ap.add_argument("--target", action="append", default=[], metavar="NAME=COMMIT")
    args = ap.parse_args()
    targets = [tuple(t.split("=", 1)) for t in args.target]
    if any(len(t) != 2 or not t[1] for t in targets):
        ap.error("--target takes NAME=COMMIT")

    remote = run("git", "remote", "get-url", "origin", cwd=args.repo).stdout.strip()
    repo_name = re.sub(r"\.git$", "", remote.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1])
    if targets and run("git", "fetch", "-q", "origin", cwd=args.repo).returncode:
        raise SystemExit(f"git fetch failed in {args.repo}")
    checked = datetime.now(timezone.utc).strftime("%m-%d %H:%MZ")

    path = Path(args.tracker) / "ledger.md"
    lines = path.read_text().split("\n")
    start = lines.index("## Status") + 1
    head = next(i for i in range(start, len(lines)) if lines[i].startswith("|"))
    cols = [c.lower() for c in cells(lines[head])]
    for name in ("Merged", "Deployed"):
        if name.lower() not in cols:
            cols.append(name.lower())
            lines[head] = joined(cells(lines[head]) + [name])
            lines[head + 1] = joined(cells(lines[head + 1]) + ["-" * len(name)])
    width, merged_n, deployed_n = len(cols), 0, 0
    i = head + 2
    while i < len(lines) and lines[i].startswith("|"):
        c = cells(lines[i])
        c += ["—"] * (width - len(c))
        row = dict(zip(cols, c))
        urls = [m.group(0) for m in PR_URL.finditer(row.get("pr", ""))]
        if group_of(row.get("state", ""))[0] == "done" and urls and not MERGED_AT.match(row["merged"]):
            value = merge_of(urls)
            if value:
                c[cols.index("merged")] = row["merged"] = value
                merged_n += 1
        ours = any(m.group(1) == repo_name for m in PR_URL.finditer(row.get("pr", "")))
        if targets and ours and MERGED_AT.match(row["merged"]) and not row["deployed"].startswith("yes, all"):
            c[cols.index("deployed")] = deployed_cell(row["merged"].split()[-1], targets, args.repo, checked)
            deployed_n += 1
        lines[i] = joined(c)
        i += 1
    path.write_text("\n".join(lines))
    print(f"merged filled: {merged_n}; deployed checked: {deployed_n}")


if __name__ == "__main__":
    main()
