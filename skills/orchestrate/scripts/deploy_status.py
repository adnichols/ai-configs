#!/usr/bin/env python3
"""Fill the ledger Status table's Merged and Deployed columns.

usage: deploy_status.py <tracker-dir> --repo <checkout>
       (--from-history-doc <space>:<document-id> | --target <name>=<commit> ... | --from-rollout) [--dry-run]

Merged: every done row whose PR column holds GitHub PR URLs and whose Merged cell is empty gets
the latest merge time and that merge commit from `gh pr view`, as `2026-10-08 19:42Z 562a1a890`.

Deployed: with --from-history-doc, --target or --from-rollout, every merged row whose PRs belong to the
--repo checkout's repository, and is not already deployed everywhere, gets how many targets run a commit
that contains its merge commit, plus the check time.
--from-history-doc is the default way to fill Deployed. It fetches the operator-maintained 'Production
deploy history' Ava document (`ava document source`; no Cloudflare access needed) and derives the targets
from it: the hubs of the newest `rollout --all` entry plus any hub named by a newer entry, each at the
commit of the newest entry naming it. It raises on a document it cannot parse.
--from-rollout reads the targets by running the read-only `pnpm rollout` overview (production hubs only,
no hub argument) in --repo: one target per production hub, the platform Worker's source commit. It needs
Cloudflare credentials that agents do not have, so use --from-history-doc instead. It fails loudly on
output it cannot parse.
--dry-run prints the targets and the cells it would write, and leaves ledger.md untouched.
This script never deploys anything.

Missing Merged and Deployed columns are added. Republish the dashboard afterwards.
"""
import argparse, html, json, re, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dashboard import MERGED_AT, Fail, ava, group_of  # noqa: E402

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


def parse_rollout(text):
    """[(hub, commit)] for the platform Worker of each hub in `pnpm rollout` console.table output.
    The overview lists a platform and a `-collab` Worker per hub; the platform one is the target.
    A commit of `unknown` is kept (deployed_cell marks it). Raises ValueError on anything else."""
    header, targets = None, {}
    for line in text.splitlines():
        if not line.startswith("│"):
            continue
        row = [c.strip().strip("'") for c in line.strip().strip("│").split("│")]
        if header is None:
            if "Hub" in row and "Worker" in row and "Source commit" in row:
                header = {name: i for i, name in enumerate(row)}
            continue
        hub, worker, commit = (row[header[k]] for k in ("Hub", "Worker", "Source commit"))
        if worker.endswith("-collab"):
            targets.setdefault(hub, None)
            continue
        if not commit:
            raise ValueError(f"hub {hub} has no source commit")
        if targets.get(hub):
            raise ValueError(f"hub {hub} lists more than one platform Worker row")
        targets[hub] = commit
    if header is None or not targets:
        raise ValueError("no hub rows found")
    bare = [h for h, c in targets.items() if c is None]
    if bare:
        raise ValueError(f"hub without a platform Worker row: {', '.join(bare)}")
    return list(targets.items())


HISTORY_HUBS = re.compile(r"<strong>Hubs:</strong>\s*([^<]*)")
HISTORY_COMMIT = re.compile(r"<strong>Commit:</strong>\s*(?:<a\b[^>]*>\s*<code>([^<]+)</code>\s*</a>|([^<\s]+))")
HISTORY_SMALL = re.compile(r"<small>(.*?)</small>", re.S)


def parse_deploy_history(doc_html):
    """[(hub, commit)] from the 'Production deploy history' document (entries newest first, one
    `<h2>` each). Targets are the hubs of the newest `rollout --all` entry plus every hub named by a
    newer entry, each at the commit of the newest entry naming it. The literal hub `none` (a failed
    deploy) is ignored; a commit of `unknown` is kept. Raises ValueError otherwise."""
    sections = re.split(r"(?=<h2\b)", doc_html)[1:]
    if not sections:
        raise ValueError("no deploy entries found")
    entries = []
    for sec in sections:
        title = re.match(r"<h2\b[^>]*>(.*?)</h2>", sec, re.S).group(1).strip()
        hubs, commit, small = HISTORY_HUBS.search(sec), HISTORY_COMMIT.search(sec), HISTORY_SMALL.search(sec)
        parts = html.unescape(small.group(1)).split(" · ") if small else []
        command = parts[1].strip() if len(parts) > 1 else ""
        entries.append((title, hubs, commit, command))
        if command == "rollout --all":
            break
    else:
        raise ValueError("no `rollout --all` entry found")
    commits, order = {}, []
    for title, hubs, commit, command in entries:
        if hubs is None:
            raise ValueError(f"deploy entry {title!r} has no Hubs line")
        if commit is None:
            raise ValueError(f"deploy entry {title!r} has no Commit line")
        for hub in (h.strip() for h in hubs.group(1).split(",")):
            if hub and hub != "none" and hub not in commits:
                commits[hub] = (commit.group(1) or commit.group(2)).strip()
                order.append(hub)
    if not commits:
        raise ValueError("the newest `rollout --all` entry names no hubs")
    rollout_hubs = [h.strip() for h in entries[-1][1].group(1).split(",")]
    order.sort(key=lambda h: (h not in rollout_hubs, rollout_hubs.index(h) if h in rollout_hubs else 0))
    return [(h, commits[h]) for h in order]


def history_doc_targets(spec):
    """Production deploy targets from the Ava deploy-history document `<space>:<document-id>`."""
    space, _, doc = spec.partition(":")
    if not space or not doc:
        raise SystemExit("--from-history-doc takes <space>:<document-id>")
    try:
        source = ava("document", "source", doc, "--space", space).get("source")
    except Fail as e:
        raise SystemExit(str(e))
    if not isinstance(source, str):
        raise SystemExit(f"ava document source {doc} returned no `source` string")
    try:
        return parse_deploy_history(source)
    except ValueError as e:
        raise SystemExit(f"deploy history document {doc} in {space}: {e}")


def rollout_targets(repo):
    """Production deploy targets from the read-only `pnpm rollout` overview in `repo`."""
    proc = run("pnpm", "rollout", cwd=repo)
    out = proc.stdout + proc.stderr
    try:
        return parse_rollout(proc.stdout), out
    except ValueError as e:
        raise SystemExit(f"pnpm rollout in {repo} (exit {proc.returncode}): {e}\n--- raw output ---\n{out}")


def usable_targets(targets, repo, raw=""):
    """Exit with a clear message, before anything is written, when no target's commit exists in
    the checkout's history (every commit `unknown`, or none fetched). `raw` is the rollout output;
    its first `failed:` line names the cause (e.g. a Cloudflare auth error)."""
    for _, commit in targets:
        if commit != "unknown" and run("git", "cat-file", "-e", f"{commit}^{{commit}}", cwd=repo).returncode == 0:
            return
    cause = next((l.strip() for l in raw.splitlines() if "failed:" in l), "no cause in output")
    raise SystemExit(
        "no deploy target has a commit found in the checkout's history; nothing written.\n"
        f"targets: {', '.join(f'{n}={c}' for n, c in targets)}\ncause: {cause}")


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
    ap.add_argument("--from-history-doc", metavar="SPACE:DOCUMENT_ID",
                    help="read targets from the Production deploy history Ava document (default source)")
    ap.add_argument("--from-rollout", action="store_true",
                    help="read targets from `pnpm rollout` in --repo (needs Cloudflare credentials)")
    ap.add_argument("--dry-run", action="store_true", help="print targets and cells; do not write ledger.md")
    args = ap.parse_args()
    if sum(map(bool, (args.target, args.from_rollout, args.from_history_doc))) > 1:
        ap.error("--target, --from-rollout and --from-history-doc are mutually exclusive")
    targets = [tuple(t.split("=", 1)) for t in args.target]
    if any(len(t) != 2 or not t[1] for t in targets):
        ap.error("--target takes NAME=COMMIT")
    raw = ""
    if args.from_history_doc:
        targets = history_doc_targets(args.from_history_doc)
    if args.from_rollout:
        targets, raw = rollout_targets(args.repo)
    if targets:
        print("targets: " + ", ".join(f"{n}={c}" for n, c in targets))
    remote = run("git", "remote", "get-url", "origin", cwd=args.repo).stdout.strip()
    repo_name = re.sub(r"\.git$", "", remote.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1])
    if targets and run("git", "fetch", "-q", "origin", cwd=args.repo).returncode:
        raise SystemExit(f"git fetch failed in {args.repo}")
    if targets:
        usable_targets(targets, args.repo, raw)
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
            cell = deployed_cell(row["merged"].split()[-1], targets, args.repo, checked)
            c[cols.index("deployed")] = cell
            if args.dry_run:
                print(f"{c[0]}: Deployed -> {cell}")
            deployed_n += 1
        lines[i] = joined(c)
        i += 1
    if not args.dry_run:
        path.write_text("\n".join(lines))
    print(f"merged filled: {merged_n}; deployed checked: {deployed_n}" + (" (dry run, ledger.md not written)" if args.dry_run else ""))


if __name__ == "__main__":
    main()
