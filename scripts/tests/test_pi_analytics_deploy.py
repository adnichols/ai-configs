import json
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from _hermes.default.scripts import pi_analytics_collector as collector


class CollectorDeployTest(unittest.TestCase):
    def test_completed_denver_day_is_dst_safe(self) -> None:
        report_date, start, end = collector.completed_day(
            datetime(2026, 3, 9, 12, tzinfo=timezone.utc)
        )
        self.assertEqual(report_date.isoformat(), "2026-03-08")
        self.assertEqual(start.isoformat(), "2026-03-08T00:00:00-07:00")
        self.assertEqual(end.isoformat(), "2026-03-09T00:00:00-06:00")
        self.assertEqual((end.astimezone(timezone.utc) - start.astimezone(timezone.utc)).total_seconds(), 23 * 3600)

        report_date, start, end = collector.completed_day(
            datetime(2026, 11, 2, 12, tzinfo=timezone.utc)
        )
        self.assertEqual(report_date.isoformat(), "2026-11-01")
        self.assertEqual((end.astimezone(timezone.utc) - start.astimezone(timezone.utc)).total_seconds(), 25 * 3600)

    def test_status_json_reads_only_status_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            status_path = Path(tmp) / "last-run.json"
            expected = {
                "host": "dever",
                "expected_date": "2026-07-19",
                "started_at": "2026-07-20T11:00:00Z",
                "finished_at": "2026-07-20T11:00:03Z",
                "state": "succeeded",
            }
            status_path.write_text(json.dumps(expected), encoding="utf-8")
            with mock.patch.object(collector, "load_config") as load_config, mock.patch.object(
                collector, "run_analyzer"
            ) as run_analyzer, mock.patch.object(collector, "publish_report") as publish, mock.patch.object(
                collector, "atomic_write_status"
            ) as write_status:
                with mock.patch("sys.stdout") as stdout:
                    result = collector.main(
                        ["--status", "--json", "--status-file", str(status_path), "--config", "/must/not/read"]
                    )
            self.assertEqual(result, 0)
            load_config.assert_not_called()
            run_analyzer.assert_not_called()
            publish.assert_not_called()
            write_status.assert_not_called()
            output = "".join(call.args[0] for call in stdout.write.call_args_list)
            self.assertEqual(json.loads(output), expected)

    def test_missing_status_is_not_run_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing.json"
            self.assertEqual(collector.read_status(path)["state"], "not_run")
            self.assertFalse(path.exists())

    def test_atomic_status_write_leaves_no_temp_and_uses_private_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state" / "last-run.json"
            value = {
                "host": "mbp", "expected_date": "2026-07-19", "started_at": "start",
                "finished_at": None, "state": "running",
            }
            collector.atomic_write_status(path, value)
            self.assertEqual(json.loads(path.read_text()), value)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(list(path.parent.glob("*.tmp")), [])

    def test_all_documented_status_states_are_readable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "status.json"
            for state in sorted(collector.VALID_STATES):
                path.write_text(json.dumps({"state": state}), encoding="utf-8")
                self.assertEqual(collector.read_status(path)["state"], state)

    def test_runtime_config_requires_host_timezone_roots_private_space_and_analyzer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            config = {
                "enabled": True,
                "host": "dever",
                "timezone": "America/Denver",
                "input_roots": ["/explicit/sessions"],
                "ccore_space": "Private",
                "analyzer_path": "/opt/pi_session_analytics.py",
            }
            path.write_text(json.dumps(config), encoding="utf-8")
            loaded = collector.load_config(path)
            self.assertEqual(loaded["ccore_binary"], "ccore")
            self.assertEqual(loaded["input_roots"], ["/explicit/sessions"])

    def test_run_analyzer_uses_exact_boundaries_explicit_roots_and_no_shell(self) -> None:
        config = {
            "analyzer_path": "/opt/pi_session_analytics.py",
            "input_roots": ["/one", "/two"],
        }
        _, start, end = collector.completed_day(datetime(2026, 7, 20, 12, tzinfo=timezone.utc))
        completed = mock.Mock(returncode=0, stdout="{}\n", stderr="")
        with mock.patch.object(collector, "_run", return_value=completed) as run:
            collector.run_analyzer(config, start, end, 10**12)
        argv = run.call_args.args[0]
        self.assertEqual(argv[1:3], ["/opt/pi_session_analytics.py", "--input-root"])
        self.assertIn("/one", argv)
        self.assertIn("/two", argv)
        self.assertEqual(argv[-4:], ["--window-start", start.isoformat(), "--window-end", end.isoformat()])

    def test_collector_lock_serializes_overlapping_host_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            status_path = Path(tmp) / "state" / "last-run.json"
            first_acquired = threading.Event()
            release_first = threading.Event()
            second_acquired = threading.Event()

            def first() -> None:
                with collector.collector_lock(status_path):
                    first_acquired.set()
                    release_first.wait(timeout=2)

            def second() -> None:
                first_acquired.wait(timeout=2)
                with collector.collector_lock(status_path):
                    second_acquired.set()

            first_thread = threading.Thread(target=first)
            second_thread = threading.Thread(target=second)
            first_thread.start()
            second_thread.start()
            self.assertTrue(first_acquired.wait(timeout=2))
            self.assertFalse(second_acquired.wait(timeout=0.1))
            release_first.set()
            self.assertTrue(second_acquired.wait(timeout=2))
            first_thread.join(timeout=2)
            second_thread.join(timeout=2)
            self.assertFalse(first_thread.is_alive())
            self.assertFalse(second_thread.is_alive())
            self.assertEqual((status_path.parent / ".pi-analytics-collector.lock").stat().st_mode & 0o777, 0o600)

    def test_invalid_config_replaces_stale_success_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "config.json"
            status_path = root / "state" / "last-run.json"
            status_path.parent.mkdir()
            status_path.write_text(json.dumps({
                "host": "dever",
                "expected_date": "2026-07-18",
                "started_at": "old",
                "finished_at": "old",
                "state": "succeeded",
            }), encoding="utf-8")
            config_path.write_text("not-json", encoding="utf-8")
            self.assertEqual(collector.run_collection(config_path, status_path, 1800), 1)
            current = json.loads(status_path.read_text(encoding="utf-8"))
            self.assertEqual(current["state"], "publish_failed")
            self.assertIsNone(current["host"])
            self.assertEqual(current["message"], "collector configuration is invalid or unreadable")
            self.assertNotEqual(current["started_at"], "old")

    def test_run_collection_maps_failure_states_and_success(self) -> None:
        config = {
            "enabled": True,
            "host": "dever",
            "timezone": "America/Denver",
            "input_roots": ["/sessions"],
            "ccore_space": "Private",
            "analyzer_path": "/analyzer",
            "ccore_binary": "ccore",
        }
        cases = [
            (collector.AnalyzerFailure("bad"), None, "analyzer_failed", 1),
            (None, collector.PublishFailure("bad"), "publish_failed", 1),
            (None, collector.ReportConflict("bad"), "report_conflict", 1),
            (collector.CollectorTimeout("slow"), None, "timed_out", 1),
            (None, None, "succeeded", 0),
        ]
        for analyzer_error, publish_error, expected_state, expected_code in cases:
            with self.subTest(state=expected_state), mock.patch.object(
                collector, "load_config", return_value=config
            ), mock.patch.object(collector, "run_analyzer") as analyzer, mock.patch.object(
                collector, "parse_canonical_report", return_value=({}, "{}\n")
            ), mock.patch.object(collector, "publish_report") as publish, mock.patch.object(
                collector, "atomic_write_status"
            ) as write_status:
                if analyzer_error:
                    analyzer.side_effect = analyzer_error
                else:
                    analyzer.return_value = "{}\n"
                if publish_error:
                    publish.side_effect = publish_error
                with tempfile.TemporaryDirectory() as tmp:
                    code = collector.run_collection(
                        Path("config"), Path(tmp) / "last-run.json", 1800
                    )
                self.assertEqual(code, expected_code)
                self.assertEqual(write_status.call_args_list[-1].args[1]["state"], expected_state)


if __name__ == "__main__":
    unittest.main()
