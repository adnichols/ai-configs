import json
import subprocess
import unittest
from datetime import date, datetime
from unittest import mock
from zoneinfo import ZoneInfo

from _hermes.default.scripts import pi_analytics_collector as collector


DENVER = ZoneInfo("America/Denver")


def sample_report(local_date: date, start: datetime, end: datetime, errors: int = 1) -> dict:
    return {
        "schema_version": "pi-session-analytics/v1",
        "reporting_window": {
            "timezone": "America/Denver",
            "local_date": local_date.isoformat(),
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
        "record_counts": {
            "input_files": 1,
            "lines_total": 3,
            "malformed_lines": 0,
            "parsed_records": 3,
            "records_in_window": 3,
            "message_records_in_window": 3,
            "sessions": 1,
            "assistant_terminal_attempts": 1,
            "error_attempts": errors,
        },
        "category_counts": {
            "empty_stream": errors,
            "timeout": 0,
            "goaway": 0,
            "http2": 0,
            "auth": 0,
            "config": 0,
            "other": 0,
        },
    }


class CCorePublishTest(unittest.TestCase):
    def setUp(self) -> None:
        self.local_date = date(2026, 7, 19)
        self.start = datetime(2026, 7, 19, tzinfo=DENVER)
        self.end = datetime(2026, 7, 20, tzinfo=DENVER)
        self.report = sample_report(self.local_date, self.start, self.end)
        self.canonical = collector.canonical_json(self.report)
        self.config = {"ccore_binary": "ccore-test", "ccore_space": "Private"}
        self.title = "pi-analytics/v1/dever/2026-07-19"

    def test_new_report_uses_fixed_create_argv_and_only_canonical_aggregate(self) -> None:
        sentinel = "PROMPT_SENTINEL secret/path tool-arguments"
        responses = [
            subprocess.CompletedProcess([], 0, json.dumps({"documents": []}), ""),
            subprocess.CompletedProcess([], 0, json.dumps({"id": "doc-1"}), ""),
        ]
        with mock.patch.object(collector, "_run", side_effect=responses) as run:
            collector.publish_report(
                self.config,
                self.title,
                self.canonical,
                self.local_date,
                self.start,
                self.end,
                10**12,
            )
        create_argv = run.call_args_list[1].args[0]
        self.assertEqual(
            create_argv,
            [
                "ccore-test", "doc", "new", "Private", self.title, self.canonical,
                "--kind", "note", "--content-type", "application/json",
            ],
        )
        self.assertNotIn(sentinel, "\n".join(create_argv))
        self.assertFalse(any(word in create_argv for word in ("delete", "archive", "retention")))

    def test_existing_report_on_later_page_is_reused_without_create(self) -> None:
        responses = [
            subprocess.CompletedProcess([], 0, json.dumps({
                "documents": [{"id": "unrelated", "title": "other"}], "next_cursor": 500
            }), ""),
            subprocess.CompletedProcess([], 0, json.dumps({
                "documents": [{"id": "doc-1", "title": self.title}], "next_cursor": None
            }), ""),
            subprocess.CompletedProcess([], 0, json.dumps({"document": {"content": self.canonical}}), ""),
        ]
        with mock.patch.object(collector, "_run", side_effect=responses) as run:
            collector.publish_report(
                self.config, self.title, self.canonical, self.local_date, self.start, self.end, 10**12
            )
        self.assertEqual(run.call_count, 3)
        self.assertEqual(run.call_args_list[0].args[0][-2:], ["--cursor", "0"])
        self.assertEqual(run.call_args_list[1].args[0][-2:], ["--cursor", "500"])
        self.assertEqual(run.call_args_list[2].args[0][1:3], ["doc", "show"])

    def test_identical_existing_report_is_reused_without_create(self) -> None:
        responses = [
            subprocess.CompletedProcess([], 0, json.dumps({"documents": [{"id": "doc-1", "title": self.title}]}), ""),
            subprocess.CompletedProcess([], 0, json.dumps({"document": {"content": self.canonical}}), ""),
        ]
        with mock.patch.object(collector, "_run", side_effect=responses) as run:
            collector.publish_report(
                self.config, self.title, self.canonical, self.local_date, self.start, self.end, 10**12
            )
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[1].args[0][1:3], ["doc", "show"])

    def test_real_ccore_show_shape_uses_current_version_content(self) -> None:
        payload = {
            "document": {"id": "doc-1", "title": self.title},
            "current_version": {"content_sha256": "fixture-hash"},
            "current_version_content": self.canonical.rstrip("\n"),
            "counts": {"versions": 1},
        }
        self.assertEqual(collector.parse_document_content(json.dumps(payload)), self.canonical)

    def test_conflicting_same_title_report_is_rejected(self) -> None:
        conflicting = collector.canonical_json(
            sample_report(self.local_date, self.start, self.end, errors=0)
        )
        responses = [
            subprocess.CompletedProcess([], 0, json.dumps({"items": [{"document_id": "doc-1", "title": self.title}]}), ""),
            subprocess.CompletedProcess([], 0, json.dumps({"content": conflicting}), ""),
        ]
        with mock.patch.object(collector, "_run", side_effect=responses):
            with self.assertRaises(collector.ReportConflict):
                collector.publish_report(
                    self.config, self.title, self.canonical, self.local_date, self.start, self.end, 10**12
                )

    def test_noncanonical_or_extra_raw_fields_never_reach_publish(self) -> None:
        raw = json.loads(self.canonical)
        raw["prompt"] = "PROMPT_SENTINEL"
        with self.assertRaises(collector.AnalyzerFailure):
            collector.parse_canonical_report(
                collector.canonical_json(raw), self.local_date, self.start, self.end
            )
        with self.assertRaises(collector.AnalyzerFailure):
            collector.parse_canonical_report(
                json.dumps(self.report, indent=2) + "\n", self.local_date, self.start, self.end
            )

    def test_failed_create_reconciles_interrupted_run(self) -> None:
        responses = [
            subprocess.CompletedProcess([], 0, json.dumps({"documents": []}), ""),
            subprocess.CompletedProcess([], 1, "", "interrupted"),
            subprocess.CompletedProcess([], 0, json.dumps({"documents": [{"id": "doc-1", "title": self.title}]}), ""),
            subprocess.CompletedProcess([], 0, json.dumps({"current_version": {"content": self.canonical}}), ""),
        ]
        with mock.patch.object(collector, "_run", side_effect=responses):
            collector.publish_report(
                self.config, self.title, self.canonical, self.local_date, self.start, self.end, 10**12
            )


if __name__ == "__main__":
    unittest.main()
