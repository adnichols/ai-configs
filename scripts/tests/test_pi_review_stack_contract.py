import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "scripts" / "pi_review_stack_contract.py"
MANIFEST = ROOT / "scripts" / "pi-review-stack-managed-surfaces.json"


class PiReviewStackContractTest(unittest.TestCase):
    def test_manifest_v1_is_valid_and_enumerates_locked_families(self):
        result = subprocess.run(
            ["python3", str(CONTRACT), "validate", "--manifest", str(MANIFEST), "--repo-root", str(ROOT)],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(1, payload["schemaVersion"])
        self.assertEqual(payload["surfaceCount"], len(payload["ids"]))
        required = {
            "pi-prompts", "pi-extensions", "pi-libraries", "pi-agents", "pi-models", "pi-settings",
            "pi-readme", "pi-append-system", "pi-extension-removals",
            "skill-autoreview", "skill-claude-code-review", "skill-codex-review-partner",
            "skill-delivery-run", "skill-pre-pr-implementation-review", "skill-reviewed-html-plan", "skill-run-plan",
            "script-review-orchestration", "script-git-with-index-lock", "script-ensure-git-with-index-lock", "script-delivery",
            "link-git-with-index-lock", "link-ensure-git-with-index-lock", "link-delivery",
        }
        self.assertTrue(required.issubset(payload["ids"]), required - set(payload["ids"]))

    def test_manifest_rejects_unknown_fields_and_unsafe_paths(self):
        source = json.loads(MANIFEST.read_text())
        source["surfaces"][0]["unexpected"] = True
        source["surfaces"][1]["destination"] = "${PI_AGENT_DIR}/../escape"
        with tempfile.TemporaryDirectory() as temp:
            candidate = Path(temp) / "manifest.json"
            candidate.write_text(json.dumps(source))
            result = subprocess.run(
                ["python3", str(CONTRACT), "validate", "--manifest", str(candidate), "--repo-root", str(ROOT)],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertNotEqual(0, result.returncode)
        self.assertRegex(result.stderr, "unknown field|parent traversal")

    def test_summary_v1_is_atomic_private_and_complete(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "nested" / "receipt.json"
            result = subprocess.run(
                [
                    "python3", str(CONTRACT), "write-summary", "--output", str(output),
                    "--command", "install", "--mode", "pi-review-stack", "--status", "success",
                    "--repo-root", str(ROOT), "--cwd", temp, "--transport-status", "pass",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            payload = json.loads(output.read_text())
            self.assertEqual(1, payload["schemaVersion"])
            self.assertEqual("install", payload["command"])
            self.assertEqual("success", payload["status"])
            self.assertEqual("scripts/pi-review-stack-managed-surfaces.json", payload["managedSurfaceManifest"]["path"])
            self.assertRegex(payload["managedSurfaceManifest"]["sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(len(json.loads(MANIFEST.read_text())["surfaces"]), payload["managedSurfaceManifest"]["surfaceCount"])
            self.assertEqual(0o600, stat.S_IMODE(output.stat().st_mode))
            self.assertFalse(any(output.parent.glob("*.tmp.*")))

    def test_summary_rejects_mode_outside_locked_enum(self):
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run(
                ["python3", str(CONTRACT), "write-summary", "--output", str(Path(temp) / "receipt.json"), "--command", "remote-hosts", "--mode", "strict", "--status", "failed", "--repo-root", str(ROOT)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("invalid summary mode enum", result.stderr)

    def test_summary_rejects_symlink_directory_and_nonregular_destination(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            real = root / "real.json"
            real.write_text("keep")
            link = root / "link.json"
            link.symlink_to(real)
            directory = root / "directory.json"
            directory.mkdir()
            for output in (link, directory):
                with self.subTest(output=output.name):
                    result = subprocess.run(
                        ["python3", str(CONTRACT), "write-summary", "--output", str(output), "--command", "install", "--mode", "pi-review-stack", "--status", "failed", "--repo-root", str(ROOT)],
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                    self.assertNotEqual(0, result.returncode)
            self.assertEqual("keep", real.read_text())


if __name__ == "__main__":
    unittest.main()
