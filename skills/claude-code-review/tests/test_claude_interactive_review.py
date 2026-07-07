#!/usr/bin/env python3
"""Tests for the canonical Claude interactive tmux review launcher."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LAUNCHER = ROOT / "skills/claude-code-review/scripts/claude_interactive_review.py"
GUARDRAIL = ROOT / "skills/claude-code-review/scripts/check_no_direct_claude_review_launches.py"
FAKE_CLAUDE = ROOT / "skills/claude-code-review/tests/fixtures/fake_claude.py"
LINEAR_REVIEW = ROOT / "_opencode/scripts/linear_build_review.py"


def run_cmd(args: list[str], *, env: dict[str, str] | None = None, cwd: Path | None = None, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(args, cwd=str(cwd or ROOT), env=merged, text=True, capture_output=True, timeout=timeout)


class LauncherTestCase(unittest.TestCase):
    def make_fake_env(self, tmp: Path, extra: dict[str, str] | None = None) -> dict[str, str]:
        fake_bin = tmp / "bin"
        fake_home = tmp / "home"
        zdotdir = tmp / "zdotdir"
        fake_bin.mkdir()
        fake_home.mkdir()
        zdotdir.mkdir()
        claude = fake_bin / "claude"
        claude.write_text(f"#!/usr/bin/env bash\nexec {sys.executable!r} {str(FAKE_CLAUDE)!r} \"$@\"\n", encoding="utf-8")
        claude.chmod(0o755)
        zshenv = zdotdir / ".zshenv"
        zshenv.write_text(f"export PATH={fake_bin}:$PATH\n", encoding="utf-8")
        env = {
            "PATH": f"{fake_bin}:{os.environ.get('PATH', '')}",
            "HOME": str(fake_home),
            "ZDOTDIR": str(zdotdir),
        }
        if extra:
            env.update(extra)
        return env

    def launcher_args(self, tmp: Path, *, sentinel: str = "CLAUDE_REVIEW_DONE_TEST_SENTINEL_12345", timeout: int = 8) -> tuple[list[str], Path]:
        prompt = tmp / "prompt.md"
        output = tmp / "review.md"
        prompt.write_text("Read-only review. Return VERDICT: PASS_SCOPED and one sentence.", encoding="utf-8")
        args = [
            sys.executable,
            str(LAUNCHER),
            "--cwd",
            str(ROOT),
            "--prompt-file",
            str(prompt),
            "--output",
            str(output),
            "--review-name",
            "fake-review",
            "--timeout-seconds",
            str(timeout),
        ]
        if sentinel:
            args.extend(["--sentinel", sentinel])
        return args, output

    def test_fake_interactive_success_outputs_answer_and_tears_down(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            args, output = self.launcher_args(tmp)
            argv_file = tmp / "claude-argv.jsonl"
            proc = run_cmd(args, env=self.make_fake_env(tmp, {"FAKE_CLAUDE_ARGV_FILE": str(argv_file)}), timeout=30)
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            text = output.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("VERDICT: PASS_SCOPED"), text)
            self.assertIn("model=claude-opus-4-7", text)
            self.assertIn("effort=xhigh", text)
            argv_entries = [json.loads(line) for line in argv_file.read_text(encoding="utf-8").splitlines()]
            self.assertIn(["--model", "claude-opus-4-7", "--effort", "xhigh"], argv_entries)
            socket_line = next(line for line in text.splitlines() if line.startswith("socket="))
            socket = socket_line.split("=", 1)[1]
            tmux_probe = run_cmd(["tmux", "-L", socket, "list-sessions"], timeout=5)
            self.assertNotEqual(tmux_probe.returncode, 0, "successful review leaked private tmux server")

    def test_omitted_sentinel_generates_nonce_sentinel(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            args, output = self.launcher_args(tmp, sentinel="")
            proc = run_cmd(args, env=self.make_fake_env(tmp), timeout=30)
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            self.assertIn("Fake Claude review body", output.read_text(encoding="utf-8"))

    def test_invalid_sentinel_rejected_before_tmux_launch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            args, output = self.launcher_args(tmp, sentinel="DONE")
            proc = run_cmd(args, env=self.make_fake_env(tmp), timeout=15)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("CLAUDE_REVIEW_INVALID_SENTINEL", output.read_text(encoding="utf-8"))

    def test_claude_discovery_uses_login_shell_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            args, output = self.launcher_args(tmp)
            env = self.make_fake_env(tmp)
            fake_bin = str(tmp / "bin")
            env["PATH"] = os.pathsep.join(part for part in env["PATH"].split(os.pathsep) if part != fake_bin)
            proc = run_cmd(args, env=env, timeout=30)
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            self.assertIn("Fake Claude review body", output.read_text(encoding="utf-8"))

    def test_prompt_cleared_tui_output_succeeds_before_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            args, output = self.launcher_args(tmp)
            proc = run_cmd(args, env=self.make_fake_env(tmp, {"FAKE_CLAUDE_NO_ECHO": "1"}), timeout=30)
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            text = output.read_text(encoding="utf-8")
            self.assertIn("Fake Claude review body", text)
            self.assertIn("clear_boundary=prompt-cleared marker/sentinel extraction before baseline", text)

    def test_auth_preflight_false_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            args, output = self.launcher_args(tmp)
            proc = run_cmd(args, env=self.make_fake_env(tmp, {"FAKE_CLAUDE_AUTH": "0"}), timeout=20)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("CLAUDE_AUTH_UNAVAILABLE_IN_TMUX_PREFLIGHT", output.read_text(encoding="utf-8"))
            self.assertIn("inspect=tmux", output.read_text(encoding="utf-8"))

    def test_tui_not_logged_in_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            args, output = self.launcher_args(tmp)
            proc = run_cmd(args, env=self.make_fake_env(tmp, {"FAKE_CLAUDE_NOT_LOGGED_IN": "1"}), timeout=20)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("CLAUDE_AUTH_UNAVAILABLE_IN_TUI", output.read_text(encoding="utf-8"))

    def test_session_limit_after_submit_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            args, output = self.launcher_args(tmp)
            proc = run_cmd(args, env=self.make_fake_env(tmp, {"FAKE_CLAUDE_SESSION_LIMIT": "1"}), timeout=30)
            self.assertEqual(proc.returncode, 25, proc.stderr + proc.stdout)
            text = output.read_text(encoding="utf-8")
            self.assertIn("CLAUDE_SESSION_LIMIT_IN_TUI", text)
            self.assertIn("session/rate limit after submit", text)

    def test_tui_not_ready_does_not_succeed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            args, output = self.launcher_args(tmp, timeout=3)
            proc = run_cmd(args, env=self.make_fake_env(tmp, {"FAKE_CLAUDE_NO_READY": "1"}), timeout=20)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("CLAUDE_TUI_NOT_READY", output.read_text(encoding="utf-8"))

    def test_answer_before_post_submit_baseline_fails_boundary_uncertain(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            args, output = self.launcher_args(tmp)
            proc = run_cmd(args, env=self.make_fake_env(tmp, {"FAKE_CLAUDE_BOUNDARY_UNCERTAIN": "1"}), timeout=20)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("CLAUDE_TUI_BOUNDARY_UNCERTAIN", output.read_text(encoding="utf-8"))

    def test_baseline_mismatch_without_occurrence_diff_is_uncertain(self) -> None:
        spec = importlib.util.spec_from_file_location("launcher_under_test", LAUNCHER)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        marker = "CLAUDE_REVIEW_ANSWER_START_deadbeef"
        sentinel = "CLAUDE_REVIEW_DONE_TEST_SENTINEL_12345"
        self.assertIsNone(module.suffix_after_baseline("old prompt", "unrelated later text", marker, sentinel))

    def test_launcher_pins_claude_code_to_opus_4_7_extra_high(self) -> None:
        spec = importlib.util.spec_from_file_location("launcher_under_test", LAUNCHER)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        self.assertEqual(module.CLAUDE_REVIEW_MODEL, "claude-opus-4-7")
        self.assertEqual(module.CLAUDE_REVIEW_EFFORT, "xhigh")

    def test_auth_status_accepts_compact_json(self) -> None:
        spec = importlib.util.spec_from_file_location("launcher_under_test", LAUNCHER)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        self.assertTrue(module.auth_status_logged_in('{"loggedIn":true,"authMethod":"fake"}\nEXIT=0\n'))
        self.assertTrue(module.auth_status_logged_in('noise\n{"authMethod":"fake","loggedIn": true}\nEXIT=0\n'))
        self.assertFalse(module.auth_status_logged_in('{"loggedIn":false,"authMethod":"none"}\nEXIT=1\n'))

    def test_prompt_cleared_answer_extraction_rejects_visible_prompt(self) -> None:
        spec = importlib.util.spec_from_file_location("launcher_under_test", LAUNCHER)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        marker = "CLAUDE_REVIEW_ANSWER_START_deadbeef"
        sentinel = "CLAUDE_REVIEW_DONE_TEST_SENTINEL_12345"
        visible_prompt = f"Claude review launcher emission protocol\n{marker}\n<review text here>\n{sentinel}\nCLAUDE_REVIEW_FINAL_SENTINEL:{sentinel}"
        cleared_answer = f"Claude Code\n{marker}\nVERDICT: PASS_SCOPED\nPrompt cleared answer\n{sentinel}\n❯"
        self.assertIsNone(module.extract_prompt_cleared_answer(visible_prompt, marker, sentinel))
        self.assertIn("Prompt cleared answer", module.extract_prompt_cleared_answer(cleared_answer, marker, sentinel))

    def test_smoke_success_tears_down(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            output = tmp / "smoke.txt"
            proc = run_cmd([
                sys.executable,
                str(LAUNCHER),
                "--smoke",
                "--cwd",
                str(ROOT),
                "--output",
                str(output),
                "--review-name",
                "fake-smoke",
                "--timeout-seconds",
                "8",
            ], env=self.make_fake_env(tmp), timeout=25)
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            text = output.read_text(encoding="utf-8")
            self.assertIn("CLAUDE_REVIEW_SMOKE_READY", text)
            self.assertIn("model=claude-opus-4-7", text)
            self.assertIn("effort=xhigh", text)
            socket = next(line for line in text.splitlines() if line.startswith("socket=")).split("=", 1)[1]
            self.assertNotEqual(run_cmd(["tmux", "-L", socket, "list-sessions"], timeout=5).returncode, 0)


class GuardrailTestCase(unittest.TestCase):
    def run_guardrail(self, root: Path) -> subprocess.CompletedProcess[str]:
        return run_cmd([sys.executable, str(GUARDRAIL), "--root", str(root)], timeout=20)

    def test_guardrail_allows_benign_prose_paths_and_constants(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / "review-doc.md"
            path.write_text(textwrap.dedent("""
                This mentions skills/claude-code-review and claude_interactive_review.py.
                The marker CLAUDE_REVIEW_DONE_X and slug claude-plan-nod636 are prose.
                We want interactive Claude review reliability.
            """), encoding="utf-8")
            proc = self.run_guardrail(root)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_guardrail_rejects_direct_transport_candidates(self) -> None:
        bad_lines = [
            "claude -p prompt",
            "claude --print prompt",
            "cat prompt | claude",
            "claude < prompt.txt",
            "claude --future-noninteractive x",
            "interactive_shell({ command: 'claude hello' })",
            "process({ command: 'claude hello' })",
            "os.execvp('claude', ['claude', '--permission-mode', 'bypassPermissions'])",
            "cd repo && zsh -ilc 'claude'",
            "Review command: tmux new-window -n review 'claude'",
            "REVIEW_CMD=claude --dangerously-skip-permissions prompt",
            "cmd=claude prompt",
            "RUN_CLAUDE=claude prompt",
            'cmd="claude prompt"',
        ]
        for line in bad_lines:
            with self.subTest(line=line), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                (root / "review.md").write_text(line + "\n", encoding="utf-8")
                proc = self.run_guardrail(root)
                self.assertNotEqual(proc.returncode, 0, proc.stdout)
                self.assertIn("CLAUDE_DIRECT_REVIEW_LAUNCHES_FOUND", proc.stdout)

    def test_guardrail_rejects_multiline_python_argv_candidates(self) -> None:
        bad_blocks = [
            'cmd = ["claude", "-p", prompt]\nsubprocess.run(cmd)\n',
            'RUN_CLAUDE = ["claude", "--print", prompt]\n',
            'subprocess.run([\n    "claude",\n    "-p",\n    prompt,\n])\n',
            'os.execvp("claude", [\n    "claude",\n    "--permission-mode",\n    "bypassPermissions",\n])\n',
        ]
        for block in bad_blocks:
            with self.subTest(block=block), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                (root / "review.py").write_text(block, encoding="utf-8")
                proc = self.run_guardrail(root)
                self.assertNotEqual(proc.returncode, 0, proc.stdout)
                self.assertIn("CLAUDE_DIRECT_REVIEW_LAUNCHES_FOUND", proc.stdout)

    def test_guardrail_allows_marked_forbidden_examples(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "review.md").write_text("claude -p prompt  # [FORBIDDEN-EXAMPLE]\n", encoding="utf-8")
            self.assertEqual(self.run_guardrail(root).returncode, 0)

    def test_guardrail_rejects_previous_line_forbidden_marker(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "review.md").write_text("# [FORBIDDEN-EXAMPLE]\nclaude -p prompt\n", encoding="utf-8")
            self.assertNotEqual(self.run_guardrail(root).returncode, 0)

    def test_guardrail_self_and_tests_exemptions_are_path_scoped(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            exempt = root / "skills/claude-code-review/tests/sample.md"
            exempt.parent.mkdir(parents=True)
            exempt.write_text("claude -p prompt\n", encoding="utf-8")
            non_exempt = root / "other/review/sample.md"
            non_exempt.parent.mkdir(parents=True)
            non_exempt.write_text("claude -p prompt\n", encoding="utf-8")
            proc = self.run_guardrail(root)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn(str(non_exempt), proc.stdout)
            self.assertNotIn(str(exempt), proc.stdout)

    def test_guardrail_scans_plan_artifacts_when_explicitly_rooted(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plan = root / "thoughts/plans/review-plan.html"
            plan.parent.mkdir(parents=True)
            plan.write_text("claude -p prompt\n", encoding="utf-8")
            proc = self.run_guardrail(root)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn(str(plan), proc.stdout)


class OpenCodeResolverTestCase(unittest.TestCase):
    def load_module(self):
        spec = importlib.util.spec_from_file_location("linear_build_review_under_test", LINEAR_REVIEW)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        return module

    def test_env_override_resolves_launcher(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "launcher.py"
            path.write_text("# launcher\n", encoding="utf-8")
            old = os.environ.get("CLAUDE_REVIEW_LAUNCHER")
            os.environ["CLAUDE_REVIEW_LAUNCHER"] = str(path)
            try:
                self.assertEqual(self.load_module().resolve_claude_review_launcher(), path)
            finally:
                if old is None:
                    os.environ.pop("CLAUDE_REVIEW_LAUNCHER", None)
                else:
                    os.environ["CLAUDE_REVIEW_LAUNCHER"] = old

    def test_repo_checkout_resolves_launcher(self) -> None:
        old_launcher = os.environ.pop("CLAUDE_REVIEW_LAUNCHER", None)
        old_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as td:
            os.environ["HOME"] = td
            try:
                self.assertEqual(self.load_module().resolve_claude_review_launcher(), LAUNCHER)
            finally:
                if old_home is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = old_home
                if old_launcher is not None:
                    os.environ["CLAUDE_REVIEW_LAUNCHER"] = old_launcher

    def test_installed_agents_resolves_before_repo_checkout(self) -> None:
        old_launcher = os.environ.pop("CLAUDE_REVIEW_LAUNCHER", None)
        old_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            installed = home / ".agents/skills/claude-code-review/scripts/claude_interactive_review.py"
            installed.parent.mkdir(parents=True)
            installed.write_text("# installed launcher\n", encoding="utf-8")
            os.environ["HOME"] = str(home)
            try:
                self.assertEqual(self.load_module().resolve_claude_review_launcher(), installed)
            finally:
                if old_home is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = old_home
                if old_launcher is not None:
                    os.environ["CLAUDE_REVIEW_LAUNCHER"] = old_launcher

    def test_opencode_compatibility_copy_resolves_launcher(self) -> None:
        old_launcher = os.environ.pop("CLAUDE_REVIEW_LAUNCHER", None)
        old_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as td:
            home = Path(td) / "home"
            os.environ["HOME"] = str(home)
            opencode = home / ".config/opencode/skills/claude-code-review/scripts/claude_interactive_review.py"
            opencode.parent.mkdir(parents=True)
            opencode.write_text("# opencode launcher\n", encoding="utf-8")
            module = self.load_module()
            module.__file__ = str(Path(td) / "checkout/_opencode/scripts/linear_build_review.py")
            try:
                self.assertEqual(module.resolve_claude_review_launcher(), opencode)
            finally:
                if old_home is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = old_home
                if old_launcher is not None:
                    os.environ["CLAUDE_REVIEW_LAUNCHER"] = old_launcher

    def test_missing_launcher_failure_message_lists_install_and_override(self) -> None:
        old_launcher = os.environ.pop("CLAUDE_REVIEW_LAUNCHER", None)
        old_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as td:
            os.environ["HOME"] = str(Path(td) / "home")
            module = self.load_module()
            module.__file__ = str(Path(td) / "checkout/_opencode/scripts/linear_build_review.py")
            try:
                with self.assertRaises(FileNotFoundError) as exc:
                    module.resolve_claude_review_launcher()
                message = str(exc.exception)
                self.assertIn("Run ./install.sh --opencode", message)
                self.assertIn("CLAUDE_REVIEW_LAUNCHER", message)
                self.assertIn(".config/opencode/skills/claude-code-review", message)
            finally:
                if old_home is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = old_home
                if old_launcher is not None:
                    os.environ["CLAUDE_REVIEW_LAUNCHER"] = old_launcher


class RealClaudeTestCase(unittest.TestCase):
    def test_real_smoke(self) -> None:
        if os.environ.get("RUN_REAL_CLAUDE_SMOKE") != "1":
            self.skipTest("RUN_REAL_CLAUDE_SMOKE not set")
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "real-smoke.txt"
            proc = run_cmd([
                sys.executable,
                str(LAUNCHER),
                "--smoke",
                "--cwd",
                str(ROOT),
                "--output",
                str(output),
                "--review-name",
                "real-smoke",
                "--timeout-seconds",
                "120",
            ], timeout=180)
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            self.assertIn("CLAUDE_REVIEW_SMOKE_READY", output.read_text(encoding="utf-8"))

    def test_real_e2e_review(self) -> None:
        if os.environ.get("RUN_REAL_CLAUDE_E2E") != "1":
            self.skipTest("RUN_REAL_CLAUDE_E2E not set")
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            prompt = tmp / "prompt.md"
            output = tmp / "real-review.md"
            prompt.write_text("Read-only smoke review. Return exactly: VERDICT: PASS_SCOPED followed by one short sentence.", encoding="utf-8")
            proc = run_cmd([
                sys.executable,
                str(LAUNCHER),
                "--cwd",
                str(ROOT),
                "--prompt-file",
                str(prompt),
                "--output",
                str(output),
                "--review-name",
                "real-e2e-review",
                "--timeout-seconds",
                "300",
            ], timeout=420)
            text = output.read_text(encoding="utf-8") if output.exists() else ""
            if proc.returncode == 25 and "CLAUDE_SESSION_LIMIT_IN_TUI" in text:
                self.skipTest("real Claude session/rate limit is active")
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            self.assertIn("VERDICT: PASS_SCOPED", text)
            self.assertIn("clear_boundary=", text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--real-smoke", action="store_true")
    parser.add_argument("--real-e2e-review", action="store_true")
    args, remaining = parser.parse_known_args()
    if args.real_smoke:
        os.environ["RUN_REAL_CLAUDE_SMOKE"] = "1"
    if args.real_e2e_review:
        os.environ["RUN_REAL_CLAUDE_E2E"] = "1"
    unittest.main(argv=[sys.argv[0], *remaining])
    return 0


if __name__ == "__main__":
    main()
