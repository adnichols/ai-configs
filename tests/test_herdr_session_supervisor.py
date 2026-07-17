import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).parents[1] / "scripts/herdr_session_supervisor.py"
SPEC = importlib.util.spec_from_file_location("herdr_session_supervisor", SCRIPT)
assert SPEC and SPEC.loader
supervisor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(supervisor)


def write_transcript(path: Path, *, error=True, goal_status=None, managed_pid=None):
    entries = [{"type": "message", "message": {"role": "user", "content": "work"}}]
    if goal_status:
        entries.append(
            {
                "type": "custom",
                "customType": "goal-state",
                "data": {"goal": {"id": "g", "status": goal_status}},
            }
        )
    if managed_pid is not None:
        entries.append(
            {
                "type": "message",
                "message": {
                    "role": "toolResult",
                    "toolName": "process",
                    "details": {
                        "action": "start",
                        "process": {
                            "id": "proc_7",
                            "pid": managed_pid,
                            "name": "verification",
                            "status": "running",
                        },
                    },
                },
            }
        )
    entries.append(
        {
            "type": "message",
            "message": {
                "role": "assistant",
                "stopReason": "error" if error else "stop",
                "errorMessage": "Provider API overloaded during compaction" if error else None,
                "content": [],
            },
        }
    )
    path.write_text("".join(json.dumps(item) + "\n" for item in entries))


class SupervisorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "session.jsonl"

    def tearDown(self):
        self.temp.cleanup()

    def agent(self):
        return {
            "pane_id": "w1:p1",
            "agent": "pi",
            "agent_status": "idle",
            "agent_session": {"kind": "path", "value": str(self.path)},
        }

    def scan(self, state, now, process_active=False):
        with (
            patch.object(supervisor, "collect_agents", return_value=[("default", self.agent())]),
            patch.object(
                supervisor,
                "process_evidence",
                return_value={"background_active": process_active, "meaningful": [], "raw": {}},
            ),
        ):
            return supervisor.inspect_once(
                state,
                now=now,
                grace_seconds=120,
                required_observations=3,
                dry_run=True,
                log_path=Path(self.temp.name) / "log",
            )

    def test_requires_grace_and_nudges_once(self):
        write_transcript(self.path)
        state = {}
        self.assertEqual(self.scan(state, 0), [])
        self.assertEqual(self.scan(state, 60), [])
        self.assertEqual(len(self.scan(state, 120)), 1)
        self.assertEqual(self.scan(state, 180), [])

    def test_active_goal_prevents_intervention(self):
        write_transcript(self.path, goal_status="active")
        state = {}
        for now in (0, 60, 120, 180):
            self.assertEqual(self.scan(state, now), [])
        self.assertEqual(state["records"]["default:w1:p1"]["reason"], "goal-controlled")

    def test_background_work_prevents_intervention(self):
        write_transcript(self.path)
        state = {}
        for now in (0, 60, 120, 180):
            self.assertEqual(self.scan(state, now, process_active=True), [])
        self.assertEqual(state["records"]["default:w1:p1"]["reason"], "background-active")

    def test_live_managed_process_from_transcript_prevents_intervention(self):
        write_transcript(self.path, managed_pid=4242)
        state = {}
        with patch.object(supervisor.os, "kill", return_value=None):
            for now in (0, 60, 120, 180):
                self.assertEqual(self.scan(state, now), [])
        self.assertEqual(state["records"]["default:w1:p1"]["reason"], "background-active")

    def test_healthy_session_is_quiet(self):
        write_transcript(self.path, error=False)
        state = {}
        for now in (0, 60, 120, 180):
            self.assertEqual(self.scan(state, now), [])

    def test_infers_unique_pi_cwd_transcript(self):
        expected = Path(self.temp.name) / "latest.jsonl"
        with patch.object(Path, "home", return_value=Path(self.temp.name)):
            bucket = (
                Path(self.temp.name)
                / ".pi/agent/sessions/--tmp-unique-worktree--"
            )
            bucket.mkdir(parents=True)
            expected = bucket / "latest.jsonl"
            expected.write_text("{}\n")
            self.assertEqual(supervisor.infer_pi_transcript("/tmp/unique/worktree"), expected)


if __name__ == "__main__":
    unittest.main()
