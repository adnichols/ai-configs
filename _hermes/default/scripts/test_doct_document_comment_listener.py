#!/usr/bin/env python3
"""Regression checks for the document-scoped Doct listener contract."""
from __future__ import annotations

import importlib.util
import pathlib
import tempfile
import unittest
from unittest import mock

SCRIPT = pathlib.Path.home() / ".hermes" / "scripts" / "doct_document_comment_listener.py"
SPEC = importlib.util.spec_from_file_location("doct_document_comment_listener", SCRIPT)
assert SPEC and SPEC.loader
listener = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(listener)


class ListenerContractTests(unittest.TestCase):
    def test_document_listener_uses_claiming_endpoint_not_raw_event_stream(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('DOCT_AGENT, "plans", "agent", "next"', source)
        self.assertIn('"--wait", "--timeout", "60", "--json"', source)
        self.assertNotIn('"plans", "listen"', source)

    def test_claim_parts_reads_nested_claim_and_thread(self) -> None:
        self.assertEqual(
            listener.claim_parts({"thread": {"id": "thread-1"}, "claim": {"id": "claim-1"}}),
            ("thread-1", "claim-1"),
        )

    def test_worker_prompt_carries_canonical_source_and_completion_contract(self) -> None:
        claim = {"threadId": "thread-1", "claimId": "claim-1", "body": "test"}
        with tempfile.TemporaryDirectory() as tmp:
            captured: dict[str, object] = {}

            def fake_subprocess_run(cmd, **kwargs):
                captured["cmd"] = cmd
                return mock.Mock(returncode=0)

            with mock.patch.object(listener.subprocess, "run", side_effect=fake_subprocess_run):
                rc = listener.process_claim(
                    "doc-1",
                    "workspace-1",
                    "https://doct.example/docs/doc-1",
                    "/repo/thoughts/plans/example.html",
                    claim,
                    pathlib.Path(tmp),
                )

            self.assertEqual(rc, 0)
            cmd = captured["cmd"]
            self.assertIsInstance(cmd, list)
            prompt = cmd[-1]
            self.assertIn("Canonical source path: /repo/thoughts/plans/example.html", prompt)
            self.assertIn("reply", prompt)
            self.assertIn("ack and resolve", prompt)
            self.assertIn("release the claim", prompt)


if __name__ == "__main__":
    unittest.main(verbosity=2)
