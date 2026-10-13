#!/usr/bin/env python3

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from deploy_status import parse_rollout, usable_targets  # noqa: E402

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
