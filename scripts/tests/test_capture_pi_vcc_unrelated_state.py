import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/capture-pi-vcc-unrelated-state.py"


class CapturePiVccUnrelatedStateTest(unittest.TestCase):
    def capture(self, agent: Path, output: Path):
        env = {**os.environ, "PI_CODING_AGENT_DIR": str(agent)}
        subprocess.run(
            ["python3", str(SCRIPT), "--output", str(output)],
            cwd=ROOT,
            env=env,
            check=True,
            timeout=600,
        )
        return output.read_bytes(), json.loads(output.read_text())

    def test_output_is_deterministic_and_excludes_stable_package(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            agent = root / "agent"
            stable = agent / "local-packages/ai-configs/pi-vcc"
            stable.mkdir(parents=True)
            (stable / "coordinator.ts").write_text("old")
            (agent / "unrelated.txt").write_text("keep")
            legacy = root / "vcc-fork"
            legacy.mkdir()
            (legacy / "package.json").write_text(json.dumps({"name": "@sting8k/pi-vcc"}))
            settings = agent / "settings.json"
            settings.write_text(json.dumps({
                "theme": "dark",
                "packages": ["npm:keep", "npm:company-pi-vcc-tools", str(stable), {"source": str(legacy)}],
            }))
            first_bytes, first = self.capture(agent, root / "first.json")
            second_bytes, second = self.capture(agent, root / "second.json")
            self.assertEqual(first_bytes, second_bytes)
            self.assertEqual(first, second)
            self.assertIn("unrelated.txt", first["files"])
            self.assertNotIn("settings.json", first["files"])
            self.assertFalse(any(path.startswith("local-packages/ai-configs/pi-vcc") for path in first["files"]))
            (stable / "coordinator.ts").write_text("candidate")
            settings.write_text(json.dumps({
                "theme": "dark",
                "packages": ["npm:keep", "npm:company-pi-vcc-tools", {"source": str(stable)}],
            }))
            changed_bytes, _changed = self.capture(agent, root / "changed.json")
            self.assertEqual(first_bytes, changed_bytes)

    def test_volatile_runtime_surfaces_are_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            agent = root / "agent"
            for relative in (
                "sessions/work/session.jsonl",
                "cache/review-prompts/result.txt",
                "messenger/state.db",
                "powerline-footer/stash-history.json",
                ".update-check",
                "pi-vcc.log.jsonl",
            ):
                path = agent / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("before")
            first_bytes, first = self.capture(agent, root / "first.json")
            for path in agent.rglob("*"):
                if path.is_file():
                    path.write_text("after")
            second_bytes, second = self.capture(agent, root / "second.json")
            self.assertEqual(first_bytes, second_bytes)
            self.assertEqual({}, first["files"])
            self.assertEqual(first, second)

    def test_unrelated_file_and_normalized_settings_changes_are_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            agent = root / "agent"
            agent.mkdir()
            unrelated = agent / "unrelated.txt"
            unrelated.write_text("one")
            settings = agent / "settings.json"
            settings.write_text(json.dumps({"theme": "dark", "packages": ["npm:keep"]}))
            first_bytes, first = self.capture(agent, root / "first.json")
            unrelated.write_text("two")
            second_bytes, second = self.capture(agent, root / "second.json")
            self.assertNotEqual(first_bytes, second_bytes)
            self.assertNotEqual(first["files"]["unrelated.txt"], second["files"]["unrelated.txt"])
            unrelated.write_text("one")
            settings.write_text(json.dumps({"theme": "light", "packages": ["npm:keep"]}))
            third_bytes, third = self.capture(agent, root / "third.json")
            self.assertNotEqual(first_bytes, third_bytes)
            self.assertNotEqual(first["normalizedSettingsHash"], third["normalizedSettingsHash"])

    def test_missing_packages_and_only_pi_vcc_packages_hash_identically(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            agent = root / "agent"
            stable = agent / "local-packages/ai-configs/pi-vcc"
            stable.mkdir(parents=True)
            (stable / "package.json").write_text(json.dumps({"name": "@adnichols/pi-vcc"}))
            settings = agent / "settings.json"
            settings.write_text(json.dumps({"theme": "dark"}))
            first_bytes, first = self.capture(agent, root / "first.json")
            settings.write_text(json.dumps({
                "theme": "dark",
                "packages": [str(stable), "git:adnichols/pi-vcc"],
            }))
            second_bytes, second = self.capture(agent, root / "second.json")
            self.assertEqual(first_bytes, second_bytes)
            self.assertEqual(first["normalizedSettingsHash"], second["normalizedSettingsHash"])


if __name__ == "__main__":
    unittest.main()
