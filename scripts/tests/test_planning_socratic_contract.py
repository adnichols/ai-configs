import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class PlanningEvidenceContractTest(unittest.TestCase):
    def test_canonical_workflow_uses_conditional_evidence_in_existing_sections(self):
        text = (ROOT / "skills/planning-workflow/SKILL.md").read_text()
        section = text.split("### Conditional planning evidence checkpoint", 1)[1].split("Required sections", 1)[0]
        for evidence in ("First hour", "Consumers", "Siblings", "Moving ground", "Falsification", "Proof", "Untested", "Expansion disposition"):
            self.assertIn("**%s**" % evidence, section)
        self.assertIn("Do not require a standalone Socratic questionnaire", section)
        self.assertIn("Contract and distributed-integration inventory", section)
        self.assertIn("production-path proof", section)
        self.assertIn("Decisions / Deviations log", section)

    def test_authoring_and_review_guidance_do_not_require_questionnaire(self):
        for relative in ("skills/dev-plan/SKILL.md", "skills/reviewed-html-plan/SKILL.md"):
            text = (ROOT / relative).read_text()
            self.assertRegex(text.lower(), r"conditional planning[- ]evidence", relative)
            self.assertIn("do not require a standalone questionnaire", text.lower(), relative)
            self.assertIn("consumer/sibling", text, relative)
            self.assertIn("residual risk", text, relative)
            self.assertIn("expansion disposition", text, relative)

    def test_lightweight_plans_are_not_forced_to_repeat_eight_answers(self):
        text = (ROOT / "skills/planning-workflow/SKILL.md").read_text()
        self.assertIn("A lightweight or single-site plan is not forced to repeat these labels", text)
        self.assertNotIn("Every full implementation plan must contain a dedicated `Socratic plan questions` section", text)


if __name__ == "__main__":
    unittest.main()
