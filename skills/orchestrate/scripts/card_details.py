#!/usr/bin/env python3
"""Publish a Needs-you card's details (Markdown) as a subdocument of the tracker's dashboard and print its URL.

The card on the dashboard stays short; evidence, quoted spec text, limits and option detail live here.
Rerunning with the same --out edits the same document. Needs python3 stdlib and pandoc.

  card_details.py <tracker-dir> <details.md> --title "BB-144 details" --out <tracker-dir>/card-details/bb-144.json
"""
from __future__ import annotations

import argparse, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import spec_diff  # noqa: E402
from dashboard import Fail  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    ap.add_argument("tracker_dir", type=Path)
    ap.add_argument("details", type=Path)
    ap.add_argument("--title", required=True)
    ap.add_argument("--out", type=Path, required=True, help="state file recording the document; reuse it to edit")
    a = ap.parse_args()
    space, parent = spec_diff.dashboard_of(a.tracker_dir.expanduser())
    source = spec_diff.md(a.details.read_text())
    a.out.parent.mkdir(parents=True, exist_ok=True)
    state = spec_diff.publish(source, a.title, space, parent, a.out)
    print(state["web_url"])
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Fail as e:
        print(e, file=sys.stderr)
        sys.exit(e.code)
