import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE_CONTRACT = ROOT / "scripts/pi-vcc-real-host-integration.ts"


class PiVccValidationCliTest(unittest.TestCase):
    def run_command(self, command, env=None):
        return subprocess.run(
            command, cwd=ROOT, env={**os.environ, **(env or {})}, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=600,
        )

    def assert_artifact_layout(self, root: Path):
        self.assertTrue((root / "sessions").is_dir())
        self.assertTrue(any((root / "sessions").rglob("*.jsonl")))
        self.assertTrue((root / "logs/pi-vcc.jsonl").is_file())

    def candidate_contract_command(self, artifacts: Path | None = None):
        command = [
            "bun", str(CANDIDATE_CONTRACT), "--candidate", "source", "--cases", "all",
            "--session-mode", "file-backed", "--provider", "deterministic-fake",
        ]
        if artifacts is not None:
            command.extend(["--artifacts-dir", str(artifacts)])
        return command

    def test_candidate_contract_accepts_existing_empty_artifacts_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            artifacts = Path(directory) / "candidate-contract"
            artifacts.mkdir()
            result = self.run_command(self.candidate_contract_command(artifacts))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(str(artifacts.resolve()), result.stdout)
            self.assert_artifact_layout(artifacts)

    def test_candidate_contract_creates_nonexistent_artifacts_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            artifacts = Path(directory) / "nested/candidate"
            result = self.run_command(self.candidate_contract_command(artifacts))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(str(artifacts.resolve()), result.stdout)
            self.assert_artifact_layout(artifacts)

    def test_candidate_contract_rejects_nonempty_artifacts_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            artifacts = Path(directory) / "artifacts"
            artifacts.mkdir()
            occupied = artifacts / "occupied"
            occupied.write_text("do not overwrite")
            result = self.run_command(self.candidate_contract_command(artifacts))
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(occupied.read_text(), "do not overwrite")

    def test_installed_candidate_does_not_fall_back_to_source(self):
        with tempfile.TemporaryDirectory() as directory:
            artifacts = Path(directory) / "failure-artifacts"
            result = self.run_command(
                [
                    "bun", str(CANDIDATE_CONTRACT), "--candidate", "installed", "--cases", "all",
                    "--session-mode", "file-backed", "--provider", "deterministic-fake",
                    "--artifacts-dir", str(artifacts),
                ],
                {"PI_VCC_INSTALLED_PACKAGE": "/definitely/missing/pi-vcc"},
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(artifacts.is_dir())
            self.assertIn(str(artifacts.resolve()), result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
