import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import pi_session_analytics as analytics


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "pi-session-analytics"
WINDOW_START = "2026-07-19T00:00:00-06:00"
WINDOW_END = "2026-07-20T00:00:00-06:00"
PRIVACY_PREFIX = "PRIVACY_SENTINEL_"
BASELINE = (
    Path(__file__).resolve().parents[2]
    / "thoughts"
    / "retro"
    / "pi-session-analytics-sanitized-baseline-v1.json"
)


class PiSessionAnalyticsTest(unittest.TestCase):
    def window(self):
        return analytics.reporting_window(WINDOW_START, WINDOW_END)

    def run_cli(self, fixture_name):
        command = [
            sys.executable,
            str(Path(analytics.__file__)),
            "--input-root",
            str(FIXTURES / fixture_name),
            "--window-start",
            WINDOW_START,
            "--window-end",
            WINDOW_END,
        ]
        return subprocess.run(command, check=False, capture_output=True, text=True)

    def test_comprehensive_fixture_locks_v1_aggregate(self):
        report = analytics.analyze([FIXTURES / "comprehensive"], self.window())
        self.assertEqual(report["schema_version"], "pi-session-analytics/v1")
        self.assertEqual(
            report["reporting_window"],
            {
                "timezone": "America/Denver",
                "local_date": "2026-07-19",
                "start": WINDOW_START,
                "end": WINDOW_END,
            },
        )
        self.assertEqual(
            report["record_counts"],
            {
                "input_files": 1,
                "lines_total": 11,
                "malformed_lines": 0,
                "parsed_records": 11,
                "records_in_window": 11,
                "message_records_in_window": 10,
                "sessions": 1,
                "assistant_terminal_attempts": 8,
                "error_attempts": 7,
            },
        )
        self.assertEqual(
            report["category_counts"],
            {
                "empty_stream": 1,
                "timeout": 1,
                "goaway": 1,
                "http2": 1,
                "auth": 1,
                "config": 1,
                "other": 1,
            },
        )

    def test_output_is_canonical_and_contains_no_privacy_sentinel(self):
        result = self.run_cli("comprehensive")
        self.assertEqual(result.returncode, 0, result.stderr)
        parsed = json.loads(result.stdout)
        self.assertEqual(result.stdout, analytics.canonical_json(parsed))
        self.assertNotIn(PRIVACY_PREFIX, result.stdout)
        for forbidden_fragment in (
            "content",
            "prompt",
            "source",
            "path",
            "credential",
            "toolCall",
            "thinking",
            "fixture-provider",
            "fixture-model",
            "fixture-api",
            "Provider returned",
        ):
            self.assertNotIn(forbidden_fragment, result.stdout)

    def test_checked_in_baseline_is_fixture_derived(self):
        report = analytics.analyze([FIXTURES / "comprehensive"], self.window())
        self.assertEqual(BASELINE.read_text(encoding="utf-8"), analytics.canonical_json(report))
        self.assertNotIn(PRIVACY_PREFIX, BASELINE.read_text(encoding="utf-8"))

    def test_zero_error_fixture_is_one_successful_session(self):
        report = analytics.analyze([FIXTURES / "zero-error"], self.window())
        self.assertEqual(report["record_counts"]["sessions"], 1)
        self.assertEqual(report["record_counts"]["assistant_terminal_attempts"], 1)
        self.assertEqual(report["record_counts"]["error_attempts"], 0)
        self.assertEqual(sum(report["category_counts"].values()), 0)

    def test_zero_session_fixture_ignores_nonterminal_and_out_of_window_errors(self):
        report = analytics.analyze([FIXTURES / "zero-session"], self.window())
        self.assertEqual(report["record_counts"]["sessions"], 0)
        self.assertEqual(report["record_counts"]["assistant_terminal_attempts"], 0)
        self.assertEqual(report["record_counts"]["error_attempts"], 0)
        self.assertEqual(sum(report["category_counts"].values()), 0)

    def test_only_error_message_drives_classification(self):
        record = {
            "type": "message",
            "timestamp": "2026-07-19T12:00:00Z",
            "message": {
                "role": "assistant",
                "provider": "fixture-provider",
                "model": "fixture-model",
                "api": "fixture-api",
                "stopReason": "error",
                "errorMessage": "unrecognized structured failure",
                "content": "empty_stream timeout goaway http2 invalid token unsupported model",
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "session.jsonl").write_text(json.dumps(record) + "\n", encoding="utf-8")
            report = analytics.analyze([root], self.window())
        self.assertEqual(report["category_counts"]["other"], 1)
        self.assertEqual(sum(report["category_counts"].values()), 1)

    def test_fixed_case_insensitive_error_tokens_and_precedence(self):
        cases = {
            "EMPTY_STREAM": "empty_stream",
            "request timeout": "timeout",
            "request TIMED OUT": "timeout",
            "HTTP/2 GOAWAY": "goaway",
            "HTTP2 reset": "http2",
            "Account Suspended": "auth",
            "TOKEN REJECTED": "auth",
            "Invalid-Provider": "config",
            "MODEL NOT SUPPORTED": "config",
            "something else": "other",
            None: "other",
        }
        for message, expected in cases.items():
            with self.subTest(message=message):
                self.assertEqual(analytics.classify_error(message), expected)

    def test_out_of_window_appends_and_files_do_not_change_daily_report_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            in_window = {
                "type": "message",
                "timestamp": "2026-07-19T12:00:00Z",
                "message": {"role": "assistant", "stopReason": "stop"},
            }
            daily = root / "daily.jsonl"
            daily.write_text(json.dumps(in_window) + "\n", encoding="utf-8")
            before = analytics.canonical_json(analytics.analyze([root], self.window()))
            out_of_window = {
                "type": "message",
                "timestamp": "2026-07-20T12:00:00Z",
                "message": {"role": "assistant", "stopReason": "stop"},
            }
            with daily.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(out_of_window) + "\n")
                handle.write("later malformed private transcript\n")
            (root / "later.jsonl").write_text(json.dumps(out_of_window) + "\n", encoding="utf-8")
            after = analytics.canonical_json(analytics.analyze([root], self.window()))
        self.assertEqual(before, after)
        self.assertEqual(json.loads(after)["record_counts"]["input_files"], 1)

    def test_symlinked_jsonl_cannot_escape_explicit_root(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "allowed"
            root.mkdir()
            outside = base / "private.jsonl"
            outside.write_text(
                json.dumps({
                    "type": "message",
                    "timestamp": "2026-07-19T12:00:00Z",
                    "message": {"role": "assistant", "stopReason": "error", "errorMessage": "timeout"},
                }) + "\n",
                encoding="utf-8",
            )
            (root / "escaped.jsonl").symlink_to(outside)
            with self.assertRaisesRegex(analytics.AnalyticsError, "outside its resolved boundary"):
                analytics.analyze([root], self.window())

    def test_repeatable_roots_are_deduplicated(self):
        root = FIXTURES / "zero-error"
        report = analytics.analyze([root, root], self.window())
        self.assertEqual(report["record_counts"]["input_files"], 1)
        self.assertEqual(report["record_counts"]["sessions"], 1)

    def test_window_must_be_exact_denver_calendar_day(self):
        with self.assertRaisesRegex(analytics.AnalyticsError, "exactly one America/Denver calendar day"):
            analytics.reporting_window(
                "2026-07-19T01:00:00-06:00", "2026-07-20T01:00:00-06:00"
            )
        spring = analytics.reporting_window(
            "2026-03-08T00:00:00-07:00", "2026-03-09T00:00:00-06:00"
        )
        self.assertEqual(spring.local_date.isoformat(), "2026-03-08")

    def test_cli_rejects_missing_input_root(self):
        result = subprocess.run(
            [
                sys.executable,
                str(Path(analytics.__file__)),
                "--input-root",
                str(FIXTURES / "missing"),
                "--window-start",
                WINDOW_START,
                "--window-end",
                WINDOW_END,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("an input root is not a directory", result.stderr)
        self.assertNotIn(str(FIXTURES), result.stderr)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
