from __future__ import annotations

import copy
import datetime as dt
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _hermes.default.scripts import gm_plan_comment_listener as listener
from _hermes.default.scripts import pi_analytics_action as action

FIXTURES = Path(__file__).parent / "fixtures" / "pi-analytics-actions"
SIGNAL = "a" * 64
EVIDENCE = "b" * 64
HTML_HASH = "c" * 64
CARD_ID = f"pi-analytics-card-{SIGNAL}"
SENTINELS = "PROMPT_SENTINEL SOURCE_SENTINEL /private/path CREDENTIAL_SENTINEL TOOL_ARGUMENT_SENTINEL"
UTC_NOW = dt.datetime(2026, 7, 20, 12, tzinfo=dt.timezone.utc)


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def registry() -> dict:
    return {
        "active_plans": [{
            "document_id": "doc-good-morning-current",
            "workspace_id": "workspace-personal-fixture",
            "routine": "good_morning",
            "status": "active",
            "document_version": 8,
            "current_version": "8",
            "html_sha256": HTML_HASH,
            "pi_analytics_cards": [{
                "card_id": CARD_ID,
                "signal_key": SIGNAL,
                "evidence_snapshot_id": EVIDENCE,
            }],
        }]
    }


def ok_runner(calls: list[list[str]]):
    def run(argv, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(list(argv))
        if kwargs.get("shell"):
            raise AssertionError("restricted action commands must never use a shell")
        output = json.dumps({"version": 8}) + "\n" if argv[:3] == ["doct-agent", "documents", "get"] else "{}\n"
        return subprocess.CompletedProcess(argv, 0, output, "")
    return run


def plan_actions(calls: list[list[str]]) -> list[str]:
    return [call[2] for call in calls if call[:2] == ["doct-agent", "plans"]]


class PiAnalyticsActionValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = json.loads((FIXTURES / "config.json").read_text(encoding="utf-8"))

    def _paths(self, root: Path) -> tuple[Path, Path]:
        registry_path = root / "active-plans.json"
        registry_path.write_text(json.dumps(registry()), encoding="utf-8")
        return registry_path, root / "actions.json"

    def test_valid_current_aaron_action_for_each_exact_command(self) -> None:
        for disposition in ("accept", "investigate", "defer", "dismiss"):
            with self.subTest(disposition=disposition), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                registry_path, ledger_path = self._paths(root)
                claim = fixture("valid-agent-claim.json")
                claim["thread"]["comments"][-1]["body"] = f"  pi-action {disposition}\n"
                calls: list[list[str]] = []
                code = action.process_claim(
                    claim,
                    registry_path=registry_path,
                    ledger_path=ledger_path,
                    aaron_user_id=self.config["aaron_doct_user_id"],
                    runner=ok_runner(calls),
                    now=UTC_NOW,
                )
                self.assertEqual(code, 0)
                saved = json.loads(ledger_path.read_text(encoding="utf-8"))
                self.assertEqual(len(saved["deliveries"]), 1)
                self.assertEqual(saved["signals"][SIGNAL]["action"], disposition)
                self.assertEqual(plan_actions(calls), ["reply", "ack", "resolve"])

    def test_observed_claim_shape_without_optional_identity_fields_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry_path, ledger_path = self._paths(root)
            claim = fixture("valid-agent-claim.json")
            claim["item"].pop("documentVersion", None)
            claim["item"].pop("signalKey", None)
            claim["item"].pop("evidenceSnapshotId", None)
            claim["thread"]["anchor"]["selector"] = f'[data-plan-node-id="{CARD_ID}"]'
            calls: list[list[str]] = []
            self.assertEqual(
                action.process_claim(
                    claim,
                    registry_path=registry_path,
                    ledger_path=ledger_path,
                    aaron_user_id=self.config["aaron_doct_user_id"],
                    runner=ok_runner(calls),
                    now=UTC_NOW,
                ),
                0,
            )
            self.assertEqual(plan_actions(calls), ["reply", "ack", "resolve"])
            self.assertEqual(len(json.loads(ledger_path.read_text())["deliveries"]), 1)

    def test_author_id_loads_from_host_local_config_with_environment_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "actions.json"
            config_path.write_text(
                json.dumps({"aaron_doct_user_id": "user-from-config"}), encoding="utf-8"
            )
            with mock.patch.dict(action.os.environ, {}, clear=True):
                self.assertEqual(action.configured_aaron_user_id(config_path), "user-from-config")
            with mock.patch.dict(
                action.os.environ,
                {"GM_PI_ANALYTICS_AARON_DOCT_USER_ID": "user-from-environment"},
                clear=True,
            ):
                self.assertEqual(
                    action.configured_aaron_user_id(config_path), "user-from-environment"
                )

    def test_only_surrounding_whitespace_is_normalized(self) -> None:
        invalid = (
            "Please pi-action accept",
            "pi-action  accept",
            "PI-ACTION accept",
            "pi-action accept thanks",
            "pi-action snooze",
        )
        for body in invalid:
            with self.subTest(body=body), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                registry_path, ledger_path = self._paths(root)
                claim = fixture("valid-agent-claim.json")
                claim["thread"]["comments"][-1]["body"] = body
                code = action.process_claim(
                    claim, registry_path=registry_path, ledger_path=ledger_path,
                    aaron_user_id=self.config["aaron_doct_user_id"], runner=ok_runner([]), now=UTC_NOW,
                )
                self.assertEqual(code, 2)
                self.assertFalse(ledger_path.exists())

    def test_wrong_author_malformed_stale_and_identity_mismatches_are_rejected(self) -> None:
        cases = {}
        claim = fixture("valid-agent-claim.json")
        claim["thread"]["routingMetadata"]["submitAction"] = "comment"
        claim["item"]["routingMetadata"]["submitAction"] = "comment"
        cases["wrong submit action"] = claim

        claim = fixture("valid-agent-claim.json")
        claim["thread"]["comments"][-1]["authorUserId"] = "user-not-aaron"
        cases["wrong user"] = claim

        claim = fixture("valid-agent-claim.json")
        claim["thread"]["comments"] = []
        cases["malformed"] = claim

        for field, value in (
            ("documentId", "doc-stale"),
            ("documentVersion", 7),
            ("generatedHtmlHash", "d" * 64),
            ("sourceHash", "d" * 64),
            ("signalKey", "d" * 64),
            ("evidenceSnapshotId", "d" * 64),
        ):
            claim = fixture("valid-agent-claim.json")
            if field == "documentId":
                claim[field] = value
                claim["item"][field] = value
                claim["thread"][field] = value
            else:
                claim["item"][field] = value
                if field == "generatedHtmlHash":
                    claim["item"]["sourceHash"] = value
            cases[f"wrong {field}"] = claim

        claim = fixture("valid-agent-claim.json")
        claim["thread"]["anchor"]["nodeId"] = f"pi-analytics-card-{'d' * 64}"
        cases["wrong card"] = claim

        claim = fixture("valid-agent-claim.json")
        claim["workspaceId"] = "workspace-other"
        claim["item"]["workspaceId"] = "workspace-other"
        claim["item"]["claim"]["workspaceId"] = "workspace-other"
        claim["thread"]["workspaceId"] = "workspace-other"
        cases["wrong registry workspace"] = claim

        for name, bad_claim in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                registry_path, ledger_path = self._paths(root)
                calls: list[list[str]] = []
                code = action.process_claim(
                    bad_claim, registry_path=registry_path, ledger_path=ledger_path,
                    aaron_user_id=self.config["aaron_doct_user_id"], runner=ok_runner(calls), now=UTC_NOW,
                )
                self.assertEqual(code, 2)
                self.assertFalse(ledger_path.exists())
                expected_actions = [] if name in {"wrong documentId", "wrong registry workspace"} else [
                    "reply", "ack", "resolve"
                ]
                self.assertEqual(plan_actions(calls), expected_actions)
                self.assertTrue(all("hermes" not in call for call in calls))

    def test_doct_timeout_uses_rejection_cleanup_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry_path, ledger_path = self._paths(root)
            claim = fixture("valid-agent-claim.json")
            calls: list[list[str]] = []

            def timeout_document_lookup(argv, **kwargs):  # type: ignore[no-untyped-def]
                calls.append(list(argv))
                if argv[:3] == ["doct-agent", "documents", "get"]:
                    raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
                return subprocess.CompletedProcess(argv, 0, "{}\n", "")

            self.assertEqual(
                action.process_claim(
                    claim,
                    registry_path=registry_path,
                    ledger_path=ledger_path,
                    aaron_user_id=self.config["aaron_doct_user_id"],
                    runner=timeout_document_lookup,
                    now=UTC_NOW,
                ),
                2,
            )
            self.assertFalse(ledger_path.exists())
            self.assertEqual(plan_actions(calls), ["reply", "ack", "resolve"])

    def test_duplicate_and_crash_retry_record_one_decision_without_extending_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry_path, ledger_path = self._paths(root)
            claim = fixture("valid-agent-claim.json")
            claim["thread"]["comments"][-1]["body"] = "pi-action accept"
            failed_calls: list[list[str]] = []

            def fail_after_write(argv, **kwargs):  # type: ignore[no-untyped-def]
                failed_calls.append(list(argv))
                if argv[:3] == ["doct-agent", "documents", "get"]:
                    return subprocess.CompletedProcess(argv, 0, json.dumps({"version": 8}), "")
                return subprocess.CompletedProcess(argv, 1, "", "fixture failure")

            self.assertEqual(action.process_claim(
                claim, registry_path=registry_path, ledger_path=ledger_path,
                aaron_user_id=self.config["aaron_doct_user_id"], runner=fail_after_write, now=UTC_NOW,
            ), 1)
            first = json.loads(ledger_path.read_text(encoding="utf-8"))
            first_until = first["signals"][SIGNAL]["visible_until"]

            calls: list[list[str]] = []
            claim["thread"]["comments"][-1]["body"] = "pi-action dismiss"
            self.assertEqual(action.process_claim(
                claim, registry_path=registry_path, ledger_path=ledger_path,
                aaron_user_id=self.config["aaron_doct_user_id"], runner=ok_runner(calls),
                now=UTC_NOW + dt.timedelta(days=2),
            ), 0)
            second = json.loads(ledger_path.read_text(encoding="utf-8"))
            self.assertEqual(len(second["deliveries"]), 1)
            self.assertEqual(second["signals"][SIGNAL]["visible_until"], first_until)
            self.assertEqual(second["signals"][SIGNAL]["action"], "accept")
            self.assertEqual(plan_actions(calls), ["reply", "ack", "resolve"])
            reply = next(call for call in calls if call[:3] == ["doct-agent", "plans", "reply"])
            self.assertIn("accept", reply[reply.index("--body") + 1])

    def test_partial_doct_close_retry_skips_completed_reply(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry_path, ledger_path = self._paths(root)
            claim = fixture("valid-agent-claim.json")
            first_calls: list[list[str]] = []

            def fail_on_ack(argv, **kwargs):  # type: ignore[no-untyped-def]
                first_calls.append(list(argv))
                if argv[:3] == ["doct-agent", "documents", "get"]:
                    return subprocess.CompletedProcess(argv, 0, json.dumps({"version": 8}), "")
                if argv[:3] == ["doct-agent", "plans", "ack"]:
                    return subprocess.CompletedProcess(argv, 1, "", "fixture failure")
                return subprocess.CompletedProcess(argv, 0, "{}\n", "")

            self.assertEqual(action.process_claim(
                claim, registry_path=registry_path, ledger_path=ledger_path,
                aaron_user_id=self.config["aaron_doct_user_id"], runner=fail_on_ack, now=UTC_NOW,
            ), 1)
            self.assertEqual(plan_actions(first_calls), ["reply", "ack", "release"])

            retry_calls: list[list[str]] = []
            self.assertEqual(action.process_claim(
                claim, registry_path=registry_path, ledger_path=ledger_path,
                aaron_user_id=self.config["aaron_doct_user_id"], runner=ok_runner(retry_calls), now=UTC_NOW,
            ), 0)
            self.assertEqual(plan_actions(retry_calls), ["ack", "resolve"])
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            delivery = next(iter(ledger["deliveries"].values()))
            self.assertEqual(delivery["closure"], {"reply": True, "ack": True, "resolve": True})

    def test_claim_file_is_removed_after_worker_reads_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            claim_path = root / "claim.json"
            claim_path.write_text(json.dumps(fixture("valid-agent-claim.json")), encoding="utf-8")
            with mock.patch.object(action, "configured_aaron_user_id", return_value="user-aaron-fixture"), mock.patch.object(
                action, "process_claim", return_value=0
            ) as process:
                code = action.main([
                    "--claim-file", str(claim_path), "--registry", str(root / "registry.json"),
                    "--ledger", str(root / "ledger.json"), "--config", str(root / "config.json"),
                ])
            self.assertEqual(code, 0)
            self.assertFalse(claim_path.exists())
            process.assert_called_once()

    def test_privacy_sentinels_never_enter_ledger_or_replies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry_path, ledger_path = self._paths(root)
            claim = fixture("valid-agent-claim.json")
            claim["thread"]["anchor"]["textQuote"] = SENTINELS
            claim["privatePrompt"] = SENTINELS
            calls: list[list[str]] = []
            self.assertEqual(action.process_claim(
                claim, registry_path=registry_path, ledger_path=ledger_path,
                aaron_user_id=self.config["aaron_doct_user_id"], runner=ok_runner(calls), now=UTC_NOW,
            ), 0)
            self.assertNotIn(SENTINELS, ledger_path.read_text(encoding="utf-8"))
            self.assertNotIn(SENTINELS, json.dumps(calls))


class PiAnalyticsListenerRoutingTests(unittest.TestCase):
    def test_restricted_worker_is_in_full_bundle_but_not_collector_component(self) -> None:
        bundle = Path(__file__).resolve().parents[2] / "_hermes" / "default"
        manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
        component = json.loads(
            (bundle / "components" / "pi-analytics-collector.json").read_text(encoding="utf-8")
        )
        paths = {item["path"] for item in manifest["files"]}
        self.assertIn("scripts/pi_analytics_action.py", paths)
        self.assertNotIn("scripts/pi_analytics_action.py", component["files"])
        self.assertEqual(component["files"], ["scripts/pi_analytics_collector.py"])

    def test_ordinary_conversation_is_noop_and_nonanalytics_agent_keeps_generic_path(self) -> None:
        ordinary = fixture("ordinary-conversation-claim.json")
        generic = fixture("non-analytics-agent-claim.json")
        with mock.patch.object(listener, "release_claim") as release, mock.patch.object(
            listener, "start_worker", return_value=mock.sentinel.generic
        ) as start_generic, mock.patch.object(listener, "start_analytics_worker") as start_analytics, mock.patch.object(
            listener, "log"
        ):
            self.assertIsNone(listener.dispatch_claim("doc-good-morning-current", "workspace-personal-fixture", ordinary))
            release.assert_called_once()
            start_generic.assert_not_called()
            start_analytics.assert_not_called()

            self.assertIs(
                listener.dispatch_claim("doc-good-morning-current", "workspace-personal-fixture", generic),
                mock.sentinel.generic,
            )
            start_generic.assert_called_once_with("doc-good-morning-current", "workspace-personal-fixture", generic)
            start_analytics.assert_not_called()

    def test_agent_routed_analytics_prefix_is_restricted_and_comments_are_noop(self) -> None:
        for node_id in (CARD_ID, "pi-analytics-card-malformed"):
            with self.subTest(node_id=node_id, submit="agent"):
                claim = fixture("valid-agent-claim.json")
                claim["thread"]["anchor"]["nodeId"] = node_id
                with mock.patch.object(
                    listener, "start_analytics_worker", return_value=mock.sentinel.restricted
                ) as restricted, mock.patch.object(listener, "start_worker") as broad:
                    self.assertIs(
                        listener.dispatch_claim("doc-good-morning-current", "workspace-personal-fixture", claim),
                        mock.sentinel.restricted,
                    )
                    restricted.assert_called_once()
                    broad.assert_not_called()

            with self.subTest(node_id=node_id, submit="comment"):
                claim = fixture("valid-agent-claim.json")
                claim["thread"]["anchor"]["nodeId"] = node_id
                claim["thread"]["routingMetadata"]["submitAction"] = "comment"
                claim["item"]["routingMetadata"]["submitAction"] = "comment"
                with mock.patch.object(listener, "release_claim") as release, mock.patch.object(
                    listener, "start_analytics_worker"
                ) as restricted, mock.patch.object(listener, "start_worker") as broad, mock.patch.object(listener, "log"):
                    self.assertIsNone(
                        listener.dispatch_claim("doc-good-morning-current", "workspace-personal-fixture", claim)
                    )
                    release.assert_called_once()
                    restricted.assert_not_called()
                    broad.assert_not_called()

    def test_restricted_worker_uses_minimal_private_claim_file_and_fixed_python_argv(self) -> None:
        claim = fixture("valid-agent-claim.json")
        claim["privatePrompt"] = SENTINELS
        claim["thread"]["anchor"]["textQuote"] = SENTINELS
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake_proc = mock.Mock(pid=12345)
            with mock.patch.object(listener, "RUN_DIR", root / "runs"), mock.patch.object(
                listener, "WORKER_DIR", root / "workers"
            ), mock.patch.object(listener, "active_worker_for_thread", return_value=None), mock.patch.object(
                listener, "log"
            ), mock.patch("subprocess.Popen", return_value=fake_proc) as popen:
                proc = listener.start_analytics_worker(
                    "doc-good-morning-current", "workspace-personal-fixture", claim
                )
            self.assertIs(proc, fake_proc)
            argv = popen.call_args.args[0]
            self.assertEqual(argv[0], listener.sys.executable)
            self.assertTrue(argv[1].endswith("pi_analytics_action.py"))
            self.assertEqual(argv[2], "--claim-file")
            claim_path = Path(argv[3])
            projected = claim_path.read_text(encoding="utf-8")
            self.assertNotIn(SENTINELS, projected)
            self.assertEqual(claim_path.stat().st_mode & 0o777, 0o600)
            value = json.loads(projected)
            self.assertEqual(set(value), {
                "documentId", "workspaceId", "threadId", "claimId",
                "claim", "item", "thread", "source",
            })
            self.assertEqual(set(value["claim"]), set())
            self.assertEqual(set(value["item"]), {
                "documentId", "workspaceId", "threadId", "documentVersion",
                "generatedHtmlHash", "sourceHash", "signalKey", "evidenceSnapshotId",
                "routingMetadata", "claim",
            })
            self.assertEqual(set(value["item"]["claim"]), {
                "id", "documentId", "workspaceId", "threadId",
            })
            self.assertEqual(set(value["thread"]), {
                "documentId", "workspaceId", "threadId", "anchor",
                "routingMetadata", "comments",
            })
            self.assertEqual(set(value["thread"]["anchor"]), {"nodeId", "selector"})
            self.assertEqual(set(value["thread"]["comments"][-1]), {
                "authorType", "authorUserId", "body",
            })
            self.assertEqual(value["thread"]["comments"][-1]["body"], "pi-action investigate")
            self.assertEqual(set(value["source"]), {"generatedHtmlHash", "sourceHash"})
            self.assertNotIn("textQuote", projected)
            self.assertNotIn("privatePrompt", projected)
            self.assertNotIn("status", projected)
            self.assertNotIn("hermes", argv)
            self.assertNotIn("chat", argv)
            self.assertNotIn("shell", popen.call_args.kwargs)

    def test_restricted_commands_cannot_reach_external_mutation_systems(self) -> None:
        allowed = {"reply", "ack", "resolve", "release"}
        for disposition in ("accept", "investigate", "defer", "dismiss"):
            with self.subTest(disposition=disposition), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                registry_path = root / "registry.json"
                registry_path.write_text(json.dumps(registry()), encoding="utf-8")
                claim = fixture("valid-agent-claim.json")
                claim["thread"]["comments"][-1]["body"] = f"pi-action {disposition}"
                calls: list[list[str]] = []
                action.process_claim(
                    claim, registry_path=registry_path, ledger_path=root / "ledger.json",
                    aaron_user_id="user-aaron-fixture", runner=ok_runner(calls), now=UTC_NOW,
                )
                self.assertTrue(calls)
                for argv in calls:
                    if argv[:2] == ["doct-agent", "documents"]:
                        self.assertEqual(argv[2], "get")
                        continue
                    self.assertEqual(argv[:2], ["doct-agent", "plans"])
                    self.assertIn(argv[2], allowed)
                    joined = " ".join(argv).lower()
                    for forbidden in ("hermes", "linear", "todoist", "benchmark", "git", "config", "task create"):
                        self.assertNotIn(forbidden, joined)


if __name__ == "__main__":
    unittest.main()
