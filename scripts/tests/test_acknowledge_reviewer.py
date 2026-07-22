#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills/herdr-reviewers/scripts/acknowledge_reviewer.py"

FAKE_HERDR = r'''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
state_path = Path(os.environ["FAKE_HERDR_STATE"])
log_path = Path(os.environ["FAKE_HERDR_LOG"])
state = json.loads(state_path.read_text())
args = sys.argv[1:]
with log_path.open("a") as handle:
    handle.write(json.dumps(args) + "\n")
if args == ["workspace", "list"]:
    result = {"workspaces": [{"workspace_id": "w1", "focused": True}]}
elif args == ["tab", "list", "--workspace", "w1"]:
    result = {"tabs": [{"tab_id": state["focused_tab"], "focused": True}]}
elif args[:2] == ["agent", "get"]:
    result = {"agent": {"agent_status": state["status"]}}
elif args[:2] == ["agent", "focus"]:
    if state.get("focus_fails"):
        raise SystemExit(2)
    state["status"] = "idle"
    state["focused_tab"] = "w1:t2"
    state_path.write_text(json.dumps(state))
    result = {"agent": {"agent_status": "idle"}}
elif args[:2] == ["tab", "focus"]:
    state["focused_tab"] = args[2]
    state_path.write_text(json.dumps(state))
    result = {"tab": {"tab_id": args[2]}}
else:
    raise SystemExit(3)
print(json.dumps({"id": "test", "result": result}))
'''


class AcknowledgeReviewerTests(unittest.TestCase):
    def run_case(self, status: str, *, focus_fails: bool = False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake = root / "herdr"
            fake.write_text(FAKE_HERDR)
            fake.chmod(0o755)
            state = root / "state.json"
            state.write_text(json.dumps({
                "status": status,
                "focused_tab": "w1:t1",
                "focus_fails": focus_fails,
            }))
            log = root / "calls.jsonl"
            env = {
                **dict(__import__("os").environ),
                "FAKE_HERDR_STATE": str(state),
                "FAKE_HERDR_LOG": str(log),
            }
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "reviewer", "--herdr-bin", str(fake)],
                capture_output=True,
                text=True,
                env=env,
            )
            calls = [json.loads(line) for line in log.read_text().splitlines()]
            final_state = json.loads(state.read_text())
            return completed, calls, final_state

    def test_done_reviewer_is_acknowledged_and_original_tab_restored(self):
        completed, calls, state = self.run_case("done")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), "acknowledged")
        self.assertIn(["agent", "focus", "reviewer"], calls)
        self.assertIn(["tab", "focus", "w1:t1"], calls)
        self.assertEqual(state["status"], "idle")
        self.assertEqual(state["focused_tab"], "w1:t1")

    def test_idle_reviewer_is_a_noop(self):
        completed, calls, state = self.run_case("idle")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), "already_seen")
        self.assertEqual(calls, [["agent", "get", "reviewer"]])
        self.assertEqual(state["focused_tab"], "w1:t1")

    def test_working_reviewer_is_rejected(self):
        completed, calls, state = self.run_case("working")
        self.assertEqual(completed.returncode, 1)
        self.assertIn("must be done", completed.stderr)
        self.assertEqual(calls, [["agent", "get", "reviewer"]])
        self.assertEqual(state["focused_tab"], "w1:t1")

    def test_focus_is_restored_when_acknowledgment_fails(self):
        completed, calls, state = self.run_case("done", focus_fails=True)
        self.assertEqual(completed.returncode, 1)
        self.assertIn(["tab", "focus", "w1:t1"], calls)
        self.assertEqual(state["focused_tab"], "w1:t1")


if __name__ == "__main__":
    unittest.main()
