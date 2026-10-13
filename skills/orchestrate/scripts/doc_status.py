#!/usr/bin/env python3
"""Show a one-row build status at the top of every design document the tracker builds from.

usage: doc_status.py <tracker-dir> [--dry-run] [--doc <uuid>] [--space spc_...]

Mapping: an item file (`items/WI-NN-*.md`) lists the documents it builds from on one line,
`Source docs: <url>[, <url>...]`. Only that line counts; other document links in the file are ignored.

Each mapped document gets one wrapper element, `<div data-orchestrate-status="<tracker>">`, as the first
element of its HTML body (first child of a leading `<main>`). It holds a 'Build status' label, the update
time, a link to the tracker dashboard, and one segment per item: WI id, short title, stage, PR links
(draft marked), and the merge date once merged. A rerun replaces the wrapper in place, touches nothing
else in the body, and writes nothing when the row is unchanged apart from its update time.

Stages come from the ledger row: Planned, Building, In review, Merged, Deployed, Partly deployed,
Blocked, Closed. Draft state of an open PR comes from `gh pr view`. Run it after `deploy_status.py`
fills the Merged and Deployed columns, and from the twice-daily reconcile. Never deploys anything.
"""
import argparse, hashlib, html, json, re, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dashboard import Fail, ava, group_of, preflight  # noqa: E402
from ledger import header, issue_rows, natural  # noqa: E402

SOURCE_DOCS = re.compile(r"^Source docs:[ \t]*(.*)$", re.M)
DOC_URL = re.compile(r"https?://[^\s,]+/d/([0-9a-fA-F-]{36})")
PR_URL = re.compile(r"https://github\.com/[^/\s]+/[^/\s]+/pull/(\d+)")
MERGED_SET = re.compile(r"\b[0-9a-f]{7,40}\b|\d{4}-\d{2}-\d{2}")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
UPDATED = re.compile(r"Updated \d{4}-\d{2}-\d{2} \d{2}:\d{2}Z")
MAIN_OPEN = re.compile(r"\A\s*<main\b[^>]*>")

PLANNED, BUILDING, IN_REVIEW, MERGED = "Planned", "Building", "In review", "Merged"
DEPLOYED, PARTLY, BLOCKED, CLOSED = "Deployed", "Partly deployed", "Blocked", "Closed"
COLORS = {  # Ava theme variables with fallbacks
    PLANNED: "var(--ava-muted, #57606a)",
    BUILDING: "var(--ava-warn, #9a6700)",
    IN_REVIEW: "var(--ava-accent, #0969da)",
    MERGED: "var(--ava-accent, #0969da)",
    DEPLOYED: "var(--ava-ok, #1a7f37)",
    PARTLY: "var(--ava-warn, #9a6700)",
    BLOCKED: "var(--ava-danger, #cf222e)",
    CLOSED: "var(--ava-muted, #57606a)",
}


# ---- pure parts -----------------------------------------------------------

def source_docs(item_text):
    """Document ids on the item's `Source docs:` line, in order, without repeats."""
    ids = []
    for line in SOURCE_DOCS.findall(item_text):
        for doc in DOC_URL.findall(line):
            if doc.lower() not in ids:
                ids.append(doc.lower())
    return ids


def doc_items(tracker):
    """{doc id: [item id, ...]} from every items/WI-*.md file's `Source docs:` line."""
    out = {}
    for path in sorted((Path(tracker) / "items").glob("WI-*.md")):
        item = re.match(r"WI-\d+", path.name)
        if not item:
            continue
        for doc in source_docs(path.read_text()):
            out.setdefault(doc, []).append(item.group())
    return {doc: sorted(ids, key=natural) for doc, ids in out.items()}


def pr_urls(cell):
    return [m.group() for m in PR_URL.finditer(cell)]


def is_merged(row):
    return bool(MERGED_SET.search(row.get("merged", "")))


def needs_pr_lookup(row):
    """Only an unmerged row in an active state needs the PR's draft/open state to pick its stage."""
    return bool(pr_urls(row.get("pr", ""))) and not is_merged(row) and group_of(row.get("state", ""))[0] in {"needs", "land", "work"}


def stage(row, prs=()):
    """Stage word for a ledger row. prs: [{"isDraft": bool, "state": "OPEN"|"MERGED"|"CLOSED"}] for its PRs."""
    deployed = row.get("deployed", "").lower()
    if deployed.startswith("yes, all"):
        return DEPLOYED
    if deployed.startswith("partly"):
        return PARTLY
    state = row.get("state", "").upper()
    if is_merged(row) or state == "MERGED":
        return MERGED
    cls, _ = group_of(state)
    if cls == "blocked":
        return BLOCKED
    if cls == "done":
        return CLOSED
    if cls == "queued":
        return PLANNED
    ready = any(p.get("state") == "OPEN" and not p.get("isDraft") for p in prs)
    if cls == "land" or ready:
        return IN_REVIEW
    return BUILDING


def short_title(title, limit=48):
    title = re.sub(r"\s*\([^)]*\)", "", title.split(" → ")[0]).strip()
    if len(title) <= limit:
        return title
    return title[:limit].rsplit(" ", 1)[0].rstrip(",;:( ") + "…"


def segment(item, row, prs):
    word = stage(row, prs)
    by_url = {p["url"]: p for p in prs if "url" in p}
    parts = [f'<strong>{html.escape(item)}</strong> {html.escape(short_title(row.get("title", "")), quote=False)}:',
             f'<strong style="color:{COLORS[word]}">{word}</strong>']
    for url in pr_urls(row.get("pr", "")):
        p = by_url.get(url, {})
        draft = " (draft)" if p.get("isDraft") and p.get("state", "OPEN") == "OPEN" else ""
        parts.append(f'<a href="{html.escape(url)}">#{PR_URL.match(url).group(1)}</a>{draft}')
    date = DATE.search(row.get("merged", ""))
    if date and word in {MERGED, DEPLOYED, PARTLY}:
        parts.append(f"merged {date.group()}")
    return f'<span style="display:inline-block;margin-right:14px">{" ".join(parts)}</span>'


def render_row(key, dashboard_url, now, segments):
    stamp = now.strftime("%Y-%m-%d %H:%MZ")
    label = (f'<strong>Build status</strong> <span style="color:var(--ava-muted, #57606a)">Updated {stamp} · '
             f'<a href="{html.escape(dashboard_url)}">tracker</a></span> ')
    style = ("margin:0 0 12px;padding:6px 10px;font-size:13px;line-height:1.7;"
             "border:1px solid var(--ava-rule, #d0d7de);border-radius:var(--ava-radius, 6px);"
             "background:var(--ava-surface, #f6f8fa)")
    return f'<div data-orchestrate-status="{html.escape(key)}" style="{style}">{label}{"".join(segments)}</div>'


def wrapper_re(key):
    return re.compile(rf'<div data-orchestrate-status="{re.escape(html.escape(key))}"[^>]*>.*?</div>', re.S)


def splice(body, key, row):
    """Body with its status wrapper for `key` replaced by `row`, or inserted first when absent.
    Everything outside the wrapper is returned byte for byte."""
    pattern = wrapper_re(key)
    if pattern.search(body):
        return pattern.sub(lambda _: row, body, count=1)
    m = MAIN_OPEN.match(body)
    at = m.end() if m else 0
    return body[:at] + row + body[at:]


def unchanged(body, key, row):
    """True when the body already holds this row, ignoring only the update time."""
    m = wrapper_re(key).search(body)
    return bool(m) and UPDATED.sub("Updated", m.group()) == UPDATED.sub("Updated", row)


# ---- I/O ------------------------------------------------------------------

def pr_state(url):
    p = subprocess.run(["gh", "pr", "view", url, "--json", "isDraft,state"], capture_output=True, text=True)
    if p.returncode:
        raise Fail(3, f"gh pr view {url} failed: {p.stderr.strip()}")
    return {"url": url, **json.loads(p.stdout)}


def build_row(items, rows, key, dashboard_url, now, cache):
    segments = []
    for item in items:
        row = rows.get(item)
        if row is None:
            raise Fail(3, f"{item} has a `Source docs:` line but no ledger row")
        prs = []
        if needs_pr_lookup(row):
            for url in pr_urls(row["pr"]):
                if url not in cache:
                    cache[url] = pr_state(url)
                prs.append(cache[url])
        segments.append(segment(item, row, prs))
    return render_row(key, dashboard_url, now, segments)


def process(doc, items, space, rows, key, dashboard_url, now, cache, dry_run):
    meta = ava("document", "get", doc, "--space", space)
    fmt = meta.get("properties", {}).get("source_format")
    if fmt != "html":
        return f"{doc} skipped: source_format is {fmt!r}, not html"
    src = ava("document", "source", doc, "--space", space)
    body, revision = src["source"], src["revision_id"]
    row = build_row(items, rows, key, dashboard_url, now, cache)
    if unchanged(body, key, row):
        return f"{doc} unchanged ({', '.join(items)})"
    new = splice(body, key, row)
    verb = "updated" if wrapper_re(key).search(body) else "inserted"
    if dry_run:
        return f"{doc} would be {verb} (dry run) ({', '.join(items)})"
    idem = "orchestrate-doc-status-" + hashlib.sha256(f"{doc}\0{revision}\0{new}".encode()).hexdigest()[:32]
    resp = ava("document", "edit", doc, "--space", space, "--idempotency-key", idem,
               "--expected-revision", revision, data={"source": new})
    back = ava("document", "source", doc, "--space", space)["source"]
    if back != new:
        raise Fail(3, f"{doc} readback differs from what was written; check the document")
    warnings = resp.get("warnings") or []
    return f"{doc} {verb} ({', '.join(items)})" + (f"; {len(warnings)} sanitizer warning(s)" if warnings else "")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("tracker")
    ap.add_argument("--dry-run", action="store_true", help="report what would change; write nothing")
    ap.add_argument("--doc", help="only this document id")
    ap.add_argument("--space", help="Ava space; default: the ledger's `Ava space:` line")
    a = ap.parse_args()
    tracker = Path(a.tracker).expanduser()
    text = (tracker / "ledger.md").read_text()
    space = a.space or header(text, "Ava space")
    dashboard_url = header(text, "Dashboard")
    key = header(text, "Tracker") or tracker.name
    if not space or not dashboard_url:
        raise SystemExit("ledger lacks an `Ava space:` or `Dashboard:` line")
    rows = {r["id"]: r for r in issue_rows(text)}
    docs = doc_items(tracker)
    if a.doc:
        docs = {d: i for d, i in docs.items() if d == a.doc.lower()}
        if not docs:
            raise SystemExit(f"no item lists {a.doc} on a `Source docs:` line")
    if not docs:
        print("no item has a `Source docs:` line")
        return
    preflight()
    now, cache, failed = datetime.now(timezone.utc), {}, False
    for doc, items in docs.items():
        try:
            print(process(doc, items, space, rows, key, dashboard_url, now, cache, a.dry_run))
        except Fail as e:
            failed = True
            print(f"{doc} FAILED: {e}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
