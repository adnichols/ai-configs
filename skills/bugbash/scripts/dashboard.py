#!/usr/bin/env python3
"""Render a bugbash ledger as an HTML dashboard and publish it to Ava.

    dashboard.py <bugbash-dir> [--space SPACE_ID] [--title TITLE] [--force]
    dashboard.py <bugbash-dir> --render-only

The ledger (<bugbash-dir>/ledger.md) is the only input. The first run
registers an Ava HTML document and records `Dashboard:` and `Ava space:` in
the ledger header; later runs replace the document in place, then read the
source back and compare it. Publish state is kept in <bugbash-dir>/dashboard.json.

The layout comes from ../references/dashboard-template.html, or from
<bugbash-dir>/dashboard-template.html when the operator's feedback has been
applied to this bugbash's copy first.

Exit codes: 0 published (or unchanged), 2 bad input or ledger, 3 Ava
unavailable, unauthenticated, or the publish failed. On 3 the driver must tell
the operator; the dashboard is never skipped silently.
"""
import argparse, hashlib, html, json, re, shutil, subprocess, sys
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


def inline(s):
    s = html.escape(s)
    s = re.sub(r"(https?://[^\s<)`]+)", r'<a href="\1" target="_blank" rel="noopener">\1</a>', s)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", s)


def render(text, title, template, updated):
    mode = header(text, "Mode") or "UNKNOWN"
    rows = issue_rows(text)
    waiting = bullets(section(text, "Waiting on you"))
    decisions = bullets(section(text, "Operator decisions"))[:DECISIONS_SHOWN]

    counts = {}
    for r in rows:
        label = group_of(r.get("state", ""))[1]
        counts[label] = counts.get(label, 0) + 1
    chips = "".join(
        f'<span class="chip {c}">{html.escape(l)} · {counts.get(l, 0)}</span>' for c, l, _ in STATE_GROUPS)
    needs = "".join(f"<li>{inline(w)}</li>" for w in waiting) or '<li class="empty">Nothing needs you right now.</li>'

    trs = []
    for r in rows:
        cls, _ = group_of(r.get("state", ""))
        pr = r.get("pr", "")
        trs.append(
            f'<tr class="{cls}"><td class="id">{html.escape(r.get("id", ""))}</td>'
            f'<td><div class="t">{inline(r.get("title", ""))}</div>'
            f'<div class="sub">{html.escape(r.get("type", ""))} · {html.escape(r.get("repo", ""))}</div></td>'
            f'<td><span class="pill {cls}">{html.escape(r.get("state", ""))}</span></td>'
            f'<td>{inline(r.get("waiting on", ""))}</td>'
            f'<td class="pr">{pr_cell(pr)}</td></tr>')

    meta = f"Mode: {html.escape(mode)} · updated {html.escape(updated)} · comment on this document to talk to the driver"
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


def publish(source, unstamped_digest, title, space, state_path, ledger_path, ledger, force):
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    plan_id = state.get("plan_id")
    if not plan_id:  # state file lost but the ledger still names the document: adopt it
        m = re.search(r"/d/([0-9a-f-]{36})", header(ledger, "Dashboard"))
        plan_id = m.group(1) if m else None

    if plan_id and not force and state.get("digest") == unstamped_digest and state.get("plan_id") == plan_id:
        print(f"unchanged: {state.get('web_url')}")
        return
    sha = digest(source)[:16]
    if not plan_id:
        r = ava("document", "register", "--space", space, "--idempotency-key", f"bugbash-dashboard-{sha}",
                data={"title": title, "source": source, "source_format": "html"})
        plan_id, web_url = pick(r, "plan_id", "document_id"), r.get("web_url") or r.get("document_url")
        state = {"space_id": space, "plan_id": plan_id, "web_url": web_url, "revision_id": revision_of(r)}
        state_path.write_text(json.dumps(state, indent=2) + "\n")
    else:
        cur = ava("document", "status", plan_id, "--space", space)
        rev = revision_of(cur)
        r = ava("document", "edit", plan_id, "--space", space, "--idempotency-key", f"bugbash-dashboard-{rev}-{sha}",
                "--expected-revision", rev, data={"source": source, "title": title})
        state.update(space_id=space, plan_id=plan_id, revision_id=revision_of(r))
        state.setdefault("web_url", None)
    got = ava("document", "plan-source", plan_id, "--space", space)
    if got.get("source") != source:
        raise Fail(3, "published source does not match the rendered dashboard; not marking it published")
    if not state.get("web_url"):
        state["web_url"] = ava("document", "get", plan_id, "--space", space).get("web_url")
    state["digest"] = unstamped_digest
    state_path.write_text(json.dumps(state, indent=2) + "\n")

    updated = set_header(set_header(ledger, "Ava space", space), "Dashboard", state["web_url"])
    if updated != ledger:
        ledger_path.write_text(updated)
    print(f"published: {state['web_url']} (revision {state['revision_id']})")


def main():
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    ap.add_argument("bugbash_dir", type=Path)
    ap.add_argument("--space", help="Ava Space ID (spc_...); default: dashboard.json, then the ledger `Ava space:` line")
    ap.add_argument("--title", help="document title; default: ledger heading + ' — status'")
    ap.add_argument("--force", action="store_true", help="republish even when the ledger content is unchanged")
    ap.add_argument("--render-only", action="store_true", help="write dashboard.html and skip Ava")
    args = ap.parse_args()

    root = args.bugbash_dir.expanduser().resolve()
    ledger_path = root / "ledger.md"
    if not ledger_path.is_file():
        raise Fail(2, f"{ledger_path} not found")
    ledger = ledger_path.read_text()
    heading = re.search(r"^# (.+)$", ledger, re.M)
    title = args.title or (f"{heading.group(1).strip()} — status" if heading else f"{root.name} — status")
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
        raise Fail(2, f"this bugbash's dashboard already lives in {state['space_id']}; "
                      "remove dashboard.json to publish a new one elsewhere")
    ledger_space = header(ledger, "Ava space")
    space = args.space or state.get("space_id") or (ledger_space if ledger_space.startswith("spc_") else "")
    if not space:
        raise Fail(2, "no Ava Space: pass --space spc_... (ask the operator which Space; `ava space list --json`)")
    publish(source, digest(unstamped), title, space, state_path, ledger_path, ledger, args.force)


if __name__ == "__main__":
    try:
        main()
    except Fail as e:
        print(f"dashboard.py: {e}", file=sys.stderr)
        sys.exit(e.code)
