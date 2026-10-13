#!/usr/bin/env python3
"""Tests for landing_queue.py against real temporary git repositories. Run: python3 test_landing_queue.py"""
import io, json, os, subprocess, sys, tempfile, unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))
import landing_queue as lq

ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
LONG = "".join(f"line {i}\n" for i in range(40))


def sh(cwd, *cmd):
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True, env={**os.environ, **ENV}).stdout.strip()


class Fixture:
    """origin with main; PR n is a branch off main pushed to refs/pull/<n>/head. The clone is the --repo."""

    def __init__(self, tmp):
        self.tmp = Path(tmp)
        origin, self.repo, self.tracker = self.tmp / "origin.git", self.tmp / "clone", self.tmp / "tracker"
        sh(self.tmp, "git", "init", "--bare", "-b", "main", str(origin))
        sh(self.tmp, "git", "clone", "-q", str(origin), str(self.repo))
        (self.repo / "shared.txt").write_text(LONG)
        sh(self.repo, "git", "add", "."), sh(self.repo, "git", "commit", "-qm", "base"), sh(self.repo, "git", "push", "-q", "origin", "HEAD:main")
        self.heads = {}
        self.pr(1, {"shared.txt": LONG.replace("line 35", "line 35 pr")})
        self.tracker.mkdir()
        self.header = ""
        self.queue(f"1. #1 WI-01 validated {self.heads[1][:9]} — note")

    def pr(self, n, files):
        sh(self.repo, "git", "checkout", "-q", "-b", f"pr{n}", "origin/main")
        for name, text in files.items():
            (self.repo / name).parent.mkdir(parents=True, exist_ok=True)
            (self.repo / name).write_text(text)
        sh(self.repo, "git", "add", "."), sh(self.repo, "git", "commit", "-qm", f"pr {n}")
        self.heads[n] = sh(self.repo, "git", "rev-parse", "HEAD")
        sh(self.repo, "git", "push", "-q", "origin", f"HEAD:refs/pull/{n}/head")
        sh(self.repo, "git", "checkout", "-q", "main")
        return self.heads[n]

    def queue(self, body):
        (self.tracker / "ledger.md").write_text(f"# T\n{self.header}\n## Status\n\n## Landing queue\n{body}\n\n## Waiting on you\n")

    def push_main(self, files):
        sh(self.repo, "git", "pull", "-q", "origin", "main")
        for name, text in files.items():
            (self.repo / name).parent.mkdir(parents=True, exist_ok=True)
            (self.repo / name).write_text(text)
        sh(self.repo, "git", "add", "."), sh(self.repo, "git", "commit", "-qm", "main moves"), sh(self.repo, "git", "push", "-q", "origin", "HEAD:main")
        return sh(self.repo, "git", "rev-parse", "HEAD")

    def main_sha(self):
        sh(self.repo, "git", "fetch", "-q", "origin")
        return sh(self.repo, "git", "rev-parse", "origin/main")

    def gates(self, *records):
        (self.tracker / "gates.jsonl").write_text("".join((r if isinstance(r, str) else json.dumps(r)) + "\n" for r in records))

    def report(self, strict=False, state="OPEN", draft=False, mergeable="MERGEABLE"):
        def fake(cmd, cwd, *a, **k):
            if cmd[0] == "gh":
                return mock.Mock(stdout=json.dumps({"state": state, "isDraft": draft, "mergeable": mergeable, "headRefOid": self.heads[int(cmd[3])]}))
            return real(cmd, cwd, *a, **k)
        real = lq.run
        out = io.StringIO()
        with mock.patch.object(lq, "run", fake), mock.patch.object(lq, "strict_policy", return_value=strict), \
                mock.patch.object(sys, "argv", ["lq", str(self.tracker), "--repo", str(self.repo), "--json"]), redirect_stdout(out):
            self.rc = lq.main()
        return json.loads(out.getvalue())

    def verdicts(self, **kw):
        return [e["verdict"] for e in self.report(**kw)["entries"]]

    def exit_code(self):
        with mock.patch.object(sys, "stderr", io.StringIO()), mock.patch.object(sys, "argv", ["lq", str(self.tracker), "--repo", str(self.repo)]):
            return lq.main()


class Verdicts(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.f = Fixture(self._tmp.name)

    def test_validated_pr_on_current_main_merges_without_any_gate_record(self):
        self.assertEqual(self.f.verdicts(), ["MERGE"])

    def test_main_moving_in_other_files_still_merges(self):
        self.f.push_main({"other.txt": "x\n"})
        e = self.f.report()["entries"][0]
        self.assertEqual((e["verdict"], e["overlap"]), ("MERGE", []))

    def test_main_changing_a_file_the_pr_changes_sends_update_even_without_conflict(self):
        self.f.push_main({"shared.txt": LONG.replace("line 2\n", "line 2 main\n")})
        e = self.f.report()["entries"][0]
        self.assertEqual((e["verdict"], e["conflicts"], e["overlap"]), ("UPDATE", [], ["shared.txt"]))

    def test_conflict_sends_update(self):
        self.f.push_main({"shared.txt": LONG.replace("line 35", "line 35 main")})
        e = self.f.report()["entries"][0]
        self.assertEqual((e["verdict"], e["conflicts"]), ("UPDATE", ["shared.txt"]))

    def test_overlap_only_in_generated_paths_merges_but_a_conflict_there_updates(self):
        self.f.pr(2, {"groma/map.md": "pr\n", "b.txt": "b\n"})
        self.f.header = "Generated paths: groma/*\n"
        self.f.queue(f"1. #2 WI-02 validated {self.f.heads[2][:9]} — note")
        self.f.push_main({"groma/other.md": "main\n"})
        self.assertEqual(self.f.verdicts(), ["MERGE"])
        self.f.push_main({"groma/map.md": "main\n"})
        self.assertEqual(self.f.verdicts(), ["UPDATE"])

    def test_later_pr_sharing_files_with_an_earlier_landing_pr_waits(self):
        self.f.pr(2, {"shared.txt": LONG.replace("line 5\n", "line 5 two\n")})
        self.f.pr(3, {"c.txt": "c\n"})
        self.f.queue("\n".join(f"{i}. #{n} WI-0{n} validated {self.f.heads[n][:9]} — note" for i, n in enumerate((1, 2, 3), 1)))
        self.assertEqual(self.f.verdicts(), ["MERGE", "WAIT", "MERGE"])

    def test_a_pr_that_cannot_land_does_not_hold_later_prs(self):
        self.f.pr(2, {"shared.txt": LONG.replace("line 5\n", "line 5 two\n")})
        self.f.queue(f"1. #1 WI-01 validated deadbeef1 — note\n2. #2 WI-02 validated {self.f.heads[2][:9]} — note")
        self.assertEqual(self.f.verdicts(), ["REVALIDATE", "MERGE"])

    def test_moved_head_revalidates(self):
        self.f.queue("1. #1 WI-01 validated deadbeef1 — note")
        self.assertEqual(self.f.verdicts(), ["REVALIDATE"])

    def test_strict_branch_policy_sends_update(self):
        self.assertEqual(self.f.verdicts(strict=True), ["UPDATE"])

    def test_draft_closed_and_github_only_conflicts_are_blocked(self):
        self.assertEqual(self.f.verdicts(draft=True), ["BLOCKED"])
        self.assertEqual(self.f.verdicts(state="CLOSED"), ["BLOCKED"])
        self.assertEqual(self.f.verdicts(mergeable="CONFLICTING"), ["BLOCKED"])

    def test_legacy_state_words_in_queue_lines_still_parse(self):
        self.f.queue(f"1. #1 WI-01 validated {self.f.heads[1][:9]} — LANDING merge as-is")
        e = self.f.report()["entries"][0]
        self.assertEqual((e["verdict"], e["note"]), ("MERGE", "merge as-is"))


class MainGate(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.f = Fixture(self._tmp.name)

    def rec(self, sha, result, log="/logs/main.log"):
        return {"kind": "main", "sha": sha, "result": result, **({"log": log} if log else {})}

    def test_failed_main_gate_never_blocks_a_merge(self):
        self.f.gates(self.rec(self.f.main_sha(), "FAILED"))
        r = self.f.report()
        self.assertEqual([e["verdict"] for e in r["entries"]], ["MERGE"])
        self.assertEqual(r["main_gate"]["record"]["result"], "FAILED")

    def test_run_is_due_when_main_tip_has_no_record_and_nothing_runs(self):
        self.assertTrue(self.f.report()["main_gate"]["due"])
        self.f.gates(self.rec(self.f.main_sha(), "RUNNING", log=None))
        self.assertFalse(self.f.report()["main_gate"]["due"])

    def test_a_run_in_progress_on_an_older_main_defers_the_next_run(self):
        old = self.f.main_sha()
        self.f.push_main({"other.txt": "x\n"})
        self.f.gates(self.rec(old, "RUNNING", log=None))
        m = self.f.report()["main_gate"]
        self.assertEqual((m["record"], m["due"], m["running"]["sha"]), (None, False, old))

    def test_deploy_candidate_is_the_newest_clean_main_not_the_tip(self):
        old = self.f.main_sha()
        tip = self.f.push_main({"other.txt": "x\n"})
        self.f.gates(self.rec(old, "RUNNING", log=None), self.rec(old, "CLEAN", "/logs/old.log"), self.rec(tip, "FAILED"))
        m = self.f.report()["main_gate"]
        self.assertEqual((m["candidate"]["sha"], m["record"]["result"], m["due"]), (old, "FAILED", False))

    def test_a_later_failed_record_for_the_same_sha_withdraws_it_as_candidate(self):
        sha = self.f.main_sha()
        self.f.gates(self.rec(sha, "CLEAN"), self.rec(sha, "FAILED"))
        self.assertIsNone(self.f.report()["main_gate"]["candidate"])

    def test_abbreviated_sha_matches_the_base(self):
        self.f.gates(self.rec(self.f.main_sha()[:9], "CLEAN"))
        self.assertEqual(self.f.report()["main_gate"]["record"]["result"], "CLEAN")

    def test_records_of_other_kinds_are_ignored(self):
        self.f.gates({"kind": "pr", "pr": 1, "base": "x", "head": "y", "result": "CLEAN", "log": "/l"}, {"at": "2026-10-12", "verdict": "CLEAN"})
        self.assertEqual(self.f.report()["main_gate"]["record"], None)

    def test_finished_main_record_needs_a_log_and_garbage_exits_2(self):
        self.f.gates(self.rec(self.f.main_sha(), "CLEAN", log=None))
        self.assertEqual(self.f.exit_code(), 2)
        self.f.gates("not json")
        self.assertEqual(self.f.exit_code(), 2)

    def test_empty_queue_still_reports_main_gate(self):
        self.f.queue("Empty.")
        r = self.f.report()
        self.assertEqual((r["entries"], r["main_gate"]["due"]), ([], True))


if __name__ == "__main__":
    unittest.main()
