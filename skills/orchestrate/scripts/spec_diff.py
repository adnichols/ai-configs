#!/usr/bin/env python3
"""Render a proposed spec or ADR change as one Ava HTML diff page, publish it, and check what landed.

  spec_diff.py REPO --base REF --path spec [--path ...] --title TITLE
               [--head REF] [--summary-file FILE] [--reply TEXT] [--out DIR]
               [--publish --tracker-dir DIR]
  spec_diff.py REPO --check DIR/manifest.json [--head REF]

Input is git content, never retyped text: the base is the merge base of --base and the head, and the head is
either --head REF or, when absent, the uncommitted edits in the working tree (untracked files included).
Every changed file under the --path pathspecs becomes a section with a change list, side-by-side
Before | After hunks, and the file rendered in place with additions green and removals red.

--out DIR receives page.html, manifest.json (sha256 of each proposed file) and, when published, ava.json
(the document id, so a rerun updates the same document). --check compares the files now at the head with
that manifest, so a worker can prove it landed byte-identical text. Needs python3 stdlib and pandoc.
"""
from __future__ import annotations

import argparse, bisect, difflib, hashlib, html, json, os, posixpath, re, shutil, subprocess, sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dashboard
from dashboard import Fail

CONTEXT = 4
FULL_LINES = 300  # files at most this long render whole; longer files render only the sections around a change
SIMILAR = 0.4  # line pairs less alike than this get row colors without word highlights

esc = html.escape


# ---- git input ------------------------------------------------------------

def git(root: Path, *args: str, ok=(0,)) -> subprocess.CompletedProcess:
    p = subprocess.run(["git", "-C", str(root), *args], capture_output=True)
    if p.returncode not in ok:
        raise Fail(2, f"`git {' '.join(args[:2])}` failed in {root}: {p.stderr.decode(errors='replace').strip()}")
    return p


def commit(root: Path, ref: str) -> str:
    return git(root, "rev-parse", "--verify", f"{ref}^{{commit}}").stdout.decode().strip()


def read_head(root: Path, head: str | None, path: str) -> bytes | None:
    """The file's bytes at `head`, or in the working tree when head is None. None when absent."""
    if head is None:
        p = root / path
        return p.read_bytes() if p.is_file() else None
    p = git(root, "cat-file", "blob", f"{head}:{path}", ok=(0, 128))
    return p.stdout if p.returncode == 0 else None


@dataclass(frozen=True)
class Source:
    root: Path
    base_ref: str
    base: str  # merge base commit
    head_ref: str | None
    head: str | None  # commit, or None for the working tree

    def old(self, path: str) -> bytes | None:
        return read_head(self.root, self.base, path)

    def new(self, path: str) -> bytes | None:
        return read_head(self.root, self.head, path)


def resolve(root: Path, base_ref: str, head_ref: str | None) -> Source:
    head = commit(root, head_ref) if head_ref else None
    p = git(root, "merge-base", commit(root, base_ref), head or commit(root, "HEAD"), ok=(0, 1))
    if p.returncode:
        raise Fail(2, f"{base_ref} and {head_ref or 'HEAD'} share no history")
    return Source(root, base_ref, p.stdout.decode().strip(), head_ref, head)


@dataclass(frozen=True)
class Change:
    path: str
    old: bytes | None
    new: bytes | None

    @property
    def status(self) -> str:
        return "added" if self.old is None else "deleted" if self.new is None else "modified"


def changes(src: Source, pathspecs: list[str]) -> list[Change]:
    """Changed files under the pathspecs. Renames count as a delete plus an add. A path whose bytes match
    on both sides (a mode change, a touched file) is not a change."""
    diff = ["diff", "--name-status", "-z", "--no-renames", src.base, *([src.head] if src.head else []), "--", *pathspecs]
    tokens = [os.fsdecode(t) for t in git(src.root, *diff).stdout.split(b"\0")]
    paths = {tokens[i + 1] for i in range(0, len(tokens) - 1, 2)}
    if src.head is None:
        untracked = git(src.root, "ls-files", "--others", "--exclude-standard", "-z", "--", *pathspecs).stdout
        paths |= {os.fsdecode(t) for t in untracked.split(b"\0") if t}
    found = [Change(p, src.old(p), src.new(p)) for p in sorted(paths)]
    return [c for c in found if c.old != c.new]


def decode(data: bytes | None) -> str | None:
    """Text of one side ('' when absent), or None for binary content."""
    if data is None:
        return ""
    if b"\0" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def sha256(data: bytes | None) -> str | None:
    return hashlib.sha256(data).hexdigest() if data is not None else None


def repo_url_of(root: Path) -> str | None:
    p = git(root, "remote", "get-url", "origin", ok=(0, 2, 128))
    m = re.match(r"(?:git@github\.com:|https?://github\.com/|ssh://git@github\.com/)([^/]+/[^/]+?)(?:\.git)?/?$",
                 p.stdout.decode().strip()) if p.returncode == 0 else None
    return f"https://github.com/{m.group(1)}" if m else None


# ---- markdown to HTML -----------------------------------------------------

REFDEF = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*\S+")
SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:", re.I)
A_TAG = re.compile(r'<a\s+href="([^"]*)"([^>]*)>(.*?)</a>', re.S)
IMG_TAG = re.compile(r'<img\b[^>]*>')
ALT = re.compile(r'alt="([^"]*)"')


class Links:
    """Rewrites a spec file's links so Ava keeps them: a repo-relative link becomes a GitHub URL at a commit
    that contains its target, and anything else Ava would remove becomes plain text."""

    def __init__(self, src: Source, repo_url: str | None):
        self.src, self.repo_url, self._kinds = src, repo_url, {}

    def target(self, path: str) -> str | None:
        for sha in (self.src.head, self.src.base):
            if sha is None:
                continue
            if (sha, path) not in self._kinds:
                p = git(self.src.root, "cat-file", "-t", f"{sha}:{path}", ok=(0, 128))
                self._kinds[sha, path] = p.stdout.decode().strip() if p.returncode == 0 else None
            if self._kinds[sha, path] in ("blob", "tree"):
                return f"{self.repo_url}/{self._kinds[sha, path]}/{sha}/{quote(path)}"
        return None

    def href(self, raw: str, file_path: str) -> str | None:
        url = html.unescape(raw)
        if SCHEME.match(url):
            return url if url.split(":", 1)[0].lower() in ("http", "https", "mailto") else None
        if not self.repo_url:
            return None
        target, _, frag = url.partition("#")
        target = unquote(target.split("?", 1)[0])
        if not target:  # an anchor inside the same file
            target = file_path
        elif target.startswith("/"):
            target = posixpath.normpath(target.lstrip("/"))
        else:
            target = posixpath.normpath(posixpath.join(posixpath.dirname(file_path), target))
        if target.startswith("..") or target == ".":
            return None
        found = self.target(target)
        return f"{found}#{frag}" if found and frag else found

    def rewrite(self, fragment: str, file_path: str) -> str:
        def anchor(m):
            url = self.href(m.group(1), file_path)
            return f'<a href="{esc(url)}"{m.group(2)}>{m.group(3)}</a>' if url else m.group(3)

        def image(m):
            alt = ALT.search(m.group(0))
            return f"<em>[image: {alt.group(1) if alt and alt.group(1) else 'no description'}]</em>"
        return IMG_TAG.sub(image, A_TAG.sub(anchor, fragment))


def pandoc(markdown: str) -> str:
    p = subprocess.run(["pandoc", "-f", "gfm", "-t", "html", "--wrap=none"], input=markdown, capture_output=True, text=True)
    if p.returncode:
        raise Fail(3, f"pandoc failed: {p.stderr.strip()}")
    return p.stdout


def md(markdown: str, refdefs: str = "", links: Links | None = None, path: str = "") -> str:
    """One Markdown chunk as Ava-safe HTML. `refdefs` keeps [text][ref] links working when a chunk is
    rendered apart from its definitions."""
    lines = [l for l in markdown.splitlines() if l.strip()]
    if lines and all(REFDEF.match(l) for l in lines):
        return f"<pre>{esc(markdown)}</pre>"
    out = pandoc(markdown + ("\n\n" + refdefs if refdefs else ""))
    out = re.sub(r'\sid="[^"]*"', "", out)  # pandoc repeats heading ids when several files share one page
    out = out.replace("<table>", '<div style="overflow-x:auto"><table>').replace("</table>", "</table></div>")
    return links.rewrite(out, path) if links else out


# ---- block segmentation ---------------------------------------------------

FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
HEADING = re.compile(r"^#{1,6}\s")
ITEM = re.compile(r"^(\s{0,3})(?:[-*+]|\d{1,9}[.)])\s+")


@dataclass(frozen=True)
class Unit:
    """The smallest block the in-place view adds or removes: a heading, a top-level list item, or any
    other run of lines (a paragraph, a table, a whole fenced block). A `table-diff` unit is a table
    holding the rows of both sides, with `marks` naming each body row eq, add or rm."""
    text: str
    kind: str  # heading | item | block | table-diff
    marks: tuple[str, ...] = ()


def units(text: str) -> list[Unit]:
    lines = text.splitlines()
    out: list[Unit] = []
    cur: list[str] = []
    kind, indent, fence = "block", 0, ""

    def flush():
        nonlocal cur
        while cur and not cur[-1].strip():
            cur.pop()
        if cur:
            out.append(Unit("\n".join(cur), kind))
        cur = []

    start = 0
    if lines and lines[0].strip() == "---":  # YAML front matter reads as code, not as a rule and a heading
        end = next((i for i in range(1, min(len(lines), 60)) if lines[i].strip() == "---"), None)
        if end:
            out.append(Unit("```yaml\n" + "\n".join(lines[1:end]) + "\n```", "block"))
            start = end + 1
    for line in lines[start:]:
        if fence:
            cur.append(line)
            m = FENCE.match(line)
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and line.strip() == m.group(1):
                fence = ""
                if kind == "block":
                    flush()
            continue
        m = FENCE.match(line)
        if m:
            if kind != "item" or not cur:
                flush()
                kind = "block"
            cur.append(line)
            fence = m.group(1)
            continue
        if not line.strip():
            if kind == "block":
                flush()
            else:
                cur.append(line)
            continue
        item = ITEM.match(line)
        if HEADING.match(line):
            flush()
            kind = "heading"
            cur = [line]
            flush()
            kind = "block"
        elif item and (kind != "item" or len(item.group(1)) <= indent):
            flush()
            kind, indent, cur = "item", len(item.group(1)), [line]
        elif cur and (kind == "block" or line[:1] in " \t" or cur[-1].strip()):
            cur.append(line)  # continuation of the paragraph, table or item
        else:
            flush()
            kind, cur = "block", [line]
    flush()
    return out


def joined(group: Sequence[Unit]) -> str:
    parts = [group[0].text]
    for prev, unit in zip(group, group[1:]):
        parts.append(("\n" if prev.kind == unit.kind == "item" else "\n\n") + unit.text)
    return "".join(parts)


TABLE_DELIM = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$")


def table_parts(unit: Unit) -> tuple[list[str], list[str]] | None:
    """(header and delimiter lines, body rows) when the unit is a pipe table."""
    lines = unit.text.splitlines()
    if len(lines) >= 2 and TABLE_DELIM.match(lines[1]) and all(l.lstrip().startswith("|") for l in lines):
        return lines[:2], lines[2:]
    return None


def table_diff(a: Unit, b: Unit) -> Unit | None:
    """One table showing a replaced pair's rows in order, when both have the same header, so an edit to
    one row reads as one row and not as the whole table removed and added."""
    ta, tb = table_parts(a), table_parts(b)
    if not ta or not tb or ta[0] != tb[0]:
        return None
    rows, marks = [], []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, ta[1], tb[1], autojunk=False).get_opcodes():
        if op == "equal":
            rows += tb[1][j1:j2]
            marks += ["eq"] * (j2 - j1)
        else:
            rows += ta[1][i1:i2] + tb[1][j1:j2]
            marks += ["rm"] * (i2 - i1) + ["add"] * (j2 - j1)
    return Unit("\n".join(ta[0] + rows), "table-diff", tuple(marks))


def segments(old: str, new: str) -> list[tuple[str, list[Unit]]]:
    ua, ub = units(old), units(new)
    sm = difflib.SequenceMatcher(None, [u.text for u in ua], [u.text for u in ub], autojunk=False)
    out: list[tuple[str, list[Unit]]] = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            out.append(("eq", ub[j1:j2]))
            continue
        merged = table_diff(ua[i1], ub[j1]) if (i2 - i1, j2 - j1) == (1, 1) else None
        if merged:
            out.append(("mod", [merged]))
            continue
        if i2 > i1:
            out.append(("rm", ua[i1:i2]))
        if j2 > j1:
            out.append(("add", ub[j1:j2]))
    return out


@dataclass(frozen=True)
class Piece:
    kind: str  # eq | add | rm | mod | skip
    units: tuple[Unit, ...] = ()
    skipped: int = 0  # unchanged blocks a skip stands for


def pieces(segs: list[tuple[str, list[Unit]]], whole: bool) -> list[Piece]:
    """Segments with unchanged parts far from any change replaced by a skip. A change keeps its whole
    enclosing section: from the nearest heading before it to the next heading after it."""
    flat = [(kind, u) for kind, group in segs for u in group]
    keep = [True] * len(flat)
    if not whole:
        keep = [False] * len(flat)

        def heading(i):
            return flat[i][0] != "rm" and flat[i][1].kind == "heading"
        i = 0
        while i < len(flat):
            if flat[i][0] == "eq":
                i += 1
                continue
            j = i
            while j < len(flat) and flat[j][0] != "eq":
                j += 1
            start = next((s for s in range(i, -1, -1) if heading(s)), 0)
            end = next((e for e in range(j, len(flat)) if heading(e)), len(flat))
            keep[start:end] = [True] * (end - start)
            i = j
    out: list[Piece] = []
    i = 0
    while i < len(flat):
        j = i
        if keep[i]:
            while j < len(flat) and keep[j] and flat[j][0] == flat[i][0] and flat[i][0] != "mod":
                j += 1
            out.append(Piece(flat[i][0], tuple(u for _, u in flat[i:max(j, i + 1)])))
            j = max(j, i + 1)
        else:
            while j < len(flat) and not keep[j]:
                j += 1
            out.append(Piece("skip", skipped=j - i))
        i = j
    return out


def table_html(unit: Unit, refdefs: str, links: Links | None, path: str) -> str:
    """A table holding rows of both sides, each body row tagged with its diff status (eq, add or rm)."""
    marks = iter(unit.marks)
    head, sep, body = md(unit.text, refdefs, links, path).partition("<tbody>")
    return head + sep + re.sub(r'<tr(?: class="[^"]*")?>', lambda _: f'<tr class="row-{next(marks, "eq")}">', body)


def in_place(old: str, new: str, whole: bool, links: Links | None, path: str) -> str:
    refdefs = "\n".join(l for l in (old + "\n" + new).splitlines() if REFDEF.match(l))
    out = []
    for p in pieces(segments(old, new), whole):
        if p.kind == "skip":
            out.append(f'<p class="skip">… {p.skipped} unchanged block{"s" if p.skipped != 1 else ""} omitted …</p>')
        elif p.kind == "mod":
            out.append(f'<div class="mod"><div class="tag">Changed table</div>{table_html(p.units[0], refdefs, links, path)}</div>')
        else:
            body = md(joined(p.units), refdefs, links, path)
            if p.kind == "eq":
                out.append(f'<div class="eq">{body}</div>')
            else:
                label = "Added" if p.kind == "add" else "Removed"
                out.append(f'<div class="{p.kind}"><div class="tag">{label}</div>{body}</div>')
    return "".join(out)


# ---- side-by-side hunks ---------------------------------------------------

def headings(lines: list[str]) -> tuple[list[int], list[str]]:
    """Line index and title of every heading outside fenced blocks."""
    at, titles, fence = [], [], ""
    for i, line in enumerate(lines):
        m = FENCE.match(line)
        if fence:
            fence = "" if m and m.group(1)[0] == fence[0] else fence
        elif m:
            fence = m.group(1)
        elif HEADING.match(line):
            at.append(i)
            titles.append(line.lstrip("# ").strip())
    return at, titles


def words(a: str, b: str) -> tuple[str, str]:
    """Word-level highlight of one changed line pair; unrelated lines get none."""
    ta, tb = re.split(r"(\s+)", a), re.split(r"(\s+)", b)
    sm = difflib.SequenceMatcher(None, ta, tb, autojunk=False)
    if sm.ratio() < SIMILAR:
        return esc(a), esc(b)
    sa, sb = [], []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        x, y = esc("".join(ta[i1:i2])), esc("".join(tb[j1:j2]))
        if op == "equal":
            sa.append(x)
            sb.append(y)
        else:
            if x:
                sa.append(f"<del>{x}</del>")
            if y:
                sb.append(f"<ins>{y}</ins>")
    return "".join(sa), "".join(sb)


def hunks(old: str, new: str) -> list[tuple[str, str]]:
    """(enclosing section title, table rows) for each group of changes, with CONTEXT lines around it."""
    al, bl = old.splitlines(), new.splitlines()
    heads_a, titles_a = headings(al)
    heads_b, titles_b = headings(bl)
    out = []
    for group in difflib.SequenceMatcher(None, al, bl, autojunk=False).get_grouped_opcodes(CONTEXT):
        op, i1, _, j1, j2 = next(g for g in group if g[0] != "equal")
        heads, titles, at = (heads_b, titles_b, j1) if j2 > j1 else (heads_a, titles_a, i1)
        n = bisect.bisect_right(heads, at) - 1
        rows = []
        for op, i1, i2, j1, j2 in group:
            if op == "equal":
                for k in range(i2 - i1):
                    t = esc(al[i1 + k])
                    rows.append(f'<tr class="ctx"><td class="n">{i1 + k + 1}</td><td>{t}</td><td class="n">{j1 + k + 1}</td><td>{t}</td></tr>')
                continue
            for k in range(max(i2 - i1, j2 - j1)):
                left = al[i1 + k] if i1 + k < i2 else None
                right = bl[j1 + k] if j1 + k < j2 else None
                if left is not None and right is not None:
                    lh, rh = words(left, right)
                else:
                    lh = esc(left) if left is not None else ""
                    rh = esc(right) if right is not None else ""
                rows.append(
                    f'<tr><td class="n">{i1 + k + 1 if left is not None else ""}</td>'
                    f'<td class="{"rm" if left is not None else "gap"}">{lh}</td>'
                    f'<td class="n">{j1 + k + 1 if right is not None else ""}</td>'
                    f'<td class="{"add" if right is not None else "gap"}">{rh}</td></tr>')
        out.append((titles[n] if n >= 0 else "", "".join(rows)))
    return out


# ---- page -----------------------------------------------------------------

CSS = """<style>
.dv del{background:light-dark(#ffd7d5,#5a1e1e);color:inherit;text-decoration:line-through}
.dv ins{background:light-dark(#c8f0d0,#1d4a2a);color:inherit;text-decoration:none}
.dv .eq{color:var(--ava-muted,light-dark(#57606a,#9aa4b0))}
.dv .add,.dv .rm{border-left:4px solid;padding:4px 12px;margin:8px 0;border-radius:var(--ava-radius,6px)}
.dv .add{border-color:var(--ava-ok,#1a7f37);background:light-dark(#e9f7ec,#13281a)}
.dv .rm{border-color:var(--ava-danger,#cf222e);background:light-dark(#fdecec,#2a1414);text-decoration:line-through}
.dv .tag{font:600 12px var(--ava-font-sans,sans-serif);text-transform:uppercase;letter-spacing:.04em;color:var(--ava-muted,light-dark(#57606a,#9aa4b0));text-decoration:none}
.dv .skip{text-align:center;color:var(--ava-muted,light-dark(#57606a,#9aa4b0));font-style:italic}
.dv .card{background:var(--ava-surface,light-dark(#fff,#1b1b1b));border:1px solid var(--ava-rule,light-dark(#d0d7de,#3a3f45));border-radius:var(--ava-radius,6px);padding:12px 16px;margin:12px 0}
.dv table.sbs{border-collapse:collapse;width:100%;min-width:520px;font:13px/1.45 var(--ava-font-mono,monospace)}
.dv table.sbs td{vertical-align:top;padding:2px 6px;white-space:pre-wrap;word-break:break-word;border:0}
.dv table.sbs th{font:600 12px var(--ava-font-sans,sans-serif);text-align:left;padding:4px 6px}
.dv table.sbs td.n{color:var(--ava-muted,light-dark(#57606a,#9aa4b0));text-align:right;user-select:none;width:3em}
.dv table.sbs td.rm{background:light-dark(#fdecec,#2a1414)}
.dv table.sbs td.add{background:light-dark(#e9f7ec,#13281a)}
.dv table.sbs tr.ctx td{color:var(--ava-muted,light-dark(#57606a,#9aa4b0))}
.dv .mod{margin:8px 0}
.dv pre{overflow-x:auto;max-width:100%}
.dv code{overflow-wrap:anywhere}
.dv pre code{overflow-wrap:normal}
.dv tr.row-add td{background:light-dark(#e9f7ec,#13281a)}
.dv tr.row-rm td{background:light-dark(#fdecec,#2a1414);text-decoration:line-through}
.dv .stat-add{color:var(--ava-ok,#1a7f37);font-weight:600}
.dv .stat-rm{color:var(--ava-danger,#cf222e);font-weight:600}
</style>"""


@dataclass(frozen=True)
class Options:
    title: str
    summary: str  # Markdown, may be empty
    reply: str  # plain text, may be empty
    full_lines: int = FULL_LINES


def is_markdown(path: str) -> bool:
    return path.lower().endswith((".md", ".markdown"))


def file_link(links: Links, path: str) -> str:
    """A GitHub link to the file where it exists, else the bare path."""
    url = links.target(path) if links.repo_url else None
    return f'<a href="{esc(url)}">{esc(path)}</a>' if url else esc(path)


def section(src: Source, links: Links, ch: Change, n: int, opts: Options) -> tuple[str, str]:
    """(change-list item, body) for one changed file."""
    fid = f"f{n}"
    name = f"<code>{esc(ch.path)}</code>"
    title = f'<h2 id="{fid}">{file_link(links, ch.path)}</h2>'
    old, new = decode(ch.old), decode(ch.new)
    if old is None or new is None:
        return (f'<li><a href="#{fid}">{name}</a> binary file {ch.status}</li>',
                f"{title}<p>This is a binary file ({ch.status}). Its content is not shown.</p>")
    ops = [o for o in difflib.SequenceMatcher(None, old.splitlines(), new.splitlines(), autojunk=False).get_opcodes()
           if o[0] != "equal"]
    if not ops:  # the bytes differ but every line matches: only line endings or the final newline changed
        return (f'<li><a href="#{fid}">{name}</a> line endings only</li>',
                f"{title}<p>Only line endings or the final newline differ. No line changed.</p>")
    stat = (f'<span class="stat-add">+{sum(o[4] - o[3] for o in ops)}</span> '
            f'<span class="stat-rm">−{sum(o[2] - o[1] for o in ops)}</span>')
    markdown = is_markdown(ch.path)
    total = max(len(old.splitlines()), len(new.splitlines()))
    whole = total <= opts.full_lines
    if not markdown:
        note = " This is not a Markdown file, so only the before and after lines are shown."
    elif ch.status != "modified":
        note = f" The whole file is {ch.status}."
    else:
        note = "" if whole else f" The file is {total} lines, so only the sections around a change are shown."
    parts = [title, f"<p>{stat} lines.{note}</p>"]
    sub = []
    if not markdown or ch.status == "modified":
        for k, (sect, rows) in enumerate(hunks(old, new), 1):
            cid = f"{fid}-c{k}"
            where = f": § {esc(sect)}" if sect else ""
            sub.append(f'<li><a href="#{cid}">Change {k}{where}</a></li>')
            parts.append(f'<h3 id="{cid}">Change {k}{where}, before and after</h3><div style="overflow-x:auto">'
                         f'<table class="sbs"><tr><th></th><th>Before ({esc(src.base_ref)})</th><th></th><th>After (proposed)</th></tr>'
                         f"{rows}</table></div>")
    if markdown:
        label = "Read the whole file with the change in place" if whole else "Read the changed sections with the change in place"
        parts.append(f'<details open><summary><strong>{label}</strong></summary>'
                     f'<div class="card">{in_place(old, new, whole, links, ch.path)}</div></details>')
    item = f'<li><a href="#{fid}">{name}</a> {stat}' + (f"<ul>{''.join(sub)}</ul>" if sub else "") + "</li>"
    return item, "".join(parts)


def page(src: Source, repo_url: str | None, found: list[Change], opts: Options) -> str:
    links = Links(src, repo_url)
    def named(ref: str, sha: str) -> str:
        return f"<code>{sha[:9]}</code>" if sha.startswith(ref) else f"<code>{esc(ref)}</code> (<code>{sha[:9]}</code>)"
    proposal = named(src.head_ref, src.head) if src.head and src.head_ref \
        else "the uncommitted edits in the working tree. Nothing is committed yet"
    intro = (f"<p>Proposed change to {len(found)} file{'s' if len(found) != 1 else ''}, shown as a diff against "
             f"{named(src.base_ref, src.base)}. The proposal is {proposal}."
             + (f" {esc(opts.reply)}" if opts.reply else "") + "</p>")
    summary = f'<div class="card">{md(opts.summary)}</div>' if opts.summary else ""
    sections = [section(src, links, ch, n, opts) for n, ch in enumerate(found)]
    prints = "".join(f"<li><code>{esc(c.path)}</code> {'removed' if c.new is None else 'sha256 ' + sha256(c.new)[:12]}</li>"
                     for c in found)
    footer = ("<h2>Approval covers exactly this diff</h2><p>The text that lands must be byte-identical to the proposed files. "
              "Check it with <code>spec_diff.py REPO --check manifest.json</code>.</p>"
              f"<details><summary>Fingerprints of the proposed files</summary><ul>{prints}</ul></details>")
    return (f'<main class="dv" style="max-width:1100px;margin:0 auto">{CSS}<h1>{esc(opts.title)}</h1>{intro}{summary}'
            f'<h2>Changes</h2><ul>{"".join(i for i, _ in sections)}</ul>{"".join(b for _, b in sections)}{footer}</main>')


def manifest(src: Source, found: list[Change]) -> dict:
    return {"base": src.base, "head": src.head, "files": {c.path: sha256(c.new) for c in found}}


# ---- publish --------------------------------------------------------------

def dashboard_of(tracker_dir: Path) -> tuple[str, str]:
    """(space id, dashboard document id) recorded by dashboard.py, which every page this tracker makes hangs under."""
    f = tracker_dir / "dashboard.json"
    state = json.loads(f.read_text()) if f.exists() else {}
    if not state.get("plan_id") or not state.get("space_id"):
        raise Fail(2, f"{f} has no dashboard plan_id; run dashboard.py {tracker_dir} first so this page can be filed under it")
    return state["space_id"], state["plan_id"]


def publish(source: str, title: str, space: str, parent: str, state_path: Path) -> dict:
    """Register the page under the dashboard document, or edit the one recorded in state_path, then verify the
    stored source and the parent. A create that ignored parent_id is moved and checked again."""
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    sha = dashboard.digest(source)[:16]
    plan_id = state.get("plan_id")
    if not plan_id:
        r = dashboard.ava("document", "register", "--space", space, "--idempotency-key", f"spec-diff-register-{sha}",
                          data={"title": title, "source": source, "source_format": "html", "parent_id": parent})
        plan_id = dashboard.pick(r, "plan_id", "document_id")
        state = {"space_id": space, "plan_id": plan_id, "web_url": r.get("web_url") or r.get("document_url"),
                 "digest": sha}
        state_path.write_text(json.dumps(state, indent=2) + "\n")
    elif state.get("digest") != sha:
        rev = dashboard.revision_of(dashboard.ava("document", "status", plan_id, "--space", space))
        dashboard.ava("document", "edit", plan_id, "--space", space, "--idempotency-key", f"spec-diff-{rev}-{sha}",
                      "--expected-revision", rev, data={"source": source, "title": title})
    if dashboard.ava("document", "plan-source", plan_id, "--space", space).get("source") != source:
        raise Fail(3, "published source does not match the rendered page; not reporting it as published")
    dashboard.place(space, plan_id, parent)
    if not state.get("web_url"):
        state["web_url"] = dashboard.ava("document", "get", plan_id, "--space", space).get("web_url")
    state["digest"] = sha
    state_path.write_text(json.dumps(state, indent=2) + "\n")
    state["warnings"] = dashboard.ava("document", "render", plan_id, "--space", space).get("warnings") or []
    return state


# ---- command line ---------------------------------------------------------

def check(manifest_path: Path, root: Path, head_ref: str | None) -> int:
    want = json.loads(manifest_path.read_text())
    head = commit(root, head_ref) if head_ref else None
    bad = [p for p, digest in want["files"].items() if sha256(read_head(root, head, p)) != digest]
    for p in bad:
        print(f"differs from the approved page: {p}", file=sys.stderr)
    print("byte-identical to the approved page" if not bad else f"{len(bad)} file(s) differ")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    ap.add_argument("repo", type=Path, help="checkout or worktree holding the proposal")
    ap.add_argument("--base", help="ref the proposal is measured against, usually the branch's base branch")
    ap.add_argument("--head", help="commit holding the proposal; default: uncommitted edits in the working tree")
    ap.add_argument("--path", action="append", default=[], help="pathspec of spec files to show, repeatable (e.g. spec, docs/adr)")
    ap.add_argument("--title")
    ap.add_argument("--summary-file", type=Path, help="Markdown: what changes and why, in plain terms")
    ap.add_argument("--reply", default="", help="plain sentence telling the operator how to answer on the dashboard")
    ap.add_argument("--repo-url", help="https://github.com/OWNER/REPO for links; default: derived from origin")
    ap.add_argument("--full-lines", type=int, default=FULL_LINES, help="files up to this many lines render whole")
    ap.add_argument("--out", type=Path, help="output directory; default: <tracker-dir>/spec-diffs/<title slug>")
    ap.add_argument("--publish", action="store_true", help="publish or update the page under the tracker's dashboard document")
    ap.add_argument("--tracker-dir", "--bugbash-dir", dest="tracker_dir", type=Path,
                    help="holds dashboard.json; the page is filed under its dashboard document")
    ap.add_argument("--check", type=Path, metavar="MANIFEST", help="compare the files at the head with manifest.json and exit")
    args = ap.parse_args()
    root = args.repo.expanduser().resolve()

    if args.check:
        return check(args.check, root, args.head)
    if not (args.base and args.path and args.title):
        raise Fail(2, "--base, --path and --title are required")
    if args.publish and not args.tracker_dir:
        raise Fail(2, "--publish needs --tracker-dir so the page is filed under that tracker's dashboard document")
    space, parent = dashboard_of(args.tracker_dir.expanduser()) if args.publish else ("", "")
    if not shutil.which("pandoc"):
        raise Fail(3, "pandoc is not on PATH. Install it (for example `brew install pandoc`); it renders the Markdown.")
    out = args.out
    if not out:
        if not args.tracker_dir:
            raise Fail(2, "pass --out DIR, or --tracker-dir to use <tracker-dir>/spec-diffs/<title slug>")
        out = args.tracker_dir.expanduser() / "spec-diffs" / (re.sub(r"[^a-z0-9]+", "-", args.title.lower()).strip("-") or "proposal")
    src = resolve(root, args.base, args.head)
    found = changes(src, args.path)
    if not found:
        raise Fail(2, f"no changed files under {', '.join(args.path)} between {src.base[:9]} and {args.head or 'the working tree'}")
    repo_url = (args.repo_url or repo_url_of(root) or "").rstrip("/") or None
    if not repo_url:
        print("spec_diff.py: no GitHub origin and no --repo-url, so links inside the specs are shown as plain text", file=sys.stderr)
    summary = args.summary_file.read_text() if args.summary_file else ""
    source = page(src, repo_url, found, Options(args.title, summary, args.reply, args.full_lines))
    out.mkdir(parents=True, exist_ok=True)
    (out / "page.html").write_text(source)
    (out / "manifest.json").write_text(json.dumps(manifest(src, found), indent=2) + "\n")
    print(f"{len(found)} changed file(s): {out / 'page.html'}")
    if not args.publish:
        return 0

    dashboard.preflight()
    state = publish(source, args.title, space, parent, out / "ava.json")
    verified = next((d.get("parent_id") for d in dashboard.tree(space) if d["document_id"] == state["plan_id"]), None)
    print(f"published: {state['web_url']}")
    print(f"parent_id: {verified} (dashboard {parent})")
    for w in state["warnings"]:
        print(f"ava warning {w.get('code')}: {w.get('message')}", file=sys.stderr)
    print(f"ava warnings: {len(state['warnings'])}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Fail as e:
        print(f"spec_diff.py: {e}", file=sys.stderr)
        sys.exit(e.code)
