#!/usr/bin/env python3

import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
SKILL = SCRIPTS.parent
RECONCILE = SCRIPTS / "reconcile.py"
FIXTURE = SCRIPTS / "fixtures/week-of-oct-5"
NOW = "2026-10-12T12:00Z"
AGENT = "11111111-2222-3333-4444-555555555555"

FAKE_PASEO = """#!/usr/bin/env python3
import json, os, sys
data = json.load(open(os.environ["FAKE_PASEO"]))
args = sys.argv[1:]
if args[0] == "inspect":
    agent = data["agents"].get(args[1])
    if agent is None:
        print(json.dumps({"error": {"message": "Failed to inspect agent: Agent not found: " + args[1]}}))
        sys.exit(1)
    print(json.dumps(agent))
else:
    print(json.dumps(data["ls"]))
"""


def ago(**delta):
    return (datetime(2026, 10, 12, 12, 0, tzinfo=timezone.utc) - timedelta(**delta)).strftime("%Y-%m-%dT%H:%M:00Z")


def tracker_dir(root, rows, timelines=None, header=""):
    """rows: (id, state, waiting on, workspace/agent) tuples; timelines: id -> list of timeline lines."""
    lines = [f"# test\n\nMode: ORCHESTRATION\n{header}\n\n## Status",
             "| ID | Kind | Title | Repo | State | Workspace / agent | PR | Waiting on | Priority | Merged | Deployed |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for id_, state, waiting, worker, *merged in rows:
        lines.append(f"| {id_} | BUG | title of {id_} | r | {state} | {worker or '—'} | — | {waiting} | P2 | {merged[0] if merged else '—'} | — |")
    (root / "items").mkdir()
    (root / "ledger.md").write_text("\n".join(lines) + "\n\n## Landing queue\nEmpty.\n")
    for id_, state, *_ in rows:
        stamps = (timelines or {}).get(id_, [ago(hours=1)])
        (root / "items" / f"{id_}-x.md").write_text(f"# {id_}\n\n## Timeline\n" + "".join(f"- {t} event\n" for t in stamps))
    return root


class ReconcileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.tracker = self.root / "tracker"
        self.tracker.mkdir()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.fake = self.root / "fake.json"
        self.fake.write_text(json.dumps({"agents": {}, "ls": []}))
        paseo = self.bin / "paseo"
        paseo.write_text(FAKE_PASEO)
        paseo.chmod(0o755)
        self.env = {**os.environ, "PATH": f"{self.bin}:{os.environ['PATH']}", "FAKE_PASEO": str(self.fake),
                    "ORCHESTRATE_HOSTS": str(self.root / "no-hosts.json")}

    def tearDown(self):
        self.temp.cleanup()

    def run_reconcile(self, tracker=None, *args):
        p = subprocess.run([sys.executable, str(RECONCILE), str(tracker or self.tracker), "--now", NOW, "--json", *args],
                           capture_output=True, text=True, env=self.env)
        out = json.loads(p.stdout) if p.stdout.strip() else None
        return p.returncode, out, p.stderr

    def verdicts(self, *args, **kw):
        code, out, err = self.run_reconcile(None, *args)
        self.assertIn(code, (0, 10), err)
        return code, {r["id"]: r for r in out["rows"]}

    def set_agents(self, agents, ls=()):
        self.fake.write_text(json.dumps({"agents": agents, "ls": list(ls)}))

    def test_week_of_oct_5_fixture_flags_queued_rows_with_cleared_gates(self):
        code, out, _ = self.run_reconcile(FIXTURE, "--now", "2026-10-11T13:30Z", "--no-live")
        self.assertEqual(code, 10)
        rows = {r["id"]: r for r in out["rows"]}
        self.assertEqual({i: r["verdict"] for i, r in rows.items()}, {"BB-78": "LAUNCH", "BB-114": "LAUNCH", "BB-115": "LAUNCH", "BB-116": "LAUNCH"})
        self.assertEqual(rows["BB-78"]["gate_cleared_at"], "2026-10-08 22:45Z")
        self.assertEqual(rows["BB-78"]["last_movement"], "2026-10-08 19:50Z")
        self.assertIn("actions=4", out["summary"])

    def test_gate_open_waits_then_goes_stale_and_clears_when_dependency_merges(self):
        tracker_dir(self.tracker, [("WI-1", "IN_PROGRESS", "worker", None), ("WI-2", "QUEUED", "gate: WI-1", None)],
                    {"WI-2": [ago(hours=2)]})
        code, rows = self.verdicts("--no-live")
        self.assertEqual((rows["WI-2"]["verdict"], rows["WI-2"]["gate"]), ("WAIT", "waiting on WI-1"))
        _, rows = self.verdicts("--no-live", "--bound", "stale=90m")
        self.assertEqual(rows["WI-2"]["verdict"], "STALE")
        ledger = (self.tracker / "ledger.md").read_text().replace("| IN_PROGRESS |", "| CLOSED |")
        (self.tracker / "ledger.md").write_text(ledger)
        _, rows = self.verdicts("--no-live")
        self.assertEqual(rows["WI-2"]["verdict"], "LAUNCH")
        self.assertNotIn("WI-1", rows)

    def test_gate_that_cannot_be_judged_is_check_not_launch(self):
        tracker_dir(self.tracker, [("WI-1", "QUEUED", "gate: WI-99", None), ("WI-2", "BACKLOG", "gate: soon", None),
                                   ("WI-3", "QUEUED", "gate: https://github.com/o/r/pull/9", None)])
        _, rows = self.verdicts("--no-live", "--no-net")
        self.assertEqual({i: r["verdict"] for i, r in rows.items()}, {"WI-1": "CHECK", "WI-2": "CHECK", "WI-3": "CHECK"})

    def test_park_is_the_only_way_a_queued_row_with_no_gate_is_not_launched(self):
        tracker_dir(self.tracker, [("WI-1", "BACKLOG", "park: log only until the retro", None), ("WI-2", "BACKLOG", "log it", None)],
                    {"WI-1": [ago(hours=3)], "WI-2": [ago(hours=3)]})
        _, rows = self.verdicts("--no-live")
        self.assertEqual((rows["WI-1"]["verdict"], rows["WI-2"]["verdict"]), ("PARKED", "LAUNCH"))
        _, rows = self.verdicts("--no-live", "--bound", "stale=2h")
        self.assertEqual(rows["WI-1"]["verdict"], "STALE")

    def test_operator_wait_reports_age_and_asks_after_the_bound(self):
        tracker_dir(self.tracker, [("WI-1", "NEEDS_OPERATOR", "operator: card", None), ("WI-2", "VALIDATED", "operator: card", None),
                                   ("WI-3", "VALIDATED", "—", None)],
                    {"WI-1": [ago(hours=30)], "WI-2": [ago(hours=2)], "WI-3": [ago(hours=2)]})
        _, rows = self.verdicts("--no-live")
        self.assertEqual([rows[i]["verdict"] for i in ("WI-1", "WI-2", "WI-3")], ["ASK", "WAIT_OPERATOR", "LAND"])
        self.assertEqual(rows["WI-1"]["age"], "1d6h")

    def test_merged_needs_cleanup_and_terminal_rows_are_skipped(self):
        tracker_dir(self.tracker, [("WI-1", "MERGED", "—", None), ("WI-2", "CLEANED", "—", None), ("WI-3", "CLOSED (duplicate)", "—", None),
                                   ("WI-4", "DEFERRED", "—", None)])
        _, rows = self.verdicts("--no-live")
        self.assertEqual({i: r["verdict"] for i, r in rows.items()}, {"WI-1": "CLEANUP"})

    def test_merge_hold_is_held_and_worker_questions_are_the_drivers(self):
        tracker_dir(self.tracker, [("WI-1", "VALIDATED", "operator: merge hold", None), ("WI-2", "NEEDS_ORCHESTRATOR", "driver: oracle", None)],
                    {"WI-1": [ago(hours=40)]})
        code, rows = self.verdicts("--no-live")
        self.assertEqual((code, rows["WI-1"]["verdict"], rows["WI-2"]["verdict"]), (10, "HELD", "DECIDE"))

    def test_nothing_to_act_on_exits_zero(self):
        tracker_dir(self.tracker, [("WI-1", "NEEDS_OPERATOR", "operator: card", None)])
        code, rows = self.verdicts("--no-live")
        self.assertEqual((code, rows["WI-1"]["verdict"]), (0, "WAIT_OPERATOR"))

    def test_worker_idle_missing_or_with_a_slow_review_is_chased(self):
        names = {"WI-1": ("11111111-2222-3333-4444-aaaaaaaaaaaa", "idle", dict(minutes=5)),
                 "WI-2": ("11111111-2222-3333-4444-bbbbbbbbbbbb", "idle", dict(hours=3)),
                 "WI-3": ("11111111-2222-3333-4444-cccccccccccc", "running", dict(minutes=1)),
                 "WI-4": ("11111111-2222-3333-4444-dddddddddddd", "running", dict(minutes=1)),
                 "WI-5": ("11111111-2222-3333-4444-eeeeeeeeeeee", None, None)}
        tracker_dir(self.tracker, [(i, "HANDED_OFF", "worker", f"dever: ws / {a}") for i, (a, _, _) in names.items()])
        agents = {a: {"Status": s, "UpdatedAt": ago(**d), "CreatedAt": ago(hours=5), "ParentAgentId": None} for a, s, d in names.values() if s}
        agents["rev-1"] = {"Status": "running", "UpdatedAt": ago(minutes=1), "CreatedAt": ago(minutes=45), "ParentAgentId": names["WI-4"][0]}
        agents["rev-2"] = {"Status": "running", "UpdatedAt": ago(minutes=1), "CreatedAt": ago(minutes=10), "ParentAgentId": names["WI-3"][0]}
        self.set_agents(agents, [{"id": "rev-1", "status": "running", "name": "Review PR 9"}, {"id": "rev-2", "status": "running", "name": "reviewer-two"}])
        _, rows = self.verdicts()
        self.assertEqual([rows[i]["verdict"] for i in names], ["OK", "CHASE", "OK", "CHASE", "CHASE"])
        self.assertIn("running 45m", rows["WI-4"]["why"])
        self.assertIn("not found", rows["WI-5"]["why"])

    def test_missing_gh_or_future_dated_entries_do_not_hide_or_break_rows(self):
        tracker_dir(self.tracker, [("WI-1", "QUEUED", "gate: https://github.com/o/r/pull/9", None), ("WI-2", "BLOCKED", "lab", None)],
                    {"WI-2": [ago(hours=30), "2026-10-12T20:00Z"]})
        self.env["PATH"] = str(self.bin)
        code, out, err = self.run_reconcile(None, "--no-live")
        rows = {r["id"]: r for r in out["rows"]}
        self.assertEqual((code, rows["WI-1"]["verdict"], rows["WI-2"]["verdict"]), (10, "CHECK", "STALE"), err)
        self.assertIn("future-dated entries ignored", rows["WI-2"]["age_source"])

    def test_worker_row_without_live_check_falls_back_to_timeline_age(self):
        tracker_dir(self.tracker, [("WI-1", "HANDED_OFF", "worker", f"dever: ws / {AGENT}"), ("WI-2", "HANDED_OFF", "worker", "—")],
                    {"WI-1": [ago(minutes=20)], "WI-2": [ago(hours=3)]})
        _, rows = self.verdicts("--no-live")
        self.assertEqual((rows["WI-1"]["verdict"], rows["WI-2"]["verdict"]), ("OK", "CHASE"))

    def test_ledger_header_sets_bounds_and_a_bad_bound_is_rejected(self):
        tracker_dir(self.tracker, [("WI-1", "BLOCKED", "waiting for lab", None)], {"WI-1": [ago(hours=3)]}, header="Reconcile: stale=2h")
        _, rows = self.verdicts("--no-live")
        self.assertEqual(rows["WI-1"]["verdict"], "STALE")
        code, _, err = self.run_reconcile(None, "--bound", "stale=soon")
        self.assertEqual(code, 2)
        self.assertIn("bad duration", err)

    def test_dashboard_attention_block_lists_flagged_rows(self):
        sys.path.insert(0, str(SCRIPTS))
        import dashboard
        tracker_dir(self.tracker, [("WI-1", "QUEUED", "—", None), ("WI-2", "NEEDS_OPERATOR", "operator: card", None)])
        template = (SKILL / "references/dashboard-template.html").read_text()
        ledger = (self.tracker / "ledger.md").read_text()
        page = dashboard.render(ledger, "t", template, "", self.tracker, datetime(2026, 10, 12, 12, 0, tzinfo=timezone.utc))
        self.assertIn("Needs attention: stale or unlaunched", page)
        self.assertRegex(page, r"WI-1</span> <span class=\"pill blocked\">LAUNCH</span>")
        self.assertNotIn(">WAIT_OPERATOR<", page)
        self.assertIn("last movement 2026-10-12 11:00Z", page)

    def test_dashboard_text_does_not_change_while_a_verdict_holds(self):
        sys.path.insert(0, str(SCRIPTS))
        import dashboard
        tracker_dir(self.tracker, [("WI-1", "BLOCKED", "lab", None)], {"WI-1": [ago(hours=30)]})
        template = (SKILL / "references/dashboard-template.html").read_text()
        ledger = (self.tracker / "ledger.md").read_text()
        at = lambda hours: dashboard.render(ledger, "t", template, "", self.tracker, datetime(2026, 10, 12, 12 + hours, 0, tzinfo=timezone.utc))
        self.assertIn("STALE", at(0))
        self.assertEqual(at(0), at(3))


if __name__ == "__main__":
    unittest.main()
