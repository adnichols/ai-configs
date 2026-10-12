"""Ledger parsing shared by dashboard.py and reconcile.py."""
import re


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
        cells = [c.strip().replace(r"\|", "|") for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
        if cols is None:
            cols = [c.lower() for c in cells]
        elif not set("".join(cells)) <= set("-: "):
            out.append(dict(zip(cols, cells)))
    return out


def natural(s):
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", s)]
