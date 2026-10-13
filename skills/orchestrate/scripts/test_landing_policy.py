#!/usr/bin/env python3
"""Guards the landing policy: failures block, warnings never do (operator ruling 2026-10-12).

A zero-warning landing bar turned one main repair into a 22-hour merge hold and a
1,306-file PR. Run: python3 test_landing_policy.py"""
import re, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SKILL_ROOTS = [REPO / "skills", REPO / "_codex" / "skills"]
WARNINGS_BLOCK = re.compile(
    r"zero[- ]warnings?|failures? and warnings?|failure or warning|check or warning"
    r"|warnings? (?:is|are|count|counts) (?:as )?(?:a )?failures?",
    re.IGNORECASE,
)


class LandingPolicy(unittest.TestCase):
    def test_no_skill_makes_warnings_block(self):
        hits = []
        for root in SKILL_ROOTS:
            for path in sorted(root.rglob("*.md")):
                for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                    if WARNINGS_BLOCK.search(line):
                        hits.append(f"{path.relative_to(REPO)}:{n}: {line.strip()[:160]}")
        self.assertEqual(hits, [], "warnings never block a landing (orchestrate SKILL.md § What fails a gate)")

if __name__ == "__main__":
    unittest.main()
