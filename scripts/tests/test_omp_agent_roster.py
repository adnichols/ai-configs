import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OMP = ROOT / "_omp"
AGENTS = OMP / "agents"
EXTENSIONS = OMP / "extensions"
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

    def test_source_extensions_capture_current_host_runtime(self):
        self.assertEqual(
            {
                "deepinfra.ts",
                "herdr-omp-agent-state.ts",
                "orca-agent-status.ts",
                "orca-prefill.ts",
                "orca-titlebar-spinner.ts",
                "thinking-shortcuts.ts",
            },
            {path.name for path in EXTENSIONS.glob("*.ts")},
        )


    def test_planner_uses_omp_frontmatter_and_pi_runtime_profile(self):
        metadata, body = split_frontmatter(AGENTS / "planner.md")

        self.assertEqual("planner", metadata.get("name"))
        self.assertEqual("@plan", metadata.get("model"))
        self.assertNotIn("thinking-level", metadata)
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

        self.assertIn("default: xai-oauth/grok-4.6:medium", config)
        self.assertIn("smol: openai-codex/gpt-5.6-luna:xhigh", config)
        self.assertIn("advisor: xai-oauth/grok-4.6:medium", config)
        self.assertIn("Oracle: fireworks/kimi-k3:max", config)
        self.assertIn("slow: cursor/kimi-k3-max:max", config)
        self.assertIn("plan: xai-oauth/grok-4.6:high", config)
        self.assertIn("completeness: xai-oauth/grok-4.6:medium", config)
        self.assertIn("advisor: priority", config)
        self.assertEqual("completeness", metadata.get("name"))
        self.assertEqual("xai/grok-4.5:high", metadata.get("model"))
        self.assertIn("request-bound artifact", metadata.get("description", ""))
        self.assertIn("requiredEnvelope", body)

    def test_omp_guidance_only_bootstraps_delivery_skill(self):
        guidance = (OMP / "AGENTS.md").read_text()
        skill = DELIVERY_SKILL.read_text()
        metadata, _ = split_frontmatter(DELIVERY_SKILL)

        for required in (
            "explicit opt-in only",
            '"arm our delivery workflow"',
            "invokes `/delivery` or `delivery arm`",
            "`/delivery:spawn` or `delivery spawn`",
            "skill://delivery-run",
            "authoritative for all workflow details",
        ):
            self.assertIn(required, guidance)

        for workflow_detail in (
            "workflowProfile=omp-lite",
            "delivery bootstrap --runtime omp",
            ".delivery/ledger.json",
            "openai-codex/gpt-5.6-luna:xhigh",
            "completion-review --prepare",
            "acceptCommand",
        ):
            self.assertNotIn(workflow_detail, guidance)

        self.assertIn("Do not trigger for generic planning", metadata.get("description", ""))
        for required in (
            "## OMP Lite path",
            "runtime: omp",
            "workflowProfile: omp-lite",
            "current OMP agent as owner",
            "delivery bootstrap --runtime omp",
            "openai-codex/gpt-5.6-luna:xhigh",
            "xai/grok-4.5:high",
            "exact seven-line envelope",
            "acceptCommand",
        ):
            self.assertIn(required, skill)

    def test_installer_deploys_complete_agent_roster(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "omp-agent"
            env = os.environ.copy()
            env["OMP_CONFIG_TARGET"] = str(target)
            env["OMP_CONFIG_PRUNE"] = "1"
            shared_target = Path(temp) / "agents-shared"
            bin_target = Path(temp) / "bin"
            fake_omp_bin = Path(temp) / "fake-bin"
            fake_omp_bin.mkdir()
            fake_omp = fake_omp_bin / "omp"
            fake_omp.write_text("#!/bin/sh\nexit 0\n")
            fake_omp.chmod(0o755)
            env["PATH"] = f"{fake_omp_bin}{os.pathsep}{env['PATH']}"
            env["OMP_SHARED_TARGET"] = str(shared_target)
            env["OMP_BIN_TARGET"] = str(bin_target)
            stale_agents = target / "agents"
            stale_agents.mkdir(parents=True)
            (stale_agents / "legacy.md").write_text("legacy\n")
            stale_extensions = target / "extensions"
            stale_extensions.mkdir(parents=True)
            (stale_extensions / "legacy.ts").write_text("legacy\n")
            (target / "commands").mkdir(parents=True)
            (target / "commands" / "legacy.md").write_text("legacy\n")
            (target / "SYSTEM.md").write_text("legacy\n")
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
                {
                    "deepinfra.ts",
                    "herdr-omp-agent-state.ts",
                    "orca-agent-status.ts",
                    "orca-prefill.ts",
                    "orca-titlebar-spinner.ts",
                    "thinking-shortcuts.ts",
                },
                {path.name for path in (target / "extensions").glob("*.ts")},
            )
            self.assertEqual(
                (OMP / "AGENTS.md").read_text(),
                (target / "AGENTS.md").read_text(),
            )
            self.assertFalse((target / "APPEND_SYSTEM.md").exists())
            self.assertFalse((target / "commands").exists())
            self.assertFalse((target / "SYSTEM.md").exists())
            backups = list((Path(f"{target}.before-ai-configs")).glob("*/**/*"))
            self.assertTrue(any(path.name == "legacy.md" for path in backups))
            self.assertTrue(any(path.name == "legacy.ts" for path in backups))
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

    def test_omp_runtime_discovers_installed_guidance(self):
        omp_cli = shutil.which("omp")
        if not omp_cli:
            self.skipTest("omp is not installed")
        sdk_ts = Path(os.path.realpath(omp_cli)).resolve().parent.parent / "src" / "sdk.ts"
        if not sdk_ts.is_file():
            self.skipTest(f"OMP SDK source missing at {sdk_ts}")

        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "omp-agent"
            env = os.environ.copy()
            env["OMP_CONFIG_TARGET"] = str(target)
            shared_target = Path(temp) / "agents-shared"
            bin_target = Path(temp) / "bin"
            fake_omp_bin = Path(temp) / "fake-bin"
            fake_omp_bin.mkdir()
            fake_omp = fake_omp_bin / "omp"
            fake_omp.write_text("#!/bin/sh\nexit 0\n")
            fake_omp.chmod(0o755)
            env["PATH"] = f"{fake_omp_bin}{os.pathsep}{env['PATH']}"
            env["OMP_SHARED_TARGET"] = str(shared_target)
            env["OMP_BIN_TARGET"] = str(bin_target)
            env["PI_CODING_AGENT_DIR"] = str(target)
            subprocess.run(
                ["bash", str(OMP / "install.sh")],
                cwd=ROOT,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            project = Path(temp) / "project"
            project.mkdir()
            expected = target / "AGENTS.md"
            script = (
                f"const {{ discoverContextFiles }} = await import({sdk_ts.as_posix()!r});"
                f"const files = await discoverContextFiles({project.as_posix()!r});"
                f"const expected = {str(expected)!r};"
                "const match = files.find(file => file.path === expected);"
                "if (!match) throw new Error('OMP did not discover installed AGENTS.md');"
                "if (!match.content.includes('Delivery is **explicit opt-in only**')) "
                "throw new Error('discovered file is not the managed OMP guidance');"
                "process.stdout.write(match.path);"
            )
            discovered = subprocess.run(
                ["bun", "-e", script],
                cwd=ROOT,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            self.assertEqual(str(expected), discovered)




if __name__ == "__main__":
    unittest.main()
