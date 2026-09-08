import importlib.util
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills/codex-review-partner/scripts/check_no_direct_codex_review_launches.py"
SPEC = importlib.util.spec_from_file_location("codex_policy", SCRIPT)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class ScannerTest(unittest.TestCase):
    def test_repository_policy(self):
        result = subprocess.run(["python3", str(SCRIPT)], cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_multiline_and_shell_indirection_are_detected(self):
        fixtures = [
            "bash run-review.sh \\\n  --mode plan-review \\\n  --input prompt.md",
            "launcher=\"$HOME/.agents/skills/codex-review-partner/scripts/run-review.sh\"\n"
            "bash \"$launcher\" \\\n  --mode implementation-review --input prompt.md",
            "codex \\\n exec \\\n review --base main",
        ]
        for fixture in fixtures:
            with self.subTest(fixture=fixture):
                self.assertTrue(MOD.scan_text(fixture, prompt_file=True))

    def test_skill_file_style_direct_wrappers_are_detected(self):
        fixtures = [
            "## Codex review\nRun this from Pi:\n```bash\n$HOME/.agents/skills/codex-review-partner/scripts/run-review.sh \\\n+  --mode adversarial-implementation-review \\\n+  --input /tmp/prompt.md\n```",
            "### Review gate\nUse `codex exec review --base origin/main` and inspect the result.",
        ]
        for fixture in fixtures:
            with self.subTest(fixture=fixture):
                self.assertTrue(MOD.scan_text(fixture, prompt_file=True))

    def test_narrow_exempt_forms_remain_allowed(self):
        fixtures = [
            "run-review.sh --mode pair --input prompt.md",
            "codex --version",
            'codex exec "implement the review parser"',
            "cat run-review.sh",
            "run-review.sh --mode plan-review  # codex-review-policy-exempt",
        ]
        for fixture in fixtures:
            with self.subTest(fixture=fixture):
                self.assertEqual(MOD.scan_text(fixture, prompt_file=True), [])


if __name__ == "__main__":
    unittest.main()
