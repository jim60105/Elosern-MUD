"""Fixed-fixture reader tests: narrative records (task 2.4 / 6.1).

Establishes the delta requirement "Complete curated entity summaries" for the
narrative kind: every approved subtype — events, story threads, letters with
their delivery state, dream sessions/exchanges, director decisions, scheduled
beats, authoring drafts and creative requests — projects a list row and a
detail payload, while a bare identity is refused and an unknown record is a
404. The ``gm-runtime-state::*`` requirement IDs this module covers enter the
traceability index when the change's delta spec is synced at archive.
"""

from __future__ import annotations

from evennia.utils.test_resources import EvenniaTest
from world.narrative.models import (
    AuthoringDraft,
    CreativeRequest,
    DreamSession,
    LetterSend,
    LetterState,
    NarrativeEvent,
    ScheduledBeat,
    StoryDirectorDecision,
    StoryThread,
)

from web.gm.readers import narrative
from web.gm.tests._state_support import (
    failed_sections,
    field_value,
    link_kinds,
    section_keys,
)


class NarrativeReaderTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.event = NarrativeEvent.objects.create(
            source_id="t_reader_event",
            event_type="t_reader_kind",
            content={"note": "合成內容"},
            participants=["t_reader_actor"],
            location="t_reader_place",
            tick=120,
            visibility="private",
        )
        self.thread = StoryThread.objects.create(
            thread_id="t_reader_thread",
            origin="t_reader_origin",
            participants=["t_reader_actor"],
            visible_to=["t_reader_actor"],
            state="active",
            revision=2,
            created_tick=90,
        )
        self.letter = LetterSend.objects.create(
            source_id="t_reader_letter",
            sender_id="t_reader_sender",
            recipient_id="t_reader_recipient",
            recipient_kind="character",
            body="合成書信",
            sent_tick=100,
            due_tick=400,
        )
        LetterState.objects.create(
            letter=self.letter,
            recipient_id="t_reader_recipient",
            due_tick=400,
            status="delivered",
        )
        self.dream = DreamSession.objects.create(
            session_id="t_reader_dream",
            owner_id="t_reader_actor",
            completed_exchanges=3,
            state="open",
            created_tick=80,
        )
        self.decision = StoryDirectorDecision.objects.create(
            decision_id="t_reader_decision",
            owner_id="t_reader_actor",
            source_kind="event",
            source_ref="t_reader_event",
            outcome="scheduled",
            scheduled=True,
            created_tick=70,
        )
        self.beat = ScheduledBeat.objects.create(
            beat_id="t_reader_beat",
            decision=self.decision,
            owner_id="t_reader_actor",
            thread=self.thread,
            kind="state",
            effect="t_reader_effect",
            arrangement_revision=2,
            execution_ref="t_reader_event",
            created_tick=70,
        )
        self.draft = AuthoringDraft.objects.create(
            draft_id="t_reader_draft",
            owner_id="t_reader_actor",
            direction={"note": "合成草稿"},
            revision=2,
            confirmed_revision=1,
            created_tick=60,
        )
        self.request = CreativeRequest.objects.create(
            submission_key="t_reader_request",
            draft=self.draft,
            owner_id="t_reader_actor",
            version=1,
            direction={"note": "合成請求"},
            validation_status="valid",
            submitted_tick=50,
        )

    def _lists(self):
        return {
            subtype: narrative.list_items(subtype, {})
            for subtype in narrative.SUBTYPES
        }

    def test_every_approved_subtype_yields_exactly_its_own_records(self):
        lists = self._lists()
        self.assertEqual(
            {subtype: [item["id"] for item in items] for subtype, items in lists.items()},
            {
                "event": ["event:t_reader_event"],
                "thread": ["thread:t_reader_thread"],
                "letter": ["letter:t_reader_letter"],
                "dream": ["dream:t_reader_dream"],
                "decision": ["decision:t_reader_decision"],
                "beat": ["beat:t_reader_beat"],
                "draft": ["draft:t_reader_draft"],
                "request": ["request:t_reader_request"],
            },
        )
        for subtype, items in lists.items():
            with self.subTest(subtype=subtype):
                self.assertEqual(items[0]["kind"], "narrative")
                self.assertEqual(items[0]["subtype"], subtype)

    def test_list_rows_carry_the_summary_fields_of_each_subtype(self):
        lists = self._lists()
        self.assertEqual(
            {
                subtype: [field["label"] for field in items[0]["fields"]]
                for subtype, items in lists.items()
            },
            {
                "event": ["事件類型", "tick", "可見性", "地點"],
                "thread": ["狀態", "修訂", "建立 tick", "來源"],
                "letter": ["寄件人", "收件人", "狀態", "到期 tick"],
                "dream": ["擁有者", "狀態", "完成次數", "結果"],
                "decision": ["擁有者", "來源", "結果", "已排程"],
                "beat": ["種類", "效果", "擁有者", "執行參照"],
                "draft": ["擁有者", "修訂", "已確認版本", "建立 tick"],
                "request": ["擁有者", "版本", "驗證", "提交 tick"],
            },
        )
        letter = lists["letter"][0]
        self.assertEqual(field_value(letter, "狀態"), "delivered")

    def test_every_subtype_detail_projects_its_stored_record_as_raw_data(self):
        identities = {
            "event": "event:t_reader_event",
            "thread": "thread:t_reader_thread",
            "letter": "letter:t_reader_letter",
            "dream": "dream:t_reader_dream",
            "decision": "decision:t_reader_decision",
            "beat": "beat:t_reader_beat",
            "draft": "draft:t_reader_draft",
            "request": "request:t_reader_request",
        }
        for subtype, identity in identities.items():
            with self.subTest(subtype=subtype):
                detail = narrative.detail(subtype, identity.split(":", 1)[1])
                self.assertEqual(detail["kind"], "narrative")
                self.assertEqual(detail["id"], identity)
                self.assertEqual(detail["subtype"], subtype)
                self.assertTrue(detail["sections"])
                self.assertEqual(failed_sections(detail), {})
                self.assertEqual(set(detail["raw"]), {"record"})
                self.assertTrue(section_keys(detail))

    def test_event_detail_exposes_content_participants_and_visibility(self):
        detail = narrative.detail("event", "t_reader_event")
        identity = next(section for section in detail["sections"] if section["key"] == "identity")
        rows = {row["label"]: row["value"] for row in identity["rows"]}
        self.assertEqual(rows["事件類型"], "t_reader_kind")
        self.assertEqual(rows["可見性"], "private")
        self.assertEqual(rows["地點"], "t_reader_place")
        content = next(section for section in detail["sections"] if section["key"] == "content")
        self.assertEqual(content["type"], "tree")

    def test_thread_detail_links_its_provenance_sources(self):
        from world.narrative.models import StoryThreadLink

        StoryThreadLink.objects.create(
            thread=self.thread,
            source_kind="event",
            source_ref="t_reader_event",
            relation="caused_by",
            created_tick=90,
        )
        detail = narrative.detail("thread", "t_reader_thread")
        self.assertLessEqual({"narrative"}, link_kinds(detail))

    def test_a_bare_identity_is_refused_and_an_unknown_record_is_a_404(self):
        for identity in ("t_reader_event", "", "unknown:t_reader_event"):
            with self.subTest(identity=identity), self.assertRaises(Exception) as raised:
                narrative.split_identity(identity)
            self.assertEqual(raised.exception.code, "invalid_filter")
        with self.assertRaises(Exception) as missing:
            narrative.detail("event", "t_reader_absent")
        self.assertEqual(missing.exception.code, "object_not_found")

    def test_list_filters_are_applied_to_the_indexed_fields(self):
        self.assertEqual(len(narrative.list_items("event", {"event_type": "t_reader_kind"})), 1)
        self.assertEqual(narrative.list_items("event", {"event_type": "t_other"}), [])
        self.assertEqual(len(narrative.list_items("event", {"visibility": "private"})), 1)
        self.assertEqual(len(narrative.list_items("thread", {"state": "active"})), 1)
        self.assertEqual(len(narrative.list_items("letter", {"status": "delivered"})), 1)
        self.assertEqual(narrative.list_items("letter", {"status": "pending"}), [])
        self.assertEqual(len(narrative.list_items("event", {"owner": "t_reader_place"})), 1)
