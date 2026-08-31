import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HANDOFF_SKILL = ROOT / "skills" / "herdr-agent-handoff" / "SKILL.md"
HERDR_SKILL = ROOT / "skills" / "herdr" / "SKILL.md"
MATRIX = ROOT / "skills" / "install-matrix.json"


class HerdrAgentHandoffTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.handoff = HANDOFF_SKILL.read_text()
        cls.herdr = HERDR_SKILL.read_text()
        cls.matrix = json.loads(MATRIX.read_text())["installableSkills"]

    def test_skill_is_universally_installable(self):
        self.assertEqual(
            {
                "class": "universal-installable",
                "allowedConsumers": ["codex", "claude", "pi", "devin"],
                "canonicalSource": "skills/herdr-agent-handoff",
                "sourceType": "repo",
            },
            {
                key: self.matrix["herdr-agent-handoff"][key]
                for key in (
                    "class",
                    "allowedConsumers",
                    "canonicalSource",
                    "sourceType",
                )
            },
        )

    def test_herdr_loads_handoff_contract_before_mutation_guidance(self):
        bridge = "load `skill://herdr-agent-handoff` before creating or opening"
        self.assertIn(bridge, self.herdr)
        self.assertLess(self.herdr.index(bridge), self.herdr.index("## Establish current context"))
        self.assertLess(self.herdr.index(bridge), self.herdr.index("herdr pane split"))
        self.assertLess(self.herdr.index(bridge), self.herdr.index("herdr worktree create"))

    def test_default_creates_same_host_session_and_worktree(self):
        for required in (
            "Create a new named Herdr session on the source host.",
            "Create a new Git worktree in that session.",
            "herdr --session <new-session>",
            "worktree create",
            "Do not reuse the source session or checkout.",
        ):
            self.assertIn(required, self.handoff)
        self.assertNotIn("session or worktree", self.handoff.lower())

    def test_remote_destination_is_explicit_and_keeps_both_resources(self):
        for required in (
            "If the operator specifies a remote host, create both the Herdr session and the worktree on that host.",
            "Without an explicit remote host, use the local host.",
            "herdr --remote <destination-ssh-target> --session <new-session>",
            "Paths in remote commands refer to the destination host.",
        ):
            self.assertIn(required, self.handoff)

    def test_remote_destination_reuses_one_global_selector_prefix(self):
        for required in (
            "Build one reusable `<destination-herdr>` prefix",
            "The `--remote` and `--session` selectors are global selectors before the command group.",
            "<destination-herdr> status",
            "<destination-herdr> workspace list",
            "<destination-herdr> worktree create",
            "<destination-herdr> pane run",
            "<destination-herdr> agent start",
            "<destination-herdr> agent prompt",
            "<destination-herdr> agent get",
            "<destination-herdr> agent read",
            "Every destination path is interpreted on the destination host.",
            "Do not run local `git`, `tar`, or `delivery --cwd <remote-path>` commands",
        ):
            self.assertIn(required, self.handoff)

    def test_transfer_preserves_runtime_and_model(self):
        for required in (
            "same agent kind, active fully qualified model",
            "Do not infer the active model from a configured default",
            "--kind <source-kind>",
            "--model <source-active-model> --thinking <source-thinking-level>",
            "report an incomplete handoff instead of silently launching a different profile",
        ):
            self.assertIn(required, self.handoff)

    def test_transfer_preserves_clean_and_dirty_git_state(self):
        for required in (
            "git rev-parse HEAD",
            "git status --porcelain=v1 -z --untracked-files=all",
            "git diff --cached --binary --full-index",
            "git diff --binary --full-index",
            "git ls-files --others --exclude-standard -z",
            "git bundle",
            "copy the bundle over SSH",
            "git apply --index --binary",
            "destination `HEAD` equals the recorded source `HEAD`",
            "every untracked path, mode, size, and content hash matches",
        ):
            self.assertIn(required, self.handoff)
        self.assertLess(
            self.handoff.index("## Preserve the source checkout"),
            self.handoff.index("## Create the worktree, restore state, and start the agent"),
        )
        self.assertLess(
            self.handoff.index("destination `HEAD` equals the recorded source `HEAD`"),
            self.handoff.index("Start the destination agent"),
        )

    def test_live_transfer_does_not_require_a_handoff_document(self):
        self.assertIn(
            "Do not create a handoff document unless the operator separately requests one.",
            self.handoff,
        )
        self.assertNotIn("cmd-create-handoff", self.handoff)

    def test_acceptance_does_not_callback_a_waiting_source(self):
        for required in (
            "Prove callback routing before the acceptance prompt.",
            "herdr --remote <source-ssh-target> --session <source-session> status",
            "agent get <source-pane-or-agent>",
            "Never use a synchronous source callback during acceptance.",
            "Put every missing-context question in the `HANDOFF_BLOCKED` receipt.",
            "If the receiver returns `HANDOFF_BLOCKED`, the wait has ended.",
            "If the source is `working`, wait for it to settle before sending the question.",
            "The source is no longer waiting for your acceptance receipt.",
        ):
            self.assertIn(required, self.handoff)
        self.assertNotIn(
            "If essential context is missing, call the source instead of guessing.",
            self.handoff,
        )
        self.assertLess(
            self.handoff.index("Prove callback routing before the acceptance prompt."),
            self.handoff.index("Use this first prompt."),
        )

    def test_source_stops_work_but_remains_available(self):
        for required in (
            "HANDOFF_ACCEPTED",
            "HANDOFF_CONTEXT_COMPLETE",
            "The source agent must stop editing or running implementation commands",
            "Keep the source Herdr pane alive",
            "HANDOFF_INCOMPLETE",
            "A shell-only worktree is not a handoff.",
        ):
            self.assertIn(required, self.handoff)


if __name__ == "__main__":
    unittest.main()
