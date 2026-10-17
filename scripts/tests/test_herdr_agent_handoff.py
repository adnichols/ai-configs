import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MATRIX = ROOT / "skills" / "install-matrix.json"


class HerdrAgentHandoffTest(unittest.TestCase):
    def test_skill_is_universally_installable(self):
        matrix = json.loads(MATRIX.read_text())["installableSkills"]
        self.assertEqual(
            {
                "class": "universal-installable",
                "allowedConsumers": ["codex", "claude", "pi", "devin"],
                "canonicalSource": "skills/herdr-agent-handoff",
                "sourceType": "repo",
            },
            {
                key: matrix["herdr-agent-handoff"][key]
                for key in (
                    "class",
                    "allowedConsumers",
                    "canonicalSource",
                    "sourceType",
                )
            },
        )


if __name__ == "__main__":
    unittest.main()
