#!/usr/bin/env python3
"""Render an orchestrator tracker's ledger as an HTML dashboard and publish it to Ava.

    dashboard.py <tracker-dir> [--space SPACE_ID] [--title TITLE] [--force]
    dashboard.py <tracker-dir> --render-only

The ledger (<tracker-dir>/ledger.md) is the only input. The first run
registers an Ava HTML document and records `Dashboard:` and `Ava space:` in
the ledger header; later runs replace the document in place, then read the
source back and compare it. Publish state is kept in <tracker-dir>/dashboard.json.

The layout comes from ../references/dashboard-template.html, or from
<tracker-dir>/dashboard-template.html when the operator's feedback has been
applied to this tracker's copy first.

Exit codes: 0 published (or unchanged), 2 bad input or ledger, 3 Ava
unavailable, unauthenticated, or the publish failed. On 3 the driver must tell
the operator; the dashboard is never skipped silently.
"""
import argparse, hashlib, html, json, re, shutil, subprocess, sys, uuid
from datetime import datetime
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "references" / "dashboard-template.html"
LOCAL_TEMPLATE = "dashboard-template.html"

STATE_GROUPS = [  # (css class, label, state prefixes)
    ("needs", "Needs you", ("PROTOTYPE_REVIEW", "NEEDS_OPERATOR", "VALIDATED", "NOT_REPRODUCED", "EXPECTED_BEHAVIOR")),
    ("work", "Worker active", ("READY", "QUEUED", "HANDED_OFF", "BUILDING", "REWORK", "IN_PROGRESS", "VALIDATING", "FAILED_VALIDATION", "CLOSING")),
    ("blocked", "Blocked", ("BLOCKED",)),
    ("done", "Done", ("DONE", "MERGED", "CLEANED", "CLOSED")),
]
DECISIONS_SHOWN = 8
DEFAULT_SPACE = "spc_16ef6d824e21402b9a42560b13436034"  # Development: the operator's standard Space for work trackers
FOLDER_PATH = ("Coding Work",)  # each tracker is a document directly inside this root folder
ARCHIVE = "Archive"  # a CONCLUDED tracker's dashboard moves to Archive/<folder path>


class Fail(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code = code


# ---- ledger parsing -------------------------------------------------------

def section(text, name):
    m = re.search(rf"^## {re.escape(name)}\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    return m.group(1).strip() if m else ""


def header(text, key):
    m = re.search(rf"^{re.escape(key)}:[ \t]*(.*)$", text, re.M)
    return m.group(1).strip() if m else ""


def set_header(text, key, value):
    line = f"{key}: {value}"
    if re.search(rf"^{re.escape(key)}:", text, re.M):
        return re.sub(rf"^{re.escape(key)}:.*$", lambda _: line, text, count=1, flags=re.M)
    m = re.search(r"^## ", text, re.M)
    at = m.start() if m else len(text)
    return text[:at].rstrip("\n") + f"\n{line}\n\n" + text[at:]


def issue_rows(text):
    """Status table rows keyed by lowercased header cell, so column order is free."""
    cols, out = None, []
    for line in section(text, "Status").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cols is None:
            cols = [c.lower() for c in cells]
        elif not set("".join(cells)) <= set("-: "):
            out.append(dict(zip(cols, cells)))
    return out


def bullets(body):
    return [l[2:].strip() for l in body.splitlines() if l.startswith("- ")]


def group_of(state):
    for cls, label, prefixes in STATE_GROUPS:
        if state.upper().startswith(prefixes):
            return cls, label
    return "work", "Worker active"


# ---- rendering ------------------------------------------------------------

def pr_cell(pr):
    """GitHub PR URLs become `repo#N` so the column stays narrow; the href keeps the full URL."""
    m = re.fullmatch(r"https://github\.com/[^/\s]+/([^/\s]+)/pull/(\d+)", pr)
    if m:
        return f'<a href="{html.escape(pr)}" target="_blank" rel="noopener">{html.escape(m.group(1))}#{m.group(2)}</a>'
    return inline(pr) if pr not in ("—", "") else "—"


ASK_FIELDS = (("Problem", "Problem"), ("Fix", "Proposed change"), ("Decide", "Your call"), ("Links", "Look at"))


CARD_RULE = ("each ask is one `### <ID>: <the problem> → <the change>` card with `Problem:` (what is wrong, in plain "
             "technical-founder language) and `Decide:` (exactly what the operator must do or choose); no bold, no bullet asks. "
             "See references/ledger-template.md")


def asks(body):
    """`## Waiting on you` items as (title, {field: [lines]}).

    Item: `### <ID>: <the problem or gap> → <what we're changing>` followed by `Problem:`, `Fix:`, `Decide:`
    and `Links:` fields; a field may continue on following lines, including `- ` or `1.` lists.
    `Broken:` (the bugbash name for `Problem:`) is read as `Problem:`.
    Anything else is a ledger error (exit 2): the card format is the only accepted format.
    """
    if not body:
        return []
    head, *blocks = re.split(r"^### ", body, flags=re.M)
    if head.strip():
        raise Fail(2, f"## Waiting on you has content outside a `###` card ({head.strip().splitlines()[0][:80]!r}); {CARD_RULE}")
    out = []
    for block in blocks:
        title, _, rest = block.partition("\n")
        title = title.strip()
        fields, key = {}, None
        for line in rest.splitlines():
            m = re.match(r"^(Problem|Broken|Fix|Decide|Links):\s*(.*)$", line)
            if m:
                key = "Problem" if m.group(1) == "Broken" else m.group(1)
                fields[key] = [m.group(2)] if m.group(2) else []
            elif line.strip() and key is None:
                raise Fail(2, f"Waiting on you card {title!r} has text before any field ({line.strip()[:80]!r}); {CARD_RULE}")
            elif line.strip():
                fields[key].append(line.strip())
        if "**" in title or any("**" in l for ls in fields.values() for l in ls):
            raise Fail(2, f"Waiting on you card {title!r} uses bold (`**`); {CARD_RULE}")
        for need in ("Problem", "Decide"):
            if not fields.get(need):
                raise Fail(2, f"Waiting on you card {title!r} has no `{need}:` text; {CARD_RULE}")
        out.append((title, fields))
    return out


def ask_card(title, fields):
    parts = [f'<article class="ask"><h3>{inline(title)}</h3>']
    for key, label in ASK_FIELDS:
        lines = fields.get(key)
        if not lines:
            continue
        cls = " decide" if key == "Decide" else ""
        if len(lines) > 1 or re.match(r"(- |\d+\. )", lines[0]):
            items = "".join(f"<li>{inline(re.sub(r'^(- |[0-9]+[.] )', '', l))}</li>" for l in lines)
            tag = "ol" if lines[0][:1].isdigit() else "ul"
            body = f"<{tag}>{items}</{tag}>"
        else:
            body = f"<p>{inline(lines[0])}</p>"
        parts.append(f'<div class="f{cls}"><div class="k">{label}</div>{body}</div>')
    parts.append("</article>")
    return "".join(parts)


def inline(s):
    s = html.escape(s)
    s = re.sub(r"(https?://[^\s<)`]+)", r'<a href="\1" target="_blank" rel="noopener">\1</a>', s)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", s)


def render(text, title, template, updated):
    mode = header(text, "Mode") or "UNKNOWN"
    rows = issue_rows(text)
    waiting = asks(section(text, "Waiting on you"))
    decisions = bullets(section(text, "Operator decisions"))[:DECISIONS_SHOWN]

    counts = {}
    for r in rows:
        label = group_of(r.get("state", ""))[1]
        counts[label] = counts.get(label, 0) + 1
    chips = "".join(
        f'<span class="chip {c}">{html.escape(l)} · {counts.get(l, 0)}</span>' for c, l, _ in STATE_GROUPS)
    needs = "".join(ask_card(t, f) for t, f in waiting) or '<p class="empty">Nothing needs you right now.</p>'

    trs = []
    for r in rows:
        cls, _ = group_of(r.get("state", ""))
        pr = r.get("pr", "")
        trs.append(
            f'<tr class="{cls}"><td class="id">{html.escape(r.get("id", ""))}</td>'
            f'<td><div class="t">{inline(r.get("title", ""))}</div>'
            f'<div class="sub">{html.escape(r.get("kind") or r.get("type", ""))} · {html.escape(r.get("repo", ""))}</div></td>'
            f'<td><span class="pill {cls}">{html.escape(r.get("state", ""))}</span></td>'
            f'<td>{inline(r.get("waiting on", ""))}</td>'
            f'<td class="pr">{pr_cell(pr)}</td></tr>')

    meta = (f"Mode: {html.escape(mode)} · updated {html.escape(updated)} · a listener watches comments on this "
            "document and acknowledges each one in its thread within about 30 seconds")
    out = template
    for key, val in {
        "title": html.escape(title), "meta": meta, "chips": chips, "needs": needs,
        "issues": "".join(trs), "decisions": "".join(f"<li>{inline(d)}</li>" for d in decisions),
    }.items():
        out = out.replace("{{" + key + "}}", val)
    return out


# ---- Ava ------------------------------------------------------------------

def ava(*args, data=None):
    cmd = ["ava", *args, "--json"]
    if data is not None:
        cmd += ["--data", json.dumps(data)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise Fail(3, f"`ava {' '.join(args[:3])}` failed (exit {p.returncode}): {(p.stderr or p.stdout).strip()}")
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError:
        raise Fail(3, f"`ava {' '.join(args[:3])}` returned non-JSON output: {p.stdout[:200]!r}")


def preflight():
    if not shutil.which("ava"):
        raise Fail(3, "the `ava` CLI is not on PATH. Report this to the operator: install it with the "
                      "bootstrap command from Ava Settings. The dashboard was NOT published.")
    p = subprocess.run(["ava", "auth", "status", "--json"], capture_output=True, text=True)
    try:
        status = json.loads(p.stdout)
    except json.JSONDecodeError:
        status = {}
    if p.returncode != 0 or not status.get("registered"):
        raise Fail(3, "the `ava` CLI is not authenticated "
                      f"({(p.stderr or p.stdout).strip()[:200] or 'not registered'}). Report this to the operator: "
                      "run `ava auth renew` or enroll with an enrollment code. The dashboard was NOT published.")


def pick(resp, *keys):
    for k in keys:
        if isinstance(resp.get(k), str):
            return resp[k]
    raise Fail(3, f"Ava response lacks any of {keys}; keys were {sorted(resp)}")


def revision_of(resp):
    return pick(resp, "revision_id", "head_revision_id", "latest_revision_id")


def digest(s):
    return hashlib.sha256(s.encode()).hexdigest()


def tree(space):
    return ava("document", "tree", "--space", space)["documents"]


def folders(docs, title, parent):
    return [d for d in docs if d.get("kind") == "folder" and d.get("title") == title and d.get("parent_id") == parent]


def title_path(docs, doc_id):
    by_id = {d["document_id"]: d for d in docs}
    titles, doc = [], by_id.get(doc_id)
    while doc:
        titles.append(doc.get("title"))
        doc = by_id.get(doc.get("parent_id"))
    return tuple(reversed(titles))


def resolve_folder(space, path, known_id):
    """Id of the folder at `path` (titles from the Space root), creating missing levels.

    A known id wins when it is still a folder at exactly that title path. Otherwise each level is
    found by title under the previous one, and only absent levels are created.
    """
    docs = tree(space)
    if known_id and any(d["document_id"] == known_id and d.get("kind") == "folder" for d in docs) \
            and title_path(docs, known_id) == path:
        return known_id
    chain, parent = [], None
    for title in path:
        found = folders(docs, title, parent)
        if not found:
            break
        parent = found[0]["document_id"]
        chain.append(parent)
    if len(chain) == len(path):
        return parent
    parent = chain[-1] if chain else None
    for title in path[len(chain):]:
        body = {"space_id": space, "title": title, "kind": "folder"}
        if parent:
            body["parent_id"] = parent
        parent = pick(ava("document", "create", "--space", space, "--idempotency-key", uuid.uuid4().hex, data=body),
                      "document_id", "resource_id")
    return parent


def place(space, plan_id, folder):
    def parent_of():
        return next((d.get("parent_id") for d in tree(space) if d["document_id"] == plan_id), None)
    if parent_of() == folder:
        return
    ava("document", "move", plan_id, "--space", space, "--idempotency-key", uuid.uuid4().hex,
        data={"parent_id": folder})
    if parent_of() != folder:
        raise Fail(3, f"dashboard {plan_id} is not under folder {folder} after the move")


def publish(source, unstamped_digest, title, space, state_path, ledger_path, ledger, force, folder_path):
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    plan_id = state.get("plan_id")
    if not plan_id:  # state file lost but the ledger still names the document: adopt it
        m = re.search(r"/d/([0-9a-f-]{36})", header(ledger, "Dashboard"))
        plan_id = m.group(1) if m else None

    if plan_id and not force and state.get("folder_id") and state.get("digest") == unstamped_digest \
            and state.get("plan_id") == plan_id:
        print(f"unchanged: {state.get('web_url')}")
        return
    sha = digest(source)[:16]
    published = None
    folder = resolve_folder(space, folder_path, state.get("folder_id") or header(ledger, "Dashboard folder"))
    if not plan_id:
        # A retry after a lost response must send the identical request, so the
        # first register's key and body are saved before the call.
        pending = state.get("pending_register") or {"key": uuid.uuid4().hex, "title": title, "source": source}
        state.update(space_id=space, pending_register=pending)
        state_path.write_text(json.dumps(state, indent=2) + "\n")
        r = ava("document", "register", "--space", space, "--idempotency-key", f"orchestrate-dashboard-{pending['key']}",
                data={"title": pending["title"], "source": pending["source"], "source_format": "html"})
        plan_id, web_url = pick(r, "plan_id", "document_id"), r.get("web_url") or r.get("document_url")
        state = {"space_id": space, "plan_id": plan_id, "web_url": web_url, "revision_id": revision_of(r)}
        state_path.write_text(json.dumps(state, indent=2) + "\n")
        published = pending["source"]
    if published != source:
        cur = ava("document", "status", plan_id, "--space", space)
        rev = revision_of(cur)
        r = ava("document", "edit", plan_id, "--space", space, "--idempotency-key", f"orchestrate-dashboard-{rev}-{sha}",
                "--expected-revision", rev, data={"source": source, "title": title})
        state.update(space_id=space, plan_id=plan_id, revision_id=revision_of(r))
        state.setdefault("web_url", None)
    got = ava("document", "plan-source", plan_id, "--space", space)
    if got.get("source") != source:
        raise Fail(3, "published source does not match the rendered dashboard; not marking it published")
    if not state.get("web_url"):
        state["web_url"] = ava("document", "get", plan_id, "--space", space).get("web_url")
    place(space, plan_id, folder)
    state["folder_id"] = folder
    state["digest"] = unstamped_digest
    state_path.write_text(json.dumps(state, indent=2) + "\n")

    updated = set_header(set_header(set_header(ledger, "Ava space", space), "Dashboard", state["web_url"]),
                         "Dashboard folder", folder)
    if updated != ledger:
        ledger_path.write_text(updated)
    print(f"published: {state['web_url']} (revision {state['revision_id']})")


def main():
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    ap.add_argument("tracker_dir", type=Path)
    ap.add_argument("--space", help=f"Ava Space ID (spc_...); default: dashboard.json, the ledger, then {DEFAULT_SPACE} (Development, the operator's standard)")
    ap.add_argument("--folder-path", default="/".join(FOLDER_PATH),
                    help=f"folder titles from the Space root, joined by '/'; default: Coding Work. "
                         f"When the ledger's Mode is CONCLUDED the dashboard goes to {ARCHIVE}/<folder path>")
    ap.add_argument("--title", help="document title; default: the ledger's `# ` heading (the tracker title)")
    ap.add_argument("--force", action="store_true", help="republish even when the ledger content is unchanged")
    ap.add_argument("--render-only", action="store_true", help="write dashboard.html and skip Ava")
    args = ap.parse_args()

    root = args.tracker_dir.expanduser().resolve()
    ledger_path = root / "ledger.md"
    if not ledger_path.is_file():
        raise Fail(2, f"{ledger_path} not found")
    ledger = ledger_path.read_text()
    heading = re.search(r"^# (.+)$", ledger, re.M)
    title = args.title or (heading.group(1).strip() if heading else root.name)
    template = (root / LOCAL_TEMPLATE if (root / LOCAL_TEMPLATE).is_file() else TEMPLATE).read_text()

    unstamped = render(ledger, title, template, "")
    source = render(ledger, title, template, datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z"))
    (root / "dashboard.html").write_text(source)
    if args.render_only:
        print(root / "dashboard.html")
        return

    preflight()
    state_path = root / "dashboard.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    if args.space and state.get("space_id") and args.space != state["space_id"]:
        raise Fail(2, f"this tracker's dashboard already lives in {state['space_id']}; "
                      "remove dashboard.json to publish a new one elsewhere")
    ledger_space = header(ledger, "Ava space")
    space = args.space or state.get("space_id") or (ledger_space if ledger_space.startswith("spc_") else DEFAULT_SPACE)
    folder_path = tuple(p.strip() for p in args.folder_path.split("/") if p.strip())
    if not folder_path:
        raise Fail(2, "--folder-path is empty")
    if header(ledger, "Mode").upper().startswith("CONCLUDED") and folder_path[0] != ARCHIVE:
        folder_path = (ARCHIVE,) + folder_path
    publish(source, digest(unstamped), title, space, state_path, ledger_path, ledger, args.force, folder_path)


if __name__ == "__main__":
    try:
        main()
    except Fail as e:
        print(f"dashboard.py: {e}", file=sys.stderr)
        sys.exit(e.code)
