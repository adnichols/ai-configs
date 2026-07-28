import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / "scripts/patch_pi_explore_subagents.py"
UPSTREAM_SPAWN = '''\tconst proc = spawn("pi", args, {
\t\tcwd,
\t\tshell: false,
\t\tdetached: process.platform !== "win32",
\t\tstdio: ["pipe", "pipe", "pipe"],
\t\tenv: { ...process.env, [CHILD_ENV]: "1" },
\t});'''


class PatchPiExploreSubagentsTest(unittest.TestCase):
    def create_package(self, root: Path, source: str = UPSTREAM_SPAWN) -> Path:
        target = root / "npm/node_modules/@howaboua/pi-explore-subagents/src/subagent.ts"
        target.parent.mkdir(parents=True)
        target.write_text(f'import {{ spawn }} from "node:child_process";\n{source}\n')
        return target

    def run_patch(self, agent_dir: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(PATCH), *arguments],
            env={**os.environ, "PI_CODING_AGENT_DIR": str(agent_dir)},
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def patch(self, agent_dir: Path) -> subprocess.CompletedProcess[str]:
        return self.run_patch(agent_dir)

    def test_removes_all_herdr_identity_from_rpc_child_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            target = self.create_package(Path(directory))
            first = self.patch(Path(directory))
            self.assertEqual(first.returncode, 0, first.stderr)
            patched = target.read_text()
            self.assertIn('env: childEnv,', patched)
            for variable in (
                "HERDR_ENV",
                "HERDR_SOCKET_PATH",
                "HERDR_WORKSPACE_ID",
                "HERDR_TAB_ID",
                "HERDR_PANE_ID",
            ):
                self.assertIn(f'"{variable}"', patched)
                self.assertIn(f"delete childEnv[key]", patched)
            self.assertNotIn('env: { ...process.env, [CHILD_ENV]: "1" },', patched)

            second = self.patch(Path(directory))
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertIn("isolation verified", second.stdout)
            checked = self.run_patch(Path(directory), "--check")
            self.assertEqual(checked.returncode, 0, checked.stderr)

            # A lone marker must not hide a partially removed deletion loop.
            target.write_text(patched.replace("\t\tdelete childEnv[key];\n", "", 1))
            malformed = self.run_patch(Path(directory), "--check")
            self.assertNotEqual(malformed.returncode, 0)
            self.assertIn("complete Herdr child-environment isolation is absent", malformed.stderr)

    def test_refuses_an_unrecognized_upstream_launch_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            self.create_package(Path(directory), "const proc = spawn(\"pi\", args, { env: process.env });")
            result = self.patch(Path(directory))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("expected upstream spawn block not found", result.stderr)

    def test_missing_package_is_a_safe_noop(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.patch(Path(directory))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("package not found", result.stdout)


if __name__ == "__main__":
    unittest.main()
