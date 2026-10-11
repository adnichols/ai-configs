#!/usr/bin/env python3
"""Tests for landing_queue.py against real temporary git repositories. Run: python3 test_landing_queue.py"""
import io, json, subprocess, sys, tempfile, unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))
import landing_queue as lq

ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
LONG = "".join(f"line {i}\n" for i in range(40))


def sh(cwd, *cmd):
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True, env={**__import__("os").environ, **ENV}).stdout.strip()


class Fixture:
    """origin with main and PR 1 (edits line 35 of shared.txt); the clone is the --repo."""

    def __init__(self, tmp):
        self.tmp = Path(tmp)
        origin, self.repo, self.tracker = self.tmp / "origin.git", self.tmp / "clone", self.tmp / "tracker"
        sh(self.tmp, "git", "init", "--bare", "-b", "main", str(origin))
        sh(self.tmp, "git", "clone", "-q", str(origin), str(self.repo))
        (self.repo / "shared.txt").write_text(LONG)
        sh(self.repo, "git", "add", "."), sh(self.repo, "git", "commit", "-qm", "base"), sh(self.repo, "git", "push", "-q", "origin", "HEAD:main")
        sh(self.repo, "git", "checkout", "-qb", "pr")
        (self.repo / "shared.txt").write_text(LONG.replace("line 35", "line 35 pr"))
        sh(self.repo, "git", "commit", "-qam", "pr")
        self.head = sh(self.repo, "git", "rev-parse", "HEAD")
        sh(self.repo, "git", "push", "-q", "origin", "HEAD:refs/pull/1/head")
        sh(self.repo, "git", "checkout", "-q", "main")
        self.tracker.mkdir()
        self.queue(f"1. #1 WI-01 validated {self.head[:9]} — LANDING note")

    def queue(self, body):
        (self.tracker / "ledger.md").write_text(f"## Status\n\n## Landing queue\n{body}\n\n## Waiting on you\n")

    def push_main(self, text, name="shared.txt"):
        (self.repo / name).write_text(text)
        sh(self.repo, "git", "add", "."), sh(self.repo, "git", "commit", "-qm", "main moves"), sh(self.repo, "git", "push", "-q", "origin", "HEAD:main")
        return sh(self.repo, "git", "rev-parse", "HEAD")

    def main_sha(self):
        return sh(self.repo, "git", "rev-parse", "HEAD")

    def gates(self, *records):
        (self.tracker / "gates.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))

    def verdict(self, strict=False, state="OPEN", draft=False, mergeable="MERGEABLE"):
        view = {"state": state, "isDraft": draft, "mergeable": mergeable, "headRefOid": self.head}
        real = lq.run
        fake = lambda cmd, cwd, *a, **k: mock.Mock(stdout=json.dumps(view)) if cmd[0] == "gh" else real(cmd, cwd, *a, **k)
        out = io.StringIO()
        with mock.patch.object(lq, "run", fake), mock.patch.object(lq, "strict_policy", return_value=strict), \
                mock.patch.object(sys, "argv", ["lq", str(self.tracker), "--repo", str(self.repo), "--json"]), redirect_stdout(out):
            self.rc = lq.main()
        return json.loads(out.getvalue())[0]

    def main_gate(self, sha=None, result="CLEAN"):
        return {"kind": "main", "sha": sha or self.main_sha(), "result": result, "log": "/logs/main.log"}

    def pr_gate(self, base=None, result="CLEAN", log="/logs/pr1.log"):
        return {"kind": "pr", "pr": 1, "base": base or self.main_sha(), "head": self.head, "result": result, "log": log}


class LandingQueue(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.f = Fixture(self._tmp.name)

    def test_no_gate_records_means_main_red(self):
        e = self.f.verdict()
        self.assertEqual(e["verdict"], "MAIN_RED")
        self.assertIn("no CLEAN gate record", e["reasons"][0])

    def test_failed_main_gate_means_main_red_even_with_a_clean_pr_gate(self):
        self.f.gates(self.f.main_gate(result="FAILED"), self.f.pr_gate())
        self.assertEqual(self.f.verdict()["verdict"], "MAIN_RED")

    def test_clean_main_without_pr_gate_asks_for_gate_run(self):
        self.f.gates(self.f.main_gate())
        e = self.f.verdict()
        self.assertEqual(e["verdict"], "GATE")
        self.assertEqual(e["base"], self.f.main_sha())

    def test_merge_requires_pr_gate_on_this_base_and_head(self):
        self.f.gates(self.f.main_gate(), self.f.pr_gate())
        e = self.f.verdict()
        self.assertEqual((e["verdict"], e["gate"]["log"]), ("MERGE", "/logs/pr1.log"))

    def test_overlap_without_conflict_merges_when_gate_clean_on_combined_tree(self):
        sha = self.f.push_main(LONG.replace("line 2\n", "line 2 main\n"))
        self.f.gates(self.f.main_gate(sha), self.f.pr_gate(sha))
        e = self.f.verdict()
        self.assertEqual(e["overlap"], ["shared.txt"])
        self.assertEqual((e["conflicts"], e["verdict"]), ([], "MERGE"))

    def test_overlap_without_conflict_still_needs_a_gate_run(self):
        sha = self.f.push_main(LONG.replace("line 2\n", "line 2 main\n"))
        self.f.gates(self.f.main_gate(sha))
        self.assertEqual(self.f.verdict()["verdict"], "GATE")

    def test_gate_record_for_an_older_base_does_not_authorize_merge(self):
        old = self.f.main_sha()
        sha = self.f.push_main(LONG.replace("line 2\n", "line 2 main\n"))
        self.f.gates(self.f.main_gate(sha), self.f.pr_gate(old))
        self.assertEqual(self.f.verdict()["verdict"], "GATE")

    def test_failed_combined_gate_sends_update(self):
        self.f.gates(self.f.main_gate(), self.f.pr_gate(result="FAILED", log="/logs/bad.log"))
        e = self.f.verdict()
        self.assertEqual(e["verdict"], "UPDATE")
        self.assertIn("/logs/bad.log", e["reasons"][0])

    def test_conflict_sends_update_despite_clean_records(self):
        sha = self.f.push_main(LONG.replace("line 35", "line 35 main"))
        self.f.gates(self.f.main_gate(sha), self.f.pr_gate(sha))
        e = self.f.verdict()
        self.assertEqual((e["verdict"], e["conflicts"]), ("UPDATE", ["shared.txt"]))

    def test_moved_head_revalidates(self):
        self.f.gates(self.f.main_gate(), self.f.pr_gate())
        self.f.queue("1. #1 WI-01 validated deadbeef1 — LANDING note")
        self.assertEqual(self.f.verdict()["verdict"], "REVALIDATE")

    def test_strict_branch_policy_sends_update_despite_clean_gate(self):
        self.f.gates(self.f.main_gate(), self.f.pr_gate())
        self.assertEqual(self.f.verdict(strict=True)["verdict"], "UPDATE")

    def test_draft_pr_is_blocked(self):
        self.f.gates(self.f.main_gate(), self.f.pr_gate())
        self.assertEqual(self.f.verdict(draft=True)["verdict"], "BLOCKED")

    def test_github_conflicting_with_clean_local_merge_is_blocked(self):
        self.f.gates(self.f.main_gate(), self.f.pr_gate())
        self.assertEqual(self.f.verdict(mergeable="CONFLICTING")["verdict"], "BLOCKED")

    def test_main_red_outranks_a_conflict(self):
        self.f.push_main(LONG.replace("line 35", "line 35 main"))
        self.assertEqual(self.f.verdict()["verdict"], "MAIN_RED")

    def test_main_record_for_an_older_sha_does_not_clear_a_moved_main(self):
        old = self.f.main_sha()
        self.f.push_main(LONG.replace("line 2\n", "line 2 main\n"))
        self.f.gates(self.f.main_gate(old), self.f.pr_gate(old))
        self.assertEqual(self.f.verdict()["verdict"], "MAIN_RED")

    def test_last_record_for_the_same_tree_wins(self):
        self.f.gates(self.f.pr_gate(result="FAILED"), self.f.main_gate(), self.f.pr_gate())
        self.assertEqual(self.f.verdict()["verdict"], "MERGE")
        self.f.gates(self.f.main_gate(), self.f.pr_gate(), self.f.pr_gate(result="FAILED"))
        self.assertEqual(self.f.verdict()["verdict"], "UPDATE")

    def test_abbreviated_shas_in_records_match(self):
        rec = self.f.pr_gate()
        rec["base"], rec["head"] = rec["base"][:9], rec["head"][:9]
        self.f.gates({**self.f.main_gate(), "sha": self.f.main_sha()[:9]}, rec)
        self.assertEqual(self.f.verdict()["verdict"], "MERGE")

    def test_repair_item_at_position_1_lands_on_a_red_main_through_the_same_gate(self):
        self.f.queue(f"1. #1 WI-90 validated {self.f.head[:9]} — LANDING REPAIR fix main")
        self.f.gates(self.f.main_gate(result="FAILED"))
        self.assertEqual(self.f.verdict()["verdict"], "GATE")
        self.f.gates(self.f.main_gate(result="FAILED"), self.f.pr_gate(result="FAILED"))
        self.assertEqual(self.f.verdict()["verdict"], "UPDATE")
        self.f.gates(self.f.main_gate(result="FAILED"), self.f.pr_gate())
        self.assertEqual(self.f.verdict()["verdict"], "MERGE")

    def test_ordinary_entry_stays_main_red_when_note_merely_mentions_repair(self):
        self.f.queue(f"1. #1 WI-01 validated {self.f.head[:9]} — LANDING needs REPAIR first")
        self.f.gates(self.f.main_gate(result="FAILED"), self.f.pr_gate())
        self.assertEqual(self.f.verdict()["verdict"], "MAIN_RED")

    def test_clean_record_needs_a_log_path(self):
        self.f.gates(self.f.main_gate(), self.f.pr_gate(log=""))
        with mock.patch.object(sys, "stderr", io.StringIO()), mock.patch.object(sys, "argv", ["lq", str(self.f.tracker), "--repo", str(self.f.repo)]):
            self.assertEqual(lq.main(), 2)

    def test_malformed_gate_line_exits_2(self):
        (self.f.tracker / "gates.jsonl").write_text("not json\n")
        with mock.patch.object(sys, "stderr", io.StringIO()), mock.patch.object(sys, "argv", ["lq", str(self.f.tracker), "--repo", str(self.f.repo)]):
            self.assertEqual(lq.main(), 2)


if __name__ == "__main__":
    unittest.main()
