#!/usr/bin/env python3
"""Check that every Aaron ruling in journal/aaron-decisions.md has been processed.

Usage: ruling-check.py [--journal PATH] [--checkout ~/code/ccore2] [--ref origin/main]

Each journal entry is one line: `- <date> | <question> | <Aaron's words> | <disposition>`.
Dispositions (closed set):
  encoded: <target>[; <target>]   the standing part lives in a rule, skill, check, or spec
  transient: <reference>          a one-off approval that has been carried out
  pending: <owner>                not encoded yet; this script fails until it is
A target is `<path>[ § <heading>][ "<phrase>"]`; the phrase must appear in the file, so a
pointer cannot pass on a heading alone. A ccore2 path is checked at --ref, so a ruling
counts as encoded only once its encoding is merged. `bot:<path>` is resolved under the
bot library (for example `bot:skills/pr-merge-gates/SKILL.md § Authority`).

Exit 0 = every entry encoded or transient. Exit 1 = pending or invalid entries, listed.
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

LIBRARY = Path(__file__).resolve().parents[2]
BOT_ROOT = LIBRARY.parent


def read_target(path, checkout, ref):
    if path.startswith("bot:"):
        file = LIBRARY / path[len("bot:"):]
        return file.read_text() if file.is_file() else None
    shown = subprocess.run(["git", "-C", checkout, "show", f"{ref}:{path}"], capture_output=True, text=True)
    return shown.stdout if shown.returncode == 0 else None


def target_problem(target, checkout, ref):
    location, phrase = re.match(r'^(.*?)(?:\s+"([^"]+)")?$', target.strip()).groups()
    path, _, heading = (part.strip() for part in location.partition("§"))
    text = read_target(path, checkout, ref)
    if text is None:
        return f"{path} not found" + ("" if path.startswith("bot:") else f" at {ref}")
    if heading and not re.search(rf"^#+\s+{re.escape(heading)}\s*$", text, re.MULTILINE):
        return f"{path} has no heading '{heading}'"
    if phrase and " ".join(phrase.split()) not in " ".join(text.split()):
        return f"{path} does not contain \"{phrase}\""
    return None


def entry_problem(disposition, checkout, ref):
    kind, _, rest = disposition.partition(":")
    kind, rest = kind.strip(), rest.strip()
    if kind == "transient" and rest:
        return None
    if kind == "pending":
        return f"pending ({rest or 'no owner'}): encode it as a rule, skill, check, or spec change"
    if kind == "encoded" and rest:
        problems = [p for p in (target_problem(t, checkout, ref) for t in rest.split(";")) if p]
        return "; ".join(problems) or None
    return f"disposition '{disposition}' is not encoded:, transient:, or pending:"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--journal", default=str(BOT_ROOT / "journal" / "aaron-decisions.md"))
    ap.add_argument("--checkout", default=os.path.expanduser("~/code/ccore2"))
    ap.add_argument("--ref", default="origin/main")
    args = ap.parse_args()

    failures = 0
    entries = 0
    for number, line in enumerate(Path(args.journal).read_text().splitlines(), start=1):
        if not re.match(r"- \d{4}-\d{2}-\d{2} \|", line):
            continue
        entries += 1
        fields = line[2:].split(" | ")
        if len(fields) < 4:
            problem = "expected `- <date> | <question> | <words> | <disposition>`"
        else:
            problem = entry_problem(fields[-1], args.checkout, args.ref)
        if problem:
            failures += 1
            print(f"journal:{number}: {fields[0]} {fields[1] if len(fields) > 1 else ''}: {problem}")
    print(f"{entries} ruling(s), {failures} not processed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
