import json
import tempfile
import unittest
from pathlib import Path

from scripts.analyze_oracle_session import analyze
from scripts.probe_pi_oracle_transport import resolve

ROOT = Path(__file__).resolve().parents[2]


class _Args:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class OracleLaunchContractTest(unittest.TestCase):
    def test_source_oracle_frontmatter_pins_contract(self):
        text = (ROOT / "_pi/agents/oracle.md").read_text()
        self.assertIn("inherit_context: true", text)
        self.assertIn("isolation: none", text)
        self.assertIn("thinking: high", text)
        self.assertIn("defaultContext: fork", text)
        self.assertIn("Caller contract", text)
        self.assertIn('subagent_type: "oracle"', text)

    def test_probe_passes_against_installed_transport_with_buggy_caller(self):
        agent_dir = Path.home() / ".pi/agent"
        if not (agent_dir / "npm/node_modules/@tintinweb/pi-subagents").is_dir():
            self.skipTest("installed pi-subagents package missing")
        args = _Args(
            agent_dir=str(agent_dir),
            agent_source_dir=str(ROOT / "_pi/agents"),
            caller_isolation="worktree",
            caller_inherit_context=False,
        )
        payload = resolve(args)
        self.assertEqual("pass", payload["status"], payload.get("reason"))
        self.assertEqual("none", payload["profile"]["effectiveIsolation"])
        self.assertTrue(payload["profile"]["effectiveInheritContext"])

    def test_analyzer_accepts_correct_call_and_rejects_bad_overrides(self):
        good = {
            "role": "assistant",
            "content": [
                {
                    "type": "toolCall",
                    "name": "Agent",
                    "arguments": {
                        "subagent_type": "oracle",
                        "description": "Choose cleanup ownership",
                        "prompt": (
                            "Decision: cleanup ownership A vs B.\n"
                            "Inherited: plan locked A.\n"
                            "Options: A CLI helper; B node tx.\n"
                            "Current recommendation: B because incident notes break AC2.\n"
                            "Uncertainty: public success semantics.\n"
                            "Should we revise the locked ownership to Option B?"
                        ),
                    },
                },
                {
                    "type": "text",
                    "text": "Oracle recommendation accepted: revise lock to Option B.",
                },
            ],
        }
        bad = {
            "role": "assistant",
            "content": [
                {
                    "type": "toolCall",
                    "name": "Agent",
                    "arguments": {
                        "subagent_type": "oracle",
                        "description": "Choose cleanup ownership",
                        "inherit_context": False,
                        "isolation": "worktree",
                        "thinking": "medium",
                        "prompt": "Just pick one without a question mark",
                    },
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            good_path = Path(tmp) / "good.jsonl"
            bad_path = Path(tmp) / "bad.jsonl"
            good_path.write_text(json.dumps(good) + "\n", encoding="utf-8")
            bad_path.write_text(json.dumps(bad) + "\n", encoding="utf-8")
            good_result = analyze(good_path)
            self.assertEqual("pass", good_result["status"], good_result)
            self.assertEqual(1, good_result["oracleCallCount"])
            bad_result = analyze(bad_path)
            self.assertEqual("fail", bad_result["status"])
            joined = " ".join(bad_result["errors"] + bad_result.get("warnings", []))
            # Launch-arg overrides are soft (install strip-guard); missing '?' packet is hard.
            self.assertIn("?", joined)
            self.assertTrue(
                any("isolation" in w for w in bad_result.get("warnings", []))
                or any("isolation" in e for e in bad_result.get("errors", []))
            )

    def test_fixture_operator_prompt_never_names_oracle(self):
        prompt = (
            ROOT / "scripts/fixtures/oracle-proactive-trigger/OPERATOR_PROMPT.md"
        ).read_text()
        self.assertNotRegex(prompt, r"(?i)\boracle\b")
        plan = (
            ROOT
            / "scripts/fixtures/oracle-proactive-trigger/thoughts/plans/remote-delete-cleanup-ownership.md"
        ).read_text()
        self.assertIn("Option A", plan)
        self.assertIn("locked", plan.lower())
        evidence = (
            ROOT / "scripts/fixtures/oracle-proactive-trigger/evidence/incident-notes.md"
        ).read_text()
        self.assertIn("Option B", evidence)
        self.assertIn("conflicts with locked", evidence.lower())


if __name__ == "__main__":
    unittest.main()
