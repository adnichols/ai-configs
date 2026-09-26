import json

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
            {"oracle.md", "planner.md", "reviewer.md"},
            {path.name for path in AGENTS.glob("*.md")},
        )

    def test_source_extensions_capture_current_host_runtime(self):
        self.assertEqual(
            {
                "deepinfra.ts",
                "herdr-omp-agent-state.ts",
                "orca-agent-status.ts",
                "paseo-terminal-status.ts",
                "orca-prefill.ts",
                "orca-titlebar-spinner.ts",
                "thinking-shortcuts.ts",
                "eval-no-file-writes.ts",
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
            "CWD",
            "REVIEW_ROOT",
        ):
            self.assertIn(required, body)
        # Planner never recommends a model: implementation stays on the driving
        # OMP session's `default` role. Terra is not a planner or executor pick.
        self.assertNotIn("terra-high", body)
        self.assertNotIn("IMPLEMENTATION:", body)

    def test_every_managed_agent_resolves_a_configured_role(self):
        config = (OMP / "config.yml").read_text()
        block = config.split("\nmodelRoles:\n", 1)[1]
        roles = set()
        for line in block.splitlines():
            if not line.startswith("  "):
                break
            roles.add(line.strip().split(":", 1)[0])

        for path in sorted(AGENTS.glob("*.md")) + sorted((ROOT / "_adn" / "agents").glob("*.md")):
            metadata, _ = split_frontmatter(path)
            model = metadata.get("model", "")
            self.assertTrue(model.startswith("@"), f"{path.name} pins a model instead of a role: {model}")
            self.assertIn(model[1:], roles, f"{path.name} names undefined role {model}")

    def test_omp_guidance_forbids_mannered_prose(self):
        guidance = (OMP / "AGENTS.md").read_text()
        self.assertIn("When a literal phrase is available, use it", guidance)
        self.assertIn("a dial worth turning", guidance)


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
            "late-attach authorization",
        ):
            self.assertIn(required, guidance)


        for workflow_detail in (
            "workflowProfile=omp-lite",
            "delivery bootstrap --runtime omp",
            ".delivery/ledger.json",
            "xai-oauth/grok-4.6:high",
            "devin/swe-2:high",
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
            "`default` role",
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
                {
                    "oracle.md",
                    "planner.md",
                    "reviewer.md",
                    "arch-one.md",
                    "arch-two.md",
                    "arch-three.md",
                    "reviewer-two.md",
                    "reviewer-three.md",
                    "comment-sicko.md",
                },
                {path.name for path in installed.glob("*.md")},
            )
            self.assertEqual(
                {
                    "deepinfra.ts",
                    "herdr-omp-agent-state.ts",
                    "orca-agent-status.ts",
                "paseo-terminal-status.ts",
                    "orca-prefill.ts",
                    "orca-titlebar-spinner.ts",
                    "thinking-shortcuts.ts",
                    "eval-no-file-writes.ts",
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
