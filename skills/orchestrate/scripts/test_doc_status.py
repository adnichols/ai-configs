#!/usr/bin/env python3

import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import doc_status as ds  # noqa: E402

KEY = "20261012-weekly"
DASH = "https://nodaste.hub.avalandra.com/d/667c13fb-6a28-4f05-a91d-8493cca00f1a"
T1 = datetime(2026, 10, 13, 6, 0, tzinfo=timezone.utc)
T2 = datetime(2026, 10, 13, 18, 0, tzinfo=timezone.utc)
PR = "https://github.com/Nodaste-Lab/ccore2/pull/940"
OPEN, DRAFT = {"url": PR, "state": "OPEN", "isDraft": False}, {"url": PR, "state": "OPEN", "isDraft": True}


def row(**kw):
    return {"id": "WI-1", "title": "Top bar", "state": "IN_PROGRESS", "pr": "—", "merged": "—", "deployed": "—", **kw}


def banner(*segments, now=T1):
    return ds.render_row(KEY, DASH, now, list(segments))


class Stage(unittest.TestCase):
    def test_deployed_forms(self):
        merged = "2026-10-12 14:14Z ad23dacdf"
        cases = [
            ("yes, all 2 (checked 10-13 06:00Z)", ds.DEPLOYED),
            ("partly, 1 of 2; not yet: prod (checked 10-13 06:00Z)", ds.PARTLY),
            ("no, 0 of 2 (checked 10-13 06:00Z)", ds.MERGED),
            ("—", ds.MERGED),
            ("requester notified 14:56Z", ds.MERGED),
        ]
        for deployed, want in cases:
            with self.subTest(deployed=deployed):
                self.assertEqual(ds.stage(row(state="CLEANED", merged=merged, deployed=deployed)), want)

    def test_merged_cell_forms(self):
        for cell in ("2026-10-12 14:14Z ad23dacdf", "f9260871f (2026-10-13)", "1e3f20627 (#857), 0db7ad08f (#865)"):
            with self.subTest(cell=cell):
                self.assertEqual(ds.stage(row(state="CLEANED", merged=cell)), ds.MERGED)
        self.assertEqual(ds.stage(row(state="MERGED")), ds.MERGED)

    def test_state_groups(self):
        for state, want in [("BACKLOG", ds.PLANNED), ("READY", ds.PLANNED), ("INTAKE", ds.PLANNED),
                            ("IN_PROGRESS", ds.BUILDING), ("BUILDING", ds.BUILDING),
                            ("READY_TO_MERGE", ds.IN_REVIEW), ("VALIDATED", ds.IN_REVIEW),
                            ("BLOCKED", ds.BLOCKED), ("SOMETHING_NEW", ds.BLOCKED),
                            ("CLOSED", ds.CLOSED), ("DROPPED", ds.CLOSED), ("CLEANED", ds.CLOSED),
                            ("DONE", ds.CLOSED)]:
            with self.subTest(state=state):
                self.assertEqual(ds.stage(row(state=state)), want)

    def test_reverted_merge_is_not_merged(self):
        self.assertEqual(ds.stage(row(state="DROPPED", merged="reverted")), ds.CLOSED)

    def test_pr_draft_decides_building_or_review(self):
        self.assertEqual(ds.stage(row(pr=PR), []), ds.BUILDING)
        self.assertEqual(ds.stage(row(pr=PR), [DRAFT]), ds.BUILDING)
        self.assertEqual(ds.stage(row(pr=PR), [OPEN]), ds.IN_REVIEW)
        self.assertEqual(ds.stage(row(pr=PR), [DRAFT, OPEN]), ds.IN_REVIEW)
        self.assertEqual(ds.stage(row(pr=PR), [{**OPEN, "state": "CLOSED"}]), ds.BUILDING)

    def test_pr_lookup_only_for_unmerged_active_rows(self):
        self.assertTrue(ds.needs_pr_lookup(row(pr=PR)))
        self.assertFalse(ds.needs_pr_lookup(row(pr="—")))
        self.assertFalse(ds.needs_pr_lookup(row(pr=PR, merged="2026-10-12 14:14Z ad23dacdf")))
        self.assertFalse(ds.needs_pr_lookup(row(pr=PR, state="CLEANED")))


class Segment(unittest.TestCase):
    def test_draft_pr_and_title(self):
        seg = ds.segment("WI-101", row(title="Katie's top bar plan (doc d0f5bd10): header → more", pr=PR), [DRAFT])
        self.assertIn("WI-101", seg)
        self.assertIn("Katie's top bar plan:", seg)
        self.assertIn("Building", seg)
        self.assertIn(f'<a href="{PR}">#940</a> (draft)', seg)
        self.assertNotIn("merged", seg)

    def test_merge_date_once_merged(self):
        seg = ds.segment("WI-5", row(state="CLEANED", pr=PR, merged="2026-10-12 14:14Z abc1234"), [])
        self.assertIn("merged 2026-10-12", seg)
        self.assertNotIn("(draft)", seg)

    def test_title_is_escaped_and_short(self):
        seg = ds.segment("WI-5", row(title="<b>x</b> " + "word " * 30), [])
        self.assertNotIn("<b>x", seg)
        self.assertIn("…", seg)


class Splice(unittest.TestCase):
    BODY = '<main><h1>Plan</h1>\n<p>Body &amp; more</p></main>\n'

    def test_inserts_first_inside_main_when_no_marker(self):
        out = ds.splice(self.BODY, KEY, banner("<span>a</span>"))
        self.assertTrue(out.startswith("<main><div data-orchestrate-status="))
        self.assertEqual(out.replace(banner("<span>a</span>"), ""), self.BODY)

    def test_inserts_at_start_without_main(self):
        body = "<h1>Plan</h1><p>x</p>"
        out = ds.splice(body, KEY, banner("<span>a</span>"))
        self.assertTrue(out.startswith("<div data-orchestrate-status="))
        self.assertEqual(out.replace(banner("<span>a</span>"), ""), body)

    def test_idempotent(self):
        row_ = banner("<span>a</span>")
        once = ds.splice(self.BODY, KEY, row_)
        self.assertEqual(ds.splice(once, KEY, row_), once)

    def test_replaces_in_place_and_leaves_rest_unchanged(self):
        old, new = banner("<span>a</span>"), banner("<span>b</span>", now=T2)
        once = ds.splice(self.BODY, KEY, old)
        twice = ds.splice(once, KEY, new)
        self.assertEqual(twice.count("data-orchestrate-status"), 1)
        self.assertEqual(twice, ds.splice(self.BODY, KEY, new))
        self.assertEqual(twice.replace(new, ""), self.BODY)

    def test_other_tracker_marker_is_left_alone(self):
        other = ds.render_row("20261020-other", DASH, T1, ["<span>o</span>"])
        body = ds.splice(self.BODY, "20261020-other", other)
        out = ds.splice(body, KEY, banner("<span>a</span>"))
        self.assertIn(other, out)
        self.assertEqual(out.count("data-orchestrate-status"), 2)

    def test_unchanged_ignores_only_update_time(self):
        body = ds.splice(self.BODY, KEY, banner("<span>a</span>", now=T1))
        self.assertTrue(ds.unchanged(body, KEY, banner("<span>a</span>", now=T2)))
        self.assertFalse(ds.unchanged(body, KEY, banner("<span>b</span>", now=T1)))
        self.assertFalse(ds.unchanged(self.BODY, KEY, banner("<span>a</span>")))


class Mapping(unittest.TestCase):
    def test_only_source_docs_line_counts(self):
        a, b, c = ("11111111-1111-1111-1111-111111111111", "22222222-2222-2222-2222-222222222222",
                   "33333333-3333-3333-3333-333333333333")
        text = (f"# WI-1\n\nSource: https://h/d/{c}\nSource docs: https://h/d/{a}, https://h/d/{b}, https://h/d/{a}\n"
                f"See also https://h/d/{c}\n")
        self.assertEqual(ds.source_docs(text), [a, b])
        self.assertEqual(ds.source_docs(f"no line https://h/d/{c}"), [])

    def test_doc_items_groups_item_files(self):
        a = "11111111-1111-1111-1111-111111111111"
        with tempfile.TemporaryDirectory() as t:
            items = Path(t) / "items"
            (items / "WI-9-repro").mkdir(parents=True)
            (items / "WI-10-x.md").write_text(f"Source docs: https://h/d/{a}\n")
            (items / "WI-9-y.md").write_text(f"Source docs: https://h/d/{a}\n")
            (items / "WI-11-z.md").write_text(f"mentions https://h/d/{a}\n")
            self.assertEqual(ds.doc_items(t), {a: ["WI-9", "WI-10"]})


if __name__ == "__main__":
    unittest.main()
