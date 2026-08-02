import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / "scripts" / "patch_pi_subagents_review_isolation.py"


class PatchPiSubagentsReviewIsolationTest(unittest.TestCase):
    def test_patches_source_and_dist_idempotently(self):
        with tempfile.TemporaryDirectory() as temp:
            agent_dir = Path(temp)
            package = agent_dir / "npm/node_modules/@tintinweb/pi-subagents"
            files = {
                "src/types.ts": 'export type IsolationMode = "worktree";\n',
                "dist/types.d.ts": 'export type IsolationMode = "worktree";\n',
                "src/custom-agents.ts": 'isolation: fm.isolation === "worktree" ? "worktree" : undefined,\n',
                "dist/custom-agents.js": 'isolation: fm.isolation === "worktree" ? "worktree" : undefined,\n',
                "src/invocation-config.ts": "isolation: agentConfig?.isolation ?? params.isolation,\n",
                "dist/invocation-config.js": "isolation: agentConfig?.isolation ?? params.isolation,\n",
            }
            for relative, content in files.items():
                target = package / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content)

            env = {**os.environ, "PI_CODING_AGENT_DIR": str(agent_dir)}
            for _ in range(2):
                result = subprocess.run(
                    ["python3", str(PATCH)],
                    env=env,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(0, result.returncode, result.stderr)

            self.assertIn(
                'IsolationMode = "worktree" | "none"',
                (package / "src/types.ts").read_text(),
            )
            self.assertIn(
                'fm.isolation === "worktree" || fm.isolation === "none"',
                (package / "dist/custom-agents.js").read_text(),
            )

    def test_rejects_incompatible_layout_without_partial_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            agent_dir = Path(temp)
            package = agent_dir / "npm/node_modules/@tintinweb/pi-subagents"
            files = {
                "src/types.ts": 'export type IsolationMode = "worktree";\n',
                "src/custom-agents.ts": 'isolation: fm.isolation === "worktree" ? "worktree" : undefined,\n',
                "dist/custom-agents.js": 'isolation: fm.isolation === "worktree" ? "worktree" : undefined,\n',
                "src/invocation-config.ts": "isolation: agentConfig?.isolation ?? params.isolation,\n",
                "dist/invocation-config.js": "isolation: agentConfig?.isolation ?? params.isolation,\n",
            }
            for relative, content in files.items():
                target = package / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content)
            before = (package / "src/types.ts").read_text()

            result = subprocess.run(
                ["python3", str(PATCH)],
                env={**os.environ, "PI_CODING_AGENT_DIR": str(agent_dir)},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("missing", result.stderr)
            self.assertEqual(before, (package / "src/types.ts").read_text())

    def test_rejects_missing_package(self):
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run(
                ["python3", str(PATCH)],
                env={**os.environ, "PI_CODING_AGENT_DIR": temp},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("required package not found", result.stderr)

    def test_rejects_missing_agent_config_precedence(self):
        with tempfile.TemporaryDirectory() as temp:
            agent_dir = Path(temp)
            package = agent_dir / "npm/node_modules/@tintinweb/pi-subagents"
            for relative in ("src/invocation-config.ts", "dist/invocation-config.js"):
                target = package / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("isolation: params.isolation ?? agentConfig?.isolation,\n")

            result = subprocess.run(
                ["python3", str(PATCH)],
                env={**os.environ, "PI_CODING_AGENT_DIR": str(agent_dir)},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("agent-config isolation precedence missing", result.stderr)


if __name__ == "__main__":
    unittest.main()
