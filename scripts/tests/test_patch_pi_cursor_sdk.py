import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / "scripts/patch_pi_cursor_sdk.py"
UPSTREAM_DEFAULT = "return parseEnvBoolean(env[CURSOR_ASK_QUESTION_ENV], true);"
PATCHED_DEFAULT = "return parseEnvBoolean(env[CURSOR_ASK_QUESTION_ENV], false);"


class PatchPiCursorSdkTest(unittest.TestCase):
    def create_package(self, root: Path, source: str = UPSTREAM_DEFAULT) -> Path:
        target = root / "npm/node_modules/pi-cursor-sdk/src/cursor-question-tool.ts"
        target.parent.mkdir(parents=True)
        target.write_text(f"export function enabled() {{ {source} }}\n", encoding="utf-8")
        return target

    def run_patch(self, agent_dir: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(PATCH), *arguments],
            env={**os.environ, "PI_CODING_AGENT_DIR": str(agent_dir)},
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_disables_question_bridge_and_verifies_idempotently(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = self.create_package(root)

            first = self.run_patch(root)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertIn(PATCHED_DEFAULT, target.read_text(encoding="utf-8"))

            second = self.run_patch(root)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertIn("disabled by default", second.stdout)

            checked = self.run_patch(root, "--check")
            self.assertEqual(checked.returncode, 0, checked.stderr)

    def test_check_and_patch_reject_unknown_upstream_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.create_package(root, "return true;")

            checked = self.run_patch(root, "--check")
            self.assertNotEqual(checked.returncode, 0)
            self.assertIn("not disabled by default", checked.stderr)

            patched = self.run_patch(root)
            self.assertNotEqual(patched.returncode, 0)
            self.assertIn("expected upstream default not found", patched.stderr)

    def test_missing_package_is_a_safe_noop(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_patch(Path(directory))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("package not found", result.stdout)


if __name__ == "__main__":
    unittest.main()
