"""Tests for the retained LLM call transcript sink (gm-portal-s2a)."""

from datetime import date
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import os
import unittest

from django.test import override_settings

from tools.spec_traceability import covers_requirement
from world.observability import transcript


class _TranscriptCase(unittest.TestCase):
    """A temporary transcript directory with a pinned local date."""

    today = date(2026, 10, 7)

    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.root = Path(self._tmp.name) / "llm"
        patches = [
            patch.object(transcript, "_transcript_dir", return_value=str(self.root)),
            patch.object(transcript, "_today", side_effect=lambda: self.today),
            override_settings(LLM_TRANSCRIPT_ENABLED=True, LLM_TRANSCRIPT_RETENTION_DAYS=14),
        ]
        for item in patches:
            item.enable() if isinstance(item, override_settings) else item.start()
            self.addCleanup(item.disable if isinstance(item, override_settings) else item.stop)
        self.addCleanup(self._tmp.cleanup)

    def lines(self, day):
        path = self.root / f"{day.isoformat()}.jsonl"
        return path.read_text(encoding="utf-8").splitlines()


class WriteAndFindTests(_TranscriptCase):
    def test_write_appends_unicode_json_lines_to_the_local_date_file(self):
        transcript.write({"kind": "outcome", "call_id": "a" * 32, "final_text": "夜色裡的燈火"})
        transcript.write({"kind": "exchange", "call_id": "b" * 32})
        lines = self.lines(self.today)
        self.assertEqual(len(lines), 2)
        self.assertIn("夜色裡的燈火", lines[0])
        self.assertNotIn("\\u", lines[0])
        self.assertEqual(json.loads(lines[1])["call_id"], "b" * 32)

    @covers_requirement('llm-transcript::retained-daily-transcript-storage')
    def test_find_returns_matching_records_newest_date_first_in_file_order(self):
        target, other = "c" * 32, "d" * 32
        self.today = date(2026, 10, 6)
        transcript.write({"call_id": target, "seq": 1})
        transcript.write({"call_id": other, "seq": 2})
        self.today = date(2026, 10, 7)
        transcript.write({"call_id": target, "seq": 3})
        transcript.write({"call_id": target, "seq": 4, "text": "回聲"})
        records = transcript.find(target)
        self.assertEqual([record["seq"] for record in records], [3, 4, 1])
        self.assertEqual(records[1]["text"], "回聲")

    def test_find_ignores_files_outside_the_retention_window(self):
        target = "e" * 32
        self.today = date(2026, 9, 20)
        transcript.write({"call_id": target, "seq": "old"})
        self.today = date(2026, 10, 7)
        with override_settings(LLM_TRANSCRIPT_RETENTION_DAYS=14):
            self.assertEqual(transcript.find(target), [])
        with override_settings(LLM_TRANSCRIPT_RETENTION_DAYS=30):
            self.assertEqual([r["seq"] for r in transcript.find(target)], ["old"])

    def test_write_scrubs_secrets_structurally_and_in_escaped_form(self):
        quoted = 'pa"ss\\word'
        transcript.write(
            {
                "call_id": "f" * 32,
                "response": {"echo": {"Authorization": "Bearer sk-live", "nested": ["sk-live"]}},
                "error": {"message": f"denied {quoted}"},
                "sk-live": "key in a mapping key",
            },
            secrets=("sk-live", quoted, "", "   "),
        )
        line = self.lines(self.today)[0]
        self.assertNotIn("sk-live", line)
        self.assertNotIn("word", line)
        self.assertIn("Bearer [redacted]", line)
        self.assertIn("key in a mapping key", line)


class RetentionTests(_TranscriptCase):
    @covers_requirement('llm-transcript::retained-daily-transcript-storage')
    def test_prune_keeps_today_and_the_previous_retention_minus_one_dates(self):
        self.root.mkdir(parents=True)
        for name in ("2026-09-24.jsonl", "2026-09-23.jsonl", "2026-10-07.jsonl", "notes.txt"):
            (self.root / name).write_text("{}\n", encoding="utf-8")
        transcript.prune()
        remaining = sorted(os.listdir(self.root))
        self.assertEqual(remaining, ["2026-09-24.jsonl", "2026-10-07.jsonl", "notes.txt"])

    def test_prune_without_a_directory_is_a_no_op(self):
        transcript.prune()
        self.assertFalse(self.root.exists())

    def test_invalid_injected_retention_falls_back_to_the_default(self):
        for value in (0, True, "7"):
            with self.subTest(value=value), override_settings(LLM_TRANSCRIPT_RETENTION_DAYS=value):
                self.assertEqual(transcript.retention_days(), transcript.DEFAULT_RETENTION_DAYS)


class DisabledAndFailureTests(_TranscriptCase):
    @covers_requirement('llm-transcript::retained-daily-transcript-storage')
    def test_disabled_write_is_a_no_op_and_lookup_reports_disabled(self):
        with override_settings(LLM_TRANSCRIPT_ENABLED=False):
            transcript.write({"call_id": "a" * 32})
            self.assertFalse(transcript.is_enabled())
            with self.assertRaises(transcript.TranscriptDisabled):
                transcript.find("a" * 32)
        self.assertFalse(self.root.exists())

    @covers_requirement('llm-transcript::retained-daily-transcript-storage')
    def test_unwritable_storage_and_unserialisable_records_never_raise(self):
        self.root.parent.mkdir(parents=True, exist_ok=True)
        self.root.write_text("not a directory", encoding="utf-8")
        with patch("sys.stderr", new_callable=StringIO) as err:
            transcript.write({"call_id": "a" * 32})
            transcript.write({"call_id": "b" * 32, "value": object()})
        self.assertEqual(err.getvalue().count("[llm_transcript] write failed"), 2)

    def test_stderr_failure_is_contained(self):
        with patch.object(transcript, "_transcript_dir", side_effect=OSError("gone")), \
                patch("builtins.print", side_effect=OSError("stderr closed")):
            transcript.write({"call_id": "a" * 32})
            transcript.prune()

    @covers_requirement('llm-transcript::retained-daily-transcript-storage')
    def test_malformed_lines_and_unreadable_files_are_skipped_best_effort(self):
        target = "a" * 32
        transcript.write({"call_id": target, "seq": 1})
        with open(self.root / f"{self.today.isoformat()}.jsonl", "a", encoding="utf-8") as handle:
            handle.write('{"call_id": "' + target + '", broken\n')
        yesterday = self.root / "2026-10-06.jsonl"
        yesterday.write_text(json.dumps({"call_id": target}) + "\n", encoding="utf-8")
        real_open = open

        def flaky_open(path, *args, **kwargs):
            if str(path) == str(yesterday):
                raise PermissionError("denied")
            return real_open(path, *args, **kwargs)

        with patch("sys.stderr", new_callable=StringIO) as err, \
                patch("builtins.open", side_effect=flaky_open):
            records = transcript.find(target)
        self.assertEqual([record["seq"] for record in records], [1])
        self.assertIn("malformed", err.getvalue())
        self.assertIn("read failed for 2026-10-06", err.getvalue())

    def test_unreadable_settings_fail_closed_to_disabled(self):
        with patch.object(transcript, "_settings", side_effect=RuntimeError("unconfigured")):
            self.assertFalse(transcript.is_enabled())
            self.assertEqual(transcript.retention_days(), transcript.DEFAULT_RETENTION_DAYS)
