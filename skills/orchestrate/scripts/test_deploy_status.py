#!/usr/bin/env python3

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from deploy_status import parse_deploy_history, parse_rollout, usable_targets  # noqa: E402

# Real `pnpm rollout` output captured with Cloudflare queries failing (every commit `unknown`).
REAL = (SCRIPTS / "fixtures/rollout-overview.txt").read_text()
HUBS = ["nodaste", "thelords", "adntest", "tmne", "navi", "monsoonvc", "plantista", "mycelios"]


def with_commits(text):
    """The real table with the Source commit cells filled: platform rows get a sha, collab rows another."""
    def fill(m):
        row = m.group(0)
        sha = "bbbbbbbbbbbb" if "-collab'" in row else "aaaaaaaaaaaa"
        return row.replace("'unknown'", f"'{sha}'", 1)
    return re.sub(r"^│ \d+ .*$", fill, text, flags=re.M)


class ParseRollout(unittest.TestCase):
    def test_real_output_lists_every_hub_with_unknown_commit(self):
        self.assertEqual(parse_rollout(REAL), [(h, "unknown") for h in HUBS])

    def test_platform_worker_commit_is_the_target(self):
        self.assertEqual(parse_rollout(with_commits(REAL)), [(h, "aaaaaaaaaaaa") for h in HUBS])

    def test_collab_listed_first_does_not_hide_platform(self):
        lines = with_commits(REAL).split("\n")
        i = next(n for n, l in enumerate(lines) if "'nodaste-ccore2'" in l)
        lines[i], lines[i + 1] = lines[i + 1], lines[i]
        self.assertEqual(parse_rollout("\n".join(lines))[0], ("nodaste", "aaaaaaaaaaaa"))

    def test_no_table_fails(self):
        with self.assertRaises(ValueError):
            parse_rollout("Production rollout · origin/main f9260871f843\nboom\n")

    def test_empty_commit_fails(self):
        bad = REAL.replace("'unknown'     │ 'unknown'", "''            │ 'unknown'", 1)
        with self.assertRaises(ValueError):
            parse_rollout(bad)

    def test_hub_with_only_collab_row_fails(self):
        bad = "\n".join(l for l in REAL.split("\n") if "'mycelios-ccore2'" not in l)
        with self.assertRaises(ValueError):
            parse_rollout(bad)

    def test_duplicate_platform_rows_fail(self):
        lines = REAL.split("\n")
        i = next(n for n, l in enumerate(lines) if "'tmne-ccore2'" in l)
        lines.insert(i, lines[i])
        with self.assertRaises(ValueError):
            parse_rollout("\n".join(lines))



def entry(time, hubs, commit, command=None):
    """One deploy-history entry in the document's real shape; command None omits the <small> line."""
    link = "unknown" if commit == "unknown" else f'<a href="https://x/commit/{commit}"><code>{commit}</code></a>'
    small = f"<p><small>op@x.com · {command} · run r</small></p>" if command else ""
    hubs_line = f"<strong>Hubs:</strong> {', '.join(hubs)}<br>" if hubs is not None else ""
    return (f'<h2 id="run-{time}">{time}</h2><p>{hubs_line}<strong>Date:</strong> d<br>'
            f"<strong>Commit:</strong> {link}</p>{small}<h3>PRs</h3><ul><li>#1 x</li></ul>")


class ParseDeployHistory(unittest.TestCase):
    INTRO = "<h1>Production deploy history</h1><ul><li>A <code>hub deploy</code> entry</li></ul>"
    HISTORY = Path("/tmp/deploy-history.html")

    def parse(self, *entries):
        return parse_deploy_history(self.INTRO + "".join(entries))

    def test_newest_entry_wins_per_hub(self):
        got = self.parse(entry("t3", ["a", "b"], "ccc", "rollout --all"),
                         entry("t2", ["a", "b"], "bbb", "rollout --all"))
        self.assertEqual(got, [("a", "ccc"), ("b", "ccc")])

    def test_older_non_rollout_hubs_are_excluded(self):
        got = self.parse(entry("t3", ["a", "b"], "ccc", "rollout --all"),
                         entry("t2", ["old"], "bbb", "hub deploy old"),
                         entry("t1", ["gone"], "aaa", "backfill (Cloudflare versions)"))
        self.assertEqual(got, [("a", "ccc"), ("b", "ccc")])

    def test_hub_added_by_newer_hub_deploy_is_included(self):
        got = self.parse(entry("t4", ["a"], "ddd", "hub deploy a"),
                         entry("t3", ["new"], "ccc", "hub deploy new"),
                         entry("t2", ["a", "b"], "bbb", "rollout --all"))
        self.assertEqual(got, [("a", "ddd"), ("b", "bbb"), ("new", "ccc")])

    def test_unknown_commit_is_kept(self):
        got = self.parse(entry("t2", ["a", "b"], "unknown", "rollout --all"))
        self.assertEqual(got, [("a", "unknown"), ("b", "unknown")])

    def test_none_hub_is_ignored(self):
        got = self.parse(entry("t3", ["none"], "ddd", None),
                         entry("t2", ["a"], "bbb", "rollout --all"))
        self.assertEqual(got, [("a", "bbb")])

    def test_newer_entry_without_small_line_still_counts_its_hubs(self):
        got = self.parse(entry("t3", ["x"], "ddd"), entry("t2", ["a"], "bbb", "rollout --all"))
        self.assertEqual(got, [("a", "bbb"), ("x", "ddd")])

    def test_missing_rollout_all_raises(self):
        with self.assertRaisesRegex(ValueError, "rollout --all"):
            self.parse(entry("t2", ["a"], "bbb", "hub deploy a"))

    def test_no_entries_raises(self):
        with self.assertRaisesRegex(ValueError, "no deploy entries"):
            parse_deploy_history(self.INTRO)

    def test_entry_missing_hubs_or_commit_raises(self):
        with self.assertRaisesRegex(ValueError, "no Hubs"):
            self.parse(entry("t2", None, "bbb", "rollout --all"))
        with self.assertRaisesRegex(ValueError, "no Commit"):
            self.parse("<h2>t2</h2><p><strong>Hubs:</strong> a</p><p><small>o · rollout --all · r</small></p>")

    @unittest.skipUnless(HISTORY.exists(), "saved deploy-history document not present")
    def test_real_document(self):
        got = dict(parse_deploy_history(self.HISTORY.read_text()))
        for hub in ("thelords", "tmne", "navi", "monsoonvc", "plantista", "mycelios"):
            self.assertEqual(got[hub], "1e3f20627")
        self.assertNotIn("none", got)


class UsableTargets(unittest.TestCase):
    RAW = "nodaste/nodaste-ccore2: Cloudflare API GET /workers/scripts/x/deployments failed: 403 Authentication error\n"

    def repo(self, tmp):
        git = lambda *a: subprocess.run(["git", "-C", tmp, *a], check=True, capture_output=True, text=True)
        git("init", "-q")
        git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "x")
        return git("rev-parse", "HEAD").stdout.strip()

    def test_all_unknown_exits_naming_auth_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.repo(tmp)
            with self.assertRaises(SystemExit) as cm:
                usable_targets([(h, "unknown") for h in HUBS], tmp, self.RAW)
        self.assertIn("403 Authentication error", str(cm.exception))
        self.assertIn("nothing written", str(cm.exception))

    def test_commits_absent_from_history_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.repo(tmp)
            with self.assertRaises(SystemExit):
                usable_targets([("nodaste", "deadbeefdead")], tmp)

    def test_one_known_commit_is_enough(self):
        with tempfile.TemporaryDirectory() as tmp:
            sha = self.repo(tmp)
            usable_targets([("a", "unknown"), ("b", sha[:12])], tmp)


if __name__ == "__main__":
    unittest.main()
