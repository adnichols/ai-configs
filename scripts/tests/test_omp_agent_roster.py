import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OMP = ROOT / "_omp"
AGENTS = OMP / "agents"
DELIVERY_SKILL = ROOT / "skills" / "delivery-run" / "SKILL.md"
DELIVERY_CLI = ROOT / "skills" / "delivery-run" / "scripts" / "delivery"


def split_frontmatter(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text()
    marker, frontmatter, body = text.split("---", 2)
    if marker:
        raise AssertionError(f"unexpected content before frontmatter in {path}")
    metadata = {}
    for line in frontmatter.strip().splitlines():
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"')
    return metadata, body


class OmpAgentRosterTest(unittest.TestCase):
    def test_source_roster_includes_planner(self):
        self.assertEqual(
            {"oracle.md", "planner.md", "reviewer.md", "completeness.md"},
            {path.name for path in AGENTS.glob("*.md")},
        )

    def test_planner_uses_omp_frontmatter_and_pi_runtime_profile(self):
        metadata, body = split_frontmatter(AGENTS / "planner.md")

        self.assertEqual("planner", metadata.get("name"))
        self.assertEqual("openai-codex/gpt-5.6-sol", metadata.get("model"))
        self.assertEqual("medium", metadata.get("thinking-level"))
        self.assertEqual("read, grep, glob, bash, write", metadata.get("tools"))
        for pi_only_key in ("mode", "reasoningEffort", "isolation"):
            self.assertNotIn(pi_only_key, metadata)

        for required in (
            "planning-only",
            "PLAN_EXECUTION_READY",
            "IMPLEMENTATION_PROFILE",
            "CWD",
            "REVIEW_ROOT",
            "luna-xhigh",
            "terra-high",
        ):
            self.assertIn(required, body)

    def test_omp_delivery_model_routing_is_pinned(self):
        config = (OMP / "config.yml").read_text()
        metadata, body = split_frontmatter(AGENTS / "completeness.md")

        self.assertIn("default: openai-codex/gpt-5.6-luna:xhigh", config)
        self.assertIn("smol: openai-codex/gpt-5.6-luna:xhigh", config)
        self.assertIn("advisor: opencode-zen/deepseek-v4-flash:high", config)
        self.assertIn("Trouble: xai/grok-4.6:high", config)
        self.assertEqual("completeness", metadata.get("name"))
        self.assertEqual("xai/grok-4.6:high", metadata.get("model"))
        self.assertIn("request-bound artifact", metadata.get("description", ""))
        self.assertIn("requiredEnvelope", body)

    def test_omp_guidance_routes_delivery_phrases_to_omp_lite(self):
        guidance = (OMP / "AGENTS.md").read_text()
        skill = DELIVERY_SKILL.read_text()

        for required in (
            "arm our delivery workflow",
            "skill://delivery-run",
            "delivery spawn --runtime omp",
            "delivery bootstrap --runtime omp",
            "workflowProfile=omp-lite",
            "completion-review --prepare",
            "@completeness",
            "xai/grok-4.6:high",
            "acceptCommand",
        ):
            self.assertIn(required, guidance)
        for required in (
            '"arm our delivery workflow"',
            "## OMP Lite path",
            "runtime: omp",
            "workflowProfile: omp-lite",
            "current OMP agent as owner",
            "openai-codex/gpt-5.6-luna:xhigh",
            "xai/grok-4.6:high",
            "exact seven-line envelope",
        ):
            self.assertIn(required, skill)

    def test_delivery_workflow_is_explicit_opt_in_only(self):
        guidance = (OMP / "AGENTS.md").read_text()
        skill = DELIVERY_SKILL.read_text()
        metadata, _ = split_frontmatter(DELIVERY_SKILL)
        description = metadata.get("description", "")

        # Negative: generic or unrelated requests must not arm delivery.
        self.assertIn("explicit opt-in only", guidance)
        self.assertIn("Never arm", guidance)
        self.assertIn("prewalk", guidance)
        self.assertIn("Do not trigger for generic planning", description)
        self.assertIn("such as prewalk", description)
        self.assertIn("do not bootstrap or initialize delivery", skill)

        # Positive: explicit delivery requests and commands still activate.
        self.assertIn('"arm our delivery workflow"', skill)
        self.assertIn("start delivery", skill)
        self.assertIn("delivery spawn", skill)

    def test_installer_deploys_complete_agent_roster(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "omp-agent"
            env = os.environ.copy()
            env["OMP_CONFIG_TARGET"] = str(target)
            shared_target = Path(temp) / "agents-shared"
            bin_target = Path(temp) / "bin"
            env["OMP_SHARED_TARGET"] = str(shared_target)
            env["OMP_BIN_TARGET"] = str(bin_target)
            subprocess.run(
                ["bash", str(OMP / "install.sh")],
                cwd=ROOT,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )

            installed = target / "agents"
            self.assertEqual(
                {"oracle.md", "planner.md", "reviewer.md", "completeness.md"},
                {path.name for path in installed.glob("*.md")},
            )
            self.assertEqual(
                (AGENTS / "planner.md").read_text(),
                (installed / "planner.md").read_text(),
            )
            self.assertEqual(
                (AGENTS / "completeness.md").read_text(),
                (installed / "completeness.md").read_text(),
            )
            self.assertEqual(
                (OMP / "config.yml").read_text(),
                (target / "config.yml").read_text(),
            )
            self.assertEqual(
                DELIVERY_SKILL.read_text(),
                (shared_target / "skills" / "delivery-run" / "SKILL.md").read_text(),
            )
            self.assertEqual(
                DELIVERY_CLI.read_text(),
                (shared_target / "scripts" / "delivery").read_text(),
            )
            self.assertEqual(
                (shared_target / "scripts" / "delivery").resolve(),
                (bin_target / "delivery").resolve(),
            )


if __name__ == "__main__":
    unittest.main()
