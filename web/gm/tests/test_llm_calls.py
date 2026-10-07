"""Retained call detail behind ``GET /gm/api/llm/calls/<call_id>`` (gm-portal-s2b)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from django.test import override_settings

from tools.spec_traceability import covers_requirement
from web.gm.tests._support import GmTestCase
from world.observability import transcript

CALL = "ab" * 16
OTHER = "cd" * 16


def _url(call_id: str) -> str:
    return f"/gm/api/llm/calls/{call_id}"


class LlmCallDetailTest(GmTestCase):
    def setUp(self):
        super().setUp()
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        for item in (
            mock.patch.object(transcript, "_transcript_dir", return_value=str(self.root)),
            mock.patch.object(transcript, "_today", side_effect=lambda: self.today),
        ):
            item.start()
            self.addCleanup(item.stop)
        self.today = date(2026, 10, 7)
        enabled = override_settings(LLM_TRANSCRIPT_ENABLED=True)
        enabled.enable()
        self.addCleanup(enabled.disable)
        self.client = self.client_for("developer")

    @covers_requirement('gm-operations-dashboard::validated-retained-call-detail')
    def test_malformed_identifiers_are_rejected_before_lookup(self):
        with mock.patch.object(transcript, "find") as find:
            for bad in ("AB" * 16, "ab" * 15, "zz" * 16, "ab" * 16 + "0", "not-a-call-id"):
                with self.subTest(call_id=bad):
                    self.assert_error_envelope(self.client.get(_url(bad)), 400, "invalid_call_id")
        find.assert_not_called()

    @covers_requirement('gm-operations-dashboard::validated-retained-call-detail')
    def test_unknown_call_is_not_found(self):
        transcript.write({"kind": "outcome", "call_id": OTHER})
        self.assert_error_envelope(self.client.get(_url(CALL)), 404, "transcript_not_found")

    @covers_requirement('gm-operations-dashboard::validated-retained-call-detail')
    def test_disabled_transcripts_answer_409(self):
        with override_settings(LLM_TRANSCRIPT_ENABLED=False):
            self.assert_error_envelope(self.client.get(_url(CALL)), 409, "transcript_disabled")

    @covers_requirement('gm-operations-dashboard::validated-retained-call-detail')
    def test_retained_call_returns_outcome_and_ordered_exchanges_across_dates(self):
        self.today = date(2026, 10, 6)
        transcript.write({"kind": "exchange", "call_id": CALL, "attempt": 0, "request": {"messages": []}})
        self.today = date(2026, 10, 7)
        transcript.write({"kind": "exchange", "call_id": CALL, "attempt": 1, "response": "原始文字"})
        transcript.write({"kind": "outcome", "call_id": CALL, "result": "degraded",
                          "attempts": [{"attempt": 0, "validation_errors": ["x"]}]})
        transcript.write({"kind": "outcome", "call_id": OTHER})
        data = self.assert_ok_envelope(self.client.get(_url(CALL)))
        self.assertEqual(data["outcome"]["result"], "degraded")
        # Newest date first, file order within a date (S2a lookup order).
        self.assertEqual([e["attempt"] for e in data["exchanges"]], [1, 0])
        self.assertEqual(data["exchanges"][0]["response"], "原始文字")

    @covers_requirement('gm-operations-dashboard::validated-retained-call-detail')
    def test_outcome_only_and_exchange_only_calls_return_what_exists(self):
        transcript.write({"kind": "outcome", "call_id": CALL, "result": "degraded",
                          "reason": "profile_disabled", "attempts": []})
        data = self.assert_ok_envelope(self.client.get(_url(CALL)))
        self.assertEqual((data["outcome"]["reason"], data["exchanges"]), ("profile_disabled", []))
        transcript.write({"kind": "exchange", "call_id": OTHER, "attempt": 0})
        data = self.assert_ok_envelope(self.client.get(_url(OTHER)))
        self.assertIsNone(data["outcome"])
        self.assertEqual(len(data["exchanges"]), 1)

    @covers_requirement('gm-operations-dashboard::validated-retained-call-detail')
    def test_best_effort_read_failures_map_to_404_or_partial_success(self):
        transcript.write({"kind": "outcome", "call_id": CALL, "result": "ok"})
        with mock.patch.object(transcript, "_read_matches", side_effect=PermissionError("denied")), \
                mock.patch("sys.stderr"):
            self.assert_error_envelope(self.client.get(_url(CALL)), 404, "transcript_not_found")
        (self.root / "2026-10-06.jsonl").write_text("{broken\n", encoding="utf-8")
        with mock.patch("sys.stderr"):
            data = self.assert_ok_envelope(self.client.get(_url(CALL)))
        self.assertEqual(data["outcome"]["result"], "ok")

    @covers_requirement('gm-operations-dashboard::landed-foundation-and-transcript-prerequisites')
    def test_access_matrix(self):
        transcript.write({"kind": "outcome", "call_id": CALL, "result": "ok"})
        self.assert_error_envelope(self.client_for("anonymous").get(_url(CALL)), 401, "unauthenticated")
        self.assert_error_envelope(self.client_for("player").get(_url(CALL)), 403, "forbidden")
        for kind in ("developer", "superuser"):
            with self.subTest(kind=kind):
                self.assert_ok_envelope(self.client_for(kind).get(_url(CALL)))
