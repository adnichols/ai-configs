import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / "scripts" / "patch_pi_subagents_review_isolation.py"
PROBE = ROOT / "scripts" / "probe_pi_review_transport.py"


class PatchPiSubagentsReviewIsolationTest(unittest.TestCase):
    def test_patches_source_and_dist_idempotently(self):
        with tempfile.TemporaryDirectory() as temp:
            agent_dir = Path(temp)
            package = agent_dir / "npm/node_modules/@tintinweb/pi-subagents"
            guidance_src = (
                '- isolation: "worktree" runs the agent in an isolated git worktree; changes land on a branch.\n'
                '- Use inherit_context if the agent needs the parent conversation history.\n'
                '- Use isolation: "worktree" to run the agent in an isolated git worktree '
                '(safe parallel file modifications). The worktree is automatically cleaned up if the agent '
                'makes no changes; otherwise the path and branch are returned in the result.\n'
                'Set to "worktree" to run the agent in a temporary git worktree (isolated copy of the repo). '
                'Changes are saved to a branch on completion.\n'
                'const customConfig = getAgentConfig(subagentType);\n\n'
                '      const resolvedConfig = resolveAgentInvocationConfig(customConfig, params);\n'
            )
            guidance_dist = (
                '- isolation: "worktree" runs the agent in an isolated git worktree; changes land on a branch.\n'
                '- Use inherit_context if the agent needs the parent conversation history.\n'
                '- Use isolation: "worktree" to run the agent in an isolated git worktree '
                '(safe parallel file modifications). The worktree is automatically cleaned up if the agent '
                'makes no changes; otherwise the path and branch are returned in the result.\n'
                'Set to "worktree" to run the agent in a temporary git worktree (isolated copy of the repo). '
                'Changes are saved to a branch on completion.\n'
                'const customConfig = getAgentConfig(subagentType);\n'
                '            const resolvedConfig = resolveAgentInvocationConfig(customConfig, params);\n'
            )
            files = {
                "src/types.ts": 'export type IsolationMode = "worktree";\n',
                "dist/types.d.ts": 'export type IsolationMode = "worktree";\n',
                "src/custom-agents.ts": 'isolation: fm.isolation === "worktree" ? "worktree" : undefined,\n',
                "dist/custom-agents.js": 'isolation: fm.isolation === "worktree" ? "worktree" : undefined,\n',
                "src/invocation-config.ts": "isolation: agentConfig?.isolation ?? params.isolation,\n",
                "dist/invocation-config.js": "isolation: agentConfig?.isolation ?? params.isolation,\n",
                "src/index.ts": guidance_src,
                "dist/index.js": guidance_dist,
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
            self.assertIn(
                "Never set isolation for oracle, reviewer, or planner",
                (package / "dist/index.js").read_text(),
            )
            self.assertIn(
                "Omit inherit_context for oracle",
                (package / "src/index.ts").read_text(),
            )
            self.assertIn(
                "ai-configs live-checkout agent guard",
                (package / "dist/index.js").read_text(),
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

    def test_probe_reports_effective_live_review_profiles_without_model_call(self):
        with tempfile.TemporaryDirectory() as temp:
            agent_dir = Path(temp)
            package = agent_dir / "npm/node_modules/@tintinweb/pi-subagents"
            for relative in ("src/invocation-config.ts", "dist/invocation-config.js"):
                target = package / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("isolation: agentConfig?.isolation ?? params.isolation,\n")
            agents = agent_dir / "agents"
            agents.mkdir()
            (agents / "planner.md").write_text(
                "---\nname: planner\nmodel: openai-codex/gpt-5.6-sol\nreasoningEffort: medium\nisolation: none\n---\n"
            )
            (agents / "reviewer.md").write_text(
                "---\nname: reviewer\nmodel: openai-codex/gpt-5.6-terra\nreasoningEffort: medium\nisolation: none\n---\n"
            )
            result = subprocess.run(
                ["python3", str(PROBE), "--agent-dir", str(agent_dir), "--target-checkout", temp, "--json"],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            payload = __import__("json").loads(result.stdout)
            self.assertEqual("pass", payload["status"])
            self.assertEqual(str(Path(temp).resolve()), payload["targetCheckout"])
            self.assertEqual("none", payload["profiles"]["reviewer"]["effectiveIsolation"])
            self.assertEqual("openai-codex/gpt-5.6-sol", payload["profiles"]["planner"]["model"])

    def test_accepts_current_off_veto_package(self):
        with tempfile.TemporaryDirectory() as temp:
            agent_dir = Path(temp)
            package = agent_dir / "npm/node_modules/@tintinweb/pi-subagents"
            requested = "const requested = agentConfig?.isolation ?? params.isolation;\n"
            files = {
                "src/types.ts": 'export type IsolationMode = "worktree" | "off";\n',
                "dist/types.d.ts": 'export type IsolationMode = "worktree" | "off";\n',
                "src/custom-agents.ts": 'if (val === "off" || val === "none" || val === "no" || val === false) return "off";\n',
                "dist/custom-agents.js": 'if (val === "off" || val === "none" || val === "no" || val === false)\n        return "off";\n',
                "src/invocation-config.ts": requested,
                "dist/invocation-config.js": requested,
                "src/index.ts": (
                    "const customConfig = getAgentConfig(subagentType);\n\n"
                    "      const resolvedConfig = resolveAgentInvocationConfig(customConfig, params, {\n"
                ),
                "dist/index.js": (
                    "const customConfig = getAgentConfig(subagentType);\n"
                    "            const resolvedConfig = resolveAgentInvocationConfig(customConfig, params, {\n"
                ),
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
                'IsolationMode = "worktree" | "off"',
                (package / "src/types.ts").read_text(),
            )
            self.assertNotIn(
                'IsolationMode = "worktree" | "none"',
                (package / "src/types.ts").read_text(),
            )
            self.assertIn(
                "ai-configs live-checkout agent guard",
                (package / "src/index.ts").read_text(),
            )
            self.assertIn(
                "ai-configs live-checkout agent guard",
                (package / "dist/index.js").read_text(),
            )
            agents = agent_dir / "agents"
            agents.mkdir()
            (agents / "planner.md").write_text(
                "---\nname: planner\nmodel: openai-codex/gpt-5.6-sol\nreasoningEffort: medium\nisolation: none\n---\n"
            )
            (agents / "reviewer.md").write_text(
                "---\nname: reviewer\nmodel: openai-codex/gpt-5.6-terra\nreasoningEffort: medium\nisolation: none\n---\n"
            )
            probe = subprocess.run(
                ["python3", str(PROBE), "--agent-dir", str(agent_dir), "--json"],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, probe.returncode, probe.stderr)
            payload = __import__("json").loads(probe.stdout)
            self.assertEqual("pass", payload["status"])
            self.assertEqual("agent-first", payload["transportPrecedence"])

    def test_probe_fails_closed_on_incompatible_effective_isolation(self):
        with tempfile.TemporaryDirectory() as temp:
            agent_dir = Path(temp)
            package = agent_dir / "npm/node_modules/@tintinweb/pi-subagents"
            for relative in ("src/invocation-config.ts", "dist/invocation-config.js"):
                target = package / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("isolation: params.isolation ?? agentConfig?.isolation,\n")
            agents = agent_dir / "agents"
            agents.mkdir()
            for name, model in (("planner", "openai-codex/gpt-5.6-sol"), ("reviewer", "openai-codex/gpt-5.6-terra")):
                (agents / f"{name}.md").write_text(
                    f"---\nname: {name}\nmodel: {model}\nreasoningEffort: medium\nisolation: none\n---\n"
                )
            result = subprocess.run(
                ["python3", str(PROBE), "--agent-dir", str(agent_dir), "--caller-isolation", "worktree", "--json"],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(0, result.returncode)
            payload = __import__("json").loads(result.stdout)
            self.assertEqual("fail", payload["status"])
            self.assertIn("caller isolation overrides", payload["reason"])


if __name__ == "__main__":
    unittest.main()
