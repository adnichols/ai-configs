import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REAL_HOST = ROOT / "scripts/pi-vcc-real-host-integration.ts"
SOAK = ROOT / "scripts/run-pi-vcc-continuation-soak.sh"


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

    def test_real_host_accepts_existing_empty_artifacts_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            artifacts = Path(directory) / "real-host"
            artifacts.mkdir()
            result = self.run_command([
                "bun", str(REAL_HOST), "--candidate", "source", "--cases", "all",
                "--session-mode", "file-backed", "--provider", "deterministic-fake",
                "--artifacts-dir", str(artifacts),
            ])
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(str(artifacts.resolve()), result.stdout)
            self.assert_artifact_layout(artifacts)

    def test_soak_creates_nonexistent_artifacts_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            artifacts = Path(directory) / "nested/soak"
            result = self.run_command([
                "bash", str(SOAK), "--candidate", "source", "--compactions", "10",
                "--fault-matrix", "all", "--artifacts-dir", str(artifacts),
            ])
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(str(artifacts.resolve()), result.stdout)
            self.assert_artifact_layout(artifacts)

    def test_both_launchers_reject_nonempty_artifacts_directory(self):
        commands = (
            ["bun", str(REAL_HOST), "--candidate", "source", "--cases", "all", "--session-mode", "file-backed", "--provider", "deterministic-fake"],
            ["bash", str(SOAK), "--candidate", "source", "--compactions", "10", "--fault-matrix", "all"],
        )
        for command in commands:
            with self.subTest(command=Path(command[1]).name), tempfile.TemporaryDirectory() as directory:
                artifacts = Path(directory) / "artifacts"
                artifacts.mkdir()
                (artifacts / "occupied").write_text("do not overwrite")
                result = self.run_command([*command, "--artifacts-dir", str(artifacts)])
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual((artifacts / "occupied").read_text(), "do not overwrite")

    def test_explicit_artifacts_roots_survive_launcher_failure(self):
        commands = (
            (
                ["bun", str(REAL_HOST), "--candidate", "installed", "--cases", "all", "--session-mode", "file-backed", "--provider", "deterministic-fake"],
                {"PI_VCC_INSTALLED_PACKAGE": "/definitely/missing/pi-vcc"},
            ),
            (
                ["bash", str(SOAK), "--candidate", "installed", "--compactions", "10", "--fault-matrix", "all"],
                {"PI_VCC_INSTALLED_PACKAGE": "/definitely/missing/pi-vcc", "PI_VCC_INSTALLED_EXTENSION": "/definitely/missing/extension.ts"},
            ),
        )
        for command, env in commands:
            with self.subTest(command=Path(command[1]).name), tempfile.TemporaryDirectory() as directory:
                artifacts = Path(directory) / "failure-artifacts"
                result = self.run_command([*command, "--artifacts-dir", str(artifacts)], env)
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(artifacts.is_dir())
                self.assertIn(str(artifacts.resolve()), result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
