#!/usr/bin/env python3
"""Check a ccore2 PR's gate receipts against its current head before the monitor merges it.

Usage: gate-check.py <PR> [--receipts PATH] [--repo Nodaste-Lab/ccore2] [--checkout ~/code/ccore2]

Exit 0 = every gate is present, passing, and bound to the current patch-id; the monitor may merge.
Exit 1 = gates missing or stale; stdout lists exactly what to nudge for.
Exit 2 = no local worktree for the branch (PR from another host, e.g. dever); report only.
"""
import argparse
import glob
import json
import os
import subprocess
import sys

REQUIRED = ["interrogate", "deslop", "no-comments", "autoreview", "lab"]
PASSING = {"PASS", "PASS+NOTES"}
LAB_NA_REASONS = {"test-only", "docs-only", "lab-manager-undeployed", "no-repro-red-green"}


def run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True).stdout


def find_worktree(checkout, branch):
    path = None
    for line in run(["git", "worktree", "list", "--porcelain"], cwd=checkout).splitlines():
        if line.startswith("worktree "):
            path = line[len("worktree "):]
        elif line == f"branch refs/heads/{branch}":
            return path
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pr", type=int)
    ap.add_argument("--repo", default="Nodaste-Lab/ccore2")
    ap.add_argument("--checkout", default=os.path.expanduser("~/code/ccore2"))
    ap.add_argument("--receipts")
    args = ap.parse_args()

    pr = json.loads(run(["gh", "pr", "view", str(args.pr), "-R", args.repo, "--json",
                         "headRefName,headRefOid,baseRefName,state,mergeable,comments"]))
    if pr["state"] != "OPEN":
        print(f"#{args.pr} is {pr['state']}; nothing to check.")
        return 1

    wt = find_worktree(args.checkout, pr["headRefName"])
    if wt is None:
        print(f"#{args.pr} EXTERNAL: no local worktree for {pr['headRefName']} (another host?). Report only.")
        return 2

    run(["git", "fetch", "-q", "origin", pr["baseRefName"], pr["headRefName"]], cwd=wt)
    head = pr["headRefOid"]
    base = f"origin/{pr['baseRefName']}"
    diff = run(["git", "diff", run(["git", "merge-base", base, head], cwd=wt).strip(), head], cwd=wt)
    patch_id = subprocess.run(["git", "patch-id", "--stable"], input=diff, capture_output=True,
                              text=True, check=True).stdout.split()[0] if diff else ""

    problems = []
    notes = []
    if subprocess.run(["git", "merge-base", "--is-ancestor", base, head], cwd=wt).returncode != 0:
        problems.append(f"rebase onto {base} (head {head[:9]} is behind)")
    if pr["mergeable"] == "CONFLICTING":
        problems.append("resolve merge conflicts")

    receipts_path = args.receipts
    if receipts_path is None:
        hits = glob.glob(os.path.join(wt, ".ccore/verified-build/*/gates.json"))
        hits = [h for h in hits if json.load(open(h)).get("pr") == args.pr]
        receipts_path = hits[0] if len(hits) == 1 else None
        if len(hits) > 1:
            problems.append(f"one gates.json per PR; found {len(hits)}")
    gates = {}
    if receipts_path and os.path.exists(receipts_path):
        for g in json.load(open(receipts_path)).get("gates", []):
            gates[g["gate"]] = g  # later entries supersede earlier runs of the same gate
    else:
        problems.append("write .ccore/verified-build/<slug>/gates.json")

    for name in REQUIRED:
        g = gates.get(name)
        if g is None:
            problems.append(f"{name}: missing")
            continue
        if g.get("patch_id") != patch_id:
            problems.append(f"{name}: stale (receipt patch-id {str(g.get('patch_id'))[:12]}, current {patch_id[:12]})")
        if g.get("exception") and g.get("exception_approved_by") != "Aaron":
            problems.append(f"{name}: exception '{g['exception']}' needs Aaron's approval (exception_approved_by)")
        if name == "lab" and g.get("result") == "NA":
            reason = g.get("na_reason")
            if reason not in LAB_NA_REASONS:
                problems.append(f"lab: NA reason '{reason}' not in {sorted(LAB_NA_REASONS)}")
            if reason == "no-repro-red-green" and not g.get("test"):
                problems.append("lab: no-repro-red-green needs the red/green test named in 'test'")
        elif g.get("result") not in PASSING:
            problems.append(f"{name}: result {g.get('result')}")
        if name == "autoreview":
            if not g.get("reviewer_role"):
                problems.append("autoreview: record 'reviewer_role' (the OMP role that ran the single review)")
            if not any(patch_id[:12] in c["body"] for c in pr["comments"]):
                problems.append(f"autoreview: post the review as a PR comment citing patch-id {patch_id[:12]}")
            if g.get("family") and g.get("family") == g.get("author_family"):
                notes.append("autoreview: reviewer and author share a model family (note only; roles define coverage)")

    status = "READY" if not problems else "MISSING"
    print(f"#{args.pr} {status} head={head[:9]} patch-id={patch_id[:12]} worktree={wt}")
    for n in notes:
        print(f"  note: {n}")
    for p in problems:
        print(f"  - {p}")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
